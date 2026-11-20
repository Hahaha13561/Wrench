sigsegv_handler:
    mov rax, qword [rsi + 16]
    mov rbx, qword [rel global_err_frame]
    test rbx, rbx
    jz .unhandled_segfault
    mov rcx, qword [rbx + 24]
    mov qword [rel global_err_frame], rcx
    mov rdx, qword [rbx + 16]
    mov rbp, qword [rbx + 8]
    mov rsp, qword [rbx]
    jmp rdx

.unhandled_segfault:
    mov eax, 1
    mov edi, 1
    lea rsi, [rel unhandled_msg]
    mov edx, 48
    syscall
    mov eax, 60
    mov edi, 139
    syscall

sig_restorer:
    mov eax, 15
    syscall

rt_exit_prog:
    mov eax, 60
    syscall