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
    req_type_t req_type_by_core [N_CORES];
    logic [ADDR_WIDTH-1:0] req_addr_by_core [N_CORES];
    logic [DATA_WIDTH-1:0] req_data_by_core [N_CORES];
    logic [N_CORES-1:0] snoop_hit_by_core, snoop_owner_by_core;
    logic [DATA_WIDTH-1:0] snoop_data_by_core [N_CORES];
    logic [N_CORES-1:0] done_by_core, snoop_valid_by_core;
    logic [CORE_SEL_WIDTH-1:0] grant_idx, cur, rr_idx;
    logic [WAIT_WIDTH-1:0] wait_count;
    logic [CORE_SEL_WIDTH-1:0] gidx, last;
    logic busy, grant, mem_access, served_by_owner, shared, owner, o_en;
    logic [ADDR_WIDTH-1:0] req_addr;
    logic [DATA_WIDTH-1:0] req_data;
    req_type_t req_type;
    logic [DATA_WIDTH-1:0] owner_data;

    for (genvar i = 0; i < N_CORES; i++) begin : gen_bus_if
        assign reqs[i] = bus[i].req;
        assign req_type_by_core[i] = bus[i].req_type;
        assign req_addr_by_core[i] = bus[i].addr;
        assign req_data_by_core[i] = bus[i].data;
        assign snoop_hit_by_core[i] = bus[i].snoop_hit;
        assign snoop_owner_by_core[i] = bus[i].snoop_owner;
        assign snoop_data_by_core[i] = bus[i].snoop_data;

        assign bus[i].done = done_by_core[i];
        assign bus[i].snoop_valid = snoop_valid_by_core[i];
        assign bus[i].snoop_type = req_type;
        assign bus[i].snoop_addr = req_addr;
        assign bus[i].resp_shared = shared;
        assign bus[i].resp_data = owner ? owner_data : mem.dout;
    end

    always_comb begin
        //loads all requests onto the bus

        busy = (wait_count != '0);
        //as long as there is a wait, we are busy
        grant = !busy && (|reqs);
        //if we are not busy and there is a request, we can grant it
        grant_idx = '0;
        //round-robin: scan from the farthest core after last down to the nearest, so the
        //nearest requester is assigned last and wins. Written without break and with the
        //cast outside the if, because sv2v turns both into latches in the generated Verilog.
        for (int i = N_CORES - 1; i >= 0; i--) begin
            rr_idx = CORE_SEL_WIDTH'((int'(last) + 1 + i) % N_CORES);
            if (reqs[rr_idx]) begin
                grant_idx = rr_idx;
            end
        end

        cur = busy ? gidx : grant_idx;
        //if busy, we are still processing gidx, otherwise we are processing the new grant_idx
        req_type = req_type_by_core[cur];
        req_addr = req_addr_by_core[cur];
        req_data = req_data_by_core[cur];

        for (int i = 0; i < N_CORES; i++) begin
            snoop_valid_by_core[i] = grant && (CORE_SEL_WIDTH'(i) != cur);
        end
    end

    always_comb begin
        shared = 1'b0;
        owner = 1'b0;
        owner_data = '0;
        for (int i = 0; i < N_CORES; i++) begin
            if (CORE_SEL_WIDTH'(i) != cur) begin
                shared |= snoop_hit_by_core[i];
                owner |= snoop_owner_by_core[i];
                owner_data |= snoop_owner_by_core[i] ? snoop_data_by_core[i] : '0;
            end
        end

        o_en = protocol[1];
        served_by_owner = (req_type == RD) && owner && o_en;
        mem_access = (req_type == WB) || ((req_type == RD) && !served_by_owner);

        done_by_core = '0;
        for (int i = 0; i < N_CORES; i++) begin
            if (CORE_SEL_WIDTH'(i) == cur) begin
                done_by_core[i] = grant ? !mem_access : (wait_count == 1);
            end
        end

        mem.addr = req_addr;
        mem.din = (req_type == WB) ? req_data : owner_data;
        mem.we = grant && ((req_type == WB) || ((req_type == RD) && owner && !o_en));
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wait_count <= '0;
            gidx <= '0;
            last <= CORE_SEL_WIDTH'(N_CORES - 1);
        end else begin
            if (grant) begin
                last <= grant_idx;
                if (mem_access) begin
                    gidx <= grant_idx;
                    wait_count <= WAIT_WIDTH'(MEM_LATENCY);
                end
            end else if (busy) begin
                wait_count <= wait_count - 1;
            end
        end
    end

endmodule

/* verilator lint_off IMPORTSTAR */
