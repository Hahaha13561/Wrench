rt_concat_strings:
    push rbp
    mov rbp, rsp
    push rbx
    test rdi, rdi
    jnz .check_rsi
    lea rdi, [rel empty_str]
.check_rsi:
    test rsi, rsi
    jnz .do_concat
    lea rsi, [rel empty_str]
.do_concat:
    push rdi
    push rsi
    xor ebx, ebx
.len1:
    cmp byte [rdi + rbx], 0
    je .len1_done
    inc rbx
    jmp .len1
.len1_done:
    xor ecx, ecx
.len2:
    cmp byte [rsi + rcx], 0
    je .len2_done
    inc rcx
    jmp .len2
.len2_done:
    lea rax, [rbx + rcx + 1]
    push rax
    push rbx
    push rcx
    mov rdi, rax
    call rt_alloc
    mov r8, rax
    pop rcx
    pop rbx
    pop rax
    pop rsi
    pop rdi
    xor r9d, r9d
.copy1:
    cmp r9, rbx
    je .copy1_done
    mov dl, byte [rdi + r9]
    mov byte [r8 + r9], dl
    inc r9
    jmp .copy1
.copy1_done:
    xor r10d, r10d
    lea r11, [r8 + rbx]
.copy2:
    cmp r10, rcx
    je .copy2_done
    mov dl, byte [rsi + r10]
    mov byte [r11 + r10], dl
    inc r10
    jmp .copy2
.copy2_done:
    mov byte [r11 + rcx], 0
    mov rax, r8
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_compare_strings:
    push rbp
    mov rbp, rsp
    push rbx
    test rdi, rdi
    jz .cmp_rdi_null
    test rsi, rsi
    jz .cmp_rsi_null
    xor ecx, ecx
.cmp_loop:
    mov al, byte [rdi + rcx]
    mov bl, byte [rsi + rcx]
    cmp al, bl
    jne .cmp_diff
    test al, al
    jz .cmp_equal
    inc rcx
    jmp .cmp_loop
.cmp_diff:
    ja .cmp_greater
    mov rax, -1
    jmp .cmp_exit
.cmp_greater:
    mov eax, 1
    jmp .cmp_exit
.cmp_equal:
    xor eax, eax
    jmp .cmp_exit
.cmp_rdi_null:
    test rsi, rsi
    jz .cmp_equal
    mov rax, -1
    jmp .cmp_exit
.cmp_rsi_null:
    mov eax, 1
.cmp_exit:
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_int_to_str:
    push rbp
    mov rbp, rsp
    push rbx
    push rdi
    mov edi, 32
    call rt_alloc
    pop rcx
    mov r8, rax
    test rcx, rcx
    jnz .check_neg
    mov byte [r8], 48
    mov byte [r8 + 1], 0
    mov rax, r8
    pop rbx
    mov rsp, rbp
    pop rbp
    ret
.check_neg:
    xor r9d, r9d
    test rcx, rcx
    jge .conv_setup
    neg rcx
    mov r9d, 1
.conv_setup:
    mov rax, rcx
    mov ebx, 10
    xor r10d, r10d
.conv_loop:
    test rax, rax
    jz .pop_dig
    xor edx, edx
    div rbx
    add rdx, 48
    push rdx
    inc r10
    jmp .conv_loop
.pop_dig:
    xor r11d, r11d
    cmp r9d, 1
    jne .pop_loop
    mov byte [r8 + r11], 45
    inc r11
.pop_loop:
    test r10, r10
    jz .done_str
    pop rdx
    mov byte [r8 + r11], dl
    inc r11
    dec r10
    jmp .pop_loop
.done_str:
    mov byte [r8 + r11], 0
    mov rax, r8
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_bool_to_str:
    test rdi, rdi
    jnz .bool_true
    lea rax, [rel bool_false_msg]
    ret
.bool_true:
    lea rax, [rel bool_true_msg]
    ret

rt_char_to_str:
    push rbp
    mov rbp, rsp
    push rbx
    mov rbx, rdi
    mov edi, 2
    call rt_alloc
    mov byte [rax], bl
    mov byte [rax + 1], 0
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_str_to_int:
    push rbp
    mov rbp, rsp
    push rbx
    xor ecx, ecx
    xor ebx, ebx
    xor r8d, r8d
    cmp byte [rdi], 45
    jne .parse_loop
    mov r8d, 1
    inc rcx
.parse_loop:
    movzx rax, byte [rdi + rcx]
    test rax, rax
    jz .parse_done
    cmp rax, 48
    jl .parse_error
    cmp rax, 57
    jg .parse_error
    sub rax, 48
    imul rbx, 10
    add rbx, rax
    inc rcx
    jmp .parse_loop
.parse_done:
    mov rax, rbx
    cmp r8d, 1
    jne .parse_exit
    neg rax
.parse_exit:
    pop rbx
    mov rsp, rbp
    pop rbp
    ret
.parse_error:
    xor eax, eax
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

rt_str_ndup:
    push rbp
    mov rbp, rsp
    push rdi
    push rsi
    lea rdi, [rsi + 1]
    call rt_alloc
    pop rsi
    pop rdi
    xor ecx, ecx
.ndup_copy_loop:
    cmp rcx, rsi
    je .ndup_copy_done
    mov dl, byte [rdi + rcx]
    mov byte [rax + rcx], dl
    inc rcx
    jmp .ndup_copy_loop
.ndup_copy_done:
    mov byte [rax + rsi], 0
    mov rsp, rbp
    pop rbp
    ret