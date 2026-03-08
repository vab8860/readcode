from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from parser import (
    AskStmt,
    BinaryOp,
    Condition,
    DoStmt,
    Expr,
    IfStmt,
    NumberLiteral,
    Program,
    RepeatStmt,
    SetStmt,
    ShowStmt,
    StringLiteral,
    TaskDefStmt,
    VarRef,
)


class RuntimeErrorRC(Exception):
    pass


Value = Union[int, str]


@dataclass
class Environment:
    variables: Dict[str, Value] = field(default_factory=dict)
    tasks: Dict[str, List[Any]] = field(default_factory=dict)  # task name -> list[Stmt]


def execute(program: Program, *, env: Optional[Environment] = None) -> Environment:
    if env is None:
        env = Environment()
    _exec_block(program.statements, env)
    return env


def _exec_block(statements: List[Any], env: Environment) -> None:
    for st in statements:
        _exec_stmt(st, env)


def _exec_stmt(st: Any, env: Environment) -> None:
    if isinstance(st, SetStmt):
        env.variables[st.name] = _eval_expr(st.value, env, line_no=st.line_no)
        return

    if isinstance(st, AskStmt):
        raw = input(f"{st.name}: ")
        s = raw.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            env.variables[st.name] = int(s)
        else:
            env.variables[st.name] = s
        return

    if isinstance(st, ShowStmt):
        vals = [_eval_expr(p, env) for p in st.parts]
        print(" ".join(str(v) for v in vals))
        return

    if isinstance(st, IfStmt):
        if _eval_condition(st.condition, env, line_no=st.line_no):
            _exec_block(st.body, env)
        elif st.else_body is not None:
            _exec_block(st.else_body, env)
        return

    if isinstance(st, RepeatStmt):
        times_val = _eval_expr(st.times, env, line_no=st.line_no)
        if not isinstance(times_val, int):
            raise RuntimeErrorRC(
                f"Oops! 'repeat' needs a number on line {st.line_no}. Example: repeat 5 times ..."
            )
        if times_val < 0:
            raise RuntimeErrorRC(
                f"Oops! 'repeat' can't use a negative number on line {st.line_no}."
            )
        for _ in range(times_val):
            _exec_block(st.body, env)
        return

    if isinstance(st, TaskDefStmt):
        env.tasks[st.name] = st.body
        return

    if isinstance(st, DoStmt):
        if st.task_name not in env.tasks:
            raise RuntimeErrorRC(
                f"Oops! Task '{st.task_name}' not found on line {st.line_no}. "
                f"Did you forget to define it? Example: task {st.task_name} ..."
            )
        _exec_block(env.tasks[st.task_name], env)
        return

    raise RuntimeErrorRC(
        f"Oops! I can't run this kind of statement yet: {type(st).__name__}."
    )


def _eval_condition(cond: Condition, env: Environment, *, line_no: int | None = None) -> bool:
    left = env.variables.get(cond.name)
    if left is None:
        raise RuntimeErrorRC(
            f"Oops! Variable '{cond.name}' not found. Did you forget to set it? "
            f"Example: set {cond.name} to 18"
        )
    right = _eval_expr(cond.right, env)

    # If one side is int and the other is a numeric string, coerce.
    if isinstance(left, int) and isinstance(right, str) and (right.isdigit() or (right.startswith("-") and right[1:].isdigit())):
        right = int(right)
    if isinstance(right, int) and isinstance(left, str) and (left.isdigit() or (left.startswith("-") and left[1:].isdigit())):
        left = int(left)

    if cond.op == "==":
        return left == right
    if cond.op == "!=":
        return left != right

    # Ordering comparisons require integers
    if not isinstance(left, int) or not isinstance(right, int):
        if line_no is not None:
            raise RuntimeErrorRC(
                f"Oops! Can't compare text with numbers on line {line_no}. "
                f"Try using numbers on both sides."
            )
        raise RuntimeErrorRC(
            "Oops! Can't compare text with numbers. Try using numbers on both sides."
        )

    if cond.op == ">":
        return left > right
    if cond.op == "<":
        return left < right
    if cond.op == ">=":
        return left >= right
    if cond.op == "<=":
        return left <= right

    raise RuntimeErrorRC(f"Unknown comparison operator: {cond.op}")


def _eval_expr(expr: Expr, env: Environment, *, line_no: int | None = None) -> Value:
    if isinstance(expr, StringLiteral):
        return expr.value
    if isinstance(expr, NumberLiteral):
        return expr.value
    if isinstance(expr, VarRef):
        if expr.name not in env.variables:
            raise RuntimeErrorRC(
                f"Oops! Variable '{expr.name}' not found. Did you forget to set it? "
                f"Example: set {expr.name} to John"
            )
        return env.variables[expr.name]
    if isinstance(expr, BinaryOp):
        left = _eval_expr(expr.left, env, line_no=line_no)
        right = _eval_expr(expr.right, env, line_no=line_no)
        if expr.op == "joined_with":
            ls = str(left)
            rs = str(right)
            if ls and rs:
                return f"{ls} {rs}"
            return f"{ls}{rs}"
        # Ensure both operands are numbers for math operations
        if not isinstance(left, int) or not isinstance(right, int):
            raise RuntimeErrorRC(
                "Oops! Math operations need numbers. Example: set sum to 10 plus 5"
            )
        if expr.op == "plus":
            return left + right
        if expr.op == "minus":
            return left - right
        if expr.op == "times":
            return left * right
        if expr.op == "divided_by":
            if right == 0:
                if line_no is not None:
                    raise RuntimeErrorRC(f"Oops! You can't divide by zero on line {line_no}!")
                raise RuntimeErrorRC("Oops! You can't divide by zero!")
            return left // right  # integer division
        raise RuntimeErrorRC(f"Unknown math operator: {expr.op}")
    raise RuntimeErrorRC(
        f"Oops! I can't understand this expression yet: {type(expr).__name__}."
    )
