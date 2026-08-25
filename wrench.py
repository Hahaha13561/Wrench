import argparse
import sys
import os 
import subprocess
import copy
import json
from lexer import tokenize
from parser import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGen

def resolve_imports(ast, current_dir, linked_objects, imported_asts=None, fully_included=None):
    """Scans the AST, finds inclusions, origins and links, resolves and merges back to the AST."""
    if imported_asts is None:
        imported_asts = {}
    if fully_included is None:
        fully_included = set()

    new_ast = []
    for node in ast:
        node_type = type(node).__name__

        if node_type == 'LinkNode':
            obj_file = node.target_str_tok[1].strip('"\'')
            linked_objects.add(obj_file)

        elif node_type == 'IncludeNode':
            module_name = node.module_tok[1].strip('"\'')
            if not module_name.endswith('.wr'):
                module_name += '.wr'

            if module_name.startswith("std/"):
                module_path = os.path.normpath(os.path.join(os.getcwd(), module_name))
            else:
                module_path = os.path.normpath(os.path.join(current_dir, module_name))

            if not node.item_tok and module_path in fully_included:
                continue

            if module_path not in imported_asts:
                if not os.path.exists(module_path):
                    raise Exception(f"Importing Error: '{module_path}' is not found.")
                with open(module_path, 'r', encoding='utf-8') as f:
                    sub_code = f.read()

                sub_tokens = tokenize(sub_code)
                sub_parser = Parser(sub_tokens)
                sub_ast = sub_parser.parse()

                sub_dir = os.path.dirname(module_path) or current_dir
                sub_ast = resolve_imports(sub_ast, sub_dir, linked_objects, imported_asts, fully_included)
                imported_asts[module_path] = sub_ast

            sub_ast = imported_asts[module_path]

            if node.item_tok:
                item_name = node.item_tok[1]
                alias_name = node.alias_tok[1] if node.alias_tok else item_name

                found = False
                for sub_node in sub_ast:
                    sub_node_type = type(sub_node).__name__
                    name = None
                    target_tok = None

                    if sub_node_type == 'FuncDefNode':
                        name = sub_node.func_name_tok[1]
                        target_tok = sub_node.func_name_tok

                    elif sub_node_type == 'ClassDefNode':
                        name = sub_node.class_name_tok[1]
                        target_tok = sub_node.class_name_tok

                    elif sub_node_type == 'VarAssignNode':
                        name = sub_node.var_name_tok[1]
                        target_tok = sub_node.var_name_tok

                    if name == item_name:
                        if node.alias_tok:
                            node_to_add = copy.deepcopy(sub_node)
                            line = target_tok[2] if target_tok and len(target_tok) > 2 else 0
                            col = target_tok[3] if target_tok and len(target_tok) > 3 else 0
                            alias_tok = ('IDENTIFIER', alias_name, line, col)
                            if sub_node_type == 'FuncDefNode':
                                node_to_add.func_name_tok = alias_tok
                            elif sub_node_type == 'ClassDefNode':
                                node_to_add.class_name_tok = alias_tok
                            elif sub_node_type == 'VarAssignNode':
                                node_to_add.var_name_tok = alias_tok

                        else:
                            node_to_add = sub_node

                        new_ast.append(node_to_add)
                        found = True
                        break

                if not found:
                    raise Exception(f"Import Error: '{item_name}' is not found in '{module_name}'.")
            else:
                new_ast.extend(sub_ast)
                fully_included.add(module_path)

        else:
            new_ast.append(node)

    return new_ast

def output_symbols(input_file, is_strict=True):
    """Parses the source code, analyzes semantics and outputs the AST as JSON."""
    if not os.path.exists(input_file):
        print(json.dumps({"error": f"File '{input_file}' not found."}))
        sys.exit(1)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tokens = tokenize(source_code)
        parser = Parser(tokens)
        ast = parser.parse()

        linked_objects = set()
        current_dir = os.path.dirname(os.path.abspath(input_file))
        ast = resolve_imports(ast, current_dir, linked_objects)

        analyzer = SemanticAnalyzer(strict_mode=is_strict)
        analyzer.analyze(ast)

        symbol_data = {
            "functions": getattr(analyzer, 'functions', {}),
            "classes": getattr(analyzer, 'classes', {}),
            "globals": getattr(analyzer, 'global_symbols', {})
        }

        print(json.dumps(symbol_data, indent=2, default=str))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

