rt_alloc:
    push rbp
    mov rbp, rsp
    add rdi, 8
    push rdi
    mov rsi, rdi
    xor edi, edi
    mov edx, 3
    mov r10d, 34
    mov r8, -1
    xor r9d, r9d
    mov eax, 9
    syscall
    test rax, rax
    js .alloc_failed
    push rax
    mov rdi, rax
    mov rdx, [rbp - 8]
    mov rcx, rdx
    shr rcx, 3
    xor eax, eax
    rep stosq
    mov rcx, rdx
    and rcx, 7
    rep stosb
    pop rax
    mov rcx, [rbp - 8]
    sub rcx, 8
    mov qword [rax], rcx
    add rax, 8
    mov rsp, rbp
    pop rbp
    ret
.alloc_failed:
    pop rdi
    xor eax, eax
    mov rsp, rbp
    pop rbp
    ret

rt_free:
    push rbp
    mov rbp, rsp
    test rdi, rdi
    jz .free_done
    sub rdi, 8
    mov rsi, qword [rdi]
    add rsi, 8
    mov eax, 11
    syscall
.free_done:
    mov rsp, rbp
    pop rbp
    ret

rt_realloc_mem:
    test rdi, rdi
    jnz .do_mremap
    mov rdi, rsi
    jmp rt_alloc
.do_mremap:
    push rbp
    mov rbp, rsp
    sub rdi, 8
    mov rcx, qword [rdi]
    add rcx, 8
    mov rdx, rsi
    add rdx, 8
    mov rsi, rcx
    mov r10d, 1
    mov eax, 25
    syscall
    test rax, rax
    js .realloc_failed
    sub rdx, 8
    mov qword [rax], rdx
    add rax, 8
    mov rsp, rbp
    pop rbp
    ret
.realloc_failed:
    xor eax, eax
    mov rsp, rbp
    pop rbp
    ret

rt_get_len:
    sub rdi, 8
    mov rax, qword [rdi]
    shr rax, 3
    ret

rt_set_mem:
    mov qword [rdi + rsi], rdx
    ret

rt_get_mem:
    mov rax, qword [rdi + rsi]
    ret

rt_get_mem32:
    movsxd rax, dword [rdi + rsi]
    ret