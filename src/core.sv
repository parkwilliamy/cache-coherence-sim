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

    inst_t icache [ICACHE_SIZE];
    logic [PC_WIDTH-1:0] pc;
    exec_if exec ();

    always_ff @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < ICACHE_SIZE; i++) begin
                icache[i] <= '0;
            end
            pc <= '0;
        end else begin

            if (dec.start) pc <= 0;

            if (dec.icache_load) begin // If decoder is initializing this instruction cache
                icache[pc[$clog2(ICACHE_SIZE)-1:0]] <= dec.load_inst; // Write new instruction into I$
                pc <= pc+1;                  // Increment PC for next instruction write
            end

            if (exec.inst_done) pc <= pc+1; // If instruction retires, increment PC

        end
    end

    assign exec.local_valid = (dec.run && pc != ICACHE_SIZE[PC_WIDTH-1:0]);
    assign exec.local_inst = icache[pc[$clog2(ICACHE_SIZE)-1:0]];
    assign dec.core_done = (pc == ICACHE_SIZE[PC_WIDTH-1:0]);

    cache_ctrl i_cache_ctrl (
        .clk(clk),
        .rst_n(rst_n),
        .exec(exec.cache_ctrl),
        .bus(bus),
        .lines(dec.lines),
        .protocol(protocol)
    );

endmodule

/* verilator lint_off IMPORTSTAR */
