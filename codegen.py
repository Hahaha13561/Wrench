class CodeGen:
    def __init__(self, semantic_analyzer=None):
        self.assembly = []
        self.functions_code = [] # Serbest fonksiyonlar ve metotların bağımsız bloğu
        self.current_func_exit_label = None # Ortak çıkış etiketi
        self.environments = [{}] # Hafıza offset'lerini tutan Symbol Table
        self.stack_offset = 0 # RAM'de kaç bayt aşağı inildiği (Offset Tracker)
        self.label_count = 0 # Label sayacı
        self.data_section = [] # Statik metin verilerinin tutulacağı kısım
        self.string_count = 0 # String etiketleri sayacı
        self.class_layouts = {} # Sınıf boyutları
        self.type_environments = [{}]
        self.current_class = None
        self.loop_stack = []
        self.function_return_types = {}
        self.method_return_types = {}
        self.semantic_analyzer = semantic_analyzer

        if semantic_analyzer:
            self.sync_semantic(semantic_analyzer)

    def sync_semantic(self, sem):
        """Passes all the function, method, and class types collected by Semantic Analyzer to CodeGen."""
        self.semantic_analyzer = sem

        if hasattr(sem, 'functions'):
            for f_name, f_info in sem.functions.items():
                if isinstance(f_info, dict):
                    self.function_return_types[f_name] = f_info.get('return_type', 'unit')
                elif hasattr(f_info, 'return_type'):
                    self.function_return_types[f_name] = f_info.return_type

        if hasattr(sem, 'classes'):
            for c_name, c_info in sem.classes.items():
                methods = c_info.get('methods', {}) if isinstance(c_info, dict) else getattr(c_info, 'methods', {})
                for m_name, m_info in methods.items():
                    m_ret = m_info.get('return_type', 'unit') if isinstance(m_info, dict) else getattr(m_info, 'return_type', 'unit')
                    self.method_return_types[(c_name, m_name)] = m_ret

    def generate(self, node):
        """Executes the appropriate function based on the type of Node in the tree."""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generate_branch(self, cond_node, false_label):
        """Turns the Condition Statements into Inverse JMP instructions."""

        #If the condition is a BinOp:
        if type(cond_node).__name__ == 'BinOpNode':
            op = cond_node.op_tok[1]
            op_type = getattr(cond_node, 'operand_type', getattr(cond_node.left_node, 'eval_type', 'int'))

            #Integer comparisions
            if op_type in ('int', 'integer', 'bool', 'ptr', 'pointer') and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                self.generate(cond_node.left_node)
                self.assembly.append("    push rax")
                self.generate(cond_node.right_node)
                self.assembly.append("    mov rbx, rax")
                self.assembly.append("    pop rax")
                self.assembly.append("    cmp rax, rbx")

                #Inverse jumps
                if op in ('=?', '?=', 'is', 'same'): self.assembly.append(f"    jne {false_label}")
                elif op in ('!=', '=!'):            self.assembly.append(f"    je {false_label}")
                elif op == '>':                     self.assembly.append(f"    jle {false_label}")
                elif op == '<':                     self.assembly.append(f"    jge {false_label}")
                elif op in ('>=', '=>'):            self.assembly.append(f"    jl {false_label}")
                elif op in ('<=', '=<'):            self.assembly.append(f"    jg {false_label}")
                return

            #Float/Double Comparisions
            elif op_type == 'double' and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                self.generate(cond_node.right_node)
                self.assembly.append("    push rax")
                self.generate(cond_node.left_node)
                self.assembly.append("    movq xmm0, rax")
                self.assembly.append("    movq xmm1, [rsp]")
                self.assembly.append("    add rsp, 8")
                self.assembly.append("    ucomisd xmm0, xmm1")

                #Inverse Jumps
                if op in ('=?', '?=', 'is', 'same'): self.assembly.append(f"    jne {false_label}")
                elif op in ('!=', '=!'):            self.assembly.append(f"    je {false_label}")
                elif op == '>':                     self.assembly.append(f"    jbe {false_label}")
                elif op == '<':                     self.assembly.append(f"    jae {false_label}")
                elif op in ('>=', '=>'):            self.assembly.append(f"    jb {false_label}")
                elif op in ('<=', '=<'):            self.assembly.append(f"    ja {false_label}")
                return

            #String Comparisions
            elif op_type in ('str', 'string') and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                self.generate(cond_node.right_node)
                self.assembly.append("    push rax")
                self.generate(cond_node.left_node)
                self.assembly.append("    mov rdi, rax")
                self.assembly.append("    pop rsi")
                self.assembly.append("    call compare_strings")
                self.assembly.append("    test rax, rax")

                #Inverse Jumps
                if op in ('=?', '?=', 'is', 'same'): self.assembly.append(f"    jne {false_label}")
                elif op in ('!=', '=!'):            self.assembly.append(f"    je {false_label}")
                elif op == '>':                     self.assembly.append(f"    jle {false_label}")
                elif op == '<':                     self.assembly.append(f"    jge {false_label}")
                elif op in ('>=', '=>'):            self.assembly.append(f"    jl {false_label}")
                elif op in ('<=', '=<'):            self.assembly.append(f"    jg {false_label}")
                return

        self.generate(cond_node)
        self.assembly.append("    test rax, rax")
        self.assembly.append(f"    je {false_label}")

    def generic_visit(self, node):
        raise Exception (f'ERROR: No Assembly Translation for {type(node).__name__}.')

    def get_code(self):
        """Combines assembly code to produce an executable NASM template."""

        data_code = [
            "section .data",
            "    empty_str db 0",
            "    null_print_msg db `(null)`, 0",
            "    dot_str db `.`, 0",
            "    segfault_msg db `[CRITICAL]: Violated Memory Adress -->`, 0",
            "    unhandled_msg db `[FATAL]: Uncaught Segfault! Program Terminated.`, 10, 0",
            "global_err_frame dq 0",
            "global_argc dq 0",
            "global_argv dq 0",
            "",
            "sigaction_struct:",
            "    dq sigsegv_handler    ; sa_sigaction",
            "    dq 0x44000004    ; sa_flags: SA_SIGINFO (0x4) | SA_RESTORER(0x04000000) | SA_NODEFER (0x40000000)",
            "    dq sig_restorer    ; sa_restorer",
            "    dq 0    ; sa_mask"
        ]

        if self.data_section:
            data_code.extend(self.data_section)
            data_code.append("")

        header = [
            "section .text",
            "global _start",
            "",
            "print_string:",
            "    push rbp",
            "    mov rbp, rsp",
            "    test rax, rax",
            "    je .print_null_str",
            "    mov rbx, rax",
            "    xor ecx, ecx",
            ".strlen_loop:",
            "    cmp byte [rbx + rcx], 0",
            "    je .strlen_done",
            "    inc rcx",
            "    jmp .strlen_loop",
            ".strlen_done:",
            "    mov rdx, rcx",
            "    mov rsi, rbx",
            "    mov edi, 1",
            "    mov eax, 1",
            "    syscall",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".print_null_str:",
            "    mov eax, 1",
            "    mov edi, 1",
            "    lea rsi, [rel null_print_msg]",
            "    mov edx, 6",
            "    syscall",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "print_int:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    sub rsp, 32",
            "    mov ebx, 10",
            "    xor ecx, ecx",
            "    xor r8d, r8d",
            "    test rax, rax",
            "    jge .divide_loop",
            "    neg rax",
            "    mov r8d, 1",
            ".divide_loop:",
            "    xor edx, edx",
            "    div rbx",
            "    add rdx, 48",
            "    push rdx",
            "    inc rcx",
            "    test rax, rax",
            "    jne .divide_loop",
            "    cmp r8, 1",
            "    jne .pop_chars",
            "    push 45",
            "    inc rcx",
            ".pop_chars:",
            "    xor edi, edi",
            ".pop_loop:",
            "    cmp rdi, rcx",
            "    je .print_num",
            "    pop rax",
            "    mov byte [rbp - 32 + rdi], al",
            "    inc rdi",
            "    jmp .pop_loop",
            ".print_num:",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    lea rsi, [rbp - 32]",
            "    mov rdx, rcx",
            "    syscall",
            "    add rsp, 32",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "print_hex:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rsp, 32",
            "    mov byte [rbp - 32], 48",
            "    mov byte [rbp - 31], 120",
            "    mov ecx, 16",
            "    mov ebx, 2",
            ".hex_loop:",
            "    mov rdx, rax",
            "    shr rdx, 60",
            "    and rdx, 0xF",
            "    cmp dl, 9",
            "    jle .is_num",
            "    add dl, 87",
            "    jmp .store_hex",
            ".is_num:",
            "    add dl, 48",
            ".store_hex:",
            "    mov byte [rbp - 32 + rbx], dl",
            "    inc rbx",
            "    shl rax, 4",
            "    dec rcx",
            "    jnz .hex_loop",
            "    mov byte [rbp - 32 + rbx], 0",
            "",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    lea rsi, [rbp - 32]",
            "    mov rdx, 18",
            "    syscall",
            "    add rsp, 32",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "sigsegv_handler:",
            "    mov rax, qword [rsi + 16]",
            "    mov rbx, qword [rel global_err_frame]",
            "    cmp rbx, 0",
            "    je .unhandled_segfault",
            "    mov rcx, qword [rbx + 24]",
            "    mov qword [rel global_err_frame], rcx",
            "    mov rdx, qword [rbx + 16]",
            "    mov rbp, qword [rbx + 8]",
            "    mov rsp, qword [rbx]",
            "    jmp rdx",
            "",
            ".unhandled_segfault:",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    lea rsi, [rel unhandled_msg]",
            "    mov rdx, 56",
            "    syscall",
            "    mov eax, 60",
            "    mov rdi, 139",
            "    syscall",
            "",
            "sig_restorer:",
            "    mov rax, 15",
            "    syscall",
            "",
            "print_float:",
            "    push rbp",
            "    mov rbp, rsp",
            "    movq xmm0, rax",
            "    sub rsp, 16",
            "    movsd [rsp], xmm0",
            "    cvttsd2si rbx, xmm0",
            "    push rbx",
            "    mov rax, rbx",
            "    call print_int",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    lea rsi, [rel dot_str]",
            "    mov rdx, 1",
            "    syscall",
            "    movsd xmm0, [rsp]",
            "    add rsp, 16",
            "    cvtsi2sd xmm1, rbx",
            "    subsd xmm0, xmm1",
            "    mov rax, 100000",
            "    cvtsi2sd xmm1, rax",
            "    mulsd xmm0, xmm1",
            "    cvttsd2si rax, xmm0",
            "    test rax, rax",
            "    jge .print_frac",
            "    neg rax",
            ".print_frac:",
            "    call print_int",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "concat_strings:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    cmp rdi, 0",
            "    jne .check_rsi",
            "    lea rdi, [rel empty_str]",
            ".check_rsi:",
            "    cmp rsi, 0",
            "    jne .do_concat",
            "    lea rsi, [rel empty_str]",
            ".do_concat:",
            "    push rdi",
            "    push rsi",
            "    xor ebx, ebx",
            ".len1:",
            "    cmp byte [rdi + rbx], 0",
            "    je .len1_done",
            "    inc rbx",
            "    jmp .len1",
            ".len1_done:",
            "    xor ecx, ecx",
            ".len2:",
            "    cmp byte [rsi + rcx], 0",
            "    je .len2_done",
            "    inc rcx",
            "    jmp .len2",
            ".len2_done:",
            "    mov rax, rbx",
            "    add rax, rcx",
            "    inc rax",
            "    push rax",
            "    push rbx",
            "    push rcx",
            "    mov rdi, rax",
            "    call alloc",
            "    mov r8, rax",
            "    pop rcx",
            "    pop rbx",
            "    pop rax",
            "    pop rsi",
            "    pop rdi",
            "    xor r9d, r9d",
            ".copy1:",
            "    cmp r9, rbx",
            "    je .copy1_done",
            "    mov dl, byte [rdi + r9]",
            "    mov byte [r8 + r9], dl",
            "    inc r9",
            "    jmp .copy1",
            ".copy1_done:",
            "    xor r10d, r10d",
            "    lea r11, [r8 + rbx]",
            ".copy2:",
            "    cmp r10, rcx",
            "    je .copy2_done",
            "    mov dl, byte [rsi + r10]",
            "    mov byte [r11 + r10], dl",
            "    inc r10",
            "    jmp .copy2",
            ".copy2_done:",
            "    mov byte [r11 + rcx], 0",
            "    mov rax, r8",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "compare_strings:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    test rdi, rdi",
            "    je .cmp_rdi_null",
            "    test rsi, rsi",
            "    je .cmp_rsi_null",
            "    xor ecx, ecx",
            ".cmp_loop:",
            "    mov al, byte [rdi + rcx]",
            "    mov bl, byte [rsi + rcx]",
            "    cmp al, bl",
            "    jne .cmp_diff",
            "    cmp al, 0",
            "    je .cmp_equal",
            "    inc rcx",
            "    jmp .cmp_loop",
            ".cmp_diff:",
            "    ja .cmp_greater",
            "    mov rax, -1",
            "    jmp .cmp_exit",
            ".cmp_greater:",
            "    mov rax, 1",
            "    jmp .cmp_exit",
            ".cmp_equal:",
            "    xor eax, eax",
            "    jmp .cmp_exit",
            ".cmp_rdi_null:",
            "    cmp rsi, 0",
            "    je .cmp_equal",
            "    mov rax, -1",
            "    jmp .cmp_exit",
            ".cmp_rsi_null:",
            "    mov rax, 1",
            ".cmp_exit:",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "int_to_str:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    mov rax, rdi",
            "    mov edi, 32",
            "    push rax",
            "    call alloc",
            "    pop rcx",
            "    mov r8, rax",
            "    test rcx, rcx",
            "    jne .check_neg",
            "    mov byte [r8], 48",
            "    mov byte [r8+1], 0",
            "    mov rax, r8",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".check_neg:",
            "    xor r9d, r9d",
            "    cmp rcx, 0",
            "    jge .conv_setup",
            "    neg rcx",
            "    mov r9, 1",
            ".conv_setup:",
            "    mov rax, rcx",
            "    mov rbx, 10",
            "    xor r10d, r10d",
            ".conv_loop:",
            "    test rax, rax",
            "    je .pop_dig",
            "    xor edx, edx",
            "    div rbx",
            "    add rdx, 48",
            "    push rdx",
            "    inc r10",
            "    jmp .conv_loop",
            ".pop_dig:",
            "    xor r11d, r11d",
            "    cmp r9, 1",
            "    jne .pop_loop",
            "    mov byte [r8 + r11], 45",
            "    inc r11",
            ".pop_loop:",
            "    cmp r10, 0",
            "    je .done_str",
            "    pop rdx",
            "    mov byte [r8 + r11], dl",
            "    inc r11",
            "    dec r10",
            "    jmp .pop_loop",
            ".done_str:",
            "    mov byte [r8 + r11], 0",
            "    mov rax, r8",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "read_input:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rax",
            "    xor edi, edi",
            "    mov rsi, rax",
            "    mov rdx, 3",
            "    mov r10, 34",
            "    mov r8, -1",
            "    xor r9d, r9d",
            "    mov eax, 9",
            "    syscall",
            "    mov rsi, rax",
            "    push rsi",
            "    xor edi, edi",
            "    mov rdx, [rbp - 8]",
            "    xor eax, eax",
            "    syscall",
            "    pop rsi",
            "    test rax, rax",
            "    jle .read_done",
            "    mov byte [rsi + rax - 1], 0",
            ".read_done:",
            "    mov rax, rsi",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "read_int:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    sub rsp, 32",
            "    xor eax, eax",
            "    xor edi, edi",
            "    lea rsi, [rbp - 40]",
            "    mov rdx, 31",
            "    syscall",
            "    xor ecx, ecx",
            "    xor ebx, ebx",
            "    xor r8d, r8d",
            "    cmp byte [rbp - 40], 45",
            "    jne .atoi_loop",
            "    mov r8, 1",
            "    inc rcx",
            ".atoi_loop:",
            "    movzx rax, byte [rbp - 40 + rcx]",
            "    cmp rax, 10",
            "    je .atoi_done",
            "    test rax, rax",
            "    je .atoi_done",
            "    cmp rax, 48",
            "    jl .atoi_done",
            "    cmp rax, 57",
            "    jg .atoi_done",
            "    sub rax, 48",
            "    imul rbx, 10",
            "    add rbx, rax",
            "    inc rcx",
            "    jmp .atoi_loop",
            ".atoi_done:",
            "    mov rax, rbx",
            "    cmp r8, 1",
            "    jne .read_int_exit",
            "    neg rax",
            ".read_int_exit:",
            "    add rsp, 32",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "str_to_int:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rbx",
            "    xor ecx, ecx",
            "    xor ebx, ebx",
            "    xor r8d, r8d",
            "    cmp byte [rdi], 45",
            "    jne .parse_loop",
            "    mov r8, 1",
            "    inc rcx",
            ".parse_loop:",
            "    movzx rax, byte [rdi + rcx]",
            "    test rax, rax",
            "    je .parse_done",
            "    cmp rax, 48",
            "    jl .parse_error",
            "    cmp rax, 57",
            "    jg .parse_error",
            "    sub rax, 48",
            "    imul rbx, 10",
            "    add rbx, rax",
            "    inc rcx",
            "    jmp .parse_loop",
            ".parse_done:",
            "    mov rax, rbx",
            "    cmp r8, 1",
            "    jne .parse_exit",
            "    neg rax",
            ".parse_exit:",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".parse_error:",
            "    xor eax, eax",
            "    pop rbx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "int_pow:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rcx, rsi",
            "    mov rax, 1",
            "    test rcx, rcx",
            "    jle .pow_done",
            ".pow_loop:",
            "    imul rax, rdi",
            "    dec rcx",
            "    jnz .pow_loop",
            ".pow_done:",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "float_pow:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rsp, 16",
            "    movsd [rsp], xmm0",
            "    movsd [rsp+8], xmm1",
            "    fld qword [rsp+8]",
            "    fld qword [rsp]",
            "    fyl2x",
            "    fld st0",
            "    frndint",
            "    fsub st1, st0",
            "    fxch st1",
            "    f2xm1",
            "    fld1",
            "    faddp st1, st0",
            "    fscale",
            "    fstp st1",
            "    fstp qword [rsp]",
            "    movsd xmm0, [rsp]",
            "    add rsp, 16",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "alloc:",
            "    push rbp",
            "    mov rbp, rsp",
            "    add rdi, 8",
            "    push rdi",
            "    mov rsi, rdi",
            "    xor edi, edi",
            "    mov rdx, 3",
            "    mov r10, 34",
            "    mov r8, -1",
            "    xor r9d, r9d",
            "    mov eax, 9",
            "    syscall",
            "    test rax, rax",
            "    js .alloc_failed",
            "    push rax",
            "    mov rdi, rax",
            "    mov rcx, [rbp -8]",
            "    xor al, al",
            "    rep stosb",
            "    pop rax",
            "    mov rcx, [rbp - 8]",
            "    sub rcx, 8",
            "    mov qword [rax], rcx",
            "    add rax, 8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".alloc_failed:",
            "    pop rdi",
            "    xor eax, eax",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "free:",
            "    push rbp",
            "    mov rbp, rsp",
            "    test rdi, rdi",
            "    jz .free_done",
            "    sub rdi, 8",
            "    mov rsi, qword [rdi]",
            "    add rsi, 8",
            "    mov rax, 11",
            "    syscall",
            ".free_done:",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "set_mem:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov qword [rdi + rsi], rdx",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "get_mem:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rax, qword [rdi + rsi]",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "get_mem32:",
            "    push rbp",
            "    mov rbp, rsp",
            "    movsxd rax, dword [rdi + rsi]",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "get_len:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rdi, 8",
            "    mov rax, qword [rdi]",
            "    shr rax, 3",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "realloc_mem:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rdi, 8",
            "    mov rcx, qword [rdi]",
            "    add rcx, 8",
            "    mov rdx, rsi",
            "    add rdx, 8",
            "    mov rsi, rcx",
            "    mov r10, 1",
            "    mov rax, 25",
            "    syscall",
            "    sub rdx, 8",
            "    mov qword [rax], rdx",
            "    add rax, 8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "exit_prog:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov eax, 60",
            "    syscall" 
            ]

        start_section = [
            "",
            "_start:",
            "    mov rax, qword [rsp]",
            "    mov qword [rel global_argc], rax",
            "    lea rax, [rsp + 8]",
            "    mov qword [rel global_argv], rax",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rdi, 11",
            "    lea rsi, [rel sigaction_struct]",
            "    mov rdx, 0",
            "    mov r10, 8",
            "    mov rax, 13",
            "    syscall"
        ]
        
        footer = [
            "",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ; Program Exit (Syscall 60)",
            "    mov eax, 60",
            "    xor edi, edi",
            "    syscall"
        ]

        return "\n".join(data_code + header + self.functions_code + start_section + self.assembly + footer)
        
    def get_new_label(self, base_name):
        self.label_count += 1
        return f"{base_name}_{self.label_count}"

    def get_var_offset(self, var_name):
        """Searches for the variable backward, starting from the innermost (new) Scope."""
        for env in reversed(self.environments):
            if var_name in env:
                return env[var_name]
        return None

    def get_var_type(self, var_name):
        """Finds the class of the variable."""
        for env in reversed(self.type_environments):
            if var_name in env:
                return env[var_name]
        return None 

    def get_var_loc(self, var_name):
        for i in range(len(self.environments)-1, -1, -1):
            env = self.environments[i]
            if var_name in env:
                val = env[var_name]
                if isinstance(val, str) and val.startswith("gvar_"):
                    return f"qword [rel {val}]"
                else:
                    return f"qword [rbp - {val}]"
        return None

    def _get_obj_type(self, node):
        if node is None:
            return None

        node_class = type(node).__name__
        eval_t = getattr(node, 'eval_type', None)

        if eval_t and eval_t not in ('any', 'var', 'unknown', None):
            return eval_t

        if node_class == 'VarAccessNode':
            var_name = node.var_name_tok[1]
            vtype = self.get_var_type(var_name)
            if not vtype and self.semantic_analyzer:
                lookup_fn = getattr(self.semantic_analyzer, 'lookup_var_type', None)
                if callable(lookup_fn):
                    vtype = lookup_fn(var_name)
            return vtype

        elif node_class == 'MemberAccessNode':
            parent_type = self._get_obj_type(node.left_node)
            member_name = node.member_name_tok[1]
            if parent_type and parent_type in self.class_layouts:
                field_info = self.class_layouts[parent_type]['layout'].get(member_name)
                if field_info:
                    return field_info.get('type')

        elif node_class == 'FuncCallNode':
            func_name = node.node_to_call.var_name_tok[1]
            ret_type = self.function_return_types.get(func_name)
            if not ret_type and self.semantic_analyzer and hasattr(self.semantic_analyzer, 'functions'):
                f_info = self.semantic_analyzer.functions.get(func_name)
                if isinstance(f_info, dict):
                    ret_type = f_info.get('return_type')
            return ret_type

        elif node_class == 'MethodCallNode':
            parent_type = self._get_obj_type(node.left_node)
            method_name = node.method_name_tok[1]
            while parent_type:
                ret_type = self.method_return_types.get((parent_type, method_name))
                if ret_type:
                    return ret_type
                parent_info = self.class_layouts.get(parent_type)
                parent_type = parent_info.get('parent') if parent_info else None

        elif node_class == 'NewObjectNode':
            c_name = node.class_name_tok[1]
            return c_name

        return None

    def _parse_format_string(self, raw_fmt):
        """Splits the format text into static text ('TEXT') and dynamic fields ('PLACEHOLDER')."""
        chunks = []
        i = 0
        n = len(raw_fmt)
        current_text = ""

        while i < n:
            if raw_fmt[i] == '\\' and i + 1 < n and raw_fmt[i+1] in ('{', '}'):
                current_text += raw_fmt[i + 1]
                i += 2
                continue

            if raw_fmt[i] == '{':
                if current_text:
                    chunks.append(('TEXT', current_text))
                    current_text = ""

                i += 1
                expr_parts = []
                specifiers = []
                depth = 1
                inside_spec = False
                current_buf = ""

                while i < n and depth > 0:

                    if raw_fmt[i] == '\\' and i + 1 < n and raw_fmt[i + 1] in ('{', '}'):
                        current_buf += raw_fmt[i + 1]
                        i += 2
                        continue

                    if raw_fmt[i] == '{':
                        if i + 1 < n and raw_fmt[i + 1] == ':':
                            if not inside_spec:
                                expr_parts.append(current_buf.strip())
                                inside_spec = True
                            else:
                                if current_buf.strip():
                                    specifiers.append(current_buf.strip())
                            current_buf = ""
                            depth += 1
                            i += 2  
                            continue
                        else:
                            depth += 1
                            current_buf += '{'
                            i += 1
                            continue

                    elif raw_fmt[i] == '}':
                        depth -= 1
                        if depth == 0:
                            if inside_spec:
                                if current_buf.strip():
                                    specifiers.append(current_buf.strip())
                            else:
                                expr_parts.append(current_buf.strip())
                            current_buf = ""
                        else:
                            if inside_spec:
                                if current_buf.strip():
                                    specifiers.append(current_buf.strip())
                                current_buf = ""
                        i += 1
                        continue

                    else:
                        current_buf += raw_fmt[i]
                        i += 1

                if depth != 0:
                    raise Exception("Syntax Error: Unclosed '{' in format string.")

                main_expr = expr_parts[0] if expr_parts else ""
                chunks.append(('PLACEHOLDER', main_expr, specifiers))
                continue

            current_text += raw_fmt[i]
            i += 1

        if current_text:
            chunks.append(('TEXT', current_text))

        return chunks

    def _build_placeholder_ast(self, expr_str, specifiers, pos_args, pos_idx):
        """Turns the dynamic fields and pipeline functions into AST Nodes."""
        from lexer import tokenize
        from parser import Parser, FuncCallNode, VarAccessNode

        if expr_str:
            tokens = tokenize(expr_str)
            p = Parser(tokens)
            node = p.comp_expr()

        else:
            if pos_idx >= len(pos_args):
                raise Exception("Compile Error: Not enough arguments provided for printf format.")
            node = pos_args[pos_idx]
            pos_idx += 1

        builtin_shortcuts = {'x', 'X', 'd', 'i', 'f', 's', 'c'}
        active_shortcuts = []

        for spec in specifiers:
            if spec in builtin_shortcuts:
                active_shortcuts.append(spec)
            else:
                func_var_node = VarAccessNode(('IDENTIFIER', spec, 0, 0))
                node = FuncCallNode(func_var_node, [node])

        return node, active_shortcuts, pos_idx
       
    def enter_scope(self):
        """Creates a new local scope when a new { is opened."""
        self.environments.append({})
        self.type_environments.append({})

    def exit_scope(self):
        """Closes the last local scope when closed with a }."""
        self.environments.pop()
        self.type_environments.pop()
    # ----- VISITOR FUNCTIONS -----

    def visit_list(self, node_list):
        class_nodes = {node.class_name_tok[1]: node for node in node_list if type(node).__name__ == 'ClassDefNode'}
        registered = set()

        def register(c_name):
            if c_name in registered: return
            c_node = class_nodes[c_name]
            if c_node.parent_class_tok:
                p_name = c_node.parent_class_tok[1]
                if p_name not in class_nodes:
                    raise Exception(f"Compiling Error: Prior Class Not Found")
                register(p_name)
            self.register_class(c_node)
            registered.add(c_name)

        for c_name in class_nodes:
            register(c_name)

        for node in node_list:
            ntype = type(node).__name__
            if ntype == 'FuncDefNode':
                func_name = node.func_name_tok[1]
                ret_tok = getattr(node, 'return_type_tok', None) or getattr(node, 'return_type', None) or getattr(node, 'ret_type', None)
                ret_type = ret_tok[1] if isinstance(ret_tok, tuple) else (str(ret_tok) if ret_tok else 'unit')
                self.function_return_types[func_name] = ret_type

            elif ntype == 'ClassDefNode':
                c_name = node.class_name_tok[1]
                for method in node.methods:
                    m_name = method.func_name_tok[1]
                    ret_tok = getattr(method, 'return_type_tok', None) or getattr(method, 'return_type', None) or getattr(method, 'ret_type', None)
                    m_ret = ret_tok[1] if isinstance(ret_tok, tuple) else (str(ret_tok) if ret_tok else 'unit')
                    self.method_return_types[(c_name, m_name)] = m_ret

        for node in node_list:
            self.generate(node)

    def register_class(self, node):
        class_name = node.class_name_tok[1]
        layout = {}
        methods_info = {}
        current_offset = 0
        has_init = False

        if node.parent_class_tok:
            parent_name = node.parent_class_tok[1]
            parent_layout = self.class_layouts[parent_name]
            current_offset = parent_layout['size'] 
            
            for f_name, f_info in parent_layout['layout'].items():
                layout[f_name] = f_info.copy()
            for m_name, m_info in parent_layout['methods'].items():
                methods_info[m_name] = m_info.copy()
            has_init = parent_layout['has_init']

        for modifier_tok, type_tok, name_tok in node.fields:
            field_name = name_tok[1]
            mod = modifier_tok[1] if modifier_tok else 'public'
            layout[field_name] = {
                'offset': current_offset,
                'modifier': mod,
                'type': type_tok[1] if type_tok else 'var',
                'declared_in': class_name
            }
            current_offset += 8

        for method in node.methods:
            m_name = method.func_name_tok[1]
            m_mod = method.modifier_tok[1] if method.modifier_tok else 'public'
            methods_info[m_name] = {'modifier': m_mod, 'declared_in': class_name}
            if m_name == 'init':
                has_init = True

        self.class_layouts[class_name] = {
            'size': current_offset,
            'layout': layout,
            'methods': methods_info,
            'has_init': has_init,
            'parent': node.parent_class_tok[1] if node.parent_class_tok else None
        }

    def visit_NumberNode(self, node):
        """When visiting a number places it in the RAX register."""
        
        if node.tok[0] == 'FLOAT':
            self.assembly.append(f"    mov rax, __float64__({node.tok[1]})")       
        else:    
            num = int(node.tok[1])
            if 0 <= num <= 2147483647:
                self.assembly.append(f"    mov eax, {node.tok[1]}")
            else:
                self.assembly.append(f"    mov rax, {node.tok[1]}")

    def visit_IfNode(self, node):
        """Turns if, butif and else cases to JMPs."""
        end_label = self.get_new_label("IF_END")
        initial_offset = self.stack_offset

        for condition, block in node.cases:
            next_case_label = self.get_new_label("NEXT_CASE")
            self.stack_offset = initial_offset
            
            self.generate_branch(condition, next_case_label)
            self.generate(block)
            self.assembly.append(f"    jmp {end_label}")
            self.assembly.append(f"{next_case_label}:")

        #Else Case
        if node.else_case:
            self.stack_offset = initial_offset
            self.generate(node.else_case)

        # Public label all cases end at
        self.stack_offset = initial_offset
        self.assembly.append(f"{end_label}:")

    def visit_WhileNode(self, node):
        """While loop."""
        start_label = self.get_new_label("WHILE_START")
        end_label = self.get_new_label("WHILE_END")

        self.loop_stack.append((start_label, end_label))
        self.assembly.append(f"{start_label}:")

        self.generate_branch(node.condition_node, end_label)

        self.generate(node.body_node)        
        self.assembly.append(f"    jmp {start_label}")
        self.assembly.append(f"{end_label}:")

        self.loop_stack.pop()

    def visit_ForNode(self, node):
        var_name = node.var_name_tok[1]
        
        self.enter_scope()
        current_env = self.environments[-1]

        # 1. Allocates space on the stack for hidden variables.
        self.stack_offset += 8
        ptr_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        len_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        idx_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        # 2. The actual loop variable used by the programmer.
        self.stack_offset += 8
        current_env[var_name] = self.stack_offset
        elem_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        # 3. Calculates the Array and saves the pointer.
        self.generate(node.iter_node)
        self.assembly.append(f"    mov qword [rbp - {ptr_offset}], rax")

        # 4. Finds the Array length and saves.
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call get_len")
        self.assembly.append(f"    mov qword [rbp - {len_offset}], rax")

        # 5. Starts Index from 0
        self.assembly.append(f"    mov qword [rbp - {idx_offset}], 0")

        # LOOP START
        start_label = self.get_new_label("FOR_START")
        inc_label = self.get_new_label("FOR_INC")
        end_label = self.get_new_label("FOR_END")

        self.loop_stack.append((inc_label, end_label))

        self.assembly.append(f"{start_label}:")

        # 6. Condition Check
        self.assembly.append(f"    mov rax, qword [rbp - {idx_offset}]")
        self.assembly.append(f"    mov rbx, qword [rbp - {len_offset}]")
        self.assembly.append("    cmp rax, rbx")
        self.assembly.append(f"    jge {end_label}")

        # 7. Pulls the element from the array and assign it to a variable.
        self.assembly.append(f"    mov rbx, qword [rbp - {idx_offset}]")
        self.assembly.append("    shl rbx, 3") # Index*8
        self.assembly.append(f"    mov rax, qword [rbp - {ptr_offset}]")
        self.assembly.append("    mov rcx, qword [rax + rbx]")
        self.assembly.append(f"    mov qword [rbp - {elem_offset}], rcx")

        # 8. Executes code body
        self.generate(node.body)

        # 9. Increases Index by 1 and jumps back to beginning.
        self.assembly.append(f"{inc_label}:")
        self.assembly.append(f"    mov rax, qword [rbp - {idx_offset}]")
        self.assembly.append("    inc rax")
        self.assembly.append(f"    mov qword [rbp - {idx_offset}], rax")
        self.assembly.append(f"    jmp {start_label}")

        # LOOP END
        self.assembly.append(f"{end_label}:")

        self.loop_stack.pop()
        self.exit_scope()

    def visit_ReAssignNode(self, node):
        """Updates the existing variable."""
        var_name = node.var_name_tok[1]

        loc = getattr(self, 'get_var_loc', lambda x: f"qword [rbp - {self.get_var_offset(x)}]")(var_name)
        if not loc or "None" in loc:
            raise RuntimeError(f"{var_name} is not found.")

        self.generate(node.value_node)

        op = node.op_tok[1]

        var_type = self.get_var_type(var_name)
        val_type = getattr(node.value_node, 'eval_type', 'int')

        if var_type in ('str', 'string') or val_type in ('str', 'string'):
            if op in ('+=', '=+'):
                self.assembly.append("    push rax")     
                self.assembly.append(f"    mov rax, {loc}")
                self.assembly.append("    mov rdi, rax") 
                self.assembly.append("    pop rsi")      
                self.assembly.append("    call concat_strings")
                self.assembly.append(f"    mov {loc}, rax")
                return
            elif op in ('='):
                self.assembly.append(f"    mov {loc}, rax")
                return
            else:
                raise Exception("Semantic Error: unsupported operation type on string value")

        if var_type in ('double', 'float') or val_type in ('double', 'float'):
            self.assembly.append("    movq xmm1, rax")        
            self.assembly.append(f"    mov rax, {loc}")       
            self.assembly.append("    movq xmm0, rax")

            if op == '=':
                self.assembly.append(f"    movq {loc}, xmm1")
            elif op in ('+=', '=+'):
                self.assembly.append("    addsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
                self.assembly.append(f"    mov {loc}, rax")
            elif op in ('-=', '=-'):
                self.assembly.append("    subsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
                self.assembly.append(f"    mov {loc}, rax")
            elif op in ('*=', '=*'):
                self.assembly.append("    mulsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
                self.assembly.append(f"    mov {loc}, rax")
            elif op in ('/=', '=/'):
                self.assembly.append("    divsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
                self.assembly.append(f"    mov {loc}, rax")
            return
    
        if op == '=':
            self.assembly.append(f"    mov {loc}, rax")
        elif op in ('+=', '=+'):
            self.assembly.append(f"    add {loc}, rax")
        elif op in ('-=', '=-'):
            self.assembly.append(f"    sub {loc}, rax")
        elif op in ('*=', '=*'):
            self.assembly.append(f"    mov rbx, {loc}")
            self.assembly.append("    imul rax, rbx")
            self.assembly.append(f"    mov {loc}, rax")
        elif op in ('/=','=/'):
            self.assembly.append("    mov rbx, rax")
            self.assembly.append(f"    mov rax, {loc}")
            self.assembly.append("    cqo")
            self.assembly.append("    idiv rbx")
            self.assembly.append(f"    mov {loc}, rax")
        elif op in ('%=', '=%'):
            self.assembly.append("    mov rbx, rax")
            self.assembly.append(f"    mov rax, {loc}")
            self.assembly.append("    cqo")
            self.assembly.append("    idiv rbx")
            self.assembly.append(f"    mov {loc}, rdx") 
        elif op in ('^=', '=^'):
            self.assembly.append("    mov rsi, rax")
            self.assembly.append(f"    mov rdi, {loc}")
            self.assembly.append("    call int_pow")
            self.assembly.append(f"    mov {loc}, rax")

    def visit_AttemptNode(self, node):
        attempt_start = self.get_new_label("ATTEMPT_START")
        exclude_label = self.get_new_label("EXCLUDE")
        final_label = self.get_new_label("FINAL")
        end_label = self.get_new_label("ATTEMPT_END")
        old_stack = self.stack_offset

        self.stack_offset += 8
        off_old_frame = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        off_ex_lbl = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        off_old_rbp = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        off_old_rsp = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.assembly.append("    mov rax, qword [rel global_err_frame]")
        self.assembly.append(f"    mov qword [rbp - {off_old_frame}], rax")
        self.assembly.append(f"    lea rax, [rel {exclude_label}]")
        self.assembly.append(f"    mov qword [rbp - {off_ex_lbl}], rax")               
        self.assembly.append(f"    mov qword [rbp - {off_old_rbp}], rbp")                             
        self.assembly.append("    mov rax, rsp")
        self.assembly.append("    add rax, 32")                          
        self.assembly.append("    push rax")
        self.assembly.append(f"    mov qword [rbp - {off_old_rsp}], rax")

        self.assembly.append(f"    lea rax, [rbp - {off_old_rsp}]")
        self.assembly.append("    mov qword [rel global_err_frame], rax")

        self.assembly.append(f"{attempt_start}:")
        self.generate(node.attempt_body)

        self.assembly.append(f"    mov rax, qword [rbp - {off_old_frame}]")
        self.assembly.append("    mov qword [rel global_err_frame], rax")
        self.assembly.append(f"    jmp {final_label}")

        self.assembly.append(f"{exclude_label}:")
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    sub rsp, 64")

        self.stack_offset = old_stack
        if node.exclude_body:
            self.enter_scope()
            self.stack_offset = 32
            self.environments[-1]['err'] = self.stack_offset
            self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rax")
            
            self.generate(node.exclude_body)
            self.exit_scope()

        else:
            self.assembly.append("    push rax") # Saves the error if no Exclude
            if node.final_body:
                self.generate(node.final_body)
            self.assembly.append("    pop rax")
            
            self.assembly.append("    mov rbx, qword [rel global_err_frame]")
            self.assembly.append("    cmp rbx, 0")
            self.assembly.append(f"    je {end_label}_crash")
            self.assembly.append("    mov rcx, qword [rbx + 24]")
            self.assembly.append("    mov qword [rel global_err_frame], rcx")
            self.assembly.append("    mov rdx, qword [rbx + 16]")
            self.assembly.append("    mov rbp, qword [rbx + 8]")
            self.assembly.append("    mov rsp, qword [rbx]")
            self.assembly.append("    jmp rdx")
            
            self.assembly.append(f"{end_label}_crash:")
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    mov eax, 60")
            self.assembly.append("    syscall")
            self.assembly.append(f"    jmp {end_label}")

        self.assembly.append(f"{final_label}:")
        if node.final_body:
            self.generate(node.final_body)

        self.assembly.append(f"{end_label}:")

    def visit_TriggerNode(self, node):
        self.generate(node.err_value_node)

        self.assembly.append("    mov rbx, qword [rel global_err_frame]")
        self.assembly.append("    cmp rbx, 0")
        crash_label = self.get_new_label("CRASH")
        self.assembly.append(f"    je {crash_label}")

        self.assembly.append("    mov rcx, qword [rbx + 24]")
        self.assembly.append("    mov qword [rel global_err_frame], rcx")
        self.assembly.append("    mov rdx, qword [rbx + 16]") # Exclude Address
        self.assembly.append("    mov rbp, qword [rbx + 8]")  # Old RBP
        self.assembly.append("    mov rsp, qword [rbx]")      # Old RSP
        self.assembly.append("    jmp rdx")

        self.assembly.append(f"{crash_label}:")
        self.assembly.append("    mov rdi, rax") # RDI = Exit/Error Code
        self.assembly.append("    mov eax, 60")  # sys_exit
        self.assembly.append("    syscall")

    def visit_VarAssignNode(self, node):
        var_name = node.var_name_tok[1]
        
        self.generate(node.value_node)
        current_env = self.environments[-1]

        if var_name not in current_env:
            if len(self.environments) == 1:
                label = f"gvar_{var_name}"
                self.data_section.append(f"    {label} dq 0")
                current_env[var_name] = label
            else:
                self.stack_offset += 8
                current_env[var_name] = self.stack_offset
                self.assembly.append("    sub rsp, 8")

        inferred_type = self._get_obj_type(node.value_node)

        if inferred_type and inferred_type not in ('int', 'integer', 'double', 'float', 'bool', 'str', 'string', 'char', 'var', 'any'):
            self.type_environments[-1][var_name] = inferred_type

        loc = self.get_var_loc(var_name)
        self.assembly.append(f"    mov {loc}, rax")

    def visit_VarAccessNode(self, node):
        """Reads the variable value from RAM."""
        var_name = node.var_name_tok[1]
        loc = self.get_var_loc(var_name)
        if loc is None:
            raise RuntimeError(f"{var_name} is not found.")
        self.assembly.append(f"    mov rax, {loc}")

    def visit_BinOpNode(self, node):
        """Reduces mathematics, comparison, and string operations to assembly language."""
        self.generate(node.right_node)
        
        op_type = getattr(node, 'operand_type', getattr(node.left_node, 'eval_type', 'int')) 

        if op_type == 'string':
            # --- STRING ---
            op = node.op_tok[1]
            if op == '+':
                self.assembly.append("    push rax")
                self.generate(node.left_node)
                self.assembly.append("    mov rdi, rax")
                self.assembly.append("    pop rsi")
                self.assembly.append("    call concat_strings")
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.assembly.append("    push rax")
                self.generate(node.left_node)
                self.assembly.append("    mov rdi, rax")
                self.assembly.append("    pop rsi")
                self.assembly.append("    call compare_strings")
                self.assembly.append("    test rax, rax")

                if op in ('=?', '?=', 'is', 'same'): self.assembly.append("    sete al") 
                elif op in ('!=', '=!'): self.assembly.append("    setne al") 
                elif op == '>': self.assembly.append("    setg al") 
                elif op == '<': self.assembly.append("    setl al") 
                elif op in ('>=', '=>'): self.assembly.append("    setge al") 
                elif op in ('<=', '=<'): self.assembly.append("    setle al") 
                self.assembly.append("    movzx rax, al")
            else:
                raise Exception("Semantic Error: Unsupported operation between strings.")
                
        elif op_type == 'double':
            # --- FLOATING POINT NUMBERS ---
            self.assembly.append("    push rax")

            self.generate(node.left_node)

            self.assembly.append("    movq xmm0, rax")
            self.assembly.append("    movq xmm1, [rsp]")
            self.assembly.append("    add rsp, 8") 
            
            op = node.op_tok[1]
            if op == '+':
                self.assembly.append("    addsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
            elif op == '-':
                self.assembly.append("    subsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
            elif op == '*':
                self.assembly.append("    mulsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
            elif op == '/':
                self.assembly.append("    divsd xmm0, xmm1")
                self.assembly.append("    movq rax, xmm0")
            elif op == '%':
                self.assembly.append("    sub rsp, 16")
                self.assembly.append("    movsd [rsp], xmm1")
                self.assembly.append("    fld qword [rsp]")     
                self.assembly.append("    movsd [rsp], xmm0")
                self.assembly.append("    fld qword [rsp]")     
                fprem_loop = self.get_new_label("FPREM_LOOP")
                self.assembly.append(f"{fprem_loop}:")
                self.assembly.append("    fprem")               
                self.assembly.append("    fnstsw ax")
                self.assembly.append("    test ah, 4")          
                self.assembly.append(f"    jnz {fprem_loop}")
                self.assembly.append("    fstp qword [rsp]")    
                self.assembly.append("    movsd xmm0, [rsp]")   
                self.assembly.append("    fstp st0")            
                self.assembly.append("    add rsp, 16")
                self.assembly.append("    movq rax, xmm0")
            elif op == '^':
                self.assembly.append("    call float_pow")
                self.assembly.append("    movq rax, xmm0")
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.assembly.append("    ucomisd xmm0, xmm1")
                
                if op in ('=?', '?=', 'is', 'same'):
                    self.assembly.append("    sete al")
                    self.assembly.append("    setnp bl")
                    self.assembly.append("    and al, bl")
                elif op in ('!=', '=!'):
                    self.assembly.append("    setne al")
                    self.assembly.append("    setp bl")
                    self.assembly.append("    or al, bl")
                elif op == '>': self.assembly.append("    seta al") 
                elif op == '<': self.assembly.append("    setb al") 
                elif op in ('>=', '=>'): self.assembly.append("    setae al") 
                elif op in ('<=', '=<'): self.assembly.append("    setbe al") 
                
                self.assembly.append("    movzx rax, al")

        else:    
            # --- INTEGER NUMBERS ---
            self.assembly.append("    push rax")
            self.generate(node.left_node)
            self.assembly.append("    pop rbx")

            op = node.op_tok[1]
            if op == '+': self.assembly.append("    add rax, rbx")
            elif op == '-': self.assembly.append("    sub rax, rbx")
            elif op == '*': self.assembly.append("    imul rax, rbx")
            elif op == '/': 
                self.assembly.append("    cqo")
                self.assembly.append("    idiv rbx")
            elif op == '%':
                self.assembly.append("    cqo")
                self.assembly.append("    idiv rbx")
                self.assembly.append("    mov rax, rdx")
            elif op == '^':
                self.assembly.append("    mov rdi, rax")
                self.assembly.append("    mov rsi, rbx")
                self.assembly.append("    call int_pow")
            elif op == 'and':
                self.assembly.append("    and rax, rbx")
            elif op == 'or':
                self.assembly.append("    or rax, rbx")
            elif op == 'xor':
                self.assembly.append("    xor rax, rbx")
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.assembly.append("    cmp rax, rbx")

                if op in ('=?', '?=', 'is', 'same'): self.assembly.append("    sete al") 
                elif op in ('!=', '=!'): self.assembly.append("    setne al") 
                elif op == '>': self.assembly.append("    setg al") 
                elif op == '<': self.assembly.append("    setl al") 
                elif op in ('>=', '=>'): self.assembly.append("    setge al") 
                elif op in ('<=', '=<'): self.assembly.append("    setle al") 
                self.assembly.append("    movzx rax, al")

    def visit_UnaryOpNode(self, node):
        op = node.op_tok[1]

        if op == 'not':
            self.generate(node.node)
            self.assembly.append("    test rax, rax")
            self.assembly.append("    sete al")
            self.assembly.append("    movzx rax, al")

        elif op == '-':
            self.generate(node.node)
            op_type = getattr(node, 'operand_type', getattr(node, 'eval_type', getattr(node.node, 'eval_type', 'int')))
            if op_type in ('double', 'float'):
                self.assembly.append("    movq xmm0, rax")
                self.assembly.append("    pxor xmm1, xmm1")
                self.assembly.append("    subsd xmm1, xmm0")
                self.assembly.append("    movq rax, xmm1")
            else:
                self.assembly.append("    neg rax")


        elif op in ('await', 'wait'):
            self.generate(node.node)
            self.assembly.append("    mov rdi, rax") 
            self.assembly.append("    xor esi, esi")   
            self.assembly.append("    xor edx, edx")   
            self.assembly.append("    xor r10d, r10d")   
            self.assembly.append("    mov eax, 61")  
            self.assembly.append("    syscall")

    def visit_BlockNode(self, node):
        """Converts the code blocks (lines) inside curly braces to Assembly in order."""
        self.enter_scope()

        for statement in node.statements:
            self.generate(statement)

        self.exit_scope()

    def visit_FuncCallNode(self, node):
        """Calls the function and creates the Kernel Standard ABI Specifications."""
        func_name = node.node_to_call.var_name_tok[1]

        if func_name == 'print':
            arg_node = node.arg_nodes[0]
            self.generate(arg_node)

            arg_type = getattr(arg_node, 'eval_type', 'string')

            if arg_type in ('any', 'var') and type(arg_node).__name__ == 'MemberAccessNode':
                real_type = self._get_obj_type(arg_node)
                if real_type: arg_type = real_type

            if arg_type in ('hex', 'ptr', 'pointer', 'address'):
                self.assembly.append("    call print_hex")

            elif arg_type in ('int', 'integer', 'bool', 'any', 'var'):
                self.assembly.append("    call print_int")
            elif arg_type in ('double', 'float'):
                self.assembly.append("    call print_float")
            elif arg_type == 'char':
                self.assembly.append("    push rax")
                self.assembly.append("    mov rsi, rsp") # Top of address stack
                self.assembly.append("    mov edi, 1")   # stdout
                self.assembly.append("    mov edx, 1")   # 1 byte length
                self.assembly.append("    mov eax, 1")   # sys_write
                self.assembly.append("    syscall")
                self.assembly.append("    pop rax")
            else:
                self.assembly.append("    call print_string")
            return

        elif func_name == 'printf':
            if not node.arg_nodes:
                return

            fmt_node = node.arg_nodes[0]

            if type(fmt_node).__name__ == 'StringNode':
                raw_str = fmt_node.tok[1][1:-1]
                chunks = self._parse_format_string(raw_str)
                pos_args = node.arg_nodes[1:]
                pos_idx = 0

                from parser import StringNode

                for chunk in chunks:
                    if chunk[0] == 'TEXT':
                        text_content = chunk[1]
                        if text_content:
                            str_node = StringNode(('', f'"{text_content}"', 0, 0))
                            self.generate(str_node)
                            self.assembly.append("    call print_string")
                
                    elif chunk[0] == 'PLACEHOLDER':
                        _, expr_str, specifiers = chunk
                        target_ast, shortcuts, pos_idx = self._build_placeholder_ast(expr_str, specifiers, pos_args, pos_idx)
                    
                        self.generate(target_ast)
                        eval_type = getattr(target_ast, 'eval_type', None) or self._get_obj_type(target_ast) or 'int'


                        if 'x' in shortcuts or 'X' in shortcuts or eval_type in ('hex', 'ptr', 'pointer', 'address'):
                            self.assembly.append("    call print_hex")
                        elif 'f' in shortcuts or eval_type in ('double', 'float'):
                            self.assembly.append("    call print_float")
                        elif 'd' in shortcuts or 'i' in shortcuts or eval_type in ('int', 'integer', 'bool', 'any', 'var'):
                            self.assembly.append("    call print_int")
                        elif eval_type == 'char':
                            self.assembly.append("    push rax")
                            self.assembly.append("    mov rsi, rsp")
                            self.assembly.append("    mov edi, 1")
                            self.assembly.append("    mov edx, 1")
                            self.assembly.append("    mov eax, 1")
                            self.assembly.append("    syscall")
                            self.assembly.append("    pop rax")
                        else:
                            self.assembly.append("    call print_string")
                return

            else:
                for arg in node.arg_nodes:
                    self.generate(arg)
                    eval_type = getattr(arg, 'eval_type', None) or self._get_obj_type(arg) or 'string'

                    if eval_type in ('hex', 'ptr', 'pointer', 'address'):
                        self.assembly.append("    call print_hex")
                    elif eval_type in ('int', 'integer', 'bool'):
                        self.assembly.append("    call print_int")
                    elif eval_type in ('double', 'float'):
                        self.assembly.append("    call print_float")
                    elif eval_type == 'char':
                        self.assembly.append("    push rax")
                        self.assembly.append("    mov rsi, rsp")
                        self.assembly.append("    mov edi, 1")
                        self.assembly.append("    mov edx, 1")
                        self.assembly.append("    mov eax, 1")
                        self.assembly.append("    syscall")
                        self.assembly.append("    pop rax")
                    else:
                        self.assembly.append("    call print_string")
                return


        elif func_name == 'len':
            self.generate(node.arg_nodes[0]) # Take the parameter into RAX
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    call get_len")
            return
        
        elif func_name == 'realloc':
            self.generate(node.arg_nodes[1]) # Second parameter (new size)
            self.assembly.append("    push rax")
            self.generate(node.arg_nodes[0]) # First parameter (old pointer)
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    pop rsi") # Pull the second parameter into RSI
            self.assembly.append("    call realloc_mem")
            return

        elif func_name == 'type_of':
            # Take the AST node of the parameter
            arg_node = node.arg_nodes[0]
            
            # Read eval_type
            detected_type = getattr(arg_node, 'eval_type', 'unknown')
            
            from parser import StringNode
            type_str_node = StringNode(('', f'"{detected_type}"', 0, 0))
            self.visit_StringNode(type_str_node)
            return

        elif func_name == 'read':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    call read_input")
            return
        
        elif func_name == 'read_int':
            self.assembly.append("    call read_int")
            return
        
        elif func_name == 'print_float':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    call print_float")
            return

        elif func_name == 'print_hex':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    call print_hex")
            return

        elif func_name == 'exit':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    call exit_prog")
            return
        
        elif func_name == 'alloc':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    call alloc")
            return

        elif func_name == 'sys_argc':
            self.assembly.append("    mov rax, qword [rel global_argc]")
            return

        elif func_name == 'sys_argv':
            self.generate(node.arg_nodes[0])
            self.assembly.append("    mov rbx, qword [rel global_argv]")
            self.assembly.append("    mov rax, qword [rbx + rax*8]")
            return

        elif func_name == 'get_mem':
            self.generate(node.arg_nodes[1])  # offset -> RAX
            self.assembly.append("    push rax")
            self.generate(node.arg_nodes[0])  # ptr -> RAX
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    pop rsi")
            self.assembly.append("    call get_mem")
            return

        elif func_name == 'get_mem32':
            self.generate(node.arg_nodes[1])  # offset -> RAX
            self.assembly.append("    push rax")
            self.generate(node.arg_nodes[0])  # ptr -> RAX
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    pop rsi")
            self.assembly.append("    call get_mem32")
            return

        elif func_name == 'addr_of' or func_name == 'ptr_to':
            self.generate(node.arg_nodes[0])
            return
        
        elif func_name == 'syscall':
            arg_count = len(node.arg_nodes)
            if arg_count > 7:
                raise Exception("Compiling Error: syscall can take 7 arguments max (rax, rdi, rsi, rdx, r10, r8, r9)")
            arg_registers = ['rax', 'rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9']

            for arg in node.arg_nodes:
                self.generate(arg)
                self.assembly.append("    push rax")

            for i in range(arg_count-1 , -1, -1):
                target_reg = arg_registers[i]
                self.assembly.append(f"    pop {target_reg}")

            self.assembly.append("    syscall")
            return

        arg_count = len(node.arg_nodes)
        
        if arg_count > 6:
            for i in range(arg_count -1, 5, -1):
                self.generate(node.arg_nodes[i])
                self.assembly.append("    push rax")


        # x86-64 Standard Parameter Registers 
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        for i in range(min(6, arg_count)):
            self.generate(node.arg_nodes[i])
            self.assembly.append(f"    push rax")

        for i in range(min(6, arg_count)-1, -1, -1):
            self.assembly.append(f"    pop {arg_registers[i]}") 

        loc = self.get_var_loc(func_name)
        if loc is not None:
            self.assembly.append(f"    mov rax, {loc}")
            self.assembly.append("    call rax")
        else:
            self.assembly.append(f"    call {func_name}")

        extra_args = max(0, arg_count - 6)
        if extra_args > 0:
            self.assembly.append(f"    add rsp, {extra_args * 8}")

    def visit_FuncDefNode(self, node):
        """Creates a new function and configures Scope settings."""
        if node.modifier_tok and node.modifier_tok[1] == 'extern':
            func_name = node.func_name_tok[1]
            self.data_section.append(f"; extern {func_name}")
            return

        func_name = node.func_name_tok[1]
        exit_label = f"exit_func_{func_name}"

        main_assembly = self.assembly
        self.assembly = self.functions_code

        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_label
        self.assembly.append("")
        self.assembly.append(f"{func_name}")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")

        is_async = (node.modifier_tok and node.modifier_tok[1] == 'async')

        if is_async:
            self.assembly.append("    mov rax, 57")
            self.assembly.append("    syscall")
            self.assembly.append("    test rax, rax")

            parent_label = self.get_new_label(f"ASYNC_PARENT_{func_name}")
            self.assembly.append(f"    jne {parent_label}")

        old_stack_offset = self.stack_offset
        self.stack_offset = 0

        self.enter_scope()
        current_env = self.environments[-1]
        type_env = self.type_environments[-1]
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            type_env[arg_name] = arg_type[1]
            self.assembly.append("    sub rsp, 8")
            if i < 6:
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], {arg_registers[i]}")
            else:
                read_offset = 16 + (i - 6) * 8
                self.assembly.append(f"    mov rax, qword [rbp + {read_offset}]")
                self.assembly.append(f"    mov qword [rbp -{self.stack_offset}], rax ")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack_offset

        self.assembly.append(f"{exit_label}:")
        if is_async:
            self.assembly.append("    mov rdi, 0")
            self.assembly.append("    mov eax, 60") # sys_exit
            self.assembly.append("    syscall")
            self.assembly.append(f"{parent_label}:")
            self.assembly.append("    mov rsp, rbp")
            self.assembly.append("    pop rbp")
            self.assembly.append("    ret")
        else:
            self.assembly.append("    mov rsp, rbp")
            self.assembly.append("    pop rbp")
            self.assembly.append("    ret")

        self.current_func_exit_label = old_exit_label
        self.assembly = main_assembly

    def visit_AnFuncNode(self, node):
        func_lbl = self.get_new_label("ANON_FUNC")
        exit_lbl = f".exit_{func_lbl}"

        main_assembly = self.assembly
        self.assembly = self.functions_code

        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_lbl
        
        self.assembly.append("")
        self.assembly.append(f"{func_lbl}:")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")
        
        old_stack = self.stack_offset
        self.stack_offset = 0
        self.enter_scope()
        current_env = self.environments[-1]
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        
        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            self.assembly.append("    sub rsp, 8")
            if i < 6:
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], {arg_registers[i]}")
            else:
                read_offset = 16 + (i - 6) * 8
                self.assembly.append(f"    mov rax, qword [rbp + {read_offset}]")
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rax")
        
        self.generate(node.body_node)
        
        self.exit_scope()
        self.stack_offset = old_stack

        self.assembly.append(f"{exit_lbl}:")
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")
        
        self.current_func_exit_label = old_exit_label
        self.assembly = main_assembly
        
        self.assembly.append(f"    lea rax, [rel {func_lbl}]")

    def visit_ReturnNode(self, node):
        """Returns a value from the function."""
        if node.node_to_return:
            self.generate(node.node_to_return)

        if self.current_func_exit_label:
            self.assembly.append(f"    jmp {self.current_func_exit_label}")
        else:
            self.assembly.append("    mov rsp, rbp")
            self.assembly.append("    pop rbp")
            self.assembly.append("    ret")

    def visit_StringNode(self, node):
        """Writes the text data as a .data file and places the address in RAX."""
        self.string_count += 1
        label = f"str_{self.string_count}"

        #Tırnakları at
        raw_str = node.tok[1][1:-1]

        self.data_section.append(f"    {label} db `{raw_str}`, 0")

        self.assembly.append(f"    mov rax, {label}")

    def visit_SyncUnitNode(self, node):
        unit_name = node.unit_name_tok[1]
        exit_lbl = f".exit_unit_{unit_name}"

        main_assembly = self.assembly
        self.assembly = self.functions_code

        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_lbl
        
        self.assembly.append("")
        self.assembly.append(f"unit_{unit_name}:")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")
        
        self.enter_scope()
        self.generate(node.body_node)
        self.exit_scope()

        self.assembly.append(f"{exit_lbl}:")
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")

        self.current_func_exit_label = old_exit_label
        self.assembly = main_assembly

    def visit_WithNode(self, node):
        unit_name = node.unit_name_tok[1]
        if not node.is_wait:
            self.assembly.append("    mov eax, 57") 
            self.assembly.append("    syscall")
            self.assembly.append("    test rax, rax")
            parent_lbl = self.get_new_label("WITH_PARENT")
            self.assembly.append(f"    jne {parent_lbl}") 

            self.assembly.append(f"    call unit_{unit_name}")
            self.generate(node.body_node)

            self.assembly.append("    mov eax, 60")
            self.assembly.append("    xor edi, edi")
            self.assembly.append("    syscall")
            
            self.assembly.append(f"{parent_lbl}:")

        else:
            self.assembly.append(f"    call unit_{unit_name}")
            self.generate(node.body_node)

    def visit_KeywordNode(self, node):
        """Converts True, False, and Null to Binary."""
        val = node.tok[1]
        if val == 'true':
            self.assembly.append("    mov rax, 1")
        elif val in ('false', 'null'):
            self.assembly.append("    xor eax, eax")

    def visit_WhenNode(self, node):
        self.assembly.append("    mov eax, 57") 
        self.assembly.append("    syscall")
        self.assembly.append("    test rax, rax")

        parent_lbl = self.get_new_label("WHEN_PARENT")
        self.assembly.append(f"    jne {parent_lbl}")

        loop_lbl = self.get_new_label("WHEN_LOOP")
        self.assembly.append(f"{loop_lbl}:")

        self.assembly.append("    sub rsp, 16")
        self.assembly.append("    mov qword [rsp], 0")          
        self.assembly.append("    mov qword [rsp+8], 10000000") 
        self.assembly.append("    mov rdi, rsp")
        self.assembly.append("    xor esi, esi")
        self.assembly.append("    mov eax, 35") 
        self.assembly.append("    syscall")
        self.assembly.append("    add rsp, 16")

        self.generate(node.condition)
        self.assembly.append("    test rax, rax")
        self.assembly.append(f"    je {loop_lbl}")

        self.generate(node.body)
        
        self.assembly.append("    mov eax, 60")
        self.assembly.append("    xor edi, edi")
        self.assembly.append("    syscall")
        
        self.assembly.append(f"{parent_lbl}:")

    def visit_IndexAccessNode(self, node):
        eval_type = getattr(node, 'eval_type', 'any')
        
        self.generate(node.index_node)
        self.assembly.append("    push rax")

        self.generate(node.left_node)
        self.assembly.append("    pop rbx") # RBX = index

        bounds_fail = self.get_new_label("BOUNDS_FAIL")
        bounds_ok = self.get_new_label("BOUNDS_OK")

        self.assembly.append("    test rbx, rbx")
        self.assembly.append(f"    js {bounds_fail}") 

        if eval_type == 'char':
            self.assembly.append(f"    jmp {bounds_ok}")
        else:   
            self.assembly.append("    mov rcx, qword [rax -8]")
            self.assembly.append("    shr rcx, 3")
            self.assembly.append("    cmp rbx, rcx")
            self.assembly.append(f"    jge {bounds_fail}") # Fail if Index >= Size
            self.assembly.append(f"    jmp {bounds_ok}")

        self.assembly.append(f"{bounds_fail}:")
        self.assembly.append("    mov eax, 99") # OUT OF BOUNDS
        self.assembly.append("    mov rbx, qword [rel global_err_frame]")
        self.assembly.append("    cmp rbx, 0")
        crash_lbl = self.get_new_label("CRASH")
        self.assembly.append(f"    je {crash_lbl}") # Crash if no catch backup
        self.assembly.append("    mov rcx, qword [rbx + 24]")
        self.assembly.append("    mov qword [rel global_err_frame], rcx")
        self.assembly.append("    mov rdx, qword [rbx + 16]")
        self.assembly.append("    mov rbp, qword [rbx + 8]")
        self.assembly.append("    mov rsp, qword [rbx]")
        self.assembly.append("    jmp rdx") # Go to exclude
        
        self.assembly.append(f"{crash_lbl}:")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    mov eax, 60")
        self.assembly.append("    syscall") # Crash

        self.assembly.append(f"{bounds_ok}:")

        if eval_type == 'char':
            # Read 1 byte for a char
            self.assembly.append("    movzx rax, byte [rax + rbx]")
        else:
            self.assembly.append("    shl rbx, 3") # rbx*8
            self.assembly.append("    mov rax, qword [rax + rbx]")

    def visit_IndexAssignNode(self, node):
        eval_type = getattr(node, 'eval_type', 'any')
        
        self.generate(node.value_node)
        self.assembly.append("    push rax")     

        self.generate(node.index_node)
        self.assembly.append("    push rax")

        self.generate(node.left_node)           
        self.assembly.append("    pop rbx")      # RBX = index
        self.assembly.append("    pop rcx")      # RCX = new value

        bounds_fail = self.get_new_label("BOUNDS_FAIL")
        bounds_ok = self.get_new_label("BOUNDS_OK")
        
        self.assembly.append("    test rbx, rbx")
        self.assembly.append(f"    js {bounds_fail}") 
         
        if eval_type == 'char':
            self.assembly.append(f"    jmp {bounds_ok}")
        else:
            self.assembly.append("    mov r8, qword [rax -8]")
            self.assembly.append("    shr r8, 3") 
            self.assembly.append("    cmp rbx, r8")
            self.assembly.append(f"    jge {bounds_fail}") 
            self.assembly.append(f"    jmp {bounds_ok}")

        self.assembly.append(f"{bounds_fail}:")
        self.assembly.append("    mov eax, 99") # OUT OF BOUNDS
        self.assembly.append("    mov rbx, qword [rel global_err_frame]")
        self.assembly.append("    cmp rbx, 0")
        crash_lbl = self.get_new_label("CRASH")
        self.assembly.append(f"    je {crash_lbl}") 
        self.assembly.append("    mov rcx, qword [rbx + 24]")
        self.assembly.append("    mov qword [rel global_err_frame], rcx")
        self.assembly.append("    mov rdx, qword [rbx + 16]")
        self.assembly.append("    mov rbp, qword [rbx + 8]")
        self.assembly.append("    mov rsp, qword [rbx]")
        self.assembly.append("    jmp rdx") 
        
        self.assembly.append(f"{crash_lbl}:")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    mov eax, 60")
        self.assembly.append("    syscall") 

        self.assembly.append(f"{bounds_ok}:")


        op = node.op_tok[1]

        if eval_type == 'char':
            if op == '=':
                self.assembly.append("    mov byte [rax + rbx], cl") # Writes 1 byte
            else:
                raise Exception("Semantik Error: Invalid operation type on chars.")
        else:
            self.assembly.append("    shl rbx, 3") # Index*8
            if op == '=':
                self.assembly.append("    mov qword [rax + rbx], rcx")
            elif op in ('+=', '=+'):
                self.assembly.append("    add qword [rax + rbx], rcx")
            elif op in ('-=', '=-'):
                self.assembly.append("    sub qword [rax + rbx], rcx")
            elif op in ('*=', '=*'):
                self.assembly.append("    push rax")
                self.assembly.append("    mov rax, qword [rax + rbx]")
                self.assembly.append("    imul rax, rcx")
                self.assembly.append("    mov rcx, rax")
                self.assembly.append("    pop rax")
                self.assembly.append("    mov qword [rax + rbx], rcx")
            elif op in ('/=', '=/'):
                self.assembly.append("    mov r8, qword [rax + rbx]")
                self.assembly.append("    push rax")
                self.assembly.append("    push rbx")
                self.assembly.append("    mov rax, r8")
                self.assembly.append("    mov rbx, rcx")
                self.assembly.append("    cqo")
                self.assembly.append("    idiv rbx")
                self.assembly.append("    mov rcx, rax")
                self.assembly.append("    pop rbx")
                self.assembly.append("    pop rax")
                self.assembly.append("    mov qword [rax + rbx], rcx")
            elif op in ('%=', '=%'):
                self.assembly.append("    mov r8, qword [rax + rbx]")
                self.assembly.append("    push rax")
                self.assembly.append("    push rbx")
                self.assembly.append("    mov rax, r8")
                self.assembly.append("    mov rbx, rcx")
                self.assembly.append("    cqo")
                self.assembly.append("    idiv rbx")
                self.assembly.append("    mov rcx, rdx")
                self.assembly.append("    pop rbx")
                self.assembly.append("    pop rax")
                self.assembly.append("    mov qword [rax + rbx], rcx")
            elif op in ('^=', '=^'):
                self.assembly.append("    mov rdi, qword [rax + rbx]")
                self.assembly.append("    mov rsi, rcx")
                self.assembly.append("    push rax")
                self.assembly.append("    push rbx")
                self.assembly.append("    call int_pow")
                self.assembly.append("    mov rcx, rax")
                self.assembly.append("    pop rbx")
                self.assembly.append("    pop rax")
                self.assembly.append("    mov qword [rax + rbx], rcx")

    def visit_ClassDefNode(self, node):
        """Saves the class template to the memory map at compile time."""
        class_name = node.class_name_tok[1]
        self.current_class = class_name
        for method in node.methods:
            self.generate(method)
        self.current_class = None

    def visit_MemberAccessNode(self, node):
        field_name = node.member_name_tok[1]
        obj_type = self._get_obj_type(node.left_node)

        if not obj_type or obj_type == 'var':
            raise Exception(f"Compiling Error: Unknown Class for Variable (Accessing field '{field_name}')")

        if obj_type not in self.class_layouts:
            raise Exception(f"Compiling Error: Class '{obj_type}' is not defined.")

        field_info = self.class_layouts[obj_type]['layout'].get(field_name)
        if not field_info:
            if field_name in self.class_layouts[obj_type]['methods']:
                line_num = node.member_name_tok[2] if len(node.member_name_tok) > 2 else 'Unknown'
                raise Exception(f"Syntax Error: '{field_name}' is a method of '{obj_type}', but accessed as a property at Line: {line_num}.")
            raise Exception(f"Compiling Error: Class '{obj_type}' has no properties specified as: '{field_name}'")

        offset = field_info['offset']
        self.generate(node.left_node)
        self.assembly.append(f"    mov rax, qword [rax + {offset}]")

    def visit_MemberAssignNode(self, node):
        """Assigns a value to the object.field."""
        obj_type = self._get_obj_type(node.left_node)

        if not obj_type or obj_type == 'var':
            raise Exception(f"Compiling Error: Unknown Class for Variable")

        field_name = node.member_name_tok[1]
        field_info = self.class_layouts[obj_type]['layout'].get(field_name)

        if not field_info:
            raise Exception(f"Compiling Error: Class '{obj_type}' has no properties specified as: '{field_name}'")

        if field_info['modifier'] == 'private' and self.current_class != obj_type:
            raise Exception(f"Access Violation: '{field_name}' is private")

        offset = field_info['offset']    

        self.generate(node.value_node)
        self.assembly.append("    push rax")

        self.generate(node.left_node)
        self.assembly.append("    pop rcx")

        op = node.op_tok[1]
        if op == '=':
            self.assembly.append(f"    mov qword [rax + {offset}], rcx")
        elif op in ('+=', '=+'):
            self.assembly.append(f"    add qword [rax + {offset}], rcx")
        elif op in ('-=', '=-'):
            self.assembly.append(f"    sub qword [rax + {offset}], rcx")
        elif op in ('*=', '=*'):
            self.assembly.append("    push rax")
            self.assembly.append(f"    mov rax, qword [rax + {offset}]")
            self.assembly.append("    imul rax, rcx")
            self.assembly.append("    mov rcx, rax")
            self.assembly.append("    pop rax")
            self.assembly.append(f"    mov qword [rax + {offset}], rcx")
        elif op in ('/=', '=/'):
            self.assembly.append(f"    mov r8, qword [rax + {offset}]")
            self.assembly.append("    push rax")
            self.assembly.append("    mov rax, r8")
            self.assembly.append("    mov rbx, rcx")
            self.assembly.append("    cqo")
            self.assembly.append("    idiv rbx")
            self.assembly.append("    mov rcx, rax")
            self.assembly.append("    pop rax")
            self.assembly.append(f"    mov qword [rax + {offset}], rcx")
        elif op in ('%=', '=%'):
            self.assembly.append(f"    mov r8, qword [rax + {offset}]")
            self.assembly.append("    push rax")
            self.assembly.append("    mov rax, r8")
            self.assembly.append("    mov rbx, rcx")
            self.assembly.append("    cqo")
            self.assembly.append("    idiv rbx")
            self.assembly.append("    mov rcx, rdx")
            self.assembly.append("    pop rax")
            self.assembly.append(f"    mov qword [rax + {offset}], rcx")
        elif op in ('^=', '=^'):
            self.assembly.append(f"    mov rdi, qword [rax + {offset}]")
            self.assembly.append("    mov rsi, rcx")
            self.assembly.append("    push rax")
            self.assembly.append("    call int_pow")
            self.assembly.append("    mov rcx, rax")
            self.assembly.append("    pop rax")
            self.assembly.append(f"    mov qword [rax + {offset}], rcx")

    def visit_NewObjectNode(self, node):
        """Calculates the class size and calls `alloc()` When encounters the `new Class()` structure."""
        class_name = node.class_name_tok[1]

        if class_name not in self.class_layouts:
            raise Exception(f"Compiling Error: '{class_name}' is not defined.")
        
        class_size = self.class_layouts[class_name]['size']

        if class_size == 0:
            class_size = 8

        self.assembly.append(f"    mov rax, {class_size}")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call alloc")

        self.assembly.append("    push rax")

        if self.class_layouts[class_name].get('has_init'):
            init_info = self.class_layouts[class_name]['methods'].get('init')
            declared_class = init_info['declared_in'] if init_info else class_name
            method_name = f"{declared_class}_init"
            arg_count = len(node.arg_nodes) + 1

            if arg_count > 6:
                for i in range(len(node.arg_nodes)-1, 4, -1):
                    self.generate(node.arg_nodes[i])
                    self.assembly.append("    push rax")

            arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

            for i in range(min(5, len(node.arg_nodes))):
                self.generate(node.arg_nodes[i])
                self.assembly.append(f"    push rax")

            for i in range(min(5, len(node.arg_nodes)) - 1, -1, -1):
                self.assembly.append(f"    pop {arg_registers[i+1]}")

            self.assembly.append("    mov rdi, qword [rsp]")
            self.assembly.append(f"    call {method_name}")

            extra_args = max(0, arg_count -6)
            if extra_args > 0:
                self.assembly.append(f"    add rsp, {extra_args * 8}")
        
        self.assembly.append("    pop rax")

    def visit_MethodDefNode(self, node):
        """Converts a method written within a class to Assembly."""
        if not self.current_class:
            raise Exception("Compiling Error: Methods can only be defined in a class.")
        
        func_name = f"{self.current_class}_{node.func_name_tok[1]}"
        exit_label = f"exit_func_{func_name}"

        main_assembly = self.assembly
        self.assembly = self.functions_code

        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_label

        self.assembly.append("")
        self.assembly.append(f"{func_name}:")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")

        old_stack_offset = self.stack_offset
        self.stack_offset = 0

        self.enter_scope()
        current_env = self.environments[-1]
        type_env = self.type_environments[-1]

        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        self.stack_offset += 8
        current_env['this'] = self.stack_offset
        type_env['this'] = self.current_class 
        self.assembly.append("    sub rsp, 8")
        self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rdi")  

        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            type_env[arg_name] = arg_type[1]

            reg_index = i + 1 
            self.assembly.append("    sub rsp, 8")
            if reg_index < 6:
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], {arg_registers[reg_index]}")
            else:
                read_offset = 16 + (reg_index - 6) * 8
                self.assembly.append(f"    mov rax, qword [rbp + {read_offset}]")
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rax")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack_offset

        self.assembly.append(f"{exit_label}:")
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")

        self.current_func_exit_label = old_exit_label
        self.assembly = main_assembly

    def visit_MethodCallNode(self, node):
        """Translates the `object.method()` call to Assembly and secretly passes the pointer."""
        obj_type = self._get_obj_type(node.left_node)

        if not obj_type or obj_type == 'var':
            raise Exception(f"Compiling Error: Unknown Class for Variable")
        
        method_raw_name = node.method_name_tok[1]
        method_info = self.class_layouts[obj_type]['methods'].get(method_raw_name)

        if method_info and method_info['modifier'] == 'private' and self.current_class != obj_type:
            raise Exception(f"Access Violation: '{method_raw_name}()' is private")

        declared_class = method_info['declared_in'] if method_info else obj_type
        method_name = f"{declared_class}_{method_raw_name}"

        arg_count = len(node.arg_nodes) + 1

        if arg_count > 6:
            for i in range(len(node.arg_nodes) - 1, 4, -1):
                self.generate(node.arg_nodes[i])
                self.assembly.append("    push rax")

        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        for i in range(min(5, len(node.arg_nodes))):
            self.generate(node.arg_nodes[i])
            self.assembly.append(f"    push rax")

        self.generate(node.left_node)
        self.assembly.append("    push rax")

        self.assembly.append("    pop rdi")
        for i in range(min(5, len(node.arg_nodes)) - 1, -1, -1):
            self.assembly.append(f"    pop {arg_registers[i+1]}")
        
        self.assembly.append(f"    call {method_name}")

        extra_args = max(0, arg_count - 6)
        if extra_args > 0:
            self.assembly.append(f"    add rsp, {extra_args * 8}")

    def visit_ArrayLiteralNode(self, node):
        """Turns the Array Literal into alloc and mov operations."""
        element_count = len(node.elements)
        alloc_size = max((element_count + 1) * 8, 16)

        self.assembly.append(f"    mov eax, {alloc_size}")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call alloc")

        self.assembly.append("    push rax")

        for i, element_node in enumerate(node.elements):
            self.generate(element_node)

            self.assembly.append("    mov rcx, rax")
            self.assembly.append("    mov rbx, qword [rsp]")

            offset = i * 8
            self.assembly.append(f"    mov qword [rbx + {offset}], rcx")

        null_offset = element_count * 8
        self.assembly.append("    mov rbx, qword [rsp]")
        self.assembly.append(f"    mov qword [rbx + {null_offset}], 0")

        self.assembly.append("    pop rax")

    def visit_SwitchNode(self, node):
        end_label = self.get_new_label("SWITCH_END")
        default_label = self.get_new_label("DEFAULT")

        self.generate(node.switch_expr)
        self.assembly.append("    push rax")

        case_labels = []

        for i, (case_expr, _) in enumerate(node.cases):
            block_label = self.get_new_label(f"CASE_BLOCK_{i}")
            next_label = self.get_new_label(f"CASE_NEXT_{i}")
            case_labels.append(block_label)

            self.generate(case_expr)

            self.assembly.append("    mov rbx, rax")
            self.assembly.append("    mov rax, qword [rsp]")
            self.assembly.append("    cmp rax, rbx")
            self.assembly.append(f"    jne {next_label}")

            self.assembly.append("    add rsp, 8")
            self.assembly.append(f"    jmp {block_label}")

            self.assembly.append(f"{next_label}:")
        
        self.assembly.append("    add rsp, 8")
        if node.default_case:
            self.assembly.append(f"    jmp {default_label}")
        else: 
            self.assembly.append(f"    jmp {end_label}")

        for i, (_, block) in enumerate(node.cases):
            self.assembly.append(f"{case_labels[i]}:")
            self.generate(block)
            self.assembly.append(f"    jmp {end_label}")

        if node.default_case:
            self.assembly.append(f"{default_label}:")
            self.generate(node.default_case)

        self.assembly.append(f"{end_label}:")

    def visit_CastNode(self, node):
        """Does Type Casting."""
        self.generate(node.node)
        target_type = node.type_tok[1]
        source_type = getattr(node.node, 'eval_type', 'int')
        
        if target_type in ('str', 'string'):
            if source_type in ('int', 'integer'):
                self.assembly.append("    mov rdi, rax")
                self.assembly.append("    call int_to_str")
                
        elif target_type == 'bool':
            if source_type == 'double':
                self.assembly.append("    pxor xmm1, xmm1")
                self.assembly.append("    ucomisd xmm0, xmm1")
                self.assembly.append("    setne al")
                self.assembly.append("    movzx rax, al")
            elif source_type in ('str', 'string'):
                self.assembly.append("    cmp byte [rax], 0")
                self.assembly.append("    setne al")
                self.assembly.append("    movzx rax, al")
            elif source_type == 'null':
                self.assembly.append("    xor eax, eax")
            else: 
                self.assembly.append("    test rax, rax")
                self.assembly.append("    setne al")
                self.assembly.append("    movzx rax, al")

        elif target_type in ('int', 'integer') and source_type in ('str', 'string'):
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    call str_to_int")
            
        elif target_type == 'double' and source_type in ('int', 'integer', 'any', 'var'):
            self.assembly.append("    cvtsi2sd xmm0, rax")
            self.assembly.append("    movq rax, xmm0")
            
        elif target_type in ('int', 'integer') and source_type == 'double':
            self.assembly.append("    movq xmm0, rax")
            self.assembly.append("    cvttsd2si rax, xmm0")
            
        elif target_type == 'char' and source_type in ('str', 'string', 'any'):
            self.assembly.append("    movzx rax, byte [rax]")
                    
    def visit_DeleteNode(self, node):
        self.generate(node.target_node)
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call free")

    def visit_AllegeNode(self, node):
        self.generate(node.condition)
        self.assembly.append("    test rax, rax")
        
        ok_lbl = self.get_new_label("ALLEGE_OK")
        self.assembly.append(f"    jne {ok_lbl}")

        self.assembly.append("    mov eax, 1") # Allege Error Code (1)
        self.assembly.append("    mov rbx, qword [rel global_err_frame]")
        self.assembly.append("    cmp rbx, 0")
        crash_lbl = self.get_new_label("CRASH")
        self.assembly.append(f"    je {crash_lbl}") 
        self.assembly.append("    mov rcx, qword [rbx + 24]")
        self.assembly.append("    mov qword [rel global_err_frame], rcx")
        self.assembly.append("    mov rdx, qword [rbx + 16]")
        self.assembly.append("    mov rbp, qword [rbx + 8]")
        self.assembly.append("    mov rsp, qword [rbx]")
        self.assembly.append("    jmp rdx") 
        
        self.assembly.append(f"{crash_lbl}:")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    mov eax, 60")
        self.assembly.append("    syscall") 
        
        self.assembly.append(f"{ok_lbl}:")

    def visit_LimitsNode(self, node):
        self.generate(node.start_node)
        self.assembly.append("    push rax")
        
        self.generate(node.end_node)
        self.assembly.append("    mov rbx, rax")
        self.assembly.append("    pop rax")
        self.assembly.append("    mov rcx, rbx")
        self.assembly.append("    sub rcx, rax")
        
        ok_lbl = self.get_new_label("LIMITS_OK")
        self.assembly.append("    cmp rcx, 0")
        self.assembly.append(f"    jg {ok_lbl}")
        self.assembly.append("    mov ecx, 1")
        self.assembly.append(f"{ok_lbl}:")
        self.assembly.append("    push rax") 
        self.assembly.append("    push rcx")

        self.assembly.append("    mov rdi, rcx")
        self.assembly.append("    shl rdi, 3") 
        self.assembly.append("    call alloc")
        self.assembly.append("    mov r8, rax")

        self.assembly.append("    pop rcx") 
        self.assembly.append("    pop rax")

        xor_r9 = "    xor r9d, r9d"
        self.assembly.append(xor_r9)
        loop_start = self.get_new_label("LIMITS_LOOP")
        loop_end = self.get_new_label("LIMITS_END")

        self.assembly.append(f"{loop_start}:")
        self.assembly.append("    cmp r9, rcx")
        self.assembly.append(f"    jge {loop_end}")

        self.assembly.append("    mov qword [r8 + r9*8], rax")
        self.assembly.append("    inc rax") 
        self.assembly.append("    inc r9") 
        self.assembly.append(f"    jmp {loop_start}")
        
        self.assembly.append(f"{loop_end}:")
        self.assembly.append("    mov rax, r8")

    def visit_BreakNode(self, node):
        if not self.loop_stack:
            raise Exception("Semantic Error: 'break' can only be used in a loop.")
        _, end_label = self.loop_stack[-1]
        self.assembly.append(f"    jmp {end_label}")

    def visit_GoonNode(self, node):
        if not self.loop_stack:
            raise Exception("Semantic Error: 'goon' can only be used in a loop.")
        continue_label, _ = self.loop_stack[-1]
        self.assembly.append(f"    jmp {continue_label}")

if __name__ == '__main__':
    from lexer import tokenize
    from parser import Parser
    from semantic import SemanticAnalyzer

    test_code = """
    
    """

    #1. FRONTEND
    tokens = tokenize(test_code)
    parser = Parser(tokens)
    ast = parser.parse()

    #2. BACKEND
    semantic_analyzer = SemanticAnalyzer(strict_mode=True)
    semantic_analyzer.analyze(ast)

    compiler = CodeGen(semantic_analyzer=semantic_analyzer)
    compiler.generate(ast)
    asm_code = compiler.get_code()

    print("--- ENTERED WRENCH TEST CODE ---")
    print(test_code)
    print("--- GENERATED x86_64 ASSEMBLY CODE ---")
    print(asm_code)