# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb_coverage.coverage import coverage_db

import coverage as cov  # test/coverage.py: functional coverage model and assertions

RD_OP, WR_OP = 0, 1
ADDR_LSB = 3 + cov.CORE_SEL_WIDTH
DATA_LSB = ADDR_LSB + cov.ADDR_WIDTH


def cmd_word(cmd, core=0, addr=0, data=0):
    """LOAD command word with req_valid = 1 (docs/encodings.md, "MCU pin words")."""
    word = 1 | (cmd << 1) | (core << 3) | (addr << ADDR_LSB) | (data << DATA_LSB)
    assert word < 256, "command word does not fit in ui_in"
    return word


async def reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1


async def run_programs(dut, programs, memory, protocol, timeout=200):
    """Drive one complete run over the pins, starting from reset.

    programs: per core, a list of (op, addr, data), ICACHE_SIZE entries each.
    memory:   {addr: word} loaded into main memory.
    Inputs change just after a rising edge, so each command is executed at the
    following edge. Returns the cycle count reported by the decoder.
    """
    for core, program in enumerate(programs):
        assert len(program) == cov.ICACHE_SIZE
        for op, addr, data in program:
            cmd = cov.CMD_LOAD_WR if op == WR_OP else cov.CMD_LOAD_RD
            dut.ui_in.value = cmd_word(cmd, core, addr, data)
            await RisingEdge(dut.clk)
    for addr, data in memory.items():
        dut.ui_in.value = cmd_word(cov.CMD_LOAD_MEM, addr=addr, data=data)
        await RisingEdge(dut.clk)

    # The start command carries the protocol, which is then held for the run.
    dut.ui_in.value = 1 | (cov.CMD_START << 1) | (protocol << cov.PROTOCOL_LSB)
    await RisingEdge(dut.clk)
    dut.ui_in.value = protocol << cov.PROTOCOL_LSB
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) & 1:  # resp_valid
            return int(dut.uo_out.value) >> 1
    raise AssertionError(f"run did not finish within {timeout} cycles")


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1


# One MESI run that exercises the coverage model end to end. It is a smoke test of
# the model, not coverage closure. The checks at the end hold for any bus
# interleaving:
# - core 2 is the only core that touches address 2, so its line is still MODIFIED
#   when the read of address 0 (same slot) evicts it: a WB is guaranteed.
# - core 0 is the only core that writes address 0, so nothing invalidates its
#   copy: its second write and the read after it are hits.
SMOKE_PROGRAMS = [
    [(WR_OP, 0, 1), (WR_OP, 0, 0), (RD_OP, 0, 0), (RD_OP, 1, 0)],
    [(RD_OP, 0, 0), (RD_OP, 0, 0), (RD_OP, 1, 0), (RD_OP, 1, 0)],
    [(WR_OP, 2, 1), (RD_OP, 0, 0), (RD_OP, 2, 0), (RD_OP, 3, 0)],
    [(RD_OP, 3, 0), (WR_OP, 3, 1), (RD_OP, 1, 0), (RD_OP, 3, 0)],
]


@cocotb.test()
async def test_coverage_smoke(dut):
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    monitor = cov.start_coverage(dut)

    await reset(dut)
    cycles = await run_programs(dut, SMOKE_PROGRAMS, memory={1: 1}, protocol=cov.MESI)
    cocotb.log.info("run finished, cycle_count = %d", cycles)
    await ClockCycles(dut.clk, 2)

    if monitor is None:  # gate-level or sv2v build: the run above is the test
        return
    assert not monitor.model.unexpected_arcs, monitor.model.unexpected_arcs

    def fully_covered(item):
        return coverage_db[item].coverage == coverage_db[item].size

    for item in ("decoder.command_type", "core.req_type", "system.cores_granted",
                 "cache_ctrl.req_hit_cross"):
        assert fully_covered(item), f"{item}: {coverage_db[item].detailed_coverage}"
    assert coverage_db["cache_ctrl.protocol"].detailed_coverage["MESI"] >= 1
    assert coverage_db["system.program_cross"].coverage == len(SMOKE_PROGRAMS)
    # The assertions the run is bound to exercise were evaluated and held.
    for item in ("decoder.decoder_start_pulse", "bus.snoop_valid_when_grant",
                 "bus.only_one_done_valid", "core.req_valid_until_done",
                 "system.one_cache_holds_modified", "system.modified_excludes_other_copies"):
        assert fully_covered(item), f"{item}: {coverage_db[item].detailed_coverage}"
