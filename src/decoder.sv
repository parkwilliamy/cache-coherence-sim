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

    logic [1:0] current_state, next_state, cmd;
    logic [RD_WIDTH-1:0] rd_idx;
    logic [CYCLE_WIDTH-1:0] cycle_count;

    always_ff @ (posedge clk) begin
        if (!rst_n) begin
            current_state <= LOAD;
            rd_idx <= 0;
            cycle_count <= 0;
        end else begin

            case (current_state)

                LOAD: begin
                    cmd = ui_in[2:1];
                    next_state = (cmd == CMD_START) ? RUN : LOAD;
                end
                RUN: begin
                    cycle_count <= cycle_count+1;
                    next_state = (&dec.core_done) ? LOAD : RUN;
                end
                READ: begin
                    next_state = READ;
                end

            endcase

        end
    end

    always_comb begin

        case (current_state)

            LOAD: begin
                loading = 1;
                uio_oe = '0;
            end
            RUN: begin
                for (int i = 0; i < N_CORES; i++) begin
                    dec[i].run = 1;
                end
            end
            READ: begin
                uo_out[0] = 1; // set resp_valid flag
                uio_oe = 8'hFF; // set all bidir pins to outputs
                
            end

        endcase

    end

endmodule

/* verilator lint_off IMPORTSTAR */
