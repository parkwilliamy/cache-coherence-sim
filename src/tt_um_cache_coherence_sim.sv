`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

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

  dec_if dec[N_CORES] ();
  mem_if mem_decoder ();
  mem_if mem_bus ();
  logic loading;

  decoder u_decoder (
    .clk(clk),
    .rst_n(rst_n),
    .dec(dec.decoder),
    .mem(mem_decoder.writer),
    .ui_in(ui_in[7:0]),
    .uio_in(uio_in[7:0]),
    .loading(loading),
    .uo_out(uo_out[7:0]),
    .uio_out(uio_out[7:0]),
    .uio_oe(uio_oe[7:0])
  );

  bus_if bus[N_CORES] ();

  genvar i;
  generate
    for (i = 0; i < N_CORES; i++) begin
      
      core u_core (
        .clk(clk),
        .rst_n(rst_n),
        .dec(dec[i].core),
        .bus(bus[i].core),
        .protocol(ui_in[4:3])
      );

    end

  endgenerate

  bus u_bus (
    .clk(clk),
    .rst_n(rst_n),
    .bus(bus),
    .mem(mem_bus.writer),
    .protocol(ui_in[4:3])
  );

  main_mem u_main_mem (
    .clk(clk),
    .rst_n(rst_n),
    .loading(loading),
    .mem_decoder(mem_decoder.memory),
    .mem_bus(mem_bus.memory)
  );

  wire _unused = &{ena, 1'b0};

endmodule

/* verilator lint_off IMPORTSTAR */
