"""System-level tests: whole programs on the full chip, driven over the pins.

test_directed_programs runs the hand-written programs in DIRECTED_PROGRAMS under
every protocol and checks the cycle count of each run against the value the spec
gives (docs/bus.md, "Transaction cost"). After each run it reads the data caches
back over the pins and logs them.

test_all_programs is test requirement 5.4 (all_programs_tested). A program is
the content of one instruction cache: ICACHE_SIZE instructions, each one of the
cov.INST_KINDS that the decoder can load. Every core runs every program:

    runs = len(INST_KINDS) ** ICACHE_SIZE        (12^4 = 20,736 by default)

Each run is reset -> load -> start -> wait for resp_valid, because the decoder
cannot leave READ without a reset.

What is exhaustive and what is not:
- Exhaustive: the programs of each core. Core c runs order[c][run], and each
  order[c] is a permutation of all programs.
- Sampled: which programs run together, the initial memory and the protocol.
  The joint space is runs^N_CORES * 2^(MEM_SIZE * DATA_WIDTH) * 3 (about 1e19 by
  default). The permutations are independent shuffles, memory is random and the
  protocol rotates with the run number.

The stimulus is seeded by cocotb, so each regression explores new program
pairings. A failing run logs its programs, memory and protocol; the whole
sequence reproduces with COCOTB_RANDOM_SEED=<the seed cocotb logs at startup>.

SYSTEM_RUNS=<n> limits the test to the first n runs, a random sample of the
programs. Builds without the functional coverage monitor (gate-level, sv2v)
default to SAMPLE_RUNS: without the monitor a run only checks that the chip
finishes, and there is no coverage to close.
"""

import itertools
import os
import random
import time

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge
from cocotb_coverage.coverage import coverage_db

import coverage as cov  # test/coverage.py: functional coverage model and assertions
from test import RD_OP, WR_OP, run_programs

PROTOCOLS = (cov.MSI, cov.MESI, cov.MOESI)
PROTOCOL_NAMES = {cov.MSI: "MSI", cov.MESI: "MESI", cov.MOESI: "MOESI"}
SAMPLE_RUNS = 500     # default number of runs on builds without coverage
RESET_CYCLES = 2
RD_NEXT_BIT = 0       # rd_next = ui_in[0] during READ (docs/encodings.md)
LOG_EVERY = 2000      # runs between progress messages


def all_instructions():
    """Every instruction the decoder can load, as (op, addr, data), in the order
    of cov.INST_KINDS. Reads carry no data: the decoder zeroes it."""
    reads = [(RD_OP, addr, 0) for addr in range(cov.MEM_SIZE)]
    writes = [(WR_OP, addr, data)
              for addr in range(cov.MEM_SIZE) for data in range(1 << cov.DATA_WIDTH)]
    return reads + writes


def all_programs():
    """Every program: one tuple of ICACHE_SIZE instructions per bin of 5.4."""
    return list(itertools.product(all_instructions(), repeat=cov.ICACHE_SIZE))


def program_orders(programs, rng):
    """One independent shuffle of the programs per core. Run i loads
    order[core][i], so every core runs every program exactly once."""
    orders = []
    for _ in range(cov.N_CORES):
        order = list(programs)
        rng.shuffle(order)
        orders.append(order)
    return orders


def random_memory(rng):
    """Initial memory contents. Words left out keep their reset value, 0."""
    words = {addr: rng.getrandbits(cov.DATA_WIDTH) for addr in range(cov.MEM_SIZE)}
    return {addr: data for addr, data in words.items() if data}


