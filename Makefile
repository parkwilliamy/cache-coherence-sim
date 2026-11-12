# Generates src/project.v, the plain-Verilog file the Tiny Tapeout gds flow builds
# from, out of the SystemVerilog sources. Needs sv2v (https://github.com/zachjs/sv2v).
#
#   make sv2v        regenerate src/project.v
#   make sv2v-check  fail if src/project.v is out of date with the .sv sources

TOP := tt_um_cache_coherence_sim

# top_params.sv (the package) and interfaces.sv must come first.
SV_SOURCES := \
	src/top_params.sv \
	src/interfaces.sv \
	src/cache_ctrl.sv \
	src/decoder.sv \
	src/core.sv \
	src/main_mem.sv \
	src/bus.sv \
	src/tt_um_cache_coherence_sim.sv

.PHONY: sv2v sv2v-check

sv2v:
	sv2v --top $(TOP) $(SV_SOURCES) > src/project.v.tmp
	mv src/project.v.tmp src/project.v

sv2v-check:
	sv2v --top $(TOP) $(SV_SOURCES) | diff -u src/project.v - \
		|| { echo "src/project.v is out of date: run 'make sv2v' and commit it"; exit 1; }
