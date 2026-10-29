# Encodings

Packed structs list fields MSB first.

## Instruction (`inst_t`), `INST_WIDTH = ADDR_WIDTH + DATA_WIDTH + 1`

| Field | `addr` | `data` | `op` |
|---|---|---|---|
| Width | `ADDR_WIDTH` | `DATA_WIDTH` | 1 |

- `op`: 0 = read, 1 = write
- `data`: value to write (ignored by reads)
- Loaded from the pins as `{req_addr, req_data, cmd[0]}`

## Cache line (`line_t`), `LINE_WIDTH = TAG_WIDTH + DATA_WIDTH + 3`

| Field | `tag` | `data` | `v` | `d` | `x` |
|---|---|---|---|---|---|
| Width | `TAG_WIDTH` | `DATA_WIDTH` | 1 | 1 | 1 |

The state is three flags, not an enumeration:

- `v` valid: the line holds address `{tag, index}`
- `d` dirty: memory is stale, this cache must eventually write the line back
- `x` exclusive: no other cache holds the line, so a write needs no bus transaction

| State | `v` | `d` | `x` | Code | Meaning |
|---|---|---|---|---|---|
| INVALID | 0 | 0 | 0 | `000` | |
| SHARED | 1 | 0 | 0 | `100` | clean; other copies may exist |
| EXCLUSIVE | 1 | 0 | 1 | `101` | clean; only copy |
| OWNER | 1 | 1 | 0 | `110` | dirty; SHARED copies may exist; this cache supplies the data |
| MODIFIED | 1 | 1 | 1 | `111` | dirty; only copy |

Codes `001`, `010`, `011` never occur. `tag` and `data` of an INVALID line are unspecified.

## Bus request type (`req_type_t`)

| Type | Code | Issued for | Snooper with a matching valid line | Memory |
|---|---|---|---|---|
| `RD` | `00` | read miss | `x <= 0`; `d <= d && o_en` (M→O, or M→S with memory updated) | read, unless an OWNER/MODIFIED line supplies the data and O is enabled |
| `INV` | `01` | write miss, or write hit on S/O | `v, d, x <= 0` | none |
| `WB` | `10` | eviction of a dirty line | no change | written |

`11` is unused. Bit 0 means "invalidates other copies", bit 1 means "writes memory".

## Protocol select (`protocol[1:0] = ui_in[4:3]`)

Read by the cores and the bus during RUN only; during LOAD the same pins carry command payload. The MCU drives the protocol together with the `start` command, whose payload bits are don't-care, and holds it until `resp_valid = 1`. The hardware decodes the pins into two enables, which the rest of the spec uses:

- `e_en = protocol[1] || protocol[0]`: EXCLUSIVE may be entered
- `o_en = protocol[1]`: OWNER may be entered

| `protocol` | Protocol | `e_en` | `o_en` |
|---|---|---|---|
| `00` | MSI | 0 | 0 |
| `01` | MESI | 1 | 0 |
| `10` | MOESI | 1 | 1 |
| `11` | reserved; behaves as MOESI | 1 | 1 |

## MCU pin words

Pin meaning depends on the decoder phase. `in[15:0] = {uio_in, ui_in}` and `out[15:0] = {uio_out, uo_out}`; fields are packed from bit 0 upward, unused input bits are ignored and unused output bits are 0. "Default" is the default configuration.

### LOAD: command word on `in` (`uio_oe = 0`)

| Field | `req_valid` | `cmd` | `core_sel` | `req_addr` | `req_data` |
|---|---|---|---|---|---|
| Width | 1 | 2 | `$clog2(N_CORES)` | `ADDR_WIDTH` | `DATA_WIDTH` |
| Starts at | `in[0]` | `in[1]` | `in[3]` | after `core_sel` | after `req_addr` |
| Default | `ui_in[0]` | `ui_in[2:1]` | `ui_in[3]` | `ui_in[5:4]` | `ui_in[6]` |

The command is executed in the cycle in which `req_valid = 1`:

| `cmd` | Command | Payload used |
|---|---|---|
| `00` | load read instruction `{req_addr, -, 0}` into core `core_sel` | `core_sel`, `req_addr` |
| `01` | load write instruction `{req_addr, req_data, 1}` into core `core_sel` | `core_sel`, `req_addr`, `req_data` |
| `10` | write `req_data` to memory word `req_addr` | `req_addr`, `req_data` |
| `11` | start the run | none |

Limit: `3 + $clog2(N_CORES) + ADDR_WIDTH + DATA_WIDTH <= 16`.

### RUN

`protocol = ui_in[4:3]`; every other input is ignored. The MCU keeps `ui_in[0] = 0` so that the first READ cycles do not advance the readback.

### READ: result word on `out` (`uio_oe = 8'hFF`), `rd_next = ui_in[0]`

| Field | `resp_valid` | `cycle_count` | `line` |
|---|---|---|---|
| Width | 1 | `CYCLE_WIDTH` | `LINE_WIDTH` |
| Starts at | `out[0]` | `out[1]` | `out[CYCLE_WIDTH + 1]` |
| Default | `uo_out[0]` | `uo_out[7:1]` | `uio_out[4:0]` |

Limit: `1 + CYCLE_WIDTH + LINE_WIDTH <= 16`. `rd_next = 1` advances to the next line at the clock edge.

## Readback line

`{tag, data, v, d, x}`, MSB first. Lines come out in order `core 0 line 0, core 0 line 1, core 1 line 0, core 1 line 1` (position = `core * DCACHE_SIZE + line`). The line index is not output; it is the position within the core, and the full address of a valid line is `{tag, index}`. The position wraps after the last line, so the sequence can be read again.

## Cycle count

`CYCLE_WIDTH = 7` bits, unsigned, saturating at 127. Number of clock cycles the decoder spent in the RUN phase. Visible on `uo_out` in every phase; final once `resp_valid = 1`.
