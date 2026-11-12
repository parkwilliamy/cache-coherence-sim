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
    logic [15:0] mcu_in;
    cmd_word_t cmd_word;
    inst_t load_inst;
    logic load_inst_valid, start_cmd;
    line_t all_lines [N_CORES][DCACHE_SIZE];

    assign mcu_in = {uio_in, ui_in};
    assign start_cmd = (current_state == LOAD) && cmd_word.req_valid && (cmd_word.cmd == CMD_START);
    assign load_inst_valid = (current_state == LOAD) && cmd_word.req_valid && ((cmd_word.cmd == CMD_LOAD_RD) || (cmd_word.cmd == CMD_LOAD_WR));

    for (genvar i = 0; i < N_CORES; i++) begin : gen_dec_run
        assign dec[i].run = (current_state == RUN);
        //this start input might be unnecessary, if all it does is reset the PC and we can only run instructions without reset
        assign dec[i].start = start_cmd;
        //icache_load may be unnecessary as well, if we can only load instructions during the LOAD state and can never return
        assign dec[i].icache_load = load_inst_valid && (cmd_word.core_sel == CORE_SEL_WIDTH'(i));
        assign dec[i].load_inst = load_inst;
        //core done is necessary, we need to know when all cores are finished
        assign core_done_by_core[i] = dec[i].core_done;
        for (genvar j = 0; j < DCACHE_SIZE; j++) begin : gen_readback_lines
            assign all_lines[i][j] = dec[i].lines[j];
        end
    end
    //combinational block states
    always_comb begin
        next_state = current_state;
        case (current_state)
            LOAD: begin
                if (start_cmd) begin
                    next_state = RUN;
                end
            end
            RUN: begin
                if (&core_done_by_core) begin
                    next_state = READ;
                end
            end
            READ: next_state = READ;
            default: next_state = LOAD;
        endcase
    end
    //implements state logic and cycle counter
    always_ff @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= LOAD;
            rd_idx <= 0;
            cycle_count <= 0;
        end else begin
            current_state <= next_state;
            if (current_state == RUN && cycle_count != {CYCLE_WIDTH{1'b1}}) begin
                cycle_count <= cycle_count + 1'b1;
            end
            if (current_state == READ && ui_in[RD_NEXT_BIT]) begin
                if (rd_idx == RD_WIDTH'(N_CORES * DCACHE_SIZE - 1)) begin
                    rd_idx <= '0;
                end else begin
                    rd_idx <= rd_idx + 1'b1;
                end
            end
        end
    end
    
    //implements other combinational logic, including output logic
    always_comb begin
        cmd_word.req_valid = mcu_in[0];
        cmd_word.cmd = cmd_t'(mcu_in[2:1]);
        cmd_word.core_sel = mcu_in[3 +: CORE_SEL_WIDTH];
        cmd_word.req_addr = mcu_in[3 + CORE_SEL_WIDTH +: ADDR_WIDTH];
        cmd_word.req_data = mcu_in[3 + CORE_SEL_WIDTH + ADDR_WIDTH +: DATA_WIDTH];

        load_inst.addr = cmd_word.req_addr;
        load_inst.data = (cmd_word.cmd == CMD_LOAD_WR) ? cmd_word.req_data : '0;
        load_inst.op = cmd_word.cmd[0];

        loading = (current_state == LOAD);
        //reset
        uo_out = '0;
        uio_out = '0;
        uio_oe = '0;
    
        mem.we = 1'b0;
        mem.addr = '0;
        mem.din = '0;

        if (current_state == LOAD && cmd_word.req_valid && cmd_word.cmd == CMD_LOAD_MEM) begin
            mem.we = 1'b1;
            mem.addr = cmd_word.req_addr;
            mem.din = cmd_word.req_data;
        end
        
                
        if (current_state == READ) begin
            uo_out[0] = 1'b1;
            uio_oe = 8'hFF;
            uio_out[LINE_WIDTH-1:0] = all_lines[int'(rd_idx) / DCACHE_SIZE][int'(rd_idx) % DCACHE_SIZE];
        end
        uo_out[CYCLE_WIDTH:1] = cycle_count;
    end

endmodule

/* verilator lint_off IMPORTSTAR */
