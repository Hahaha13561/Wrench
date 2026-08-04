class CodeGen:
    def __init__(self):
        self.assembly = []
        self.environments = [{}] # Hafıza offset'lerini tutan Symbol Table
        self.stack_offset = 0 # RAM'de kaç bayt aşağı inildiği (Offset Tracker)
        self.label_count = 0 # Label sayacı
        self.data_section = [] # Statik metin verilerinin tutulacağı kısım
        self.string_count = 0 # String etiketleri sayacı
        self.class_layouts = {} # Sınıf boyutları
        self.type_environments = [{}]
        self.current_class = None
        self.loop_stack = []


    def generate(self, node):
        """Ağactaki Node'un türüne göre ilgili fonksiyonu çalıştırır."""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        raise Exception (f'HATA: CodeGen içinde {type(node).__name__} için bir Assembly çevirisi yazılmamış.')

    def get_code(self):
        """Assembly kodunu birleştirip çalıştırılabilir NASM şablonu verir."""

        data_code = [
            "section .data",
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
            "    mov rbx, rax",
            "    mov rcx, 0",
            ".strlen_loop:",
            "    cmp byte [rbx + rcx], 0",
            "    je .strlen_done",
            "    inc rcx",
            "    jmp .strlen_loop",
            ".strlen_done:",
            "    mov rdx, rcx",
            "    mov rsi, rbx",
            "    mov rdi, 1",
            "    mov rax, 1",
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
            "    mov rbx, 10",
            "    mov rcx, 0",
            "    mov r8, 0",
            "    cmp rax, 0",
            "    jge .divide_loop",
            "    neg rax",
            "    mov r8, 1",
            ".divide_loop:",
            "    mov rdx, 0",
            "    div rbx",
            "    add rdx, 48",
            "    push rdx",
            "    inc rcx",
            "    cmp rax, 0",
            "    jne .divide_loop",
            "    cmp r8, 1",
            "    jne .pop_chars",
            "    push 45",
            "    inc rcx",
            ".pop_chars:",
            "    mov rdi, 0",
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
            "print_hex:"
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rsp, 32",
            "    mov byte [rbp - 32], 48",
            "    mov byte [rbp - 31], 120",
            "    mov rcx, 16",
            "    mov rbx, 2",
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
            "",
            "    mov rax, qword [rsi + 16]",
            "",
            "    mov rbx, qword [rel global_err_frame]",
            "    cmp rbx, 0",
            "    je .unhandled_segfault",
            "",
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
            "    mov rax, 60",
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
            "",
            "    mov rax, 1",
            "    mov rdi, 1",
            "    lea rsi, [rel dot_str]",
            "    mov rdx, 1",
            "    syscall",
            "",
            "    pop rbx",
            "    movsd xmm0, [rsp]",
            "    add rsp, 16",
            "    cvtsi2sd xmm1, rbx",
            "    subsd xmm0, xmm1",
            "    mov rax, 100000",
            "    cvtsi2sd xmm1, rax",
            "    mulsd xmm0, xmm1",
            "    cvttsd2si rax, xmm0",
            "",
            "    cmp rax, 0",
            "    jge .print_frac",
            "    neg rax",
            ".print_frac:",
            "    call print_int",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "concat_strings:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rdi",
            "    push rsi",
            "    mov rbx, 0",
            ".len1:",
            "    cmp byte [rdi + rbx], 0",
            "    je .len1_done",
            "    inc rbx",
            "    jmp .len1",
            ".len1_done:",
            "    mov rcx, 0",
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
            "    mov r9, 0",
            ".copy1:",
            "    cmp r9, rbx",
            "    je .copy1_done",
            "    mov al, byte [rdi + r9]",
            "    mov byte [r8 + r9], al",
            "    inc r9",
            "    jmp .copy1",
            ".copy1_done:",
            "    mov r10, 0",
            "",
            "    lea r11, [r8 + rbx]",
            ".copy2:",
            "    cmp r10, rcx",
            "    je .copy2_done",
            "    mov al, byte [rsi + r10]",
            "    mov byte [r11 + r10], al",
            "    inc r10",
            "    jmp .copy2",
            ".copy2_done:",
            "    mov byte [r11 + rcx], 0",
            "    mov rax, r8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "compare_strings:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rcx, 0",
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
            "    mov rax, 0",
            ".cmp_exit:",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "int_to_str:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rax, rdi",
            "    mov rdi, 32",
            "    push rax",
            "    call alloc",
            "    pop rcx",
            "    mov r8, rax",
            "    cmp rcx, 0",
            "    jne .check_neg",
            "    mov byte [r8], 48",
            "    mov byte [r8+1], 0",
            "    mov rax, r8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".check_neg:",
            "    mov r9, 0",
            "    cmp rcx, 0",
            "    jge .conv_setup",
            "    neg rcx",
            "    mov r9, 1",
            ".conv_setup:",
            "    mov rax, rcx",
            "    mov rbx, 10",
            "    mov r10, 0",
            ".conv_loop:",
            "    cmp rax, 0",
            "    je .pop_dig",
            "    mov rdx, 0",
            "    div rbx",
            "    add rdx, 48",
            "    push rdx",
            "    inc r10",
            "    jmp .conv_loop",
            ".pop_dig:",
            "    mov r11, 0",
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
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "read_input:",
            "    push rbp",
            "    mov rbp, rsp",
            "    push rax",
            "    mov rdi, 0",
            "    mov rsi, rax",
            "    mov rdx, 3",
            "    mov r10, 34",
            "    mov r8, -1",
            "    mov r9, 0",
            "    mov rax, 9",
            "    syscall",
            "    mov rsi, rax",
            "    push rsi",
            "    mov rdi, 0",
            "    mov rdx, [rbp - 8]",
            "    mov rax, 0",
            "    syscall",
            "    pop rsi",
            "    cmp rax, 0",
            "    jle .read_done",
            "    mov byte [rsi + rax - 1], 0",
            ".read_done:",
            "    mov rax, rsi",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "read_int:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rsp, 32",
            "    mov rax, 0",
            "    mov rdi, 0",
            "    lea rsi, [rbp - 32]",
            "    mov rdx, 31",
            "    syscall",
            "    mov rcx, 0",
            "    mov rbx, 0",
            "    mov r8, 0",
            "    cmp byte [rbp - 32], 45",
            "    jne .atoi_loop",
            "    mov r8, 1",
            "    inc rcx",
            ".atoi_loop:",
            "    movzx rax, byte [rbp - 32 + rcx]",
            "    cmp rax, 10",
            "    je .atoi_done",
            "    cmp rax, 0",
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
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "str_to_int:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rcx, 0",
            "    mov rbx, 0",
            "    mov r8, 0",
            "    cmp byte [rdi], 45",
            "    jne .parse_loop",
            "    mov r8, 1",
            "    inc rcx",
            ".parse_loop:",
            "    movzx rax, byte [rdi + rcx]",
            "    cmp rax, 0",
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
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            ".parse_error:",
            "    mov rax, 0",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "int_pow:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rcx, rsi",
            "    mov rax, 1",
            "    cmp rcx, 0",
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
            "alloc:",
            "    push rbp",
            "    mov rbp, rsp",
            "    add rdi, 8",
            "    push rdi",
            "    mov rsi, rdi",
            "    mov rdi, 0",
            "    mov rdx, 3",
            "    mov r10, 34",
            "    mov r8, -1",
            "    mov r9, 0",
            "    mov rax, 9",
            "    syscall",
            "    mov rcx, [rbp - 8]",
            "    sub rcx, 8",
            "    mov qword [rax], rcx",
            "    add rax, 8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "free:",
            "    push rbp",
            "    mov rbp, rsp",
            "    sub rdi, 8",
            "    mov rsi, qword [rdi]",
            "    add rsi, 8",
            "    mov rax, 11",
            "    syscall",
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
            "    mov r10, 1",
            "    mov rax, 25",
            "    syscall",
            "    mov qword [rax], rsi",
            "    add rax, 8",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ret",
            "",
            "exit_prog:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rax, 60",
            "    syscall",
            "",
            "_start:",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov rdi, 11",
            "    lea rsi, [rel sigaction_struct]",
            "    mov rdx, 0",
            "    mov r10, 8",
            "    mov rax, 13",
            "    syscall",
            "    mov rax, qword [rbp +8]",
            "    mov qword [rel global_argc], rax",
            "    lea rax, [rbp + 16]",
            "    mov qword [rel global_argv], rax",
        ]
        
        footer = [
            "",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ; Exit program (Syscall 60)",
            "    mov rax, 60",
            "    mov rdi, 0",
            "    syscall"
        ]

        return "\n".join(data_code + header + self.assembly + footer)
        
    def get_new_label(self, base_name):
        self.label_count += 1
        return f"{base_name}_{self.label_count}"

    def get_var_offset(self, var_name):
        """Değişkeni en içteki (yeni) Scope'tan başlayarak geriye doğru arar."""
        for env in reversed(self.environments):
            if var_name in env:
                return env[var_name]
        return None

    def get_var_type(self, var_name):
        """Değişkenin class'ını bul."""
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
        node_class = type(node).__name__
        if node_class == 'VarAccessNode':
            return self.get_var_type(node.var_name_tok[1])
        elif node_class == 'MemberAccessNode':
            parent_type = self._get_obj_type(node.left_node)
            if parent_type and parent_type in self.class_layouts:
                field_info = self.class_layouts[parent_type]['layout'].get(node.member_name_tok[1])
                if field_info:
                    return field_info.get('type')
        return None

    def enter_scope(self):
        """Yeni bir { açıldığında yeni yerel kapsam (scope) yarat."""
        self.environments.append({})
        self.type_environments.append({})

    def exit_scope(self):
        """Bir } kapandığında son açılan yerel kapsamı (scope) kapat."""
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
        """Sayı görüldüğünde RAX yazmacına (register) yerleştir."""
        
        if node.tok[0] == 'FLOAT':
            self.assembly.append(f"    mov rax, __float64__({node.tok[1]})")       
        else:    
            self.assembly.append(f"    mov rax, {node.tok[1]}")

    def visit_IfNode(self, node):
        """if, butif ve else yapılarını JMP'e çevirir."""
        end_label = self.get_new_label("IF_END")

        for condition, block in node.cases:
            next_case_label = self.get_new_label("NEXT_CASE")
            
            # 1. Koşulu hesapla. RAX'e 1 ya da 0 döner.
            self.generate(condition)

            # 2. Sonucu 0 ile karşılaştır.
            self.assembly.append("    cmp rax, 0")

            # 3. Sonuç False ise bloğun içini atla ve sıradaki duruma geç
            self.assembly.append(f"    je {next_case_label}")

            # 4. Sonuç True ise kodları Assembly'e çevir.
            self.generate(block)

            # 5. Kodlar bittiğinde sona zıpla.
            self.assembly.append(f"    jmp {end_label}")

            # 6. Sıradaki butif/else kontrolü için atlama etiketini buraya yerleştir.
            self.assembly.append(f"{next_case_label}:")

        #Koşullar tutmazsa ve else bloğu varsa else'i çalıştır.
        if node.else_case:
            self.generate(node.else_case)

        # Herkesin sonda ulaştığı ortak zemin
        self.assembly.append(f"{end_label}:")

    def visit_WhileNode(self, node):
        """While döngüsü."""
        start_label = self.get_new_label("WHILE_START")
        end_label = self.get_new_label("WHILE_END")

        self.loop_stack.append((start_label, end_label))

        self.assembly.append(f"{start_label}:")

        self.generate(node.condition_node)

        self.assembly.append("    cmp rax, 0")
        self.assembly.append(f"    je {end_label}")

        self.generate(node.body_node)
        
        self.assembly.append(f"    jmp {start_label}")

        self.assembly.append(f"{end_label}:")

        self.loop_stack.pop()

    def visit_ForNode(self, node):
        var_name = node.var_name_tok[1]
        
        self.enter_scope()
        current_env = self.environments[-1]

        # 1. Gizli değişkenler için stack'te yer ayır (Array_Ptr, Array_Len, Index)
        self.stack_offset += 8
        ptr_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        len_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        self.stack_offset += 8
        idx_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        # 2. Programcının kullanacağı asıl döngü değişkeni (örn: eleman)
        self.stack_offset += 8
        current_env[var_name] = self.stack_offset
        elem_offset = self.stack_offset
        self.assembly.append("    sub rsp, 8")

        # 3. Diziyi (Array) hesapla ve pointer'ı kaydet
        self.generate(node.iter_node)
        self.assembly.append(f"    mov qword [rbp - {ptr_offset}], rax")

        # 4. Dizinin uzunluğunu bul ve kaydet (Önceden yazdığımız get_len syscall'u)
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call get_len")
        self.assembly.append(f"    mov qword [rbp - {len_offset}], rax")

        # 5. Index'i 0'dan başlat
        self.assembly.append(f"    mov qword [rbp - {idx_offset}], 0")

        # DÖNGÜ BAŞLANGICI
        start_label = self.get_new_label("FOR_START")
        inc_label = self.get_new_label("FOR_INC")
        end_label = self.get_new_label("FOR_END")

        self.loop_stack.append((inc_label, end_label))

        self.assembly.append(f"{start_label}:")

        # 6. Koşul Kontrolü: index >= length ise döngüden çık
        self.assembly.append(f"    mov rax, qword [rbp - {idx_offset}]")
        self.assembly.append(f"    mov rbx, qword [rbp - {len_offset}]")
        self.assembly.append("    cmp rax, rbx")
        self.assembly.append(f"    jge {end_label}")

        # 7. Elemanı diziden çek ve değişkene ata: elem = array[index * 8]
        self.assembly.append(f"    mov rbx, qword [rbp - {idx_offset}]")
        self.assembly.append("    shl rbx, 3") # Index'i 8 ile çarp (Pointer kaydırması)
        self.assembly.append(f"    mov rax, qword [rbp - {ptr_offset}]")
        self.assembly.append("    mov rcx, qword [rax + rbx]")
        self.assembly.append(f"    mov qword [rbp - {elem_offset}], rcx")

        # 8. Kod bloğunu (body) çalıştır
        self.generate(node.body)

        # 9. Index'i 1 artır ve başa dön
        self.assembly.append(f"{inc_label}:")
        self.assembly.append(f"    mov rax, qword [rbp - {idx_offset}]")
        self.assembly.append("    inc rax")
        self.assembly.append(f"    mov qword [rbp - {idx_offset}], rax")
        self.assembly.append(f"    jmp {start_label}")

        # DÖNGÜ BİTİŞİ
        self.assembly.append(f"{end_label}:")

        self.loop_stack.pop()
        self.exit_scope()

    def visit_ReAssignNode(self, node):
        """Var olan değişkeni güncelleme."""
        var_name = node.var_name_tok[1]

        loc = getattr(self, 'get_var_loc', lambda x: f"qword [rbp - {self.get_var_offset(x)}]")(var_name)
        if not loc or "None" in loc:
            raise RuntimeError(f"{var_name} is not found.")

        self.generate(node.value_node)

        op = node.op_tok[1]

        var_type = self.get_var_type(var_name)
        val_type = getattr(node.value_node, 'eval_type', 'int')

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
            self.assembly.append(f"    mov {loc}, rdx") # Kalanı kaydet
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

        self.stack_offset = old_stack
        # Eğer hata olduysa, Trigger Frame'i sökmüştür ve RAX içinde Hata Kodu vardır.
        if node.exclude_body:
            self.enter_scope()
            self.stack_offset += 8
            self.environments[-1]['err'] = self.stack_offset # 'err' adında yerel değişken yarat
            self.assembly.append("    sub rsp, 8")
            self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rax") # Hata kodunu 'err' içine koy
            
            self.generate(node.exclude_body)
            self.exit_scope()

        else:
            # Eğer programcı Exclude yazmadıysa, Final'i çalıştır ve Hatayı BUBBLE UP yap! (Geri Fırlat)
            self.assembly.append("    push rax") # RAX'ı koru
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
            self.assembly.append("    jmp rdx") # Üstteki frame'e fırlat
            
            self.assembly.append(f"{end_label}_crash:")
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    mov rax, 60")
            self.assembly.append("    syscall")
            self.assembly.append(f"    jmp {end_label}")

    # --- FINAL BODY ---
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
        self.assembly.append("    mov rdx, qword [rbx + 16]") # Exclude Adresi
        self.assembly.append("    mov rbp, qword [rbx + 8]")  # Eski RBP
        self.assembly.append("    mov rsp, qword [rbx]")      # Eski RSP
        self.assembly.append("    jmp rdx")

        self.assembly.append(f"{crash_label}:")
        self.assembly.append("    mov rdi, rax") # RDI = Çıkış Kodu (Hata Kodu)
        self.assembly.append("    mov rax, 60")  # sys_exit
        self.assembly.append("    syscall")

    def visit_VarAssignNode(self, node):
        """Değişkene değer atama."""

        self.generate(node.value_node)
        var_name = node.var_name_tok[1]
        current_env = self.environments[-1]

        if var_name not in current_env:
            if len(self.environments) == 1:
                label = f"gvar_{var_name}"
                self.data_section.append(f"    {label} dq 0")
                current_env[var_name] = label
            else:
                self.stack_offset += 8 # 8 byte (64 bit) yer ayır
                current_env[var_name] = self.stack_offset
                self.assembly.append("    sub rsp, 8") #Pointer'ı yukarı kaydır, RAM rezerve et.

        var_type = getattr(node, 'eval_type', None)

        if var_type and var_type not in ('int', 'integer', 'double', 'float', 'bool', 'str', 'string', 'char', 'var', 'any'):
            self.type_environments[-1][var_name] = var_type

        loc = self.get_var_loc(var_name)
        self.assembly.append(f"    mov {loc}, rax")

    def visit_VarAccessNode(self, node):
        """Değişken değerinin RAM'den okunması"""
        var_name = node.var_name_tok[1]
        loc = self.get_var_loc(var_name)
        if loc is None:
            raise RuntimeError(f"{var_name} is not found.")
        self.assembly.append(f"    mov rax, {loc}")

    def visit_BinOpNode(self, node):
        """Matematik, Kıyaslama ve String işlemlerini Assembly diline indirge."""
        self.generate(node.right_node)
        
        # DİKKAT: Artık 'eval_type' değil, donanımı seçmek için 'operand_type' okuyoruz!
        op_type = getattr(node, 'operand_type', getattr(node.left_node, 'eval_type', 'int')) 

        if op_type == 'string':
            # --- STRING İŞLEMLERİ ---
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
                self.assembly.append("    call compare_strings") # RAM'deki yazıları karşılaştırır
                self.assembly.append("    cmp rax, 0")

                if op in ('=?', '?=', 'is', 'same'): self.assembly.append("    sete al") 
                elif op in ('!=', '=!'): self.assembly.append("    setne al") 
                elif op == '>': self.assembly.append("    setg al") 
                elif op == '<': self.assembly.append("    setl al") 
                elif op in ('>=', '=>'): self.assembly.append("    setge al") 
                elif op in ('<=', '=<'): self.assembly.append("    setle al") 
                self.assembly.append("    movzx rax, al")
            else:
                raise Exception("Semantik Hata: Metinler (String) arasinda desteklenmeyen islem.")
                
        elif op_type == 'double':
            # --- ONDALIKLI SAYI İŞLEMLERİ (FPU / XMM) ---
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
                self.assembly.append("    fld qword [rsp]")     # st0 = bölen (xmm1)
                self.assembly.append("    movsd [rsp], xmm0")
                self.assembly.append("    fld qword [rsp]")     # st0 = bölünen, st1 = bölen
                fprem_loop = self.get_new_label("FPREM_LOOP")
                self.assembly.append(f"{fprem_loop}:")
                self.assembly.append("    fprem")               # Kalanı hesapla
                self.assembly.append("    fnstsw ax")
                self.assembly.append("    test ah, 4")          # C2 bayrağı kontrolü (işlem bitti mi?)
                self.assembly.append(f"    jnz {fprem_loop}")
                self.assembly.append("    fstp qword [rsp]")    # Kalanı yığıttan belleğe al
                self.assembly.append("    movsd xmm0, [rsp]")   # Kalanı xmm0'a koy
                self.assembly.append("    fstp st0")            # Böleni yığıttan temizle
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
            # --- STANDART INTEGER İŞLEMLERİ (ALU) ---
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
            self.assembly.append("    cmp rax, 0")
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
            self.assembly.append("    mov rsi, 0")   
            self.assembly.append("    mov rdx, 0")   
            self.assembly.append("    mov r10, 0")   
            self.assembly.append("    mov rax, 61")  
            self.assembly.append("    syscall")

    def visit_BlockNode(self, node):
        """Süslü parantez içi kod bloklarını (satırlar) sırayla Assembly'e çevir."""
        self.enter_scope()

        for statement in node.statements:
            self.generate(statement)

        self.exit_scope()

    def visit_FuncCallNode(self, node):
        """Fonskiyon çağır ve parametreleri System V standartlarına göre diz."""
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
                self.assembly.append("    mov rsi, rsp") # Adres stack'in tepesi
                self.assembly.append("    mov rdi, 1")   # stdout
                self.assembly.append("    mov rdx, 1")   # Uzunluk 1 byte
                self.assembly.append("    mov rax, 1")   # sys_write
                self.assembly.append("    syscall")
                self.assembly.append("    pop rax")
            else:
                self.assembly.append("    call print_string")
            return
            
        elif func_name == 'len':
            self.generate(node.arg_nodes[0]) # Parametreyi RAX'a al
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    call get_len")
            return
        
        elif func_name == 'realloc':
            self.generate(node.arg_nodes[1]) # İkinci parametre (yeni boyut)
            self.assembly.append("    push rax")
            self.generate(node.arg_nodes[0]) # Birinci parametre (eski pointer)
            self.assembly.append("    mov rdi, rax")
            self.assembly.append("    pop rsi") # İkinci parametreyi RSI'ye çek
            self.assembly.append("    call realloc_mem")
            return

        elif func_name == 'type_of':
            # Parametrenin AST node'unu al
            arg_node = node.arg_nodes[0]
            
            # Semantik analizörün yapıştırdığı 'eval_type' etiketini oku
            detected_type = getattr(arg_node, 'eval_type', 'unknown')
            
            # Bu tipi sanki programcı String olarak yazmış gibi donanıma yolla (.data'ya kaydeder)
            # Örneğin: type_of(3.14) yazarsa, derleyici bunu "double" stringi olarak koda gömer.
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

        elif func_name == 'addr_of':
            self.generate(node.arg_nodes[0])
            return

        elif func_name == 'ptr_to':
            self.generate(node.arg_nodes[0])
            return
        
        elif func_name == 'syscall':
            arg_count = len(node.arg_nodes)
            if arg_count > 7:
                raise Exception("Compiling Error: syscall can take 7 arguments max (rax, rdi, rsi, rdx, r10, r8, r9)")
            for arg in node.arg_nodes:
                self.generate(arg)
                self.assembly.append("    push rax")
            arg_registers = ['rax', 'rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9']
            for i in range(arg_count - 1, -1, -1):
                self.assembly.append(f"    pop {arg_registers[i]}")
                
            self.assembly.append("    syscall")
            return

        arg_count = len(node.arg_nodes)
        
        if arg_count > 6:
            for i in range(arg_count -1, 5, -1):
                self.generate(node.arg_nodes[i])
                self.assembly.append("    push rax")


        # x86-64 Standart Parametre Yazmaçları 
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        for i in range(min(6, arg_count)):
            self.generate(node.arg_nodes[i])
            self.assembly.append(f"    mov {arg_registers[i]}, rax")

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
        """Yeni fonksiyon oluştur ve Scope ayarlarını yap."""
        if node.modifier_tok and node.modifier_tok[1] == 'extern':
            func_name = node.func_name_tok[1]
            self.assembly.append(f"extern {func_name}")
            return

        func_name = node.func_name_tok[1]
        after_label = self.get_new_label(f"AFTER_FUNC_{func_name}")

        self.assembly.append(f"    jmp {after_label}")

        self.assembly.append(f"{func_name}:")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")

        is_async = (node.modifier_tok and node.modifier_tok[1] == 'async')

        if is_async:
            self.assembly.append("    mov rax, 57")
            self.assembly.append("    syscall")
            self.assembly.append("    cmp rax, 0")

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

        if is_async:
            self.assembly.append("    mov rdi, 0")
            self.assembly.append("    mov rax, 60") # sys_exit
            self.assembly.append("    syscall")
            self.assembly.append(f"{parent_label}:")
            self.assembly.append("    mov rsp, rbp")
            self.assembly.append("    pop rbp")
            self.assembly.append("    ret")
        else:
            self.assembly.append("    mov rsp, rbp")
            self.assembly.append("    pop rbp")
            self.assembly.append("    ret")

        self.assembly.append(f"{after_label}:")

    def visit_AnFuncNode(self, node):
        func_lbl = self.get_new_label("ANON_FUNC")
        after_lbl = self.get_new_label("AFTER_ANON_FUNC")
        
        self.assembly.append(f"    jmp {after_lbl}")
        
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
        
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")
        
        self.assembly.append(f"{after_lbl}:")
        
        self.assembly.append(f"    lea rax, [rel {func_lbl}]")

    def visit_ReturnNode(self, node):
        """Fonksiyondan bir değer çıkar."""
        if node.node_to_return:
            self.generate(node.node_to_return)

        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")

    def visit_StringNode(self, node):
        """Metin verisini .data olarak yazar ve adresi RAX'e koyar."""
        self.string_count += 1
        label = f"str_{self.string_count}"

        #Tırnakları at
        raw_str = node.tok[1][1:-1]

        self.data_section.append(f"    {label} db `{raw_str}`, 0")

        self.assembly.append(f"    mov rax, {label}")

    def visit_SyncUnitNode(self, node):
        unit_name = node.unit_name_tok[1]
        after_label = self.get_new_label(f"AFTER_UNIT_{unit_name}")
        
        self.assembly.append(f"    jmp {after_label}")
        self.assembly.append(f"unit_{unit_name}:")
        self.assembly.append("    push rbp")
        self.assembly.append("    mov rbp, rsp")
        
        self.enter_scope()
        self.generate(node.body_node)
        self.exit_scope()
        
        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")
        self.assembly.append(f"{after_label}:")

    def visit_WithNode(self, node):
        unit_name = node.unit_name_tok[1]
        if not node.is_wait:
            self.assembly.append("    mov rax, 57") 
            self.assembly.append("    syscall")
            self.assembly.append("    cmp rax, 0")
            parent_lbl = self.get_new_label("WITH_PARENT")
            self.assembly.append(f"    jne {parent_lbl}") 

            self.assembly.append(f"    call unit_{unit_name}")
            self.generate(node.body_node)

            self.assembly.append("    mov rax, 60")
            self.assembly.append("    mov rdi, 0")
            self.assembly.append("    syscall")
            
            self.assembly.append(f"{parent_lbl}:")

        else:
            self.assembly.append(f"    call unit_{unit_name}")
            self.generate(node.body_node)

    def visit_KeywordNode(self, node):
        """True, False ve Null'u Binary'e çevir."""
        val = node.tok[1]
        if val == 'true':
            self.assembly.append("    mov rax, 1")
        elif val == 'false':
            self.assembly.append("    mov rax, 0")
        elif val == 'null':
            self.assembly.append("    mov rax, 0")

    def visit_WhenNode(self, node):
        self.assembly.append("    mov rax, 57") 
        self.assembly.append("    syscall")
        self.assembly.append("    cmp rax, 0")

        parent_lbl = self.get_new_label("WHEN_PARENT")
        self.assembly.append(f"    jne {parent_lbl}")

        loop_lbl = self.get_new_label("WHEN_LOOP")
        self.assembly.append(f"{loop_lbl}:")

        self.assembly.append("    sub rsp, 16")
        self.assembly.append("    mov qword [rsp], 0")          
        self.assembly.append("    mov qword [rsp+8], 10000000") 
        self.assembly.append("    mov rdi, rsp")
        self.assembly.append("    mov rsi, 0")
        self.assembly.append("    mov rax, 35") 
        self.assembly.append("    syscall")
        self.assembly.append("    add rsp, 16")

        self.generate(node.condition)
        self.assembly.append("    cmp rax, 0")
        self.assembly.append(f"    je {loop_lbl}")

        self.generate(node.body)
        
        self.assembly.append("    mov rax, 60")
        self.assembly.append("    mov rdi, 0")
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

        self.assembly.append("    cmp rbx, 0")
        self.assembly.append(f"    jl {bounds_fail}") 

        self.assembly.append("    mov rcx, qword [rax - 8]")
        if eval_type != 'char':
            self.assembly.append("    shr rcx, 3") # 8'e bölerek eleman sayısını bul
            
        self.assembly.append("    cmp rbx, rcx")
        self.assembly.append(f"    jge {bounds_fail}") # Index >= Boyut ise hata
        self.assembly.append(f"    jmp {bounds_ok}")

        self.assembly.append(f"{bounds_fail}:")
        self.assembly.append("    mov rax, 99") # OUT OF BOUNDS Hata Kodu
        self.assembly.append("    mov rbx, qword [rel global_err_frame]")
        self.assembly.append("    cmp rbx, 0")
        crash_lbl = self.get_new_label("CRASH")
        self.assembly.append(f"    je {crash_lbl}") # Catch yedeği yoksa Crash!
        self.assembly.append("    mov rcx, qword [rbx + 24]")
        self.assembly.append("    mov qword [rel global_err_frame], rcx")
        self.assembly.append("    mov rdx, qword [rbx + 16]")
        self.assembly.append("    mov rbp, qword [rbx + 8]")
        self.assembly.append("    mov rsp, qword [rbx]")
        self.assembly.append("    jmp rdx") # Exclude bloğuna uç!
        
        self.assembly.append(f"{crash_lbl}:")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    mov rax, 60")
        self.assembly.append("    syscall") # Çöküş!

        self.assembly.append(f"{bounds_ok}:")

        if eval_type == 'char':
            # String karakteri için 1 byte oku (Örn: metin[2])
            self.assembly.append("    movzx rax, byte [rax + rbx]")
        else:
            # Standart dizi elemanı için 8 byte atla (Örn: liste[2])
            self.assembly.append("    shl rbx, 3") # rbx'i 8 ile çarp
            self.assembly.append("    mov rax, qword [rax + rbx]")

    def visit_IndexAssignNode(self, node):
        eval_type = getattr(node, 'eval_type', 'any')
        
        self.generate(node.value_node)
        self.assembly.append("    push rax")     

        self.generate(node.index_node)
        self.assembly.append("    push rax")

        self.generate(node.left_node)           
        self.assembly.append("    pop rbx")      # RBX = index
        self.assembly.append("    pop rcx")      # RCX = yeni deger

        bounds_fail = self.get_new_label("BOUNDS_FAIL")
        bounds_ok = self.get_new_label("BOUNDS_OK")
        
        self.assembly.append("    cmp rbx, 0")
        self.assembly.append(f"    jl {bounds_fail}") 
        
        self.assembly.append("    mov r8, qword [rax - 8]") 
        if eval_type != 'char':
            self.assembly.append("    shr r8, 3") 
            
        self.assembly.append("    cmp rbx, r8")
        self.assembly.append(f"    jge {bounds_fail}") 
        self.assembly.append(f"    jmp {bounds_ok}")

        self.assembly.append(f"{bounds_fail}:")
        self.assembly.append("    mov rax, 99") # OUT OF BOUNDS Hata Kodu
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
        self.assembly.append("    mov rax, 60")
        self.assembly.append("    syscall") 

        self.assembly.append(f"{bounds_ok}:")


        op = node.op_tok[1]

        if eval_type == 'char':
            if op == '=':
                self.assembly.append("    mov byte [rax + rbx], cl") # Sadece tek byte (cl) yaz
            else:
                raise Exception("Semantik Hata: String karakterleri uzerinde sadece '=' islemi yapilabilir.")
        else:
            self.assembly.append("    shl rbx, 3") # Index * 8 yap (Pointer Aritmetiği)
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
        """Class şablonunu compile time'da hafıza haritasına kaydeder."""
        class_name = node.class_name_tok[1]
        self.current_class = class_name
        for method in node.methods:
            self.generate(method)
        self.current_class = None

    def visit_MemberAccessNode(self, node):
        """nesne.alan okuması yapar """
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
        self.generate(node.left_node)
        self.assembly.append(f"    mov rax, qword [rax + {offset}]")

    def visit_MemberAssignNode(self, node):
        """nesne.alan = değer ataması yapar."""
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
        """new Class() yapısını gördüğünde sınıf boyutunu hesaplayıp alloc() çağırır."""
        class_name = node.class_name_tok[1]

        if class_name not in self.class_layouts:
            raise Exception(f"Derleme Hatası: '{class_name}' adında bir sınıf tanımlanmamış.")
        
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
                self.assembly.append(f"    mov {arg_registers[i+1]}, rax")

            self.assembly.append("    mov rdi, qword [rsp]")
            self.assembly.append(f"    call {method_name}")

            extra_args = max(0, arg_count -6)
            if extra_args > 0:
                self.assembly.append(f"    add rsp, {extra_args * 8}")
        
        self.assembly.append("    pop rax")

    def visit_MethodDefNode(self, node):
        """Sınıf içine yazılmış bir metodu Assembly'e çevirir."""
        if not self.current_class:
            raise Exception("Derleme Hatası: Metotlar sadece class içinde tanımlanabilir.")
        
        func_name = f"{self.current_class}_{node.func_name_tok[1]}"
        after_label = self.get_new_label(f"AFTER_METHOD_{func_name}")

        self.assembly.append(f"    jmp {after_label}")
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
            self.assembly.append("    sub rsp, 8")

            reg_index = i + 1 
            
            if reg_index < 6:
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], {arg_registers[reg_index]}")
            else:
                read_offset = 16 + (reg_index - 6) * 8
                self.assembly.append(f"    mov rax, qword [rbp + {read_offset}]")
                self.assembly.append(f"    mov qword [rbp - {self.stack_offset}], rax")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack_offset

        self.assembly.append("    mov rsp, rbp")
        self.assembly.append("    pop rbp")
        self.assembly.append("    ret")
        self.assembly.append(f"{after_label}:")

    def visit_MethodCallNode(self, node):
        """nesne.metot() çağrısını Assembly'e çevirir ve pointer'ı gizlice yollar."""
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
            self.assembly.append(f"    mov {arg_registers[i+1]}, rax")

        self.generate(node.left_node)
        self.assembly.append("    mov rdi, rax")

        self.assembly.append(f"    call {method_name}")

        extra_args = max(0, arg_count - 6)
        if extra_args > 0:
            self.assembly.append(f"    add rsp, {extra_args * 8}")

    def visit_ArrayLiteralNode(self, node):
        """Array Literal'ı otomatik olarak alloc ve ardışık mov işlemlerine çevirir."""
        element_count = len(node.elements)
        alloc_size = max(element_count * 8, 8)

        self.assembly.append(f"    mov rax, {alloc_size}")
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call alloc")

        self.assembly.append("    push rax")

        for i, element_node in enumerate(node.elements):
            self.generate(element_node)

            self.assembly.append("    mov rcx, rax")
            self.assembly.append("    mov rbx, qword [rsp]")

            offset = i * 8
            self.assembly.append(f"    mov qword [rbx + {offset}], rcx")

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
        """Kapsamlı Tip Dönüşümü (Cast) Yapar."""
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
                self.assembly.append("    mov rax, 0")
            else: 
                self.assembly.append("    cmp rax, 0")
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
            self.assembly.append("    movzx rax, byte [rax] ; String'in ilk karakterini al (ASCII int olarak)")
            
        
        elif target_type not in ('int', 'integer', 'double', 'float', 'bool', 'str', 'string', 'char'):
            pass

    def visit_DeleteNode(self, node):
        self.generate(node.target_node)
        self.assembly.append("    mov rdi, rax")
        self.assembly.append("    call free")

    def visit_AllegeNode(self, node):
        self.generate(node.condition)
        self.assembly.append("    cmp rax, 0")
        
        ok_lbl = self.get_new_label("ALLEGE_OK")
        self.assembly.append(f"    jne {ok_lbl}")

        self.assembly.append("    mov rax, 1") # Allege Error Code (1)
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
        self.assembly.append("    mov rax, 60")
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
        self.assembly.append("    mov rcx, 1")
        self.assembly.append(f"{ok_lbl}:")
        self.assembly.append("    push rax") 
        self.assembly.append("    push rcx")

        self.assembly.append("    mov rdi, rcx")
        self.assembly.append("    shl rdi, 3") 
        self.assembly.append("    call alloc")
        self.assembly.append("    mov r8, rax")

        self.assembly.append("    pop rcx") 
        self.assembly.append("    pop rax")

        self.assembly.append("    mov r9, 0") 
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
            raise Exception("Semantik Hata: 'break' sadece bir döngü icinde kullanilabilir.")
        _, end_label = self.loop_stack[-1]
        self.assembly.append(f"    jmp {end_label}")

    def visit_GoonNode(self, node):
        if not self.loop_stack:
            raise Exception("Semantik Hata: 'goon' sadece bir döngü icinde kullanilabilir.")
        continue_label, _ = self.loop_stack[-1]
        self.assembly.append(f"    jmp {continue_label}")

