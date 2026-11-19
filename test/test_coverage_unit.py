"""Unit tests for the coverage model in coverage.py. No simulator needed:

    python3 -m pytest test_coverage_unit.py

coverage.py is loaded by path because the name `coverage` is also a PyPI package
(pulled in by pytest-cov), which would otherwise win the import.
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "cce_coverage", Path(__file__).with_name("coverage.py"))
cov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cov)

I, S, E, O, M = cov.I, cov.S, cov.E, cov.O, cov.M
RUN = cov.RUN
NO_LINES = ((0, 0),) * cov.N_CORES


def line(tag, state, data=0):
    return (tag << (cov.DATA_WIDTH + 3)) | (data << 3) | state


def inst(addr, op, data=0):
    return (addr << (cov.DATA_WIDTH + 1)) | (data << 1) | op


def lines_with(**cores):
    """lines_with(c0=(line0, line1), c2=...) -> lines of all cores, others invalid."""
    out = [(0, 0)] * cov.N_CORES
    for name, value in cores.items():
        out[int(name[1:])] = value
    return tuple(out)


def hits(item, label):
    return cov.coverage_db[item].detailed_coverage[label]


def arc_hits(prev, curr, cause):
    return hits(cov.transition_name(prev, curr), cause)


def run_snapshot(**fields):
    return cov.Snapshot(state=RUN, **fields)


def failed_sections(model):
    return [message.split()[0] for message in model.failures]


# ---- helpers ----
def test_decoding_helpers():
    assert cov.split_addr(0b11) == (1, 1)
    assert cov.split_addr(0b10) == (0, 1)
    assert cov.decode_inst(inst(3, 1, 1)) == (3, 1, 1)
    assert cov.line_hit(line(1, S), tag=1)
    assert not cov.line_hit(line(1, S), tag=0)
    assert not cov.line_hit(line(1, I), tag=1)
    assert cov.line_state(line(1, M, data=1)) == M


def test_inst_kind_matches_the_twelve_loadable_instructions():
    kinds = {cov.inst_kind(i) for i in range(1 << cov.INST_WIDTH)} - {None}
    assert kinds == set(cov.INST_KINDS)
    assert cov.inst_kind(inst(2, 0)) == "R2"
    assert cov.inst_kind(inst(1, 1, 1)) == "W1=1"
    assert cov.inst_kind(inst(2, 0, data=1)) is None  # the decoder cannot load this


def test_requirements_cover_every_spreadsheet_row():
    assert len(cov.REQUIREMENTS) == 41
    assert cov.REQUIREMENTS["4.3"][0] == "I->E"
    assert cov.REQUIREMENTS["4.22"][0] == "O->E"
    assert cov.REQUIREMENTS["4.23"][0] == "E->I"
    for title, item in cov.REQUIREMENTS.values():
        assert item is None or item in cov.coverage_db, title
    assert cov.coverage_db["system.program_cross"].size == 12 ** cov.ICACHE_SIZE


# ---- assertion predicates ----
def test_start_pulse_ok():
    assert cov.start_pulse_ok(0b1111, True, 0)
    assert cov.start_pulse_ok(0, False, 0b1111)
    assert not cov.start_pulse_ok(0b0111, True, 0)       # one core missed the pulse
    assert not cov.start_pulse_ok(0b0001, False, 0)      # start without CMD_START
    assert not cov.start_pulse_ok(0, True, 0)            # CMD_START without start
    assert not cov.start_pulse_ok(0b1111, True, 0b1111)  # two cycles long


def test_snoop_valid_ok():
    assert cov.snoop_valid_ok(0b1101, grant=1, grant_idx=1)
    assert cov.snoop_valid_ok(0, grant=0, grant_idx=2)
    assert not cov.snoop_valid_ok(0b1111, grant=1, grant_idx=1)  # granted core snooped
    assert not cov.snoop_valid_ok(0b0101, grant=1, grant_idx=1)  # a core missed the snoop
    assert not cov.snoop_valid_ok(0b0100, grant=0, grant_idx=0)  # snoop without a grant
    assert not cov.snoop_valid_ok(0, grant=1, grant_idx=0)       # one cycle late


def test_done_onehot_ok():
    assert cov.done_onehot_ok(0)
    assert cov.done_onehot_ok(0b0100)
    assert not cov.done_onehot_ok(0b0101)


def test_req_held_ok():
    assert cov.req_held_ok(prev_req=1, prev_done=0, req=1)
    assert cov.req_held_ok(prev_req=1, prev_done=1, req=0)
    assert cov.req_held_ok(prev_req=0, prev_done=0, req=0)
    assert not cov.req_held_ok(prev_req=1, prev_done=0, req=0)


def test_line_invariants():
    # address 0 in E in one core; address 3 (tag 1, slot 1) shared by two cores
    lines = lines_with(c0=(line(0, E), line(1, S)), c1=(0, line(1, S)))
    assert cov.line_invariants(lines) == (1, 0, 0, False)
    # same slot, different tags: two different addresses, both may be M
    lines = lines_with(c0=(line(0, M), 0), c1=(line(1, M), 0))
    assert cov.line_invariants(lines) == (0, 0, 1, False)
    # O with S copies is legal
    lines = lines_with(c0=(line(0, O), 0), c1=(line(0, S), 0), c2=(line(0, S), 0))
    assert cov.line_invariants(lines) == (0, 1, 0, False)
    # violations
    assert cov.line_invariants(lines_with(c0=(line(0, E), 0), c3=(line(0, E), 0)))[0] == 2
    assert cov.line_invariants(lines_with(c0=(line(0, O), 0), c3=(line(0, O), 0)))[1] == 2
    assert cov.line_invariants(lines_with(c0=(line(0, M), 0), c3=(line(0, M), 0)))[2:] == (2, True)
    assert cov.line_invariants(lines_with(c0=(line(0, M), 0), c3=(line(0, S), 0)))[2:] == (1, True)


# ---- model: sampling ----
def test_commands_start_pulse_protocol_and_programs():
    model = cov.CoverageModel()
    before_cmd = hits("decoder.command_type", "CMD_LOAD_MEM")
    before_proto = hits("cache_ctrl.protocol", "MOESI")
    before_prog = cov.coverage_db["system.program_cross"].detailed_coverage[("R0", "W1=1", "R2", "R3")]

    model.step(cov.Snapshot(state=cov.LOAD, ui_in=1 | (cov.CMD_LOAD_MEM << 1)))
    model.step(cov.Snapshot(state=cov.LOAD, ui_in=cov.CMD_LOAD_MEM << 1))  # req_valid = 0
    start_word = 1 | (cov.CMD_START << 1) | (cov.MOESI << cov.PROTOCOL_LSB)
    model.step(cov.Snapshot(state=cov.LOAD, ui_in=start_word, start=cov.ALL_CORES))
    program = (inst(0, 0), inst(1, 1, 1), inst(2, 0), inst(3, 0))
    model.step(run_snapshot(ui_in=cov.MOESI << cov.PROTOCOL_LSB, programs=(program,)))
    model.step(run_snapshot(ui_in=cov.MOESI << cov.PROTOCOL_LSB))

    assert model.failures == []
    assert hits("decoder.command_type", "CMD_LOAD_MEM") == before_cmd + 1
    assert hits("cache_ctrl.protocol", "MOESI") == before_proto + 1  # once per run
    after_prog = cov.coverage_db["system.program_cross"].detailed_coverage[("R0", "W1=1", "R2", "R3")]
    assert after_prog == before_prog + 1


def test_core_is_sampled_at_grant_and_request_type_at_done():
    model = cov.CoverageModel()
    before = hits("core.req_type", "WB"), hits("system.cores_granted", 2)
    model.step(run_snapshot(grant=1, grant_idx=2, req=0b0100, bus_type=cov.WB,
                            snoop_valid=0b1011))
    assert (hits("core.req_type", "WB"), hits("system.cores_granted", 2)) == (before[0], before[1] + 1)
    model.step(run_snapshot(req=0b0100, bus_type=cov.WB))                 # memory latency
    model.step(run_snapshot(req=0b0100, bus_type=cov.WB, done=0b0100))
    assert model.failures == []
    assert (hits("core.req_type", "WB"), hits("system.cores_granted", 2)) == (before[0] + 1, before[1] + 1)


def test_local_arc_is_measured_from_first_examination_to_completion():
    """Read miss on a slot holding a different MODIFIED line: WB, then RD. One arc, M->E."""
    model = cov.CoverageModel()
    before = arc_hits(M, E, "read_miss")
    before_cross = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "miss")]
    victim = lines_with(c0=(line(1, M), 0))
    read0 = (inst(0, 0),) * cov.N_CORES

    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=victim, req=1))   # WB pending
    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=victim, req=1,
                            grant=1, done=0, snoop_valid=0b1110, bus_type=cov.WB, bus_addr=2))
    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=victim, req=1, done=1))
    evicted = NO_LINES
    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=evicted, req=1,
                            grant=1, snoop_valid=0b1110, bus_type=cov.RD, bus_addr=0))
    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=evicted, req=1,
                            done=1, inst_done=1))
    assert arc_hits(M, E, "read_miss") == before                  # not yet: resolved next cycle
    model.step(run_snapshot(lines=lines_with(c0=(line(0, E), 0))))

    assert model.failures == [] and model.unexpected_arcs == []
    assert arc_hits(M, E, "read_miss") == before + 1
    after_cross = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "miss")]
    assert after_cross == before_cross + 1                         # one instruction, sampled once


def test_snoop_arc_and_snooped_core_does_not_examine_its_instruction():
    model = cov.CoverageModel()
    before = arc_hits(E, I, "snoop_INV")
    before_hit = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "hit")]
    before_miss = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "miss")]
    holds_e = lines_with(c1=(line(0, E), 0))
    read0 = (inst(0, 0),) * cov.N_CORES

    # Core 1 would read-hit address 0, but in this cycle it snoops core 0's INV of it.
    model.step(run_snapshot(local_valid=0b10, local_inst=read0, lines=holds_e, req=0b01,
                            grant=1, grant_idx=0, done=0b01, snoop_valid=0b1110,
                            bus_type=cov.INV, bus_addr=0))
    model.step(run_snapshot(local_valid=0b10, local_inst=read0, lines=NO_LINES, req=0b10))

    assert model.failures == [] and model.unexpected_arcs == []
    assert arc_hits(E, I, "snoop_INV") == before + 1
    # The instruction was first examined after the snoop, as a miss.
    after_hit = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "hit")]
    after_miss = cov.coverage_db["cache_ctrl.req_hit_cross"].detailed_coverage[("read", "miss")]
    assert (after_hit, after_miss) == (before_hit, before_miss + 1)


def test_snoop_that_misses_the_cache_is_not_an_arc():
    model = cov.CoverageModel()
    model.step(run_snapshot(lines=lines_with(c1=(line(1, S), 0)), req=1, grant=1, done=1,
                            snoop_valid=0b1110, bus_type=cov.INV, bus_addr=0))
    model.step(run_snapshot(lines=lines_with(c1=(line(1, S), 0))))
    assert model.caches[1]._pending == [] and model.unexpected_arcs == []


def test_arc_outside_the_table_is_reported_not_sampled():
    model = cov.CoverageModel()
    write0 = (inst(0, 1),) * cov.N_CORES
    model.step(run_snapshot(local_valid=1, local_inst=write0, lines=NO_LINES, req=1,
                            grant=1, done=1, inst_done=1, snoop_valid=0b1110, bus_type=cov.INV))
    model.step(run_snapshot(lines=lines_with(c0=(line(0, O), 0))))  # a write miss must end in M
    assert model.unexpected_arcs == [(0, I, O, "write_miss")]


def test_reset_forgets_an_instruction_in_flight():
    model = cov.CoverageModel()
    read0 = (inst(0, 0),) * cov.N_CORES
    model.step(run_snapshot(local_valid=1, local_inst=read0, lines=NO_LINES, req=1))
    assert model.caches[0]._instr is not None
    model.reset()
    assert model.caches[0]._instr is None and model._prev_state is None


# ---- model: assertions fail ----
def test_start_pulse_violations_fail_1_1():
    model = cov.CoverageModel()
    start_word = 1 | (cov.CMD_START << 1)
    model.step(cov.Snapshot(state=cov.LOAD, ui_in=start_word, start=cov.ALL_CORES))
    assert model.failures == []
    model.step(run_snapshot(start=cov.ALL_CORES))  # still high in the next cycle
    assert failed_sections(model) == ["1.1"]


def test_snoop_valid_in_the_wrong_cycle_fails_2_2():
    model = cov.CoverageModel()
    model.step(run_snapshot(grant=1, grant_idx=0, req=1, done=1, bus_type=cov.INV, snoop_valid=0))
    assert failed_sections(model) == ["2.2"]


def test_two_dones_fail_2_4():
    model = cov.CoverageModel()
    model.step(run_snapshot(done=0b0011))
    assert failed_sections(model) == ["2.4"]


def test_dropped_request_fails_3_1():
    model = cov.CoverageModel()
    model.step(run_snapshot(req=0b0100))
    model.step(run_snapshot(req=0b0100))
    assert model.failures == []
    model.step(run_snapshot(req=0))
    assert failed_sections(model) == ["3.1"]


def test_request_completed_by_done_passes_3_1():
    model = cov.CoverageModel()
    model.step(run_snapshot(req=0b0100, grant=1, grant_idx=2, done=0b0100, snoop_valid=0b1011,
                            bus_type=cov.INV))
    model.step(run_snapshot(req=0))
    assert model.failures == []


def test_line_invariant_violations_fail_section_5():
    for state, sections in ((E, ["5.1"]), (O, ["5.2"]), (M, ["5.5", "5.6"])):
        model = cov.CoverageModel()
        model.step(run_snapshot(lines=lines_with(c0=(line(0, state), 0), c2=(line(0, state), 0))))
        assert failed_sections(model) == sections
    model = cov.CoverageModel()
    model.step(run_snapshot(lines=lines_with(c0=(line(0, M), 0), c2=(line(0, S), 0))))
    assert failed_sections(model) == ["5.6"]


# ---- module models on their own (as the module testbenches use them) ----
def test_decoder_model_standalone():
    model = cov.DecoderModel()
    before = hits("decoder.command_type", "CMD_LOAD_WR")
    model.step(cov.LOAD, 1 | (cov.CMD_LOAD_WR << 1), 0)
    model.step(cov.LOAD, 1 | (cov.CMD_START << 1), cov.ALL_CORES)
    model.step(cov.RUN, 1 | (cov.CMD_LOAD_WR << 1), 0)        # not LOAD: not a command
    assert model.findings.failures == []
    assert hits("decoder.command_type", "CMD_LOAD_WR") == before + 1
    model.step(cov.RUN, 0, 0b0001)                            # start outside CMD_START
    assert [m.split()[0] for m in model.findings.failures] == ["1.1"]


def test_bus_model_standalone():
    model = cov.BusModel()
    before = hits("system.cores_granted", 3)
    model.step(grant=1, grant_idx=3, done=0, snoop_valid=0b0111)
    model.step(grant=0, grant_idx=0, done=0b1000, snoop_valid=0)
    assert model.findings.failures == []
    assert hits("system.cores_granted", 3) == before + 1
    model.step(grant=1, grant_idx=3, done=0, snoop_valid=0b1111)
    assert [m.split()[0] for m in model.findings.failures] == ["2.2"]


def test_core_model_standalone():
    model = cov.CoreModel()
    before = hits("core.req_type", "INV")
    model.step(req=1, done=0, req_type=cov.INV)
    model.step(req=1, done=1, req_type=cov.INV)
    model.step(req=0, done=0, req_type=cov.RD)
    assert model.findings.failures == []
    assert hits("core.req_type", "INV") == before + 1
    model.step(req=1, done=0, req_type=cov.RD)
    model.step(req=0, done=0, req_type=cov.RD)
    assert [m.split()[0] for m in model.findings.failures] == ["3.1"]


def test_cache_ctrl_model_standalone_samples_protocol_per_instruction():
    model = cov.CacheCtrlModel()
    before_arc = arc_hits(I, M, "write_miss")
    before_proto = hits("cache_ctrl.protocol", "MSI")
    args = dict(local_inst=inst(1, 1, 1), snooped=0, snoop_type=cov.RD, snoop_addr=0)
    model.step(local_valid=1, inst_done=0, lines=(0, 0), protocol=cov.MSI, **args)
    model.step(local_valid=1, inst_done=1, lines=(0, 0), protocol=cov.MSI, **args)
    model.step(local_valid=0, inst_done=0, lines=(0, line(0, M, data=1)), protocol=cov.MSI, **args)
    assert model.findings.unexpected_arcs == []
    assert arc_hits(I, M, "write_miss") == before_arc + 1
    assert hits("cache_ctrl.protocol", "MSI") == before_proto + 1   # one instruction


def test_cache_ctrl_model_reports_arc_only_a_testbench_can_produce():
    """O -> S by a snooped read needs the protocol to change mid-run."""
    model = cov.CacheCtrlModel(core=2)
    args = dict(local_valid=0, local_inst=0, inst_done=0)
    model.step(snooped=1, snoop_type=cov.RD, snoop_addr=0, lines=(line(0, O), 0), **args)
    model.step(snooped=0, snoop_type=cov.RD, snoop_addr=0, lines=(line(0, S), 0), **args)
    assert model.findings.unexpected_arcs == [(2, O, S, "snoop_RD")]
