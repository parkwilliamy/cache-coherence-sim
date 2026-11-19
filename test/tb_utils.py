"""Helpers shared by the module-level tests, which drive the clock by hand."""

from cocotb.triggers import Timer


async def settle():
    await Timer(1, unit="ns")


async def tick(dut, monitor=None):
    """One clock cycle.

    With a coverage monitor (coverage.unit_monitor), the cycle is sampled first:
    after the inputs the test has set have settled and before the rising edge.
    monitor may be None, which is what unit_monitor returns on builds without
    coverage.
    """
    if monitor is not None:
        await settle()
        monitor.sample()
    dut.clk.value = 1
    await Timer(1, unit="ns")
    dut.clk.value = 0
    await Timer(1, unit="ns")
