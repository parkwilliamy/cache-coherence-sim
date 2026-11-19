import cocotb

import coverage as cov  # test/coverage.py
from tb_utils import settle, tick


@cocotb.test()
async def core_loads_icache_and_reports_done(dut):
    dut = dut.core_tb
    monitor = cov.unit_monitor(cov.CoreUnitMonitor, dut)
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.dec_start.value = 0
    dut.dec_run.value = 0
    dut.dec_icache_load.value = 0
    dut.load_inst.value = 0
    dut.protocol.value = 0
    dut.bus_done.value = 0
    dut.bus_snoop_valid.value = 0
    dut.bus_snoop_type.value = 0
    dut.bus_snoop_addr.value = 0
    dut.bus_resp_shared.value = 0
    dut.bus_resp_data.value = 0
    await settle()
    await tick(dut, monitor)
    dut.rst_n.value = 1

    dut.dec_run.value = 1
    dut.dec_start.value = 1
    dut.dec_icache_load.value = 1
    dut.load_inst.value = 0
    await settle()
    await tick(dut, monitor)
    dut.dec_start.value = 0

    dut.dec_icache_load.value = 0
    await settle()
    assert int(dut.core_done.value) == 0
