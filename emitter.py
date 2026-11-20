import os

# Runtime functions, modules containing them and their sub dependencies
RT_MANIFEST = {
    # core
    "rt_exit_prog": ("core", []),

    # memory
    "rt_alloc":          ("memory", []),
    "rt_free":           ("memory", []),
    "rt_realloc_mem":    ("memory", ["rt_alloc", "rt_free"]),
    "rt_get_len":        ("memory", []),
    "rt_set_mem":        ("memory", []),
    "rt_get_mem":        ("memory", []),
    "rt_get_mem32":      ("memory", []),

    # io
    "rt_print_string":   ("io", []),
    "rt_print_int":      ("io", []),
    "rt_print_hex":      ("io", []),
    "rt_print_float":    ("io", ["rt_print_int"]),
    "rt_read_input":     ("io", ["rt_alloc"]),
    "rt_read_int":       ("io", []),

    # string
    "rt_concat_strings": ("string", ["rt_alloc"]),
    "rt_compare_strings":("string", []),
    "rt_int_to_str":     ("string", ["rt_alloc"]),
    "rt_bool_to_str":    ("string", []),
    "rt_char_to_str":    ("string", ["rt_alloc"]),
    "rt_str_to_int":     ("string", []),
    "rt_str_ndup":       ("string", ["rt_alloc"]),

    # math
    "rt_int_pow":        ("math", []),
    "rt_float_pow":      ("math", []),
}

REG64_TO_32 = {
    "rax": "eax",
    "rbx": "ebx", 
    "rcx": "ecx", 
    "rdx": "edx",
    "rsi": "esi", 
    "rdi": "edi", 
    "r8": "r8d",  
    "r9": "r9d",
    "r10": "r10d",
    "r11": "r11d",
    "r12": "r12d",
    "r13": "r13d",
    "r14": "r14d",
    "r15": "r15d",
}

