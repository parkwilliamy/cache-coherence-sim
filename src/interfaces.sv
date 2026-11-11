`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off DECLFILENAME */
/* verilator lint_off IMPORTSTAR */
import top_params::*;

// Interfaces between modules, one modport per side. Spec: docs/uarch.md.
// Where an interface is instantiated once per core, the signals marked
// "broadcast" carry the same value in every instance.
// Use package-qualified names here; the TinyTapeout Yosys parser rejects imports in interfaces.

// decoder <-> core, one per core
interface dec_if;
    logic  start;        // 1-cycle pulse; the core resets pc
    logic  run;          // high during RUN
    logic  icache_load;  // write load_inst into icache[pc] this cycle
    top_params::inst_t load_inst;    // instruction being loaded (broadcast)
    logic  core_done;    // pc == ICACHE_SIZE
    top_params::line_t lines [top_params::DCACHE_SIZE];  // the data cache, for readback

    modport decoder (output start, run, icache_load, load_inst,
                     input  core_done, lines);
    modport core    (input  start, run, icache_load, load_inst,
                     output core_done, lines);
endinterface

// core <-> bus, one per core
interface bus_if;
    // driven by the core
    logic                  req;          // request valid; held until done
    top_params::req_type_t req_type;
    logic [top_params::ADDR_WIDTH-1:0] addr;
    logic [top_params::DATA_WIDTH-1:0] data;
    logic                  snoop_hit;    // combinational response to the current snoop
    logic                  snoop_owner;
    logic [top_params::DATA_WIDTH-1:0] snoop_data;

    // driven by the bus
    logic                  done;         // this core's transaction completes this cycle
    logic                  snoop_valid;  // this core must snoop this cycle
    top_params::req_type_t snoop_type;   // the transaction on the bus (broadcast)
    logic [top_params::ADDR_WIDTH-1:0] snoop_addr;   // (broadcast)
    logic                  resp_shared;  // sampled by the requester at done (broadcast)
    logic [top_params::DATA_WIDTH-1:0] resp_data;    // (broadcast)

    modport core (output req, req_type, addr, data, snoop_hit, snoop_owner, snoop_data,
                  input  done, snoop_valid, snoop_type, snoop_addr, resp_shared, resp_data);
    modport bus  (input  req, req_type, addr, data, snoop_hit, snoop_owner, snoop_data,
                  output done, snoop_valid, snoop_type, snoop_addr, resp_shared, resp_data);
endinterface

// writer <-> main memory. The decoder (during LOAD) and the bus are both
// writers; main_mem has one instance of each and selects on loading.
interface mem_if;
    logic                  we;    // write din to mem[addr] at the clock edge
    logic [top_params::ADDR_WIDTH-1:0] addr;
    logic [top_params::DATA_WIDTH-1:0] din;
    logic [top_params::DATA_WIDTH-1:0] dout;  // mem[addr], combinational

    modport writer (output we, addr, din, input  dout);
    modport memory (input  we, addr, din, output dout);
endinterface

// core <-> cache controller, inside core
interface exec_if;
    logic  local_valid;  // icache[pc] is valid: running and not finished
    top_params::inst_t local_inst;
    logic  inst_done;    // the instruction completed this cycle; the core increments pc

    modport core       (output local_valid, local_inst, input  inst_done);
    modport cache_ctrl (input  local_valid, local_inst, output inst_done);
endinterface

/* verilator lint_off DECLFILENAME */
/* verilator lint_off IMPORTSTAR */
