<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

The design models two cores with private instruction and data caches that share main memory. During **LOAD**, the host uploads instructions for each core and initializes memory through the input pins. It then selects MSI, MESI, or MOESI and starts the run.

During **RUN**, each core executes its uploaded instructions. The cache controllers issue read, invalidate, and write-back requests; a shared, round-robin bus arbitrates between them and broadcasts snoops so the caches maintain the selected coherence protocol. When both cores finish, **READ** signals that results are ready and returns the final cache lines one at a time.

See the [project proposal](proposal.md) for the design overview and pin-level workflow, and the [microarchitecture specification](uarch.md) for module responsibilities, interfaces, and configuration.

## How to test

Reset the design, then upload the instruction sequence one command per clock. Select the target core and instruction address for each instruction, and preload the required main-memory words. Start the run with the desired protocol selected, and keep the protocol pins stable until `resp_valid` is asserted.

After completion, read the cycle count and retrieve the final cache lines through the bidirectional pins. Pulse `rd_next` between lines; the default configuration returns core 0's lines followed by core 1's lines. Decode each line as `{tag, data, valid, dirty, exclusive}` and compare the valid lines and their coherence flags with the expected results for the uploaded program and selected protocol. The line's position identifies its cache index.

The RTL testbench can also be run from the `test` directory with `make -B`.

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any
