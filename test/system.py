"""System-level tests: whole programs on the full chip, driven over the pins.

test_all_programs is test requirement 5.4 (all_programs_tested). A program is
the content of one instruction cache: ICACHE_SIZE instructions, each one of the
cov.INST_KINDS that the decoder can load. Every core runs every program:

    runs = len(INST_KINDS) ** ICACHE_SIZE        (12^4 = 20,736 by default)

Each run is reset -> load -> start -> wait for resp_valid, because the decoder
cannot leave READ without a reset.

What is exhaustive and what is not:
- Exhaustive: the programs of each core. Core c runs order[c][run], and each
  order[c] is a permutation of all programs.
- Sampled: which programs run together, the initial memory and the protocol.
  The joint space is runs^N_CORES * 2^(MEM_SIZE * DATA_WIDTH) * 3 (about 1e19 by
  default). The permutations are independent shuffles, memory is random and the
  protocol rotates with the run number.

The stimulus is seeded by cocotb, so each regression explores new program
pairings. A failing run logs its programs, memory and protocol; the whole
sequence reproduces with COCOTB_RANDOM_SEED=<the seed cocotb logs at startup>.

SYSTEM_RUNS=<n> limits the test to the first n runs, a random sample of the
programs. Builds without the functional coverage monitor (gate-level, sv2v)
default to SAMPLE_RUNS: without the monitor a run only checks that the chip
finishes, and there is no coverage to close.
"""

import itertools
import os
import random
import time

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb_coverage.coverage import coverage_db

import coverage as cov  # test/coverage.py: functional coverage model and assertions
from test import RD_OP, WR_OP, run_programs

PROTOCOLS = (cov.MSI, cov.MESI, cov.MOESI)
PROTOCOL_NAMES = {cov.MSI: "MSI", cov.MESI: "MESI", cov.MOESI: "MOESI"}
SAMPLE_RUNS = 500     # default number of runs on builds without coverage
RESET_CYCLES = 2
LOG_EVERY = 2000      # runs between progress messages


def all_instructions():
    """Every instruction the decoder can load, as (op, addr, data), in the order
    of cov.INST_KINDS. Reads carry no data: the decoder zeroes it."""
    reads = [(RD_OP, addr, 0) for addr in range(cov.MEM_SIZE)]
    writes = [(WR_OP, addr, data)
              for addr in range(cov.MEM_SIZE) for data in range(1 << cov.DATA_WIDTH)]
    return reads + writes


def all_programs():
    """Every program: one tuple of ICACHE_SIZE instructions per bin of 5.4."""
    return list(itertools.product(all_instructions(), repeat=cov.ICACHE_SIZE))


def program_orders(programs, rng):
    """One independent shuffle of the programs per core. Run i loads
    order[core][i], so every core runs every program exactly once."""
    orders = []
    for _ in range(cov.N_CORES):
        order = list(programs)
        rng.shuffle(order)
        orders.append(order)
    return orders


def random_memory(rng):
    """Initial memory contents. Words left out keep their reset value, 0."""
    words = {addr: rng.getrandbits(cov.DATA_WIDTH) for addr in range(cov.MEM_SIZE)}
    return {addr: data for addr, data in words.items() if data}


def describe(program):
    return " ".join(f"W{addr}={data}" if op == WR_OP else f"R{addr}"
                    for op, addr, data in program)


def run_count(total, monitor):
    """Number of runs: SYSTEM_RUNS if set, else everything when the coverage
    monitor is attached and SAMPLE_RUNS when it is not."""
    requested = os.environ.get("SYSTEM_RUNS")
    if requested:
        return max(1, min(int(requested), total))
    return total if monitor is not None else min(SAMPLE_RUNS, total)


async def short_reset(dut):
    """Back to LOAD with empty caches. Inputs change just after a rising edge, as
    the coverage monitor requires."""
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, RESET_CYCLES)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_all_programs(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    monitor = cov.start_coverage(dut)

    rng = random.Random(cocotb.RANDOM_SEED)  # per test, derived from COCOTB_RANDOM_SEED
    programs = all_programs()
    orders = program_orders(programs, rng)
    runs = run_count(len(programs), monitor)
    cocotb.log.info("%d of %d runs", runs, len(programs))

    started = time.monotonic()
    longest = 0
    for run in range(runs):
        loaded = [order[run] for order in orders]
        memory = random_memory(rng)
        protocol = PROTOCOLS[run % len(PROTOCOLS)]

        await short_reset(dut)
        passed = False
        try:
            cycles = await run_programs(dut, loaded, memory, protocol)
            if monitor is not None:
                arcs = monitor.model.unexpected_arcs
                assert not arcs, f"state transitions outside the protocol: {arcs}"
            passed = True
        finally:
            # Also reached when the monitor task fails an assertion (5.1, 5.2,
            # 5.5, 5.6, ...): cocotb then cancels this task inside run_programs.
            if not passed:
                cocotb.log.error("run %d failed: protocol %s, memory %s",
                                 run, PROTOCOL_NAMES[protocol], memory)
                for core, program in enumerate(loaded):
                    cocotb.log.error("  core %d: %s", core, describe(program))
        longest = max(longest, cycles)

        if (run + 1) % LOG_EVERY == 0:
            cocotb.log.info("%d/%d runs, %.0f s", run + 1, runs, time.monotonic() - started)

    cocotb.log.info("%d runs in %.0f s, longest run %d cycles",
                    runs, time.monotonic() - started, longest)
    await ClockCycles(dut.clk, 2)

    if monitor is None:  # gate-level or sv2v build: the runs above are the test
        return
    cross = coverage_db["system.program_cross"]
    cocotb.log.info("5.4 all_programs_tested: %d/%d programs", cross.coverage, cross.size)
    if runs == len(programs):
        missed = [kinds for kinds, hits in cross.detailed_coverage.items() if not hits]
        assert not missed, f"{len(missed)} programs never ran, e.g. {missed[:3]}"
