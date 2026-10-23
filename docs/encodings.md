# Encodings

## Instructions (`inst_t`)

| Field | ADDR | DATA | OP | 
|----|----|----|----|
| Bit Width | `ADDR_WIDTH`| `DATA_WIDTH` | 1 bit |

- `inst.addr` is address to read from or write to in main memory
- `inst.data` is data to write to memory (only for write instructions)
- `inst.op` is instruction type: 0 for reads and 1 for writes
- Each line in the instruction cache holds one memory request

## Invalidate Requests (`inv_t`)

| Field | ADDR | INV | 
|----|----|----|
| Bit Width | `ADDR_WIDTH` | 1 bit |

- `inv.inv` is invalidate signal placed on bus
- `inv.addr` is address of cache line to invalidate

## Transfer Requests (`transfer_t`)

| Field | DATA | ADDR | TRANSFER |
|----|----|----|----|
| Bit Width | `DATA_WIDTH` | `ADDR_WIDTH` | 1 bit |

- `transfer.transfer` is cache to cache transfer flag
- `transfer.addr` is the address to be read from a memory request that needs to be aborted
- `transfer.data` is the data that needs to be written to the requesting core's cache

## Cache Lines (`line_t`)

| Field | TAG | DATA | STATE | 
|----|----|----|----|
| Bit Width | `TAG_WIDTH`| `DATA_WIDTH` | 3 bits |

- `line.tag` is the line tag 
- `line.data` is the cache line data
    - Due to space constraints, a line contains one word of data unlike typical caches which hold multiple data words in a single cache line
- `line.state` is the cache line's coherence state (see below)

### Line States

- `INVALID`
    - Cache line has stale data
    - State `3'b000`
- `SHARED`
    - Cache line is present in other cores as well
    - State `3'b001`
- `MODIFIED`
    - Cache line has been written to; line is dirty
    - State `3'b010`
- `EXCLUSIVE`
    - Cache line only exists in this cache
    - State `3'b011`
- `OWNER`
    - Cache line has been written to and must be shared with other cores that read it
    - State `3'b100`

