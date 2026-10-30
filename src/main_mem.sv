`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module main_mem (
    input clk,
    input rst_n,
    input loading,
    mem_if.memory mem_decoder,
    mem_if.memory mem_bus
);

    logic [DATA_WIDTH-1:0] memory [MEM_SIZE];

    always_ff @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < MEM_SIZE; i++) begin
                memory[i] <= '0;
            end
        end else begin
        end
        if (loading && mem_decoder.we) begin // Decoder initialization of main memory
            memory[mem_decoder.addr] <= mem_decoder.din;
            mem_decoder.dout <= '0;
        end else begin                        // Bus reading/writing main memory
            if (mem_bus.we) memory[mem_bus.addr] <= mem_bus.din;
            mem_bus.dout <= memory[mem_bus.addr];
        end
    end

endmodule

/* verilator lint_off IMPORTSTAR */
