# Bus

Arbitrates one transaction at a time, broadcasts it to the other caches as the snoop, collects their responses, drives main memory and models memory latency. It holds no addresses or data: the requester keeps its request lines stable for the whole transaction, and the snoop responses are recomputed from the caches every cycle.

## Storage

| Register | Width | Meaning |
|---|---|---|
| `wait` | `WAIT_WIDTH` | cycles left in the current transaction; 0 = idle |
| `gidx` | `$clog2(N_CORES)` | core being served while `wait != 0` |
| `last` | `$clog2(N_CORES)` | last core granted, for round-robin |

4 flops total.

## Combinational behaviour

```
o_en        = protocol[1]                                     (see encodings.md)
busy        = wait != 0
grant       = !busy && |req
g           = first requesting core after `last`, wrapping     (round-robin)
cur         = busy ? gidx : g
req_type, addr, data = request lines of core `cur`

snoop_type  = req_type
snoop_addr  = addr
snoop_valid[i] = grant && i != cur

shared      = OR over i != cur of snoop_hit[i]
owner       = OR over i != cur of snoop_owner[i]
owner_data  = snoop_data of the core with snoop_owner set (at most one; OR for 1-bit data)

served_by_owner = req_type == RD && owner && o_en
mem_access  = req_type == WB || (req_type == RD && !served_by_owner)

mem_if.addr = addr
mem_if.din  = req_type == WB ? data : owner_data
mem_if.we   = grant && (req_type == WB || (req_type == RD && owner && !o_en))

done[i]     = i == cur && (grant ? !mem_access : wait == 1)
resp_shared = shared
resp_data   = owner ? owner_data : mem_if.dout     (used by the requester in its done cycle)
```

Registers at the clock edge:

```
if (grant)               last <= g
if (grant && mem_access) gidx <= g; wait <= MEM_LATENCY
else if (busy)           wait <= wait - 1
```

## Transaction cost

| Kind | Data source | Cycles | Memory write |
|---|---|---|---|
| `INV` | - | 1 | - |
| `RD`, owner exists, O enabled | owner cache | 1 | - |
| `RD`, owner exists, O disabled | memory, after the owner's data is written to it | `1 + MEM_LATENCY` | at grant: `owner_data` |
| `RD`, no owner | memory | `1 + MEM_LATENCY` | - |
| `WB` | - | `1 + MEM_LATENCY` | at grant: requester's `data` |

Example, `RD` from memory with `MEM_LATENCY = 2`:

| Cycle | `wait` | Events |
|---|---|---|
| 0 | 0 | grant; `snoop_valid` to the other cores, which update at the end of the cycle; memory written if needed; `wait <= 2` |
| 1 | 2 | busy; no grants, no snoops |
| 2 | 1 | `done[cur]`; requester reads `resp_shared`/`resp_data` and updates at the end of the cycle |
| 3 | 0 | idle; next grant possible |

## Why the requester samples its response at done, not at grant

Between grant and done no other transaction runs and no snoop is issued, and the other core's local hits cannot change the validity or ownership of a line that matches the transaction address: such a line was snooped at grant, which left it in S, O or I, and writing an S/O line or allocating a line needs the bus. So `shared` and `owner` at done equal their values at grant, and in MSI/MESI the memory already holds the former owner's data. Nothing needs to be latched.

## Arbitration

Round-robin: priority starts at `last + 1`. With two cores the grant alternates whenever both request. A grant is held for the whole transaction. A core whose `WB` finishes requests its miss on the next cycle like any other request; no back-to-back privilege is needed, because the evicted slot is already invalid.
