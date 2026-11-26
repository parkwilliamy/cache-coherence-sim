import cocotb

import coverage as cov  # test/coverage.py
from tb_utils import settle, tick


RD = 0
INV = 1
WB = 2


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

    # Grant each core once; the snoop mask and done response are checked for
    # every grant by the coverage monitor.
    for core in range(4):
        dut.req.value = 1 << core
        dut.req_type.value = 0
        dut.req_addr.value = core << (2 * core)
        await settle()
        assert int(dut.done.value) == 0
        assert int(dut.snoop_valid.value) == (0b1111 & ~(1 << core))
        await tick(dut, monitor)
        await tick(dut, monitor)
        assert int(dut.done.value) == (1 << core)
        await tick(dut, monitor)

        dut.req.value = 0
        await settle()
        assert int(dut.done.value) == 0

    # A snooped owner in MSI supplies data and also writes it back to memory.
    dut.req.value = 1
    dut.req_type.value = RD
    dut.req_addr.value = 1
    dut.req_data.value = 0
    dut.snoop_hit.value = 0b0010
    dut.snoop_owner.value = 0b0010
    dut.snoop_data.value = 1 << 1
    dut.protocol.value = 0
    await settle()
    assert int(dut.shared.value) == 1
    assert int(dut.mem_we.value) == 1
    assert int(dut.mem_addr.value) == 1
    await tick(dut, monitor)
    dut.req.value = 0
    await settle()
    await tick(dut, monitor)
    await tick(dut, monitor)

    # An owner in MOESI satisfies the read directly and completes without memory.
    dut.req.value = 1 << 2
    dut.req_type.value = RD
    dut.req_addr.value = 1 << 4
    dut.snoop_hit.value = 0b0010
    dut.snoop_owner.value = 0b0010
    dut.snoop_data.value = 1 << 1
    dut.protocol.value = 2
    await settle()
    assert int(dut.done.value) == 1 << 2
    assert int(dut.resp_data.value) == 1
    await tick(dut, monitor)
    dut.req.value = 0
    dut.snoop_hit.value = 0
    dut.snoop_owner.value = 0
    await settle()

    # Exercise a busy bus with no new grant, including the transition to idle.
    dut.dut.wait_count.value = 1
    dut.req.value = 0
    await settle()
    await tick(dut, monitor)

    # Exercise all two-bit request-type encodings on every core.
    for core in range(4):
        dut.req.value = 1 << core
        dut.req_type.value = sum(value << (2 * idx) for idx, value in enumerate(
            ((core + idx) & 0b11 for idx in range(4))))
        dut.req_addr.value = sum(((core ^ idx) & 0b11) << (2 * idx) for idx in range(4))
        dut.req_data.value = ((0b1010 ^ core) & 0b1111)
        dut.snoop_hit.value = 0b1010
        dut.snoop_owner.value = 0b0101
        dut.snoop_data.value = 0b1111
        await settle()
        await tick(dut, monitor)
        dut.req.value = 0
        await settle()

    # A write-back performs a memory write and a invalidate request completes
    # immediately on grant.
    dut.req.value = 1 << 3
    dut.req_type.value = WB << 6
    dut.req_addr.value = 3 << 6
    dut.req_data.value = 1 << 3
    await settle()
    assert int(dut.mem_we.value) == 1
    assert int(dut.mem_addr.value) == 3
    assert int(dut.mem_din.value) == 1
    await tick(dut, monitor)
    dut.req.value = 0
    await settle()
    await tick(dut, monitor)
    await tick(dut, monitor)

    dut.req.value = 1 << 1
    dut.req_type.value = INV << 2
    dut.req_addr.value = 2 << 2
    await settle()
    assert int(dut.done.value) == 1 << 1
    await tick(dut, monitor)
    dut.req.value = 0
    await settle()

    # Vary every core's request fields and snoop inputs so all bus data/control
    # toggles are exercised.
    dut.protocol.value = 0b11
    dut.req.value = 0b1111
    dut.req_type.value = (WB << 6) | (INV << 4) | (RD << 2) | INV
    dut.req_addr.value = (3 << 6) | (2 << 4) | (1 << 2) | 0
    dut.req_data.value = 0b1010
    dut.snoop_hit.value = 0b1010
    dut.snoop_owner.value = 0b0101
    dut.snoop_data.value = 0b0101
    await settle()
    await tick(dut, monitor)

    dut.req.value = 0b0101
    dut.req_type.value = (RD << 6) | (WB << 4) | (INV << 2) | WB
    dut.req_addr.value = 0b11100100
    dut.req_data.value = 0b0101
    dut.snoop_hit.value = 0b0101
    dut.snoop_owner.value = 0b1010
    dut.snoop_data.value = 0b1010
    await settle()
    await tick(dut, monitor)
    await tick(dut, monitor)

    dut.req.value = 0
    dut.snoop_hit.value = 0
    dut.snoop_owner.value = 0
    await settle()
