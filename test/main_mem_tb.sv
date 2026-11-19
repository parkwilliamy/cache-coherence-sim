`timescale 1ns/1ps
`default_nettype none

import top_params::*;

module main_mem_tb (
    input  logic clk,
    input  logic rst_n,
    input  logic loading,
    input  logic dec_we,
    input  logic [ADDR_WIDTH-1:0] dec_addr,
    input  logic [DATA_WIDTH-1:0] dec_din,
    input  logic bus_we,
    input  logic [ADDR_WIDTH-1:0] bus_addr,
    input  logic [DATA_WIDTH-1:0] bus_din,
    output logic [DATA_WIDTH-1:0] dec_dout,
    output logic [DATA_WIDTH-1:0] bus_dout
);
    mem_if dec_if_inst ();
    mem_if bus_if_inst ();

    assign dec_if_inst.we = dec_we;
    assign dec_if_inst.addr = dec_addr;
    assign dec_if_inst.din = dec_din;
    assign dec_dout = dec_if_inst.dout;
    assign bus_if_inst.we = bus_we;
    assign bus_if_inst.addr = bus_addr;
    assign bus_if_inst.din = bus_din;
    assign bus_dout = bus_if_inst.dout;

    main_mem dut (
        .clk(clk), .rst_n(rst_n), .loading(loading),
        .mem_decoder(dec_if_inst.memory), .mem_bus(bus_if_inst.memory)
    );
endmodule
