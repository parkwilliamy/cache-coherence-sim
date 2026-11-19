`timescale 1ns/1ps
`default_nettype none

import top_params::*;

module decoder_tb (
    input  logic clk,
    input  logic rst_n,
    input  logic [7:0] ui_in,
    input  logic [7:0] uio_in,
    input  logic [N_CORES-1:0] core_done,
    input  logic [N_CORES*DCACHE_SIZE*LINE_WIDTH-1:0] lines,
    output logic loading,
    output logic [7:0] uo_out,
    output logic [7:0] uio_out,
    output logic [7:0] uio_oe,
    output logic mem_we,
    output logic [ADDR_WIDTH-1:0] mem_addr,
    output logic [DATA_WIDTH-1:0] mem_din,
    output logic [N_CORES-1:0] dec_run,
    output logic [N_CORES-1:0] dec_start,
    output logic [N_CORES-1:0] dec_icache_load
);
    dec_if dec_if_inst[N_CORES] ();
    mem_if mem_if_inst ();

    for (genvar i = 0; i < N_CORES; i++) begin : gen_dec
        assign dec_if_inst[i].core_done = core_done[i];
        assign dec_run[i] = dec_if_inst[i].run;
        assign dec_start[i] = dec_if_inst[i].start;
        assign dec_icache_load[i] = dec_if_inst[i].icache_load;
        for (genvar j = 0; j < DCACHE_SIZE; j++) begin : gen_lines
            assign dec_if_inst[i].lines[j] = line_t'(lines[(i*DCACHE_SIZE+j)*LINE_WIDTH+:LINE_WIDTH]);
        end
    end

    assign mem_we = mem_if_inst.we;
    assign mem_addr = mem_if_inst.addr;
    assign mem_din = mem_if_inst.din;

    decoder dut (
        .clk(clk), .rst_n(rst_n), .dec(dec_if_inst), .mem(mem_if_inst.writer),
        .ui_in(ui_in), .uio_in(uio_in), .loading(loading),
        .uo_out(uo_out), .uio_out(uio_out), .uio_oe(uio_oe)
    );
endmodule
