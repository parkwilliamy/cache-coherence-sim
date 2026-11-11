import cocotb
from cocotb.triggers import Timer


RD = 0
INV = 1
WB = 2
MSI = 0
MESI = 1
MOESI = 2


def line(tag, data, valid, dirty, exclusive):
    return (tag << 4) | (data << 3) | (valid << 2) | (dirty << 1) | exclusive


async def settle():
    await Timer(1, unit="ns")


async def tick(dut):
    dut.clk.value = 1
    await Timer(1, unit="ns")
    dut.clk.value = 0
    await Timer(1, unit="ns")


def set_local(dut, valid, addr=0, data=0, op=0):
    dut.local_valid.value = valid
    dut.local_addr.value = addr
    dut.local_data.value = data
    dut.local_op.value = op


def clear_snoop(dut):
    dut.bus_snoop_valid.value = 0
    dut.bus_snoop_type.value = RD
    dut.bus_snoop_addr.value = 0


@cocotb.test()
async def cache_controller_local_and_snoop_behavior(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.protocol.value = MSI
    dut.bus_done.value = 0
    dut.bus_resp_shared.value = 0
    dut.bus_resp_data.value = 0
    clear_snoop(dut)
    set_local(dut, 0)
    await settle()
    await tick(dut)
    dut.rst_n.value = 1
    await settle()

    assert int(dut.line0.value) == 0
    assert int(dut.line1.value) == 0

    # A read miss requests RD and installs an exclusive line when no copy exists.
    set_local(dut, 1, addr=0)
    dut.protocol.value = MESI
    await settle()
    assert int(dut.bus_req.value) == 1
    assert int(dut.bus_req_type.value) == RD
    assert int(dut.bus_req_addr.value) == 0
    assert int(dut.inst_done.value) == 0
    await tick(dut)

    dut.bus_done.value = 1
    dut.bus_resp_data.value = 1
    dut.bus_resp_shared.value = 0
    await settle()
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 0)
    dut.bus_done.value = 0
    await settle()
    assert int(dut.line0.value) == line(0, 1, 1, 0, 1)

    # Reads hit locally; a write hit in E updates the data and becomes M.
    set_local(dut, 1, addr=0)
    await settle()
    assert int(dut.bus_req.value) == 0
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 1, addr=0, data=0, op=1)
    await settle()
    assert int(dut.bus_req.value) == 0
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 0)
    await settle()
    assert int(dut.line0.value) == line(0, 0, 1, 1, 1)

    # A snoop takes priority over local work and makes a dirty line an owner in MOESI.
    set_local(dut, 1, addr=0)
    dut.protocol.value = MOESI
    dut.bus_snoop_valid.value = 1
    dut.bus_snoop_type.value = RD
    dut.bus_snoop_addr.value = 0
    await settle()
    assert int(dut.snoop_hit.value) == 1
    assert int(dut.snoop_owner.value) == 1
    assert int(dut.snoop_data.value) == 0
    assert int(dut.inst_done.value) == 0
    await tick(dut)
    set_local(dut, 0)
    dut.bus_snoop_valid.value = 0
    await settle()
    assert int(dut.line0.value) == line(0, 0, 1, 1, 0)

    # With O disabled, a read snoop downgrades the owner to clean shared.
    dut.protocol.value = MSI
    dut.bus_snoop_valid.value = 1
    dut.bus_snoop_type.value = RD
    await settle()
    assert int(dut.snoop_owner.value) == 1
    await tick(dut)
    clear_snoop(dut)
    await settle()
    assert int(dut.line0.value) == line(0, 0, 1, 0, 0)

    # A write hit on S requests INV and only writes the line when done arrives.
    set_local(dut, 1, addr=0, data=1, op=1)
    await settle()
    assert int(dut.bus_req.value) == 1
    assert int(dut.bus_req_type.value) == INV
    assert int(dut.inst_done.value) == 0
    await tick(dut)
    dut.bus_done.value = 1
    await settle()
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 0)
    dut.bus_done.value = 0
    await settle()
    assert int(dut.line0.value) == line(0, 1, 1, 1, 1)

    # An INV snoop invalidates a matching line; a write miss allocates M.
    dut.bus_snoop_valid.value = 1
    dut.bus_snoop_type.value = INV
    dut.bus_snoop_addr.value = 0
    await tick(dut)
    clear_snoop(dut)
    await settle()
    assert int(dut.line0.value) == 0

    set_local(dut, 1, addr=1, data=1, op=1)
    await settle()
    assert int(dut.bus_req.value) == 1
    assert int(dut.bus_req_type.value) == INV
    dut.bus_done.value = 1
    await settle()
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 0)
    dut.bus_done.value = 0
    await settle()
    assert int(dut.line1.value) == line(0, 1, 1, 1, 1)

    # A dirty conflict first writes back the victim, then retries as a read miss.
    set_local(dut, 1, addr=3)
    await settle()
    assert int(dut.bus_req.value) == 1
    assert int(dut.bus_req_type.value) == WB
    assert int(dut.bus_req_addr.value) == 1
    assert int(dut.bus_req_data.value) == 1
    assert int(dut.inst_done.value) == 0
    await tick(dut)
    dut.bus_done.value = 1
    await settle()
    assert int(dut.bus_req_type.value) == WB
    assert int(dut.inst_done.value) == 0
    await tick(dut)
    dut.bus_done.value = 0
    await settle()
    assert int(dut.line1.value) == 0
    assert int(dut.bus_req.value) == 1
    assert int(dut.bus_req_type.value) == RD
    assert int(dut.bus_req_addr.value) == 3

    dut.bus_done.value = 1
    dut.bus_resp_data.value = 0
    dut.bus_resp_shared.value = 1
    await settle()
    assert int(dut.inst_done.value) == 1
    await tick(dut)
    set_local(dut, 0)
    dut.bus_done.value = 0
    await settle()
    assert int(dut.line1.value) == line(1, 0, 1, 0, 0)

    # WB snoops do not change a matching clean line; a nonmatching snoop misses.
    dut.bus_snoop_valid.value = 1
    dut.bus_snoop_type.value = WB
    dut.bus_snoop_addr.value = 3
    await settle()
    assert int(dut.snoop_hit.value) == 1
    await tick(dut)
    dut.bus_snoop_addr.value = 2
    await settle()
    assert int(dut.snoop_hit.value) == 0
    await tick(dut)
    clear_snoop(dut)
    await settle()
    assert int(dut.line1.value) == line(1, 0, 1, 0, 0)
