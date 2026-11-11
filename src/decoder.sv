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

    logic [1:0] current_state, next_state;
    logic [RD_WIDTH-1:0] rd_idx;
    logic [CYCLE_WIDTH-1:0] cycle_count;
    logic [N_CORES-1:0] core_done_by_core;

    for (genvar i = 0; i < N_CORES; i++) begin : gen_dec_run
        assign dec[i].run = (current_state == RUN);
        assign core_done_by_core[i] = dec[i].core_done;
    end

    always_comb begin
        next_state = current_state;
        case (current_state)
            LOAD: begin
                if (ui_in[2:1] == CMD_START) begin
                    next_state = RUN;
                end
            end
            RUN: begin
                if (&core_done_by_core) begin
                    next_state = LOAD;
                end
            end
            READ: next_state = READ;
            default: next_state = LOAD;
        endcase
    end

    always_ff @ (posedge clk) begin
        if (!rst_n) begin
            current_state <= LOAD;
            rd_idx <= 0;
            cycle_count <= 0;
        end else begin
            current_state <= next_state;
            if (current_state == RUN) begin
                cycle_count <= cycle_count + 1'b1;
            end
        end
    end

    always_comb begin
        loading = (current_state == LOAD);
        uo_out = '0;
        uio_out = '0;
        uio_oe = '0;
        if (current_state == READ) begin
            uo_out[0] = 1'b1;
            uio_oe = 8'hFF;
        end
    end

endmodule

/* verilator lint_off IMPORTSTAR */
