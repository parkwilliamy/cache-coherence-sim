"""Last module of the regression (see COCOTB_TEST_MODULES in the Makefile).

Logs functional coverage per test requirement, accumulated over every test that
ran before it in this simulation, and writes functional_coverage.xml.
"""

import cocotb

import coverage as cov  # test/coverage.py


@cocotb.test()
async def report_functional_coverage(dut):
    if cov.coverage_supported():
        cov.report_coverage(cocotb.log.info)
