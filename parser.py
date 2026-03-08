from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from lexer import LineTokens


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class Program:
    statements: List["Stmt"]


class Stmt:
    pass


@dataclass(frozen=True)
class SetStmt(Stmt):
    name: str
    value: "Expr"
    line_no: int


@dataclass(frozen=True)
class ShowStmt(Stmt):
    parts: List["Expr"]
    line_no: int


@dataclass(frozen=True)
class DoStmt(Stmt):
    task_name: str
    line_no: int


@dataclass(frozen=True)
class IfStmt(Stmt):
    condition: "Condition"
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class RepeatStmt(Stmt):
    times: "Expr"
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class TaskDefStmt(Stmt):
    name: str
    body: List[Stmt]
    line_no: int


class Expr:
    pass


@dataclass(frozen=True)
class StringLiteral(Expr):
    value: str


@dataclass(frozen=True)
class NumberLiteral(Expr):
    value: int


@dataclass(frozen=True)
class VarRef(Expr):
    name: str


@dataclass(frozen=True)
class Condition:
    # currently only supports: the <name> is <expr>
    name: str
    equals: Expr


def parse(lines: Sequence[LineTokens]) -> Program:
    stmts, next_i = _parse_block(lines, 0, stop_at_end=False)
    if next_i != len(lines):
        lt = lines[next_i]
        raise ParseError(f"Unexpected tokens after program end on line {lt.line_no}")
    return Program(statements=stmts)


def _parse_block(
    lines: Sequence[LineTokens], start_i: int, *, stop_at_end: bool
) -> Tuple[List[Stmt], int]:
    out: List[Stmt] = []
    i = start_i
    while i < len(lines):
        lt = lines[i]
        toks = lt.tokens
        if toks == ["and", "end"]:
            if stop_at_end:
                return out, i + 1
            raise ParseError(f"Unexpected 'and end' on line {lt.line_no}")

        stmt, i = _parse_stmt(lines, i)
        out.append(stmt)

    if stop_at_end:
        raise ParseError("Missing 'and end' before end of file")

    return out, i


def _parse_stmt(lines: Sequence[LineTokens], i: int) -> Tuple[Stmt, int]:
    lt = lines[i]
    toks = lt.tokens
    if not toks:
        return _error_stmt(lines, i, "Empty statement")

    head = toks[0]
    if head == "set":
        return _parse_set(lt), i + 1
    if head == "show":
        return _parse_show(lt), i + 1
    if head == "do":
        return _parse_do(lt), i + 1

    if head == "if":
        return _parse_if(lines, i)
    if head == "repeat":
        return _parse_repeat(lines, i)
    if head == "task":
        return _parse_task(lines, i)

    raise ParseError(f"Unknown statement '{head}' on line {lt.line_no}")


def _expect_tokens(lt: LineTokens, expected: Sequence[str]) -> None:
    if list(lt.tokens[: len(expected)]) != list(expected):
        raise ParseError(
            f"Expected {' '.join(expected)} on line {lt.line_no}, got: {' '.join(lt.tokens)}"
        )


def _parse_set(lt: LineTokens) -> SetStmt:
    # set <name> to <expr>
    if len(lt.tokens) < 4:
        raise ParseError(f"Invalid set statement on line {lt.line_no}")
    if lt.tokens[2] != "to":
        raise ParseError(f"Expected 'to' in set statement on line {lt.line_no}")
    name = lt.tokens[1]
    value_tokens = lt.tokens[3:]
    value = _parse_expr_from_tokens(value_tokens, lt.line_no)
    return SetStmt(name=name, value=value, line_no=lt.line_no)


def _parse_show(lt: LineTokens) -> ShowStmt:
    # show <expr...>
    if len(lt.tokens) < 2:
        raise ParseError(f"Invalid show statement on line {lt.line_no}")
    parts: List[Expr] = []
    # For simplicity, parse each token as an expr (quoted string, number, or var)
    for tok in lt.tokens[1:]:
        parts.append(_parse_expr_from_tokens([tok], lt.line_no))
    return ShowStmt(parts=parts, line_no=lt.line_no)


def _parse_do(lt: LineTokens) -> DoStmt:
    # do <taskname>
    if len(lt.tokens) != 2:
        raise ParseError(f"Invalid do statement on line {lt.line_no}")
    return DoStmt(task_name=lt.tokens[1], line_no=lt.line_no)


def _parse_if(lines: Sequence[LineTokens], i: int) -> Tuple[IfStmt, int]:
    lt = lines[i]
    # if the <name> is <expr> ...
    if len(lt.tokens) < 6:
        raise ParseError(f"Invalid if statement on line {lt.line_no}")
    if lt.tokens[1] != "the":
        raise ParseError(f"Expected 'the' in if statement on line {lt.line_no}")
    name = lt.tokens[2]
    if lt.tokens[3] != "is":
        raise ParseError(f"Expected 'is' in if statement on line {lt.line_no}")

    if lt.tokens[-1] != "...":
        raise ParseError(f"Expected '...' to start if block on line {lt.line_no}")

    equals_tokens = lt.tokens[4:-1]
    equals_expr = _parse_expr_from_tokens(equals_tokens, lt.line_no)
    cond = Condition(name=name, equals=equals_expr)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return IfStmt(condition=cond, body=body, line_no=lt.line_no), next_i


def _parse_repeat(lines: Sequence[LineTokens], i: int) -> Tuple[RepeatStmt, int]:
    lt = lines[i]
    # repeat <expr> times ...
    if len(lt.tokens) < 4:
        raise ParseError(f"Invalid repeat statement on line {lt.line_no}")
    if lt.tokens[-1] != "...":
        raise ParseError(f"Expected '...' to start repeat block on line {lt.line_no}")
    if lt.tokens[-2] != "times":
        raise ParseError(f"Expected 'times' in repeat statement on line {lt.line_no}")

    times_tokens = lt.tokens[1:-2]
    times_expr = _parse_expr_from_tokens(times_tokens, lt.line_no)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return RepeatStmt(times=times_expr, body=body, line_no=lt.line_no), next_i


def _parse_task(lines: Sequence[LineTokens], i: int) -> Tuple[TaskDefStmt, int]:
    lt = lines[i]
    # task <name> ...
    if len(lt.tokens) != 3:
        raise ParseError(f"Invalid task statement on line {lt.line_no}")
    if lt.tokens[2] != "...":
        raise ParseError(f"Expected '...' to start task block on line {lt.line_no}")
    name = lt.tokens[1]

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return TaskDefStmt(name=name, body=body, line_no=lt.line_no), next_i


def _parse_expr_from_tokens(tokens: Sequence[str], line_no: int) -> Expr:
    if len(tokens) != 1:
        raise ParseError(f"Only single-token expressions supported on line {line_no}")

    tok = tokens[0]
    if tok.startswith('"') and tok.endswith('"') and len(tok) >= 2:
        return StringLiteral(value=tok[1:-1])

    if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
        return NumberLiteral(value=int(tok))

    # variable reference
    return VarRef(name=tok)


def _error_stmt(lines: Sequence[LineTokens], i: int, msg: str) -> Tuple[Stmt, int]:
    lt = lines[i]
    raise ParseError(f"{msg} on line {lt.line_no}")
