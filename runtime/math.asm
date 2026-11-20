rt_int_pow:
    mov rcx, rsi
    mov eax, 1
    test rcx, rcx
    jle .pow_done
.pow_loop:
    imul rax, rdi
    dec rcx
    jnz .pow_loop
.pow_done:
    ret

rt_float_pow:
    push rbp
    mov rbp, rsp
    sub rsp, 16
    movsd [rsp], xmm0
    movsd [rsp + 8], xmm1
    fld qword [rsp + 8]
    fld qword [rsp]
    fyl2x
    fld st0
    frndint
    fsub st1, st0
    fxch st1
    f2xm1
    fld1
    faddp st1, st0
    fscale
    fstp st1
    fstp qword [rsp]
    movsd xmm0, [rsp]
    add rsp, 16
    mov rsp, rbp
    pop rbp
    ret