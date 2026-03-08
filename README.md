# ReadCode

A simple, human-readable programming language designed to remove the barrier between humans and computers.

## What is ReadCode?

ReadCode is a minimal, line-oriented scripting language that reads like plain English. It prioritizes readability and simplicity over performance, making it ideal for beginners, educational purposes, and quick automation scripts.

### Goal

The primary goal of ReadCode is to **remove the barrier between humans and computers** by creating a language that:
- Reads like natural language
- Has minimal syntax rules
- Provides immediate feedback
- Is easy to learn and teach

## Installation

1. Clone the repository:
```bash
git clone https://github.com/vab8860/readcode.git
cd readcode
```

2. Run programs with Python 3.7+:
```bash
python run.py examples/hello.read
```

## Syntax Guide

ReadCode uses simple, English-like statements. Programs are line-oriented and use whitespace to separate tokens.

### Basic Statements

```readcode
# Variable assignment
set age to 18

# Output text
show hello world
show "quoted strings" and variables

# Conditional logic
if the age is 18 ...
  show you are adult
else ...
  show you are minor
and end

# Loops
repeat 5 times ...
  show hello
and end

# Define tasks (functions)
task greet ...
  show hello world
and end

# Call tasks
do greet
```

### Data Types

- **Numbers**: `42`, `-7`
- **Strings**: `"hello world"` (quoted) or `hello` (unquoted identifiers)
- **Variables**: Referenced by name, e.g., `age`

### Control Structures

- `if the <variable> is <value> ...` and `else ...` blocks
- `repeat <number> times ...` loops
- `task <name> ...` function definitions

## Example Programs

### Hello World
```readcode
set age to 18
show hello world

if the age is 18 ...
  show you are adult
else ...
  show you are minor
and end
```

### Counter
```readcode
set count to 5
repeat 5 times ...
  show count
and end
```

### Function with Parameters
```readcode
set name to Alice

task greet ...
  show "Hello" name
and end

do greet
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
    └── grammar.md  # Formal grammar specification
```

## Running Programs

```bash
# Run an example
python run.py examples/hello.read

# Run your own program
python run.py my_program.read
```

## Error Handling

ReadCode provides clear, line-numbered error messages:
- Syntax errors during parsing
- Runtime errors during execution
- Missing variables treated as plain strings

## Future Plans

### Version 0.3
- [ ] Math operations (`add`, `subtract`, `multiply`, `divide`)
- [ ] Input from user (`ask` statement)
- [ ] String operations (`concat`, `length`)
- [ ] Comparison operators (`greater than`, `less than`)

### Version 0.4
- [ ] Arrays/lists support
- [ ] File I/O operations
- [ ] Better error recovery
- [ ] Debugger mode

### Version 1.0
- [ ] Standard library
- [ ] Package management
- [ ] IDE extension
- [ ] Web-based playground

## Contributing

ReadCode is intentionally simple. Contributions should align with the goal of maintaining readability and simplicity. Areas for contribution:
- Bug fixes
- Documentation improvements
- Educational examples
- Performance optimizations (without sacrificing readability)

## License

MIT License - see LICENSE file for details.

## Philosophy

> "The best programming language is the one that reads like a story and writes like a conversation."

ReadCode believes that programming should be accessible to everyone, regardless of their technical background. By using natural language syntax and minimal concepts, we hope to bridge the gap between human thought and machine execution.
