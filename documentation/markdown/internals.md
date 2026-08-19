<a id="internals-main"></a>

# Compiler Internals

This section provides a deep dive into the internal architecture of the Wrench compiler. It is intended for core developers, contributors, and those curious about how Wrench translates raw text into bare-metal machine code.

## 1. The Compilation Pipeline

The Wrench compiler operates as a multi-pass pipeline, orchestrated primarily by the Command Line Interface (CLI) module (`wrench.py`). The lifecycle of a Wrench program involves the following stages:

1. **Lexical Analysis (Frontend):** The source file (`.wr`) is read as a raw string and converted into a stream of tokens.
2. **Parsing (Frontend):** The token stream is processed by a Recursive Descent Parser to construct an Abstract Syntax Tree (AST).
3. **Import Resolution (Middle-end):** The compiler scans the AST for `include` and `link` nodes. If found, it recursively reads, tokenizes, and parses the imported modules, merging their ASTs into the main tree to form a unified, flattened AST.
4. **Semantic Analysis (Middle-end):** A Visitor walks the unified AST to enforce scoping rules, validate types (Strict Mode), and annotate nodes with hardware-level evaluation types.
5. **Code Generation (Backend):** The annotated AST is compiled down to x86-64 System V ABI Assembly code (`.asm`).
6. **Assembling & Linking (Toolchain):** The compiler invokes `nasm` to convert the Assembly into an ELF64 object file (`.o`), and then calls the GNU Linker (`ld`) to link it with any external objects, producing the final standalone executable.

#### Versionchanged
Changed in version 0.1.1: The compilation pipeline CLI status reporting was standardized, and `CodeGen` now directly ingests the `SemanticAnalyzer` state to perform synchronized type lowering and return-type verification.

## 2. Lexical Analysis

The Lexer converts the raw source string into a list of structured tokens. Wrench uses a sequential Regular Expression (regex) pattern matcher to achieve this.

**Token Matching Order:**
The order of regex rules is critical to prevent partial matches. For example, multi-line comments (`/# ... #/`) are evaluated before single-line comments (`//`), and double-character operators (like `=?` or `+=`) are matched before single-character operators.

#### Versionadded
Added in version 0.1.1: Added the `ARROW` token (`->`) to the token specification for explicit return type signatures. All internal lexer diagnostic messages were converted to English.

**Token Structure:**
Whenever a valid substring is matched, the Lexer generates a tuple containing four elements:
`(kind, value, line_num, column)`

Tracking the `line_num` and `column` directly at the lexical level allows the Parser and Semantic Analyzer to throw highly precise, pinpoint error messages when syntax or typing violations occur.

**Keyword Mapping:**
To keep the regex engine fast, Wrench does not use separate regex rules for every keyword. Instead, any continuous string of letters is initially categorized as an `IDENTIFIER`. Before appending the token, the Lexer checks if the identifier exists within the predefined `KEYWORDS` set. If a match is found, the token’s kind is immediately mutated from `IDENTIFIER` to `KEYWORD`.

## 3. Abstract Syntax Tree & Parsing

The Parser transforms the flat token stream into a hierarchical Abstract Syntax Tree (AST). It is implemented as a **Recursive Descent Parser**, predicting the structural grammar by reading tokens sequentially via `advance()` and `peek()` methods.

#### Versionadded
Added in version 0.1.1: Introduced the `expect_identifier()` helper method. This guard prevents language keywords or members of the `BUILTIN_FUNCTION` set (e.g., `print`, `alloc`, `len`) from being redefined or misused as identifier names. Function and method parsers were extended to parse arrow return signatures (`-> ReturnType`).

**Order of Operations (Operator Precedence):**
Mathematical and logical precedence is strictly enforced by the call stack hierarchy within the parser. The evaluation flows from the lowest precedence (broadest expressions) down to the highest precedence (tightest binding):
1. `comp_expr()`: Logical operations (`and`, `or`, `not`).
2. `rel_expr()`: Relational comparisons (`>?`, `<=`).
3. `expr()`: Addition and subtraction (`+`, `-`).
4. `term()`: Multiplication, division, modulo, and power (`*`, `/`, `%`, `^`).
5. `factor()`: Unary operations and type casting (`cast`).
6. `base_factor()`: Literals, variable access, function calls, and array/member indexing.

**Node Generation:**
Every matched grammar rule produces a specific Node object (e.g., `BinOpNode`, `IfNode`, `AttemptNode`). The parser also enforces the strict semicolon rule at the statement level, halting compilation immediately with precise line/column data if a terminator is missing.

## 4. Semantic Analysis & Type Checking

Before any machine code is generated, the AST must be validated and annotated. The Semantic Analyzer acts as the crucial middle-end, traversing the AST using the **Visitor Design Pattern**.

