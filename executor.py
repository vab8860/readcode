from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from parser import (
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
        env.variables[st.name] = _eval_expr(st.value, env)
        return

    if isinstance(st, ShowStmt):
        vals = [_eval_expr(p, env) for p in st.parts]
        print(" ".join(str(v) for v in vals))
        return

    if isinstance(st, IfStmt):
        if _eval_condition(st.condition, env):
            _exec_block(st.body, env)
        return

    if isinstance(st, RepeatStmt):
        times_val = _eval_expr(st.times, env)
        if not isinstance(times_val, int):
            raise RuntimeErrorRC(f"repeat expects a number on line {st.line_no}")
        if times_val < 0:
            raise RuntimeErrorRC(f"repeat expects a non-negative number on line {st.line_no}")
        for _ in range(times_val):
            _exec_block(st.body, env)
        return

    if isinstance(st, TaskDefStmt):
        env.tasks[st.name] = st.body
        return

    if isinstance(st, DoStmt):
        if st.task_name not in env.tasks:
            raise RuntimeErrorRC(f"Unknown task '{st.task_name}' on line {st.line_no}")
        _exec_block(env.tasks[st.task_name], env)
        return

    raise RuntimeErrorRC(f"Unsupported statement type: {type(st).__name__}")


def _eval_condition(cond: Condition, env: Environment) -> bool:
    left = env.variables.get(cond.name)
    if left is None:
        raise RuntimeErrorRC(f"Unknown variable '{cond.name}' in condition")
    right = _eval_expr(cond.equals, env)
    return left == right


def _eval_expr(expr: Expr, env: Environment) -> Value:
    if isinstance(expr, StringLiteral):
        return expr.value
    if isinstance(expr, NumberLiteral):
        return expr.value
    if isinstance(expr, VarRef):
        if expr.name not in env.variables:
            # treat unknown identifiers as plain strings
            return expr.name
        return env.variables[expr.name]
    raise RuntimeErrorRC(f"Unsupported expression type: {type(expr).__name__}")
