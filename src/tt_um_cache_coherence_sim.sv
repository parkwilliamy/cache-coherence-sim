`timescale 1ns/1ps
`default_nettype none

import top_params::*;

module tt_um_cache_coherence_sim (
    input  logic [7:0] ui_in,    // Dedicated inputs
    output logic [7:0] uo_out,   // Dedicated outputs
    input  logic [7:0] uio_in,   // IOs: Input path
    output logic [7:0] uio_out,  // IOs: Output path
    output logic [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  logic       ena,      // always 1 when the design is powered, so you can ignore it
    input  logic       clk,      // clock
    input  logic       rst_n     // reset_n - low to reset
);

  assign uio_out = 0;
  assign uio_oe  = 0;

  arbiter core_arbiter (
    .clk(clk),
    .rst_n(rst_n),
    .req(ui_in[N_CORES-1:0]),
    .gnt(uo_out[N_CORES-1:0])
  );

endmodule
