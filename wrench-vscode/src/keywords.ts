export interface SymbolMeta {
    name: string;
    detail: string;
    description: string;
    snippet?: string;
    returnType?: string;
}

export const CONTROL_KEYWORDS: Record<string, SymbolMeta> = {
    "if": { name: "if", detail: "Condition Block", description: "Executes the block if the specified condition is true." },
    "else": { name: "else", detail: "Default Condition Block", description: "Runs when no condition is met." },
    "butif": { name: "butif", detail: "Alternative Condition Block", description: "Additional condition to run if the previous if/butif fails." },
    "while": { name: "while", detail: "Conditional Loop", description: "Runs as long as the condition is true." },
    "for": { name: "for", detail: "Element Loop", description: "Allows iterating over a collection or array." },
    "limits": { name: "limits", detail: "Range Generator", description: "Generates an array between start and end values." },
    "in": { name: "in", detail: "Loop Operator", description: "Specifies the iteration source in a for loop." },
    "switch": { name: "switch", detail: "Multi-Condition Block", description: "Provides branching based on a value." },
    "case": { name: "case", detail: "Switch Case", description: "A single matching state inside a switch." },
    "default": { name: "default", detail: "Default Switch State", description: "State that runs when there is no match." },
    "break": { name: "break", detail: "Loop/Switch Breaker", description: "Terminates the current loop or switch." },
    "goon": { name: "goon", detail: "Loop Continuer", description: "Skips to the next step of the loop (continue)." },
    "when": { name: "when", detail: "Reactive Wait Block", description: "Waits in the background until the specified condition is met." },
    "with": { name: "with", detail: "Sync Unit Caller", description: "Executes a synchronous module or unit block." },
    "attempt": { name: "attempt", detail: "Error Handling Block", description: "Starts a code block where an error might occur (try)." },
    "exclude": { name: "exclude", detail: "Error Catcher", description: "Catches the error occurring within an attempt (catch)." },
    "final": { name: "final", detail: "Final Block", description: "Closing block that runs whether there is an error or not (finally)." },
    "trigger": { name: "trigger", detail: "Error Trigger", description: "Triggers a runtime error (throw)." },
    "allege": { name: "allege", detail: "Assertion", description: "Throws a runtime error if the condition is false." }
};

export const DECLARATION_KEYWORDS: Record<string, SymbolMeta> = {
    "define": { name: "define", detail: "Function Definition", description: "Defines a free or class-internal function." },
    "class": { name: "class", detail: "Class Definition", description: "Creates a new object template and data structure." },
    "extends": { name: "extends", detail: "Class Inheritance", description: "Allows inheriting from a superclass." },
    "extern": { name: "extern", detail: "External Symbol", description: "Externally linked assembly or C symbol." },
    "include": { name: "include", detail: "Module Import", description: "Includes a Wrench file or library." },
    "from": { name: "from", detail: "Module Source", description: "Specifies the source when selecting specific symbols with include." },
    "link": { name: "link", detail: "Object Linker", description: "Links an external .o/.a object file during compilation." },
    "global": { name: "global", detail: "Global Variable", description: "Defines a variable accessible at the module level." },
    "anfunc": { name: "anfunc", detail: "Anonymous Function", description: "Generates an anonymous lambda or callback function." },
    "public": { name: "public", detail: "Public Access", description: "Allows external access to a class member." },
    "private": { name: "private", detail: "Private Access", description: "Encapsulates a class member strictly within the class." },
    "async": { name: "async", detail: "Asynchronous Function", description: "Defines a function to run in the background (fork)." },
    "sync": { name: "sync", detail: "Synchronous Unit", description: "Creates a locked or synchronized code block." },
    "return": { name: "return", detail: "Return", description: "Returns a value from the function and exits." },
    "delete": { name: "delete", detail: "Memory Deleter", description: "Frees the object or address allocated on the heap." }
};

export const OPERATOR_KEYWORDS: Record<string, SymbolMeta> = {
    "and": { name: "and", detail: "Logical AND", description: "Returns true if both conditions are true." },
    "or": { name: "or", detail: "Logical OR", description: "Returns true if one of the conditions is true." },
    "not": { name: "not", detail: "Logical NOT", description: "Takes the opposite of the condition." },
    "nand": { name: "nand", detail: "NAND", description: "Opposite of the AND result." },
    "nor": { name: "nor", detail: "NOR", description: "Opposite of the OR result." },
    "xor": { name: "xor", detail: "Exclusive OR", description: "Returns true for different logical values." },
    "xnor": { name: "xnor", detail: "Exclusive NOR", description: "Returns true for identical logical values." },
    "is": { name: "is", detail: "Equality Operator", description: "Checks the equality of two values (=?)." },
    "same": { name: "same", detail: "Strict Equality", description: "Checks type and value equality." },
    "as": { name: "as", detail: "Type Conversion", description: "Converts a variable to the target type." },
    "cast": { name: "cast", detail: "Explicit Cast", description: "Performs explicit type conversion (expr cast type)." },
    "await": { name: "await", detail: "Process Awaiting", description: "Awaits the completion of an asynchronous process." },
    "wait": { name: "wait", detail: "Process Wait", description: "Waits for the completion of an asynchronous sub-process." },
    "new": { name: "new", detail: "Object Creator", description: "Allocates new memory from the class and calls init." }
};

