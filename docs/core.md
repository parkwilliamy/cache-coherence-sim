# Core

Fetches instructions from its instruction cache and feeds them to its cache controller. All bus-side signals pass straight through to `cache_ctrl` (see [cache_ctrl.md](./cache_ctrl.md)).

## Storage

| Register | Width | Meaning |
|---|---|---|
| `icache` | `ICACHE_SIZE x INST_WIDTH` = 16 | instruction cache |
| `pc` | `PC_WIDTH` = 3 | load pointer during LOAD, program counter during RUN |

19 flops, plus the 10 of `cache_ctrl`. `local_inst` is read combinationally from `icache`, so no current-instruction register is needed.

## Behaviour

- Reset: `pc = 0`.
- `icache_load`: `icache[pc[$clog2(ICACHE_SIZE)-1:0]] <= load_inst; pc <= pc + 1`. The MCU sends exactly `ICACHE_SIZE` instructions per core.
- `start`: `pc <= 0`.
- `local_valid = run && pc != ICACHE_SIZE`
- `local_inst = icache[pc[$clog2(ICACHE_SIZE)-1:0]]`
- `inst_done` (from `cache_ctrl`): `pc <= pc + 1`
- `core_done = pc == ICACHE_SIZE`, only meaningful while `run`; the decoder only looks at it then.
- `lines = cache_ctrl.cache`, for readback.

Every core executes exactly `ICACHE_SIZE` instructions in load order. A slot that was never loaded holds 0, a read of address 0. The cache controller keeps snooping after the core has finished, so the final cache states reflect everything the other core did afterwards.