def compile_file(input_file, output_name=None, is_strict=True, keep_temps=False):
    if not input_file.endswith('.wr'):
        print(f"Error: File extensions need to be '.wr' ({input_file}).")
        sys.exit(1)

    if output_name is None:
        output_name = os.path.splitext(os.path.basename(input_file))[0]

    asm_file = f"{output_name}.asm"
    obj_file = f"{output_name}.o"

    print(f"[1/5] Reading source code: {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    print("[2/5]  Tokenizing and Parsing...")
    try:
        tokens = tokenize(source_code)
        parser = Parser(tokens)
        ast = parser.parse()

        print("[3/5]  Resolving Imports and Performing Semantic Analysis...")
        linked_objects = set()
        current_dir = os.path.dirname(os.path.abspath(input_file))

        ast = resolve_imports(ast, current_dir, linked_objects)

        analyzer = SemanticAnalyzer(strict_mode=is_strict)
        analyzer.analyze(ast)

        compiler = CodeGen(semantic_analyzer=analyzer)
        compiler.generate(ast)
        asm_code = compiler.get_code()

    except Exception as e:
        #Debug code
        import traceback
        traceback.print_exc()
        #Debug code end
        print(f"\n COMPILING ERROR:\n{str(e)}")
        sys.exit(1)

    print(f"[4/5] Generating Assembly Code: {asm_file}...")
    with open(asm_file, 'w', encoding='utf-8') as f:
        f.write(asm_code)

    print("[5/5] Generating Machine Code...")
    nasm_cmd = ["nasm", "-O0", "-f", "elf64", asm_file, "-o", obj_file]
    nasm_result = subprocess.run(nasm_cmd, capture_output=True, text=True)
    if nasm_result.returncode != 0:
        print("NASM Error:\n", nasm_result.stderr)
        sys.exit(1)

    ld_cmd = ["ld", obj_file] + list(linked_objects) + ["-o", output_name]
    ld_result = subprocess.run(ld_cmd, capture_output=True, text=True)
    if ld_result.returncode != 0:
        print("Linker Error:\n", ld_result.stderr)
        sys.exit(1)

    if not keep_temps:
        if os.path.exists(asm_file):
            os.remove(asm_file)
        if os.path.exists(obj_file):
            os.remove(obj_file)
        print("[*] Cleared Temporary Files.")
    else:
        print("[*] Kept Temporary Files.")

    print(f"\nSUCCESS: Program Compiled: ./{output_name}")


if __name__ == '__main__':
    
    argparser = argparse.ArgumentParser(description="Wrench Compiler")

    argparser.add_argument("input", help=".wr source code to be compiled")

    argparser.add_argument("-o", "--output", help="Executable file name to be produced", default=None)
    argparser.add_argument("--no-strict", "-ns", action="store_true", help="Turns off strict mode in semantic analyzation.")
    argparser.add_argument("-k", "--keep", action="store_true", help= "Keeps the temporary files created during compilation (.asm/.o)")
    argparser.add_argument("-r", "--run", action="store_true", help="Automatically runs the program and delete the executable.")
    argparser.add_argument("--symbols", action="store_true", help="Gives the output symbol table as JSON.")

    args = argparser.parse_args()

    strict_flag = not args.no_strict

    if args.symbols:
        output_symbols(args.input, strict_flag)
        sys.exit(0)

    compile_file(args.input, args.output, strict_flag, args.keep)

    if args.run:
        output_name = args.output if args.output else os.path.splitext(os.path.basename(args.input))[0]
        exec_path = f"./{output_name}"

        try:
            print("-----------------------------------\n")
            subprocess.run([exec_path])
            print("\n-----------------------------------")
        except Exception as e:
            print(f"Error running file: {e}")

        if os.path.exists(exec_path):
            os.remove(exec_path)