export const VALUE_KEYWORDS: Record<string, SymbolMeta> = {
    "true": { name: "true", detail: "Logical True", description: "1 / True value." },
    "false": { name: "false", detail: "Logical False", description: "0 / False value." },
    "null": { name: "null", detail: "Null Pointer", description: "Zero address or invalid reference." },
    "this": { name: "this", detail: "Current Object", description: "Accesses the instance of the class from within a method." }
};

export const DATA_TYPES: Record<string, SymbolMeta> = {
    "int": { name: "int", detail: "64-bit Signed Integer", description: "Integer type (8 bytes)." },
    "integer": { name: "integer", detail: "64-bit Integer", description: "Alternative type name for int." },
    "double": { name: "double", detail: "64-bit Floating Point", description: "Double precision float." },
    "char": { name: "char", detail: "Character Type", description: "Single-byte character or ASCII value." },
    "str": { name: "str", detail: "String Type", description: "String type alias." },
    "string": { name: "string", detail: "String Type", description: "Null-terminated string type." },
    "bool": { name: "bool", detail: "Boolean Type", description: "Type holding true or false." },
    "var": { name: "var", detail: "Generic / Dynamic Type", description: "General variable type with type inference." },
    "unit": { name: "unit", detail: "Void Return Type", description: "Function type that does not return a value." },
    "hex": { name: "hex", detail: "Hexadecimal Type", description: "Base-16 pointer or number type." },
    "ptr": { name: "ptr", detail: "Pointer", description: "Type holding a memory address." },
    "pointer": { name: "pointer", detail: "Pointer Type", description: "Alternative name for ptr." },
    "address": { name: "address", detail: "Memory Address", description: "Raw memory addressing type." }
};

export const BUILTIN_FUNCTIONS: Record<string, SymbolMeta> = {
    "print": { name: "print", detail: "builtin print(val)", description: "Prints data to the screen.", returnType: "unit" },
    "printf": { name: "printf", detail: "builtin printf(fmt, ...)", description: "Prints a formatted string.", returnType: "unit" },
    "print_float": { name: "print_float", detail: "builtin print_float(val)", description: "Prints a float/double value to the screen.", returnType: "unit" },
    "print_hex": { name: "print_hex", detail: "builtin print_hex(val)", description: "Writes an address or value in hexadecimal format.", returnType: "unit" },
    "read": { name: "read", detail: "builtin read(buf_size) -> string", description: "Reads the input written to the screen as a string.", returnType: "string" },
    "read_int": { name: "read_int", detail: "builtin read_int() -> int", description: "Reads an integer from standard input.", returnType: "int" },
    "len": { name: "len", detail: "builtin len(arr_or_str) -> int", description: "Returns the length of the array or string.", returnType: "int" },
    "type_of": { name: "type_of", detail: "builtin type_of(val) -> string", description: "Returns the type name of the expression as a string.", returnType: "string" },
    "alloc": { name: "alloc", detail: "builtin alloc(bytes) -> ptr", description: "Allocates memory of the specified size on the heap.", returnType: "ptr" },
    "realloc": { name: "realloc", detail: "builtin realloc(ptr, new_bytes) -> ptr", description: "Resizes the allocated memory.", returnType: "ptr" },
    "free": { name: "free", detail: "builtin free(ptr)", description: "Frees the memory allocated on the heap.", returnType: "unit" },
    "str_ndup": { name: "str_ndup", detail: "builtin str_ndup(ptr, len) -> string", description: "Copies a string of a specified length from a memory address.", returnType: "string" },
    "get_mem": { name: "get_mem", detail: "builtin get_mem(ptr, offset) -> int", description: "Reads a 64-bit memory area.", returnType: "int" },
    "get_mem32": { name: "get_mem32", detail: "builtin get_mem32(ptr, offset) -> int", description: "Reads a 32-bit memory area.", returnType: "int" },
    "addr_of": { name: "addr_of", detail: "builtin addr_of(var) -> ptr", description: "Returns the memory address of the variable or symbol.", returnType: "ptr" },
    "ptr_to": { name: "ptr_to", detail: "builtin ptr_to(val) -> ptr", description: "Creates a pointer to the value.", returnType: "ptr" },
    "sys_argc": { name: "sys_argc", detail: "builtin sys_argc() -> int", description: "Returns the number of command line arguments.", returnType: "int" },
    "sys_argv": { name: "sys_argv", detail: "builtin sys_argv(index) -> string", description: "Returns the command line argument at the specified index.", returnType: "string" },
    "syscall": { name: "syscall", detail: "builtin syscall(sys_num, ...) -> int", description: "Directly executes a Linux x86-64 system call.", returnType: "int" },
    "exit": { name: "exit", detail: "builtin exit(code)", description: "Terminates the program with the specified exit code.", returnType: "unit" }
};

