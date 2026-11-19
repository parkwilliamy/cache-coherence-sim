import cocotb

import coverage as cov  # test/coverage.py
from tb_utils import settle, tick


@cocotb.test()
async def bus_arbitrates_and_applies_memory_latency(dut):
    dut = dut.bus_tb
    monitor = cov.unit_monitor(cov.BusUnitMonitor, dut)
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.req.value = 0
    dut.req_type.value = 0
    dut.req_addr.value = 0
    dut.req_data.value = 0
    dut.snoop_hit.value = 0
    dut.snoop_owner.value = 0
    dut.snoop_data.value = 0
    dut.protocol.value = 0
    await settle()
    await tick(dut, monitor)
    dut.rst_n.value = 1
    await settle()

    dut.req.value = 1
    dut.req_type.value = 0
    dut.req_addr.value = 2
    await settle()
    assert int(dut.done.value) == 0
    assert int(dut.snoop_valid.value) == 0b1110
    assert int(dut.snoop_addr.value) == 2
    await tick(dut, monitor)
    await tick(dut, monitor)
    assert int(dut.done.value) == 1
    await tick(dut, monitor)

    dut.req.value = 0
    await settle()
    assert int(dut.done.value) == 0
