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

    line_t cache [DCACHE_SIZE];
    logic [IDX_WIDTH-1:0] idx, snoop_idx;
    logic [TAG_WIDTH-1:0] tag, snoop_tag;
    line_t local_line, snoop_line;
    logic hit, evict, snoop_hit;
    logic e_en, o_en;

    always_comb begin
        idx = exec.local_inst.addr[IDX_WIDTH-1:0];
        tag = exec.local_inst.addr[ADDR_WIDTH-1:IDX_WIDTH];
        local_line = cache[idx];
        hit = local_line.v && local_line.tag == tag;
        evict = local_line.v && local_line.d && !hit;

        snoop_idx = bus.snoop_addr[IDX_WIDTH-1:0];
        snoop_tag = bus.snoop_addr[ADDR_WIDTH-1:IDX_WIDTH];
        snoop_line = cache[snoop_idx];
        snoop_hit = snoop_line.v && snoop_line.tag == snoop_tag;

        e_en = protocol[1] || protocol[0];
        o_en = protocol[1];

        bus.snoop_hit = snoop_hit;
        bus.snoop_owner = snoop_hit && snoop_line.d;
        bus.snoop_data = snoop_line.data;

        bus.req = 1'b0;
        bus.req_type = RD;
        bus.addr = exec.local_inst.addr;
        bus.data = '0;
        exec.inst_done = 1'b0;

        for (int i = 0; i < DCACHE_SIZE; i++) begin
            lines[i] = cache[i];
        end

        if (!bus.snoop_valid && exec.local_valid) begin
            if (hit) begin
                if (!exec.local_inst.op) begin
                    exec.inst_done = 1'b1;
                    
                end else if (local_line.x) begin
                    exec.inst_done = 1'b1;
                end else begin
                    bus.req = 1'b1;
                    bus.req_type = INV;
                    exec.inst_done = bus.done;
                end
            end else if (evict) begin
                bus.req = 1'b1;
                bus.req_type = WB;
                bus.addr = {local_line.tag, idx};
                bus.data = local_line.data;
            end else if (exec.local_inst.op) begin
                bus.req = 1'b1;
                bus.req_type = INV;
                exec.inst_done = bus.done;
            end else begin
                bus.req = 1'b1;
                bus.req_type = RD;
                exec.inst_done = bus.done;
            end
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < DCACHE_SIZE; i++) begin
                cache[i] <= '0;
            end
        end else if (bus.snoop_valid) begin
            if (snoop_hit) begin
                case (bus.snoop_type)
                    RD: begin
                        cache[snoop_idx].x <= 1'b0;
                        cache[snoop_idx].d <= cache[snoop_idx].d && o_en;
                    end
                    INV: begin
                        cache[snoop_idx].v <= 1'b0;
                        cache[snoop_idx].d <= 1'b0;
                        cache[snoop_idx].x <= 1'b0;
                    end
                    //just for WB, which has nothing to do with caches
                    default: begin
                    end
                endcase
            end
        end else if (exec.local_valid) begin
            if (hit && exec.local_inst.op && local_line.x) begin
                cache[idx].data <= exec.local_inst.data;
                cache[idx].d <= 1'b1;
            end else if (bus.done) begin
                if (hit && exec.local_inst.op) begin
                    cache[idx].data <= exec.local_inst.data;
                    cache[idx].d <= 1'b1;
                    cache[idx].x <= 1'b1;
                end else if (!hit && evict) begin
                    cache[idx].v <= 1'b0;
                    cache[idx].d <= 1'b0;
                    cache[idx].x <= 1'b0;
                end else if (!hit && exec.local_inst.op) begin
                    cache[idx].tag <= tag;
                    cache[idx].data <= exec.local_inst.data;
                    cache[idx].v <= 1'b1;
                    cache[idx].d <= 1'b1;
                    cache[idx].x <= 1'b1;
                end else if (!hit) begin
                    cache[idx].tag <= tag;
                    cache[idx].data <= bus.resp_data;
                    cache[idx].v <= 1'b1;
                    cache[idx].d <= 1'b0;
                    cache[idx].x <= e_en && !bus.resp_shared;
                end
            end
        end
    end

endmodule

/* verilator lint_off IMPORTSTAR */
