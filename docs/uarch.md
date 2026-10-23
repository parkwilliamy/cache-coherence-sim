# Microarchitecture

## Parameters

- `N_CORES`: number of CPU cores
- `DCACHE_SIZE`: number of cache lines per cache
- `LINE_SIZE`: cache line size = `ADDR_WIDTH+DATA_WIDTH+2`
- `MEM_SIZE`: number of words in main memory
- `ICACHE_SIZE`: number of instructions in a core’s instruction cache
- `INST_SIZE`: instruction size = `ADDR_WIDTH+DATA_WIDTH`
- `DATA_WIDTH`: bitwidth of one word of data
- `ADDR_WIDTH`: bitwidth of address = log2(`MEM_SIZE`)
- `IDX_WIDTH`: bitwidth of cache line index = log2(`DCACHE_SIZE`)
- `TAG_WIDTH`: bitwidth of cache line tag = `ADDR_WIDTH` - `IDX_WIDTH`

## Interfaces

- `mem_req_if`: Core to bus request port with request-grant handshaking
    - `req`
    - `gnt`
    - `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
    - `din[DATA_WIDTH-1:0]`: Input data for writes
    - `wen`: Write enable
    - `wb`: Writeback (for dirty cache lines)
    - Modports: `manager`, `subordinate`
- `mem_resp_if`: Core to bus response port
    - `valid`
    - `dout[DATA_WIDTH-1:0]`: Output data for reads
    - Modports: `manager`, `subordinate`

## Structs

- `inst_t`
    - Memory instruction/request stored in the instruction cache
- `inv_t`
    - Invalidate request
- `transfer_t`
    - Cache to cache transfer request
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
- `line_t cache_read_data`: Cache line data from a core; read after program is finished to check cache line states

### Outputs
- `logic start = en`: Begin program execution; one cycle pulse from MCU
- `logic uo_out[0] = resp_valid`: Response data valid signal to send to MCU
- `logic [INST_SIZE-1:0] core_insts [N_CORES]`: Array of instructions for each core's instruction cache; array of structs
- `logic icache_load`: Initialize instruction caches
- `logic [N_CORES-1:0] cache_read_reqs`: Bit vector of cache read requests for each core, where a set bit indicates the decoder is reading the lines from the cache that corresponds to that bit
- `logic uo_out[6:1] = cache_state[LINE_SIZE-1:0]`: Cache state after program is finished (address, data, line state)
- `logic uio_out[7:2] = cycle_count`: Program cycle count

### Interfaces
- `mem_req_if load_req`: Memory request channel for initializing main memory

The decoder has 4 functions:
1) Initializes instruction caches with requests/instructions
2) Initializes main memory with data
3) Configures cache controller state with coherence protocol type
4) Returns cache state and program metrics after execution is finished

## `core`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic start`: Begin program execution
- `logic icache_load`: Initialize instruction cache
- `inst_t core_inst`: Instruction to load into instruction cache
- `logic read_all`: Flag indicating all cache lines are requested to be read; cache will output each line in the cache sequentially, with one line being output per clock cycle
- `logic [2:0] protocol`: Selected cache coherence protocol
- `logic snoop_valid`: Snooped request valid
- `inst_t snoop_inst`: Snooped memory request from another core in the system
### Outputs
- `line_t line_out`: Cache line (tag, data, state bits)
- `inv_t inv`: Invalidate signal
- `transfer_t transfer`: Cache to cache transfer signal
### Interfaces
- `mem_req_if mem_req`: Memory request channel for reads/writes
- `mem_resp_if mem_resp`: Memory response channel for reads/writes

The core instantiates the cache controller. It is responsible for fetching instructions from the instruction cache and forwarding them to the cache controller.

## `cache_ctrl`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic read_all`: Flag indicating all cache lines are requested to be read; cache will output each line in the cache sequentially, with one line being output per clock cycle
- `inst_t local_inst`: Local memory request from the core the cache is attached to
- `logic [2:0] protocol`: Selected cache coherence protocol
- `logic snoop_valid`: Snooped request valid
- `inst_t snoop_inst`: Snooped memory request from another core in the system
### Outputs
- `line_t line_out`: Cache line (tag, data, state bits)
- `inv_t inv`: Invalidate signal
- `transfer_t transfer`: Cache to cache transfer signal
- `logic inst_done`: Instruction done flag; indicates to the core the next instruction can be 
fetched
### Interfaces
- `mem_req_if mem_req`: Memory request channel for reads/writes
- `mem_resp_if mem_resp`: Memory response channel for reads/writes

The cache controller holds the cache registers and decodes addresses to determine tag/index fields and whether an access results in a cache hit or miss.

## `bus`

### Inputs
- `logic clk`
- `logic rst_n`
- `inv_t inv_reqs [N_CORES]`: Invalidate signals from cores
- `transfer_t transfer_reqs [N_CORES]`: Cache to cache transfer signals from cores
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads

### Outputs
- `inst_t snoop_inst [N_CORES]`: Snooped memory request from another core in the system, broadcast to every other core
- `inv_t snoop_inv [N_CORES]`: Snooped invalidate signal form another core in the system, broadcast to every other core
- `transfer_t snoop_transfer [N_CORES]`: Snooped cache-to-cache transfer signal form another core in the system, broadcast to destination core
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable

### Interfaces
- `mem_req_if reqs [N_CORES]`: Array of bus requests from each core
- `mem_resp_if resp [N_CORES]`: Array of bus responses to each core

The bus arbitrates memory requests using a round-robin scheme, forwarding selected requests to main memory. Additionally, the bus broadcasts selected memory requests to every other core to maintain cache coherence. Finally, the bus also services invalidation and cache-to-cache transfer requests.

## `main_mem`

### Inputs
- `logic clk`
- `logic rst_n`
- `logic [ADDR_WIDTH-1:0] addr`: Address for reads/writes
- `logic [DATA_WIDTH-1:0] din`: Input data for writes
- `logic wen`: Write enable

### Outputs
- `logic [DATA_WIDTH-1:0] dout`: Output data for reads