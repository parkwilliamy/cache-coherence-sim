# Microarchitecture

This file and the per-module files are the spec for the RTL. Bit-level formats are in [encodings.md](./encodings.md); the reasoning behind each choice is in [decisions.md](./decisions.md).

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| `N_CORES` | 2 | cores; each has an instruction cache, a data cache and a cache controller |
| `DCACHE_SIZE` | 2 | data cache lines per core (direct mapped, one word per line) |
| `ICACHE_SIZE` | 4 | instructions per core |
| `MEM_SIZE` | 4 | words of main memory |
| `DATA_WIDTH` | 1 | bits per word |
| `MEM_LATENCY` | 2 | extra bus cycles for a transaction that touches main memory (must be >= 1) |
| `CYCLE_WIDTH` | 7 | width of the saturating cycle counter |

Derived:

| Name | Value | Meaning |
|---|---|---|
| `ADDR_WIDTH` | `$clog2(MEM_SIZE)` = 2 | |
| `IDX_WIDTH` | `$clog2(DCACHE_SIZE)` = 1 | line index = `addr[IDX_WIDTH-1:0]` |
| `TAG_WIDTH` | `ADDR_WIDTH - IDX_WIDTH` = 1 | tag = `addr[ADDR_WIDTH-1:IDX_WIDTH]` |
| `INST_WIDTH` | `ADDR_WIDTH + DATA_WIDTH + 1` = 4 | |
| `LINE_WIDTH` | `TAG_WIDTH + DATA_WIDTH + 3` = 5 | |
| `PC_WIDTH` | `$clog2(ICACHE_SIZE) + 1` = 3 | `pc == ICACHE_SIZE` means the core has finished |
| `WAIT_WIDTH` | `$clog2(MEM_LATENCY + 1)` = 2 | bus latency counter |
| `RD_WIDTH` | `$clog2(N_CORES * DCACHE_SIZE)` = 2 | readback counter |

## Types

- `inst_t {addr, data, op}`
- `line_t {tag, data, v, d, x}`
- `req_type_t` = `RD`, `INV`, `WB` (2 bits)
- `e_en`, `o_en`: EXCLUSIVE/OWNER enables decoded from `protocol[1:0]` (see encodings.md)

## Structure

```
pins --> decoder <==dec_if[i]==> core[i] = { icache, pc, cache_ctrl { cache[DCACHE_SIZE] } }
         decoder --mem_if (write side, while loading)--+
                                                       +--mux--> main_mem
         core[i] <==bus_if[i]==> bus -------mem_if-----+
```

The coherence protocol lives entirely in each `cache_ctrl`; the bus only arbitrates, broadcasts and models memory latency.

## Interfaces

Each interface is a SystemVerilog `interface` with one modport per side. Signal widths are `ADDR_WIDTH` for `addr`, `DATA_WIDTH` for `data`, and 1 unless a type is given. Where an interface is instantiated once per core, the signals marked *broadcast* carry the same value in every instance.

### `dec_if`: decoder ↔ core, one per core

| Driven by | Signal | Meaning |
|---|---|---|
| decoder | `start` | 1-cycle pulse; the core resets `pc` |
| decoder | `run` | high during the RUN phase |
| decoder | `icache_load` | write `load_inst` into `icache[pc]` this cycle |
| decoder | `inst_t load_inst` | instruction being loaded (*broadcast*) |
| core | `core_done` | `pc == ICACHE_SIZE` |
| core | `line_t lines[DCACHE_SIZE]` | the data cache, for readback |

### `bus_if`: core ↔ bus, one per core

| Driven by | Signal | Meaning |
|---|---|---|
| core | `req` | request valid; held until `done` |
| core | `req_type_t req_type`, `addr`, `data` | the request (see [cache_ctrl.md](./cache_ctrl.md) Table 1) |
| core | `snoop_hit`, `snoop_owner`, `snoop_data` | combinational response to the current snoop |
| bus | `done` | this core's transaction completes this cycle |
| bus | `snoop_valid` | this core must snoop this cycle |
| bus | `req_type_t snoop_type`, `snoop_addr` | the transaction on the bus (*broadcast*) |
| bus | `resp_shared`, `resp_data` | response, sampled by the requester at `done` (*broadcast*) |

### `mem_if`: writer ↔ main memory

| Driven by | Signal | Meaning |
|---|---|---|
| writer | `we`, `addr`, `din` | write `din` to `mem[addr]` at the clock edge |
| memory | `dout` | `mem[addr]`, combinational |

Two writers exist: the decoder during LOAD (it ignores `dout`) and the bus otherwise. The top level muxes them on `loading`.

### `exec_if`: core ↔ cache controller, inside `core`

| Driven by | Signal | Meaning |
|---|---|---|
| core | `local_valid`, `inst_t local_inst` | `icache[pc]` while running and not finished |
| cache_ctrl | `inst_done` | the instruction completed this cycle; the core increments `pc` |

### Standalone signals

- `clk`, `rst_n`: every module; `rst_n` is asynchronous, active low, and every register resets to 0.
- `protocol[1:0] = ui_in[4:3]`: to every `core` and to the `bus`, not registered; meaningful during RUN only.
- `loading`: decoder to the top-level memory write mux.
- MCU pins: `ui_in`, `uio_in`, `uo_out`, `uio_out` and `uio_oe` belong to the decoder, which gives them phase-dependent meanings ([decoder.md](./decoder.md), [encodings.md](./encodings.md)); only `protocol` is sliced off at the top.

## Modules

| Module | Interfaces (side) | Other ports |
|---|---|---|
| `decoder` | `dec_if[N_CORES]` (decoder), `mem_if` (writer) | in: `ui_in[7:0], uio_in[7:0]`. out: `loading`; `uo_out[7:0], uio_out[7:0], uio_oe[7:0]` |
| `core` | `dec_if` (core), `bus_if` (core) | in: `protocol` |
| `cache_ctrl` | `exec_if` (cache_ctrl), `bus_if` (core), `dec_if.lines` | in: `protocol` |
| `bus` | `bus_if[N_CORES]` (bus), `mem_if` (writer) | in: `protocol` |
| `main_mem` | `mem_if` (memory) | `MEM_SIZE x DATA_WIDTH` register file |
| `tt_um_cache_coherence_sim` | none | pins to and from the decoder, `protocol = ui_in[4:3]`, the `mem_if` writer mux on `loading` |

`core` passes `bus_if` and `dec_if.lines` straight through to its `cache_ctrl`; the `icache` and `pc` logic in `core` uses only `dec_if` and `exec_if`.

## Storage budget

| Block | Flops |
|---|---|
| instruction caches, 2 x 4 x 4 | 32 |
| program counters, 2 x 3 | 6 |
| data caches, 2 x 2 x 5 | 20 |
| main memory, 4 x 1 | 4 |
| bus: `wait` 2, `gidx` 1, `last` 1 | 4 |
| decoder: `phase` 2, `rd_idx` 2, `cycle_count` 7 | 11 |
| **total** | **77** |
