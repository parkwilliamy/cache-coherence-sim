# Encodings

## Instructions (`inst_t`)

| Field | ADDR | DATA | OP | 
|----|----|----|----|
| Bit Width | `ADDR_WIDTH`| `DATA_WIDTH` | 1 bit |

- `inst.addr` is address to read from or write to in main memory
- `inst.data` is data to write to memory (only for write instructions)
- `inst.op` is instruction type: 0 for reads and 1 for writes
- Each line of program memory holds one memory request

## Cache Lines (`line_t`)

| Field | ADDR | DATA | STATE | 
|----|----|----|----|
| Bit Width | `ADDR_WIDTH`| `DATA_WIDTH` | 3 bits |

- `line.addr` is the line address from main memory
- `line.data` is the cache line data
    - Due to space constraints, a line contains one word of data unlike typical caches which hold multiple data words in a single cache line
- `line.state` is the cache line's coherence state (see below)

### Line States

- `INVALID`
    - Cache line has stale data
    - State `3'b000`
- `SHARED`
    - Cache line is present in other cores as well
    - State `3'b001`
- `MODIFIED`
    - Cache line has been written to; line is dirty
    - State `3'b010`
- `EXCLUSIVE`
    - Cache line only exists in this cache
    - State `3'b011`
- `OWNER`
    - Cache line has been written to and must be shared with other cores that read it
    - State `3'b100`

## MCU to Cache Coherence Controller Transactions

- `N_CORES` * `PROGRAM_SIZE` instructions loaded from MCU
- `MEM_SIZE` words loaded into main memory from MCU
- `N_CORES` * `CACHE_SIZE` cache lines loaded from ASIC into MCU
- MCU asserts `req_valid` until it has initialized all cores' caches and the main memory
    - `N_CORES * PROGRAM_SIZE` + `MEM_SIZE` cycles
    - `mem_sel`, `core_sel`, `protocol_sel` are set accordingly as long as `req_valid` is asserted
- Once MCU initializes the caches and main memory, it asserts `en` as a one cycle pulse to begin execution
- `cache_state` and `cycle_count` are valid as long as `resp_valid` is asserted

### Control Flow
- If `req_valid`:
    - State transition from `IDLE` to `LOAD`
    - While in `LOAD` (`req_valid` still asserted):
        - `protocol_sel` written to `protocol` register
        - `insts_loaded = 0`
        - If `mem_sel == 0 && insts_loaded < PROGRAM_SIZE`:
            - `load_req.valid = 0`
            - `inst` = {`req_addr`, `req_data`, `req_type`}
            - `core_insts[core_sel]` = `inst`
            -  Increment `insts_loaded`
        - Else if `mem_sel == 1`:
            - `load_req.valid = 1`
            - `load_req.addr` = `req_addr`
            - `load_req.data` = `req_data`
- Else:
    - `done = &state`
    - If `done`:
        - State transition from `IDLE` to `RECEIVE`
        - `cache_read_reqs = 1`
        - `curr_core = 0`
        - While in `RECEIVE` and `curr_core < N_CORES`:
            - `resp_valid = 1`
            - After `CACHE_SIZE` clock cycles, `cache_read_reqs << 1`, `cache_state = cache_read_data[curr_core]`
            - Increment `curr_core`
        - `resp_valid = 0`

- If `en`:
    - Begin incrementing `cycles` register each clock cycle until `done` is asserted
    - Note that the counting will continue after `en` is deasserted, since `en` is a one cycle pulse