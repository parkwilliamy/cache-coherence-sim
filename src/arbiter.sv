`timescale 1ns/1ps
`default_nettype none

// Round Robin Arbiter 

module arbiter #(
    parameter int N_CORES = top_params::N_CORES
) (
    input  clk,
    input  rst_n,
    input  logic [N_CORES-1:0] req,    // Request bit vector
    output logic [N_CORES-1:0] gnt  // Grant bit vector
);

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

endmodule
