class SemanticAnalyzer:
    def __init__(self, strict_mode=True):
        self.environments = [{}]
        self.current_class = None
        self.current_return_type = None
        self.strict_mode = strict_mode
        self.class_hierarchy = {}
        self.functions = {}
        self.methods = {}
        self.fields = {}

    BUILTIN_FUNCTION_TYPES = {
        'print': 'unit',
        'printf': 'unit',
        'print_float': 'unit',
        'print_hex': 'unit',
        'free': 'unit',
        'exit': 'unit',

        'len': 'int',
        'read_int': 'int',
        'sys_argc': 'int',
        'get_mem': 'int',
        'get_mem32': 'int',
        'syscall': 'int',

        'read': 'string',
        'type_of': 'string',
        'sys_argv': 'string',

        'alloc': 'ptr',
        'realloc': 'ptr',
        'addr_of': 'ptr',
        'ptr_to': 'ptr'
    }


    def analyze(self, ast):
        for node in ast:
            if type(node).__name__ == 'ClassDefNode':
                class_name = node.class_name_tok[1]
                parent_name = node.parent_class_tok[1] if node.parent_class_tok else None
                self.class_hierarchy[class_name] = parent_name
                self.methods[class_name] = {}
                self.fields[class_name] = {}

                for method in node.methods:
                    m_name = method.func_name_tok[1]
                    ret_type = method.return_type_tok[1] if method.return_type_tok else 'unit'
                    self.methods[class_name][m_name] = ret_type

                for modifier_tok, type_tok, name_tok in node.fields:
                    f_name = name_tok[1]
                    f_type = type_tok[1] if type_tok else 'var'
                    self.fields[class_name][f_name] = f_type

            elif type(node).__name__ == 'FuncDefNode':
                f_name = node.func_name_tok[1]
                ret_type = node.return_type_tok[1] if node.return_type_tok else 'unit'
                self.functions[f_name] = ret_type

        for node in ast:
            self.visit(node)

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        if self.strict_mode:
            raise Exception(f"Semantik Hata (Strict Mode): '{type(node).__name__}' için semantik analiz (visit) kuralı tanımlanmamış. "
                f"Lütfen SemanticAnalyzer içine 'visit_{type(node).__name__}' metodunu ekleyin.")

    def check_type_compatibility(self, target_type, value_type, var_name=""):
        """Check the compability between target type and the assigned value."""
        if not self.strict_mode:
            return True

        if value_type == 'unit':
            raise Exception(f"Semantic Error: Cannot assign a 'unit' to '{var_name}', a value must be returned.")

        if target_type == value_type:
            return True
        elif target_type == 'double' and value_type == 'int':
            return True
        elif value_type == 'any' or target_type == 'any':
            return True
        elif self.is_subclass(value_type, target_type):
            return True
        elif target_type in ('hex', 'ptr', 'pointer', 'address', 'int') and value_type in ('hex', 'int'):
            return True
        else:
            raise Exception(f"Semantic Error: Variable '{var_name}' is '{target_type}', '{value_type}' is assigned.")

    def check_boolean_condition(self, cond_node, context_name="condition"):
        """Checks if the condition is transformable into a logical value."""
        cond_type = self.visit(cond_node)
        if self.strict_mode and cond_type in ('unit', 'void'):
            raise Exception(f"Semantik Error: '{context_name}' cannot be '{cond_type}'.")
        return cond_type

    def check_index_type(self, index_node, context="array index"):
        """Verifies the Index state is 'int' or 'hex'."""
        idx_type = self.visit(index_node)
        if self.strict_mode and idx_type not in ('int', 'hex', 'any'):
            raise Exception(f"Semantik Error: '{context}' should be 'int' or 'hex', given '{idx_type}'")
        return idx_type

    def get_field_type(self, class_name, field_name):
        """Finds the field type, scanning the class hierarchy upwards."""
        curr = class_name
        while curr:
            if curr in self.fields and field_name in self.fields[curr]:
                return self.fields[curr][field_name]
        return None

    # ----- VISITOR FUNCTIONS -----

    def visit_BlockNode(self ,node):
        for statement in node.statements:
            self.visit(statement)
        node.eval_type = 'unit'
        return 'unit'

    def visit_IfNode(self, node):
        for condition, block in node.cases:
            self.check_boolean_condition(condition, "if condition")
            self.environments.append({})
            self.visit(block)
            self.environments.pop()

        if node.else_case:
            self.environments.append({})
            self.visit(node.else_case)
            self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_WhileNode(self, node):
        self.check_boolean_condition(node.condition_node, "while condition")
        self.environments.append({})
        self.visit(node.body_node)
        self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_ForNode(self, node):
        iter_type = self.visit(node.iter_node)
        iter_node_class = type(node.iter_node).__name__

        elem_type = 'any'

        if iter_node_class == 'LimitsNode':
            elem_type = 'int'
        elif iter_type in ('string', 'str'):
            elem_type = 'char'
        elif iter_node_class == 'ArrayLiteralNode':
            if node.iter_node.elements:
                elem_types = [self.visit(elem) for elem in node.iter_node.elements]
                first_type = elem_types[0]
                if all(t == first_type for t in elem_types):
                    elem_type = first_type
                else:
                    elem_type = 'any'
        elif iter_type.endswith('[]'):
            elem_type = iter_type[:-2]

        self.environments.append({})
        var_name = node.var_name_tok[1]
        self.environments[-1][var_name] = elem_type

        self.visit(node.body)

        self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_AttemptNode(self, node):
        self.environments.append({})
        self.visit(node.attempt_body)
        self.environments.pop()

        if node.exclude_body:
            self.environments.append({})
            self.environments[-1]['err'] = 'int'
            self.visit(node.exclude_body)
            self.environments.pop()

        if node.final_body:
            self.environments.append({})
            self.visit(node.final_body)
            self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_TriggerNode(self, node):
        self.visit(node.err_value_node)
        node.eval_type = 'unit'
        return 'unit'

    def visit_ReturnNode(self, node):
        if node.node_to_return:
            return_val_type = self.visit(node.node_to_return)
        else:
            return_val_type = 'unit'

        if self.current_return_type is not None:
            self.check_type_compatibility(self.current_return_type, return_val_type, "return value")

        node.eval_type = return_val_type
        return return_val_type
        
    def visit_AnFuncNode(self, node):
        old_ret_type = self.current_return_type
        self.current_return_type = 'any'

        self.environments.append({})

        for arg_type_tok, arg_name_tok in node.args:
            arg_type = arg_type_tok[1]
            arg_name = arg_name_tok[1]
            self.environments[-1][arg_name] = arg_type

        self.visit(node.body_node)
        self.environments.pop()

        self.current_return_type = old_ret_type
        node.eval_type = 'any'
        return 'any'

    def visit_BreakNode(self,node):
        return 'any'

    def visit_GoonNode(self,node):
        return 'any'

    def visit_ReAssignNode(self, node):
        var_name = node.var_name_tok[1]

        current_type = None
        for env in reversed(self.environments):
            if var_name in env:
                current_type = env[var_name]
                break

        if current_type is None:
            raise Exception(f"Semantic Error: '{var_name}' is undefined.")

        value_type = self.visit(node.value_node)

        self.check_type_compatibility(current_type, value_type, var_name)

        node.eval_type = current_type
        return current_type
        
    def visit_DeleteNode(self, node):
        self.visit(node.target_node)
        node.eval_type = 'unit'
        return 'unit'

    def visit_FuncDefNode(self, node):
        if node.modifier_tok and node.modifier_tok[1] == 'extern':
            return

        old_ret_type = self.current_return_type
        self.current_return_type = node.return_type_tok[1] if node.return_type_tok else 'unit'

        self.environments.append({})

        for arg_type_tok, arg_name_tok in node.args:
            arg_type = arg_type_tok[1]
            arg_name = arg_name_tok[1]
            self.environments[-1][arg_name] = arg_type

        self.visit(node.body_node)
        self.environments.pop()

        self.current_return_type = old_ret_type
        node.eval_type = 'unit'
        return 'unit'

    def visit_MethodDefNode(self, node):
        old_ret_type = self.current_return_type
        self.current_return_type = node.return_type_tok[1] if node.return_type_tok else 'unit'

        self.environments.append({})

        self.environments[-1]['this'] = self.current_class

        for arg_type_tok, arg_name_tok in node.args:
            arg_type = arg_type_tok[1]
            arg_name = arg_name_tok[1]
            self.environments[-1][arg_name] = arg_type
            
        self.visit(node.body_node)
        self.environments.pop()

        self.current_return_type = old_ret_type
        node.eval_type = 'unit'
        return 'unit'

    def visit_FuncCallNode(self, node):
        """Analyze the parameters and return types in a function."""
        for arg in node.arg_nodes:
            self.visit(arg)

        func_name = node.node_to_call.var_name_tok[1]

        if func_name in self.BUILTIN_FUNCTION_TYPES:
            ret_type = self.BUILTIN_FUNCTION_TYPES[func_name]
        elif func_name in self.functions:
            ret_type = self.functions[func_name]
        else:
            if self.strict_mode:
                raise Exception(f"Semantic Error: '{func_name}' is not defined.")
            ret_type = 'any'
        node.eval_type = ret_type
        return ret_type
    
    def visit_MethodCallNode(self, node):
        """Analyze the parameters in object.method() call."""
        obj_type = self.visit(node.left_node)
        for arg in node.arg_nodes:
            self.visit(arg)

        m_name = node.method_name_tok[1]
        ret_type = 'any'
        if obj_type in self.methods and m_name in self.methods[obj_type]:
            ret_type = self.methods[obj_type][m_name]
        
        node.eval_type = ret_type
        return ret_type

    def visit_MemberAccessNode(self, node):
        """Analyze object.feature reading."""
        obj_type = self.visit(node.left_node)
        m_name = node.member_name_tok[1]

        ret_type = 'any'
        if obj_type in self.fields and m_name in self.fields[obj_type]:
            ret_type = self.fields[obj_type][m_name]
        node.eval_type = ret_type
        return ret_type

    def visit_MemberAssignNode(self, node):
        """Analyze the assignment: object.method = value."""
        obj_type = self.visit(node.left_node)
        m_name = node.member_name_tok[1]

        field_type = self.get_field_type(obj_type, m_name)

        if field_type is None and obj_type != 'any':
            if self.strict_mode:
                raise Exception(f"Semantic Error: No such field as '{m_name}' in class: '{obj_type}'")
            field_type = 'any'

        value_type = self.visit(node.value_node)

        target_type = field_type if field_type else 'any'

        self.check_type_compatibility(target_type, value_type, f"{obj_type}.{m_name}")

        node.eval_type = target_type
        return target_type
        
    def visit_NumberNode(self, node):
        if node.tok[0] == 'FLOAT':
            node.eval_type = 'double'
        elif node.tok[0] == 'HEX':
            node.eval_type = 'hex'
        else:
            node.eval_type = 'int'
        return node.eval_type

    def visit_StringNode(self, node):
        node.eval_type = 'string'
        return 'string'

    def visit_KeywordNode(self, node):
        if node.tok[1] in ('true', 'false'):
            node.eval_type = 'bool'
        elif node.tok[1] == 'null':
            node.eval_type = 'null'
        return node.eval_type

    def visit_VarAssignNode(self, node):
        value_type = self.visit(node.value_node)
        var_name = node.var_name_tok[1]
        
        declared_type = node.type_tok[1] if node.type_tok else value_type

        if declared_type == 'var':
            declared_type = value_type


        self.check_type_compatibility(declared_type, value_type, var_name)

        self.environments[-1][var_name] = declared_type
        
        node.eval_type = declared_type
        return declared_type

    def visit_VarAccessNode(self, node):
        var_name = node.var_name_tok[1]
        for env in reversed(self.environments):
            if var_name in env:
                node.eval_type = env[var_name]
                return env[var_name]
        raise Exception(f"Semantik Hata: '{var_name}' tanimsiz.")

    def visit_BinOpNode(self, node):
        left_type = self.visit(node.left_node)
        right_type = self.visit(node.right_node)

        op_type = 'int'
        if left_type == 'double' or right_type == 'double':
            op_type = 'double'
        elif left_type in ('string', 'str') or right_type in ('string', 'str'):
            op_type = 'string'

        node.operand_type = op_type

        op = node.op_tok[1]
        if op in ('=?', '?=', '!=', '=!', '>', '<', '>=', '=>', '<=', '=<', 'is', 'same'):
            node.eval_type = 'bool'
        else:
            node.eval_type = op_type

        return node.eval_type

    def visit_UnaryOpNode(self, node):
        val_type = self.visit(node.node)
        op = node.op_tok[1]
        if op == 'not':
            node.eval_type = 'bool'
        else:
            node.eval_type = val_type
        return node.eval_type

    def visit_CastNode(self, node):
        self.visit(node.node)
        target_type = node.type_tok[1]
        node.eval_type = target_type
        return target_type
    
    def visit_ClassDefNode(self, node):
        class_name = node.class_name_tok[1]
        self.current_class = class_name
        for method in node.methods:
            self.visit(method)
        self.current_class = None

        node.eval_type = 'unit'
        return 'unit'
    
    def visit_NewObjectNode(self, node):
        class_name = node.class_name_tok[1]

        if class_name not in self.class_hierarchy:
            raise Exception(f"Semantic Error: class '{class_name}' is not found.")
        
        node.eval_type = class_name
        return class_name

    def visit_IndexAccessNode(self, node):
        left_type = self.visit(node.left_node)
        self.check_index_type(node.index_node, 'read index')
        
        if left_type in ('string', 'str'):
            elem_type = 'char'
        elif left_type.endswith('[]'):
            elem_type = left_type[:-2]
        else:
            elem_type = 'any'

        node.eval_type = elem_type
        return elem_type
    
    def visit_IndexAssignNode(self, node):
        left_type = self.visit(node.left_node)
        self.check_index_type(node.index_node, "assign index")
        value_type = self.visit(node.value_node)
        
        if left_type in ('string', 'str'):
            elem_type = 'char'
        elif left_type.endswith('[]'):
            elem_type = left_type[:-2]
        else:
            elem_type = 'any'

        node.eval_type = elem_type
        return elem_type

    def visit_ArrayLiteralNode(self, node):
        if not node.elements:
            node.eval_type = 'array'
            return 'array'

        elem_types = [self.visit(elem) for elem in node.elements]
        first_type = elem_types[0]

        if all(t == first_type for t in elem_types) and first_type != 'any':
            arr_type = f"{first_type}[]"
        else:
            arr_type = 'array'

        node.eval_type = arr_type
        return arr_type

    def visit_LimitsNode(self, node):
        start_type = self.visit(node.start_node)
        end_type = self.visit(node.end_node)

        if self.strict_mode:
            if start_type not in ('int', 'hex', 'any') or end_type not in ('int', 'hex', 'any'):
                raise Exception(f"Semantik Error: start and end parameters for 'limits' should be 'int'.")
        node.eval_type = 'int[]'
        return 'int[]'

    def visit_SwitchNode(self, node):
        switch_type = self.visit(node.switch_expr)

        for case_expr, block in node.cases:
            case_type = self.visit(case_expr)
            self.check_type_compatibility(switch_type, case_type, "switch case")

            self.environments.append({})
            self.visit(block)
            self.environments.pop()

        if node.default_case:
            self.environments.append({})
            self.visit(node.default_case)
            self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_AllegeNode(self, node):
        self.visit(node.condition)
        node.eval_type = 'unit'
        return 'unit'

    def visit_SyncUnitNode(self, node):
        self.environments.append({})
        self.visit(node.body_node)
        self.environments.pop()
        node.eval_type = 'unit'
        return 'unit'

    def visit_WithNode(self, node):
        self.environments.append({})
        self.visit(node.body_node)
        self.environments.pop()
        node.eval_type = 'unit'
        return 'unit'

    def visit_WhenNode(self, node):
        self.check_boolean_condition(node.condition, "when condition")
        self.environments.append({})
        self.visit(node.body)
        self.environments.pop()

        node.eval_type = 'unit'
        return 'unit'

    def visit_IncludeNode(self, node):
        node.eval_type = 'unit'
        return 'unit'

    def visit_LinkNode(self, node):
        node.eval_type = 'unit'
        return 'unit'

    def is_subclass(self, child, parent):
        if child == parent:
            return True
        curr = self.class_hierarchy.get(child)
        while curr:
            if curr == parent:
                return True
            curr = self.class_hierarchy.get(curr)
        return False