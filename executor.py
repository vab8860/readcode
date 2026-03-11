from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import random
import urllib.request
from typing import Any, Dict, List, Optional, Union

from lexer import lex
from parser import (
    AddToListStmt,
    AskStmt,
    AsyncBlockStmt,
    ApiCallStmt,
    CreateFileStmt,
    DeleteFileStmt,
    EmailStmt,
    BinaryOp,
    CountOfExpr,
    Condition,
    DoStmt,
    DoMethodStmt,
    Expr,
    FetchStmt,
    IfStmt,
    ImportStmt,
    ListAccessExpr,
    ListLiteral,
    ListFilesStmt,
    MultiSetStmt,
    NewObjectExpr,
    NumberLiteral,
    ObjectDefStmt,
    Program,
    ReadFileStmt,
    RandomBetweenExpr,
    ReadFromExpr,
    ReturnStmt,
    RunTaskExpr,
    RepeatStmt,
    SaveStmt,
    SetAttrStmt,
    SetStmt,
    ShowStmt,
    StringOpExpr,
    StringLiteral,
    TaskDefStmt,
    TryCatchStmt,
    WhileStmt,
    AttrRefExpr,
    VarRef,
    WebsocketStmt,
    WriteFileStmt,
    parse,
)


class RuntimeErrorRC(Exception):
    pass


def _integration_error(msg: str, *, line_no: int | None) -> RuntimeErrorRC:
    if line_no is None:
        return RuntimeErrorRC(msg)
    return RuntimeErrorRC(f"{msg} on line {line_no}.")


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


Value = Union[int, str, list, dict]


@dataclass
class ClassDef:
    name: str
    properties: List[str]
    methods: Dict[str, TaskDefStmt]


@dataclass
class ObjectInstance:
    class_name: str
    attrs: Dict[str, Value]


@dataclass
class Environment:
    variables: Dict[str, Value] = field(default_factory=dict)
    tasks: Dict[str, TaskDefStmt] = field(default_factory=dict)
    classes: Dict[str, ClassDef] = field(default_factory=dict)
    imported_modules: Dict[str, bool] = field(default_factory=dict)


def execute(program: Program, *, env: Optional[Environment] = None, base_dir: str | Path | None = None) -> Environment:
    if env is None:
        env = Environment()
    if base_dir is None:
        base = Path.cwd()
    else:
        base = Path(base_dir)
    _exec_block(program.statements, env, base_dir=base)
    return env


def _exec_block(statements: List[Any], env: Environment, *, base_dir: Path) -> None:
    for st in statements:
        _exec_stmt(st, env, base_dir=base_dir)


