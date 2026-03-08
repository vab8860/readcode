# ReadCode v0.1 Release

**Release Date:** March 8, 2026  
**Version:** 0.1.0  

## Overview

ReadCode v0.1 is the initial release of a simple, human-readable programming language designed to remove the barrier between humans and computers. This version provides the core language features with a clean, English-like syntax.

## Features

### Core Language Features
- **Variable Assignment**: `set age to 18`
- **Output**: `show hello world`
- **Conditional Logic**: `if the age is 18 ... else ... and end`
- **Loops**: `repeat 5 times ... and end`
- **Task Definitions**: `task greet ... and end`
- **Task Execution**: `do greet`

### Data Types
- Numbers (integers): `42`, `-7`
- Strings: `"hello world"` (quoted) or unquoted identifiers
- Variables: Simple name-based references

### Error Handling
- Line-numbered syntax errors
- Clear runtime error messages
- Graceful handling of unknown variables (treated as strings)

## Installation & Setup

### Prerequisites
- Python 3.7 or higher

### Quick Start
```bash
git clone https://github.com/vab8860/readcode.git
cd readcode
python run.py examples/hello.read
```

## Example Programs

### Hello World
```readcode
set age to 18
show "hello" "world"

if the age is 18 ...
  show you are adult
else ...
  show you are minor
and end

repeat 5 times ...
  show hello
and end

task greet ...
  show hello world
and end

do greet
```

### Calculator Example
```readcode
set a to 10
set b to 5
show "a =" a

if the a is 10 ...
  show a is correct
else ...
  show a is wrong
and end
```

## Project Structure
```
readcode/
├── run.py          # CLI entry point
├── lexer.py        # Tokenizes source code
├── parser.py       # Builds AST from tokens  
├── executor.py     # Executes AST
├── examples/       # Example programs
│   ├── hello.read
│   ├── calculator.read
│   ├── greet.read
│   └── countdown.read
└── docs/
    └── grammar.md   # Formal grammar
```

## Language Grammar

The language follows a simple, line-oriented grammar:

```
program        := statement*
statement      := set_stmt | show_stmt | if_stmt | repeat_stmt | task_def | do_stmt
set_stmt       := "set" IDENT "to" expr
show_stmt      := "show" expr+
if_stmt        := "if" "the" IDENT "is" expr "..." block "and" "end" ["else" "..." block "and" "end"]
repeat_stmt    := "repeat" expr "times" "..." block "and" "end"
task_def       := "task" IDENT "..." block "and" "end"
do_stmt        := "do" IDENT
block          := statement*
expr           := STRING | NUMBER | IDENT
```

## Known Limitations

### Current Constraints
- No arithmetic operations (addition, subtraction, etc.)
- No user input capabilities
- No file I/O operations
- No array/list data structures
- Single-token expressions only
- No string manipulation functions

### Intentional Design Decisions
- Line-oriented syntax for simplicity
- Minimal keywords to reduce cognitive load
- Unknown identifiers treated as strings for flexibility
- No complex data types to maintain simplicity

## Future Roadmap

### v0.2 (Next Release)
- [ ] ELSE clause support (completed)
- [ ] Enhanced test examples
- [ ] Improved error messages

### v0.3
- [ ] Basic arithmetic operations
- [ ] User input with `ask` statement
- [ ] String operations (`concat`, `length`)
- [ ] Comparison operators (`greater than`, `less than`)

### v0.4
- [ ] Arrays and lists
- [ ] File I/O operations
- [ ] Better error recovery
- [ ] Debugger mode

### v1.0 (Stable)
- [ ] Standard library
- [ ] Package management
- [ ] IDE extensions
- [ ] Web-based playground
- [ ] Comprehensive documentation

## Testing

The release includes comprehensive example programs in the `examples/` folder:

- `hello.read` - Demonstrates all language features
- `calculator.read` - Basic variable operations
- `greet.read` - Task definitions with variables
- `countdown.read` - Loop and conditional example

Run tests:
```bash
python run.py examples/hello.read
python run.py examples/calculator.read
python run.py examples/greet.read
python run.py examples/countdown.read
```

## Contributing

We welcome contributions that align with ReadCode's philosophy of simplicity and readability. Areas for contribution:

- Bug fixes and error handling improvements
- Documentation enhancements
- Educational examples
- Performance optimizations (without sacrificing readability)

## Support

- **Documentation**: See `README.md` and `docs/grammar.md`
- **Issues**: Report bugs via GitHub Issues
- **Examples**: Check the `examples/` directory

## Philosophy

ReadCode v0.1 represents our first step toward making programming accessible to everyone. By using natural language syntax and minimal concepts, we aim to bridge the gap between human thought and machine execution.

> "The best programming language is the one that reads like a story and writes like a conversation."

---

**Thank you for trying ReadCode v0.1!**  
Your feedback and contributions will help shape the future of this project.
