`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module decoder (
    input clk,
    input rst_n,
    dec_if.decoder dec[N_CORES],
    mem_if.writer mem,
    input logic [7:0] ui_in,
    input logic [7:0] uio_in,
    output logic loading,
    output logic [7:0] uo_out,
    output logic [7:0] uio_out,
    output logic [7:0] uio_oe
);

endmodule

/* verilator lint_off IMPORTSTAR */
