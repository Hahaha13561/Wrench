<a id="stdlib-main"></a>

# Wrench Standard Library

The Wrench Standard Library provides essential built-in modules for data structures, system operations, file I/O, process execution, pattern matching, mathematical calculations, and low-level memory utilities.

#### Versionchanged
Changed in version 0.1.1: All standard library functions and methods have been updated with explicit return type annotations (`-> ReturnType`). Internal embedded test suites were stripped from all library source files to optimize compilation size.

## 1. Collections (collections.wr)

The `collections.wr` module provides dynamic data structures: `List` and `Map`. Since Wrench does not have a Garbage Collector, both structures require explicit memory cleanup using their respective `destroy()` methods.

### 1.1. List

A dynamically resizing array structure.

* **init()**: Initializes the list and allocates raw memory.
* **push(var item)**: Adds an element to the end of the list.
* **get(int index) -> any**: Returns the item at the specified index. Throws Out Of Bounds Error (Code 99) if invalid.
* **set(int index, var item)**: Updates the value at the specified index.
* **pop() -> any**: Removes and returns the last item in the list.
* **clear()**: Deletes the underlying memory and resets the list state.
* **destroy()**: Frees the raw memory allocated for the list’s data.

```text
include "std/collections.wr";

var my_list = new List();
my_list.push(10);
my_list.push(20);
print_int(my_list.get(1) cast int); // Prints 20

my_list.destroy();
delete my_list;
```

### 1.2. Map

A key-value dictionary structure operating on dual parallel lists.

* **init()**: Initializes internal storage lists.
* **set(str key, var value) -> int**: Adds or updates a key-value pair.
* **get(str key) -> any**: Returns the value associated with the key.
* **has(str key) -> bool**: Returns `true` if the key exists in the map, otherwise `false`.
* **destroy()**: Frees internal key and value lists.

## 2. Error Management (error.wr)

Provides a hierarchical exception and error handling system built upon `BaseException` and branching into `Exception`, `FatalError`, and `Warning`.

### 2.1. The Root Class

* **BaseException**: Base error class initialized with a `message` and `code`. Provides `print_err()`.

### 2.2. Main Branch 1: Exception

Standard run-time errors including `ArithmeticError`, `LookupError` (`IndexError`, `KeyError`), `NameError`, `ValueError`, `SyntaxError`, `OSError` (`FileNotFoundError`, `PermissionError`, `FileExistsError`), `TypeError`, and `RuntimeError`.

### 2.3. Main Branch 2: FatalError

Critical system failures carrying a `fault_addr` hex property, including `SystemExit`, `KeyboardInterrupt`, `GeneratorExit`, `MemoryError`, `SystemError`, and `RecursionError`.

### 2.4. Main Branch 3: Warning

Non-fatal alerts including `DeprecationWarning`, `UserWarning`, `SyntaxWarning`, and `RuntimeWarning`.

## 3. File System (fs.wr)

Handles file and directory operations using direct OS kernel calls.

### 3.1. The File Class

* **init(str file_path)**: Opens file in read-only mode, measures size via `sys_lseek`, and loads contents into memory.
* **read() -> str**: Returns loaded file content.
* **close()**: Closes file descriptor and frees the allocated buffer.

### 3.2. File Operations

* **write_file(str file_path, str content) -> bool**: Overwrites file with content.
* **append_file(str file_path, str content) -> bool**: Appends content to file end.
* **delete_file(str file_path) -> bool**: Unlinks file from filesystem.

### 3.3. Directory Operations

* **dir_list(str dir_path) -> List**: Reads directory structure using kernel dirent syscalls and returns a `List` of filenames.

## 4. Math (math.wr)

Provides mathematical constants, trigonometry, logarithms, rounding, and PRNG.

### 4.1. Core Functions

* **rad_to_deg(double rad) -> double** / **deg_to_rad(double deg) -> double**: Angle conversion.
* **sin(double x) -> double** / **cos(double x) -> double** / **tan(double x) -> double**: Trigonometry.
* **asin(double x) -> double** / **acos(double x) -> double** / **atan2(double y, double x) -> double**: Inverse trigonometry.
* **pow(double base, double exp) -> double** / **sqrt(double x) -> double** / **cbrt(double x) -> double**: Powers and roots.
* **log(double x) -> double** / **log10(double x) -> double** / **log2(double x) -> double**: Logarithms.
* **num_abs(var x) -> any** / **fabs(double x) -> double**: Absolute values.
* **floor(double x) -> double** / **ceil(double x) -> double** / **round(double x) -> double**: Rounding.
* **rand() -> int** / **rand_range(int min_val, int max_val) -> int** / **rand_float() -> double**: Pseudo-random generation.
* **dist2d(double x1, double y1, double x2, double y2) -> double**: 2D Euclidean distance.

## 5. String (string.wr)

Provides string manipulation routines.

* **str_len(str text) -> int**: Returns string character count.
* **substring(str text, int start, int end) -> str**: Returns extracted substring.
* **uppercase(str text) -> str** / **lowercase(str text) -> str**: ASCII casing conversions.
* **split(str text, char delimeter) -> var**: Splits string into array by delimiter.
* **parse_int(str text) -> int**: Converts string to integer.
* **to_string(int number) -> str**: Converts integer to string.
* **concat(str left, str right) -> str**: Concatenates two strings.

## 6. System (sys.wr)

#### Versionchanged
Changed in version 0.1.1: Restructured around a centralized `SysModule` instance named `sys`.

