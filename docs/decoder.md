# Decoder

Loads the program and main memory from the MCU, starts the run, counts cycles and returns the cache lines. It owns the raw pin vectors `ui_in`, `uio_in`, `uo_out`, `uio_out` and `uio_oe`; what each pin means depends on the phase (bit formats in [encodings.md](./encodings.md), "MCU pin words"). The coherence protocol is read from `ui_in[4:3]` by the cores and the bus directly, during RUN only, and is not registered.

## Storage

| Register | Width | Meaning |
|---|---|---|
| `phase` | 2 | LOAD, RUN, READ |
| `rd_idx` | `RD_WIDTH` = 2 | readback position |
| `cycle_count` | `CYCLE_WIDTH` = 7 | saturating cycle counter |

11 flops.

## Phases

| Phase | Entered | Behaviour | Left when |
|---|---|---|---|
| LOAD | reset | `loading = 1`; `uio_oe = 0` (all `uio` pins are inputs); executes the command on the pins each cycle (below) | `start` command → RUN; `start` is pulsed in that cycle |
| RUN | | `run = 1`; `cycle_count` increments every cycle, saturating; every input except `protocol` is ignored | `&core_done` → READ |
| READ | | `resp_valid = 1`; `uio_oe = 8'hFF` (all `uio` pins are outputs); `line_out = lines[rd_idx / DCACHE_SIZE][rd_idx % DCACHE_SIZE]`; `rd_idx <= rd_idx + 1` when `rd_next`, wrapping to 0 after the last line | never; reset only |

`cycle_count` ends up as the execution time plus one: the cycle in which the last instruction completes is followed by one RUN cycle in which the decoder sees `&core_done`. The offset is the same for every protocol.

READ is terminal, so the lines can be read back as many times as needed.

`lines[c][k]` above is `dec[c].lines[k]`, the unpacked array in each core's `dec_if`. An interface array cannot be indexed with a variable, so the decoder copies each `dec[c].lines` into a local `line_t all_lines[N_CORES][DCACHE_SIZE]` in a generate loop and indexes that with `rd_idx`.

Command decode, active in LOAD only:

```
start          = req_valid && cmd == 2'b11
icache_load[i] = req_valid && !cmd[1] && core_sel == i
load_inst      = {req_addr, req_data, cmd[0]}
mem_if.we      = req_valid && cmd == 2'b10
mem_if.addr    = req_addr
mem_if.din     = req_data
```

`uo_out` carries `{cycle_count, resp_valid}` in every phase, so the count can be watched during RUN. `uio_out` carries the line and is only driven in READ. `uio_oe` is 0 out of reset, so the design never drives `uio` while the MCU is loading.

## MCU protocol

The MCU steps the clock one cycle at a time (`tt.clock_project_once()`) during LOAD, because each clock executes one command. During RUN the clock may free-run. Readback advances only on `rd_next`, so it does not matter how many clocks pass between the end of the run and the first read.

`uio` is driven by the MCU during LOAD and by the ASIC from the first READ cycle. The MCU must stop driving its side of `uio` after the start command, before the run can finish, or the two will drive against each other.

1. Reset. Configure the MCU side of `uio` as outputs.
2. For each core `c` and slot `k = 0 .. ICACHE_SIZE-1`: `req_valid = 1, cmd = {0, op}, core_sel = c`, `req_addr/req_data` = instruction `k`; one clock.
3. For each address `a`: `req_valid = 1, cmd = 10, req_addr = a, req_data` = word; one clock.
4. `req_valid = 1, cmd = 11, ui_in[4:3] = protocol`; one clock. Then set `ui_in[0] = 0`, configure the MCU side of `uio` as inputs, and keep `ui_in[4:3]` as they are.
5. Clock, stepped or free-running, until `resp_valid = 1`. If free-running, stop the clock.
6. Read `cycle_count` and line 0 from the output word. Then `N_CORES * DCACHE_SIZE - 1` times: `rd_next = 1`, one clock, read the next line. Order: core 0 line 0, core 0 line 1, core 1 line 0, core 1 line 1.
7. Reset to run another program.
