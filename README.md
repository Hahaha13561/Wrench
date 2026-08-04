# Wrench, The Programming Language

**Version** v0.1.0 (Alpha Prototype)

Wrench is a native, low-level programming language designed to get you as close to the hardware as possible without forcing you to write raw assembly by hand. It bypasses massive background runtimes and virtual machines, compiling directly into binary machine code.

Current prototype targets **Linux x86-64** architecture and is taking the final steps before the bootstrapping phase.

## 📂 Project Structure

The compiler currently is written in Python and modularized into the following pipeline:

*`wrench.py`: The main CLI Entry Point.
* `lexer.py`: Lexical analysis and tokenization.
* `parser.py`: Abstract Syntax Tree (AST) generation.
* `semantic.py`: Strict type-checking and semantic validation.
* `codegen.py`: Linux x86-64 assembly generation.
* `std/`: The Wrench Standard Library containing following essential modules:
    *`collections.wr`
    *`error.wr`
    *`fs.wr`
    *`math.wr`
    *`string.wr`
    *`sys.wr`
    *`time.wr`

## Prerequisites

Since the Wrench compiler is currently running its prototype phase through Python, you will need:

* **Python 3.x** installed on your system.
* **Linux x86-64 environment** (If you are on Windows, using **WSL - Windows Subsystem for Linux** is highly recommended to run the compiled binaries).

## Usage

Write your Wrench code in a `.wr` file and invoke the compiler via the command line:

```bash
python wrench.py hello.wr
```

## Compiler Flags

*`-o`/`--output`: Set the executable file name.
*`-ns`/`--no-strict`: Disable strict mode in semantic analysis for rapid prototyping.
*`-k`/`--keep`: Keep temporary files (.asm / .o) to inspect the generated x86-64 assembly.
*`-r`/`--run`: Compile, automatically run the program, and delete the executable immediately.

## Documentation

Comprehensive documentation, including a full tutorial, language reference, and standard library details, is provided in the release. Please refer to the PDF and HTML files included in the documentation folder or the latest release assets.