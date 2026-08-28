class NumberNode:
    """Number Nodes."""
    def __init__(self, tok):
        self.tok = tok #Lexer token

    def __repr__(self):
        return f'{self.tok[1]}'
    

class VarAccessNode:
    """Variable Access Node."""
    def __init__(self, var_name_tok):
        self.var_name_tok = var_name_tok

    def __repr__(self):
        return f'{self.var_name_tok[1]}'


class KeywordNode:
    """Keyword Node."""
    def __init__(self, tok):
        self.tok = tok

    def __repr__(self):
        return f'{self.tok[1]}'


class IfNode:
    """If Node, containing 'if', 'butif' and 'else' cases."""
    def __init__(self, cases, else_case):
        self.cases = cases
        self.else_case = else_case

    def __repr__(self):
        res = f"IF ({self.cases[0][0]}):\n    {self.cases[0][1]}"
        for cond, block in self.cases[1:]:
            res += f"\n BUTIF ({cond}):\n {block}"
        if self.else_case:
            res += f"\n ELSE (else):\n   {self.else_case}"
        return res


class UnaryOpNode:
    """Single Operation Node."""
    def __init__(self, op_tok, node):
        self.op_tok = op_tok
        self.node = node
    
    def __repr__(self):
        return f"({self.op_tok[1]} {self.node})"
        

class WhileNode:
    """While Node."""
    def __init__(self, condition, body):
        self.condition_node = condition
        self.body_node = body
    
    def __repr__(self):
        return f"WHILE ({self.condition_node}):\n   {self.body_node}"
    

class LimitsNode:
    """Limits Node, returns Range Array."""
    def __init__(self, start_node, end_node):
        self.start_node = start_node
        self.end_node = end_node

    def __repr__(self):
        return f"LIMITS_ARRAY({self.start_node} -> {self.end_node})"


class ForNode:
    """For Node."""
    def __init__(self, var_name_tok, iter_node, body):
        self.var_name_tok = var_name_tok
        self.iter_node = iter_node
        self.body = body

    def __repr__(self):
        return f"FOR ({self.var_name_tok[1]} IN {self.iter_node}):\n  {self.body}"


class WhenNode:
    """When Node."""
    def __init__(self, condition, body, isglobal=False):
        self.condition = condition
        self.body = body
        self.isglobal = isglobal

    def __repr__(self):
        g_str = "GLOBAL " if self.isglobal else ""
        return f"{g_str}WHEN ({self.condition}):\n  {self.body}"


class VarAssignNode:
    """Variable Assign Node."""
    def __init__(self,modifier_tok, type_tok, var_name_tok, value_node):
        self.modifier_tok = modifier_tok
        self.type_tok = type_tok
        self.var_name_tok = var_name_tok
        self.value_node = value_node

    def __repr__(self):
        mod_str = f"{self.modifier_tok[1]} " if self.modifier_tok else ""
        return f"(ASSIGN: {mod_str}{self.type_tok[1]} {self.var_name_tok[1]} = {self.value_node})"
    

