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

    logic [N_CORES-1:0] reqs;
    logic [CORE_SEL_WIDTH-1:0] grant_idx, cur;
    logic [WAIT_WIDTH-1:0] wait_count;
    logic [CORE_SEL_WIDTH-1:0] gidx, last;
    logic busy, grant, mem_access, served_by_owner, shared, owner, o_en;
    logic [ADDR_WIDTH-1:0] req_addr;
    logic [DATA_WIDTH-1:0] req_data;
    req_type_t req_type;
    logic [DATA_WIDTH-1:0] owner_data;

    always_comb begin
        reqs = '0;
        for (int i = 0; i < N_CORES; i++) begin
            reqs[i] = bus[i].req;
        end
        //loads all requests onto the bus

        busy = (wait_count != '0);
        //as long as there is a wait, we are busy
        grant = !busy && (|reqs);
        //if we are not busy and there is a request, we can grant it
        grant_idx = '0;
        if (|reqs) begin
            //if any requests, we will grant the next one in a round-robin fashion
            for (int i = 0; i < N_CORES; i++) begin
                automatic int idx = (last + 1 + i) % N_CORES;
                if (reqs[idx]) begin
                    grant_idx = idx;
                    break;
                end
                //loops through requests after last given request, and grants the first one it finds
            end
            //
        end

        cur = busy ? gidx : grant_idx;
        //if busy, we are still processing gidx, otherwise we are processing the new grant_idx
        req_type = bus[cur].req_type;
        req_addr = bus[cur].addr;
        req_data = bus[cur].data;

        shared = 1'b0;
        owner = 1'b0;
        owner_data = '0;
        for (int i = 0; i < N_CORES; i++) begin
            if (i != cur) begin
                shared |= bus[i].snoop_hit;
                owner |= bus[i].snoop_owner;
                owner_data |= bus[i].snoop_owner ? bus[i].snoop_data : '0;
            end
        end

        o_en = protocol[1];
        served_by_owner = (req_type == RD) && owner && o_en;
        mem_access = (req_type == WB) || ((req_type == RD) && !served_by_owner);

        for (int i = 0; i < N_CORES; i++) begin
            bus[i].done = 1'b0;
            bus[i].snoop_valid = 1'b0;
            bus[i].snoop_type = req_type;
            bus[i].snoop_addr = req_addr;
            bus[i].resp_shared = 1'b0;
            bus[i].resp_data = '0;
        end

        if (grant) begin
            for (int i = 0; i < N_CORES; i++) begin
                bus[i].snoop_valid = (i != cur);
            end
        end

        for (int i = 0; i < N_CORES; i++) begin
            if (i == cur) begin
                bus[i].done = grant ? !mem_access : (wait_count == 1);
            end
            bus[i].resp_shared = shared;
            bus[i].resp_data = owner ? owner_data : mem.dout;
        end

        mem.addr = req_addr;
        mem.din = (req_type == WB) ? req_data : owner_data;
        mem.we = grant && ((req_type == WB) || ((req_type == RD) && owner && !o_en));
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wait_count <= '0;
            gidx <= '0;
            last <= N_CORES - 1;
        end else begin
            if (grant) begin
                last <= grant_idx;
                if (mem_access) begin
                    gidx <= grant_idx;
                    wait_count <= MEM_LATENCY;
                end
            end else if (busy) begin
                wait_count <= wait_count - 1;
            end
        end
    end

endmodule

/* verilator lint_off IMPORTSTAR */
