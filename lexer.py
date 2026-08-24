import re 

# KEYWORDS
KEYWORDS = {
    'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'as', 'if', 'else', 'butif', 'exclude', 'allege', 'async', 'sync',
    'await', 'wait', 'break', 'case', 'class', 'goon', 'define', 'delete', 'false', 'true', 'final', 'attempt', 'for', 
    'limits', 'from', 'include', 'in', 'is', 'same', 'global', 'anfunc', 'null', 'while', 'public', 'private', 'when', 'with', 
    'return', 'link', 'int', 'integer', 'double', 'char', 'str', 'string', 'bool', 'var', 'unit', 'trigger', 'cast', 'new', 'this',
    'switch', 'default', 'extends', 'extern', 'hex', 'ptr', 'pointer', 'address' }

# 2. LEXER SPECIFICATIONS 
# The order is important

TOKEN_SPECIFICATION = [
    ('MULTI_COMMENT', r'/\#[\s\S]*?\#/'),                                   #Multi-line Comment
    ('SINGLE_COMMENT', r'//.*'),                                            #Single-line Comment
    ('STRING',        r'".*?"|\'.*?\''),                                    #Strings
    ('HEX',           r'0[xX][0-9a-fA-F]+'),                                #Hexadecimal Numbers
    ('FLOAT',         r'\d+\.\d+'),                                         #Floating Point Numbers
    ('INTEGER',       r'\d+'),                                              #Integer Numbers
    ('OP_ASSIGN',     r'\+=|=\+|-=|=-|\*=|=\*|/=|=/|%=|=%|\^=|=\^'),        #Assign Operators
    ('ARROW', r'->'),                                                       #Arrow
    ('OP_MULTI', r'=\?|\?=|!=|=!|>=|=>|<=|=<|<|>'),                         #Multi-char Operators
    ('OP_SINGLE',     r'[+\-*/%^=]'),                                       #Single-char Operators
    ('PUNCTUATION',   r'[;,\(\)\{\}\[\]\.:]'),                              #Punctuations
    ('IDENTIFIER',    r'[A-Za-z_]\w*'),                                     #Identifiers
    ('WHITESPACE',    r'[ \t\n]+'),                                         #Spaces
    ('MISMATCH',      r'.'),                                                #Unrecognized Characters
]

def tokenize(code):
    tokens = []
    tok_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in TOKEN_SPECIFICATION)

    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()

        line_num = code.count('\n', 0, mo.start()) + 1
        line_start = code.rfind('\n', 0, mo.start()) + 1
        column = mo.start() - line_start + 1

        if kind == 'WHITESPACE':
            continue
        elif kind in ('SINGLE_COMMENT', 'MULTI_COMMENT'):
            continue
        elif kind == 'IDENTIFIER':
            if value.lower() in KEYWORDS:
                kind = 'KEYWORD'
                value = value.lower()
        elif kind == 'MISMATCH':
            raise RuntimeError(f"Unexpected Character '{value}' Line: {line_num} Column: {column}")
        
        tokens.append((kind, value, line_num, column))

    return tokens
