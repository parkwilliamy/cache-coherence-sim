`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module core (
    input clk,
    input rst_n,
    dec_if.core dec,
    bus_if.core bus,
    input logic [1:0] protocol
);

endmodule

/* verilator lint_off IMPORTSTAR */
