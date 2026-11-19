import cocotb
from cocotb.triggers import Timer


async def settle():
    await Timer(1, unit="ns")


async def tick(dut):
    dut.clk.value = 1
    await Timer(1, unit="ns")
    dut.clk.value = 0
    await Timer(1, unit="ns")


def cmd_word(valid, cmd, core=0, addr=0, data=0):
    return valid | (cmd << 1) | (core << 3) | (addr << 5) | (data << 7)


@cocotb.test()
async def decoder_load_run_and_read_states(dut):
    dut = dut.decoder_tb
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.core_done.value = 0
    dut.lines.value = 0
    await settle()
    await tick(dut)
    dut.rst_n.value = 1
    await settle()
    assert int(dut.loading.value) == 1

    dut.ui_in.value = cmd_word(1, 2, addr=2, data=1)
    await settle()
    assert int(dut.mem_we.value) == 1
    assert int(dut.mem_addr.value) == 2
    assert int(dut.mem_din.value) == 1
    await tick(dut)
    dut.ui_in.value = 0
    await settle()
    assert int(dut.mem_we.value) == 0

    dut.ui_in.value = cmd_word(1, 3)
    await settle()
    await tick(dut)
    dut.ui_in.value = 0
    dut.core_done.value = 0b1111
    await settle()
    assert int(dut.loading.value) == 0
    assert int(dut.dec_run.value) == 0b1111
    await tick(dut)
    await settle()
    assert int(dut.uio_oe.value) == 0xff
    assert int(dut.uo_out.value) & 1 == 1
