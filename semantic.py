class SemanticAnalyzer:
    def __init__(self, strict_mode=True):
        self.environments = [{}]
        self.current_class = None
        self.strict_mode = strict_mode
        self.class_hierarchy = {}
    
    def analyze(self, ast):
        for node in ast:
            if type(node).__name__ == 'ClassDefNode':
                class_name = node.class_name_tok[1]
                parent_name = node.parent_class_tok[1] if node.parent_class_tok else None
                self.class_hierarchy[class_name] = parent_name

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

    def visit_BlockNode(self ,node):
        for statement in node.statements:
            self.visit(statement)

    def visit_IfNode(self, node):
        for condition, block in node.cases:
            self.visit(condition)
            self.environments.append({})
            self.visit(block)
            self.environments.pop()

        if node.else_case:
            self.environments.append({})
            self.visit(node.else_case)
            self.environments.pop()

    def visit_WhileNode(self, node):
        self.visit(node.condition_node)
        self.environments.append({})
        self.visit(node.body_node)
        self.environments.pop()

    def visit_ForNode(self, node):
        self.visit(node.iter_node)

        self.environments.append({})
        var_name = node.var_name_tok[1]

        self.environments[-1][var_name] = 'any'

        self.visit(node.body)

        self.environments.pop()

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

    def visit_TriggerNode(self, node):
        self.visit(node.err_value_node)
        node.eval_type = 'any'
        return 'any'

    def visit_ReturnNode(self, node):
        if node.node_to_return:
            self.visit(node.node_to_return)
            node.eval_type = getattr(node.node_to_return, 'eval_type', 'any')
        return 'any'

    def visit_ReAssignNode(self, node):
        self.visit(node.value_node)
        return 'any'

    def visit_DeleteNode(self, node):
        self.visit(node.target_node)
        return 'any'

    def visit_FuncDefNode(self, node):
        if node.modifier_tok and node.modifier_tok[1] == 'extern':
            return

        self.environments.append({})

        for arg_type_tok, arg_name_tok in node.args:
            arg_type = arg_type_tok[1]
            arg_name = arg_name_tok[1]
            self.environments[-1][arg_name] = arg_type

        self.visit(node.body_node)
        self.environments.pop()

    def visit_MethodDefNode(self, node):
        self.environments.append({})

        self.environments[-1]['this'] = self.current_class

        for arg_type_tok, arg_name_tok in node.args:
            arg_type = arg_type_tok[1]
            arg_name = arg_name_tok[1]
            self.environments[-1][arg_name] = arg_type
            
        self.visit(node.body_node)
        self.environments.pop()

    def visit_FuncCallNode(self, node):
        """Fonksiyon çağrısındaki parametreleri analiz et."""
        for arg in node.arg_nodes:
            self.visit(arg)
        node.eval_type = 'any' # Şimdilik dönüş tipini bilmiyoruz
        return 'any'
    
    def visit_MethodCallNode(self, node):
        """nesne.metot() çağrısındaki parametreleri analiz et."""
        self.visit(node.left_node)
        for arg in node.arg_nodes:
            self.visit(arg)
        node.eval_type = 'any'
        return 'any'

    def visit_MemberAccessNode(self, node):
        """nesne.ozellik (Örn: donusen_oyuncu.seviye) okumasını analiz et."""
        self.visit(node.left_node)
        node.eval_type = 'any' # İleride class_layouts içinden asıl tip bulunabilir
        return 'any'

    def visit_MemberAssignNode(self, node):
        """nesne.ozellik = deger atamasını analiz et."""
        self.visit(node.left_node)
        self.visit(node.value_node)
        node.eval_type = 'any'
        return 'any'

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


        if self.strict_mode and declared_type != value_type:
            if declared_type == 'double' and value_type == 'int':
                pass
            elif value_type == 'any' or declared_type == 'any': 
                pass
            elif self.is_subclass(value_type, declared_type):
                pass
            elif declared_type in ('hex', 'ptr', 'pointer', 'address', 'int') and value_type in ('hex', 'int'):
                pass
            else:
                raise Exception(f"Semantik Hata: '{var_name}' degiskeni '{declared_type}' tipinde ama '{value_type}' ataniyor.")

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
        return class_name
    
    def visit_NewObjectNode(self, node):
        class_name = node.class_name_tok[1]

        if class_name not in self.class_hierarchy:
            raise Exception(f"Semantik Hata: '{class_name}' adinda bir sinif bulunamadi.")
        
        node.eval_type = class_name
        return class_name

    def visit_IndexAccessNode(self, node):
        left_type = self.visit(node.left_node)
        self.visit(node.index_node)
        
        if left_type in ('string', 'str'):
            node.eval_type = 'char'
        else:
            node.eval_type = 'any'
        return node.eval_type
    
    def visit_IndexAssignNode(self, node):
        left_type = self.visit(node.left_node)
        self.visit(node.index_node)
        value_type = self.visit(node.value_node)
        
        if left_type in ('string', 'str'):
            node.eval_type = 'char'
        else:
            node.eval_type = 'any'
        return node.eval_type

    def is_subclass(self, child, parent):
        if child == parent:
            return True
        curr = self.class_hierarchy.get(child)
        while curr:
            if curr == parent:
                return True
            curr = self.class_hierarchy.get(curr)
        return False