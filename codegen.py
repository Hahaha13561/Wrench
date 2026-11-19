from emitter import AsmEmitter

class CodeGen:
    def __init__(self, semantic_analyzer=None):
        self.emit = AsmEmitter()
        self.current_func_exit_label = None
        self.environments = [{}]
        self.stack_offset = 0
        self.label_count = 0
        self.string_count = 0
        self.class_layouts = {}
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

    def _can_use_direct_rhs(self, node):
        """Returns an immediate or memory operand string if RHS can be used directly without stack push/pop."""
        ntype = type(node).__name__
        if ntype == 'NumberNode' and node.tok[0] != 'FLOAT':
            val = int(node.tok[1], 0)
            if -2147483648 <= val <= 2147483647:
                return node.tok[1]
        elif ntype == 'VarAccessNode':
            return self.get_var_loc(node.var_name_tok[1])
        return None

    def _emit_raise_error(self, err_code):
        """Emits standard runtime exception unwinding or exits with err_code if uncaught."""
        crash_lbl = self.get_new_label("CRASH")
        self.emit.mov("eax", err_code)
        self.emit.mov("rbx", "qword [rel global_err_frame]")
        self.emit.cmp("rbx", 0)
        self.emit.jcc("e", crash_lbl)
        self.emit.mov("rcx", "qword [rbx + 24]")
        self.emit.mov("qword [rel global_err_frame]", "rcx")
        self.emit.mov("rdx", "qword [rbx + 16]")
        self.emit.mov("rbp", "qword [rbx + 8]")
        self.emit.mov("rsp", "qword [rbx]")
        self.emit.jmp("rdx")
        self.emit.label(crash_lbl)
        self.emit.mov("rdi", "rax")
        self.emit.mov("eax", 60)
        self.emit.syscall()

    def _emit_print_char(self):
        """Prints the single byte in AL to stdout."""
        self.emit.push("rax")
        self.emit.mov("rsi", "rsp")
        self.emit.mov("edi", 1)
        self.emit.mov("edx", 1)
        self.emit.mov("eax", 1)
        self.emit.syscall()
        self.emit.pop("rax")

    def generate_branch(self, cond_node, false_label):
        """Turns Condition Statements into Inverse JMP instructions."""
        if type(cond_node).__name__ == 'BinOpNode':
            op = cond_node.op_tok[1]
            op_type = getattr(cond_node, 'operand_type', getattr(cond_node.left_node, 'eval_type', 'int'))

            # Integer / Pointer / Bool comparisons
            if op_type in ('int', 'integer', 'bool', 'ptr', 'pointer') and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                direct_rhs = self._can_use_direct_rhs(cond_node.right_node)
                if direct_rhs is not None:
                    self.generate(cond_node.left_node)
                    self.emit.cmp("rax", direct_rhs)
                else:
                    self.generate(cond_node.right_node)
                    self.emit.push("rax")
                    self.generate(cond_node.left_node)
                    self.emit.pop("rbx")
                    self.emit.cmp("rax", "rbx")

                if op in ('=?', '?=', 'is', 'same'):   self.emit.jcc("ne", false_label)
                elif op in ('!=', '=!'):              self.emit.jcc("e", false_label)
                elif op == '>':                       self.emit.jcc("le", false_label)
                elif op == '<':                       self.emit.jcc("ge", false_label)
                elif op in ('>=', '=>'):              self.emit.jcc("l", false_label)
                elif op in ('<=', '=<'):              self.emit.jcc("g", false_label)
                return

            # Float/Double comparisons
            elif op_type == 'double' and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                self.generate(cond_node.right_node)
                self.emit.push("rax")
                self.generate(cond_node.left_node)
                self.emit.inst("movq", "xmm0", "rax")
                self.emit.inst("movq", "xmm1", "[rsp]")
                self.emit.add("rsp", 8)
                self.emit.inst("ucomisd", "xmm0", "xmm1")

                if op in ('=?', '?=', 'is', 'same'):   self.emit.jcc("ne", false_label)
                elif op in ('!=', '=!'):              self.emit.jcc("e", false_label)
                elif op == '>':                       self.emit.jcc("be", false_label)
                elif op == '<':                       self.emit.jcc("ae", false_label)
                elif op in ('>=', '=>'):              self.emit.jcc("b", false_label)
                elif op in ('<=', '=<'):              self.emit.jcc("a", false_label)
                return

            # String comparisons
            elif op_type in ('str', 'string') and op in ('=?', '?=', 'is', 'same', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<'):
                self.generate(cond_node.right_node)
                self.emit.push("rax")
                self.generate(cond_node.left_node)
                self.emit.mov("rdi", "rax")
                self.emit.pop("rsi")
                self.emit.call_rt("rt_compare_strings")
                self.emit.cmp("rax", 0)

                if op in ('=?', '?=', 'is', 'same'):   self.emit.jcc("ne", false_label)
                elif op in ('!=', '=!'):              self.emit.jcc("e", false_label)
                elif op == '>':                       self.emit.jcc("le", false_label)
                elif op == '<':                       self.emit.jcc("ge", false_label)
                elif op in ('>=', '=>'):              self.emit.jcc("l", false_label)
                elif op in ('<=', '=<'):              self.emit.jcc("g", false_label)
                return

        self.generate(cond_node)
        self.emit.cmp("rax", 0)
        self.emit.jcc("e", false_label)

    def generic_visit(self, node):
        raise Exception(f'ERROR: No Assembly Translation for {type(node).__name__}.')

    def get_code(self):
        """Produces the final NASM assembly output via AsmEmitter."""
        return self.emit.build()

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

        if node_class == 'BinOpNode':
            if node.op_tok[1] in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same', 'and', 'or'):
                return 'bool'

        elif node_class == 'VarAccessNode':
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

    def _is_temp_string(self, node):
        """Checks whether the node produces a heap-allocated temporary string that needs to be freed."""
        if node is None:
            return False

        ntype = type(node).__name__
        if ntype in ('VarAccessNode', 'StringNode', 'MemberAccessNode'):
            return False

        if ntype == 'BinOpNode':
            op_type = getattr(node, 'operand_type', getattr(node.left_node, 'eval_type', 'int'))
            return op_type in ('str', 'string') and node.op_tok[1] == '+'

        if ntype == 'CastNode':
            src_type = getattr(node.node, 'eval_type', None) or self._get_obj_type(node.node)
            return node.type_tok[1] in ('str', 'string') and src_type not in ('bool', 'boolean')

        if ntype == 'FuncCallNode':
            ret_type = self._get_obj_type(node)
            return ret_type in ('str', 'string')

        return False

    def _emit_str_coercion(self, expr_type):
        """Turns the value in RAX into a string pointer in runtime."""
        if expr_type in ('str', 'string'):
            return
        elif expr_type in ('bool', 'boolean'):
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_bool_to_str")
        elif expr_type == 'char':
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_char_to_str")
        else:
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_int_to_str")
       
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
        """Places a numeric literal into RAX."""
        if node.tok[0] == 'FLOAT':
            self.emit.mov("rax", f"__float64__({node.tok[1]})")      
        else:    
            num = int(node.tok[1], 0)
            if num == 0:
                self.emit.mov("rax", 0)
            elif 0 < num <= 2147483647:
                self.emit.mov("eax", node.tok[1])
            else:
                self.emit.mov("rax", node.tok[1])

    def visit_IfNode(self, node):
        """Turns if, butif and else cases to JMPs."""
        end_label = self.get_new_label("IF_END")
        initial_offset = self.stack_offset

        for condition, block in node.cases:
            next_case_label = self.get_new_label("NEXT_CASE")
            self.stack_offset = initial_offset

            self.generate_branch(condition, next_case_label)
            self.generate(block)
            self.emit.jmp(end_label)
            self.emit.label(next_case_label)

        if node.else_case:
            self.stack_offset = initial_offset
            self.generate(node.else_case)

        self.stack_offset = initial_offset
        self.emit.label(end_label)

    def visit_WhileNode(self, node):
        """While loop."""
        start_label = self.get_new_label("WHILE_START")
        end_label = self.get_new_label("WHILE_END")

        self.loop_stack.append((start_label, end_label))
        self.emit.label(start_label)

        self.generate_branch(node.condition_node, end_label)
        self.generate(node.body_node)
        self.emit.jmp(start_label)
        self.emit.label(end_label)

        self.loop_stack.pop()

    def visit_ForNode(self, node):
        var_name = node.var_name_tok[1]

        self.enter_scope()
        current_env = self.environments[-1]

        # Single 32-byte allocation for ptr, len, idx, and loop variable
        self.emit.sub("rsp", 32)
        self.stack_offset += 8
        ptr_offset = self.stack_offset
        self.stack_offset += 8
        len_offset = self.stack_offset
        self.stack_offset += 8
        idx_offset = self.stack_offset
        self.stack_offset += 8
        current_env[var_name] = self.stack_offset
        elem_offset = self.stack_offset

        self.generate(node.iter_node)
        self.emit.mov(f"qword [rbp - {ptr_offset}]", "rax")

        self.emit.mov("rdi", "rax")
        self.emit.call_rt("rt_get_len")
        self.emit.mov(f"qword [rbp - {len_offset}]", "rax")
        self.emit.mov(f"qword [rbp - {idx_offset}]", 0)

        start_label = self.get_new_label("FOR_START")
        inc_label = self.get_new_label("FOR_INC")
        end_label = self.get_new_label("FOR_END")

        self.loop_stack.append((inc_label, end_label))
        self.emit.label(start_label)

        self.emit.mov("rax", f"qword [rbp - {idx_offset}]")
        self.emit.cmp("rax", f"qword [rbp - {len_offset}]")
        self.emit.jcc("ge", end_label)

        self.emit.mov("rbx", f"qword [rbp - {idx_offset}]")
        self.emit.mov("rax", f"qword [rbp - {ptr_offset}]")
        self.emit.mov("rcx", "qword [rax + rbx*8]")
        self.emit.mov(f"qword [rbp - {elem_offset}]", "rcx")

        self.generate(node.body)

        self.emit.label(inc_label)
        self.emit.inst("inc", f"qword [rbp - {idx_offset}]")
        self.emit.jmp(start_label)

        self.emit.label(end_label)
        self.loop_stack.pop()
        self.exit_scope()

    def visit_ReAssignNode(self, node):
        """Updates an existing variable."""
        var_name = node.var_name_tok[1]
        loc = self.get_var_loc(var_name)
        if not loc or "None" in loc:
            raise RuntimeError(f"{var_name} is not found.")

        self.generate(node.value_node)
        op = node.op_tok[1]

        var_type = self.get_var_type(var_name)
        val_type = getattr(node.value_node, 'eval_type', None) or self._get_obj_type(node.value_node) or 'int'

        if var_type in ('str', 'string') or val_type in ('str', 'string'):
            if op in ('+=', '=+'):
                self._emit_str_coercion(val_type)
                self.emit.push("rax")
                self.emit.mov("rax", loc)
                self._emit_str_coercion(var_type)
                self.emit.mov("rdi", "rax")
                self.emit.pop("rsi")
                self.emit.call_rt("rt_concat_strings")
                self.emit.mov(loc, "rax")
                return
            elif op == '=':
                self.emit.mov(loc, "rax")
                return
            else:
                raise Exception("Semantic Error: unsupported operation type on string value")

        if var_type in ('double', 'float') or val_type in ('double', 'float'):
            self.emit.inst("movq", "xmm1", "rax")
            if op == '=':
                self.emit.inst("movq", loc, "xmm1")
                return
            self.emit.mov("rax", loc)
            self.emit.inst("movq", "xmm0", "rax")

            if op in ('+=', '=+'):
                self.emit.inst("addsd", "xmm0", "xmm1")
            elif op in ('-=', '=-'):
                self.emit.inst("subsd", "xmm0", "xmm1")
            elif op in ('*=', '=*'):
                self.emit.inst("mulsd", "xmm0", "xmm1")
            elif op in ('/=', '=/'):
                self.emit.inst("divsd", "xmm0", "xmm1")
            self.emit.inst("movq", "rax", "xmm0")
            self.emit.mov(loc, "rax")
            return

        if op == '=':
            self.emit.mov(loc, "rax")
        elif op in ('+=', '=+'):
            self.emit.add(loc, "rax")
        elif op in ('-=', '=-'):
            self.emit.sub(loc, "rax")
        elif op in ('*=', '=*'):
            self.emit.inst("imul", "rax", loc)
            self.emit.mov(loc, "rax")
        elif op in ('/=', '=/'):
            self.emit.mov("rbx", "rax")
            self.emit.mov("rax", loc)
            self.emit.inst("cqo")
            self.emit.inst("idiv", "rbx")
            self.emit.mov(loc, "rax")
        elif op in ('%=', '=%'):
            self.emit.mov("rbx", "rax")
            self.emit.mov("rax", loc)
            self.emit.inst("cqo")
            self.emit.inst("idiv", "rbx")
            self.emit.mov(loc, "rdx")
        elif op in ('^=', '=^'):
            self.emit.mov("rsi", "rax")
            self.emit.mov("rdi", loc)
            self.emit.call_rt("rt_int_pow")
            self.emit.mov(loc, "rax")

    def visit_AttemptNode(self, node):
        attempt_start = self.get_new_label("ATTEMPT_START")
        exclude_label = self.get_new_label("EXCLUDE")
        final_label = self.get_new_label("FINAL")
        end_label = self.get_new_label("ATTEMPT_END")
        old_stack = self.stack_offset

        self.emit.sub("rsp", 32)
        self.stack_offset += 8
        off_old_frame = self.stack_offset
        self.stack_offset += 8
        off_ex_lbl = self.stack_offset
        self.stack_offset += 8
        off_old_rbp = self.stack_offset
        self.stack_offset += 8
        off_old_rsp = self.stack_offset

        self.emit.mov("rax", "qword [rel global_err_frame]")
        self.emit.mov(f"qword [rbp - {off_old_frame}]", "rax")
        self.emit.lea("rax", f"[rel {exclude_label}]")
        self.emit.mov(f"qword [rbp - {off_ex_lbl}]", "rax")
        self.emit.mov(f"qword [rbp - {off_old_rbp}]", "rbp")
        self.emit.lea("rax", "[rsp + 32]")
        self.emit.mov(f"qword [rbp - {off_old_rsp}]", "rax")

        self.emit.lea("rax", f"[rbp - {off_old_rsp}]")
        self.emit.mov("qword [rel global_err_frame]", "rax")

        self.emit.label(attempt_start)
        self.generate(node.attempt_body)

        self.emit.mov("rax", f"qword [rbp - {off_old_frame}]")
        self.emit.mov("qword [rel global_err_frame]", "rax")
        self.emit.jmp(final_label)

        self.emit.label(exclude_label)
        self.emit.mov("rsp", "rbp")
        self.emit.sub("rsp", 64)

        self.stack_offset = old_stack
        if node.exclude_body:
            self.enter_scope()
            self.stack_offset = 32
            self.environments[-1]['err'] = self.stack_offset
            self.emit.mov(f"qword [rbp - {self.stack_offset}]", "rax")

            self.generate(node.exclude_body)
            self.exit_scope()
        else:
            self.emit.push("rax")
            if node.final_body:
                self.generate(node.final_body)
            self.emit.pop("rax")

            self.emit.mov("rbx", "qword [rel global_err_frame]")
            self.emit.cmp("rbx", 0)
            self.emit.jcc("e", f"{end_label}_crash")
            self.emit.mov("rcx", "qword [rbx + 24]")
            self.emit.mov("qword [rel global_err_frame]", "rcx")
            self.emit.mov("rdx", "qword [rbx + 16]")
            self.emit.mov("rbp", "qword [rbx + 8]")
            self.emit.mov("rsp", "qword [rbx]")
            self.emit.jmp("rdx")

            self.emit.label(f"{end_label}_crash")
            self.emit.mov("rdi", "rax")
            self.emit.mov("eax", 60)
            self.emit.syscall()
            self.emit.jmp(end_label)

        self.emit.label(final_label)
        if node.final_body:
            self.generate(node.final_body)

        self.emit.label(end_label)

    def visit_TriggerNode(self, node):
        self.generate(node.err_value_node)
        crash_label = self.get_new_label("CRASH")

        self.emit.mov("rbx", "qword [rel global_err_frame]")
        self.emit.cmp("rbx", 0)
        self.emit.jcc("e", crash_label)

        self.emit.mov("rcx", "qword [rbx + 24]")
        self.emit.mov("qword [rel global_err_frame]", "rcx")
        self.emit.mov("rdx", "qword [rbx + 16]")
        self.emit.mov("rbp", "qword [rbx + 8]")
        self.emit.mov("rsp", "qword [rbx]")
        self.emit.jmp("rdx")

        self.emit.label(crash_label)
        self.emit.mov("rdi", "rax")
        self.emit.mov("eax", 60)
        self.emit.syscall()

    def visit_VarAssignNode(self, node):
        var_name = node.var_name_tok[1]

        self.generate(node.value_node)
        current_env = self.environments[-1]

        if var_name not in current_env:
            if len(self.environments) == 1:
                label = f"gvar_{var_name}"
                self.emit.emit_data(f"{label} dq 0")
                current_env[var_name] = label
            else:
                self.stack_offset += 8
                current_env[var_name] = self.stack_offset
                self.emit.sub("rsp", 8)

        declared_type = node.type_tok[1] if hasattr(node, 'type_tok') and node.type_tok else None
        inferred_type = self._get_obj_type(node.value_node)
        var_type = declared_type if (declared_type and declared_type != 'var') else inferred_type

        if var_type:
            self.type_environments[-1][var_name] = var_type

        loc = self.get_var_loc(var_name)
        self.emit.mov(loc, "rax")

    def visit_VarAccessNode(self, node):
        """Reads the variable value from RAM."""
        var_name = node.var_name_tok[1]
        loc = self.get_var_loc(var_name)
        if loc is None:
            if (self.semantic_analyzer and hasattr(self.semantic_analyzer, 'functions') and var_name in self.semantic_analyzer.functions) or var_name in self.function_return_types:
                self.emit.lea("rax", f"[rel fn_{var_name}]")
                return
            raise RuntimeError(f"{var_name} is not found.")
        self.emit.mov("rax", loc)

    def visit_BinOpNode(self, node):    
        """Reduces mathematics, comparison, and string operations to assembly language."""
        op_type = getattr(node, 'operand_type', getattr(node.left_node, 'eval_type', 'int'))
        left_type = getattr(node.left_node, 'eval_type', None) or self._get_obj_type(node.left_node) or 'int'
        right_type = getattr(node.right_node, 'eval_type', None) or self._get_obj_type(node.right_node) or 'int'
        op = node.op_tok[1]

        if op_type in ('str', 'string') or left_type in ('str', 'string') or right_type in ('str', 'string'):
            self.generate(node.right_node)
            if op == '+':
                left_is_temp = self._is_temp_string(node.left_node) or (left_type not in ('str', 'string', 'bool', 'boolean'))
                right_is_temp = self._is_temp_string(node.right_node) or (right_type not in ('str', 'string', 'bool', 'boolean'))

                self._emit_str_coercion(right_type)
                self.emit.push("rax")
                self.generate(node.left_node)
                self._emit_str_coercion(left_type)
                self.emit.push("rax")

                self.emit.mov("rdi", "qword [rsp]")
                self.emit.mov("rsi", "qword [rsp + 8]")
                self.emit.call_rt("rt_concat_strings")

                if left_is_temp or right_is_temp:
                    self.emit.push("rax")
                    if left_is_temp:
                        self.emit.mov("rdi", "qword [rsp + 8]")
                        self.emit.call_rt("rt_free")
                    if right_is_temp:
                        self.emit.mov("rdi", "qword [rsp + 16]")
                        self.emit.call_rt("rt_free")
                    self.emit.pop("rax")

                self.emit.add("rsp", 16)
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.emit.push("rax")
                self.generate(node.left_node)
                self.emit.mov("rdi", "rax")
                self.emit.pop("rsi")
                self.emit.call_rt("rt_compare_strings")
                self.emit.cmp("rax", 0)

                if op in ('=?', '?=', 'is', 'same'):   self.emit.inst("sete", "al")
                elif op in ('!=', '=!'):              self.emit.inst("setne", "al")
                elif op == '>':                       self.emit.inst("setg", "al")
                elif op == '<':                       self.emit.inst("setl", "al")
                elif op in ('>=', '=>'):              self.emit.inst("setge", "al")
                elif op in ('<=', '=<'):              self.emit.inst("setle", "al")
                self.emit.inst("movzx", "rax", "al")
            else:
                raise Exception("Semantic Error: Unsupported operation between strings.")

        elif op_type == 'double':
            self.generate(node.right_node)
            self.emit.push("rax")
            self.generate(node.left_node)

            self.emit.inst("movq", "xmm0", "rax")
            self.emit.inst("movq", "xmm1", "[rsp]")
            self.emit.add("rsp", 8)

            if op == '+':
                self.emit.inst("addsd", "xmm0", "xmm1")
                self.emit.inst("movq", "rax", "xmm0")
            elif op == '-':
                self.emit.inst("subsd", "xmm0", "xmm1")
                self.emit.inst("movq", "rax", "xmm0")
            elif op == '*':
                self.emit.inst("mulsd", "xmm0", "xmm1")
                self.emit.inst("movq", "rax", "xmm0")
            elif op == '/':
                self.emit.inst("divsd", "xmm0", "xmm1")
                self.emit.inst("movq", "rax", "xmm0")
            elif op == '%':
                # Pure SSE2 remainder: xmm0 - trunc(xmm0 / xmm1) * xmm1
                self.emit.inst("movapd", "xmm2", "xmm0")
                self.emit.inst("divsd", "xmm2", "xmm1")
                self.emit.inst("roundsd", "xmm2", "xmm2", 3)
                self.emit.inst("mulsd", "xmm2", "xmm1")
                self.emit.inst("subsd", "xmm0", "xmm2")
                self.emit.inst("movq", "rax", "xmm0")
            elif op == '^':
                self.emit.call_rt("rt_float_pow")
                self.emit.inst("movq", "rax", "xmm0")
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.emit.inst("ucomisd", "xmm0", "xmm1")
                if op in ('=?', '?=', 'is', 'same'):
                    self.emit.inst("sete", "al")
                    self.emit.inst("setnp", "bl")
                    self.emit.inst("and", "al", "bl")
                elif op in ('!=', '=!'):
                    self.emit.inst("setne", "al")
                    self.emit.inst("setp", "bl")
                    self.emit.inst("or", "al", "bl")
                elif op == '>':          self.emit.inst("seta", "al")
                elif op == '<':          self.emit.inst("setb", "al")
                elif op in ('>=', '=>'): self.emit.inst("setae", "al")
                elif op in ('<=', '=<'): self.emit.inst("setbe", "al")
                self.emit.inst("movzx", "rax", "al")

        else:
            # --- INTEGER NUMBERS ---
            direct_rhs = self._can_use_direct_rhs(node.right_node)
            if direct_rhs is not None and op in ('+', '-', 'and', 'or', 'xor', '=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.generate(node.left_node)
                rhs_op = direct_rhs
            else:
                self.generate(node.right_node)
                self.emit.push("rax")
                self.generate(node.left_node)
                self.emit.pop("rbx")
                rhs_op = "rbx"

            if op == '+':
                self.emit.add("rax", rhs_op)
            elif op == '-':
                self.emit.sub("rax", rhs_op)
            elif op == '*':
                self.emit.inst("imul", "rax", rhs_op)
            elif op == '/':
                self.emit.inst("cqo")
                self.emit.inst("idiv", "rbx")
            elif op == '%':
                self.emit.inst("cqo")
                self.emit.inst("idiv", "rbx")
                self.emit.mov("rax", "rdx")
            elif op == '^':
                self.emit.mov("rdi", "rax")
                self.emit.mov("rsi", "rbx")
                self.emit.call_rt("rt_int_pow")
            elif op == 'and':
                self.emit.inst("and", "rax", rhs_op)
            elif op == 'or':
                self.emit.inst("or", "rax", rhs_op)
            elif op == 'xor':
                self.emit.inst("xor", "rax", rhs_op)
            elif op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
                self.emit.cmp("rax", rhs_op)
                if op in ('=?', '?=', 'is', 'same'):   self.emit.inst("sete", "al")
                elif op in ('!=', '=!'):              self.emit.inst("setne", "al")
                elif op == '>':                       self.emit.inst("setg", "al")
                elif op == '<':                       self.emit.inst("setl", "al")
                elif op in ('>=', '=>'):              self.emit.inst("setge", "al")
                elif op in ('<=', '=<'):              self.emit.inst("setle", "al")
                self.emit.inst("movzx", "rax", "al")

    def visit_UnaryOpNode(self, node):
        op = node.op_tok[1]

        if op in ('not', '!'):
            self.generate(node.node)
            self.emit.cmp("rax", 0)
            self.emit.inst("sete", "al")
            self.emit.inst("movzx", "rax", "al")

        elif op == '-':
            self.generate(node.node)
            op_type = getattr(node, 'operand_type', getattr(node, 'eval_type', getattr(node.node, 'eval_type', 'int')))
            if op_type in ('double', 'float'):
                self.emit.inst("movq", "xmm0", "rax")
                self.emit.inst("pxor", "xmm1", "xmm1")
                self.emit.inst("subsd", "xmm1", "xmm0")
                self.emit.inst("movq", "rax", "xmm1")
            else:
                self.emit.inst("neg", "rax")

        elif op in ('await', 'wait'):
            self.generate(node.node)
            self.emit.mov("rdi", "rax")
            self.emit.mov("esi", 0)
            self.emit.mov("edx", 0)
            self.emit.mov("r10d", 0)
            self.emit.mov("eax", 61)
            self.emit.syscall()

    def visit_BlockNode(self, node):
        """Converts the code blocks (lines) inside curly braces to Assembly in order."""
        self.enter_scope()

        for statement in node.statements:
            self.generate(statement)

        self.exit_scope()

    def visit_FuncCallNode(self, node):
        """Calls the functions and builtins."""
        func_name = node.node_to_call.var_name_tok[1]

        if func_name == 'print':
            arg_node = node.arg_nodes[0]
            self.generate(arg_node)

            arg_type = getattr(arg_node, 'eval_type', 'string')
            if arg_type in ('any', 'var') and type(arg_node).__name__ == 'MemberAccessNode':
                real_type = self._get_obj_type(arg_node)
                if real_type:
                    arg_type = real_type

            if arg_type == 'bool':
                self.emit.mov("rdi", "rax")
                self.emit.call_rt("rt_bool_to_str")
                self.emit.call_rt("rt_print_string")
            elif arg_type in ('hex', 'ptr', 'pointer', 'address'):
                self.emit.call_rt("rt_print_hex")
            elif arg_type in ('int', 'integer', 'any', 'var'):
                self.emit.call_rt("rt_print_int")
            elif arg_type in ('double', 'float'):
                self.emit.call_rt("rt_print_float")
            elif arg_type == 'char':
                self._emit_print_char()
            else:
                self.emit.call_rt("rt_print_string")
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
                            self.emit.call_rt("rt_print_string")
                    elif chunk[0] == 'PLACEHOLDER':
                        _, expr_str, specifiers = chunk
                        target_ast, shortcuts, pos_idx = self._build_placeholder_ast(expr_str, specifiers, pos_args, pos_idx)

                        self.generate(target_ast)
                        eval_type = getattr(target_ast, 'eval_type', None) or self._get_obj_type(target_ast) or 'int'

                        if 'x' in shortcuts or 'X' in shortcuts or eval_type in ('hex', 'ptr', 'pointer', 'address'):
                            self.emit.call_rt("rt_print_hex")
                        elif 'f' in shortcuts or eval_type in ('double', 'float'):
                            self.emit.call_rt("rt_print_float")
                        elif 'd' in shortcuts or 'i' in shortcuts or eval_type in ('int', 'integer', 'bool', 'any', 'var'):
                            self.emit.call_rt("rt_print_int")
                        elif eval_type == 'char':
                            self._emit_print_char()
                        else:
                            self.emit.call_rt("rt_print_string")
                return
            else:
                for arg in node.arg_nodes:
                    self.generate(arg)
                    eval_type = getattr(arg, 'eval_type', None) or self._get_obj_type(arg) or 'string'

                    if eval_type in ('hex', 'ptr', 'pointer', 'address'):
                        self.emit.call_rt("rt_print_hex")
                    elif eval_type in ('int', 'integer', 'bool'):
                        self.emit.call_rt("rt_print_int")
                    elif eval_type in ('double', 'float'):
                        self.emit.call_rt("rt_print_float")
                    elif eval_type == 'char':
                        self._emit_print_char()
                    else:
                        self.emit.call_rt("rt_print_string")
                return

        elif func_name == 'len':
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_get_len")
            return

        elif func_name == 'realloc':
            self.generate(node.arg_nodes[1])
            self.emit.push("rax")
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.pop("rsi")
            self.emit.call_rt("rt_realloc_mem")
            return

        elif func_name == 'type_of':
            arg_node = node.arg_nodes[0]
            detected_type = getattr(arg_node, 'eval_type', 'unknown')
            from parser import StringNode
            self.visit_StringNode(StringNode(('', f'"{detected_type}"', 0, 0)))
            return

        elif func_name == 'read':
            self.generate(node.arg_nodes[0])
            self.emit.call_rt("rt_read_input")
            return

        elif func_name == 'read_int':
            self.emit.call_rt("rt_read_int")
            return

        elif func_name == 'print_float':
            self.generate(node.arg_nodes[0])
            self.emit.call_rt("rt_print_float")
            return

        elif func_name == 'print_hex':
            self.generate(node.arg_nodes[0])
            self.emit.call_rt("rt_print_hex")
            return

        elif func_name == 'exit':
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_exit_prog")
            return

        elif func_name == 'alloc':
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_alloc")
            return

        elif func_name == 'free':
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_free")
            return

        elif func_name == 'str_ndup':
            self.generate(node.arg_nodes[1])
            self.emit.push("rax")
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.pop("rsi")
            self.emit.call_rt("rt_str_ndup")
            return

        elif func_name == 'sys_argc':
            self.emit.mov("rax", "qword [rel global_argc]")
            return

        elif func_name == 'sys_argv':
            self.generate(node.arg_nodes[0])
            self.emit.mov("rbx", "qword [rel global_argv]")
            self.emit.mov("rax", "qword [rbx + rax*8]")
            return

        elif func_name == 'get_mem':
            self.generate(node.arg_nodes[1])
            self.emit.push("rax")
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.pop("rsi")
            self.emit.call_rt("rt_get_mem")
            return

        elif func_name == 'get_mem32':
            self.generate(node.arg_nodes[1])
            self.emit.push("rax")
            self.generate(node.arg_nodes[0])
            self.emit.mov("rdi", "rax")
            self.emit.pop("rsi")
            self.emit.call_rt("rt_get_mem32")
            return

        elif func_name in ('addr_of', 'ptr_to'):
            self.generate(node.arg_nodes[0])
            return

        elif func_name == 'syscall':
            arg_count = len(node.arg_nodes)
            if arg_count > 7:
                raise Exception("Compiling Error: syscall can take 7 arguments max (rax, rdi, rsi, rdx, r10, r8, r9)")
            arg_registers = ['rax', 'rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9']

            for arg in node.arg_nodes:
                self.generate(arg)
                self.emit.push("rax")

            for i in range(arg_count - 1, -1, -1):
                self.emit.pop(arg_registers[i])

            self.emit.syscall()
            return

        arg_count = len(node.arg_nodes)
        if arg_count > 6:
            for i in range(arg_count - 1, 5, -1):
                self.generate(node.arg_nodes[i])
                self.emit.push("rax")

        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        for i in range(min(6, arg_count)):
            self.generate(node.arg_nodes[i])
            self.emit.push("rax")

        for i in range(min(6, arg_count) - 1, -1, -1):
            self.emit.pop(arg_registers[i])

        loc = self.get_var_loc(func_name)
        is_user_func = (
            (self.semantic_analyzer and hasattr(self.semantic_analyzer, 'functions') and func_name in self.semantic_analyzer.functions)
            or (func_name in self.function_return_types)
        )
        if loc is None and not is_user_func:
            raise Exception(f"Compile Error: Undefined function '{func_name}'")

        if loc is not None:
            self.emit.mov("rax", loc)
            self.emit.call("rax")
        else:
            self.emit.call(f"fn_{func_name}")

        extra_args = max(0, arg_count - 6)
        if extra_args > 0:
            self.emit.add("rsp", extra_args * 8)

    def visit_FuncDefNode(self, node):
        """Creates a new function and configures Scope settings."""
        if node.modifier_tok and node.modifier_tok[1] == 'extern':
            func_name = node.func_name_tok[1]
            self.emit.emit_data(f"; extern fn_{func_name}")
            return

        func_name = node.func_name_tok[1]
        exit_label = f"exit_fn_{func_name}"

        self.emit.use_func_buffer()
        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_label

        self.emit.raw("")
        self.emit.label(f"fn_{func_name}")
        self.emit.push("rbp")
        self.emit.mov("rbp", "rsp")

        is_async = (node.modifier_tok and node.modifier_tok[1] == 'async')
        if is_async:
            self.emit.mov("eax", 57)
            self.emit.syscall()
            self.emit.cmp("rax", 0)
            parent_label = self.get_new_label(f"ASYNC_PARENT_{func_name}")
            self.emit.jcc("ne", parent_label)

        old_stack_offset = self.stack_offset
        self.stack_offset = 0

        self.enter_scope()
        current_env = self.environments[-1]
        type_env = self.type_environments[-1]
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        if node.args:
            self.emit.sub("rsp", len(node.args) * 8)

        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            type_env[arg_name] = arg_type[1]
            if i < 6:
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", arg_registers[i])
            else:
                read_offset = 16 + (i - 6) * 8
                self.emit.mov("rax", f"qword [rbp + {read_offset}]")
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", "rax")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack_offset

        self.emit.label(exit_label)
        if is_async:
            self.emit.mov("rdi", 0)
            self.emit.mov("eax", 60)
            self.emit.syscall()
            self.emit.label(parent_label)

        self.emit.mov("rsp", "rbp")
        self.emit.pop("rbp")
        self.emit.ret()

        self.current_func_exit_label = old_exit_label
        self.emit.use_main_buffer()

    def visit_AnFuncNode(self, node):
        func_lbl = self.get_new_label("ANON_FUNC")
        exit_lbl = f".exit_{func_lbl}"

        self.emit.use_func_buffer()
        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_lbl

        self.emit.raw("")
        self.emit.label(func_lbl)
        self.emit.push("rbp")
        self.emit.mov("rbp", "rsp")

        old_stack = self.stack_offset
        self.stack_offset = 0
        self.enter_scope()
        current_env = self.environments[-1]
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        if node.args:
            self.emit.sub("rsp", len(node.args) * 8)

        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            if i < 6:
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", arg_registers[i])
            else:
                read_offset = 16 + (i - 6) * 8
                self.emit.mov("rax", f"qword [rbp + {read_offset}]")
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", "rax")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack

        self.emit.label(exit_lbl)
        self.emit.mov("rsp", "rbp")
        self.emit.pop("rbp")
        self.emit.ret()

        self.current_func_exit_label = old_exit_label
        self.emit.use_main_buffer()
        self.emit.lea("rax", f"[rel {func_lbl}]")

    def visit_ReturnNode(self, node):
        """Returns a value from the function."""
        if node.node_to_return:
            self.generate(node.node_to_return)

        if self.current_func_exit_label:
            self.emit.jmp(self.current_func_exit_label)
        else:
            self.emit.mov("rsp", "rbp")
            self.emit.pop("rbp")
            self.emit.ret()

    def visit_StringNode(self, node):
        """Writes static string data to .data and loads RIP-relative address into RAX."""
        self.string_count += 1
        label = f"str_{self.string_count}"
        raw_str = node.tok[1][1:-1]

        self.emit.emit_data(f"{label} db `{raw_str}`, 0")
        self.emit.lea("rax", f"[rel {label}]")

    def visit_SyncUnitNode(self, node):
        unit_name = node.unit_name_tok[1]
        exit_lbl = f".exit_unit_{unit_name}"

        self.emit.use_func_buffer()
        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_lbl

        self.emit.raw("")
        self.emit.label(f"unit_{unit_name}")
        self.emit.push("rbp")
        self.emit.mov("rbp", "rsp")

        self.enter_scope()
        self.generate(node.body_node)
        self.exit_scope()

        self.emit.label(exit_lbl)
        self.emit.mov("rsp", "rbp")
        self.emit.pop("rbp")
        self.emit.ret()

        self.current_func_exit_label = old_exit_label
        self.emit.use_main_buffer()

    def visit_WithNode(self, node):
        unit_name = node.unit_name_tok[1]
        if not node.is_wait:
            self.emit.mov("eax", 57)
            self.emit.syscall()
            self.emit.cmp("rax", 0)
            parent_lbl = self.get_new_label("WITH_PARENT")
            self.emit.jcc("ne", parent_lbl)

            self.emit.call(f"unit_{unit_name}")
            self.generate(node.body_node)

            self.emit.mov("eax", 60)
            self.emit.mov("edi", 0)
            self.emit.syscall()

            self.emit.label(parent_lbl)
        else:
            self.emit.call(f"unit_{unit_name}")
            self.generate(node.body_node)

    def visit_KeywordNode(self, node):
        """Converts True, False, and Null to Binary."""
        val = node.tok[1]
        if val == 'true':
            self.emit.mov("eax", 1)
        elif val in ('false', 'null'):
            self.emit.mov("rax", 0)

    def visit_WhenNode(self, node):
        self.emit.mov("eax", 57)
        self.emit.syscall()
        self.emit.cmp("rax", 0)

        parent_lbl = self.get_new_label("WHEN_PARENT")
        self.emit.jcc("ne", parent_lbl)

        loop_lbl = self.get_new_label("WHEN_LOOP")
        self.emit.label(loop_lbl)

        self.emit.sub("rsp", 16)
        self.emit.mov("qword [rsp]", 0)
        self.emit.mov("qword [rsp + 8]", 10000000)
        self.emit.mov("rdi", "rsp")
        self.emit.mov("esi", 0)
        self.emit.mov("eax", 35)
        self.emit.syscall()
        self.emit.add("rsp", 16)

        self.generate(node.condition)
        self.emit.cmp("rax", 0)
        self.emit.jcc("e", loop_lbl)

        self.generate(node.body)

        self.emit.mov("eax", 60)
        self.emit.mov("edi", 0)
        self.emit.syscall()

        self.emit.label(parent_lbl)

    def visit_IndexAccessNode(self, node):
        eval_type = getattr(node, 'eval_type', 'any')

        self.generate(node.index_node)
        self.emit.push("rax")
        self.generate(node.left_node)
        self.emit.pop("rbx")

        bounds_fail = self.get_new_label("BOUNDS_FAIL")
        bounds_ok = self.get_new_label("BOUNDS_OK")

        self.emit.cmp("rbx", 0)
        self.emit.jcc("s", bounds_fail)

        if eval_type != 'char':
            self.emit.mov("rcx", "qword [rax - 8]")
            self.emit.inst("shr", "rcx", 3)
            self.emit.cmp("rbx", "rcx")
            self.emit.jcc("ge", bounds_fail)
        self.emit.jmp(bounds_ok)

        self.emit.label(bounds_fail)
        self._emit_raise_error(99)

        self.emit.label(bounds_ok)
        if eval_type == 'char':
            self.emit.inst("movzx", "rax", "byte [rax + rbx]")
        else:
            self.emit.mov("rax", "qword [rax + rbx*8]")

    def visit_IndexAssignNode(self, node):
        eval_type = getattr(node, 'eval_type', 'any')

        self.generate(node.value_node)
        self.emit.push("rax")
        self.generate(node.index_node)
        self.emit.push("rax")
        self.generate(node.left_node)
        self.emit.pop("rbx")
        self.emit.pop("rcx")

        bounds_fail = self.get_new_label("BOUNDS_FAIL")
        bounds_ok = self.get_new_label("BOUNDS_OK")

        self.emit.cmp("rbx", 0)
        self.emit.jcc("s", bounds_fail)

        if eval_type != 'char':
            self.emit.mov("r8", "qword [rax - 8]")
            self.emit.inst("shr", "r8", 3)
            self.emit.cmp("rbx", "r8")
            self.emit.jcc("ge", bounds_fail)
        self.emit.jmp(bounds_ok)

        self.emit.label(bounds_fail)
        self._emit_raise_error(99)

        self.emit.label(bounds_ok)
        op = node.op_tok[1]

        if eval_type == 'char':
            if op == '=':
                self.emit.mov("byte [rax + rbx]", "cl")
            else:
                raise Exception("Semantik Error: Invalid operation type on chars.")
        else:
            if op == '=':
                self.emit.mov("qword [rax + rbx*8]", "rcx")
            elif op in ('+=', '=+'):
                self.emit.add("qword [rax + rbx*8]", "rcx")
            elif op in ('-=', '=-'):
                self.emit.sub("qword [rax + rbx*8]", "rcx")
            elif op in ('*=', '=*'):
                self.emit.mov("r8", "qword [rax + rbx*8]")
                self.emit.inst("imul", "r8", "rcx")
                self.emit.mov("qword [rax + rbx*8]", "r8")
            elif op in ('/=', '=/'):
                self.emit.mov("r8", "qword [rax + rbx*8]")
                self.emit.push("rax")
                self.emit.push("rbx")
                self.emit.mov("rax", "r8")
                self.emit.mov("rbx", "rcx")
                self.emit.inst("cqo")
                self.emit.inst("idiv", "rbx")
                self.emit.mov("rcx", "rax")
                self.emit.pop("rbx")
                self.emit.pop("rax")
                self.emit.mov("qword [rax + rbx*8]", "rcx")
            elif op in ('%=', '=%'):
                self.emit.mov("r8", "qword [rax + rbx*8]")
                self.emit.push("rax")
                self.emit.push("rbx")
                self.emit.mov("rax", "r8")
                self.emit.mov("rbx", "rcx")
                self.emit.inst("cqo")
                self.emit.inst("idiv", "rbx")
                self.emit.mov("rcx", "rdx")
                self.emit.pop("rbx")
                self.emit.pop("rax")
                self.emit.mov("qword [rax + rbx*8]", "rcx")
            elif op in ('^=', '=^'):
                self.emit.mov("rdi", "qword [rax + rbx*8]")
                self.emit.mov("rsi", "rcx")
                self.emit.push("rax")
                self.emit.push("rbx")
                self.emit.call_rt("rt_int_pow")
                self.emit.mov("rcx", "rax")
                self.emit.pop("rbx")
                self.emit.pop("rax")
                self.emit.mov("qword [rax + rbx*8]", "rcx")

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
            raise Exception("Compiling Error: Unknown Class for Variable")

        field_name = node.member_name_tok[1]
        field_info = self.class_layouts[obj_type]['layout'].get(field_name)
        if not field_info:
            raise Exception(f"Compiling Error: Class '{obj_type}' has no properties specified as: '{field_name}'")

        offset = field_info['offset']
        self.generate(node.value_node)
        self.emit.push("rax")
        self.generate(node.left_node)
        self.emit.pop("rcx")

        op = node.op_tok[1]
        if op == '=':
            self.emit.mov(f"qword [rax + {offset}]", "rcx")
        elif op in ('+=', '=+'):
            self.emit.add(f"qword [rax + {offset}]", "rcx")
        elif op in ('-=', '=-'):
            self.emit.sub(f"qword [rax + {offset}]", "rcx")
        elif op in ('*=', '=*'):
            self.emit.mov("r8", f"qword [rax + {offset}]")
            self.emit.inst("imul", "r8", "rcx")
            self.emit.mov(f"qword [rax + {offset}]", "r8")
        elif op in ('/=', '=/'):
            self.emit.mov("r8", f"qword [rax + {offset}]")
            self.emit.push("rax")
            self.emit.mov("rax", "r8")
            self.emit.mov("rbx", "rcx")
            self.emit.inst("cqo")
            self.emit.inst("idiv", "rbx")
            self.emit.mov("rcx", "rax")
            self.emit.pop("rax")
            self.emit.mov(f"qword [rax + {offset}]", "rcx")
        elif op in ('%=', '=%'):
            self.emit.mov("r8", f"qword [rax + {offset}]")
            self.emit.push("rax")
            self.emit.mov("rax", "r8")
            self.emit.mov("rbx", "rcx")
            self.emit.inst("cqo")
            self.emit.inst("idiv", "rbx")
            self.emit.mov("rcx", "rdx")
            self.emit.pop("rax")
            self.emit.mov(f"qword [rax + {offset}]", "rcx")
        elif op in ('^=', '=^'):
            self.emit.mov("rdi", f"qword [rax + {offset}]")
            self.emit.mov("rsi", "rcx")
            self.emit.push("rax")
            self.emit.call_rt("rt_int_pow")
            self.emit.mov("rcx", "rax")
            self.emit.pop("rax")
            self.emit.mov(f"qword [rax + {offset}]", "rcx")

    def visit_NewObjectNode(self, node):
        """Calculates the class size and calls `alloc()` When encounters the `new Class()` structure."""
        class_name = node.class_name_tok[1]
        if class_name not in self.class_layouts:
            raise Exception(f"Compiling Error: '{class_name}' is not defined.")

        class_size = self.class_layouts[class_name]['size'] or 8
        self.emit.mov("edi", class_size)
        self.emit.call_rt("rt_alloc")
        self.emit.push("rax")

        if self.class_layouts[class_name].get('has_init'):
            init_info = self.class_layouts[class_name]['methods'].get('init')
            declared_class = init_info['declared_in'] if init_info else class_name
            method_name = f"cls_{declared_class}_init"
            arg_count = len(node.arg_nodes) + 1

            if arg_count > 6:
                for i in range(len(node.arg_nodes) - 1, 4, -1):
                    self.generate(node.arg_nodes[i])
                    self.emit.push("rax")

            arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
            for i in range(min(5, len(node.arg_nodes))):
                self.generate(node.arg_nodes[i])
                self.emit.push("rax")

            for i in range(min(5, len(node.arg_nodes)) - 1, -1, -1):
                self.emit.pop(arg_registers[i + 1])

            self.emit.mov("rdi", "qword [rsp]")
            self.emit.call(method_name)

            extra_args = max(0, arg_count - 6)
            if extra_args > 0:
                self.emit.add("rsp", extra_args * 8)

        self.emit.pop("rax")

    def visit_MethodDefNode(self, node):
        """Converts a method written within a class to Assembly."""
        if not self.current_class:
            raise Exception("Compiling Error: Methods can only be defined in a class.")

        func_name = f"cls_{self.current_class}_{node.func_name_tok[1]}"
        exit_label = f"exit_func_{func_name}"

        self.emit.use_func_buffer()
        old_exit_label = self.current_func_exit_label
        self.current_func_exit_label = exit_label

        self.emit.raw("")
        self.emit.label(func_name)
        self.emit.push("rbp")
        self.emit.mov("rbp", "rsp")

        old_stack_offset = self.stack_offset
        self.stack_offset = 0

        self.enter_scope()
        current_env = self.environments[-1]
        type_env = self.type_environments[-1]
        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

        # Single allocation for 'this' + method arguments
        self.emit.sub("rsp", (len(node.args) + 1) * 8)

        self.stack_offset += 8
        current_env['this'] = self.stack_offset
        type_env['this'] = self.current_class
        self.emit.mov(f"qword [rbp - {self.stack_offset}]", "rdi")

        for i, (arg_type, arg_name_tok) in enumerate(node.args):
            arg_name = arg_name_tok[1]
            self.stack_offset += 8
            current_env[arg_name] = self.stack_offset
            type_env[arg_name] = arg_type[1]

            reg_index = i + 1
            if reg_index < 6:
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", arg_registers[reg_index])
            else:
                read_offset = 16 + (reg_index - 6) * 8
                self.emit.mov("rax", f"qword [rbp + {read_offset}]")
                self.emit.mov(f"qword [rbp - {self.stack_offset}]", "rax")

        self.generate(node.body_node)

        self.exit_scope()
        self.stack_offset = old_stack_offset

        self.emit.label(exit_label)
        self.emit.mov("rsp", "rbp")
        self.emit.pop("rbp")
        self.emit.ret()

        self.current_func_exit_label = old_exit_label
        self.emit.use_main_buffer()

    def visit_MethodCallNode(self, node):
        """Translates object.method() calls and passes 'this' in RDI."""
        obj_type = self._get_obj_type(node.left_node)
        if not obj_type or obj_type == 'var':
            raise Exception("Compiling Error: Unknown Class for Variable")

        method_raw_name = node.method_name_tok[1]
        method_info = self.class_layouts[obj_type]['methods'].get(method_raw_name)
        declared_class = method_info['declared_in'] if method_info else obj_type
        method_name = f"cls_{declared_class}_{method_raw_name}"

        arg_count = len(node.arg_nodes) + 1
        if arg_count > 6:
            for i in range(len(node.arg_nodes) - 1, 4, -1):
                self.generate(node.arg_nodes[i])
                self.emit.push("rax")

        arg_registers = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        for i in range(min(5, len(node.arg_nodes))):
            self.generate(node.arg_nodes[i])
            self.emit.push("rax")

        self.generate(node.left_node)
        self.emit.mov("rdi", "rax")

        for i in range(min(5, len(node.arg_nodes)) - 1, -1, -1):
            self.emit.pop(arg_registers[i + 1])

        self.emit.call(method_name)

        extra_args = max(0, arg_count - 6)
        if extra_args > 0:
            self.emit.add("rsp", extra_args * 8)

    def visit_ArrayLiteralNode(self, node):
        """Allocates and populates an array literal."""
        element_count = len(node.elements)
        alloc_size = max((element_count + 1) * 8, 16)

        self.emit.mov("edi", alloc_size)
        self.emit.call_rt("rt_alloc")
        self.emit.push("rax")

        for i, element_node in enumerate(node.elements):
            self.generate(element_node)
            self.emit.mov("rbx", "qword [rsp]")
            self.emit.mov(f"qword [rbx + {i * 8}]", "rax")

        self.emit.mov("rbx", "qword [rsp]")
        self.emit.mov(f"qword [rbx + {element_count * 8}]", 0)
        self.emit.pop("rax")

    def visit_SwitchNode(self, node):
        end_label = self.get_new_label("SWITCH_END")
        default_label = self.get_new_label("DEFAULT")

        self.generate(node.switch_expr)
        self.emit.push("rax")

        case_labels = []
        for i, (case_expr, _) in enumerate(node.cases):
            block_label = self.get_new_label(f"CASE_BLOCK_{i}")
            next_label = self.get_new_label(f"CASE_NEXT_{i}")
            case_labels.append(block_label)

            self.generate(case_expr)
            self.emit.cmp("qword [rsp]", "rax")
            self.emit.jcc("ne", next_label)

            self.emit.add("rsp", 8)
            self.emit.jmp(block_label)
            self.emit.label(next_label)

        self.emit.add("rsp", 8)
        self.emit.jmp(default_label if node.default_case else end_label)

        for i, (_, block) in enumerate(node.cases):
            self.emit.label(case_labels[i])
            self.generate(block)
            self.emit.jmp(end_label)

        if node.default_case:
            self.emit.label(default_label)
            self.generate(node.default_case)

        self.emit.label(end_label)

    def visit_CastNode(self, node):
        """Does Type Casting."""
        self.generate(node.node)
        target_type = node.type_tok[1]
        source_type = getattr(node.node, 'eval_type', 'int')

        if target_type in ('str', 'string'):
            if source_type in ('int', 'integer'):
                self.emit.mov("rdi", "rax")
                self.emit.call_rt("rt_int_to_str")
            elif source_type in ('bool', 'boolean'):
                self.emit.mov("rdi", "rax")
                self.emit.call_rt("rt_bool_to_str")
            elif source_type == 'char':
                self.emit.mov("rdi", "rax")
                self.emit.call_rt("rt_char_to_str")

        elif target_type == 'bool':
            if source_type == 'double':
                self.emit.inst("movq", "xmm0", "rax")
                self.emit.inst("pxor", "xmm1", "xmm1")
                self.emit.inst("ucomisd", "xmm0", "xmm1")
                self.emit.inst("setne", "al")
                self.emit.inst("movzx", "rax", "al")
            elif source_type in ('str', 'string'):
                self.emit.cmp("byte [rax]", 0)
                self.emit.inst("setne", "al")
                self.emit.inst("movzx", "rax", "al")
            elif source_type == 'null':
                self.emit.mov("rax", 0)
            else:
                self.emit.cmp("rax", 0)
                self.emit.inst("setne", "al")
                self.emit.inst("movzx", "rax", "al")

        elif target_type in ('int', 'integer') and source_type in ('str', 'string'):
            self.emit.mov("rdi", "rax")
            self.emit.call_rt("rt_str_to_int")

        elif target_type == 'double' and source_type in ('int', 'integer', 'any', 'var'):
            self.emit.inst("cvtsi2sd", "xmm0", "rax")
            self.emit.inst("movq", "rax", "xmm0")

        elif target_type in ('int', 'integer') and source_type == 'double':
            self.emit.inst("movq", "xmm0", "rax")
            self.emit.inst("cvttsd2si", "rax", "xmm0")

        elif target_type == 'char' and source_type in ('str', 'string', 'any'):
            self.emit.inst("movzx", "rax", "byte [rax]")
                    
    def visit_DeleteNode(self, node):
        self.generate(node.target_node)
        self.emit.mov("rdi", "rax")
        self.emit.call_rt("rt_free")

    def visit_AllegeNode(self, node):
        self.generate(node.condition)
        ok_lbl = self.get_new_label("ALLEGE_OK")
        self.emit.cmp("rax", 0)
        self.emit.jcc("ne", ok_lbl)
        self._emit_raise_error(1)
        self.emit.label(ok_lbl)

    def visit_LimitsNode(self, node):
        self.generate(node.start_node)
        self.emit.push("rax")

        self.generate(node.end_node)
        self.emit.mov("rbx", "rax")
        self.emit.pop("rax")
        self.emit.mov("rcx", "rbx")
        self.emit.sub("rcx", "rax")

        ok_lbl = self.get_new_label("LIMITS_OK")
        self.emit.cmp("rcx", 0)
        self.emit.jcc("g", ok_lbl)
        self.emit.mov("ecx", 1)
        self.emit.label(ok_lbl)

        self.emit.push("rax")
        self.emit.push("rcx")

        self.emit.mov("rdi", "rcx")
        self.emit.inst("shl", "rdi", 3)
        self.emit.call_rt("rt_alloc")
        self.emit.mov("r8", "rax")

        self.emit.pop("rcx")
        self.emit.pop("rax")

        self.emit.mov("r9", 0)
        loop_start = self.get_new_label("LIMITS_LOOP")
        loop_end = self.get_new_label("LIMITS_END")

        self.emit.label(loop_start)
        self.emit.cmp("r9", "rcx")
        self.emit.jcc("ge", loop_end)

        self.emit.mov("qword [r8 + r9*8]", "rax")
        self.emit.add("rax", 1)
        self.emit.add("r9", 1)
        self.emit.jmp(loop_start)

        self.emit.label(loop_end)
        self.emit.mov("rax", "r8")

    def visit_BreakNode(self, node):
        if not self.loop_stack:
            raise Exception("Semantic Error: 'break' can only be used in a loop.")
        _, end_label = self.loop_stack[-1]
        self.emit.jmp(end_label)

    def visit_GoonNode(self, node):
        if not self.loop_stack:
            raise Exception("Semantic Error: 'goon' can only be used in a loop.")
        continue_label, _ = self.loop_stack[-1]
        self.emit.jmp(continue_label)

if __name__ == '__main__':
    from lexer import tokenize
    from parser import Parser
    from semantic import SemanticAnalyzer

    test_code = """
    print("Hello World!");
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