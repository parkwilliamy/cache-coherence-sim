import cocotb

import coverage as cov  # test/coverage.py
from tb_utils import settle, tick


def cmd_word(valid, cmd, core=0, addr=0, data=0):
    return valid | (cmd << 1) | (core << 3) | (addr << 5) | (data << 7)


def packed_lines():
    value = 0
    for core in range(4):
        for slot in range(2):
            line = 0x1f ^ ((core << 3) | (slot << 1))
            value |= line << ((core * 2 + slot) * 5)
    return value


@cocotb.test()
async def decoder_load_run_and_read_states(dut):
    dut = dut.decoder_tb
    monitor = cov.unit_monitor(cov.DecoderUnitMonitor, dut)
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0xa5
    dut.core_done.value = 0
    dut.lines.value = packed_lines()
    await settle()
    await tick(dut, monitor)
    dut.rst_n.value = 1
    await settle()
    assert int(dut.loading.value) == 1

    dut.ui_in.value = cmd_word(1, 0, core=2, addr=1)
    await settle()
    assert int(dut.dec_icache_load.value) == 0b0100
    assert int(dut.mem_we.value) == 0
    await tick(dut, monitor)

    dut.ui_in.value = cmd_word(1, 1, core=1, addr=2, data=1)
    await settle()
    assert int(dut.dec_icache_load.value) == 0b0010
    assert int(dut.mem_we.value) == 0
    await tick(dut, monitor)

    dut.ui_in.value = cmd_word(1, 2, addr=2, data=1)
    await settle()
    assert int(dut.mem_we.value) == 1
    assert int(dut.mem_addr.value) == 2
    assert int(dut.mem_din.value) == 1
    await tick(dut, monitor)
    dut.ui_in.value = 0
    await settle()
    assert int(dut.mem_we.value) == 0

    dut.ui_in.value = cmd_word(1, 3)
    await settle()
    await tick(dut, monitor)
    dut.ui_in.value = 0
    dut.core_done.value = 0
    await settle()
    assert int(dut.loading.value) == 0

    # Stay in RUN long enough to exercise the saturating cycle counter.
    for _ in range(130):
        await tick(dut, monitor)

    dut.core_done.value = 0b1111
    assert int(dut.dec_run.value) == 0b1111
    await tick(dut, monitor)
    await settle()
    assert int(dut.uio_oe.value) == 0xff
    assert int(dut.uo_out.value) & 1 == 1
    assert int(dut.uio_out.value) & 1 == 1

    # Exercise readback advancement through the wraparound point.
    dut.dut.cycle_count.value = 127
    dut.ui_in.value = 1
    for pattern in (0xa5, 0x5a, 0xff, 0x00):
        dut.uio_in.value = pattern
        dut.lines.value = packed_lines() ^ (0x1f << ((pattern & 7) * 5))
        for _ in range(2):
            await tick(dut, monitor)
        await tick(dut, monitor)
    dut.ui_in.value = 0

    for pattern in (0, (1 << 40) - 1, 0xaaaaaaaaaa, 0x5555555555):
        dut.lines.value = pattern
        await settle()
        await tick(dut, monitor)

    # Exercise the defensive default branch for an illegal state encoding.
    dut.dut.current_state.value = 0b11
    await settle()
    await tick(dut, monitor)
    await settle()
    assert int(dut.loading.value) == 1
