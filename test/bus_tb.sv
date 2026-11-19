`timescale 1ns/1ps
`default_nettype none

import top_params::*;

module bus_tb (
    input  logic clk,
    input  logic rst_n,
    input  logic [N_CORES-1:0] req,
    input  logic [2*N_CORES-1:0] req_type,
    input  logic [N_CORES*ADDR_WIDTH-1:0] req_addr,
    input  logic [N_CORES*DATA_WIDTH-1:0] req_data,
    input  logic [N_CORES-1:0] snoop_hit,
    input  logic [N_CORES-1:0] snoop_owner,
    input  logic [N_CORES*DATA_WIDTH-1:0] snoop_data,
    input  logic [1:0] protocol,
    output logic [N_CORES-1:0] done,
    output logic [N_CORES-1:0] snoop_valid,
    output logic [1:0] snoop_type,
    output logic [ADDR_WIDTH-1:0] snoop_addr,
    output logic shared,
    output logic [DATA_WIDTH-1:0] resp_data,
    output logic mem_we,
    output logic [ADDR_WIDTH-1:0] mem_addr,
    output logic [DATA_WIDTH-1:0] mem_din
);
    bus_if bus_if_inst[N_CORES] ();
    mem_if mem_if_inst ();

    for (genvar i = 0; i < N_CORES; i++) begin : gen_bus
        assign bus_if_inst[i].req = req[i];
        assign bus_if_inst[i].req_type = req_type_t'(req_type[i*2+:2]);
        assign bus_if_inst[i].addr = req_addr[i*ADDR_WIDTH+:ADDR_WIDTH];
        assign bus_if_inst[i].data = req_data[i*DATA_WIDTH+:DATA_WIDTH];
        assign bus_if_inst[i].snoop_hit = snoop_hit[i];
        assign bus_if_inst[i].snoop_owner = snoop_owner[i];
        assign bus_if_inst[i].snoop_data = snoop_data[i*DATA_WIDTH+:DATA_WIDTH];
        assign done[i] = bus_if_inst[i].done;
        assign snoop_valid[i] = bus_if_inst[i].snoop_valid;
    end

    assign snoop_type = bus_if_inst[0].snoop_type;
    assign snoop_addr = bus_if_inst[0].snoop_addr;
    assign shared = bus_if_inst[0].resp_shared;
    assign resp_data = bus_if_inst[0].resp_data;
    assign mem_we = mem_if_inst.we;
    assign mem_addr = mem_if_inst.addr;
    assign mem_din = mem_if_inst.din;

    bus dut (
        .clk(clk), .rst_n(rst_n), .bus(bus_if_inst), .mem(mem_if_inst.writer),
        .protocol(protocol)
    );
endmodule