#### Versionchanged
Changed in version 0.1.1: Semantic Analysis was significantly expanded:
\* **Return Type Tracking:** Tracks target return types per scope using `self.current_return_type` to ensure `return` expressions match declared function signatures.
\* **Built-in Type Definitions:** Maintains `BUILTIN_FUNCTION_TYPES` mapping expected return types for native functions (e.g., `len` -> `int`, `read` -> `string`, `alloc` -> `ptr`).
\* **Validation Helpers:** Added `check_type_compatibility()`, `check_boolean_condition()`, and `check_index_type()` to catch type mismatches before code generation.
\* **Terminology:** Standardized non-value evaluation types to `unit` (replacing `void`).

**Scope & Environment Tracking:**
The analyzer maintains a stack of dictionaries (`self.environments`) to track variable scope.
\* Entering a block (e.g., a loop or function) pushes a new dictionary onto the stack.
\* Exiting the block pops the dictionary off.
This architecture natively supports variable shadowing and guarantees that local variables do not leak into outer scopes.

**Type Tagging for Code Generation:**
The Code Generator relies on knowing the exact data type to select the correct hardware instruction (e.g., integer ALU operations vs. FPU/XMM floating-point operations). The Semantic Analyzer evaluates the tree and attaches `eval_type` and `operand_type` attributes to the AST nodes dynamically.

**Strict Mode & Tolerances:**
When `strict_mode` is enabled, the analyzer intercepts invalid type assignments. However, to support low-level system programming, it explicitly allows certain implicit conversions:
\* `int` to `double`.
\* Standard numerical types to hardware pointer types (`hex`, `ptr`).
\* Implicit Upcasting (verifying class inheritance hierarchies via an internal `class_hierarchy` map).

## 5. Code Generation & System V ABI

The Code Generator (CodeGen) is the most complex backend component of the Wrench compiler. It operates as an AST Visitor that translates semantic nodes directly into raw x86-64 NASM Assembly strings.

Rather than relying on an intermediate representation (IR) like LLVM, Wrench generates assembly natively, embedding OS-specific syscalls and hardware instructions into the final output.

### 5.1. Dedicated Assembly Buffers (functions_code)

#### Versionadded
Added in version 0.1.1: Free functions, class methods, and anonymous functions (`anfuncs`) are no longer emitted inline into the main execution pipeline with manual jump-over labels (`jmp AFTER_...`). Instead, CodeGen uses a dedicated assembly buffer (`self.functions_code`). Function bodies are collected independently and emitted before `_start`, un-cluttering the main execution flow and unifying exit labels (`exit_func_{name}`).

### 5.2. Condition Branching & Inverse Jumps (generate_branch)

#### Versionadded
Added in version 0.1.1: Condition evaluation in `if` and `while` structures was optimized via `generate_branch()`. Rather than setting boolean registers and testing them (`sete` / `movzx` / `test`), CodeGen evaluates binary comparison operands directly and emits direct inverse jump instructions (e.g., `jne`, `jle`, `jae`) to jump straight to target labels.

### 5.3. Stack Memory, Alignment, and Register Optimizations

* **16-Byte Stack Alignment:** Stack frame allocation in methods and functions respects 16-byte System V ABI alignment requirements.
* **32-Bit Register Footprint Reduction:** Resetting registers or passing small constants uses 32-bit register operations (e.g., `xor eax, eax` instead of `mov rax, 0`, `mov edi, 1` instead of `mov rdi, 1`), saving binary code bytes.
* **Formatted Output Engine:** `printf` format strings are parsed at compile time via `_parse_format_string()` into static text and dynamic placeholders, building target AST nodes and invoking specialized assembly printing routines (`print_int`, `print_float`, `print_hex`, `print_string`).

### 5.4. Hardware-Level Exception Interception

Wrench’s `attempt` / `exclude` exception handling operates entirely via OS signal trapping and stack unwinding.

1. **The Global Error Frame:** Wrench maintains a pointer in the `.data` section (`global_err_frame`) that points to a linked list of active `attempt` blocks.
2. **State Saving:** Before entering an `attempt` block, CodeGen pushes the current `rsp`, `rbp`, and the assembly label address of the `exclude` block onto the stack, registering it to the global frame.
3. **Signal Handler (SIGSEGV):** The Wrench executable header includes an `rt_sigaction` (Syscall 13) call that intercepts hardware crashes (like Segmentation Faults). If the program attempts to access invalid memory (or an Out-of-Bounds check fails), the OS executes Wrench’s internal `sigsegv_handler`.
4. **Unwinding:** The handler reads the `global_err_frame`, restores the CPU registers (`rsp`, `rbp`) to their safe state, and executes a `jmp` instruction directly into the `exclude` block, entirely bypassing a fatal crash.

### 5.5. Multi-Processing (Forking) over Threading

Wrench does not implement POSIX threads (pthreads). Instead, concurrency is handled through true multi-processing.

* **Async Execution:** The `async` modifier translates directly to a `fork` syscall. The parent process continues execution, while the child executes the isolated function.
* **Polling (The ‘when’ keyword):** Wrench’s observer pattern forks a lightweight background process. CodeGen implements a continuous loop that invokes Syscall 35 (`nanosleep`) to sleep for 10 milliseconds, waking up only to evaluate the condition before sleeping again.
