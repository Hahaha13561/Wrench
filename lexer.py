import re 

# 1. ANAHTAR KELİMELER
#  Dile ait anahtar kelimeler bu listede kontrol edilir.
KEYWORDS = {
    'and', 'or', 'not', 'nand', 'nor', 'xor', 'xnor', 'as', 'if', 'else', 'butif', 'exclude', 'allege', 'async', 'sync',
    'await', 'wait', 'break', 'case', 'class', 'goon', 'define', 'delete', 'false', 'true', 'final', 'attempt', 'for', 
    'limits', 'from', 'include', 'in', 'is', 'same', 'global', 'anfunc', 'null', 'while', 'public', 'private', 'when', 'with', 
    'return', 'link', 'int', 'integer', 'double', 'char', 'str', 'string', 'bool', 'var', 'unit', 'trigger', 'cast', 'new', 'this',
    'switch', 'default', 'extends', 'extern', 'hex', 'ptr', 'pointer', 'address' }

# 2. LEXER SPECIFICATIONS 
# Regex Sırası önemlidir.

TOKEN_SPECIFICATION = [
    ('MULTI_COMMENT', r'/\#[\s\S]*?\#/'),           #Çok sıralı yorum
    ('SINGLE_COMMENT', r'//.*'),                    #Tek sıralı yorum
    ('STRING',        r'".*?"|\'.*?\''),            #Çift ya da tek tırnaklı "metinler"
    ('HEX',           r'0[xX][0-9a-fA-F]+'),
    ('FLOAT',         r'\d+\.\d+'),                 #Ondalıklı sayılar (double)
    ('INTEGER',       r'\d+'),                      #Tam sayılar
    ('OP_ASSIGN',     r'\+=|=\+|-=|=-|\*=|=\*|/=|=/|%=|=%|\^=|=\^'),     #Bileşik Atama Operatörleri
    ('OP_MULTI', r'=\?|\?=|!=|=!|>=|=>|<=|=<|<|>'), #İki karakterli operatörler
    ('OP_SINGLE',     r'[+\-*/%^=]'),               #Tek karakterli operatörler
    ('PUNCTUATION',   r'[;,\(\)\{\}\[\]\.:]'),         #Noktalama ve parantezler
    ('IDENTIFIER',    r'[A-Za-z_]\w*'),             #Değişken ve fonksiyon identifier'ları (isim atamaları)
    ('WHITESPACE',    r'[ \t\n]+'),                 #Boşluklar (atlamak için)
    ('MISMATCH',      r'.'),                        #Tanımlanmayan karakter (Hata fırlatacak)
]

def tokenize(code):
    tokens = []
    #Kuralları regex deseninde birleştir
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
            raise RuntimeError(f"Beklenmeyen karakter '{value}' Satır: {line_num} Sütun: {column}")
        
        tokens.append((kind, value, line_num, column))

    return tokens