export const ASSIGNMENT_OPERATORS: Record<string, SymbolMeta> = {
    "=": { name: "=", detail: "Assignment Operator", description: "Assigns value to variable or field." },
    "+=": { name: "+=", detail: "Add and Assign", description: "Adds right operand to variable and assigns result." },
    "=+": { name: "=+", detail: "Add and Assign Alias", description: "Adds right operand to variable and assigns result." },
    "-=": { name: "-=", detail: "Subtract and Assign", description: "Subtracts right operand from variable and assigns result." },
    "=-": { name: "=-", detail: "Subtract and Assign Alias", description: "Subtracts right operand from variable and assigns result." },
    "*=": { name: "*=", detail: "Multiply and Assign", description: "Multiplies variable by right operand and assigns result." },
    "=*": { name: "=*", detail: "Multiply and Assign Alias", description: "Multiplies variable by right operand and assigns result." },
    "/=": { name: "/=", detail: "Divide and Assign", description: "Divides variable by right operand and assigns result." },
    "=/": { name: "=/", detail: "Divide and Assign Alias", description: "Divides variable by right operand and assigns result." },
    "%=": { name: "%=", detail: "Modulus and Assign", description: "Computes modulus of variable by right operand and assigns result." },
    "=%": { name: "=%", detail: "Modulus and Assign Alias", description: "Computes modulus of variable by right operand and assigns result." },
    "^=": { name: "^=", detail: "Power and Assign", description: "Raises variable to power of right operand and assigns result." },
    "=^": { name: "=^", detail: "Power and Assign Alias", description: "Raises variable to power of right operand and assigns result." }
};

export const COMPARISON_OPERATORS: Record<string, SymbolMeta> = {
    "=?": { name: "=?", detail: "Equality Check", description: "Checks if left operand is equal to right operand." },
    "?=": { name: "?=", detail: "Equality Check Alias", description: "Checks if left operand is equal to right operand." },
    "!=": { name: "!=", detail: "Inequality Check", description: "Checks if left operand is not equal to right operand." },
    "=!": { name: "=!", detail: "Inequality Check Alias", description: "Checks if left operand is not equal to right operand." },
    ">=": { name: ">=", detail: "Greater Than or Equal", description: "Checks if left operand is greater than or equal to right operand." },
    "=>": { name: "=>", detail: "Greater Than or Equal Alias", description: "Checks if left operand is greater than or equal to right operand." },
    "<=": { name: "<=", detail: "Less Than or Equal", description: "Checks if left operand is less than or equal to right operand." },
    "=<": { name: "=<", detail: "Less Than or Equal Alias", description: "Checks if left operand is less than or equal to right operand." },
    "<": { name: "<", detail: "Less Than", description: "Checks if left operand is less than right operand." },
    ">": { name: ">", detail: "Greater Than", description: "Checks if left operand is greater than right operand." }
};

export const ARITHMETIC_OPERATORS: Record<string, SymbolMeta> = {
    "+": { name: "+", detail: "Addition / Concatenation", description: "Adds numbers or concatenates strings." },
    "-": { name: "-", detail: "Subtraction / Negation", description: "Subtracts right operand from left or negates number." },
    "*": { name: "*", detail: "Multiplication", description: "Multiplies two numbers." },
    "/": { name: "/", detail: "Division", description: "Divides left operand by right operand." },
    "%": { name: "%", detail: "Modulus", description: "Computes remainder of integer division." },
    "^": { name: "^", detail: "Exponentiation", description: "Raises left operand to power of right operand." }
};

export const PUNCTUATION_SYMBOLS: Record<string, SymbolMeta> = {
    "->": { name: "->", detail: "Return Type Arrow", description: "Specifies return type in function declarations." },
    ":": { name: ":", detail: "Colon Separator", description: "Used in type annotations or format specifiers." },
    ";": { name: ";", detail: "Semicolon Terminator", description: "Terminates statements." },
    ",": { name: ",", detail: "Comma Separator", description: "Separates arguments or elements." },
    ".": { name: ".", detail: "Member Access", description: "Accesses fields or methods of an object." }
};

export const ALL_KEYWORDS: Record<string, SymbolMeta> = {
    ...CONTROL_KEYWORDS,
    ...DECLARATION_KEYWORDS,
    ...OPERATOR_KEYWORDS,
    ...VALUE_KEYWORDS
};

export const ALL_OPERATORS: Record<string, SymbolMeta> = {
    ...ASSIGNMENT_OPERATORS,
    ...COMPARISON_OPERATORS,
    ...ARITHMETIC_OPERATORS,
    ...OPERATOR_KEYWORDS
};

export const ALL_SYMBOLS: Record<string, SymbolMeta> = {
    ...ALL_KEYWORDS,
    ...DATA_TYPES,
    ...BUILTIN_FUNCTIONS,
    ...ASSIGNMENT_OPERATORS,
    ...COMPARISON_OPERATORS,
    ...ARITHMETIC_OPERATORS,
    ...PUNCTUATION_SYMBOLS
};