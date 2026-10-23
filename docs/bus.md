# Bus

## Structures

- `logic [$clog2(N_CORES)-1:0] gidx`: Core/index of the granted request from `reqs`
- `logic [$clog2(N_CORES)-1:0] didx`: Destination core/index for a cache-to-cache transfer
- `logic [ADDR_WIDTH-1:0] gnt_addr`: Granted request address
- `logic [DATA_WIDTH-1:0] gnt_data`: Granted request data
- `logic gnt_wen`: Granted request write enable
- `logic gnt_wb`: Granted request writeback signal
- `transfer_t curr_transfer`: Current transfer request being serviced

## Control Flow

- Uses round-robin arbiter for memory request arbitration
    - For writeback requests, bus can accept another request from the same core after instead of servicing other cores' requests
- For i in `[0, N_CORES-1]`, `i != gidx`:
    - `snoop_inst[i] = {reqs[gidx].addr, reqs[gidx].data, reqs[gidx].wen}`
    - `snoop_inv[i] = inv_reqs[gidx]`
- For k in `[0, N_CORES-1]`:
    - `snoop_transfer[didx].transfer = 0` 
- `snoop_transfer[didx] = curr_transfer`
- `addr = gnt_addr`
- `data = gnt_data`
- `wen = gnt_wen`
- One cycle after main memory is addressed:
    - `mem_resp[gidx].valid = 1`
    - `mem_resp[gidx].dout = dout`