if __name__ == '__main__':
    from lexer import tokenize
    from parser import Parser
    from semantic import SemanticAnalyzer

    test_code = """
    // --- 1. UNIFIED PRINT TEST ---
    var sayi = 42;
    var ondalik = 3.14;
    var dogru_mu = true;
    var metin = "Wrench";

    print("--- 1. AKILLI PRINT TESTI ---\\n");
    print("Sayi: ");
    print(sayi); // Otomatik olarak print_int'e yonlenecek
    
    print("\\nOndalik: ");
    print(ondalik); // Otomatik olarak print_float'a yonlenecek
    
    print("\\nBool (1/0): ");
    print(dogru_mu); // bool oldugu icin integer 1/0 olarak basilacak
    
    print("\\nString: ");
    print(metin);
    
    print("\\nChar (metin[0]): ");
    print(metin[0]); // 'W' karakterini inline syscall ile basacak
    print("\\n\\n");

    // --- 2. ANFUNC (ANONIM) CAGRI TESTI ---
    print("--- 2. ANFUNC (ANONIM) CAGRI TESTI ---\\n");
    
    var topla = anfunc(int a, int b) {
        return a + b;
    };
    
    // Fonksiyon pointer'i (topla) uzerinden dinamik cagri yapiliyor!
    var sonuc = topla(15, 25);
    
    print("Anonim Fonksiyon Sonucu (40 olmali): ");
    print(sonuc);
    print("\\n--- TEST BITTI ---\\n");
    """

    #1. FRONTEND
    tokens = tokenize(test_code)
    parser = Parser(tokens)
    ast = parser.parse()

    #2. BACKEND
    semantic_analyzer = SemanticAnalyzer(strict_mode=True)
    semantic_analyzer.analyze(ast)

    compiler = CodeGen()
    compiler.generate(ast)
    asm_code = compiler.get_code()

    print("--- ENTERED WRENCH TEST CODE ---")
    print(test_code)
    print("--- GENERATED x86_64 ASSEMBLY CODE ---")
    print(asm_code)