class BinOpNode:
    """Binary Operation Node."""
    def __init__(self, left_node, op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node

    def __repr__(self):
        return f'({self.left_node} {self.op_tok[1]} {self.right_node})'
    

class BlockNode:
    """Code Block Node. """
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        stmts_str = '\n  '.join([str(stmt) for stmt in self.statements])
        return f"{{\n   {stmts_str}\n}}"
        
    
class FuncCallNode:
    """Function Call Node."""
    def __init__(self, node_to_call, arg_nodes):
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes

    def __repr__(self):
        args_str = ', '.join([str(arg) for arg in self.arg_nodes])
        return f"CALL {self.node_to_call}({args_str})"


class FuncDefNode:
    """Function Define Node."""
    def __init__(self, modifier_tok, func_name_tok, args, body_node, return_type_tok=None):
        self.modifier_tok = modifier_tok
        self.func_name_tok = func_name_tok
        self.args = args
        self.body_node = body_node
        self.return_type_tok = return_type_tok

    def __repr__(self):
        mod_str = f"{self.modifier_tok[1].upper()} " if self.modifier_tok else ""
        args_str = ', '.join([f"{t[1]} {n[1]}" for t, n in self.args])
        ret_str = f" -> {self.return_type_tok[1]}" if self.return_type_tok else ""
        return f"{mod_str}DEFINE_FUNCTION {self.func_name_tok[1]}({args_str}){ret_str}:\n  {self.body_node}"


class ClassDefNode:
    """Class Define Node."""
    def __init__(self, class_name_tok, body_node):
        self.class_name_tok = class_name_tok
        self.body_node = body_node

    def __repr__(self):
        return f"DEFINE_CLASS {self.class_name_tok[1]}:\n {self.body_node}"
        

class ReAssignNode:
    """Reassign Node."""
    def __init__(self, var_name_tok, op_tok, value_node):
        self.var_name_tok = var_name_tok
        self.op_tok = op_tok
        self.value_node = value_node

    def __repr__(self):
        return f"(REASSIGN: {self.var_name_tok[1]} {self.op_tok[1]} {self.value_node})"


class TriggerNode:
    """Trigger Node."""
    def __init__(self, err_value_node):
        self.err_value_node = err_value_node

    def __repr__(self):
        return f"TRIGGER_ERROR({self.err_value_node})"


class AttemptNode:
    """Error Handling Node, containing 'attempt', 'exclude' and 'final' cases. """
    def __init__(self, attempt_body, exclude_body, final_body):
        self.attempt_body = attempt_body
        self.exclude_body = exclude_body
        self.final_body = final_body

    def __repr__(self):
        res = f"ATTEMPT :\n {self.attempt_body}"
        if self.exclude_body:
            res += f"\n EXCLUDE :\n {self.exclude_body}"
        if self.final_body:
            res += f"\n FINAL :\n {self.final_body}"
        return res


class AllegeNode:
    """Allege Node."""
    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"ALLEGE : {self.condition}"


class SyncUnitNode:
    """Unit Node."""
    def __init__(self, unit_name_tok, body_node):
        self.unit_name_tok = unit_name_tok
        self.body_node = body_node

    def __repr__(self):
        return f"SYNC_UNIT {self.unit_name_tok[1]}:\n {self.body_node}"


class WithNode:
    """With Node."""
    def __init__(self, unit_name_tok, body_node, is_wait=False):
        self.unit_name_tok = unit_name_tok
        self.body_node = body_node
        self.is_wait = is_wait

    def __repr__(self):
        wait_str = "WAIT " if self.is_wait else ""
        return f"{wait_str}WITH ({self.unit_name_tok[1]}):\n  {self.body_node}"


class ReturnNode:
    """Return Node."""
    def __init__(self, node_to_return):
        self.node_to_return = node_to_return

    def __repr__(self):
        return f"RETURN -> {self.node_to_return}"


class BreakNode:
    """Break Node."""
    def __repr__(self):
        return "BREAK"
    

class GoonNode:
    """Go On Node."""
    def __repr__(self):
        return "GOON"


class CastNode:
    """Type Casting Node."""
    def __init__(self, node, type_tok):
        self.node = node
        self.type_tok = type_tok

    def __repr__(self): 
        return f"TRANSFORM ({self.node} -> {self.type_tok[1]})"
        

class DeleteNode:
    """Delete Node."""
    def __init__(self, target_node):
        self.target_node = target_node

    def __repr__(self):
        return f"DELETE {self.target_node}"


class LinkNode:
    """Link Node."""
    def __init__(self, target_str_tok):
        self.target_str_tok = target_str_tok

    def __repr__(self):
        return f"LINK: {self.target_str_tok[1]}"


class IncludeNode:
    """Include Node."""
    def __init__(self, module_tok, item_tok=None, alias_tok=None):
        self.module_tok = module_tok
        self.item_tok = item_tok
        self.alias_tok = alias_tok

    def __repr__(self):
        alias_str = f"AS {self.alias_tok[1]}" if self.alias_tok else ""
        if self.item_tok:
            return f"FROM {self.module_tok[1]} INCLUDE {self.item_tok[1]}{alias_str}"
        return f"INCLUDE {self.module_tok[1]}{alias_str}"


class AnFuncNode:
    """Anonymous Function Node."""
    def __init__(self, args, body_node):
        self.args = args
        self.body_node = body_node

    def __repr__(self):
        args_str = ', '.join([f"{t[1]} {n[1]}" for t, n in self.args])
        return f"ANFUNC ({args_str}):\n  {self.body_node}"


class StringNode:
    """String Node."""
    def __init__(self, tok):
        self.tok = tok

    def __repr__(self):
        return f"STRING({self.tok[1]})"        


class IndexAccessNode:
    """Index Access Node."""
    def __init__(self, left_node, index_node):
        self.left_node = left_node
        self.index_node = index_node


class IndexAssignNode:
    """Index Assign Node."""
    def __init__(self, left_node, index_node, op_tok, value_node):
        self.left_node = left_node
        self.index_node = index_node
        self.op_tok = op_tok
        self.value_node = value_node


class ClassDefNode:
    """Class Define Node."""
    def __init__(self, class_name_tok,parent_class_tok, fields, methods):
        self.class_name_tok =class_name_tok
        self.parent_class_tok = parent_class_tok
        self.fields = fields
        self.methods = methods


class MemberAccessNode:
    """Member Access Node."""
    def __init__(self, left_node, member_name_tok):
        self.left_node = left_node
        self.member_name_tok = member_name_tok


class MemberAssignNode:
    """Member Assign Node."""
    def __init__(self, left_node, member_name_tok, op_tok, value_node):
        self.left_node = left_node
        self.member_name_tok = member_name_tok
        self.op_tok = op_tok
        self.value_node = value_node


class NewObjectNode:
    """New Object Node."""
    def __init__(self, class_name_tok, arg_nodes):
        self.class_name_tok = class_name_tok
        self.arg_nodes = arg_nodes


class MethodDefNode:
    """Method Define Node."""
    def __init__(self, modifier_tok, func_name_tok, args, body_node, return_type_tok=None):
        self.modifier_tok = modifier_tok
        self.func_name_tok = func_name_tok    
        self.args = args
        self.body_node = body_node
        self.return_type_tok = return_type_tok


class MethodCallNode:
    """Method Call Node."""
    def __init__(self, left_node, method_name_tok, arg_nodes):
        self.left_node = left_node
        self.method_name_tok = method_name_tok
        self.arg_nodes = arg_nodes


class ArrayLiteralNode:
    """Array Literal Node."""
    def __init__(self, elements):
        self.elements = elements
        

class SwitchNode:
    """Switch-Case Node."""
    def __init__(self, switch_expr, cases, default_case):
        self.switch_expr = switch_expr
        self.cases = cases
        self.default_case = default_case

# Built-in Functions
BUILTIN_FUNCTION = {
    'print', 'printf', "print_int", 'print_float', 'print_hex', 'print_string', 'read', 'read_int',
    'len', 'alloc', 'realloc', 'free', 'type_of', 'exit',
    'sys_argc', 'sys_argv', 'get_mem', 'get_mem32', 'addr_of', 'ptr_to', 'syscall'
}

class Parser:
    def __init__(self,tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.current_tok = None
        self.advance()

    def advance(self):
        """Advances to the next token."""
        self.tok_idx += 1
        if self.tok_idx < len(self.tokens):
            self.current_tok = self.tokens[self.tok_idx]
        else:
            self.current_tok = None
        return self.current_tok
    
    def peek(self):
        """Peeks current token."""
        next_idx = self.tok_idx + 1
        if next_idx < len(self.tokens):
            return self.tokens[next_idx]
        return None
    
    def throw(self, message):
        """Throws an error."""
        if self.current_tok:
            line = self.current_tok[2]
            col = self.current_tok[3]

            raise Exception(f"{message} (Line: {line}, Column: {col})")
        else:
            raise Exception(f"{message} (File end)")

    def expect_identifier(self, custom_err_msg="Expected Identifier"):
        """Expects an IDENTIFIER. Throws an error if KEYWORD or a BUILTIN_FUNCTION."""
        if self.current_tok is None:
            self.throw(f"{custom_err_msg}: Unexpected end of file")
        if self.current_tok[0] == 'KEYWORD':
            self.throw(f"Syntax Error: '{self.current_tok[1]}' is a keyword and cannot be used as an identifier.")
        if self.current_tok[1] in BUILTIN_FUNCTION:
            self.throw(f"Syntax Error: '{self.current_tok[1]}' is a built-in function and cannot be redefined or used as an identifier.")        
        if self.current_tok[0] != 'IDENTIFIER':
            self.throw(custom_err_msg)

        tok = self.current_tok
        self.advance()
        return tok

    def factor(self):
        tok = self.current_tok
        if tok is not None and tok[0] == 'OP_SINGLE' and tok[1] in ('+', '-'):
            op_tok = self.current_tok
            self.advance()
            node = self.factor()
            if op_tok[1] == '+':
                return node
            return UnaryOpNode(op_tok, node)
 

        node = self.base_factor()

        while self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'cast':
            self.advance()

            if self.current_tok is None or self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'):
                self.throw("Syntax Error: The data type or class name to be converted must follow the 'cast' command.")
            
            type_tok = self.current_tok
            self.advance()

            if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '[':
                self.advance()
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ']':
                    self.throw("Syntax Error: Expected ']' after '[' in type cast")
                self.advance()
                type_tok = (type_tok[0], type_tok[1] + "[]", type_tok[2], type_tok[3])

            
            node = CastNode(node, type_tok)
        
        return node

    #1. Base Factor
    def base_factor(self):
        tok = self.current_tok
        node = None

        if tok[0] in ('INTEGER', 'FLOAT', 'HEX'):
            self.advance()
            node = NumberNode(tok)

        elif tok[0] in ('STRING'):
            self.advance()
            node = StringNode(tok)
        
        elif tok[0] == 'IDENTIFIER' or (tok[0] == 'KEYWORD' and tok[1] == 'this'):
            self.advance()
            var_node = VarAccessNode(tok)
            
            if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '(':
                self.advance()
                arg_nodes = []

                if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                    arg_nodes.append(self.expr())

                    while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                        self.advance()
                        arg_nodes.append(self.expr())
                
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                    self.throw("Syntax Error: Expected ')'")
                
                self.advance()
                
                node = FuncCallNode(var_node, arg_nodes)
            else:
                node = var_node

            while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] in ('[', '.'):
                
                if self.current_tok[1] == '[':    
                    self.advance()
                    index_node = self.expr()

                    if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ']':
                        self.throw("Syntax Error: Expected ']'")
                    self.advance()
                
                    node = IndexAccessNode(node, index_node)

                elif self.current_tok[1] == '.':
                    self.advance()
                    member_name_tok = self.expect_identifier("Syntax Error: A valid field/method name must follow the period.")

                    if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '(':
                        self.advance()
                        arg_nodes = []
                        if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                            arg_nodes.append(self.expr())
                            while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                                self.advance()
                                arg_nodes.append(self.expr())

                        if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                            self.throw("Syntax Error: Expected ')'")
                        self.advance()

                        node = MethodCallNode(node, member_name_tok, arg_nodes)
                    else:
                        node = MemberAccessNode(node, member_name_tok)
                
            return node
        
        elif tok[0] == 'KEYWORD' and tok[1] in ('true', 'false', 'null'):
            self.advance()
            node = KeywordNode(tok)
        
        elif tok[0] == 'PUNCTUATION' and tok[1] == '(':
            self.advance()
            expr = self.comp_expr()

            if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ')':
                self.advance()
                return expr
            else:
                self.throw("Syntax Error: Expected ')'")
            
        elif tok[0] == 'KEYWORD' and tok[1] == 'limits':
            self.advance()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                self.throw("Syntax Error: Expected '(' after 'limits'")
            self.advance()

            start_node = self.expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ',':
                self.throw("Syntax Error: Invalid format (Correct format: limits(start, end))")
            self.advance()

            end_node = self.expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                self.throw("Syntax Error: 'limits' must be closed with ')'")
            self.advance()

            node = LimitsNode(start_node, end_node)

        elif tok[0] == 'KEYWORD' and tok[1] == 'anfunc':
            self.advance()
            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                self.throw("Syntax Error: Expected '(' after 'anfunc'")
            self.advance()
            args = []
            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                while True:
                    arg_type = self.current_tok
                    self.advance()
                    arg_name = self.expect_identifier("Syntax Error: Expected Parameter Name after Parameter Type")
                    args.append((arg_type, arg_name))
                    if self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                        self.advance()
                    else:
                        break
            self.advance()
            node = AnFuncNode(args, self.block())

        elif tok[0] == 'KEYWORD' and tok[1] == 'new':
            self.advance()
            class_name_tok = self.expect_identifier("Syntax Error: Expected Class Name after 'new'")

            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                self.throw("Syntax Error: Expected '(' after Class")
            self.advance()

            arg_nodes = []
            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                arg_nodes.append(self.expr())
                while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                    self.advance()
                    arg_nodes.append(self.expr())

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                self.throw("Syntax Error: 'new' call must be closed with ')'")
            self.advance()

            return NewObjectNode(class_name_tok, arg_nodes)

        elif tok[0] == 'PUNCTUATION' and tok[1] == '[':
            self.advance()

            elements = []
            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ']':
                elements.append(self.expr())

                while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                    self.advance()
                    elements.append(self.expr())

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ']':
                self.throw("Syntax Error: Array must be closed with ']'")
            self.advance()

            node = ArrayLiteralNode(elements)

        if node is None:
            self.throw(f"Syntax Error: Unexpected token: '{tok[1]}'")
              
        return node


    #2. Multiplication, Division, Modulo, and Exponentiation
    def term(self):
        left = self.factor() #Left first

        while self.current_tok is not None and self.current_tok[0] == 'OP_SINGLE' and self.current_tok[1] in ('*', '/', '%', '^'):
            op_tok = self.current_tok
            self.advance()
            right = self.factor()
            left = BinOpNode(left, op_tok, right)

        return left
    
    #3. Addition and Subtraction
    def expr(self):
        left = self.term()

        while self.current_tok is not None and self.current_tok[0] == 'OP_SINGLE' and self.current_tok[1] in ('+', '-'):
            op_tok = self.current_tok
            self.advance()
            right = self.term()
            left = BinOpNode(left, op_tok, right)

        return left
    
    #4 Comparision and Logic Statements
    def rel_expr(self):
        left = self.expr()

        while self.current_tok is not None and self.current_tok[0] == 'OP_MULTI':
            op_tok = self.current_tok
            self.advance()
            right = self.expr()
            left = BinOpNode(left, op_tok, right)

        return left

    def comp_expr(self):

        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('not', 'await', 'wait'):
            op_tok = self.current_tok
            self.advance()
            node = self.comp_expr()
            return UnaryOpNode(op_tok, node)

        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'is':
            self.advance()
            left = self.rel_expr()

            if self.current_tok is None or self.current_tok[0] != 'KEYWORD' or self.current_tok[1] != 'same':
                self.throw("Syntax Error: Expected 'same' after 'is'")

            op_tok = self.current_tok
            self.advance()
            right = self.rel_expr()
            return BinOpNode(left, op_tok, right)

        left = self.rel_expr()

        while self.current_tok is not None and (
            self.current_tok[0] == 'OP_MULTI' or
            (self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('and', 'or', 'nand', 'nor', 'xor', 'xnor', 'in', 'is'))
        ):
            op_tok = self.current_tok
            self.advance()
            right = self.rel_expr()
            left = BinOpNode(left, op_tok, right)

        return left
    
    #5. Statements
    def statement(self):

        # State 1: Class
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'class':
            self.advance()
            class_name = self.expect_identifier("Syntax Error: Undefined Class Name")

            parent_class = None
            if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'extends':
                self.advance()
                parent_class = self.expect_identifier("Syntax Error: Undefined Class after 'extends'")

            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after Class")
            self.advance()
            
            fields = []
            methods = []
            while not (self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '}'):
                
                modifier_tok = None
                if self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('public', 'private'):
                    modifier_tok = self.current_tok
                    self.advance()

                if self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'define':
                    self.advance()
                    func_name_tok = self.expect_identifier("Syntax Error: Undefined Method Name")

                    if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                        self.throw("Syntax Error: Expected '(' after Method")
                    self.advance()

                    args = []
                    if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                        if self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'):
                            self.throw("Syntax Error: Undefined Parameter Type")
                        arg_type = self.current_tok
                        self.advance()

                        arg_name = self.expect_identifier("Syntax Error: Expected Parameter Name after Parameter Type")
                        args.append((arg_type, arg_name))

                        while self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                            self.advance()
                            arg_type = self.current_tok
                            self.advance()
                            arg_name = self.expect_identifier("Syntax Error: Expected Parameter Name after Parameter Type")
                            args.append((arg_type, arg_name))

                    if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                        self.throw("Syntax Error: Expected ')' after Method Parameter")
                    self.advance()

                    return_type_tok = None
                    if self.current_tok is not None and self.current_tok[0] == 'ARROW':
                        self.advance()
                        if self.current_tok is None or self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'):
                            self.throw("Syntax Error: Expected Return Type after '->'")
                        return_type_tok = self.current_tok
                        self.advance()

                    body_node = self.statement()
                    methods.append(MethodDefNode(modifier_tok, func_name_tok, args, body_node, return_type_tok))
                
                else:
                    if self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'): 
                        self.throw("Syntax Error: Expected Variable Type or 'define'")
                    type_tok = self.current_tok
                    self.advance()
                    
                    name_tok = self.expect_identifier("Syntax Error: Expected Variable Name")
                    
                    if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                        self.throw("Syntax Error: Expected ';' after Class Definition")
                    self.advance()
                    
                    fields.append((modifier_tok, type_tok, name_tok))
            
            self.advance()
            return ClassDefNode(class_name, parent_class, fields, methods)

        # State 2: Code Block
        if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '{':
            return self.block()

        # State 3: IF/BUTIF/ELSE
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'if':
            self.advance()

            condition = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'if'")
            block_node = self.block()

            cases = [(condition, block_node)]
            else_case = None

            #BUTIF Chain
            while self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'butif':
                self.advance()
                cond = self.comp_expr()
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                    self.throw("Syntax Error: Expected '{' after 'butif'")
                cases.append((cond, self.block()))

            #ELSE Block
            if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'else':
                self.advance()
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                    self.throw("Syntax Error: Expected '{' after 'else'")
                else_case = self.block()

            return IfNode(cases, else_case)

        # State 4: WHILE
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'while':
            self.advance()
            condition = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'while'")
            
            return WhileNode(condition, self.block())

        # State 5: FOR    
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'for':
            self.advance()
            var_name_tok = self.expect_identifier("Syntax Error: Undefined Variable Name in 'for'")

            if self.current_tok is None or self.current_tok[0] != 'KEYWORD' or self.current_tok[1] != 'in':
                self.throw("Syntax Error: Expected 'in' after Variable Name")
            self.advance()

            iterable_node = self.expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
              self.throw("Syntax Error: Expected '{' after 'for'")  
            
            return ForNode(var_name_tok, iterable_node, self.block())

        # State 6: TRIGGER
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'trigger':
            self.advance() 
            
            err_node = self.expr() 
            
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' after 'trigger'")
            self.advance() 
            
            return TriggerNode(err_node)

        # State 7: SWITCH/CASE
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'switch':
            self.advance()
            
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                self.throw("Syntax Error: Expected '(' after 'switch'")
            self.advance()
            
            switch_expr = self.comp_expr()
            
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                self.throw("Syntax Error: Expected ')' after 'switch'")
            self.advance()
            
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'switch'")
            self.advance()
            
            cases = []
            default_case = None
            
            while self.current_tok is not None and not (self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '}'):
                if self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'case':
                    self.advance()
                    case_expr = self.comp_expr()
                    
                    if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ':':
                        self.throw("Syntax Error: Expected ':' after 'case' ")
                    self.advance()
                    
                    statements = []
                    while self.current_tok is not None and not (self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('case', 'default')) and not (self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '}'):
                        statements.append(self.statement())
                        
                    cases.append((case_expr, BlockNode(statements)))
                    
                elif self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'default':
                    self.advance()
                    if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ':':
                        self.throw("Syntax Error: Expected ':' after 'default'")
                    self.advance()
                    
                    statements = []
                    while self.current_tok is not None and not (self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('case', 'default')) and not (self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '}'):
                        statements.append(self.statement())
                        
                    default_case = BlockNode(statements)
                else:
                    self.throw("Syntax Error: Unssupported module type in 'switch' (Supported : 'default', 'case')")
                    
            self.advance()
            return SwitchNode(switch_expr, cases, default_case)

        # State 8: WHEN
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('when', 'global'):
            is_global = False

            #ISGLOBAL
            if self.current_tok[1] == 'global':
                is_global = True
                self.advance()
                if self.current_tok is None or self.current_tok[0] != 'KEYWORD' or self.current_tok[1] != 'when':
                    self.throw("Syntax Error: Expected 'when' after 'global'")
                
            self.advance()
            condition = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'when''")
            
            return WhenNode(condition, self.block(), is_global)

        # State 9: VARASSIGN
        modifier_tok = None
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('public', 'private'):
            modifier_tok = self.current_tok
            self.advance()

        if self.current_tok is not None and (
            (self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('int', 'integer', 'double', 'char', 'str', 'string', 'bool', 'var')) or
            (self.current_tok[0] == 'IDENTIFIER' and self.peek() is not None and self.peek()[0] == 'IDENTIFIER')
        ):
            type_tok = self.current_tok
            self.advance()

            var_name_tok = self.expect_identifier("Syntax Error: Variable Name Unassigned")

            if self.current_tok is None or self.current_tok[0] != 'OP_SINGLE' or self.current_tok[1] != '=':
                self.throw(f"Syntax Error: Expected '=' after '{var_name_tok[1]}'")
            self.advance()

            expr_node = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';'")
            self.advance()

            return VarAssignNode(modifier_tok, type_tok, var_name_tok, expr_node)

        # State 10: DEFINE FUNCTION
        func_modifier = None
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('async', 'sync', 'extern'):
            next_tok = self.peek()
            if next_tok is not None and next_tok[0] == 'KEYWORD' and next_tok[1] == 'define':
                func_modifier = self.current_tok
                self.advance()

        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'define':
            self.advance()
            func_name_tok = self.expect_identifier("Syntax Error: Expected Function Name after 'define'")

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '(':
                self.throw("Syntax Error: Expected '(' after Function Name")
            self.advance()

            args = []
            if self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                while True:
                    if self.current_tok is None or self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'):
                        self.throw("Syntax Error: Parameter Data Type Unspecified")
                    arg_type = self.current_tok
                    self.advance()

                    arg_name = self.expect_identifier("Syntax Error: Expected Parameter Name after Parameter Type")
                    args.append((arg_type, arg_name))

                    if self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ',':
                        self.advance()
                    else:
                        break

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ')':
                self.throw("Syntax Error: Expected ')' after Function Parameter")
            self.advance()

            return_type_tok = None
            if self.current_tok is not None and self.current_tok[0] == 'ARROW':
                self.advance()
                if self.current_tok is None or self.current_tok[0] not in ('KEYWORD', 'IDENTIFIER'):
                    self.throw("Syntax Error: Expected Return Type after '->'")
                return_type_tok = self.current_tok
                self.advance()

            if func_modifier and func_modifier[1] == 'extern':
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                    self.throw("Syntax Error: 'extern' function definitions must end with ';'")
                self.advance()
                return FuncDefNode(func_modifier, func_name_tok, args, None, return_type_tok)

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' in Function Definition")
            
            return FuncDefNode(func_modifier, func_name_tok, args, self.block(), return_type_tok)

        # State 11: DEFINE CLASS
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'class':
            self.advance()

            class_name_tok = self.expect_identifier("Syntax Error: Expected Class Name after 'class'")

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' in Class Definiton")
            
            return ClassDefNode(class_name_tok, self.block())

        # State 12: ALLEGE
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'allege':
            self.advance()

            condition = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' after 'allege'")
            self.advance()

            return AllegeNode(condition)

        # State 13: ATTEMPT/EXCLUDE/FINAL
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'attempt':
            self.advance()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'attempt'")
            attempt_body = self.block()

            exclude_body = None
            final_body = None

            #EXCLUDE
            if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'exclude':
                self.advance()
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                    self.throw("Syntax Error: Expected '{' after 'exclude'")
                exclude_body = self.block()

            #FINAL
            if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'final':
                self.advance()
                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                    self.throw("Syntax Error: Expected '{' after 'final'")
                final_body = self.block()

            if exclude_body is None and final_body is None:
                self.throw("Syntax Error: Expected 'final' or 'exclude' after 'attempt'")
            
            return AttemptNode(attempt_body, exclude_body, final_body)
        
        # State 14: SYNC UNIT
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'sync':
            next_tok = self.peek()
            if next_tok is not None and next_tok[0] == 'KEYWORD' and next_tok[1] == 'unit':
                self.advance() 
                self.advance()

                unit_name_tok = self.expect_identifier("Syntax Error: Expected Unit Name after 'sync unit'")

                if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                    self.throw("Syntax Error: Expected '{' in Unit Definition")
                    
                return SyncUnitNode(unit_name_tok, self.block())

        # State 15: WITH
        is_wait = False
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'wait':
            next_tok = self.peek()

            if next_tok is not None and next_tok[0] == 'KEYWORD' and next_tok[1] == 'with':
                is_wait = True
                self.advance()
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'with':
            self.advance() 
            
            unit_name_tok = self.expect_identifier("Syntax Error: Expected Unit Name after 'with'")
            
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
                self.throw("Syntax Error: Expected '{' after 'with'")
                
            return WithNode(unit_name_tok, self.block())

        # State 16: RETURN
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'return':
            self.advance()

            if self.current_tok is not None and self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == ';':
                self.advance()
                return ReturnNode(None)
            
            expr_node = self.comp_expr()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' after 'return'")
            self.advance()

            return ReturnNode(expr_node)

        # State 17: BREAK/GOON
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('break', 'goon'):
            tok_val = self.current_tok[1]
            self.advance()

            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw(f"Syntax Error: Expected ';' after'{tok_val}'")
            self.advance()

            return BreakNode() if tok_val == 'break' else GoonNode()

        # State 18: DELETE
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'delete':
            self.advance()
            target_node = self.expr()
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' after 'delete'")
            self.advance()
            return DeleteNode(target_node)

        # State 19: LINK 
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'link':
            self.advance()
            if self.current_tok is None or self.current_tok[0] != 'STRING':
                self.throw("Syntax Error: Expected File Path (\".\") after 'link' ")
            target_tok = self.current_tok
            self.advance()
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' after 'link'")
            self.advance()
            
            return LinkNode(target_tok)

        # State 20: INCLUDE/FROM
        if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] in ('include', 'from'):
            is_from = False
            item_tok = None

            if self.current_tok[1] == 'from':
                is_from = True
                self.advance()
                module_tok = self.current_tok
                self.advance()

                if self.current_tok is None or self.current_tok[0] != 'KEYWORD' or self.current_tok[1] != 'include':
                    self.throw("Syntax Error: Expected 'include' after Module Name")
                self.advance()
                
                item_tok = self.expect_identifier("Syntax Error: Expected Item Name after 'include'")
            else:
                self.advance()

                if self.current_tok is None or self.current_tok[0] not in ('STRING', 'IDENTIFIER'):
                    self.throw("Syntax Error: Expected File Path or Module Name after 'include'")

                module_tok = self.current_tok
                self.advance()

            alias_tok = None
            if self.current_tok is not None and self.current_tok[0] == 'KEYWORD' and self.current_tok[1] == 'as':
                self.advance()
                alias_tok = self.expect_identifier("Syntax Error: Expected Alias after 'as'")
 
            if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
                self.throw("Syntax Error: Expected ';' at the end of include statement")
            self.advance()

            return IncludeNode(module_tok, item_tok, alias_tok)

        
        # State 21: OPERATION/REASSIGN
        expr_node = self.comp_expr()

        if self.current_tok is not None and (
            (self.current_tok[0] == 'OP_SINGLE' and self.current_tok[1] == '=') or
            self.current_tok[0] == 'OP_ASSIGN'
        ):
            op_tok = self.current_tok
            self.advance()
            value_node = self.comp_expr()

            if isinstance(expr_node, VarAccessNode):
                expr_node = ReAssignNode(expr_node.var_name_tok, op_tok, value_node)

            elif isinstance(expr_node, IndexAccessNode):
                expr_node = IndexAssignNode(expr_node.left_node, expr_node.index_node, op_tok, value_node)
            
            elif isinstance(expr_node, MemberAccessNode):
                expr_node = MemberAssignNode(expr_node.left_node, expr_node.member_name_tok, op_tok, value_node)

            else: self.throw("Syntax Error: Assignment can only be made to variables or array/pointer indices.")

        if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != ';':
            self.throw("Syntax Error: Expected ';' after Expression")
        self.advance()

        return expr_node 

    #5. Code Blocks
    def block(self):
        # Must start with {
        if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '{':
            self.throw("Syntax Error: Expected '{' after Block" )
        self.advance()

        statements = []

        #Read until file end or }

        while self.current_tok is not None and not (self.current_tok[0] == 'PUNCTUATION' and self.current_tok[1] == '}'):
            statements.append(self.statement())

        if self.current_tok is None or self.current_tok[0] != 'PUNCTUATION' or self.current_tok[1] != '}':
            self.throw("Syntax Error: Expected '}'")
        self.advance()

        return BlockNode(statements)


    #Parse
    def parse(self):
        statements = []
        while self.current_tok is not None:
            statements.append(self.statement())
        return statements



#Test
if __name__ == '__main__':
    from lexer import tokenize
    test_code = """

    """
    
    tokens = tokenize(test_code)
    parser = Parser(tokens)
    ast = parser.parse()
    
    print("Parser Output (AST Tree):")
    for node in ast:
        print(node) 