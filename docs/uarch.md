# Microarchitecture

## Parameters

- `N_CORES`: number of CPU cores
- `CACHE_SIZE`: number of cache lines per cache
- `LINE_SIZE`: cache line size = `ADDR_WIDTH+DATA_WIDTH+2`
- `MEM_SIZE`: number of words in main memory
- `PROGRAM_SIZE`: number of memory instructions in a core’s program memory
- `INST_SIZE`: instruction size = `ADDR_WIDTH+DATA_WIDTH`
- `DATA_WIDTH`: bitwidth of one word of data
- `ADDR_WIDTH`: bitwidth of address = log2(`MEM_SIZE`)

## Interfaces

- `mem_req_if`: Core to bus request port with request-grant handshaking
    - `req`
    - `gnt`
    - `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
    - `din[DATA_WIDTH-1:0]`: Input data for writes
    - `wen`: Write enable
    - Modports: `manager`, `subordinate`
- `mem_resp_if`: Core to bus response port with ready-valid handshaking
    - `ready`
    - `valid`
    - `dout[DATA_WIDTH-1:0]`: Output data for reads
    - Modports: `manager`, `subordinate`

## Structs

- `inst_t`
    - Memory instruction/request stored in program memory
- `line_t`
    - Cache line
- See [encodings.md](./encodings.md) for specific fields

## Modules

## `decoder`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic req_valid = ui_in[0]`: Input data from MCU valid
- `logic mem_sel = ui_in[1]`: Memory select
- `logic [$clog2(N_CORES)-1:0] core_sel = ui_in[2]`: Core select
- `logic [1:0] protocol_sel = ui_in[4:3]`: Cache coherence protocol selection
- `logic [DATA_WIDTH-1:0] req_data = ui_in[5]`: MCU request data
- `logic [ADDR_WIDTH-1:0] req_addr = ui_in[7:6]`: MCU request address
- `logic req_type = uio_in[0]`: MCU request type
- `logic en = uio_in[1]`: Begin program execution; one cycle pulse from MCU
- `logic [N_CORES-1:0] state`: Core state bit vector; each bit encodes whether a program has finished executing for a given core or not
- `logic [LINE_SIZE-1:0] cache_read_data [N_CORES]`: Array of cache line data from each core; read after program is finished to check cache line states

### Outputs
- `logic start = en`: Begin program execution; one cycle pulse from MCU
- `logic uo_out[0] = resp_valid`: Response data valid signal to send to MCU
- `logic [INST_SIZE-1:0] core_insts [N_CORES]`: Array of instructions for each core's program memory; array of structs
- `logic program_mem_load`: Initialize program memory
- `logic [N_CORES-1:0] cache_read_reqs`: Bit vector of cache read requests for each core, where a set bit indicates the decoder is reading the lines from the cache that corresponds to that bit
- `logic uo_out[6:1] = cache_state[LINE_SIZE-1:0]`: Cache state after program is finished (address, data, line state)
- `logic uio_out[7:2] = cycle_count`: Program cycle count

### Interfaces
- `mem_req_if load_req`: Memory request channel for initializing main memory

The decoder has 4 functions:
1) Initializes program memory with requests/instructions
2) Initializes main memory with data
3) Configures cache controller state with coherence protocol type
4) Returns cache state and program metrics after execution is finished

## `core`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic start`: Begin program execution
- `logic program_mem_load`: Initialize program memory
- `logic [INST_SIZE-1:0] core_inst`: Instruction to load into program memory
- `logic read_all`: Flag indicating all cache lines are requested to be read; cache will output each line in the cache sequentially, with one line being output per clock cycle
- `logic snoop_valid`: Snooped request valid
- `logic [INST_WIDTH-1:0] snoop_inst`: Snooped memory request from another core in the system
### Interfaces
- `mem_req_if mem_req`: Memory request channel for reads/writes
- `mem_resp_if mem_resp`: Memory response channel for reads/writes

The core instantiates the cache and cache controller. It is responsible for fetching instructions from the program memory and forwarding them to the cache controller.

## `cache_ctrl`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic read_all`: Flag indicating all cache lines are requested to be read; cache will output each line in the cache sequentially, with one line being output per clock cycle
- `logic [INST_WIDTH-1:0] local_inst`: Local memory request from the core the cache is attached to
- `logic [INST_WIDTH-1:0] snoop_inst`: Snooped memory request from another core in the system
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads
### Outputs
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable
### Interfaces
- `mem_req_if mem_req`: Memory request channel for reads/writes
- `mem_resp_if mem_resp`: Memory response channel for reads/writes

## `cache`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic read_all`: Flag indicating all cache lines are requested to be read; cache will output each line in the cache sequentially, with one line being output per clock cycle
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable

### Outputs
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads

## `bus`

### Inputs
- `logic clk`
- `logic rst_n`
- `mem_req_if reqs [N_CORES]`: Array of bus requests from each core
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads

### Outputs
- `mem_resp_if resp [N_CORES]`: Array of bus responses to each core
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable

### Interfaces
- `mem_req_if mem_req`: Memory request channel for reads/writes
- `mem_resp_if mem_resp`: Memory response channel for reads/writes

## `main_mem`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable

### Outputs
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads