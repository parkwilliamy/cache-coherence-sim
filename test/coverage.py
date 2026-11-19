from cocotb_coverage.coverage import (
    CoverPoint, CoverCross, CoverCheck, coverage_section,
)

MEM_SIZE = 4
DATA_WIDTH = 1

CMD_LOAD_RD, CMD_LOAD_WR, CMD_LOAD_MEM, CMD_START = 0, 1, 2, 3
RD, INV, WB = 0, 1, 2
MSI, MESI, MOESI = 0, 1, 2
I, S, E, O, M = 0, 4, 5, 6, 7
STATE_TRANSITIONS = [
    (I, E),
    (I, S),
    (I, M),
    (E, E),
    (E, S),
    (E, M),
    (S, S),
    (S, I),
    (S, E),
    (S, M),
    (M, I),
    (M, S),
    (M, E),
    (M, O),
    (M, M),
    (O, O),
    (O, I),
    (O, M),
    (O, S),
    (O, E)
]

DecoderCoverage = coverage_section(
    CoverPoint("decoder.command_type", vname="cmd", bins=[CMD_LOAD_RD, CMD_LOAD_WR, CMD_LOAD_MEM, CMD_START])
)

CoreCoverage = coverage_section(
    CoverPoint("core.req_type", vname="req_type", bins=[RD, INV, WB])
)

CacheControllerCoverage = coverage_section(
    CoverPoint("cache_ctrl.protocol", vname="protocol", bins=[MSI, MESI, MOESI]),
    CoverPoint("cache_ctrl.req_type", vname="req_type", bins=[0,1]),
    CoverPoint("cache_ctrl.cache_hit", vname="cache_hit", bins=[0,1]),
    CoverCross("cache_ctrl.req_hit_cross", items=["cache_ctrl.req_type", "cache_ctrl.cache_hit"]),
    CoverPoint("cache_ctrl.state_transitions", xf=lambda prev, curr: (prev, curr), bins=STATE_TRANSITIONS)
)

SystemCoverage = coverage_section(
    CoverPoint("system.cores_granted", ) # TBD
    CoverPoint("system.inst_addr", xf=lambda inst: inst.addr, bins=list(range(MEM_SIZE))),
    CoverPoint("system.inst_data", xf=lambda inst: inst.data, bins=list(range(DATA_WIDTH))),
    CoverPoint("system.inst_op", xf=lambda inst: inst.op, bins=list(range(DATA_WIDTH))),
    CoverCross("system.program_cross", items=["system.inst_addr", "system.inst_data", "system.inst_op"])
)