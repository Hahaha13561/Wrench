<a id="reference-main"></a>

# Language Reference

Wrench Language Reference defines the grammar, types, memory management and how the system works.

You might as well check [Tutorial](tutorial.md#tutorial-main) if you’re new and starting from scratch.

<a id="reference-architecture"></a>

# 1. Design Philosophy & Architecture

Wrench is designed to bridge the gap between the ergonomic, developer-friendly syntax of high-level languages and the raw, bare-metal performance of low-level system languages. It enforces structure through explicit scoping brackets (`{}`, `[]`, `()`) rather than strict whitespace indentation.

## 1.1. Freestanding Execution & AOT Compilation

Wrench is an Ahead-Of-Time (AOT) compiled language. It does not rely on Virtual Machines (VM), Just-In-Time (JIT) compilers, or a heavy runtime environment.

The compiler translates Wrench source code directly into x86-64 Assembly (currently targeting the System V ABI). Because it does not require a background C library (libc) to function, Wrench is fundamentally freestanding. It interacts directly with the operating system kernel via native system calls (syscalls).

## 1.2 Memory Management

To maintain deterministic performance and a zero-overhead runtime, Wrench does not implement a Garbage Collector (GC).

* Memory allocation is handled transparently by the compiler for standard stack variables.
* Heap allocations (e.g., dynamic arrays, object instances created with `new`) rely on direct kernel memory mapping (e.g., `mmap`).
* Developers retain full control over the memory lifecycle using explicit keywords like `delete` and `alloc`, and can manipulate raw hardware addresses directly using primitive types such as `ptr`, `address`, and `hex`.

## 1.3. Object-Oriented Bare Metal

While Wrench utilizes an Object-Oriented Programming (OOP) paradigm, primitive data types (`int`, `char`, `double`) remain strictly lightweight. They do not carry the runtime overhead of a class instance unless explicitly cast or wrapped. Advanced mechanisms, such as signal-based exception handling (SIGSEGV catching), operate directly at the assembly level without requiring stack-unwinding libraries.

.._reference-lexical:

# 2. Lexical Structure

This section covers the basic lexical elements of Wrench, including comments, identifiers, keywords, and operators.

## 2.1. Comments

Wrench supports both single-line and multi-line comments. Comments are completely ignored by the lexer.

* **Single-line:** Starts with `//` and continues to the end of the line.
* **Multi-line:** Enclosed between `/#` and `#/`.

```text
// This is a single-line comment
/# This is a
   multi-line comment #/
```

## 2.2. Identifiers

Identifiers are used to name variables, functions, classes, and synchronization units. An identifier must start with a letter (A-Z, a-z) or an underscore (`_`), followed by any number of letters, digits, or underscores. Identifiers are case-sensitive.

#### Versionchanged
Changed in version 0.1.1: Strict identifier validation (`expect_identifier`) is now enforced during parsing. Identifiers cannot share names with reserved keywords or built-in functions (e.g., `print`, `printf`, `len`, `alloc`, `realloc`, `free`, `read`, `get_mem32`, `syscall`).

## 2.3. Keywords

The following identifiers are reserved as keywords and cannot be used as regular variable or function names:

* **Control Flow:** `if`, `else`, `butif`, `switch`, `case`, `default`, `for`, `while`, `break`, `goon`
* **Data Types:** `int`, `integer`, `double`, `char`, `str`, `string`, `bool`, `var`, `unit`, `hex`, `ptr`, `pointer`, `address`
* **Logic & Operators:** `and`, `or`, `not`, `nand`, `nor`, `xor`, `xnor`, `in`, `is`, `same`, `cast`
* **OOP & Structure:** `class`, `new`, `this`, `extends`, `public`, `private`
* **Functions & Modules:** `define`, `anfunc`, `return`, `include`, `from`, `as`, `link`, `extern`
* **Memory & Error:** `delete`, `attempt`, `exclude`, `final`, `trigger`, `allege`
* **Concurrency & Events:** `async`, `sync`, `await`, `wait`, `with`, `when`, `global`
* **Constants:** `true`, `false`, `null`, `limits`

## 2.4. Operators & Operator Tolerance

Wrench provides standard mathematical and bitwise operators, but introduces a unique **operator tolerance** rule to improve developer ergonomics and prevent common syntax errors.

#### Versionadded
Added in version 0.1.1: Added the Arrow token `->` for explicit function and method return type declarations.

* **Assignment Tolerance:** Compound assignment operators can be written in either direction. For example, `+=` and `=+` are treated identically by the lexer. This applies to all compound assignments (`-=` / `=-`, `*=` / `=*`, `/=` / `=/`, etc.).
* **Relational Tolerance:** The equality check is written as `=?` or `?=`, intentionally avoiding the common `==` vs `=` confusion found in C-like languages. Other relational operators also feature directional tolerance (`>=` / `=>`, `!=` / `=!`, `<=` / `=<`).

```text
x =+ 5;  // Identical to x += 5;
if (x =? 10) { ... } // Identical to if (x ?= 10)
```

## 2.5. Punctuation

Wrench uses `{}` for code blocks, `[]` for indexing and array literals, and `()` for parameters and logical grouping.

**Important:** Wrench enforces a strict semicolon (`;`) rule. Every variable assignment, reassignment, return, delete, link, include, and trigger statement must explicitly end with a semicolon to successfully parse.

<a id="reference-types"></a>

# 3. Types and Variables

Wrench offers a robust type system that balances the safety of static typing with the flexibility needed for low-level memory manipulation.

## 3.1. Primitive Types

Primitive types in Wrench are lightweight and translate directly into their hardware-level equivalents without background object overhead.

* **Integer:** `int` or `integer` (64-bit signed integer).
* **Floating-Point:** `double` or `float` (64-bit precision floating-point numbers mapped to xmm registers).
* **Character:** `char` (1-byte ASCII character).
* **Boolean:** `bool` (Evaluates to `1` for `true` and `0` for `false`).
* **String:** `str` or `string` (A contiguous array of characters ending with a null terminator).
* **Unit:** `unit` (Represents expressions or functions that return no value).

#### Versionchanged
Changed in version 0.1.1: The non-value return evaluation type previously referred to as `void` has been renamed to `unit`.

## 3.2. Memory & Hardware Types

To support freestanding execution and bare-metal programming, Wrench includes native types for direct memory handling:

* **Hexadecimal:** `hex` (Stores base-16 numerical values directly).
* **Pointers:** `ptr`, `pointer`, or `address` (Stores memory addresses for raw data manipulation).

In strict mode, Wrench seamlessly allows assignments between memory types (`hex`, `ptr`) and standard `int` types without raising a semantic error, acknowledging that memory addresses are fundamentally integers at the hardware level.

## 3.3. Flexible Types (var & any)

For scenarios where dynamic typing or type inference is preferred:

* **\`\`var\`\`:** Instructs the compiler to infer the variable’s type based on the assigned value during compilation. Once inferred, the type is statically locked.
* **\`\`any\`\`:** A universal wildcard type. It completely bypasses the Semantic Analyzer’s strict type-checking, allowing a variable to hold or transition between any data type.

## 3.4. Variable Declaration

Variables are declared by specifying an optional access modifier, the type, the identifier, and an initial value. Every assignment must end with a semicolon (`;`).

```text
int my_number = 42;
var inferred_text = "Wrench Compiler"; // Type becomes 'string'
hex mem_addr = 0x44000004;
```

Access modifiers (`public`, `private`) can be placed before the type. While primarily used for class fields, the parser allows them in standard variable assignments.

```text
private int hidden_value = 100;
```

## 3.5. Type Checking & Casting

The Wrench compiler includes a strict Semantic Analyzer (`strict_mode`). When strict mode is enabled, the compiler enforces type safety with specific hardware-level tolerances:

#### Versionchanged
Changed in version 0.1.1: Semantic analysis checks were expanded:
\* **Return Type Validation:** Verifies that function returns match declared signatures or fallback to `unit`.
\* **Condition Guards:** Enforces that conditional expressions (in `if`, `while`, `when`) evaluate to valid logical types rather than `unit`.
\* **Index Validation:** Confirms array access indices evaluate to `int` or `hex`.
\* **Class Hierarchy Scans:** Member lookup scans parent hierarchies via `get_field_type()`.

1. **Implicit Conversions:** Assigning an `int` to a `double` is natively permitted.
2. **Polymorphism (Upcasting):** Assigning a child class instance to a parent class type is strictly validated and allowed.
3. **Explicit Casting:** Developers can force a type conversion using the `cast` keyword.

```text
double pi = 3;             // Legal implicit conversion
var str_val = 42 cast str; // Explicit cast from int to string
```

Using `cast` translates directly into hardware-level data conversion instructions (e.g., `cvtsi2sd` for int to double, or dynamic allocations for int to string) within the Code Generator.

<a id="reference-control-flow"></a>

# 4. Control Flow

Wrench provides a familiar yet distinct set of control flow mechanisms, replacing some traditional keywords with more expressive alternatives.

## 4.1. Conditional Statements (if / butif / else)

Wrench uses `if` for initial conditions and introduces `butif` as the direct replacement for `else if` or `elif`. The fallback block is defined with `else`.

```text
if (x > 10) {
    print("x is greater than 10;");
} butif (x =? 10) {
    print("x is exactly 10;");
} else {
    print("x is less than 10;");
}
```

## 4.2. Switch / Case

Wrench supports `switch` statements for cleaner multi-condition branching.

**Important:** Unlike C or C++, Wrench does **not** feature implicit fall-through. The compiler automatically inserts jump instructions at the end of each `case` block. Therefore, you do not need to manually write `break;` at the end of a case.

```text
switch (status_code) {
    case 200:
        print("Success;");
    case 404:
        print("Not Found;");
    default:
        print("Unknown Error;");
}
```

## 4.3. Loops (while & for)

**While Loops:** Execute as long as the condition evaluates to true.

```text
while (count < 5) {
    count += 1;
}
```

**For Loops & Limits:** Wrench’s `for` loop iterates over arrays or iterable objects using the `in` keyword. To loop through a range of numbers, Wrench provides the built-in `limits(start, end)` function, which generates an iterable sequence on the fly.

```text
for i in limits(0, 10) {
    print_int(i);
}
```

## 4.4. Loop Control (break & goon)

Wrench uses standard loop control mechanisms but renames the `continue` keyword to `goon` (Go On) to better reflect its semantic purpose.

* **\`\`break;\`\`** Terminates the nearest enclosing loop entirely.
* **\`\`goon;\`\`** Skips the remaining code in the current iteration and forces the loop to proceed to the next iteration.

Both `break` and `goon` must be terminated with a semicolon.

```text
for i in limits(0, 100) {
    if (i =? 50) {
        break; // Stop the loop completely
    } butif (i % 2 =? 0) {
        goon;  // Skip even numbers
    }
    print_int(i);
}
```

<a id="reference-memory-arrays"></a>

# 5. Memory & Arrays

Because Wrench does not rely on a standard C library (libc) or a Virtual Machine, its array and memory management systems interact directly with the operating system kernel.

## 5.1. Raw Pointer Arrays & The Hidden Header

In Wrench, arrays are **not** object instances (classes). They are contiguous blocks of raw memory accessed via pointer arithmetic.

To provide safety without the overhead of a class structure, the Wrench compiler implements a **Hidden Length Header**. When an array is allocated, the compiler requests extra memory from the kernel. It writes the length of the array into the first 8 bytes (64 bits), and then advances the pointer by 8 bytes before returning it to the program.

As a result, the pointer you interact with points directly to the first element, while the array’s capacity remains safely hidden just behind the pointer (at `pointer - 8 bytes`).

## 5.2. Array Initialization & Bounds Checking

Arrays can be initialized using the array literal syntax `[]`.

```text
var my_list = [10, 20, 30, 40];
print_int(my_list[2]); // Prints 30;
```

**Out-of-Bounds Protection:** Before any array read (`my_list[i]`) or write (`my_list[i] = x;`) operation, the compiler injects assembly instructions to read the hidden length header. If the requested index is less than 0 or greater than/equal to the array’s length, the compiler throws a critical **Out of Bounds Error (Code: 99)** and routes the program to the exception handler to prevent memory corruption.

## 5.3. Strings as Character Arrays

Strings in Wrench are natively treated as arrays of characters. However, the compiler tracks the variable’s evaluation type (`eval_type == 'char'`).

When you index a standard array (e.g., an array of integers), the compiler steps forward by 8 bytes per index. When you index a string, the compiler steps forward by exactly 1 byte.

```text
var text = "Wrench";
text[0] = "F" cast char;
print(text); // Prints "French"
```

## 5.4. Manual Allocation and Deallocation

Wrench provides low-level functions to manually request and release raw memory pages from the kernel:

* **\`\`alloc(size);\`\`** Allocates a contiguous block of memory and returns a pointer. (Automatically applies the hidden length header logic).
* **\`\`realloc(pointer, new_size);\`\`** Resizes a previously allocated memory block.
* **\`\`delete pointer;\`\`** Because Wrench lacks a Garbage Collector, dynamically allocated arrays or objects must be manually freed using the `delete` keyword to prevent memory leaks.

```text
var buffer = alloc(1024); // Allocate 1024 bytes
// ... use buffer ...
delete buffer;            // Free the memory back to the OS
```

<a id="reference-functions"></a>

# 6. Functions

Functions in Wrench are defined using the `define` keyword. The language supports standard named functions, anonymous functions (anfunc), and external foreign function interfaces.

## 6.1. Function Definition & Returns

A standard function requires a name, a typed parameter list, and a code block. Wrench does not require you to explicitly declare the return type of a function in the signature; it is inferred dynamically.

#### Versionadded
Added in version 0.1.1: Functions and methods support explicit return type annotations using the `-> ReturnType` syntax. If omitted, the return type defaults to `unit` or is inferred during semantic analysis.

To return a value from a function, use the `return` keyword followed by a semicolon. To return early without a value, simply use `return;`.

```text
define calculate_area(int width, int height) {
    var area = width * height;
    return area;
}
```

## 6.2. Formatted Printing (printf)

#### Versionadded
Added in version 0.1.1: Wrench includes native `printf` format string processing. Format strings support interpolated variable names inside curly braces (e.g., `{name}`) as well as format specifier shortcuts.

Format specifier shortcuts include:
\* **\`\`x\`\` / \`\`X\`\`:** Format value as hexadecimal address or integer.
\* **\`\`d\`\` / \`\`i\`\`:** Format value as integer.
\* **\`\`f\`\`:** Format value as double / float.
\* **\`\`s\`\`:** Format value as string.
\* **\`\`c\`\`:** Format value as character.

```text
var x = 255;
printf("Value: {x:x}\n"); // Displays hex format 0xFF
```

## 6.3. Anonymous Functions (anfunc)

Wrench supports anonymous functions via the `anfunc` keyword. Anonymous functions do not have a name and are typically assigned to variables. This allows functions to be passed around dynamically as pointers.

```text
var add_numbers = anfunc(int a, int b) {
    return a + b;
};

var result = add_numbers(15, 25); // Evaluates to 40;
```

## 6.4. External Functions (extern)

Because Wrench compiles directly to Assembly and conforms to standard binary interfaces, you can easily link it with external libraries (like C standard libraries or custom Assembly files).

Use the `extern` modifier before `define` to declare a function that exists outside the current codebase. External definitions do not have a code block and must end with a semicolon.

```text
extern define printf(str format, var value) -> unit;
```

## 6.5. System V ABI & Calling Convention

At the hardware level, Wrench strictly adheres to the **System V AMD64 ABI** calling convention for x86-64 architectures.

When a function is called, the compiler automatically distributes the arguments according to this standard:
1. The first 6 arguments are loaded directly into CPU registers for maximum performance (`rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`).
2. If a function receives more than 6 arguments, the remaining arguments are automatically pushed onto the stack before the function is called.

This native compliance ensures that Wrench can seamlessly interoperate with C libraries and OS kernel structures without requiring bridging layers or wrappers.

#### NOTE
**Roadmap / Cross-Platform Support:** Currently, the compiler’s backend strictly targets the Linux System V ABI. Implementations for the Windows x64 ABI (which utilizes different parameter registers and requires a 32-byte shadow space) and MacOS architectures are scheduled for future minor releases.

<a id="reference-oop"></a>

# 7. Object-Oriented Programming (OOP)

Wrench provides a class-based Object-Oriented Programming (OOP) model. Unlike managed languages, Wrench’s OOP operates directly on raw memory. Objects are essentially structured memory blocks, and methods are standard functions that receive a hidden pointer to the object instance.

## 7.1. Class Definition & Instantiation

Classes are defined using the `class` keyword. Inside a class, you can declare fields (variables) and methods (using the `define` keyword). The `init` method acts as the constructor and is called automatically when an object is created.

To instantiate an object, use the `new` keyword. This automatically allocates the exact amount of memory required for the object’s fields via the kernel and invokes the `init` method.

```text
class Player {
    int health;
    int level;

    define init(int initial_health) {
        this.health = initial_health;
        this.level = 1;
    }
}

var p1 = new Player(100);
```

## 7.2. Inheritance (extends)

Wrench supports single inheritance using the `extends` keyword. A child class inherits all fields and methods of its parent class, and the memory layout is sequentially expanded.

```text
class Character {
    int health;
}

class Npc extends Character {
    int aggression_level;
}
```

## 7.3. Access Modifiers (public & private)

Fields and methods can be prefixed with access modifiers to control visibility. By default, members are `public`.

If a member is marked as `private`, the compiler strictly enforces access rules during the Semantic Analysis phase, preventing any external reads, writes, or method calls.

```text
class Vault {
    private int secret_code;

    public define unlock() {
        // Accessing private members internally is allowed
        if (this.secret_code =? 1234) {
            print("Unlocked;");
        }
    }
}
```

## 7.4. The ‘this’ Keyword

Inside any class method, the `this` keyword is automatically available. It acts as a pointer to the current instance of the object. Under the hood (following the System V ABI), `this` is implicitly passed as the very first argument (`rdi` register) to the method.

## 7.5. Type Casting (Upcasting & Downcasting)

Wrench’s strict semantic analyzer ensures object type safety but allows hierarchical type conversions using the `cast` keyword.

* **Upcasting:** Converting a child object to a parent type. This is implicitly allowed by the compiler but can also be done explicitly.
* **Downcasting:** Converting a parent reference back to a child type. This requires an explicit `cast`.

```text
var main_player = new Player(100);
main_player.level = 25;

Character npc = main_player; // Implicit UPCAST
var reverted_player = npc cast Player; // Explicit DOWNCAST

print_int(reverted_player.level); // Prints 25;
```

<a id="reference-error-handling"></a>

# 8. Error Handling & Signals

Because Wrench lacks a Virtual Machine and background runtime, it implements error handling directly at the hardware and operating system level. It intercepts hardware faults (like Segmentation Faults) using OS-level signal handlers (`rt_sigaction`) and routes them to user-defined fallback blocks by restoring previous stack frames.

## 8.1. Attempt, Exclude, and Final

* **\`\`attempt\`\`:** The block of code to be executed safely. Before entering, the compiler pushes the current CPU state (RSP, RBP, and the fallback address) to a linked list known as the Global Error Frame.
* **\`\`exclude\`\`:** The fallback block executed if an error occurs. When a fault is intercepted, the compiler injects an implicit local variable named `err` (containing the error code) into this block’s scope.
* **\`\`final\`\`:** A block that is guaranteed to run regardless of whether an error occurred or not.

```text
attempt {
    var arr = limits(0, 5);
    print_int(arr[10]); // Triggers an Out-of-Bounds memory fault
} exclude {
    print("Intercepted an error! Code: ");
    print_int(err); // Prints the hardware fault code (99)
} final {
    print("Execution completed;");
}
```

If an `exclude` block is omitted and an error occurs, the compiler executes the `final` block and automatically “bubbles up” the error to the next higher `attempt` frame.

## 8.2. Triggering Errors (trigger & allege)

Developers can manually invoke the error-handling mechanism using two keywords:

* **\`\`trigger\`\`:** Immediately halts the current execution and throws a specific error code. The error code is caught by the nearest `exclude` block.
* **\`\`allege\`\`:** Acts as an assertion. It evaluates a condition; if the condition is false, it automatically triggers a predefined assertion error (Error Code: 1).

```text
allege x > 0; // Throws Error 1 if x is less than or equal to 0

if (status != 200) {
    trigger 404; // Throws a custom error code
}
```

## 8.3. Hardware-Level Fault Interception

In standard C or C++, accessing an invalid memory address (e.g., an array out-of-bounds or a null pointer) causes the OS to terminate the program immediately with a Segmentation Fault (SIGSEGV).

In Wrench, the compiler registers a custom signal handler (using Syscall 13) at startup. If a memory violation occurs (such as the Array Out of Bounds check failing and throwing code 99), the OS hands control over to Wrench’s internal `sigsegv_handler`. The handler reads the Global Error Frame, unwinds the stack registers back to their safe state, and jumps directly into the user’s `exclude` block without crashing the application.

<a id="reference-concurrency"></a>

# 9. Concurrency & Interrupts

Wrench avoids the complexity of user-space threading (like standard pthreads) and instead relies on true OS-level multi-processing. Concurrency is achieved natively by utilizing the kernel’s process duplication mechanism (`fork`) and process waiting rules.

## 9.1. Asynchronous Execution (async & wait/await)

Functions can be marked with the `async` modifier. When an asynchronous function is called, the Wrench compiler invokes the kernel to fork a new child process. The child process executes the function’s code in parallel, while the parent process immediately continues to the next line of code without blocking.

To pause the parent process and wait for a specific parallel task to finish, use the `wait` or `await` operators. These operators invoke the kernel (Syscall 61) to suspend the parent process until the child process completes its execution.

```text
async define heavy_computation(int x) {
    // ... intensive work ...
}

var process_id = heavy_computation(100);
print("This prints immediately;");

await process_id; // Parent pauses here until the computation is done
print("This prints after the computation finishes;");
```

## 9.2. Synchronization Units (sync unit & with)

Wrench provides a unique mechanism for grouping code blocks that need to run concurrently or sequentially, known as Synchronization Units.

* **\`\`sync unit\`\`:** Defines a named block of code. It does not execute immediately; it merely registers the code block.
* **\`\`with\`\`:** Executes a predefined unit. By default, calling `with` runs the unit asynchronously (forking a new process). If you use `wait with`, the unit executes synchronously in the current process.

```text
sync unit download_data {
    // ... network operations ...
}

with download_data {
    print("Data download started in the background;");
}

wait with download_data {
    print("This runs synchronously after the unit completes;");
}
```

## 9.3. Event-Driven Observers (when & global when)

Wrench introduces an interrupt-like polling architecture using the `when` keyword.

A `when` block acts as a background observer. Once declared, the compiler forks a lightweight child process that immediately enters a sleep state (using `nanosleep`). It wakes up every 10 milliseconds to evaluate its condition. If the condition becomes true, the process executes the internal block and then terminates safely.

* **\`\`when\`\`:** Observes variables within the current local scope.
* **\`\`global when\`\`:** Escalates the observer to the highest hierarchy, allowing it to continuously monitor global application state regardless of the current local scope.

```text
var ready = false;

when (ready =? true) {
    print("The system is now ready!;");
}

// ... other code ...
ready = true; // The background observer wakes up, detects the change, and prints.
```

<a id="reference-modules"></a>

# 10. Modules & Linker

Wrench supports modular programming by allowing you to split your code into multiple `.wr` files. The compiler’s frontend resolves all imports, merges the Abstract Syntax Trees (AST) prior to semantic analysis, and handles external object linking natively.

## 10.1. Importing Modules (include)

To import an entire Wrench module, use the `include` keyword followed by the file name (as a string). The compiler automatically appends the `.wr` extension if it is omitted.

If a module name starts with `std/`, the compiler looks for it in the standard library directory. Otherwise, it searches relative to the current working directory.

```text
include "math_utils"; // Imports math_utils.wr from the current directory
include "std/sys";     // Imports sys.wr from the standard library
```

## 10.2. Selective Imports & Aliasing (from … include … as)

If you only need a specific function, class, or variable from another module, use the `from ... include` syntax. This prevents the entire module from polluting your global scope.

You can also rename the imported item locally using the `as` keyword to prevent naming collisions.

```text
from "math_utils" include calculate_area;

from "std/crypto" include hash_password as bcrypt_hash;
var secure_pass = bcrypt_hash("my_secret");
```

## 10.3. Linking External Object Files (link)

Wrench is designed to interoperate directly with compiled binaries from other languages (like C, C++, or raw Assembly). You can instruct the Wrench compiler to pass specific object files (`.o`) to the GNU Linker (`ld`) during the final compilation stage using the `link` keyword.

```text
link "external_physics_engine.o";
extern define apply_gravity(ptr object); // Declared in the .o file
```

When the Wrench CLI compiles this file, it gathers all `link` directives and appends them to the final linker command, ensuring the external machine code is seamlessly merged into the final executable.