# ---- Directed programs ----
# Columns are cores, rows are instruction slots: Rd<a> reads address a, Wr<a>
# writes it. Every write writes DIRECTED_WR_DATA and memory starts at 0; neither
# affects the timing.
#
# The expected cycle counts follow from docs/bus.md ("Transaction cost") with
# MEM_LATENCY = 2: an INV or a RD served by an owner takes 1 cycle, a WB or a RD
# served by memory takes 3, and a hit takes 1 cycle off the bus. The bus runs one
# transaction at a time, so a run costs the sum of its transactions, plus the hits
# that are left after the last transaction, plus the one RUN cycle in which the
# decoder sees every core done (docs/decoder.md).
DIRECTED_WR_DATA = 1
DIRECTED_PROGRAMS = [
    # Every write misses, because another core's INV took the line in between.
    # 16 INV = 16, + 1.
    ("high write traffic", """
        Wr0 Wr0 Wr0 Wr0
        Wr0 Wr0 Wr0 Wr0
        Wr0 Wr0 Wr0 Wr0
        Wr0 Wr0 Wr0 Wr0
     """, {cov.MSI: 17, cov.MESI: 17, cov.MOESI: 17}),
    # No address is shared. 4 RD from memory = 12, the last one by core 3.
    # MSI: the read leaves S, so each core's first write is an INV: + 4, then
    # core 3's two write hits, + 1 = 19.
    # MESI, MOESI: the read leaves E, so every write is a hit: core 3's three
    # write hits, + 1 = 16.
    ("exclusive writes", """
        Rd0 Rd1 Rd2 Rd3
        Wr0 Wr1 Wr2 Wr3
        Wr0 Wr1 Wr2 Wr3
        Wr0 Wr1 Wr2 Wr3
     """, {cov.MSI: 19, cov.MESI: 16, cov.MOESI: 16}),
    # No line is ever dirty and no read hits. 16 RD from memory = 48, + 1.
    ("100% miss rate", """
        Rd0 Rd1 Rd2 Rd3
        Rd1 Rd2 Rd3 Rd0
        Rd2 Rd3 Rd0 Rd1
        Rd3 Rd0 Rd1 Rd2
     """, {cov.MSI: 49, cov.MESI: 49, cov.MOESI: 49}),
    # 4 INV = 4, then 12 read misses. Each core reads in the line slot it did not
    # write, so the line it wrote is never replaced and no WB is needed.
    # MSI, MESI: the first read of each address flushes the MODIFIED copy to
    # memory and leaves it SHARED, so every read is served by memory:
    # 12 RD = 36, + 1 = 41.
    # MOESI: the writer keeps its line in O and serves every read of it:
    # 12 RD from the owner = 12, + 1 = 17.
    ("owner reads", """
        Wr0 Wr1 Wr2 Wr3
        Rd1 Rd2 Rd3 Rd0
        Rd3 Rd0 Rd1 Rd2
        Rd1 Rd2 Rd3 Rd0
     """, {cov.MSI: 41, cov.MESI: 41, cov.MOESI: 17}),
    # Each core alternates between two addresses of the same line slot, so no
    # read hits. No line is ever dirty. 16 RD from memory = 48, + 1.
    ("read conflict misses", """
        Rd0 Rd1 Rd2 Rd3
        Rd2 Rd3 Rd0 Rd1
        Rd0 Rd1 Rd2 Rd3
        Rd2 Rd3 Rd0 Rd1
     """, {cov.MSI: 49, cov.MESI: 49, cov.MOESI: 49}),
    # As above with writes: every write after a core's first replaces its own
    # MODIFIED line. 16 INV = 16, 12 WB = 36, + 1.
    ("write conflict misses", """
        Wr0 Wr1 Wr2 Wr3
        Wr2 Wr3 Wr0 Wr1
        Wr0 Wr1 Wr2 Wr3
        Wr2 Wr3 Wr0 Wr1
     """, {cov.MSI: 53, cov.MESI: 53, cov.MOESI: 53}),
]


def parse_program_grid(grid):
    """Turn a grid of Rd<a>/Wr<a> (columns = cores, rows = instruction slots) into
    one program per core, as run_programs takes them."""
    rows = [line.split() for line in grid.strip().splitlines()]
    assert len(rows) == cov.ICACHE_SIZE and all(len(row) == cov.N_CORES for row in rows), (
        f"expected {cov.ICACHE_SIZE} rows of {cov.N_CORES} instructions, got {rows}")

    def instruction(text):
        kind, addr = text[:2], int(text[2:])
        assert kind in ("Rd", "Wr") and addr < cov.MEM_SIZE, f"bad instruction {text!r}"
        return (WR_OP, addr, DIRECTED_WR_DATA) if kind == "Wr" else (RD_OP, addr, 0)

    return [tuple(instruction(row[core]) for row in rows) for core in range(cov.N_CORES)]


def describe(program):
    return " ".join(f"W{addr}={data}" if op == WR_OP else f"R{addr}"
                    for op, addr, data in program)


def run_count(total, monitor):
    """Number of runs: SYSTEM_RUNS if set, else everything when the coverage
    monitor is attached and SAMPLE_RUNS when it is not."""
    requested = os.environ.get("SYSTEM_RUNS")
    if requested:
        return max(1, min(int(requested), total))
    return total if monitor is not None else min(SAMPLE_RUNS, total)