class AsmEmitter:
    def __init__(self, runtime_dir=None):
        if runtime_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            runtime_dir = os.path.join(base_dir, "runtime")
        self.runtime_dir = runtime_dir

        self.data_lines = []
        self.bss_lines = []
        self.main_lines = []
        self.func_lines = []

        self._target = self.main_lines
        self._used_rt = set()

        # --- Buffer Management ---

    def use_main_buffer(self):
        self._target = self.main_lines

    def use_func_buffer(self):
        self._target = self.func_lines

    def emit_data(self, line):
        self.data_lines.append(f"    {line}")

    def emit_bss(self, line):
        self.bss_lines.append(f"     {line}")

    def raw(self, line):
        """Adds raw line or comment."""
        self._target.append(line)

    def label(self, name):
        if self._target and self._target[-1] == f"    jmp {name}":
            self._target.pop()
        self._target.append(f"{name}:")

    def comment(self, text):
        self._target.append(f"    ; {text}")

    # --- Base Instructions and Auto Simplifications ---

    def mov(self, dst, src):
        # Peephole: mov {register_x}, [register_x] -> ignore
        if dst == src:
            return
        # Peephole: mov [register_x], 0 -> xor [register_x_32], [register_x_32] (2 bytes, with zero extension)
        if str(src) == "0" and dst in REG64_TO_32:
            r32 = REG64_TO_32[dst]
            self._target.append(f"   xor {r32}, {r32}")
            return
        self._target.append(f"    mov {dst}, {src}")

    def cmp(self, lhs, rhs):
        # Peephole: cmp {register_x}, 0 -> test {register_x}, {register_x}
        if str(rhs) == "0" and lhs in REG64_TO_32:
            self._target.append(f"    test {lhs}, {lhs}")
            return
        self._target.append(f"    cmp {lhs}, {rhs}")

    def add(self, dst, src):
        if str(src) == "0":
            return
        if str(src) == "1":
            self._target.append(f"    inc {dst}")
            return
        self._target.append(f"    add {dst}, {src}")

    def sub(self, dst, src):
        if str(src) == "0":
            return
        if str(src) == "1":
            self._target.append(f"    dec {dst}")
            return
        self._target.append(f"    sub {dst}, {src}")

    def push(self, reg):
        self._target.append(f"    push {reg}")

    def pop(self, reg):
        if self._target:
            last = self._target[-1]
            # push [register_x] + pop [register_x] -> delete entirely
            if last == f"push {reg}":
                self._target.pop()
                return
            # push [register_x] + pop [register_y] -> mov [register_y], [register_x]
            if last.startswith("    push "):
                src_reg = last[9:]
                self._target[-1] = f"    mov {reg}, {src_reg}"
                return
        self._target.append(f"    pop {reg}")

    def lea(self, dst, src):
        self._target.append(f"    lea {dst}, {src}")

    def jmp(self, label):
        if self._target:
            last = self._target[-1].strip()
            if last.startswith("jmp ") or last == "ret":
                return
        self._target.append(f"    jmp {label}")

    def jcc(self, cond, label):
        self._target.append(f"    j{cond} {label}")

    def call(self, target):
        self._target.append(f"    call {target}")

    def call_rt(self, rt_name):
        """Calls the runtime routine and marks the dependency tree."""
        self._mark_rt_used(rt_name)
        self._target.append(f"    call {rt_name}")

    def ret(self):
        self._target.append("    ret")

    def syscall(self):
        self._target.append("    syscall")

    def inst(self, opcode, *operands):
        """Instruction creator."""
        if operands:
            ops = ", ".join(str(op) for op in operands)
            self._target.append(f"    {opcode} {ops}")
        else:
            self._target.append(f"    {opcode}")

    # --- Runtime Dependency Solving and Compiling

    def _mark_rt_used(self, rt_name):
        if rt_name in self._used_rt:
            return
        self._used_rt.add(rt_name)
        meta = RT_MANIFEST.get(rt_name)
        if meta:
            for dep in meta[1]:
                self._mark_rt_used(dep)

    def _load_runtime_chunks(self):
        """Only loads the .asm content of used modules(Core is always included)."""
        needed_modules = {"core"}
        for rt_name in self._used_rt:
            meta = RT_MANIFEST.get(rt_name)
            if meta:
                needed_modules.add(meta[0])

        # Deterministic Ordering
        ordered_modules = [m for m in ("core", "memory", "io", "string", "math") if m in needed_modules]
        chunks = []
        for mod in ordered_modules:
            mod_path = os.path.join(self.runtime_dir, f"{mod}.asm")
            with open(mod_path, "r", encoding="utf-8") as f:
                chunks.append(f"; --- runtime/{mod}.asm ---\n" + f.read().strip())
        return "\n\n".join(chunks)

    def build(self):
        """Returns the final ASM code."""
        data_section = [
            "section .data",
            "    empty_str db 0",
            "    null_print_msg db `(null)`, 0",
            "    dot_str db `.`, 0",
            "    bool_true_msg db `true`, 0",
            "    bool_false_msg db `false`, 0",
            "    segfault_msg db `[CRITICAL]: Violated Memory Adress -->`, 0",
            "    unhandled_msg db `[FATAL]: Uncaught Segfault! Program Terminated.`, 10, 0",
            "    global_err_frame dq 0",
            "    global_argc dq 0",
            "    global_argv dq 0",
            "",
            "sigaction_struct:",
            "    dq sigsegv_handler    ; sa_sigaction",
            "    dq 0x44000004         ; sa_flags: SA_SIGINFO | SA_RESTORER | SA_NODEFER",
            "    dq sig_restorer       ; sa_restorer",
            "    dq 0                  ; sa_mask",
        ]
        if self.data_lines:
            data_section.extend(self.data_lines)

        bss_section = []
        if self.bss_lines:
            bss_section = ["", "section .bss", *self.bss_lines]

        start_section = [
            "",
            "; --- Entry Point ---",
            "_start:",
            "    mov rax, qword [rsp]",
            "    mov qword [rel global_argc], rax",
            "    lea rax, [rsp + 8]",
            "    mov qword [rel global_argv], rax",
            "    push rbp",
            "    mov rbp, rsp",
            "    mov edi, 11",
            "    lea rsi, [rel sigaction_struct]",
            "    xor edx, edx",
            "    mov r10d, 8",
            "    mov eax, 13",
            "    syscall",
            *self.main_lines,
            "",
            "    mov rsp, rbp",
            "    pop rbp",
            "    ; Program Exit (Syscall 60)",
            "    mov eax, 60",
            "    xor edi, edi",
            "    syscall",
        ]

        sections = [
            *data_section,
            *bss_section,
            "",
            "section .text",
            "global _start",
            "",
            self._load_runtime_chunks(),
            "",
            "; --- User Functions ---",
            *self.func_lines,
            *start_section,
        ]

        return "\n".join(sections) + "\n"