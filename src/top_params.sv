`timescale 1ns/1ps
`default_nettype none

// Parameters, derived widths and packed types shared by every module.
// Spec: docs/uarch.md (parameters, types) and docs/encodings.md (bit formats).

package top_params;

    // ---- Configuration -------------------------------------------------------
    localparam int N_CORES     = 2;  // cores (>= 2)
    localparam int DCACHE_SIZE = 2;  // data cache lines per core, power of two (>= 2)
    localparam int ICACHE_SIZE = 4;  // instructions per core, power of two
    localparam int MEM_SIZE    = 4;  // words of main memory, power of two
    localparam int DATA_WIDTH  = 1;  // bits per word
    localparam int MEM_LATENCY = 2;  // extra bus cycles for a memory access (>= 1)
    localparam int CYCLE_WIDTH = 7;  // saturating cycle counter

    // ---- Derived widths ------------------------------------------------------
    localparam int ADDR_WIDTH     = $clog2(MEM_SIZE);
    localparam int IDX_WIDTH      = $clog2(DCACHE_SIZE);        // line index = addr[IDX_WIDTH-1:0]
    localparam int TAG_WIDTH      = ADDR_WIDTH - IDX_WIDTH;     // tag = addr[ADDR_WIDTH-1:IDX_WIDTH]
    localparam int INST_WIDTH     = ADDR_WIDTH + DATA_WIDTH + 1;
    localparam int LINE_WIDTH     = TAG_WIDTH + DATA_WIDTH + 3;
    localparam int PC_WIDTH       = $clog2(ICACHE_SIZE) + 1;    // pc == ICACHE_SIZE means finished
    localparam int WAIT_WIDTH     = $clog2(MEM_LATENCY + 1);    // bus latency counter
    localparam int RD_WIDTH       = $clog2(N_CORES * DCACHE_SIZE);  // readback counter
    localparam int CORE_SEL_WIDTH = $clog2(N_CORES);

    // ---- Instruction (inst_t) ------------------------------------------------
    typedef struct packed {
        logic [ADDR_WIDTH-1:0] addr;
        logic [DATA_WIDTH-1:0] data;  // value to write; ignored by reads
        logic                  op;    // 0 = read, 1 = write
    } inst_t;

    // ---- Cache line (line_t) -------------------------------------------------
    // {v, d, x}: 000 INVALID, 100 SHARED, 101 EXCLUSIVE, 110 OWNER, 111 MODIFIED
    typedef struct packed {
        logic [TAG_WIDTH-1:0]  tag;
        logic [DATA_WIDTH-1:0] data;
        logic                  v;     // valid
        logic                  d;     // dirty
        logic                  x;     // exclusive
    } line_t;

    // ---- Bus transaction type (req_type_t) -----------------------------------
    // bit 0: invalidates other copies; bit 1: writes memory
    typedef enum logic [1:0] {
        RD  = 2'b00,  // read miss
        INV = 2'b01,  // write miss, or write hit on S/O
        WB  = 2'b10   // eviction of a dirty line
    } req_type_t;

    // ---- Protocol select (protocol[1:0] = ui_in[4:3], read during RUN) ------
    typedef logic [1:0] protocol_t;
    localparam protocol_t MSI   = 2'b00;
    localparam protocol_t MESI  = 2'b01;
    localparam protocol_t MOESI = 2'b10;  // 2'b11 is reserved and behaves as MOESI
    localparam int        PROTOCOL_LSB = 3;

    // ---- Decoder state (state_t) ---------------------------------------------
    typedef enum logic [1:0] {
        LOAD = 2'b00,
        RUN  = 2'b01,
        READ = 2'b10   // terminal
    } state_t;

    // ---- MCU command (cmd_t), LOAD phase -------------------------------------
    // cmd[0] is the instruction op for the two load-instruction commands.
    typedef enum logic [1:0] {
        CMD_LOAD_RD  = 2'b00,  // load read instruction into core core_sel
        CMD_LOAD_WR  = 2'b01,  // load write instruction into core core_sel
        CMD_LOAD_MEM = 2'b10,  // write req_data to memory word req_addr
        CMD_START    = 2'b11   // start the run
    } cmd_t;

    // ---- MCU pin words -------------------------------------------------------
    // Packed from bit 0 upward on in = {uio_in, ui_in} (LOAD) and
    // out = {uio_out, uo_out} (READ). Both must fit in 16 bits.
    typedef struct packed {
        logic [DATA_WIDTH-1:0]     req_data;
        logic [ADDR_WIDTH-1:0]     req_addr;
        logic [CORE_SEL_WIDTH-1:0] core_sel;
        cmd_t                      cmd;
        logic                      req_valid;
    } cmd_word_t;

    typedef struct packed {
        line_t                  line;
        logic [CYCLE_WIDTH-1:0] cycle_count;
        logic                   resp_valid;
    } rd_word_t;

    localparam int CMD_WORD_WIDTH = 3 + CORE_SEL_WIDTH + ADDR_WIDTH + DATA_WIDTH;
    localparam int RD_WORD_WIDTH  = 1 + CYCLE_WIDTH + LINE_WIDTH;
    localparam int RD_NEXT_BIT    = 0;  // rd_next = ui_in[0] during READ

endpackage
