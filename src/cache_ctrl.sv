`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module cache_ctrl (
    input clk,
    input rst_n,
    exec_if.cache_ctrl exec,
    bus_if.core bus,
    output line_t lines[DCACHE_SIZE],
    input logic [1:0] protocol
);

endmodule

/* verilator lint_off IMPORTSTAR */
