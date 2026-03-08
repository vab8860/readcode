# ReadCode Grammar

This document describes the supported ReadCode syntax implemented by the interpreter.

## Lexical notes

- The language is line-oriented.
- Whitespace separates tokens.
- Double-quoted strings are supported as a single token: `"hello world"`.
- Blocks are started by a line ending with `...` and terminated by a line equal to `and end`.

## Grammar (EBNF-ish)

```
program        := statement*

statement      := set_stmt
               | show_stmt
               | if_stmt
               | repeat_stmt
               | task_def
               | do_stmt

set_stmt       := "set" IDENT "to" expr
show_stmt      := "show" expr+

do_stmt        := "do" IDENT

if_stmt        := "if" "the" IDENT "is" expr "..." NEWLINE block "and" "end"

repeat_stmt    := "repeat" expr "times" "..." NEWLINE block "and" "end"

task_def       := "task" IDENT "..." NEWLINE block "and" "end"

block          := statement*

expr           := STRING
               | NUMBER
               | IDENT

IDENT          := any non-whitespace token not otherwise reserved
NUMBER         := /-?[0-9]+/
STRING         := a double-quoted token with no escapes
```

## Semantics

- `set name to expr`
  - Evaluates `expr` and stores it in variable `name`.

- `show expr...`
  - Evaluates each expression and prints them separated by a single space.

- `if the name is expr ...` block `and end`
  - Evaluates variable `name` and compares it for equality with `expr`.
  - Executes the block if equal.

- `repeat N times ...` block `and end`
  - Evaluates `N` (must be an integer) and executes the block `N` times.

- `task greet ...` block `and end`
  - Defines a named task.

- `do greet`
  - Executes the previously defined task.
```
