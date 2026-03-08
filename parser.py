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
class AskStmt(Stmt):
    name: str
    line_no: int


@dataclass(frozen=True)
class IfStmt(Stmt):
    condition: "Condition"
    body: List[Stmt]
    else_body: Optional[List[Stmt]]
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
class BinaryOp(Expr):
    left: Expr
    op: str  # "plus", "minus", "times", "divided_by", "joined_with"
    right: Expr


@dataclass(frozen=True)
class Condition:
    name: str
    op: str  # "==", "!=", ">", "<", ">=", "<="
    right: Expr


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

        # allow else ... inside an if block; handled by caller
        if toks == ["else", "..."] and stop_at_end:
            return out, i

        stmt, i = _parse_stmt(lines, i)
        out.append(stmt)

    if stop_at_end:
        raise ParseError("Oops! You forgot to close your block with 'and end'.")

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
    if head == "ask":
        return _parse_ask(lt), i + 1

    if head == "if":
        return _parse_if(lines, i)
    if head == "repeat":
        return _parse_repeat(lines, i)
    if head == "task":
        return _parse_task(lines, i)

    raise ParseError(
        f"Oops! I don't understand '{head}' on line {lt.line_no}. Check your spelling!"
    )


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


def _parse_ask(lt: LineTokens) -> AskStmt:
    # ask <name>
    if len(lt.tokens) != 2:
        raise ParseError(f"Invalid ask statement on line {lt.line_no}")
    return AskStmt(name=lt.tokens[1], line_no=lt.line_no)


def _parse_if(lines: Sequence[LineTokens], i: int) -> Tuple[IfStmt, int]:
    lt = lines[i]
    # if the <name> is <comparison> ...
    if len(lt.tokens) < 6:
        raise ParseError(f"Invalid if statement on line {lt.line_no}")
    if lt.tokens[1] != "the":
        raise ParseError(f"Expected 'the' in if statement on line {lt.line_no}")
    name = lt.tokens[2]
    if lt.tokens[3] != "is":
        raise ParseError(f"Expected 'is' in if statement on line {lt.line_no}")

    if lt.tokens[-1] != "...":
        raise ParseError(f"Expected '...' to start if block on line {lt.line_no}")

    comp_tokens = lt.tokens[4:-1]
    op, right_tokens = _parse_comparison(comp_tokens, lt.line_no)
    right_expr = _parse_expr_from_tokens(right_tokens, lt.line_no)
    cond = Condition(name=name, op=op, right=right_expr)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)

    # check for optional else block
    else_body = None
    if next_i < len(lines) and lines[next_i].tokens == ["else", "..."]:
        else_body, next_i = _parse_block(lines, next_i + 1, stop_at_end=True)

    return IfStmt(condition=cond, body=body, else_body=else_body, line_no=lt.line_no), next_i


def _parse_comparison(tokens: Sequence[str], line_no: int) -> Tuple[str, List[str]]:
    if not tokens:
        raise ParseError(f"Invalid comparison on line {line_no}")

    # Supported forms:
    # - equal to <expr>
    # - <expr>              (back-compat: treated as == <expr>)
    # - not <expr>
    # - greater than <expr>
    # - less than <expr>
    # - greater than or equal to <expr>
    # - less than or equal to <expr>

    if len(tokens) >= 2 and tokens[0] == "equal" and tokens[1] == "to":
        return "==", list(tokens[2:])

    if tokens[0] == "not":
        return "!=", list(tokens[1:])

    if len(tokens) >= 2 and tokens[0] == "greater" and tokens[1] == "than":
        if len(tokens) >= 5 and tokens[2:5] == ["or", "equal", "to"]:
            return ">=", list(tokens[5:])
        return ">", list(tokens[2:])

    if len(tokens) >= 2 and tokens[0] == "less" and tokens[1] == "than":
        if len(tokens) >= 5 and tokens[2:5] == ["or", "equal", "to"]:
            return "<=", list(tokens[5:])
        return "<", list(tokens[2:])

    # Back-compat: "is 18" means equality
    return "==", list(tokens)


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
    # Handle binary operations: <expr> <op> <expr>
    if len(tokens) >= 3:
        # String join: <expr> joined with <expr>
        for i in range(len(tokens) - 1):
            if tokens[i] == "joined" and tokens[i + 1] == "with":
                left_tokens = tokens[:i]
                right_tokens = tokens[i + 2 :]
                if not left_tokens or not right_tokens:
                    raise ParseError(f"Invalid joined with operation on line {line_no}")
                left = _parse_expr_from_tokens(left_tokens, line_no)
                right = _parse_expr_from_tokens(right_tokens, line_no)
                return BinaryOp(left=left, op="joined_with", right=right)

        # Look for operator tokens
        for i, tok in enumerate(tokens):
            if tok in ("plus", "minus", "times", "divided", "by"):
                if tok == "divided" and i + 1 < len(tokens) and tokens[i + 1] == "by":
                    # Handle "divided by" as two tokens
                    left_tokens = tokens[:i]
                    right_tokens = tokens[i + 2 :]
                    if not left_tokens or not right_tokens:
                        raise ParseError(f"Invalid binary operation on line {line_no}")
                    left = _parse_expr_from_tokens(left_tokens, line_no)
                    right = _parse_expr_from_tokens(right_tokens, line_no)
                    return BinaryOp(left=left, op="divided_by", right=right)
                elif tok in ("plus", "minus", "times"):
                    left_tokens = tokens[:i]
                    right_tokens = tokens[i + 1 :]
                    if not left_tokens or not right_tokens:
                        raise ParseError(f"Invalid binary operation on line {line_no}")
                    left = _parse_expr_from_tokens(left_tokens, line_no)
                    right = _parse_expr_from_tokens(right_tokens, line_no)
                    return BinaryOp(left=left, op=tok, right=right)

    # Single token expression
    if len(tokens) == 1:
        tok = tokens[0]
        if tok.startswith('"') and tok.endswith('"') and len(tok) >= 2:
            return StringLiteral(value=tok[1:-1])

        if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
            return NumberLiteral(value=int(tok))

        # variable reference
        return VarRef(name=tok)

    raise ParseError(f"Unable to parse expression on line {line_no}")


def _error_stmt(lines: Sequence[LineTokens], i: int, msg: str) -> Tuple[Stmt, int]:
    lt = lines[i]
    raise ParseError(f"{msg} on line {lt.line_no}")
