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

# The `default_nettype none lines sv2v copies from the sources are replaced by a
# single `default_nettype wire. LibreLane reads the file with Yosys >= 0.6x and
# -noautowire, and under default_nettype none that Yosys rejects sv2v's
# hierarchical references into the interface arrays ("Identifier is implicitly
# declared"). The .sv sources keep `default_nettype none, so implicit nets are
# still caught there.
SV2V := { echo '`default_nettype wire'; \
	sv2v --top $(TOP) $(SV_SOURCES) | grep -v '^`default_nettype none$$'; }

sv2v:
	$(SV2V) > src/project.v.tmp
	mv src/project.v.tmp src/project.v

sv2v-check:
	$(SV2V) | diff -u src/project.v - \
		|| { echo "src/project.v is out of date: run 'make sv2v' and commit it"; exit 1; }
