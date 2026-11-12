`default_nettype wire
module tt_um_cache_coherence_sim (
	ui_in,
	uo_out,
	uio_in,
	uio_out,
	uio_oe,
	ena,
	clk,
	rst_n
);
	input wire [7:0] ui_in;
	output wire [7:0] uo_out;
	input wire [7:0] uio_in;
	output wire [7:0] uio_out;
	output wire [7:0] uio_oe;
	input wire ena;
	input wire clk;
	input wire rst_n;
	localparam signed [31:0] top_params_N_CORES = 2;
	genvar _arr_15365;
	generate
		for (_arr_15365 = 0; _arr_15365 <= 1; _arr_15365 = _arr_15365 + 1) begin : dec
			wire start;
			wire run;
			wire icache_load;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			wire [(32'sd2 + 32'sd1) + 0:0] load_inst;
			wire core_done;
			localparam signed [31:0] top_params_DCACHE_SIZE = 2;
			localparam signed [31:0] top_params_IDX_WIDTH = 1;
			localparam signed [31:0] top_params_TAG_WIDTH = top_params_ADDR_WIDTH - top_params_IDX_WIDTH;
			wire [(((32'sd2 - 32'sd1) + 3) >= 0 ? (top_params_DCACHE_SIZE * ((32'sd2 - 32'sd1) + 4)) - 1 : (top_params_DCACHE_SIZE * (1 - ((32'sd2 - 32'sd1) + 3))) + ((32'sd2 - 32'sd1) + 2)):(((32'sd2 - 32'sd1) + 3) >= 0 ? 0 : (32'sd2 - 32'sd1) + 3)] lines;
		end
		if (1) begin : mem_decoder
			reg we;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			reg [1:0] addr;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			reg [0:0] din;
			reg [0:0] dout;
		end
		if (1) begin : mem_bus
			reg we;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			reg [1:0] addr;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			reg [0:0] din;
			reg [0:0] dout;
		end
	endgenerate
	wire loading;
	localparam _bbase_F9110_dec = 0;
	function automatic signed [31:0] sv2v_cast_32_signed;
		input reg signed [31:0] inp;
		sv2v_cast_32_signed = inp;
	endfunction
	generate
		if (1) begin : u_decoder
			reg _sv2v_0;
			wire clk;
			wire rst_n;
			localparam signed [31:0] top_params_N_CORES = 2;
			localparam _mbase_dec = 0;
			wire [7:0] ui_in;
			wire [7:0] uio_in;
			reg loading;
			reg [7:0] uo_out;
			reg [7:0] uio_out;
			reg [7:0] uio_oe;
			reg [1:0] current_state;
			reg [1:0] next_state;
			localparam signed [31:0] top_params_DCACHE_SIZE = 2;
			localparam signed [31:0] top_params_RD_WIDTH = $clog2(32'sd2 * 32'sd2);
			reg [top_params_RD_WIDTH - 1:0] rd_idx;
			localparam signed [31:0] top_params_CYCLE_WIDTH = 7;
			reg [6:0] cycle_count;
			wire [1:0] core_done_by_core;
			wire [15:0] mcu_in;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			localparam signed [31:0] top_params_CORE_SEL_WIDTH = 1;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			reg [((top_params_DATA_WIDTH + top_params_ADDR_WIDTH) + top_params_CORE_SEL_WIDTH) + 2:0] cmd_word;
			reg [(top_params_ADDR_WIDTH + top_params_DATA_WIDTH) + 0:0] load_inst;
			wire load_inst_valid;
			wire start_cmd;
			localparam signed [31:0] top_params_IDX_WIDTH = 1;
			localparam signed [31:0] top_params_TAG_WIDTH = top_params_ADDR_WIDTH - top_params_IDX_WIDTH;
			wire [(top_params_TAG_WIDTH + top_params_DATA_WIDTH) + 2:0] all_lines [0:1][0:1];
			assign mcu_in = {uio_in, ui_in};
			assign start_cmd = ((current_state == 2'b00) && cmd_word[0]) && (cmd_word[2-:2] == 2'b11);
			assign load_inst_valid = ((current_state == 2'b00) && cmd_word[0]) && ((cmd_word[2-:2] == 2'b00) || (cmd_word[2-:2] == 2'b01));
			genvar _gv_i_1;
			for (_gv_i_1 = 0; _gv_i_1 < top_params_N_CORES; _gv_i_1 = _gv_i_1 + 1) begin : gen_dec_run
				localparam i = _gv_i_1;
				assign tt_um_cache_coherence_sim.dec[i + _mbase_dec].run = current_state == 2'b01;
				assign tt_um_cache_coherence_sim.dec[i + _mbase_dec].start = start_cmd;
				function automatic signed [0:0] sv2v_cast_2566C_signed;
					input reg signed [0:0] inp;
					sv2v_cast_2566C_signed = inp;
				endfunction
				assign tt_um_cache_coherence_sim.dec[i + _mbase_dec].icache_load = load_inst_valid && (cmd_word[3-:1] == sv2v_cast_2566C_signed(i));
				assign tt_um_cache_coherence_sim.dec[i + _mbase_dec].load_inst = load_inst;
				assign core_done_by_core[i] = tt_um_cache_coherence_sim.dec[i + _mbase_dec].core_done;
				genvar _gv_j_1;
				for (_gv_j_1 = 0; _gv_j_1 < top_params_DCACHE_SIZE; _gv_j_1 = _gv_j_1 + 1) begin : gen_readback_lines
					localparam j = _gv_j_1;
					assign all_lines[i][j] = tt_um_cache_coherence_sim.dec[i + _mbase_dec].lines[(((32'sd2 - 32'sd1) + 3) >= 0 ? 0 : (32'sd2 - 32'sd1) + 3) + ((1 - j) * (((32'sd2 - 32'sd1) + 3) >= 0 ? (32'sd2 - 32'sd1) + 4 : 1 - ((32'sd2 - 32'sd1) + 3)))+:(((32'sd2 - 32'sd1) + 3) >= 0 ? (32'sd2 - 32'sd1) + 4 : 1 - ((32'sd2 - 32'sd1) + 3))];
				end
			end
			always @(*) begin
				if (_sv2v_0)
					;
				next_state = current_state;
				case (current_state)
					2'b00:
						if (start_cmd)
							next_state = 2'b01;
					2'b01:
						if (&core_done_by_core)
							next_state = 2'b10;
					2'b10: next_state = 2'b10;
					default: next_state = 2'b00;
				endcase
			end
			localparam signed [31:0] top_params_RD_NEXT_BIT = 0;
			always @(posedge clk or negedge rst_n)
				if (!rst_n) begin
					current_state <= 2'b00;
					rd_idx <= 0;
					cycle_count <= 0;
				end
				else begin
					current_state <= next_state;
					if ((current_state == 2'b01) && (cycle_count != {top_params_CYCLE_WIDTH {1'b1}}))
						cycle_count <= cycle_count + 1'b1;
					if ((current_state == 2'b10) && ui_in[top_params_RD_NEXT_BIT]) begin : sv2v_autoblock_1
						reg signed [top_params_RD_WIDTH - 1:0] sv2v_tmp_cast;
						sv2v_tmp_cast = (top_params_N_CORES * top_params_DCACHE_SIZE) - 1;
						if (rd_idx == sv2v_tmp_cast)
							rd_idx <= 1'sb0;
						else
							rd_idx <= rd_idx + 1'b1;
					end
				end
			localparam signed [31:0] top_params_LINE_WIDTH = (top_params_TAG_WIDTH + top_params_DATA_WIDTH) + 3;
			always @(*) begin
				if (_sv2v_0)
					;
				cmd_word[0] = mcu_in[0];
				cmd_word[2-:2] = mcu_in[2:1];
				cmd_word[3-:1] = mcu_in[3+:top_params_CORE_SEL_WIDTH];
				cmd_word[5-:2] = mcu_in[4+:top_params_ADDR_WIDTH];
				cmd_word[6-:1] = mcu_in[6+:top_params_DATA_WIDTH];
				load_inst[3-:2] = cmd_word[5-:2];
				load_inst[1-:1] = (cmd_word[2-:2] == 2'b01 ? cmd_word[6-:1] : 1'b0);
				load_inst[0] = cmd_word[1];
				loading = current_state == 2'b00;
				uo_out = 1'sb0;
				uio_out = 1'sb0;
				uio_oe = 1'sb0;
				tt_um_cache_coherence_sim.mem_decoder.we = 1'b0;
				tt_um_cache_coherence_sim.mem_decoder.addr = 1'sb0;
				tt_um_cache_coherence_sim.mem_decoder.din = 1'sb0;
				if (((current_state == 2'b00) && cmd_word[0]) && (cmd_word[2-:2] == 2'b10)) begin
					tt_um_cache_coherence_sim.mem_decoder.we = 1'b1;
					tt_um_cache_coherence_sim.mem_decoder.addr = cmd_word[5-:2];
					tt_um_cache_coherence_sim.mem_decoder.din = cmd_word[6-:1];
				end
				if (current_state == 2'b10) begin
					uo_out[0] = 1'b1;
					uio_oe = 8'hff;
					uio_out[top_params_LINE_WIDTH - 1:0] = all_lines[sv2v_cast_32_signed(rd_idx) / top_params_DCACHE_SIZE][sv2v_cast_32_signed(rd_idx) % top_params_DCACHE_SIZE];
				end
				uo_out[top_params_CYCLE_WIDTH:1] = cycle_count;
			end
			initial _sv2v_0 = 0;
		end
	endgenerate
	assign u_decoder.clk = clk;
	assign u_decoder.rst_n = rst_n;
	assign u_decoder.ui_in = ui_in[7:0];
	assign u_decoder.uio_in = uio_in[7:0];
	assign loading = u_decoder.loading;
	assign uo_out[7:0] = u_decoder.uo_out;
	assign uio_out[7:0] = u_decoder.uio_out;
	assign uio_oe[7:0] = u_decoder.uio_oe;
	genvar _arr_3D285;
	generate
		for (_arr_3D285 = 0; _arr_3D285 <= 1; _arr_3D285 = _arr_3D285 + 1) begin : bus
			reg req;
			reg [1:0] req_type;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			reg [1:0] addr;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			reg [0:0] data;
			reg snoop_hit;
			reg snoop_owner;
			reg [0:0] snoop_data;
			wire done;
			wire snoop_valid;
			wire [1:0] snoop_type;
			wire [1:0] snoop_addr;
			wire resp_shared;
			wire [0:0] resp_data;
		end
	endgenerate
	genvar _gv_i_3;
	generate
		for (_gv_i_3 = 0; _gv_i_3 < top_params_N_CORES; _gv_i_3 = _gv_i_3 + 1) begin : genblk1
			localparam i = _gv_i_3;
			localparam _bbase_D9579_dec = _gv_i_3;
			localparam _bbase_D9579_bus = _gv_i_3;
			if (1) begin : u_core
				wire clk;
				wire rst_n;
				localparam _mbase_dec = _bbase_D9579_dec;
				localparam _mbase_bus = _bbase_D9579_bus;
				wire [1:0] protocol;
				localparam signed [31:0] top_params_ICACHE_SIZE = 4;
				localparam signed [31:0] top_params_MEM_SIZE = 4;
				localparam signed [31:0] top_params_ADDR_WIDTH = 2;
				localparam signed [31:0] top_params_DATA_WIDTH = 1;
				reg [(32'sd2 + 32'sd1) + 0:0] icache [0:3];
				localparam signed [31:0] top_params_PC_WIDTH = 3;
				reg [2:0] pc;
				if (1) begin : exec
					wire local_valid;
					localparam signed [31:0] top_params_MEM_SIZE = 4;
					localparam signed [31:0] top_params_ADDR_WIDTH = 2;
					localparam signed [31:0] top_params_DATA_WIDTH = 1;
					wire [(32'sd2 + 32'sd1) + 0:0] local_inst;
					reg inst_done;
				end
				always @(posedge clk or negedge rst_n)
					if (!rst_n) begin
						begin : sv2v_autoblock_2
							reg signed [31:0] i;
							for (i = 0; i < top_params_ICACHE_SIZE; i = i + 1)
								icache[i] <= 1'sb0;
						end
						pc <= 1'sb0;
					end
					else begin
						if (tt_um_cache_coherence_sim.dec[_mbase_dec].start)
							pc <= 0;
						if (tt_um_cache_coherence_sim.dec[_mbase_dec].icache_load) begin
							icache[pc[1:0]] <= tt_um_cache_coherence_sim.dec[_mbase_dec].load_inst;
							pc <= pc + 1;
						end
						if (exec.inst_done)
							pc <= pc + 1;
					end
				assign exec.local_valid = tt_um_cache_coherence_sim.dec[_mbase_dec].run && (pc != top_params_ICACHE_SIZE[2:0]);
				assign exec.local_inst = icache[pc[1:0]];
				assign tt_um_cache_coherence_sim.dec[_mbase_dec].core_done = pc == top_params_ICACHE_SIZE[2:0];
				localparam _bbase_81B35_bus = _gv_i_3;
				if (1) begin : i_cache_ctrl
					reg _sv2v_0;
					wire clk;
					wire rst_n;
					localparam _mbase_bus = _bbase_81B35_bus;
					localparam signed [31:0] top_params_DCACHE_SIZE = 2;
					localparam signed [31:0] top_params_DATA_WIDTH = 1;
					localparam signed [31:0] top_params_MEM_SIZE = 4;
					localparam signed [31:0] top_params_ADDR_WIDTH = 2;
					localparam signed [31:0] top_params_IDX_WIDTH = 1;
					localparam signed [31:0] top_params_TAG_WIDTH = top_params_ADDR_WIDTH - top_params_IDX_WIDTH;
					reg [(((32'sd2 - 32'sd1) + 3) >= 0 ? (top_params_DCACHE_SIZE * ((32'sd2 - 32'sd1) + 4)) - 1 : (top_params_DCACHE_SIZE * (1 - ((32'sd2 - 32'sd1) + 3))) + ((32'sd2 - 32'sd1) + 2)):(((32'sd2 - 32'sd1) + 3) >= 0 ? 0 : (32'sd2 - 32'sd1) + 3)] lines;
					wire [1:0] protocol;
					reg [(32'sd2 - 32'sd1) + 3:0] cache [0:1];
					reg [0:0] idx;
					reg [0:0] snoop_idx;
					reg [top_params_TAG_WIDTH - 1:0] tag;
					reg [top_params_TAG_WIDTH - 1:0] snoop_tag;
					reg [(32'sd2 - 32'sd1) + 3:0] local_line;
					reg [(32'sd2 - 32'sd1) + 3:0] snoop_line;
					reg hit;
					reg evict;
					reg snoop_hit;
					reg e_en;
					reg o_en;
					always @(*) begin
						if (_sv2v_0)
							;
						snoop_idx = tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_addr[0:0];
						snoop_tag = tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_addr[1:top_params_IDX_WIDTH];
						snoop_line = cache[snoop_idx];
						snoop_hit = snoop_line[2] && (snoop_line[(32'sd2 - 32'sd1) + 3-:(((32'sd2 - 32'sd1) + 3) >= 4 ? (32'sd2 - 32'sd1) - 0 : 5 - ((32'sd2 - 32'sd1) + 3))] == snoop_tag);
						tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_hit = snoop_hit;
						tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_owner = snoop_hit && snoop_line[1];
						tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_data = snoop_line[3-:1];
					end
					always @(*) begin
						if (_sv2v_0)
							;
						e_en = protocol[1] || protocol[0];
						o_en = protocol[1];
						idx = tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[2:2];
						tag = tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[3:3];
						local_line = cache[idx];
						hit = local_line[2] && (local_line[(32'sd2 - 32'sd1) + 3-:(((32'sd2 - 32'sd1) + 3) >= 4 ? (32'sd2 - 32'sd1) - 0 : 5 - ((32'sd2 - 32'sd1) + 3))] == tag);
						evict = (local_line[2] && local_line[1]) && !hit;
						tt_um_cache_coherence_sim.bus[_mbase_bus].req = 1'b0;
						tt_um_cache_coherence_sim.bus[_mbase_bus].req_type = 2'b00;
						tt_um_cache_coherence_sim.bus[_mbase_bus].addr = tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[3-:2];
						tt_um_cache_coherence_sim.bus[_mbase_bus].data = 1'sb0;
						begin : sv2v_autoblock_3
							reg signed [31:0] i;
							for (i = 0; i < top_params_DCACHE_SIZE; i = i + 1)
								lines[(((32'sd2 - 32'sd1) + 3) >= 0 ? 0 : (32'sd2 - 32'sd1) + 3) + ((1 - i) * (((32'sd2 - 32'sd1) + 3) >= 0 ? (32'sd2 - 32'sd1) + 4 : 1 - ((32'sd2 - 32'sd1) + 3)))+:(((32'sd2 - 32'sd1) + 3) >= 0 ? (32'sd2 - 32'sd1) + 4 : 1 - ((32'sd2 - 32'sd1) + 3))] = cache[i];
						end
						if (tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_valid) begin
							if (hit) begin
								if (tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0] && !local_line[0]) begin
									tt_um_cache_coherence_sim.bus[_mbase_bus].req = 1'b1;
									tt_um_cache_coherence_sim.bus[_mbase_bus].req_type = 2'b01;
								end
							end
							else if (evict) begin
								tt_um_cache_coherence_sim.bus[_mbase_bus].req = 1'b1;
								tt_um_cache_coherence_sim.bus[_mbase_bus].req_type = 2'b10;
								tt_um_cache_coherence_sim.bus[_mbase_bus].addr = {local_line[(32'sd2 - 32'sd1) + 3-:(((32'sd2 - 32'sd1) + 3) >= 4 ? (32'sd2 - 32'sd1) - 0 : 5 - ((32'sd2 - 32'sd1) + 3))], idx};
								tt_um_cache_coherence_sim.bus[_mbase_bus].data = local_line[3-:1];
							end
							else if (tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0]) begin
								tt_um_cache_coherence_sim.bus[_mbase_bus].req = 1'b1;
								tt_um_cache_coherence_sim.bus[_mbase_bus].req_type = 2'b01;
							end
							else begin
								tt_um_cache_coherence_sim.bus[_mbase_bus].req = 1'b1;
								tt_um_cache_coherence_sim.bus[_mbase_bus].req_type = 2'b00;
							end
						end
					end
					always @(*) begin
						if (_sv2v_0)
							;
						tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.inst_done = 1'b0;
						if (!tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_valid && tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_valid) begin
							if (hit) begin
								if (!tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0] || local_line[0])
									tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.inst_done = 1'b1;
								else
									tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.inst_done = tt_um_cache_coherence_sim.bus[_mbase_bus].done;
							end
							else if (!evict)
								tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.inst_done = tt_um_cache_coherence_sim.bus[_mbase_bus].done;
						end
					end
					always @(posedge clk or negedge rst_n)
						if (!rst_n) begin : sv2v_autoblock_4
							reg signed [31:0] i;
							for (i = 0; i < top_params_DCACHE_SIZE; i = i + 1)
								cache[i] <= 1'sb0;
						end
						else if (tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_valid) begin
							if (snoop_hit)
								case (tt_um_cache_coherence_sim.bus[_mbase_bus].snoop_type)
									2'b00: begin
										cache[snoop_idx][0] <= 1'b0;
										cache[snoop_idx][1] <= cache[snoop_idx][1] && o_en;
									end
									2'b01: begin
										cache[snoop_idx][2] <= 1'b0;
										cache[snoop_idx][1] <= 1'b0;
										cache[snoop_idx][0] <= 1'b0;
									end
									default:
										;
								endcase
						end
						else if (tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_valid) begin
							if ((hit && tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0]) && local_line[0]) begin
								cache[idx][3-:1] <= tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[1-:1];
								cache[idx][1] <= 1'b1;
							end
							else if (tt_um_cache_coherence_sim.bus[_mbase_bus].done) begin
								if (hit && tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0]) begin
									cache[idx][3-:1] <= tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[1-:1];
									cache[idx][1] <= 1'b1;
									cache[idx][0] <= 1'b1;
								end
								else if (!hit && evict) begin
									cache[idx][2] <= 1'b0;
									cache[idx][1] <= 1'b0;
									cache[idx][0] <= 1'b0;
								end
								else if (!hit && tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[0]) begin
									cache[idx][(32'sd2 - 32'sd1) + 3-:(((32'sd2 - 32'sd1) + 3) >= 4 ? (32'sd2 - 32'sd1) - 0 : 5 - ((32'sd2 - 32'sd1) + 3))] <= tag;
									cache[idx][3-:1] <= tt_um_cache_coherence_sim.genblk1[_gv_i_3].u_core.exec.local_inst[1-:1];
									cache[idx][2] <= 1'b1;
									cache[idx][1] <= 1'b1;
									cache[idx][0] <= 1'b1;
								end
								else if (!hit) begin
									cache[idx][(32'sd2 - 32'sd1) + 3-:(((32'sd2 - 32'sd1) + 3) >= 4 ? (32'sd2 - 32'sd1) - 0 : 5 - ((32'sd2 - 32'sd1) + 3))] <= tag;
									cache[idx][3-:1] <= tt_um_cache_coherence_sim.bus[_mbase_bus].resp_data;
									cache[idx][2] <= 1'b1;
									cache[idx][1] <= 1'b0;
									cache[idx][0] <= e_en && !tt_um_cache_coherence_sim.bus[_mbase_bus].resp_shared;
								end
							end
						end
					initial _sv2v_0 = 0;
				end
				assign i_cache_ctrl.clk = clk;
				assign i_cache_ctrl.rst_n = rst_n;
				assign tt_um_cache_coherence_sim.dec[_mbase_dec].lines = i_cache_ctrl.lines;
				assign i_cache_ctrl.protocol = protocol;
			end
			assign u_core.clk = clk;
			assign u_core.rst_n = rst_n;
			assign u_core.protocol = ui_in[4:3];
		end
	endgenerate
	localparam _bbase_19788_bus = 0;
	generate
		if (1) begin : u_bus
			reg _sv2v_0;
			wire clk;
			wire rst_n;
			localparam signed [31:0] top_params_N_CORES = 2;
			localparam _mbase_bus = 0;
			wire [1:0] protocol;
			wire [1:0] reqs;
			wire [1:0] req_type_by_core [0:1];
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			localparam signed [31:0] top_params_ADDR_WIDTH = 2;
			wire [1:0] req_addr_by_core [0:1];
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			wire [0:0] req_data_by_core [0:1];
			wire [1:0] snoop_hit_by_core;
			wire [1:0] snoop_owner_by_core;
			wire [0:0] snoop_data_by_core [0:1];
			reg [1:0] done_by_core;
			reg [1:0] snoop_valid_by_core;
			localparam signed [31:0] top_params_CORE_SEL_WIDTH = 1;
			reg [0:0] grant_idx;
			reg [0:0] cur;
			reg [0:0] rr_idx;
			localparam signed [31:0] top_params_MEM_LATENCY = 2;
			localparam signed [31:0] top_params_WAIT_WIDTH = 2;
			reg [1:0] wait_count;
			reg [0:0] gidx;
			reg [0:0] last;
			reg busy;
			reg grant;
			reg mem_access;
			reg served_by_owner;
			reg shared;
			reg owner;
			reg o_en;
			reg [1:0] req_addr;
			reg [0:0] req_data;
			reg [1:0] req_type;
			reg [0:0] owner_data;
			genvar _gv_i_2;
			for (_gv_i_2 = 0; _gv_i_2 < top_params_N_CORES; _gv_i_2 = _gv_i_2 + 1) begin : gen_bus_if
				localparam i = _gv_i_2;
				assign reqs[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].req;
				assign req_type_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].req_type;
				assign req_addr_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].addr;
				assign req_data_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].data;
				assign snoop_hit_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_hit;
				assign snoop_owner_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_owner;
				assign snoop_data_by_core[i] = tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_data;
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].done = done_by_core[i];
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_valid = snoop_valid_by_core[i];
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_type = req_type;
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].snoop_addr = req_addr;
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].resp_shared = shared;
				assign tt_um_cache_coherence_sim.bus[i + _mbase_bus].resp_data = (owner ? owner_data : tt_um_cache_coherence_sim.mem_bus.dout);
			end
			always @(*) begin
				if (_sv2v_0)
					;
				busy = wait_count != {2 {1'sb0}};
				grant = !busy && |reqs;
				grant_idx = 1'sb0;
				begin : sv2v_autoblock_5
					reg signed [31:0] i;
					for (i = 1; i >= 0; i = i - 1)
						begin
							begin : sv2v_autoblock_6
								reg signed [0:0] sv2v_tmp_cast;
								sv2v_tmp_cast = ((sv2v_cast_32_signed(last) + 1) + i) % top_params_N_CORES;
								rr_idx = sv2v_tmp_cast;
							end
							if (reqs[rr_idx])
								grant_idx = rr_idx;
						end
				end
				cur = (busy ? gidx : grant_idx);
				req_type = req_type_by_core[cur];
				req_addr = req_addr_by_core[cur];
				req_data = req_data_by_core[cur];
				begin : sv2v_autoblock_7
					reg signed [31:0] i;
					for (i = 0; i < top_params_N_CORES; i = i + 1)
						begin : sv2v_autoblock_8
							reg signed [0:0] sv2v_tmp_cast;
							sv2v_tmp_cast = i;
							snoop_valid_by_core[i] = grant && (sv2v_tmp_cast != cur);
						end
				end
			end
			always @(*) begin
				if (_sv2v_0)
					;
				shared = 1'b0;
				owner = 1'b0;
				owner_data = 1'sb0;
				begin : sv2v_autoblock_9
					reg signed [31:0] i;
					for (i = 0; i < top_params_N_CORES; i = i + 1)
						begin : sv2v_autoblock_10
							reg signed [0:0] sv2v_tmp_cast;
							sv2v_tmp_cast = i;
							if (sv2v_tmp_cast != cur) begin
								shared = shared | snoop_hit_by_core[i];
								owner = owner | snoop_owner_by_core[i];
								owner_data = owner_data | (snoop_owner_by_core[i] ? snoop_data_by_core[i] : 1'b0);
							end
						end
				end
				o_en = protocol[1];
				served_by_owner = ((req_type == 2'b00) && owner) && o_en;
				mem_access = (req_type == 2'b10) || ((req_type == 2'b00) && !served_by_owner);
				done_by_core = 1'sb0;
				begin : sv2v_autoblock_11
					reg signed [31:0] i;
					for (i = 0; i < top_params_N_CORES; i = i + 1)
						begin : sv2v_autoblock_12
							reg signed [0:0] sv2v_tmp_cast;
							sv2v_tmp_cast = i;
							if (sv2v_tmp_cast == cur)
								done_by_core[i] = (grant ? !mem_access : wait_count == 1);
						end
				end
				tt_um_cache_coherence_sim.mem_bus.addr = req_addr;
				tt_um_cache_coherence_sim.mem_bus.din = (req_type == 2'b10 ? req_data : owner_data);
				tt_um_cache_coherence_sim.mem_bus.we = grant && ((req_type == 2'b10) || (((req_type == 2'b00) && owner) && !o_en));
			end
			always @(posedge clk or negedge rst_n)
				if (!rst_n) begin
					wait_count <= 1'sb0;
					gidx <= 1'sb0;
					begin : sv2v_autoblock_13
						reg signed [0:0] sv2v_tmp_cast;
						sv2v_tmp_cast = 1;
						last <= sv2v_tmp_cast;
					end
				end
				else if (grant) begin
					last <= grant_idx;
					if (mem_access) begin
						gidx <= grant_idx;
						begin : sv2v_autoblock_14
							reg signed [1:0] sv2v_tmp_cast;
							sv2v_tmp_cast = top_params_MEM_LATENCY;
							wait_count <= sv2v_tmp_cast;
						end
					end
				end
				else if (busy)
					wait_count <= wait_count - 1;
			initial _sv2v_0 = 0;
		end
	endgenerate
	assign u_bus.clk = clk;
	assign u_bus.rst_n = rst_n;
	assign u_bus.protocol = ui_in[4:3];
	generate
		if (1) begin : u_main_mem
			wire clk;
			wire rst_n;
			wire loading;
			localparam signed [31:0] top_params_DATA_WIDTH = 1;
			localparam signed [31:0] top_params_MEM_SIZE = 4;
			reg [0:0] memory [0:3];
			always @(posedge clk or negedge rst_n)
				if (!rst_n) begin : sv2v_autoblock_15
					reg signed [31:0] i;
					for (i = 0; i < top_params_MEM_SIZE; i = i + 1)
						begin
							memory[i] <= 1'sb0;
							tt_um_cache_coherence_sim.mem_bus.dout <= 1'sb0;
							tt_um_cache_coherence_sim.mem_decoder.dout <= 1'sb0;
						end
				end
				else if (loading && tt_um_cache_coherence_sim.mem_decoder.we) begin
					memory[tt_um_cache_coherence_sim.mem_decoder.addr] <= tt_um_cache_coherence_sim.mem_decoder.din;
					tt_um_cache_coherence_sim.mem_decoder.dout <= 1'sb0;
				end
				else begin
					if (tt_um_cache_coherence_sim.mem_bus.we)
						memory[tt_um_cache_coherence_sim.mem_bus.addr] <= tt_um_cache_coherence_sim.mem_bus.din;
					tt_um_cache_coherence_sim.mem_bus.dout <= memory[tt_um_cache_coherence_sim.mem_bus.addr];
				end
		end
	endgenerate
	assign u_main_mem.clk = clk;
	assign u_main_mem.rst_n = rst_n;
	assign u_main_mem.loading = loading;
	wire _unused = &{ena, 1'b0};
endmodule
