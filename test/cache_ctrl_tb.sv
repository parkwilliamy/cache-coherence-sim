`timescale 1ns/1ps
`default_nettype none

/* verilator lint_off IMPORTSTAR */

import top_params::*;

module cache_ctrl_tb (
    input logic clk,
    input logic rst_n,
    input logic local_valid,
    input logic [ADDR_WIDTH-1:0] local_addr,
    input logic [DATA_WIDTH-1:0] local_data,
    input logic local_op,
    input logic bus_done,
    input logic bus_snoop_valid,
    input logic [1:0] bus_snoop_type,
    input logic [ADDR_WIDTH-1:0] bus_snoop_addr,
    input logic bus_resp_shared,
    input logic [DATA_WIDTH-1:0] bus_resp_data,
    input logic [1:0] protocol,
    output logic inst_done,
    output logic bus_req,
    output logic [1:0] bus_req_type,
    output logic [ADDR_WIDTH-1:0] bus_req_addr,
    output logic [DATA_WIDTH-1:0] bus_req_data,
    output logic snoop_hit,
    output logic snoop_owner,
    output logic [DATA_WIDTH-1:0] snoop_data,
    output logic [LINE_WIDTH-1:0] line0,
    output logic [LINE_WIDTH-1:0] line1
);
    exec_if exec ();
    bus_if bus ();
    line_t lines [DCACHE_SIZE];

    assign exec.local_valid = local_valid;
    assign exec.local_inst = {local_addr, local_data, local_op};

    assign bus.done = bus_done;
    assign bus.snoop_valid = bus_snoop_valid;
    assign bus.snoop_type = req_type_t'(bus_snoop_type);
    assign bus.snoop_addr = bus_snoop_addr;
    assign bus.resp_shared = bus_resp_shared;
    assign bus.resp_data = bus_resp_data;

    assign inst_done = exec.inst_done;
    assign bus_req = bus.req;
    assign bus_req_type = bus.req_type;
    assign bus_req_addr = bus.addr;
    assign bus_req_data = bus.data;
    assign snoop_hit = bus.snoop_hit;
    assign snoop_owner = bus.snoop_owner;
    assign snoop_data = bus.snoop_data;
    assign line0 = lines[0];
    assign line1 = lines[1];

    cache_ctrl dut (
        .clk(clk),
        .rst_n(rst_n),
        .exec(exec.cache_ctrl),
        .bus(bus.core),
        .lines(lines),
        .protocol(protocol)
    );
endmodule

/* verilator lint_off IMPORTSTAR */