* **sys.argv**: List of CLI arguments.
* **sys.platform**: String identifier for running platform (e.g., `"linux"`).
* **sys.exit(int code)**: Terminates execution with given status code.
* **sys.getsizeof(var obj) -> int**: Calculates allocated byte size of an object or memory buffer.
* **args() -> List**: Legacy wrapper returning CLI argument list.
* **execute(str program, List cmd_args) -> int**: Forks and executes an external binary.

```text
include "std/sys.wr";

print(sys.argv.get(0) cast str);
if (sys.argv.length < 2) {
    sys.exit(1);
}
```

## 7. Time (time.wr)

* **now() -> int**: Returns UNIX epoch time in seconds.
* **now_ms() -> int**: Returns epoch time in milliseconds.
* **ticks() -> int**: Returns monotonic clock milliseconds.
* **sleep(int ms) -> int**: Pauses process execution for specified duration.
* **measure(var func_ptr) -> int**: Profiles execution time of target function pointer in milliseconds.
* **epoch_to_utc(int epoch) -> var**: Converts epoch to `[year, month, day, hr, min, sec]` array.
* **now_utc() -> var**: Returns current UTC date/time array.

## 8. Argument Parser (argparser.wr)

#### Versionadded
Added in version 0.1.1: Provides CLI command line argument definition and sub-command parsing.

### 8.1. Argument & ArgumentParser Classes

* **ArgumentParser.init(str desc)**: Creates parser instance.
* **add_argument(str name, str arg_type, str action)**: Defines expected flag or positional parameter (actions: `"store"`, `"store_true"`, `"count"`).
* **add_subparsers(str command_name, str desc) -> ArgumentParser**: Adds sub-command parser.
* **parse_args(List sys_args) -> Map**: Parses argument list and returns a `Map` containing options.
* **destroy()**: Frees internal arguments and subparser structures.

```text
include "std/argparser.wr";

var parser = new ArgumentParser("Wrench CLI Tool");
parser.add_argument("-v", "bool", "store_true");
parser.add_argument("-o", "str", "store");

var opts = parser.parse_args(sys.argv);
```

## 9. Memory Cloning (clone.wr)

#### Versionadded
Added in version 0.1.1: Provides raw memory duplication, filling, and array element swapping.

### 9.1. CloneModule Class (clone)

* **clone.clone_mem(var dest, var src, int count)**: Copies `count` bytes from source to destination address.
* **clone.fill(var target, int value, int count)**: Sets target memory buffer bytes to `value`.
* **clone.swap_arr(var arr, int i, int j)**: Swaps elements at indices `i` and `j`.
* **clone.clone(var obj) -> var**: Reads object size via hidden header and returns a newly allocated duplicate clone in heap memory.

## 10. Operating System (os.wr)

#### Versionadded
Added in version 0.1.1: Provides system path management, current directory querying, environment inspection, and OS error mapping.

### 10.1. PathModule Class (os.path)

* **os.path.join(str p1, str p2) -> str**: Joins path components with directory separators.
* **os.path.dirname(str p) -> str**: Extracts directory component of a path.
* **os.path.normpath(str p) -> str**: Resolves `.` and `..` relative path components.
* **os.path.exists(str p) -> bool**: Checks if path exists on file system via kernel access check.
* **os.path.abspath(str p) -> str**: Resolves path into an absolute file system path.

### 10.2. OSModule Class (os)

* **os.getcwd() -> str**: Queries current working directory path via Syscall 79 (`getcwd`).
* **os.remove(str p) -> bool**: Unlinks file path.
* **os.rmdir(str p) -> bool**: Removes directory path.
* **os.makedirs(str p, bool exist_ok)**: Recursively creates path directory tree.
* **os.access(str p, int mode) -> bool**: Verifies file permission access flags.
* **os.getenv(str key) -> str**: Searches process environment variables for key value.

```text
include "std/os.wr";

var cwd = os.getcwd();
var config_path = os.path.join(cwd, "config.json");

if (os.path.exists(config_path)) {
    var user = os.getenv("USER");
}
```

## 11. Regular Expressions (regex.wr)

#### Versionadded
Added in version 0.1.1: Provides regular expression pattern searching, matching, and text substitution.

* **compile(str pattern) -> RegexPattern**: Compiles regular expression pattern string.
* **match(str pattern, str text) -> str**: Tests match at string head.
* **finditer(str pattern, str text) -> List**: Scans text and returns a `List` of matching substrings.
* **split(str pattern, str text) -> List**: Splits text into a `List` using pattern matches as delimiters.
* **sub(str pattern, str repl, str text) -> str**: Replaces matches in text with replacement string.

## 12. Subprocess Management (subprocess.wr)

#### Versionadded
Added in version 0.1.1: Provides child process spawning, process I/O pipe redirection, signal handling, and execution waiting.

### 12.1. Classes and Global Functions

* **CompletedProcess**: Process execution snapshot containing `cmd`, `returncode`, `stdout`, `stderr`, and merged `output`.
* **Popen.poll() -> int**: Non-blocking status check on child process PID.
* **Popen.wait_proc(int timeout_ms) -> int**: Waits for process completion or sends `SIGKILL` (-9) if timeout expires.
* **Popen.communicate() -> CompletedProcess**: Reads output pipes, closes file descriptors, waits for termination, and returns process summary.
* **run(var cmd_array, bool capture_output, int timeout_ms) -> CompletedProcess**: Spawns process using kernel `fork` (Syscall 57) and `execve` (Syscall 59), handling pipe creation (Syscall 22) and duplication (Syscall 33).

```text
include "std/subprocess.wr";

var cmd = ["/bin/ls", "-la"];
CompletedProcess proc = run(cmd, true, 5000);

if (proc.returncode =? 0) {
    print(proc.stdout);
}
```
