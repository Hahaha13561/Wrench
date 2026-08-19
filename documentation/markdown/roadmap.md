<a id="roadmap-main"></a>

# Roadmap & Future Vision

Wrench is currently in its **Prototype Phase**, written in Python and strictly targeting Linux x86-64 via System V ABI. This roadmap outlines the strategic phases to evolve Wrench from a Python-based prototype into a fully bootstrapped, self-hosting, cross-platform systems programming language.

## Phase 1: Prototype Completion & Syntax Freeze (v0.1.x)

The primary goal of Phase 1 is to finalize the core language specifications and standard library foundations before moving away from the Python environment.

* **Essential Library Integration:** Finalize and integrate critical standard library modules (such as `regex.wr` and advanced Error/IO libraries).
* **Syntax & Semantics Freeze:** Lock down the language grammar and strict mode typing rules.
* **Backward Compatibility Baseline:** Establish a strict versioning transition plan to ensure that code written for the frozen v0.1.x syntax can be compiled by future bootstrapped versions without breaking.
* **Raw Syscall Foundation:** Solidify the native Linux syscall bridges for file I/O, networking, and memory allocation without relying on external C libraries.

## Phase 2: Bootstrapping (v0.2.0)

Phase 2 begins the process of rewriting the compiler in Wrench itself.

* **Native Rewrites:** Port the Python modules (`lexer.py`, `parser.py`, `semantic.py`, `codegen.py`) directly into Wrench (`lexer.wr`, `parser.wr`, etc.).
* **Data Structure Migration:** Replace Python’s dynamic data structures (lists, dictionaries) and dynamic memory model with Wrench’s static arrays, hidden length headers, and custom AST node classes.
* **Recursion & Memory Limits:** Implement robust stack depth and recursion management in the native parser to handle AST generation without the safety net of Python’s memory manager.

## Phase 3: True Self-Hosting (v1.0.0)

This phase proves the language’s independence. Wrench will compile its own compiler.

* **Stage 1 (Cross-compiling the compiler):** Use the Python prototype to compile `wrench.wr`, producing the first native executable: `wrench-v1`.
* **Stage 2 (Self-compiling):** Use `wrench-v1` to compile `wrench.wr` again, producing `wrench-v2`.
* **Verification & Diffing:** Implement a binary diffing/hashing algorithm to mathematically prove that the output of `wrench-v1` and `wrench-v2` are completely identical, confirming that the native compiler’s logic is flawlessly self-sustaining.

## Phase 4: Cross-Platform Expansion (v1.1.0+)

Expanding Wrench beyond Linux x86-64 by introducing target triples and dynamic OS bridges.

* **Target Triple Architecture:** Implement the `--target` CLI flag to allow cross-compilation (e.g., compiling Windows binaries from a Linux host).
* **Windows x64 Support:**
  \* Adapt CodeGen to output the Windows ABI (implementing the 32-byte shadow space and Windows register calling conventions).
  \* Build a native OS bridge interacting with the Win32 API and `kernel32.dll`.
  \* Integrate compatible linker alternatives to replace GNU Linker (`ld`).
* **macOS (Apple Silicon / ARM64 & x86):**
  \* Adapt NASM generation rules for ARM64 architectures.
  \* Build a modular POSIX and `libSystem` core bridge specifically for the macOS target.

## Phase 5: Optimizations & Ecosystem Tooling (v1.x.x)

Enhancing developer experience, performance, and CI/CD pipelines.

* **Compiler Optimization Passes:**
  \* Implement Dead Code Elimination during the Semantic Analysis phase.
  \* Advance the Register Allocation algorithms to reduce reliance on stack memory (optimizing beyond the standard 6-register System V rule).
* **Developer Tooling:**
  \* Build a native Package Manager and a standardized Code Formatter (Linter).
  \* Develop a VSCode Extension (VSIX) that communicates directly with the Wrench compiler for real-time error highlighting and AST analysis.
* **CI/CD & Virtualized Testing:**
  \* Setup comprehensive GitHub Actions matrices.
  \* Integrate local cross-platform verification using QEMU and Wine to map and intercept hardware virtualization error codes automatically.

## Phase 6: Advanced Memory & OS Level Architecture

The long-term vision pushes Wrench into extreme low-level environments.

* **Memory Safety & Leak Analysis:** Develop advanced static analysis tools to prevent memory leaks when relying on manual `alloc` and `delete`.
* **Optional Garbage Collection:** Introduce an *optional* GC module that can be toggled on for application development, or completely detached for kernel-level programming.
* **The Ultimate Goal - Wrench OS:** Utilize Wrench to write a custom Operating System Kernel, beginning with defining the Interrupt Descriptor Table (IDT) and handling hardware CPU interrupts natively in Wrench.
