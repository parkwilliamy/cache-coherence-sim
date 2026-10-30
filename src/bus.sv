`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module bus (
    input  clk,
    input  rst_n,
    bus_if.bus bus[N_CORES],
    mem_if.writer mem,
    input logic [1:0] protocol
);

    /*
    logic [N_CORES-1:0] mask, masked_req, gnt_masked, gnt_unmasked;

    always_ff @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mask <= '1;
        end else begin
            mask <= ~((gnt << 1) - 1);
        end
    end

    assign masked_req = req & mask;
    assign gnt_masked = masked_req & (~masked_req + 1);
    assign gnt_unmasked = req & (~req + 1);
    assign gnt = (|masked_req) ? gnt_masked : gnt_unmasked;
    */

endmodule

/* verilator lint_off IMPORTSTAR */
