# Core

## Structures

- `logic [INST_SIZE-1:0] program_mem [PROGRAM_SIZE]`: Program memory
    - Uses a `head` pointer that points to the next instruction in program memory to be executed (initialized to `PROGRAM_SIZE-1`)
- `logic [INST_SIZE-1:0] curr_inst`: Current instruction being executed

## Control Flow

- If `program_mem_load == 1`:
    - `program_mem[head] = core_inst`
    - Decrement `head`
- Else if `start == 1`:
    - State transition from `IDLE` to `ACTIVE`

- While current state is `ACTIVE`:
    - `curr_inst = program_mem[head]`
    - Decrement `head`
    - Pass `curr_inst` to `cache_ctrl` module's `local_inst` port
    - Pass `protocol` to `cache_ctrl` module's `protocol` port
    - Pass `snoop_valid` and `snoop_inst` to `cache_ctrl` module's `snoop_inst` port
    - Pass `read_all` signal to `cache_ctrl` module's 
    - Accept `mem_req` from `cache_ctrl` module's `mem_req` port
    - Pass `mem_resp` to `cache_ctrl` module's `mem_resp` port