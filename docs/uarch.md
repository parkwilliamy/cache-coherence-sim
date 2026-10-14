# Microarchitecture

## Parameters

- `N_CORES`: number of CPU cores
- `N_LINES`: number of cache lines per cache
- `MEM_SIZE`: number of words in main memory
- `PROGRAM_SIZE`: number of memory instructions in a core’s program memory
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


## Modules

## `decoder`

### Inputs
- `clk`
- `rst_n`
- `req_valid = ui_in[0]`: Input data from MCU valid
- `mem_sel = ui_in[1]`: Memory select
- `core_sel[$clog2(N_CORES)-1:0] = ui_in[2]`: Core select
- `protocol_sel[1:0] = ui_in[4:3]`: Cache coherence protocol selection
- `req_data[DATA_WIDTH-1:0] = ui_in[5]`: MCU request data
- `req_addr[ADDR_WIDTH-1:0] = ui_in[7:6]`: MCU request address
- `req_type = uio_in[0]`: MCU request type
- `en = uio_in[1]`: Begin program execution 

### Outputs
- `done = uo_out[0]`: Program done
- `state[ADDR_WIDTH+DATA_WIDTH+2:0] = uo_out[6:1]`: Cache state after program is finished (address, data, line state)
- `cycle_count = uio_out[7:2]`: Program cycle count

## `core`

### Inputs
- `clk`
- `rst_n`
- `inst[DATA_WIDTH+ADDR_WIDTH:0]`: Memory instruction/request
### Interfaces
- `mem_req`: Memory request channel for reads/writes
- `mem_resp`: Memory response channel for reads/writes
- `bus_req`: Bus request channel for bus snooping

## `cache`

### Inputs
- `clk`
- `rst_n`
- `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
- `din[DATA_WIDTH-1:0]`: Input data for writes
- `wen`: Write enable

### Outputs
- `dout[DATA_WIDTH-1:0]`: Output data for reads

## `cache_ctrl`

### Inputs
- `clk`
- `rst_n`
- `local_inst[DATA_WIDTH+ADDR_WIDTH:0]`: Local memory request from the core the cache is attached to
- `snoop_inst[DATA_WIDTH+ADDR_WIDTH:0]`: Snooped memory request from another core in the system
- `dout[DATA_WIDTH-1:0]`: Output data for reads
### Outputs
- `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
- `din[DATA_WIDTH-1:0]`: Input data for writes
- `wen`: Write enable
### Interfaces
- `mem_req`: Memory request channel for reads/writes
- `mem_resp`: Memory response channel for reads/writes
- `bus_req`: Bus request channel for bus snooping

## `bus`

### Inputs
- `clk`
- `rst_n`
- `req[N_CORES-1:0]`: Bus request bit vector
- `dout[DATA_WIDTH-1:0]`: Output data for reads

### Outputs
- `gnt[N_CORES-1:0]`: Bus grant bit vector
- `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
- `din[DATA_WIDTH-1:0]`: Input data for writes
- `wen`: Write enable

### Interfaces
- `mem_req`: Memory request channel for reads/writes
- `mem_resp`: Memory response channel for reads/writes
- `bus_req`: Bus request channel for bus snooping

## `main_mem`

### Inputs
- `clk`
- `rst_n`
- `addr[ADDR_WIDTH-1:0]`: Address for reads/writes
- `din[DATA_WIDTH-1:0]`: Input data for writes
- `wen`: Write enable

### Outputs
- `dout[DATA_WIDTH-1:0]`: Output data for reads