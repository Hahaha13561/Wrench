rt_print_string:
    test rax, rax
    jz .print_null_str
    mov rsi, rax
    xor edx, edx
.strlen_loop:
    cmp byte [rsi + rdx], 0
    je .strlen_done
    inc rdx
    jmp .strlen_loop
.strlen_done:
    mov edi, 1
    mov eax, 1
    syscall
    ret
.print_null_str:
    mov eax, 1
    mov edi, 1
    lea rsi, [rel null_print_msg]
    mov edx, 6
    syscall
    ret

rt_print_int:
    push rbp
    mov rbp, rsp
    push rbx
    sub rsp, 32
    mov ebx, 10
    xor ecx, ecx
    xor r8d, r8d
    test rax, rax
    jge .divide_loop
    neg rax
    mov r8d, 1
.divide_loop:
    xor edx, edx
    div rbx
    add rdx, 48
    push rdx
    inc rcx
    test rax, rax
    jne .divide_loop
    cmp r8d, 1
    jne .pop_chars
    push 45
    inc rcx
.pop_chars:
    xor edi, edi
.pop_loop:
    cmp rdi, rcx
    je .print_num
    pop rax
    mov byte [rbp - 32 + rdi], al
    inc rdi
    jmp .pop_loop
.print_num:
    mov eax, 1
    mov edi, 1
    lea rsi, [rbp - 32]
    mov rdx, rcx
    syscall
    add rsp, 32
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_print_hex:
    push rbp
    mov rbp, rsp
    push rbx
    sub rsp, 32
    mov byte [rbp - 32], 48
    mov byte [rbp - 31], 120
    mov ecx, 16
    mov ebx, 2
.hex_loop:
    mov rdx, rax
    shr rdx, 60
    and edx, 0xF
    cmp dl, 9
    jle .is_num
    add dl, 87
    jmp .store_hex
.is_num:
    add dl, 48
.store_hex:
    mov byte [rbp - 32 + rbx], dl
    inc rbx
    shl rax, 4
    dec rcx
    jnz .hex_loop
    mov byte [rbp - 32 + rbx], 0
    mov eax, 1
    mov edi, 1
    lea rsi, [rbp - 32]
    mov edx, 18
    syscall
    add rsp, 32
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_print_float:
    push rbp
    mov rbp, rsp
    push rbx
    sub rsp, 16
    movq xmm0, rax
    movsd [rsp], xmm0
    cvttsd2si rbx, xmm0
    mov rax, rbx
    call rt_print_int
    mov eax, 1
    mov edi, 1
    lea rsi, [rel dot_str]
    mov edx, 1
    syscall
    movsd xmm0, [rsp]
    cvtsi2sd xmm1, rbx
    subsd xmm0, xmm1
    mov eax, 100000
    cvtsi2sd xmm1, eax
    mulsd xmm0, xmm1
    cvttsd2si rax, xmm0
    test rax, rax
    jge .print_frac
    neg rax
.print_frac:
    call rt_print_int
    add rsp, 16
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_read_input:
    push rbp
    mov rbp, rsp
    push rax
    mov rdi, rax
    call rt_alloc
    test rax, rax
    jz .read_alloc_fail
    mov rsi, rax
    push rsi
    xor edi, edi
    mov rdx, [rbp - 8]
    xor eax, eax
    syscall
    pop rsi
    test rax, rax
    jle .read_done
    mov byte [rsi + rax - 1], 0
.read_done:
    mov rax, rsi
.read_alloc_fail:
    mov rsp, rbp
    pop rbp
    ret

rt_read_int:
    push rbp
    mov rbp, rsp
    push rbx
    sub rsp, 32
    xor eax, eax
    xor edi, edi
    lea rsi, [rbp - 40]
    mov edx, 31
    syscall
    xor ecx, ecx
    xor ebx, ebx
    xor r8d, r8d
    cmp byte [rbp - 40], 45
    jne .atoi_loop
    mov r8d, 1
    inc rcx
.atoi_loop:
    movzx rax, byte [rbp - 40 + rcx]
    cmp rax, 10
    je .atoi_done
    test rax, rax
    je .atoi_done
    cmp rax, 48
    jl .atoi_done
    cmp rax, 57
    jg .atoi_done
    sub rax, 48
    imul rbx, 10
    add rbx, rax
    inc rcx
    jmp .atoi_loop
.atoi_done:
    mov rax, rbx
    cmp r8d, 1
    jne .read_int_exit
    neg rax
.read_int_exit:
    add rsp, 32
    pop rbx
    mov rsp, rbp
    pop rbp
    ret