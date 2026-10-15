# Decoder

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
            - `program_mem_load = 1`
            - `inst` = {`req_addr`, `req_data`, `req_type`}
            - `core_insts[core_sel]` = `inst`
            -  Increment `insts_loaded`
        - Else if `mem_sel == 1`:
            - `load_req.valid = 1`
            - `program_mem_load = 0`
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