# Encodings

## Instructions (`inst_t`)

| Field | ADDR | DATA | OP | 
|----|----|----|----|
| Bit Width | `ADDR_WIDTH`| `DATA_WIDTH` | 1 bit |

- `inst.addr` is address to read from or write to in main memory
- `inst.data` is data to write to memory (only for write instructions)
- `inst.op` is instruction type: 0 for reads and 1 for writes
- Each line of program memory holds one memory request

## Cache Lines (`line_t`)

| Field | ADDR | DATA | STATE | 
|----|----|----|----|
| Bit Width | `ADDR_WIDTH`| `DATA_WIDTH` | 3 bits |

- `line.addr` is the line address from main memory
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

