import json
import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
vscode_dir = os.path.dirname(script_dir)

keywords_path = os.path.join(vscode_dir, "src", "keywords.ts")
grammar_path = os.path.join(vscode_dir, "syntaxes", "wrench.tmLanguage.json")

def parse_ts_export_keys(const_name, content):
    """Finds export const CONST_NAME and extracts dictionary keys."""
    pattern = rf"export const {const_name}[\s\S]*?=\s*\{{([\s\S]*?)\}};"
    match = re.search(pattern, content)
    if not match:
        return []
    block = match.group(1)
    return re.findall(r'["\']([^"\']+)["\']\s*:', block)

def escape_regex_symbol(symbol):
    """Escapes special regex characters for non-word operators."""
    res = ""
    for char in symbol:
        if char in r".^$*+?()[]{}|\/":
            res += "\\" + char
        else:
            res += char
    return res

with open(keywords_path, "r", encoding="utf-8") as f:
    ts_content = f.read()

with open(grammar_path, "r", encoding="utf-8") as f:
    grammar = json.load(f)

# Word Keywords Mappings -> \b(key1|key2)\b
word_mappings = {
    "CONTROL_KEYWORDS": ("control_keywords", 0),
    "DECLARATION_KEYWORDS": ("declaration_keywords", 0),
    "OPERATOR_KEYWORDS": ("operator_keywords", 0),
    "VALUE_KEYWORDS": ("value_keywords", 0),
    "DATA_TYPES": ("types", 0),
    "BUILTIN_FUNCTIONS": ("builtins", 0),
}

for ts_const, (repo_name, pattern_idx) in word_mappings.items():
    keys = parse_ts_export_keys(ts_const, ts_content)
    if keys:
        pattern_str = r"\b(" + "|".join(keys) + r")\b"
        grammar["repository"][repo_name]["patterns"][pattern_idx]["match"] = pattern_str

# Symbol Operators Mappings -> (op1|op2)
operator_mappings = {
    "ASSIGNMENT_OPERATORS": ("operators", 1),
    "COMPARISON_OPERATORS": ("operators", 2),
    "ARITHMETIC_OPERATORS": ("operators", 3),
}

for ts_const, (repo_name, pattern_idx) in operator_mappings.items():
    keys = parse_ts_export_keys(ts_const, ts_content)
    if keys:
        escaped_keys = [escape_regex_symbol(k) for k in keys]
        pattern_str = "(" + "|".join(escaped_keys) + ")"
        grammar["repository"][repo_name]["patterns"][pattern_idx]["match"] = pattern_str

with open(grammar_path, "w", encoding="utf-8") as f:
    json.dump(grammar, f, indent=2, ensure_ascii=False)

print("Updated wrench.tmLanguage.json")