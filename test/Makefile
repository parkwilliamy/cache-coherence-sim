# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
# RTL tests need Verilator for the SystemVerilog sources. The gate-level test
# (GATES=yes) runs in the Tiny Tapeout gl_test action, which only installs Icarus
# Verilog and also runs a plain `make clean` there, so fall back to Icarus
# whenever Verilator is not installed.
ifeq ($(GATES),yes)
SIM ?= icarus
else ifeq ($(shell command -v verilator),)
SIM ?= icarus
endif
SIM ?= verilator
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
# RTL sources. The gds flow builds from src/project.v, which sv2v generates from
# the .sv files (run `make sv2v` in the repo root). Tests run on the .sv files by
# default; `make SV2V=1` runs the same tests on the generated project.v.
ifeq ($(SV2V),1)
PROJECT_SOURCES += project.v
# generated code trips Verilator style warnings (widths, shadowed names)
COMPILE_ARGS    += -Wno-fatal
else
PROJECT_SOURCES += top_params.sv
PROJECT_SOURCES += interfaces.sv
PROJECT_SOURCES += bus.sv
PROJECT_SOURCES += decoder.sv
PROJECT_SOURCES += cache_ctrl.sv
PROJECT_SOURCES += core.sv
PROJECT_SOURCES += main_mem.sv
PROJECT_SOURCES += tt_um_cache_coherence_sim.sv
endif

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
COMPILE_ARGS    += -Wno-fatal
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

# Code coverage (test requirement 1.4, decoder states and transitions):
#   make CODE_COVERAGE=1        build with Verilator coverage, write coverage.dat
#   make code-coverage-report   annotate the sources into coverage_annotated/
# Verilator only. It gets its own build directory because cocotb does not rebuild
# when only the flags change.
ifeq ($(CODE_COVERAGE),1)
ifeq ($(SIM),verilator)
SIM_BUILD				= sim_build/rtl_cov
EXTRA_ARGS      += --coverage
endif
endif
else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Verilator needs --timing for the delays in tb.v
ifeq ($(SIM),verilator)
COMPILE_ARGS    += --timing
endif

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
VERILOG_SOURCES += $(PWD)/cache_ctrl_tb.sv
VERILOG_SOURCES += $(PWD)/bus_tb.sv
VERILOG_SOURCES += $(PWD)/decoder_tb.sv
VERILOG_SOURCES += $(PWD)/main_mem_tb.sv
VERILOG_SOURCES += $(PWD)/core_tb.sv
TOPLEVEL = tb

# List test modules to run, separated by commas and without the .py suffix:
# test_coverage_report must stay last: it reports the functional coverage of every
# test that ran before it.
COCOTB_TEST_MODULES = test,test_bus,test_decoder,test_main_mem,test_core,test_cache_ctrl,test_coverage_report

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: code-coverage-report
code-coverage-report:
	verilator_coverage --annotate coverage_annotated --annotate-min 1 coverage.dat
