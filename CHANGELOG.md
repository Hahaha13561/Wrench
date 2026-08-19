# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-08-17

### Added
* **Standard Library Modules**:
  * `std/argparser.wr`: Argument parsing library supporting `Argument`, `ArgumentParser`, flags, actions, and subparsers.
  * `std/clone.wr`: Memory cloning, array cell swapping, target memory filling, and dynamic `clone()` helpers.
  * `std/os.wr`: Path operations (`join`, `dirname`, `normpath`, `abspath`) and OS subsystem helpers (`getcwd`, `remove`, `rmdir`, `makedirs`, `access`, `getenv`) with OS error mapping.
  * `std/regex.wr`: Regular expression matching utilities including `compile`, `match`, `finditer`, `split`, and `sub`.
  * `std/subprocess.wr`: Process management and IPC library utilizing native x86-64 Linux syscalls (`SYS_FORK`, `SYS_EXECVE`, `SYS_PIPE`, `SYS_DUP2`, `SYS_WAIT4`, `SYS_KILL`) with `Popen` and `CompletedProcess` abstractions.
* **Language Features & Parser**:
  * Added explicit function and method return-type syntax support via the `->` (ARROW) token.
  * Added `expect_identifier` helper and `BUILTIN_FUNCTION` protection rules in the parser to prevent redefinition of built-in functions/keywords.
  * Added token context window logging for syntax parse errors.
* **Compiler & Tooling**:
  * Added `BUILTIN_FUNCTION_TYPES` mapping in the semantic analyzer to enforce proper call/return evaluation for language built-ins.
  * Added traceback logging on compilation exceptions in `wrench.py`.

### Changed
* **Compiler Backend & Assembly (`codegen.py`)**:
  * Synchronized `CodeGen` with `SemanticAnalyzer` to pass return-type metadata, strict variable types, and class member structures.
  * Decoupled free functions, methods, and anonymous functions into a dedicated `functions_code` assembly block linked into the executable entry point.
  * Implemented `generate_branch` to convert boolean conditions directly into inverse jump assembly instructions.
  * Added format string parsing and placeholder AST construction for native `printf` support.
  * Updated runtime assembly routines (`print_string` with null checks, `print_hex`, `concat_strings`, `compare_strings`, `alloc`, `get_mem32`, `get_len`).
  * Replaced 64-bit register moves with 32-bit register alternatives for stack space optimization.
* **Semantic Analyzer (`semantic.py`)**:
  * Expanded semantic checks to track function signatures, class methods, class fields, and inheritance hierarchies.
  * Extended visitor rules across AST nodes (Blocks, Conditions, Loops, Returns, Assignments, Class Definitions, Index Access) to infer and validate `eval_type`.
* **Standard Library & CLI**:
  * Reordered CLI execution workflow in `wrench.py` (`Tokenize` -> `Parse` -> `Resolve Imports` -> `Semantic Analysis` -> `CodeGen`).
  * Annotated standard library functions with return types (`->`) across `collections`, `string`, `fs`, `math`, `time`, and `sys`.
  * Restructured `std/sys.wr` into a structured `SysModule` object.

### Fixed & Removed
* Unified function exit labels and strengthened array bounds checking with SIGSEGV stack recovery in code generation.
* Fixed import alias resolution in CLI to preserve line and column metadata.
* Removed embedded inline test harnesses across all standard library files.
* Translated Turkish error messages and code comments into English across parser, codegen, and standard modules.