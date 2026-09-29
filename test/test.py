# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


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

    dut._log.info("Test round robin arbiter")

    # Single requester: grant goes straight to it
    dut.ui_in.value = 0b0100
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0b0100

    # All cores requesting: grant rotates round robin from the last grant
    dut.ui_in.value = 0b1111
    for expected in [0b1000, 0b0001, 0b0010, 0b0100, 0b1000]:
        await ClockCycles(dut.clk, 1)
        assert dut.uo_out.value == expected, f"expected {expected:04b}, got {dut.uo_out.value}"

    # No requests: no grant
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0
