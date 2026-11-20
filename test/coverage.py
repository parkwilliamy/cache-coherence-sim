"""Functional coverage model and assertions for the cache coherence emulator.

Implements "Cache Coherence Emulator Test Requirements.xlsx"; each item below is
tagged with its section ID from that sheet. The file has three layers:

1. Coverage definitions and their sampling functions (cocotb-coverage). An item
   only counts when its sampling function is called.
2. Models: plain Python, one per module (DecoderModel, BusModel, CoreModel,
   CacheCtrlModel) plus CoverageModel, which runs all of them on the full chip
   and adds the system-level items. A model is stepped once per clock with the
   signals of that cycle and decides what to sample and which assertions to
   evaluate. No simulator needed, so they are unit-tested (test_coverage_unit.py).
3. Monitors: the cocotb side. They read the design, step a model and fail the
   test when an assertion is violated.
   - CoverageMonitor: the full chip (tb.dut), sampled at every falling clock edge.
   - DecoderUnitMonitor, BusUnitMonitor, CoreUnitMonitor, CacheCtrlUnitMonitor:
     the module testbenches (tb.decoder_tb, ...). Those tests drive the clock by
     hand, so they are sampled explicitly, by tb_utils.tick(), just before each
     rising edge.

Every monitor samples into the same coverage database, so module-level and
full-chip hits count towards the same bins.

Usage, in a test on the full chip (tb.dut):

    monitor = coverage.start_coverage(dut)   # None on gate-level / sv2v builds

In a module-level test:

    monitor = coverage.unit_monitor(coverage.BusUnitMonitor, dut.bus_tb)
    ...
    await tick(dut, monitor)                 # tb_utils.tick

test_coverage_report.py, the last test module, logs the result:

    coverage.report_coverage(cocotb.log.info)
    
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple

import cocotb
from cocotb.triggers import FallingEdge, ReadOnly
from cocotb.utils import get_sim_time
from cocotb_coverage.coverage import (
    CoverPoint, CoverCross, CoverCheck, coverage_section, coverage_db,
)

# ---- Parameters (mirror src/top_params.sv; checked against the DUT on attach) ----
N_CORES = 4
DCACHE_SIZE = 2
ICACHE_SIZE = 4
MEM_SIZE = 4
DATA_WIDTH = 1

ADDR_WIDTH = (MEM_SIZE - 1).bit_length()
IDX_WIDTH = (DCACHE_SIZE - 1).bit_length()
TAG_WIDTH = ADDR_WIDTH - IDX_WIDTH
LINE_WIDTH = TAG_WIDTH + DATA_WIDTH + 3
INST_WIDTH = ADDR_WIDTH + DATA_WIDTH + 1
CORE_SEL_WIDTH = (N_CORES - 1).bit_length()
PROTOCOL_LSB = 3
ALL_CORES = (1 << N_CORES) - 1

# ---- Encodings (docs/encodings.md) ----
CMD_LOAD_RD, CMD_LOAD_WR, CMD_LOAD_MEM, CMD_START = 0, 1, 2, 3
RD, INV, WB = 0, 1, 2
MSI, MESI, MOESI = 0, 1, 2
I, S, E, O, M = 0, 4, 5, 6, 7       # {v, d, x}
LOAD, RUN, READ = 0, 1, 2           # decoder state

STATE_NAMES = {I: "I", S: "S", E: "E", O: "O", M: "M"}
SNOOP_CAUSES = {RD: "snoop_RD", INV: "snoop_INV", WB: "snoop_WB"}

# Legal coherence arcs: (from, to) -> causes.
# Local causes are measured per instruction: the state of the addressed line slot
# when the instruction is first examined versus the state after it completes
# (docs/svg/CCE_FSM1.svg). An eviction and the refill that follows are one arc,
# so M->E is "read miss on a slot holding a different, modified line".
# Snoop causes are measured per snooped transaction that hits the line
# (docs/svg/CCE_FSM2.svg).
TRANSITION_ARCS = {
    (I, E): ["read_miss"],                                     # 4.3
    (I, S): ["read_miss"],                                     # 4.4
    (I, M): ["write_miss"],                                    # 4.5
    (E, E): ["read_hit", "read_miss"],                         # 4.6
    (E, S): ["read_miss", "snoop_RD"],                         # 4.7
    (E, M): ["write_hit", "write_miss"],                       # 4.8
    (S, S): ["read_hit", "read_miss", "snoop_RD", "snoop_WB"], # 4.9
    (S, I): ["snoop_INV"],                                     # 4.10
    (S, E): ["read_miss"],                                     # 4.11
    (S, M): ["write_hit", "write_miss"],                       # 4.12
    (M, I): ["snoop_INV"],                                     # 4.13
    (M, S): ["read_miss", "snoop_RD"],                         # 4.14
    (M, E): ["read_miss"],                                     # 4.15
    (M, O): ["snoop_RD"],                                      # 4.16
    (M, M): ["read_hit", "write_hit", "write_miss"],           # 4.17
    (O, O): ["read_hit", "snoop_RD"],                          # 4.18
    (O, I): ["snoop_INV"],                                     # 4.19
    (O, M): ["write_hit", "write_miss"],                       # 4.20
    (O, S): ["read_miss"],                                     # 4.21
    (O, E): ["read_miss"],                                     # 4.22
    (E, I): ["snoop_INV"],                                     # 4.23
}
STATE_TRANSITIONS = list(TRANSITION_ARCS)


def transition_name(prev, curr):
    return f"cache_ctrl.state_transitions.{STATE_NAMES[prev]}_to_{STATE_NAMES[curr]}"


# ---- Decoding helpers ----
def line_state(line):
    return line & 0b111


def line_tag(line):
    return line >> (DATA_WIDTH + 3)


def split_addr(addr):
    """Return (idx, tag) of an address."""
    return addr & (DCACHE_SIZE - 1), addr >> IDX_WIDTH


def line_hit(line, tag):
    return bool(line & 0b100) and line_tag(line) == tag


def decode_inst(inst):
    """Return (addr, data, op) of an inst_t."""
    return inst >> (DATA_WIDTH + 1), (inst >> 1) & ((1 << DATA_WIDTH) - 1), inst & 1


def inst_kind(inst):
    """Name of an instruction as loaded by the decoder, e.g. 'R2' or 'W1=0'.

    The decoder zeroes the data field of reads, so a read with data != 0 cannot
    be loaded and has no bin.
    """
    addr, data, op = decode_inst(inst)
    if op:
        return f"W{addr}={data}"
    return f"R{addr}" if data == 0 else None


INST_KINDS = [f"R{a}" for a in range(MEM_SIZE)] + [
    f"W{a}={d}" for a in range(MEM_SIZE) for d in range(1 << DATA_WIDTH)
]


def popcount(x):
    return bin(x).count("1")


# ---- Assertion predicates (plain values in, bool out) ----
def start_pulse_ok(start, expected, prev_start):
    """1.1: start goes to every core in the cycle CMD_START is on the pins, and
    only then, so it is never high for two cycles in a row."""
    return start == (ALL_CORES if expected else 0) and not (start & prev_start)


def snoop_valid_ok(snoop_valid, grant, grant_idx):
    """2.2: in the grant cycle every core but the granted one snoops; otherwise none."""
    expected = ALL_CORES & ~(1 << grant_idx) if grant else 0
    return snoop_valid == expected


def done_onehot_ok(done):
    """2.4: at most one core sees done."""
    return popcount(done) <= 1


def req_held_ok(prev_req, prev_done, req):
    """3.1: a request that was pending and not completed is still pending."""
    return bool(prev_done or req) if prev_req else True


def line_holders(lines):
    """Per address, the states of every valid copy across the cores."""
    holders = {addr: [] for addr in range(MEM_SIZE)}
    for core_lines in lines:
        for idx, line in enumerate(core_lines):
            if line & 0b100:
                holders[(line_tag(line) << IDX_WIDTH) | idx].append(line_state(line))
    return holders


def line_invariants(lines):
    """Return (max E copies, max O copies, max M copies, M shares an address with
    another valid copy), the maxima taken over all addresses."""
    max_e = max_o = max_m = 0
    m_shared = False
    for states in line_holders(lines).values():
        n_m = states.count(M)
        max_e = max(max_e, states.count(E))
        max_o = max(max_o, states.count(O))
        max_m = max(max_m, n_m)
        m_shared = m_shared or (n_m > 0 and len(states) > 1)
    return max_e, max_o, max_m, m_shared


# ---- Coverage definitions ----
# Every item of a coverage_section is sampled with the arguments of the function
# it decorates, so there is one sampling function per kind of event.

def _assertion(name):
    """CoverCheck sampled as f(ok, exercised): FAIL when the property is violated,
    PASS when it held in a cycle that actually exercised it."""
    return CoverCheck(
        name,
        f_fail=lambda ok, exercised: not ok,
        f_pass=lambda ok, exercised: ok and exercised,
    )


# Decoder
DecoderCoverage = coverage_section(                                             # 1.3
    CoverPoint("decoder.command_type", vname="cmd",
               bins=[CMD_LOAD_RD, CMD_LOAD_WR, CMD_LOAD_MEM, CMD_START],
               bins_labels=["CMD_LOAD_RD", "CMD_LOAD_WR", "CMD_LOAD_MEM", "CMD_START"])
)


@DecoderCoverage
def sample_decoder_command(cmd):
    pass


@_assertion("decoder.decoder_start_pulse")                                      # 1.1
def assert_decoder_start_pulse(ok, exercised):
    pass


# Bus
@_assertion("bus.snoop_valid_when_grant")                                       # 2.2
def assert_snoop_valid_when_grant(ok, exercised):
    pass


@_assertion("bus.only_one_done_valid")                                          # 2.4
def assert_only_one_done_valid(ok, exercised):
    pass


# Core
CoreCoverage = coverage_section(                                                # 3.4
    CoverPoint("core.req_type", vname="req_type", bins=[RD, INV, WB],
               bins_labels=["RD", "INV", "WB"])
)

SystemGrantCoverage = coverage_section(                                         # 5.3
    CoverPoint("system.cores_granted", vname="core", bins=list(range(N_CORES)))
)


@CoreCoverage
def sample_core_req_type(req_type):
    """Once per bus transaction of a core, in the cycle it completes (done)."""


@SystemGrantCoverage
def sample_core_granted(core):
    """Once per bus transaction, in the cycle the bus grants it."""


@_assertion("core.req_valid_until_done")                                        # 3.1
def assert_req_valid_until_done(ok, exercised):
    pass


# Cache controller
ProtocolCoverage = coverage_section(                                            # 4.1
    # 2'b11 is reserved (behaves as MOESI) and has no bin.
    CoverPoint("cache_ctrl.protocol", vname="protocol", bins=[MSI, MESI, MOESI],
               bins_labels=["MSI", "MESI", "MOESI"])
)


@ProtocolCoverage
def sample_protocol(protocol):
    """Full chip: once per run. cache_ctrl testbench (no run there): once per
    instruction, with the protocol it is examined under."""


CacheControllerCoverage = coverage_section(                                     # 4.2
    # Crossed points cannot use bins_labels, so the bins are the names.
    CoverPoint("cache_ctrl.req_type", vname="req_type", bins=["read", "write"]),
    CoverPoint("cache_ctrl.cache_hit", vname="cache_hit", bins=["miss", "hit"]),
    CoverCross("cache_ctrl.req_hit_cross", items=["cache_ctrl.req_type", "cache_ctrl.cache_hit"]),
)


@CacheControllerCoverage
def sample_cache_request(req_type, cache_hit):
    """Once per instruction, in the first cycle it is examined."""


CacheTransitionCoverage = coverage_section(*[                                   # 4.3 - 4.23
    CoverPoint(transition_name(prev, curr),
               xf=lambda prev, curr, cause: (prev, curr, cause),
               bins=[(prev, curr, cause) for cause in causes],
               bins_labels=causes)
    for (prev, curr), causes in TRANSITION_ARCS.items()
])


@CacheTransitionCoverage
def sample_transition(prev, curr, cause):
    pass


# System
class _HitCounts(dict):
    """Cross bin -> hits, which also counts the bins that have reached at_least."""

    def __init__(self, hits, at_least):
        super().__init__(hits)
        self.at_least = at_least
        self.covered = sum(1 for count in hits.values() if count >= at_least)

    def __setitem__(self, cross_bin, count):
        if count == self.at_least:  # a sample raises a count by one, so this is once
            self.covered += 1
        super().__setitem__(cross_bin, count)


class CountedCross(CoverCross):
    """CoverCross with a running count of its covered bins.

    CoverCross recounts every bin twice per sample. system.program_cross has
    len(INST_KINDS) ** ICACHE_SIZE bins (20,736), which made that about 10 ms per
    sampled program and most of the runtime of system.test_all_programs.
    """

    def __init__(self, name, *args, **kwargs):
        created = name not in coverage_db
        super().__init__(name, *args, **kwargs)
        if created:
            self._hits = _HitCounts(self._hits, self._at_least)

    @property
    def coverage(self):
        return self._weight * self._hits.covered


SystemCoverage = coverage_section(                                              # 5.4
    # One point per instruction cache slot, crossed over the slots: a bin of the
    # cross is one whole program. Any core running a program covers it.
    *[CoverPoint(f"system.program_slot{k}",
                 xf=lambda program, k=k: inst_kind(program[k]), bins=INST_KINDS)
      for k in range(ICACHE_SIZE)],
    CountedCross("system.program_cross",
               items=[f"system.program_slot{k}" for k in range(ICACHE_SIZE)]),
)


@SystemCoverage
def sample_program(program):
    """Once per core per run; program is the tuple of loaded instructions."""


@_assertion("system.one_cache_holds_exclusive")                                 # 5.1
def assert_one_cache_holds_exclusive(ok, exercised):
    pass


@_assertion("system.one_cache_holds_owner")                                     # 5.2
def assert_one_cache_holds_owner(ok, exercised):
    pass


@_assertion("system.one_cache_holds_modified")                                  # 5.5
def assert_one_cache_holds_modified(ok, exercised):
    pass


@_assertion("system.modified_excludes_other_copies")                            # 5.6
def assert_modified_excludes_other_copies(ok, exercised):
    pass


# Spreadsheet section -> (title, coverage item). None: not in this file, see the
# module docstring.
REQUIREMENTS = {
    "1.1": ("decoder_start_pulse", "decoder.decoder_start_pulse"),
    "1.2": ("inst_valid_on_icache_load", None),
    "1.3": ("all_commands_tested", "decoder.command_type"),
    "1.4": ("all_states_tested", None),
    "2.1": ("resp_valid_when_done", None),
    "2.2": ("snoop_valid_when_grant", "bus.snoop_valid_when_grant"),
    "2.3": ("snoop_req_valid_when_snoop_valid", None),
    "2.4": ("only_one_done_valid", "bus.only_one_done_valid"),
    "3.1": ("req_valid_until_done", "core.req_valid_until_done"),
    "3.2": ("req_valid_when_req", None),
    "3.3": ("local_inst_valid_when_inst_valid", None),
    "3.4": ("transaction_types_covered", "core.req_type"),
    "4.1": ("all_protocols_tested", "cache_ctrl.protocol"),
    "4.2": ("all_cache_req_types_tested", "cache_ctrl.req_hit_cross"),
    **{
        f"4.{3 + n}": (f"{STATE_NAMES[prev]}->{STATE_NAMES[curr]}", transition_name(prev, curr))
        for n, (prev, curr) in enumerate(TRANSITION_ARCS)
    },
    "5.1": ("one_cache_holds_exclusive", "system.one_cache_holds_exclusive"),
    "5.2": ("one_cache_holds_owner", "system.one_cache_holds_owner"),
    "5.3": ("all_cores_req_serviced", "system.cores_granted"),
    "5.4": ("all_programs_tested", "system.program_cross"),
    "5.5": ("one_cache_holds_modified", "system.one_cache_holds_modified"),
    "5.6": ("modified_excludes_other_copies", "system.modified_excludes_other_copies"),
}


# ---- Model ----
@dataclass
class Snapshot:
    """The design during one clock cycle: registers as they are in that cycle and
    the combinational signals derived from them. Per-core flags are bit vectors
    with core i in bit i."""
    state: int = LOAD                         # decoder state
    ui_in: int = 0
    start: int = 0                            # dec_if.start
    grant: int = 0                            # bus grants a request this cycle
    grant_idx: int = 0                        # core granted
    req: int = 0                              # bus_if.req
    done: int = 0                             # bus_if.done
    snoop_valid: int = 0                      # bus_if.snoop_valid
    bus_type: int = RD                        # transaction on the bus (= snoop_type)
    bus_addr: int = 0                         # (= snoop_addr)
    local_valid: int = 0                      # exec_if.local_valid
    inst_done: int = 0                        # exec_if.inst_done
    local_inst: Tuple[int, ...] = (0,) * N_CORES
    lines: Tuple[Tuple[int, ...], ...] = ((0,) * DCACHE_SIZE,) * N_CORES
    programs: Optional[Tuple[Tuple[int, ...], ...]] = None   # icaches; first RUN cycle only


class Findings:
    """What the models report besides coverage. One instance is shared by the
    models of a monitor."""

    def __init__(self, log=None):
        self.log = log
        self.failures = []          # assertion violations, as messages
        self.unexpected_arcs = []   # (core, prev, curr, cause) not in TRANSITION_ARCS

    def check(self, recorder, section, ok, exercised, detail):
        """Record one evaluation of an assertion; detail() is only called on failure."""
        recorder(bool(ok), bool(exercised))
        if not ok:
            self.failures.append(f"{section} {REQUIREMENTS[section][0]}: {detail()}")


class DecoderModel:
    """1.1 and 1.3."""

    def __init__(self, findings=None):
        self.findings = findings or Findings()
        self.reset()

    def reset(self):
        self._prev_start = 0

    def step(self, state, ui_in, start):
        cmd_valid = state == LOAD and bool(ui_in & 1)
        cmd = (ui_in >> 1) & 0b11
        if cmd_valid:
            sample_decoder_command(cmd)                                          # 1.3
        start_expected = cmd_valid and cmd == CMD_START
        prev_start = self._prev_start
        self.findings.check(
            assert_decoder_start_pulse, "1.1",
            start_pulse_ok(start, start_expected, prev_start), start_expected,
            lambda: f"start={start:0{N_CORES}b}, CMD_START on pins={start_expected}, "
                    f"start in previous cycle={prev_start:0{N_CORES}b}")
        self._prev_start = start


class BusModel:
    """2.2, 2.4 and 5.3."""

    def __init__(self, findings=None):
        self.findings = findings or Findings()

    def reset(self):
        pass

    def step(self, grant, grant_idx, done, snoop_valid):
        self.findings.check(
            assert_snoop_valid_when_grant, "2.2",
            snoop_valid_ok(snoop_valid, grant, grant_idx), grant,
            lambda: f"snoop_valid={snoop_valid:0{N_CORES}b}, grant={grant}, "
                    f"granted core={grant_idx}")
        self.findings.check(
            assert_only_one_done_valid, "2.4", done_onehot_ok(done), done,
            lambda: f"done={done:0{N_CORES}b}")
        if grant:
            sample_core_granted(grant_idx)                                       # 5.3


class CoreModel:
    """3.1 and 3.4, for the bus requests of one core."""

    def __init__(self, findings=None, core=0):
        self.findings = findings or Findings()
        self.core = core
        self.reset()

    def reset(self):
        self._prev_req = self._prev_done = 0

    def step(self, req, done, req_type):
        if self._prev_req:
            self.findings.check(
                assert_req_valid_until_done, "3.1",
                req_held_ok(1, self._prev_done, req), self._prev_done,
                lambda: f"core {self.core} dropped req before done")
        if req and done:
            sample_core_req_type(req_type)                                       # 3.4
        self._prev_req, self._prev_done = req, done


class CacheCtrlModel:
    """4.2 and 4.3 - 4.23 for one cache; also 4.1 when step() is given the protocol."""

    def __init__(self, findings=None, core=0):
        self.findings = findings or Findings()
        self.core = core
        self.reset()

    def reset(self):
        self._instr = None    # instruction in flight: (idx, state at start, cause)
        self._pending = []    # arcs armed last cycle: (idx, state before, cause)

    def _record_arc(self, prev, curr, cause):
        if cause in TRANSITION_ARCS.get((prev, curr), ()):
            sample_transition(prev, curr, cause)
            return
        self.findings.unexpected_arcs.append((self.core, prev, curr, cause))
        if self.findings.log is not None:
            self.findings.log.warning(
                "core %d: transition %s->%s by %s is not in TRANSITION_ARCS", self.core,
                STATE_NAMES.get(prev, bin(prev)), STATE_NAMES.get(curr, bin(curr)), cause)

    def step(self, local_valid, local_inst, inst_done, snooped, snoop_type, snoop_addr, lines,
             protocol=None):
        """lines: the lines of this cache. snooped: this cache snoops this cycle."""
        # Arcs armed in the previous cycle took effect at the clock edge in between.
        for idx, before, cause in self._pending:
            self._record_arc(before, line_state(lines[idx]), cause)
        self._pending = []

        if snooped:
            idx, tag = split_addr(snoop_addr)
            line = lines[idx]
            if line_hit(line, tag) and snoop_type in SNOOP_CAUSES:
                self._pending.append((idx, line_state(line), SNOOP_CAUSES[snoop_type]))
        # A snooped cache does not examine its instruction in that cycle.
        if local_valid and not snooped:
            if self._instr is None:
                addr, _, op = decode_inst(local_inst)
                idx, tag = split_addr(addr)
                line = lines[idx]
                hit = line_hit(line, tag)
                sample_cache_request("write" if op else "read", "hit" if hit else "miss")  # 4.2
                if protocol is not None:
                    sample_protocol(protocol)                                    # 4.1
                cause = ("write" if op else "read") + ("_hit" if hit else "_miss")
                self._instr = (idx, line_state(line), cause)
            if inst_done:
                self._pending.append(self._instr)
                self._instr = None


class CoverageModel:
    """The full chip: every module model, plus the system-level items (4.1 per run,
    5.1, 5.2, 5.4, 5.5, 5.6). Stepped with one Snapshot per clock."""

    def __init__(self, log=None):
        self.findings = Findings(log)
        self.failures = self.findings.failures
        self.unexpected_arcs = self.findings.unexpected_arcs
        self.decoder = DecoderModel(self.findings)
        self.bus = BusModel(self.findings)
        self.cores = [CoreModel(self.findings, core) for core in range(N_CORES)]
        self.caches = [CacheCtrlModel(self.findings, core) for core in range(N_CORES)]
        self.reset()

    def reset(self):
        """Forget everything that spans cycles. Call while the design is in reset."""
        for model in (self.decoder, self.bus, *self.cores, *self.caches):
            model.reset()
        self._prev_state = None
        self._checked_lines = None

    def step(self, s):
        self.decoder.step(s.state, s.ui_in, s.start)

        if self._prev_state == LOAD and s.state == RUN:                          # run begins
            sample_protocol((s.ui_in >> PROTOCOL_LSB) & 0b11)                    # 4.1
            for program in s.programs or ():
                sample_program(tuple(program))                                   # 5.4

        self.bus.step(s.grant, s.grant_idx, s.done, s.snoop_valid)

        for core in range(N_CORES):
            # bus_type is the request of the core being served, so it is this
            # core's req_type whenever its done is set.
            self.cores[core].step((s.req >> core) & 1, (s.done >> core) & 1, s.bus_type)
            self.caches[core].step(
                (s.local_valid >> core) & 1, s.local_inst[core], (s.inst_done >> core) & 1,
                (s.snoop_valid >> core) & 1, s.bus_type, s.bus_addr, s.lines[core])

        if s.lines != self._checked_lines:
            self._checked_lines = s.lines
            max_e, max_o, max_m, m_shared = line_invariants(s.lines)
            check = self.findings.check
            check(assert_one_cache_holds_exclusive, "5.1", max_e <= 1, max_e == 1,
                  lambda: f"{max_e} cores hold the same line in E, lines={s.lines}")
            check(assert_one_cache_holds_owner, "5.2", max_o <= 1, max_o == 1,
                  lambda: f"{max_o} cores hold the same line in O, lines={s.lines}")
            check(assert_one_cache_holds_modified, "5.5", max_m <= 1, max_m == 1,
                  lambda: f"{max_m} cores hold the same line in M, lines={s.lines}")
            check(assert_modified_excludes_other_copies, "5.6", not m_shared, max_m >= 1,
                  lambda: f"a line in M has another valid copy, lines={s.lines}")

        self._prev_state = s.state


# ---- cocotb monitor: full chip ----
class CoverageMonitor:
    """Feeds a CoverageModel from the full-chip RTL, one Snapshot per falling clock
    edge. Stimulus must change the inputs on rising edges, so that what is sampled
    at the falling edge is what the next rising edge acts on.

    An assertion violation raises in the monitor task, which fails the running test.
    """

    def __init__(self, tb):
        chip = tb.dut
        self._log = cocotb.log
        self._clk = chip.clk
        self._rst_n = chip.rst_n
        self._ui_in = chip.ui_in
        self._state = chip.u_decoder.current_state
        self._start = [chip[f"dec[{i}]"].start for i in range(N_CORES)]
        bus = chip.u_bus
        self._grant = bus.grant
        self._grant_idx = bus.grant_idx
        self._req = bus.reqs                        # = bus_if[i].req
        self._done = bus.done_by_core               # = bus_if[i].done
        self._snoop_valid = bus.snoop_valid_by_core # = bus_if[i].snoop_valid
        self._bus_type = bus.req_type               # = bus_if[i].snoop_type
        self._bus_addr = bus.req_addr               # = bus_if[i].snoop_addr
        cores = [chip.genblk1[i].u_core for i in range(N_CORES)]
        self._local_valid = [c.exec.local_valid for c in cores]
        self._local_inst = [c.exec.local_inst for c in cores]
        self._inst_done = [c.exec.inst_done for c in cores]
        self._icache = [[c.icache[k] for k in range(ICACHE_SIZE)] for c in cores]
        self._cache = [[c.i_cache_ctrl.cache[k] for k in range(DCACHE_SIZE)] for c in cores]
        self._check_parameters(cores[0])

        self.model = CoverageModel(log=self._log)
        self._last = None
        self._task = None

    def _check_parameters(self, core):
        actual = {
            "N_CORES": len(self._req),
            "ICACHE_SIZE": len(core.icache),
            "DCACHE_SIZE": len(core.i_cache_ctrl.cache),
            "ADDR_WIDTH": len(self._bus_addr),
            "INST_WIDTH": len(self._local_inst[0]),
            "LINE_WIDTH": len(self._cache[0][0]),
        }
        expected = {name: globals()[name] for name in actual}
        if actual != expected:
            raise ValueError(
                f"coverage.py parameters do not match the design: design has {actual}, "
                f"coverage.py has {expected}. Update the constants at the top of coverage.py.")

    def start(self):
        self._task = cocotb.start_soon(self._run())
        return self

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    @staticmethod
    def _bits(handles):
        value = 0
        for i, handle in enumerate(handles):
            value |= int(handle.value) << i
        return value

    def _snapshot(self):
        state = int(self._state.value)
        last = self._last
        if state == RUN or last is None or last.state == RUN:
            # The caches and the instruction stream only move during RUN.
            lines = tuple(tuple(int(line.value) for line in core) for core in self._cache)
            local_valid = self._bits(self._local_valid)
            inst_done = self._bits(self._inst_done)
            local_inst = tuple(int(inst.value) for inst in self._local_inst)
        else:
            lines, local_valid, inst_done, local_inst = last.lines, 0, 0, last.local_inst
        programs = None
        if state == RUN and last is not None and last.state == LOAD:
            programs = tuple(tuple(int(inst.value) for inst in core) for core in self._icache)
        return Snapshot(
            state=state,
            ui_in=int(self._ui_in.value),
            start=self._bits(self._start),
            grant=int(self._grant.value),
            grant_idx=int(self._grant_idx.value),
            req=int(self._req.value),
            done=int(self._done.value),
            snoop_valid=int(self._snoop_valid.value),
            bus_type=int(self._bus_type.value),
            bus_addr=int(self._bus_addr.value),
            local_valid=local_valid,
            inst_done=inst_done,
            local_inst=local_inst,
            lines=lines,
            programs=programs,
        )

    async def _run(self):
        while True:
            await FallingEdge(self._clk)
            await ReadOnly()
            if not int(self._rst_n.value):
                self.model.reset()
                self._last = None
                continue
            self._last = self._snapshot()
            self.model.step(self._last)
            if self.model.failures:
                raise AssertionError(
                    f"assertion failed at {get_sim_time('ns')} ns: " + "; ".join(self.model.failures))


# ---- cocotb monitors: module testbenches ----
class UnitMonitor:
    """Base of the monitors for the module testbenches (test/*_tb.sv).

    Those tests drive the clock by hand and set the inputs while it is low, so
    there is no edge at which a background task could sample. Instead sample()
    is called once per clock cycle, after the inputs have settled and before the
    rising edge: tb_utils.tick() does that. A violated assertion raises there.
    """

    def __init__(self, tb):
        self._rst_n = tb.rst_n
        self.findings = Findings(log=cocotb.log)
        self.model = None   # set by the subclass

    def _step(self):
        raise NotImplementedError

    def sample(self):
        if not int(self._rst_n.value):
            self.model.reset()
            return
        self._step()
        if self.findings.failures:
            raise AssertionError(
                f"assertion failed at {get_sim_time('ns')} ns: " + "; ".join(self.findings.failures))


class DecoderUnitMonitor(UnitMonitor):
    """decoder_tb: 1.1, 1.3."""

    def __init__(self, tb):
        super().__init__(tb)
        self._state = tb.dut.current_state
        self._ui_in = tb.ui_in
        self._start = tb.dec_start
        self.model = DecoderModel(self.findings)

    def _step(self):
        self.model.step(int(self._state.value), int(self._ui_in.value), int(self._start.value))


class BusUnitMonitor(UnitMonitor):
    """bus_tb: 2.2, 2.4, 5.3."""

    def __init__(self, tb):
        super().__init__(tb)
        self._grant = tb.dut.grant
        self._grant_idx = tb.dut.grant_idx
        self._done = tb.done
        self._snoop_valid = tb.snoop_valid
        self.model = BusModel(self.findings)

    def _step(self):
        self.model.step(int(self._grant.value), int(self._grant_idx.value),
                        int(self._done.value), int(self._snoop_valid.value))


class CoreUnitMonitor(UnitMonitor):
    """core_tb: 3.1, 3.4."""

    def __init__(self, tb):
        super().__init__(tb)
        self._req = tb.bus_req
        self._done = tb.bus_done
        self._req_type = tb.bus_req_type
        self.model = CoreModel(self.findings)

    def _step(self):
        self.model.step(int(self._req.value), int(self._done.value), int(self._req_type.value))


class CacheCtrlUnitMonitor(UnitMonitor):
    """cache_ctrl_tb: 4.1 (per instruction), 4.2, 4.3 - 4.23.

    The testbench can drive what the system never does (for example change the
    protocol mid-run), so arcs outside TRANSITION_ARCS are possible here. They
    are logged and collected in findings.unexpected_arcs, not failed.
    """

    def __init__(self, tb):
        super().__init__(tb)
        self._local_valid = tb.local_valid
        self._local = (tb.local_addr, tb.local_data, tb.local_op)
        self._inst_done = tb.inst_done
        self._snoop_valid = tb.bus_snoop_valid
        self._snoop_type = tb.bus_snoop_type
        self._snoop_addr = tb.bus_snoop_addr
        self._lines = [getattr(tb, f"line{k}") for k in range(DCACHE_SIZE)]
        self._protocol = tb.protocol
        self.model = CacheCtrlModel(self.findings)

    def _step(self):
        addr, data, op = (int(handle.value) for handle in self._local)
        self.model.step(
            int(self._local_valid.value), (addr << (DATA_WIDTH + 1)) | (data << 1) | op,
            int(self._inst_done.value), int(self._snoop_valid.value),
            int(self._snoop_type.value), int(self._snoop_addr.value),
            tuple(int(line.value) for line in self._lines), int(self._protocol.value))


def coverage_supported():
    """The monitor needs the hierarchy of the SystemVerilog sources. The gate-level
    netlist and the sv2v-generated project.v do not have it."""
    return os.environ.get("GATES") != "yes" and os.environ.get("SV2V") != "1"


def start_coverage(tb):
    """Attach a CoverageMonitor to the full chip (tb.dut) and start it. Returns the
    monitor, or None on builds where it cannot run."""
    if not coverage_supported():
        cocotb.log.info("functional coverage is not collected on gate-level or sv2v builds")
        return None
    return CoverageMonitor(tb).start()


def unit_monitor(monitor_class, tb):
    """Monitor for a module testbench, e.g. unit_monitor(BusUnitMonitor, dut.bus_tb).
    Returns None on builds where coverage cannot run; tb_utils.tick() accepts that."""
    return monitor_class(tb) if coverage_supported() else None


# ---- Reporting ----
def requirement_coverage():
    """Spreadsheet section -> (title, covered bins, total bins); the two numbers are
    None for requirements that are not implemented in this file."""
    result = {}
    for section, (title, item) in REQUIREMENTS.items():
        if item is None:
            result[section] = (title, None, None)
        else:
            result[section] = (title, coverage_db[item].coverage, coverage_db[item].size)
    return result


def report_coverage(logger=print, filename="functional_coverage.xml"):
    """Log coverage per test requirement and export the whole database to XML.
    The database accumulates over every test of one simulation run."""
    logger("Functional coverage by test requirement:")
    for section, (title, covered, size) in requirement_coverage().items():
        if size is None:
            logger(f"  {section:<5}{title:<34}not in coverage.py (deferred or code coverage)")
            continue
        note = ""
        item = coverage_db[REQUIREMENTS[section][1]]
        if isinstance(item, CoverCheck):
            hits = item.detailed_coverage
            note = f"  PASS={hits['PASS']} FAIL={hits['FAIL']}"
        logger(f"  {section:<5}{title:<34}{covered:>6}/{size:<6}{100 * covered / size:6.1f}%{note}")
    if filename:
        coverage_db.export_to_xml(filename=filename)
