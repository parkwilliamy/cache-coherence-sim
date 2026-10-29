# Design Decisions

Each entry: what was decided and why. Numbered so they can be referenced in reviews.

## Protocol

1. **Write-validate.** Write-back, write-allocate, no fetch on write. A write miss issues `INV` only and the line becomes MODIFIED with the written data. Possible because a line is one word, so a write replaces the whole line; fetching first would move data the writer is about to overwrite.
2. **Line state as flags `{v, d, x}`.** Valid, dirty, exclusive. Every transition is a one- or two-bit update, hit detection uses `v` directly, eviction uses `d`, silent writes use `x`. An enumerated state would need decoding for each of those tests.
3. **Protocol decoded into two enables.** `e_en = protocol != 0` allows EXCLUSIVE, `o_en = protocol[1]` allows OWNER, so 00 = MSI, 01 = MESI, 10 = MOESI. `11` is reserved and behaves as MOESI; there is no fourth protocol. A snooped M line becomes O when `o_en`, else S with the bus writing its data to memory.
4. **Only dirty lines supply data.** S/E snoopers report `shared` but memory supplies the word. This is what makes OWNER measurable: with O, repeated read misses to a dirty line cost 1 cycle; without O they cost a memory access.
5. **Snooped M→S writes memory in the same transaction.** S is clean, so without this the dirty value would never reach memory. The write is charged memory latency, which is the realistic MESI cost that MOESI avoids.
6. **"No other cache has the line" = `!resp_shared`.** Computed by the bus as the OR of the snoopers' `snoop_hit`; the requester's own cache is excluded.
7. **Snooped `WB` does nothing.** A dirty line is M or O; S copies next to an O line stay correct after the writeback.

## Bus and timing

8. **Three transaction types `RD`, `INV`, `WB`; the snoop is the transaction.** Snoopers see `{req_type, addr}` and answer with combinational `snoop_hit`, `snoop_owner`, `snoop_data`. Broadcasting the transaction rather than the requester's instruction means a snooper needs no knowledge of the requester's state, and every invalidate and data transfer is a bus transaction with defined timing.
9. **Memory latency model.** A transaction that touches memory occupies the bus for `1 + MEM_LATENCY` cycles; `INV` and owner-served `RD` take 1. Memory itself is written at grant; the latency is pure occupancy. Without it every transaction would cost the same and the protocols would be indistinguishable.
10. **No request FSM in the cache controller.** The request is recomputed every cycle from the instruction and the line; the requester commits at `done`, snoopers at grant. Correct because nothing can change a line matching the transaction address between grant and done (see bus.md). Avoids per-core FSM state, latched requests, and any race between an upgrade and a snoop of the same line.
11. **Snoop priority.** A snooped core does no local work in the grant cycle, so one next-state computation per controller suffices and a local write can never race a snoop on the same line.
12. **Round-robin without a writeback privilege.** After a `WB` the slot is invalid, so the retried miss is an ordinary request. The arbiter holds its grant for the whole transaction.
13. **Nothing latched in the bus but `wait`, `gidx`, `last`.** The requester holds its request lines; the snoopers' responses are stable; memory already holds the owner's data when the requester samples `resp_data` at done.

## Decoder, core and MCU interface

14. **Protocol read from the pins, not registered.** Saves a register and the load-phase logic. `ui_in[4:3]` is only read during RUN, so during LOAD the same pins carry command payload; the MCU drives the protocol with the start command (whose payload is don't-care) and holds it.
15. **`pc` doubles as the load pointer.** Counts loads during LOAD, is cleared by `start`, counts completed instructions during RUN; `pc == ICACHE_SIZE` means finished. One counter serves both phases and doubles as the done flag.
16. **Readback is a counter in the decoder.** `rd_idx` selects a line out of all cores' lines; one line per `rd_next`. The cores need no readback logic, and the line index is not output because the MCU knows the order.
17. **Single-step clocking only where it matters.** The MCU steps the clock during LOAD (one command per clock) and may free-run during RUN. Readback advances only on the `rd_next` strobe, so the clock may still be running when READ begins and no line can be skipped. Without the strobe, a free-running clock would overrun the readback before the MCU could stop it.
18. **Pinout: `uio` direction follows the phase.** `uio_oe = 0` during LOAD and RUN and `8'hFF` during READ, giving 16 input bits for commands and 16 output bits for results. Loading, memory writes and start are one 2-bit `cmd` field, and `protocol` shares pins with the command payload. Input and output words are packed from bit 0 upward so the layout follows the parameters. Limits: `3 + $clog2(N_CORES) + ADDR_WIDTH + DATA_WIDTH <= 16` and `1 + CYCLE_WIDTH + LINE_WIDTH <= 16`. With a fixed `uio` direction only 10 input bits would be available, which the default configuration already uses up. The MCU must release its `uio` drivers after the start command. `cycle_count` is `CYCLE_WIDTH` bits and saturates, so an overlong run reads as the maximum rather than wrapping.
19. **One run per reset.** Phases are LOAD → RUN → READ; READ is terminal and `rd_idx` wraps, so the lines can be re-read but nothing can restart the run or the cycle counter by accident.
20. **Memory write port muxed at the top.** Decoder during LOAD, bus otherwise, so neither needs to know about the other.

## Storage

77 flops, 32 of which are the instruction caches (see [uarch.md](./uarch.md)).

Further cuts, not taken: streaming instructions from the MCU instead of storing them (saves 38 flops, but needs an 8-pin per-core instruction interface and a lockstep MCU loop); fixed priority arbitration instead of round-robin (1 flop, biases the comparison).

## Pin budget

| Phase | Direction | Available | Used by default config | Limit |
|---|---|---|---|---|
| LOAD | in | 16 | 7 | `3 + $clog2(N_CORES) + ADDR_WIDTH + DATA_WIDTH <= 16` |
| RUN | in | 8 (`ui_in`) | 2 | `protocol` only |
| READ | out | 16 | 13 | `1 + CYCLE_WIDTH + LINE_WIDTH <= 16` |
| READ | in | 8 (`ui_in`) | 1 | `rd_next` only |

Every configuration that fits one tile's area fits the input limit. The output limit binds first for wide data (for example 4 cores with `DATA_WIDTH = 4` and `CYCLE_WIDTH = 8` needs 18 output bits). Not taken, available if needed: send `cycle_count` as item 0 of the readback stream instead of alongside each line, which relaxes the output limit to `1 + max(CYCLE_WIDTH, LINE_WIDTH) <= 16` at the cost of one mux and one extra readback step.
