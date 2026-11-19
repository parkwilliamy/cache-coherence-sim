import cocotb
from cocotb.triggers import Timer


async def settle():
    await Timer(1, unit="ns")


async def tick(dut):
    dut.clk.value = 1
    await Timer(1, unit="ns")
    dut.clk.value = 0
    await Timer(1, unit="ns")


@cocotb.test()
async def main_memory_decoder_load_and_bus_access(dut):
    dut = dut.main_mem_tb
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.loading.value = 1
    dut.dec_we.value = 0
    dut.dec_addr.value = 0
    dut.dec_din.value = 0
    dut.bus_we.value = 0
    dut.bus_addr.value = 0
    dut.bus_din.value = 0
    await settle()
    await tick(dut)
    dut.rst_n.value = 1

    dut.dec_addr.value = 2
    dut.dec_din.value = 1
    dut.dec_we.value = 1
    await settle()
    await tick(dut)
    dut.dec_we.value = 0
    await settle()
    dut.loading.value = 0
    dut.bus_addr.value = 2
    await settle()
    await tick(dut)
    dut.bus_we.value = 0
    await settle()
    assert int(dut.bus_dout.value) == 1

    dut.bus_din.value = 0
    dut.bus_we.value = 1
    await settle()
    await tick(dut)
    dut.bus_we.value = 0
    await settle()
    await tick(dut)
    await settle()
    assert int(dut.bus_dout.value) == 0
