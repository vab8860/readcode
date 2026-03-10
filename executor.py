from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any, Dict, List, Optional, Union

from parser import (
    AddToListStmt,
    AskStmt,
    BinaryOp,
    CountOfExpr,
    Condition,
    DoStmt,
    Expr,
    IfStmt,
    ListAccessExpr,
    ListLiteral,
    MultiSetStmt,
    NumberLiteral,
    Program,
    RandomBetweenExpr,
    ReadFromExpr,
    ReturnStmt,
    RunTaskExpr,
    RepeatStmt,
    SaveStmt,
    SetStmt,
    ShowStmt,
    StringOpExpr,
    StringLiteral,
    TaskDefStmt,
    WhileStmt,
    VarRef,
)


class RuntimeErrorRC(Exception):
    pass


def _undefined_name_error(name: str, *, line_no: int | None) -> RuntimeErrorRC:
    if line_no is None:
        return RuntimeErrorRC(
            f"Oops! '{name}' is not defined. "
            f"Did you mean to write it as text? Use quotes: set something to \"{name}\" "
            f"Or did you forget to create it first? Example: set {name} to 10"
        )
    return RuntimeErrorRC(
        f"Oops! '{name}' is not defined on line {line_no}.\n"
        f"Did you mean to write it as text? Use quotes: set something to \"{name}\"\n"
        f"Or did you forget to create it first? Example: set {name} to 10"
    )


Value = Union[int, str, list]


@dataclass
class Environment:
    variables: Dict[str, Value] = field(default_factory=dict)
    tasks: Dict[str, TaskDefStmt] = field(default_factory=dict)


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

    if isinstance(st, MultiSetStmt):
        for name, expr in zip(st.names, st.values):
            env.variables[name] = _eval_expr(expr, env, line_no=st.line_no)
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
        # special case: show all <list>
        if len(st.parts) == 1 and isinstance(st.parts[0], VarRef) and st.parts[0].name in env.variables:
            v = env.variables[st.parts[0].name]
            if isinstance(v, list):
                print(" ".join(str(x) for x in v))
                return

        vals = [_eval_expr(p, env) for p in st.parts]
        print(" ".join(str(v) for v in vals))
        return

    if isinstance(st, AddToListStmt):
        if st.list_name not in env.variables:
            raise RuntimeErrorRC(
                f"Oops! List '{st.list_name}' not found. Create it first. Example: set {st.list_name} to list apple banana"
            )
        target = env.variables[st.list_name]
        if not isinstance(target, list):
            raise RuntimeErrorRC(
                f"Oops! '{st.list_name}' is not a list. Create it using: set {st.list_name} to list apple banana"
            )
        item_val = _eval_expr(st.item, env, line_no=st.line_no)
        target.append(item_val)
        return

    if isinstance(st, SaveStmt):
        filename_val = _eval_expr(st.filename, env, line_no=st.line_no)
        if not isinstance(filename_val, str):
            raise RuntimeErrorRC(
                f"Oops! File name must be text on line {st.line_no}. Example: save \"hello\" to \"file.txt\""
            )
        content_val = _eval_expr(st.content, env, line_no=st.line_no)
        try:
            with open(filename_val, "w", encoding="utf-8") as f:
                f.write(str(content_val))
        except OSError:
            raise RuntimeErrorRC(
                f"Oops! I couldn't save to '{filename_val}' on line {st.line_no}."
            )
        return

    if isinstance(st, ReturnStmt):
        value = _eval_expr(st.value, env, line_no=st.line_no)
        raise _ReturnSignal(value)

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

    if isinstance(st, WhileStmt):
        guard = 0
        while _eval_condition(st.condition, env, line_no=st.line_no):
            _exec_block(st.body, env)
            guard += 1
            if guard > 1_000_000:
                raise RuntimeErrorRC(
                    f"Oops! Your while loop seems to run forever (line {st.line_no})."
                )
        return

    if isinstance(st, TaskDefStmt):
        env.tasks[st.name] = st
        return

    if isinstance(st, DoStmt):
        if st.task_name not in env.tasks:
            raise RuntimeErrorRC(
                f"Oops! Task '{st.task_name}' not found on line {st.line_no}. "
                f"Did you forget to define it? Example: task {st.task_name} ..."
            )
        _call_task(env, st.task_name, st.args, line_no=st.line_no)
        return

    raise RuntimeErrorRC(
        f"Oops! I can't run this kind of statement yet: {type(st).__name__}."
    )


def _eval_condition(cond: Condition, env: Environment, *, line_no: int | None = None) -> bool:
    left = env.variables.get(cond.name)
    if left is None:
        raise _undefined_name_error(cond.name, line_no=line_no)
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


