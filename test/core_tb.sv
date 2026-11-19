`timescale 1ns/1ps
`default_nettype none

import top_params::*;

module core_tb (
    input  logic clk,
    input  logic rst_n,
    input  logic dec_start,
    input  logic dec_run,
    input  logic dec_icache_load,
    input  logic [INST_WIDTH-1:0] load_inst,
    input  logic [1:0] protocol,
    input  logic bus_done,
    input  logic bus_snoop_valid,
    input  logic [1:0] bus_snoop_type,
    input  logic [ADDR_WIDTH-1:0] bus_snoop_addr,
    input  logic bus_resp_shared,
    input  logic [DATA_WIDTH-1:0] bus_resp_data,
    output logic core_done,
    output logic bus_req,
    output logic [1:0] bus_req_type,
    output logic [ADDR_WIDTH-1:0] bus_req_addr,
    output logic [DATA_WIDTH-1:0] bus_req_data
);
    dec_if dec_if_inst ();
    bus_if bus_if_inst ();

    assign dec_if_inst.start = dec_start;
    assign dec_if_inst.run = dec_run;
    assign dec_if_inst.icache_load = dec_icache_load;
    assign dec_if_inst.load_inst = inst_t'(load_inst);
    assign core_done = dec_if_inst.core_done;

    assign bus_if_inst.done = bus_done;
    assign bus_if_inst.snoop_valid = bus_snoop_valid;
    assign bus_if_inst.snoop_type = req_type_t'(bus_snoop_type);
    assign bus_if_inst.snoop_addr = bus_snoop_addr;
    assign bus_if_inst.resp_shared = bus_resp_shared;
    assign bus_if_inst.resp_data = bus_resp_data;
    assign bus_req = bus_if_inst.req;
    assign bus_req_type = bus_if_inst.req_type;
    assign bus_req_addr = bus_if_inst.addr;
    assign bus_req_data = bus_if_inst.data;

    core dut (
        .clk(clk), .rst_n(rst_n), .dec(dec_if_inst.core),
        .bus(bus_if_inst.core), .protocol(protocol)
    );
endmodule