def _exec_stmt(st: Any, env: Environment, *, base_dir: Path) -> None:
    if isinstance(st, SetStmt):
        env.variables[st.name] = _eval_expr(st.value, env, line_no=st.line_no, base_dir=base_dir)
        return

    if isinstance(st, MultiSetStmt):
        for name, expr in zip(st.names, st.values):
            env.variables[name] = _eval_expr(expr, env, line_no=st.line_no, base_dir=base_dir)
        return

    if isinstance(st, SetAttrStmt):
        if st.obj_name not in env.variables:
            raise _undefined_name_error(st.obj_name, line_no=st.line_no)
        obj = env.variables[st.obj_name]
        if not isinstance(obj, ObjectInstance):
            raise RuntimeErrorRC(f"Oops! '{st.obj_name}' is not an object on line {st.line_no}.")
        obj.attrs[st.attr] = _eval_expr(st.value, env, line_no=st.line_no, base_dir=base_dir)
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

        vals = [_eval_expr(p, env, base_dir=base_dir) for p in st.parts]
        print(" ".join(str(v) for v in vals))
        return

    if isinstance(st, ImportStmt):
        _exec_import(st, env, base_dir=base_dir)
        return

    if isinstance(st, TryCatchStmt):
        try:
            _exec_block(st.body, env, base_dir=base_dir)
        except (RuntimeErrorRC, OSError, ValueError, ZeroDivisionError):
            _exec_block(st.catch_body, env, base_dir=base_dir)
        return

    if isinstance(st, ObjectDefStmt):
        methods: Dict[str, TaskDefStmt] = {}
        for m in st.methods:
            methods[m.name] = TaskDefStmt(name=m.name, params=[], body=m.body, line_no=m.line_no)
        env.classes[st.name] = ClassDef(name=st.name, properties=list(st.properties), methods=methods)
        return

    if isinstance(st, DoMethodStmt):
        if st.obj_name not in env.variables:
            raise _undefined_name_error(st.obj_name, line_no=st.line_no)
        obj = env.variables[st.obj_name]
        if not isinstance(obj, ObjectInstance):
            raise RuntimeErrorRC(f"Oops! '{st.obj_name}' is not an object on line {st.line_no}.")
        cls = env.classes.get(obj.class_name)
        if cls is None:
            raise RuntimeErrorRC(f"Oops! Class '{obj.class_name}' not found for object '{st.obj_name}' on line {st.line_no}.")
        method = cls.methods.get(st.method_name)
        if method is None:
            raise RuntimeErrorRC(f"Oops! Method '{st.method_name}' not found on '{obj.class_name}' on line {st.line_no}.")

        # Evaluate args in current scope
        arg_vals: List[Value] = [_eval_expr(a, env, line_no=st.line_no, base_dir=base_dir) for a in st.args]
        if len(arg_vals) != 0:
            # reserved for future: positional args
            pass

        # Local scope: variables + object attrs available directly by name, and self refers to object
        old_vars = env.variables
        local_vars = dict(old_vars)
        local_vars["self"] = obj
        for k, v in obj.attrs.items():
            local_vars[k] = v
        env.variables = local_vars
        try:
            _exec_block(method.body, env, base_dir=base_dir)
        except _ReturnSignal:
            pass
        finally:
            # persist any property updates back into object attrs
            for prop in cls.properties:
                if prop in env.variables:
                    obj.attrs[prop] = env.variables[prop]
            env.variables = old_vars
        return

    if isinstance(st, AsyncBlockStmt):
        # Implementation: run sequentially for now (future: true concurrency)
        _exec_block(st.body, env, base_dir=base_dir)
        return

    if isinstance(st, FetchStmt):
        url_val = _eval_expr(st.url, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(url_val, str):
            raise RuntimeErrorRC(f"Oops! fetch needs a URL text on line {st.line_no}.")
        env.variables["data"] = _fetch_url(url_val, line_no=st.line_no)
        return

    if isinstance(st, EmailStmt):
        try:
            from integrations import IntegrationError, send_email
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e

        to_val = _eval_expr(st.to_addr, env, line_no=st.line_no, base_dir=base_dir)
        subject_val = _eval_expr(st.subject, env, line_no=st.line_no, base_dir=base_dir)
        msg_val = _eval_expr(st.message, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(to_val, str) or not isinstance(subject_val, str) or not isinstance(msg_val, str):
            raise RuntimeErrorRC(f"Oops! Email to/subject/message must be text on line {st.line_no}.")
        try:
            send_email(to_val, subject_val, msg_val)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        return

    if isinstance(st, CreateFileStmt):
        try:
            from integrations import IntegrationError, create_file
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e
        path_val = _eval_expr(st.path, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(path_val, str):
            raise RuntimeErrorRC(f"Oops! File path must be text on line {st.line_no}.")
        try:
            create_file(path_val, base_dir=base_dir)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        return

    if isinstance(st, WriteFileStmt):
        try:
            from integrations import IntegrationError, write_file
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e
        content_val = _eval_expr(st.content, env, line_no=st.line_no, base_dir=base_dir)
        path_val = _eval_expr(st.path, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(path_val, str):
            raise RuntimeErrorRC(f"Oops! File path must be text on line {st.line_no}.")
        try:
            write_file(path_val, str(content_val), base_dir=base_dir)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        return

    if isinstance(st, ReadFileStmt):
        try:
            from integrations import IntegrationError, read_file
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e
        path_val = _eval_expr(st.path, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(path_val, str):
            raise RuntimeErrorRC(f"Oops! File path must be text on line {st.line_no}.")
        try:
            env.variables[st.var_name] = read_file(path_val, base_dir=base_dir)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        return

    if isinstance(st, DeleteFileStmt):
        try:
            from integrations import IntegrationError, delete_file
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e
        path_val = _eval_expr(st.path, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(path_val, str):
            raise RuntimeErrorRC(f"Oops! File path must be text on line {st.line_no}.")
        try:
            delete_file(path_val, base_dir=base_dir)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        return

    if isinstance(st, ListFilesStmt):
        try:
            from integrations import IntegrationError, list_files
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e
        path_val = _eval_expr(st.path, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(path_val, str):
            raise RuntimeErrorRC(f"Oops! Folder path must be text on line {st.line_no}.")
        try:
            items = list_files(path_val, base_dir=base_dir)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
        print(" ".join(items))
        return

    if isinstance(st, ApiCallStmt):
        try:
            from integrations import IntegrationError, call_api
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e

        url_val = _eval_expr(st.url, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(url_val, str):
            raise RuntimeErrorRC(f"Oops! API url must be text on line {st.line_no}.")

        headers: Dict[str, str] = {}
        for k, vexpr in st.headers:
            v = _eval_expr(vexpr, env, line_no=st.line_no, base_dir=base_dir)
            headers[k] = str(v)

        params: Dict[str, str] = {}
        for k, vexpr in st.params:
            v = _eval_expr(vexpr, env, line_no=st.line_no, base_dir=base_dir)
            params[k] = str(v)

        print("Calling API...")
        try:
            resp = call_api(url_val, method=st.method, headers=headers, params=params)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e

        if st.store_var:
            env.variables[st.store_var] = resp
        else:
            env.variables["response"] = resp
        return

    if isinstance(st, WebsocketStmt):
        try:
            from integrations import IntegrationError, start_websocket_server
        except ModuleNotFoundError as e:
            raise RuntimeErrorRC("Oops! integrations.py is missing.") from e

        def on_message(msg: str) -> Optional[str]:
            # provide message as a variable during handler execution
            old_vars = env.variables
            local_vars = dict(old_vars)
            local_vars["message"] = msg
            env.variables = local_vars
            try:
                _exec_block(st.on_message_body, env, base_dir=base_dir)
            finally:
                env.variables = old_vars
            return None

        print(f"Websocket server running on port {st.port}...")
        try:
            start_websocket_server(port=st.port, on_message=on_message)
        except IntegrationError as e:
            raise RuntimeErrorRC(str(e)) from e
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
        value = _eval_expr(st.value, env, line_no=st.line_no, base_dir=base_dir)
        raise _ReturnSignal(value)

    if isinstance(st, IfStmt):
        if _eval_condition(st.condition, env, line_no=st.line_no):
            _exec_block(st.body, env, base_dir=base_dir)
        elif st.else_body is not None:
            _exec_block(st.else_body, env, base_dir=base_dir)
        return

    if isinstance(st, RepeatStmt):
        times_val = _eval_expr(st.times, env, line_no=st.line_no, base_dir=base_dir)
        if not isinstance(times_val, int):
            raise RuntimeErrorRC(
                f"Oops! 'repeat' needs a number on line {st.line_no}. Example: repeat 5 times ..."
            )
        if times_val < 0:
            raise RuntimeErrorRC(
                f"Oops! 'repeat' can't use a negative number on line {st.line_no}."
            )
        for _ in range(times_val):
            _exec_block(st.body, env, base_dir=base_dir)
        return

    if isinstance(st, WhileStmt):
        guard = 0
        while _eval_condition(st.condition, env, line_no=st.line_no):
            _exec_block(st.body, env, base_dir=base_dir)
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
        _call_task(env, st.task_name, st.args, line_no=st.line_no, base_dir=base_dir)
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


def _eval_expr(expr: Expr, env: Environment, *, line_no: int | None = None, base_dir: Path | None = None) -> Any:
    if base_dir is None:
        base = Path.cwd()
    else:
        base = base_dir
    if isinstance(expr, StringLiteral):
        return expr.value
    if isinstance(expr, NumberLiteral):
        return expr.value
    if isinstance(expr, VarRef):
        if expr.name not in env.variables:
            raise _undefined_name_error(expr.name, line_no=line_no)
        return env.variables[expr.name]
    if isinstance(expr, AttrRefExpr):
        if expr.obj_name not in env.variables:
            raise _undefined_name_error(expr.obj_name, line_no=line_no)
        obj = env.variables[expr.obj_name]
        if not isinstance(obj, ObjectInstance):
            raise RuntimeErrorRC(f"Oops! '{expr.obj_name}' is not an object.")
        if expr.attr not in obj.attrs:
            return ""
        return obj.attrs[expr.attr]
    if isinstance(expr, NewObjectExpr):
        cls = env.classes.get(expr.class_name)
        if cls is None:
            raise RuntimeErrorRC(f"Oops! Class '{expr.class_name}' not found.")
        attrs: Dict[str, Value] = {p: "" for p in cls.properties}
        return ObjectInstance(class_name=cls.name, attrs=attrs)
    if isinstance(expr, ListLiteral):
        return [_eval_expr(it, env, line_no=line_no, base_dir=base) for it in expr.items]
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
        low_val = _eval_expr(expr.low, env, line_no=line_no, base_dir=base)
        high_val = _eval_expr(expr.high, env, line_no=line_no, base_dir=base)
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
        filename_val = _eval_expr(expr.filename, env, line_no=line_no, base_dir=base)
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
        v = _eval_expr(expr.value, env, line_no=line_no, base_dir=base)
        if expr.op == "length":
            return len(str(v))
        s = str(v)
        if expr.op == "uppercase":
            return s.upper()
        if expr.op == "lowercase":
            return s.lower()
        raise RuntimeErrorRC(f"Oops! Unknown string operation: {expr.op}")
    if isinstance(expr, BinaryOp):
        left = _eval_expr(expr.left, env, line_no=line_no, base_dir=base)
        right = _eval_expr(expr.right, env, line_no=line_no, base_dir=base)
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
        return _call_task(env, expr.task_name, expr.args, line_no=line_no, base_dir=base)
    raise RuntimeErrorRC(
        f"Oops! I can't understand this expression yet: {type(expr).__name__}."
    )


class _ReturnSignal(Exception):
    def __init__(self, value: Value):
        self.value = value


def _call_task(env: Environment, name: str, args: List[Expr], *, line_no: int | None, base_dir: Path) -> Value:
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
    arg_vals: List[Value] = [_eval_expr(a, env, line_no=line_no, base_dir=base_dir) for a in args]

    # create local scope
    old_vars = env.variables
    local_vars = dict(old_vars)
    for p, v in zip(task.params, arg_vals):
        local_vars[p] = v
    env.variables = local_vars

    try:
        _exec_block(task.body, env, base_dir=base_dir)
    except _ReturnSignal as rs:
        return rs.value
    finally:
        env.variables = old_vars

    return ""


def _exec_import(st: ImportStmt, env: Environment, *, base_dir: Path) -> None:
    # Prevent re-import cycles
    key = str((base_dir / st.path).resolve())
    if env.imported_modules.get(key):
        return
    env.imported_modules[key] = True

    mod_path = (base_dir / st.path).resolve()
    try:
        src = mod_path.read_text(encoding="utf-8")
    except OSError:
        raise RuntimeErrorRC(f"Oops! I couldn't import '{st.path}'. File not found.")

    lines = lex(src)
    program = parse(lines)
    execute(program, env=env, base_dir=mod_path.parent)


def _fetch_url(url: str, *, line_no: int) -> str:
    print("Fetching data...")
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            raw = resp.read()
            try:
                return raw.decode("utf-8")
            except Exception:
                return raw.decode("latin-1", errors="replace")
    except Exception as e:
        raise RuntimeErrorRC(f"Oops! I couldn't fetch data from '{url}' on line {line_no}.") from e