async def short_reset(dut):
    """Back to LOAD with empty caches. Inputs change just after a rising edge, as
    the coverage monitor requires."""
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, RESET_CYCLES)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def checked_run(dut, monitor, label, loaded, memory, protocol):
    """Reset, run the loaded programs and return the cycle count. Fails on a state
    transition outside the protocol, and logs the stimulus of a failing run."""
    await short_reset(dut)
    passed = False
    try:
        cycles = await run_programs(dut, loaded, memory, protocol)
        if monitor is not None:
            arcs = monitor.model.unexpected_arcs
            assert not arcs, f"state transitions outside the protocol: {arcs}"
        passed = True
    finally:
        # Also reached when the monitor task fails an assertion (5.1, 5.2,
        # 5.5, 5.6, ...): cocotb then cancels this task inside run_programs.
        if not passed:
            cocotb.log.error("%s failed: protocol %s, memory %s",
                             label, PROTOCOL_NAMES[protocol], memory)
            for core, program in enumerate(loaded):
                cocotb.log.error("  core %d: %s", core, describe(program))
    return cycles


async def read_cache_lines(dut):
    """Read every data cache line back over the pins (docs/decoder.md, "MCU
    protocol", step 6). Call just after run_programs, before the next reset.
    Returns the raw line_t values, lines[core][index].

    rd_next is raised just after a rising edge and each line is sampled at the
    falling edge, half a cycle before the readback position advances.
    """
    held = int(dut.ui_in.value)  # the protocol, still on the pins
    dut.ui_in.value = held | (1 << RD_NEXT_BIT)
    words = []
    for _ in range(cov.N_CORES * cov.DCACHE_SIZE):
        await FallingEdge(dut.clk)
        words.append(int(dut.uio_out.value) & ((1 << cov.LINE_WIDTH) - 1))
        await RisingEdge(dut.clk)
    dut.ui_in.value = held  # the position has wrapped back to core 0, line 0
    return [words[core * cov.DCACHE_SIZE:(core + 1) * cov.DCACHE_SIZE]
            for core in range(cov.N_CORES)]


def describe_line(line, idx):
    """A cache line as <state><addr>=<data>, e.g. 'M2=1', or '-' when INVALID."""
    state = cov.line_state(line)
    if state == cov.I:
        return "-"
    addr = (cov.line_tag(line) << cov.IDX_WIDTH) | idx
    data = (line >> 3) & ((1 << cov.DATA_WIDTH) - 1)
    return f"{cov.STATE_NAMES.get(state, '?')}{addr}={data}"


def describe_caches(lines):
    """One column per core, each listing its lines in index order."""
    return "  ".join(
        f"core {core}: " + " ".join(f"{describe_line(line, idx):<4}"
                                    for idx, line in enumerate(core_lines))
        for core, core_lines in enumerate(lines))


@cocotb.test()
async def test_directed_programs(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    monitor = cov.start_coverage(dut)

    wrong = []
    for name, grid, expected in DIRECTED_PROGRAMS:
        loaded = parse_program_grid(grid)
        cocotb.log.info("%s", name)
        for protocol in PROTOCOLS:
            cycles = await checked_run(
                dut, monitor, f"directed program '{name}'", loaded, {}, protocol)
            lines = await read_cache_lines(dut)
            if cycles != expected[protocol]:
                wrong.append(f"{name}, {PROTOCOL_NAMES[protocol]}: {cycles} cycles, "
                             f"expected {expected[protocol]}")
            cocotb.log.info("  %-5s %3d cycles   %s",
                            PROTOCOL_NAMES[protocol], cycles, describe_caches(lines))
    await ClockCycles(dut.clk, 2)
    assert not wrong, "cycle counts differ from the spec:\n  " + "\n  ".join(wrong)


@cocotb.test()
async def test_all_programs(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    monitor = cov.start_coverage(dut)

    rng = random.Random(cocotb.RANDOM_SEED)  # per test, derived from COCOTB_RANDOM_SEED
    programs = all_programs()
    orders = program_orders(programs, rng)
    runs = run_count(len(programs), monitor)
    cocotb.log.info("%d of %d runs", runs, len(programs))

    started = time.monotonic()
    longest = 0
    for run in range(runs):
        loaded = [order[run] for order in orders]
        memory = random_memory(rng)
        protocol = PROTOCOLS[run % len(PROTOCOLS)]

        cycles = await checked_run(dut, monitor, f"run {run}", loaded, memory, protocol)
        longest = max(longest, cycles)

        if (run + 1) % LOG_EVERY == 0:
            cocotb.log.info("%d/%d runs, %.0f s", run + 1, runs, time.monotonic() - started)

    cocotb.log.info("%d runs in %.0f s, longest run %d cycles",
                    runs, time.monotonic() - started, longest)
    await ClockCycles(dut.clk, 2)

    if monitor is None:  # gate-level or sv2v build: the runs above are the test
        return
    cross = coverage_db["system.program_cross"]
    cocotb.log.info("5.4 all_programs_tested: %d/%d programs", cross.coverage, cross.size)
    if runs == len(programs):
        missed = [kinds for kinds, hits in cross.detailed_coverage.items() if not hits]
        assert not missed, f"{len(missed)} programs never ran, e.g. {missed[:3]}"