def _eval_expr(expr: Expr, env: Environment, *, line_no: int | None = None) -> Any:
    if isinstance(expr, StringLiteral):
        return expr.value
    if isinstance(expr, NumberLiteral):
        return expr.value
    if isinstance(expr, VarRef):
        if expr.name not in env.variables:
            raise _undefined_name_error(expr.name, line_no=line_no)
        return env.variables[expr.name]
    if isinstance(expr, ListLiteral):
        return [_eval_expr(it, env, line_no=line_no) for it in expr.items]
    if isinstance(expr, ListAccessExpr):
        if expr.list_name not in env.variables:
            raise RuntimeErrorRC(
                f"Oops! List '{expr.list_name}' not found. Create it first. Example: set {expr.list_name} to list apple banana"
            )
        v = env.variables[expr.list_name]
        if not isinstance(v, list):
            raise RuntimeErrorRC(f"Oops! '{expr.list_name}' is not a list.")
        if not v:
            raise RuntimeErrorRC(f"Oops! List '{expr.list_name}' is empty.")
        if expr.kind == "first":
            return v[0]
        if expr.kind == "last":
            return v[-1]
        raise RuntimeErrorRC(f"Oops! Unknown list access: {expr.kind}")
    if isinstance(expr, CountOfExpr):
        if expr.list_name not in env.variables:
            raise RuntimeErrorRC(
                f"Oops! List '{expr.list_name}' not found. Create it first. Example: set {expr.list_name} to list apple banana"
            )
        v = env.variables[expr.list_name]
        if not isinstance(v, list):
            raise RuntimeErrorRC(f"Oops! '{expr.list_name}' is not a list.")
        return len(v)

    if isinstance(expr, RandomBetweenExpr):
        low_val = _eval_expr(expr.low, env, line_no=line_no)
        high_val = _eval_expr(expr.high, env, line_no=line_no)
        if not isinstance(low_val, int) or not isinstance(high_val, int):
            if line_no is not None:
                raise RuntimeErrorRC(
                    f"Oops! 'random between' needs numbers on line {line_no}. Example: set n to random between 1 and 10"
                )
            raise RuntimeErrorRC(
                "Oops! 'random between' needs numbers. Example: set n to random between 1 and 10"
            )
        if low_val > high_val:
            low_val, high_val = high_val, low_val
        return random.randint(low_val, high_val)

    if isinstance(expr, ReadFromExpr):
        filename_val = _eval_expr(expr.filename, env, line_no=line_no)
        if not isinstance(filename_val, str):
            if line_no is not None:
                raise RuntimeErrorRC(
                    f"Oops! File name must be text on line {line_no}. Example: set content to read from \"file.txt\""
                )
            raise RuntimeErrorRC(
                "Oops! File name must be text. Example: set content to read from \"file.txt\""
            )
        try:
            with open(filename_val, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            if line_no is not None:
                raise RuntimeErrorRC(
                    f"Oops! I couldn't read from '{filename_val}' on line {line_no}."
                )
            raise RuntimeErrorRC(f"Oops! I couldn't read from '{filename_val}'.")

    if isinstance(expr, StringOpExpr):
        v = _eval_expr(expr.value, env, line_no=line_no)
        if expr.op == "length":
            return len(str(v))
        s = str(v)
        if expr.op == "uppercase":
            return s.upper()
        if expr.op == "lowercase":
            return s.lower()
        raise RuntimeErrorRC(f"Oops! Unknown string operation: {expr.op}")
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
    if isinstance(expr, RunTaskExpr):
        if expr.task_name not in env.tasks:
            raise RuntimeErrorRC(
                f"Oops! Task '{expr.task_name}' not found. Did you forget to define it?"
            )
        return _call_task(env, expr.task_name, expr.args, line_no=line_no)
    raise RuntimeErrorRC(
        f"Oops! I can't understand this expression yet: {type(expr).__name__}."
    )


class _ReturnSignal(Exception):
    def __init__(self, value: Value):
        self.value = value


def _call_task(env: Environment, name: str, args: List[Expr], *, line_no: int | None) -> Value:
    task = env.tasks.get(name)
    if task is None:
        raise RuntimeErrorRC(
            f"Oops! Task '{name}' not found. Did you forget to define it? Example: task {name} ..."
        )

    if len(args) != len(task.params):
        raise RuntimeErrorRC(
            f"Oops! Task '{name}' expects {len(task.params)} value(s) but you gave {len(args)}."
        )

    # evaluate arguments in current scope
    arg_vals: List[Value] = [_eval_expr(a, env, line_no=line_no) for a in args]

    # create local scope
    old_vars = env.variables
    local_vars = dict(old_vars)
    for p, v in zip(task.params, arg_vals):
        local_vars[p] = v
    env.variables = local_vars

    try:
        _exec_block(task.body, env)
    except _ReturnSignal as rs:
        return rs.value
    finally:
        env.variables = old_vars

    return ""
