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
    args: List["Expr"]
    line_no: int


@dataclass(frozen=True)
class ReturnStmt(Stmt):
    value: "Expr"
    line_no: int


@dataclass(frozen=True)
class AddToListStmt(Stmt):
    item: "Expr"
    list_name: str
    line_no: int


@dataclass(frozen=True)
class AskStmt(Stmt):
    name: str
    line_no: int


@dataclass(frozen=True)
class AskAIStmt(Stmt):
    prompt: Expr
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
    params: List[str]
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class SaveStmt(Stmt):
    content: "Expr"
    filename: "Expr"
    line_no: int


@dataclass(frozen=True)
class WhileStmt(Stmt):
    condition: "Condition"
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class MultiSetStmt(Stmt):
    names: List[str]
    values: List["Expr"]
    line_no: int


@dataclass(frozen=True)
class ImportStmt(Stmt):
    path: str
    line_no: int


@dataclass(frozen=True)
class TryCatchStmt(Stmt):
    body: List[Stmt]
    catch_body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class MethodDef:
    name: str
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class ObjectDefStmt(Stmt):
    name: str
    properties: List[str]
    methods: List[MethodDef]
    line_no: int


@dataclass(frozen=True)
class SetAttrStmt(Stmt):
    obj_name: str
    attr: str
    value: "Expr"
    line_no: int


@dataclass(frozen=True)
class DoMethodStmt(Stmt):
    obj_name: str
    method_name: str
    args: List["Expr"]
    line_no: int


@dataclass(frozen=True)
class AsyncBlockStmt(Stmt):
    body: List[Stmt]
    line_no: int


@dataclass(frozen=True)
class FetchStmt(Stmt):
    url: "Expr"
    line_no: int


@dataclass(frozen=True)
class EmailStmt(Stmt):
    to_addr: Expr
    subject: Expr
    message: Expr
    line_no: int


@dataclass(frozen=True)
class CreateFileStmt(Stmt):
    path: Expr
    line_no: int


@dataclass(frozen=True)
class WriteFileStmt(Stmt):
    content: Expr
    path: Expr
    line_no: int


@dataclass(frozen=True)
class ReadFileStmt(Stmt):
    path: Expr
    var_name: str
    line_no: int


@dataclass(frozen=True)
class DeleteFileStmt(Stmt):
    path: Expr
    line_no: int


@dataclass(frozen=True)
class ListFilesStmt(Stmt):
    path: Expr
    line_no: int


@dataclass(frozen=True)
class ApiCallStmt(Stmt):
    url: Expr
    method: str
    headers: List[tuple[str, Expr]]
    params: List[tuple[str, Expr]]
    store_var: Optional[str]
    line_no: int


@dataclass(frozen=True)
class WebsocketStmt(Stmt):
    port: int
    on_message_body: List[Stmt]
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
class AttrRefExpr(Expr):
    obj_name: str
    attr: str


@dataclass(frozen=True)
class NewObjectExpr(Expr):
    class_name: str


@dataclass(frozen=True)
class ListLiteral(Expr):
    items: List[Expr]


@dataclass(frozen=True)
class ListAccessExpr(Expr):
    kind: str  # "first" | "last"
    list_name: str


@dataclass(frozen=True)
class CountOfExpr(Expr):
    list_name: str


@dataclass(frozen=True)
class RunTaskExpr(Expr):
    task_name: str
    args: List[Expr]


@dataclass(frozen=True)
class BinaryOp(Expr):
    left: Expr
    op: str  # "plus", "minus", "times", "divided_by", "joined_with"
    right: Expr


@dataclass(frozen=True)
class RandomBetweenExpr(Expr):
    low: Expr
    high: Expr


@dataclass(frozen=True)
class ReadFromExpr(Expr):
    filename: Expr


@dataclass(frozen=True)
class StringOpExpr(Expr):
    op: str  # "uppercase" | "lowercase" | "length"
    value: Expr


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
        if toks == ["and", "end"] or toks == ["done"]:
            if stop_at_end:
                return out, i + 1
            if toks == ["done"]:
                raise ParseError(f"Unexpected 'done' on line {lt.line_no}")
            raise ParseError(f"Unexpected 'and end' on line {lt.line_no}")

        # allow else ... inside an if block; handled by caller
        if toks == ["else", "..."] and stop_at_end:
            return out, i

        stmt, i = _parse_stmt(lines, i)
        out.append(stmt)

    if stop_at_end:
        raise ParseError("Oops! You forgot to close your block with 'and end'.")

    return out, i


def _parse_block_until(
    lines: Sequence[LineTokens], start_i: int, *, end_tokens: Sequence[Sequence[str]], context_line_no: int
) -> Tuple[List[Stmt], int]:
    out: List[Stmt] = []
    i = start_i
    while i < len(lines):
        lt = lines[i]
        if any(lt.tokens == list(et) for et in end_tokens):
            return out, i
        stmt, i = _parse_stmt(lines, i)
        out.append(stmt)
    raise ParseError(
        f"Oops! You forgot to close your block started on line {context_line_no}."
    )


def _parse_stmt(lines: Sequence[LineTokens], i: int) -> Tuple[Stmt, int]:
    lt = lines[i]
    toks = lt.tokens
    if not toks:
        return _error_stmt(lines, i, "Empty statement")

    head = toks[0]
    if head == "set":
        # multiple assignment: set a, b, c to 1, 2, 3
        if "to" in toks:
            try:
                to_i = toks.index("to")
                if "," in toks[1:to_i]:
                    return _parse_multi_set(lt), i + 1
            except ValueError:
                pass
        # attribute assignment: set obj.prop to <expr>
        if len(toks) >= 4 and toks[2] == "to" and "." in toks[1]:
            return _parse_set_attr(lt), i + 1
        return _parse_set(lt), i + 1
    if head == "let":
        return _parse_let(lt), i + 1
    if head == "show":
        return _parse_show(lt), i + 1
    if head == "say":
        return _parse_say(lt), i + 1
    if head == "do":
        if len(toks) >= 2 and "." in toks[1]:
            return _parse_do_method(lt), i + 1
        return _parse_do(lt), i + 1
    if head == "ask":
        if toks[:2] == ["ask", "ai"]:
            return _parse_ask_ai(lt), i + 1
        return _parse_ask(lt), i + 1
    if head == "please":
        return _parse_please(lt), i + 1

    if head == "if":
        return _parse_if(lines, i)
    if head == "while":
        return _parse_while(lines, i)
    if head == "repeat":
        return _parse_repeat(lines, i)
    if head == "task":
        return _parse_task(lines, i)

    if head == "give":
        return _parse_return(lt), i + 1

    if head == "add":
        if len(toks) >= 2 and toks[1] == "property":
             # This is handled inside _parse_object, but if it's seen here it's an error
             raise ParseError(f"Oops! 'add property' must be inside a 'create object' block on line {lt.line_no}.")
        return _parse_add_to_list(lt), i + 1

    if head == "save":
        return _parse_save(lt), i + 1

    if head == "import":
        return _parse_import(lt), i + 1

    if head == "try":
        return _parse_try_catch(lines, i)

    if head == "create" and len(toks) >= 3 and toks[1] == "object":
        return _parse_object(lines, i)

    if head == "run" and toks[:2] == ["run", "async"]:
        return _parse_async(lines, i)

    if head == "fetch":
        return _parse_fetch(lt), i + 1

    if head == "send" and toks[:3] == ["send", "email", "to"]:
        return _parse_email(lines, i)

    if head == "create" and toks[:2] == ["create", "file"]:
        return _parse_create_file(lt), i + 1
    if head == "write":
        return _parse_write_file(lt), i + 1
    if head == "read" and toks[:2] == ["read", "file"]:
        return _parse_read_file(lt), i + 1
    if head == "delete" and toks[:2] == ["delete", "file"]:
        return _parse_delete_file(lt), i + 1
    if head == "list" and toks[:2] == ["list", "files"]:
        return _parse_list_files(lt), i + 1

    if head == "call" and toks[:2] == ["call", "api"]:
        return _parse_api_call(lines, i)

    if head == "create" and toks[:4] == ["create", "websocket", "on", "port"]:
        return _parse_websocket(lines, i)

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
    # multiple assignment: set a, b, c to 1, 2, 3
    try:
        to_i = lt.tokens.index("to")
    except ValueError:
        to_i = -1
    if to_i != -1 and "," in lt.tokens[1:to_i]:
        return _parse_multi_set(lt)

    name = lt.tokens[1]
    value_tokens = lt.tokens[3:]
    value = _parse_expr_from_tokens(value_tokens, lt.line_no)
    return SetStmt(name=name, value=value, line_no=lt.line_no)


def _parse_set_attr(lt: LineTokens) -> SetAttrStmt:
    # set obj.prop to <expr>
    if len(lt.tokens) < 4 or lt.tokens[2] != "to" or "." not in lt.tokens[1]:
        raise ParseError(f"Invalid set statement on line {lt.line_no}")
    obj_name, attr = lt.tokens[1].split(".", 1)
    if not obj_name or not attr:
        raise ParseError(f"Invalid property assignment on line {lt.line_no}. Example: set john.name to \"John\"")
    value = _parse_expr_from_tokens(lt.tokens[3:], lt.line_no)
    return SetAttrStmt(obj_name=obj_name, attr=attr, value=value, line_no=lt.line_no)


def _parse_let(lt: LineTokens) -> SetStmt:
    # let <name> be <expr>
    if len(lt.tokens) < 4:
        raise ParseError(f"Invalid let statement on line {lt.line_no}")
    if lt.tokens[2] != "be":
        raise ParseError(f"Expected 'be' in let statement on line {lt.line_no}")
    name = lt.tokens[1]
    value_tokens = lt.tokens[3:]
    value = _parse_expr_from_tokens(value_tokens, lt.line_no)
    return SetStmt(name=name, value=value, line_no=lt.line_no)


def _parse_show(lt: LineTokens) -> ShowStmt:
    # show <expr...>
    if len(lt.tokens) < 2:
        raise ParseError(f"Invalid show statement on line {lt.line_no}")
    # show all <listname>
    if len(lt.tokens) == 3 and lt.tokens[1] == "all":
        return ShowStmt(parts=[_parse_expr_from_tokens(["all", lt.tokens[2]], lt.line_no)], line_no=lt.line_no)
    parts = _parse_show_parts(lt.tokens[1:], lt.line_no)
    return ShowStmt(parts=parts, line_no=lt.line_no)


def _parse_add_to_list(lt: LineTokens) -> AddToListStmt:
    # add <item> to <listname>
    if len(lt.tokens) < 4:
        raise ParseError(f"Invalid add statement on line {lt.line_no}. Example: add orange to fruits")
    if lt.tokens[-2] != "to":
        raise ParseError(f"Invalid add statement on line {lt.line_no}. Example: add orange to fruits")
    item_tokens = lt.tokens[1:-2]
    item_expr = _parse_expr_from_tokens(item_tokens, lt.line_no)
    return AddToListStmt(item=item_expr, list_name=lt.tokens[-1], line_no=lt.line_no)


def _parse_save(lt: LineTokens) -> SaveStmt:
    # save <content expr> to <filename expr>
    if len(lt.tokens) < 4:
        raise ParseError(
            f"Invalid save statement on line {lt.line_no}. Example: save \"hello\" to \"file.txt\""
        )
    if "to" not in lt.tokens[1:]:
        raise ParseError(
            f"Invalid save statement on line {lt.line_no}. Example: save \"hello\" to \"file.txt\""
        )
    to_i = lt.tokens.index("to")
    if to_i <= 1 or to_i >= len(lt.tokens) - 1:
        raise ParseError(
            f"Invalid save statement on line {lt.line_no}. Example: save \"hello\" to \"file.txt\""
        )
    content_tokens = lt.tokens[1:to_i]
    filename_tokens = lt.tokens[to_i + 1 :]
    content = _parse_expr_from_tokens(content_tokens, lt.line_no)
    filename = _parse_expr_from_tokens(filename_tokens, lt.line_no)
    return SaveStmt(content=content, filename=filename, line_no=lt.line_no)


def _parse_multi_set(lt: LineTokens) -> MultiSetStmt:
    # set a, b, c to 1, 2, 3
    if lt.tokens[0] != "set" or len(lt.tokens) < 4:
        raise ParseError(f"Invalid set statement on line {lt.line_no}")
    if "to" not in lt.tokens:
        raise ParseError(f"Expected 'to' in set statement on line {lt.line_no}")
    to_i = lt.tokens.index("to")
    if to_i <= 1:
        raise ParseError(f"Invalid multiple assignment on line {lt.line_no}. Example: set a, b to 1, 2")

    name_tokens = lt.tokens[1:to_i]
    value_tokens = lt.tokens[to_i + 1 :]

    names: List[str] = []
    current: List[str] = []
    for t in name_tokens:
        if t == ",":
            if not current:
                raise ParseError(f"Invalid multiple assignment on line {lt.line_no}. Example: set a, b to 1, 2")
            names.append("".join(current).strip())
            current = []
            continue
        current.append(t)
    if current:
        names.append("".join(current).strip())

    values: List[Expr] = []
    current_expr: List[str] = []
    for t in value_tokens:
        if t == ",":
            if not current_expr:
                raise ParseError(f"Invalid multiple assignment on line {lt.line_no}. Example: set a, b to 1, 2")
            values.append(_parse_expr_from_tokens(current_expr, lt.line_no))
            current_expr = []
            continue
        current_expr.append(t)
    if current_expr:
        values.append(_parse_expr_from_tokens(current_expr, lt.line_no))

    if not names:
        raise ParseError(f"Invalid multiple assignment on line {lt.line_no}. Example: set a, b to 1, 2")
    if len(names) != len(values):
        raise ParseError(
            f"Invalid multiple assignment on line {lt.line_no}. You gave {len(names)} names but {len(values)} values."
        )
    return MultiSetStmt(names=names, values=values, line_no=lt.line_no)


def _parse_while(lines: Sequence[LineTokens], i: int) -> Tuple[WhileStmt, int]:
    lt = lines[i]
    # while <name> is <comparison> ...
    if len(lt.tokens) < 5:
        raise ParseError(f"Invalid while statement on line {lt.line_no}. Example: while age is less than 18 ...")
    if lt.tokens[-1] != "...":
        raise ParseError(f"Expected '...' to start while block on line {lt.line_no}")
    if lt.tokens[2] != "is":
        raise ParseError(f"Expected 'is' in while statement on line {lt.line_no}")

    name = lt.tokens[1]
    op, rhs_tokens = _parse_comparison(lt.tokens[3:-1], lt.line_no)
    right = _parse_expr_from_tokens(rhs_tokens, lt.line_no)
    cond = Condition(name=name, op=op, right=right)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return WhileStmt(condition=cond, body=body, line_no=lt.line_no), next_i


def _parse_show_parts(tokens: Sequence[str], line_no: int) -> List[Expr]:
    # Split into multiple expressions.
    # - If we see a 'joined with' operator, that whole remaining sequence is a single expression.
    # - If we see a math operator, we parse <left> <op> <right> where left/right are single-token.
    # - Otherwise, each token is treated as its own single-token expression.
    out: List[Expr] = []
    i = 0
    while i < len(tokens):
        # string operations: uppercase/lowercase/length of <expr>
        if i + 2 < len(tokens) and tokens[i] in ("uppercase", "lowercase", "length") and tokens[i + 1] == "of":
            expr = _parse_expr_from_tokens(tokens[i:], line_no)
            out.append(expr)
            return out

        # list helper expressions
        if i + 3 < len(tokens) and tokens[i] in ("first", "last") and tokens[i + 1] == "item" and tokens[i + 2] == "of":
            out.append(_parse_expr_from_tokens(tokens[i : i + 4], line_no))
            i += 4
            continue
        if i + 2 < len(tokens) and tokens[i] == "count" and tokens[i + 1] == "of":
            out.append(_parse_expr_from_tokens(tokens[i : i + 3], line_no))
            i += 3
            continue

        # joined with consumes the rest (supports: <left> joined with <right>, nested if needed)
        if "joined" in tokens[i:]:
            j = i
            while j < len(tokens) - 1:
                if tokens[j] == "joined" and tokens[j + 1] == "with":
                    expr = _parse_expr_from_tokens(tokens[i:], line_no)
                    out.append(expr)
                    return out
                j += 1

        # math op as 3 or 4 tokens: a plus b | a minus b | a times b | a divided by b
        if i + 2 < len(tokens) and tokens[i + 1] in ("plus", "minus", "times"):
            expr = _parse_expr_from_tokens(tokens[i : i + 3], line_no)
            out.append(expr)
            i += 3
            continue
        if i + 3 < len(tokens) and tokens[i + 1] == "divided" and tokens[i + 2] == "by":
            expr = _parse_expr_from_tokens(tokens[i : i + 4], line_no)
            out.append(expr)
            i += 4
            continue

        out.append(_parse_expr_from_tokens([tokens[i]], line_no))
        i += 1

    return out


def _parse_say(lt: LineTokens) -> ShowStmt:
    # say <expr...>
    # alias of show
    lt2 = LineTokens(line_no=lt.line_no, raw=lt.raw, tokens=["show", *lt.tokens[1:]])
    return _parse_show(lt2)


def _parse_do(lt: LineTokens) -> DoStmt:
    # do <taskname> [with <arg1> (and <arg2> ...)]
    if len(lt.tokens) < 2:
        raise ParseError(f"Invalid do statement on line {lt.line_no}")

    name = lt.tokens[1]
    args: List[Expr] = []
    if len(lt.tokens) == 2:
        return DoStmt(task_name=name, args=args, line_no=lt.line_no)

    if lt.tokens[2] != "with":
        raise ParseError(f"Invalid do statement on line {lt.line_no}. Did you mean: do {name} with ...")

    arg_tokens = lt.tokens[3:]
    args = _parse_arg_list(arg_tokens, lt.line_no)
    return DoStmt(task_name=name, args=args, line_no=lt.line_no)


def _parse_do_method(lt: LineTokens) -> DoMethodStmt:
    # do obj.method [with <args>]
    if len(lt.tokens) < 2 or "." not in lt.tokens[1]:
        raise ParseError(f"Invalid do statement on line {lt.line_no}")
    obj_name, method_name = lt.tokens[1].split(".", 1)
    if not obj_name or not method_name:
        raise ParseError(f"Invalid method call on line {lt.line_no}. Example: do john.greet")
    args: List[Expr] = []
    if len(lt.tokens) == 2:
        return DoMethodStmt(obj_name=obj_name, method_name=method_name, args=args, line_no=lt.line_no)
    if lt.tokens[2] != "with":
        raise ParseError(f"Invalid do statement on line {lt.line_no}. Did you mean: do {obj_name}.{method_name} with ...")
    args = _parse_arg_list(lt.tokens[3:], lt.line_no)
    return DoMethodStmt(obj_name=obj_name, method_name=method_name, args=args, line_no=lt.line_no)


def _parse_import(lt: LineTokens) -> ImportStmt:
    # import "file.read"
    if len(lt.tokens) != 2:
        raise ParseError(f"Invalid import on line {lt.line_no}. Example: import \"mymodule.read\"")
    p = lt.tokens[1]
    if not (p.startswith('"') and p.endswith('"')):
        raise ParseError(f"Import path must be in quotes on line {lt.line_no}. Example: import \"mymodule.read\"")
    return ImportStmt(path=p[1:-1], line_no=lt.line_no)


def _parse_try_catch(lines: Sequence[LineTokens], i: int) -> Tuple[TryCatchStmt, int]:
    lt = lines[i]
    if lt.tokens != ["try", "..."]:
        raise ParseError(f"Invalid try on line {lt.line_no}. Example: try ...")

    body, next_i = _parse_block_until(lines, i + 1, end_tokens=[("catch", "errors", "...")], context_line_no=lt.line_no)
    if next_i >= len(lines) or lines[next_i].tokens != ["catch", "errors", "..."]:
        raise ParseError(f"Expected 'catch errors ...' after try block started on line {lt.line_no}")
    catch_body, end_i = _parse_block(lines, next_i + 1, stop_at_end=True)
    return TryCatchStmt(body=body, catch_body=catch_body, line_no=lt.line_no), end_i


def _parse_object(lines: Sequence[LineTokens], i: int) -> Tuple[ObjectDefStmt, int]:
    lt = lines[i]
    # create object "Person"
    if len(lt.tokens) != 3 or lt.tokens[0:2] != ["create", "object"]:
        raise ParseError(f"Invalid object definition on line {lt.line_no}. Example: create object \"Person\"")
    name_tok = lt.tokens[2]
    if not (name_tok.startswith('"') and name_tok.endswith('"')):
        raise ParseError(f"Object name must be in quotes on line {lt.line_no}. Example: create object \"Person\"")
    obj_name = name_tok[1:-1]

    properties: List[str] = []
    methods: List[MethodDef] = []
    j = i + 1
    while j < len(lines):
        cur = lines[j]
        toks = cur.tokens
        if toks == ["end", "object"]:
            return ObjectDefStmt(name=obj_name, properties=properties, methods=methods, line_no=lt.line_no), j + 1

        if toks[:2] == ["add", "property"]:
            if len(toks) != 3:
                raise ParseError(f"Invalid property on line {cur.line_no}. Example: add property name")
            properties.append(toks[2])
            j += 1
            continue

        if len(toks) == 4 and toks[0:2] == ["add", "method"] and toks[-1] == "...":
            if len(toks) != 4:
                raise ParseError(f"Invalid method definition on line {cur.line_no}. Example: add method greet ...")
            m_name = toks[2]
            m_body, next_j = _parse_block_until(
                lines, j + 1, end_tokens=[("end", "method")], context_line_no=cur.line_no
            )
            if next_j >= len(lines) or lines[next_j].tokens != ["end", "method"]:
                raise ParseError(f"Expected 'end method' for method started on line {cur.line_no}")
            methods.append(MethodDef(name=m_name, body=m_body, line_no=cur.line_no))
            j = next_j + 1
            continue

        raise ParseError(
            f"Oops! I don't understand '{toks[0]}' inside object on line {cur.line_no}."
        )

    raise ParseError(f"Oops! You forgot to close your object started on line {lt.line_no} with 'end object'.")


def _parse_async(lines: Sequence[LineTokens], i: int) -> Tuple[AsyncBlockStmt, int]:
    lt = lines[i]
    if lt.tokens != ["run", "async", "..."]:
        raise ParseError(f"Invalid async block on line {lt.line_no}. Example: run async ...")
    body, next_i = _parse_block_until(lines, i + 1, end_tokens=[("end", "async")], context_line_no=lt.line_no)
    if next_i >= len(lines) or lines[next_i].tokens != ["end", "async"]:
        raise ParseError(f"Expected 'end async' for async block started on line {lt.line_no}")
    return AsyncBlockStmt(body=body, line_no=lt.line_no), next_i + 1


def _parse_fetch(lt: LineTokens) -> FetchStmt:
    # fetch data from "url"
    if len(lt.tokens) < 4 or lt.tokens[1] != "data" or lt.tokens[2] != "from":
        raise ParseError(f"Invalid fetch on line {lt.line_no}. Example: fetch data from \"https://example.com\"")
    url = _parse_expr_from_tokens(lt.tokens[3:], lt.line_no)
    return FetchStmt(url=url, line_no=lt.line_no)


def _parse_email(lines: Sequence[LineTokens], i: int) -> Tuple[EmailStmt, int]:
    lt = lines[i]
    # send email to "addr"
    if len(lt.tokens) != 4 or lt.tokens[:3] != ["send", "email", "to"]:
        raise ParseError(f"Invalid email start on line {lt.line_no}. Example: send email to \"user@gmail.com\"")
    to_addr = _parse_expr_from_tokens([lt.tokens[3]], lt.line_no)

    j = i + 1
    subject: Optional[Expr] = None
    message: Optional[Expr] = None
    while j < len(lines):
        cur = lines[j]
        toks = cur.tokens
        if toks == ["end", "email"]:
            if subject is None or message is None:
                raise ParseError(f"Email block missing subject or message (started on line {lt.line_no}).")
            return EmailStmt(to_addr=to_addr, subject=subject, message=message, line_no=lt.line_no), j + 1

        if toks and toks[0] == "subject" and len(toks) == 2:
            subject = _parse_expr_from_tokens([toks[1]], cur.line_no)
            j += 1
            continue
        if toks and toks[0] == "message" and len(toks) == 2:
            message = _parse_expr_from_tokens([toks[1]], cur.line_no)
            j += 1
            continue

        raise ParseError(f"Oops! I don't understand '{toks[0]}' inside email on line {cur.line_no}.")

    raise ParseError(f"Oops! You forgot to close your email started on line {lt.line_no} with 'end email'.")


def _parse_create_file(lt: LineTokens) -> CreateFileStmt:
    # create file "path"
    if len(lt.tokens) != 3 or lt.tokens[:2] != ["create", "file"]:
        raise ParseError(f"Invalid create file on line {lt.line_no}. Example: create file \"data.txt\"")
    path = _parse_expr_from_tokens([lt.tokens[2]], lt.line_no)
    return CreateFileStmt(path=path, line_no=lt.line_no)


def _parse_write_file(lt: LineTokens) -> WriteFileStmt:
    # write "Hello" to file "data.txt"
    if len(lt.tokens) != 5 or lt.tokens[2] != "to" or lt.tokens[3] != "file":
        raise ParseError(f"Invalid write file on line {lt.line_no}. Example: write \"Hello\" to file \"data.txt\"")
    content = _parse_expr_from_tokens([lt.tokens[1]], lt.line_no)
    path = _parse_expr_from_tokens([lt.tokens[4]], lt.line_no)
    return WriteFileStmt(content=content, path=path, line_no=lt.line_no)


def _parse_read_file(lt: LineTokens) -> ReadFileStmt:
    # read file "x" into var
    if len(lt.tokens) != 5 or lt.tokens[:2] != ["read", "file"] or lt.tokens[3] != "into":
        raise ParseError(f"Invalid read file on line {lt.line_no}. Example: read file \"data.txt\" into content")
    path = _parse_expr_from_tokens([lt.tokens[2]], lt.line_no)
    return ReadFileStmt(path=path, var_name=lt.tokens[4], line_no=lt.line_no)


def _parse_delete_file(lt: LineTokens) -> DeleteFileStmt:
    # delete file "x"
    if len(lt.tokens) != 3 or lt.tokens[:2] != ["delete", "file"]:
        raise ParseError(f"Invalid delete file on line {lt.line_no}. Example: delete file \"data.txt\"")
    path = _parse_expr_from_tokens([lt.tokens[2]], lt.line_no)
    return DeleteFileStmt(path=path, line_no=lt.line_no)


def _parse_list_files(lt: LineTokens) -> ListFilesStmt:
    # list files in "folder"
    if len(lt.tokens) != 4 or lt.tokens[:3] != ["list", "files", "in"]:
        raise ParseError(f"Invalid list files on line {lt.line_no}. Example: list files in \"myfolder\"")
    path = _parse_expr_from_tokens([lt.tokens[3]], lt.line_no)
    return ListFilesStmt(path=path, line_no=lt.line_no)


def _parse_api_call(lines: Sequence[LineTokens], i: int) -> Tuple[ApiCallStmt, int]:
    lt = lines[i]
    # call api "url"
    if len(lt.tokens) != 3 or lt.tokens[:2] != ["call", "api"]:
        raise ParseError(f"Invalid api call on line {lt.line_no}. Example: call api \"https://api.example.com\"")
    url = _parse_expr_from_tokens([lt.tokens[2]], lt.line_no)

    method = "GET"
    headers: List[tuple[str, Expr]] = []
    params: List[tuple[str, Expr]] = []
    store_var: Optional[str] = None

    j = i + 1
    while j < len(lines):
        cur = lines[j]
        toks = cur.tokens
        if not toks:
            j += 1
            continue
        if toks[0] == "method" and len(toks) == 2:
            m = _parse_expr_from_tokens([toks[1]], cur.line_no)
            if not isinstance(m, StringLiteral):
                raise ParseError(f"Method must be a quoted string on line {cur.line_no}. Example: method \"GET\"")
            method = m.value
            j += 1
            continue
        if toks[0] == "header" and len(toks) == 4 and toks[2] == "value":
            k_expr = _parse_expr_from_tokens([toks[1]], cur.line_no)
            if not isinstance(k_expr, StringLiteral):
                raise ParseError(f"Header name must be text on line {cur.line_no}. Example: header \"Authorization\" value \"key\"")
            v_expr = _parse_expr_from_tokens([toks[3]], cur.line_no)
            headers.append((k_expr.value, v_expr))
            j += 1
            continue
        if toks[0] == "parameter" and len(toks) == 4 and toks[2] == "value":
            k_expr = _parse_expr_from_tokens([toks[1]], cur.line_no)
            if not isinstance(k_expr, StringLiteral):
                raise ParseError(f"Parameter name must be text on line {cur.line_no}. Example: parameter \"city\" value \"Delhi\"")
            v_expr = _parse_expr_from_tokens([toks[3]], cur.line_no)
            params.append((k_expr.value, v_expr))
            j += 1
            continue
        if toks[:3] == ["store", "response", "in"] and len(toks) == 4:
            store_var = toks[3]
            j += 1
            continue

        break

    return ApiCallStmt(url=url, method=method, headers=headers, params=params, store_var=store_var, line_no=lt.line_no), j


def _parse_websocket(lines: Sequence[LineTokens], i: int) -> Tuple[WebsocketStmt, int]:
    lt = lines[i]
    # create websocket on port 8080
    if len(lt.tokens) != 5 or lt.tokens[:4] != ["create", "websocket", "on", "port"]:
        raise ParseError(f"Invalid websocket on line {lt.line_no}. Example: create websocket on port 8080")
    port_tok = lt.tokens[4]
    if not port_tok.isdigit():
        raise ParseError(f"Websocket port must be a number on line {lt.line_no}.")
    port = int(port_tok)

    j = i + 1
    if j >= len(lines) or lines[j].tokens != ["on", "message", "received", "..."]:
        raise ParseError(f"Expected 'on message received ...' after websocket start on line {lt.line_no}.")

    body, next_j = _parse_block_until(
        lines, j + 1, end_tokens=[("end", "websocket")], context_line_no=lines[j].line_no
    )
    if next_j >= len(lines) or lines[next_j].tokens != ["end", "websocket"]:
        raise ParseError(f"Expected 'end websocket' for websocket started on line {lt.line_no}.")
    return WebsocketStmt(port=port, on_message_body=body, line_no=lt.line_no), next_j + 1


def _parse_return(lt: LineTokens) -> ReturnStmt:
    # give back <expr>
    if len(lt.tokens) < 3 or lt.tokens[1] != "back":
        raise ParseError(f"Invalid return statement on line {lt.line_no}. Use: give back value")
    expr = _parse_expr_from_tokens(lt.tokens[2:], lt.line_no)
    return ReturnStmt(value=expr, line_no=lt.line_no)


def _parse_ask(lt: LineTokens) -> AskStmt:
    # ask <name>
    if len(lt.tokens) != 2:
        raise ParseError(f"Invalid ask statement on line {lt.line_no}")
    return AskStmt(name=lt.tokens[1], line_no=lt.line_no)


def _parse_ask_ai(lt: LineTokens) -> AskAIStmt:
    # ask ai "prompt"
    if len(lt.tokens) != 3 or lt.tokens[:2] != ["ask", "ai"]:
        raise ParseError(f"Invalid ask ai statement on line {lt.line_no}. Example: ask ai \"write hello world\"")
    prompt = _parse_expr_from_tokens([lt.tokens[2]], lt.line_no)
    return AskAIStmt(prompt=prompt, line_no=lt.line_no)


def _parse_please(lt: LineTokens) -> AskStmt:
    # please ask <name>
    if len(lt.tokens) != 3 or lt.tokens[1] != "ask":
        raise ParseError(
            f"Invalid statement on line {lt.line_no}. Did you mean: please ask name"
        )
    return AskStmt(name=lt.tokens[2], line_no=lt.line_no)


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

    # not equal to <expr>
    if len(tokens) >= 3 and tokens[0] == "not" and tokens[1] == "equal" and tokens[2] == "to":
        return "!=", list(tokens[3:])

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

    # allow both:
    # repeat 5 times ...
    # repeat 5 times do ...
    if len(lt.tokens) >= 5 and lt.tokens[-2] == "do" and lt.tokens[-3] == "times":
        times_tokens = lt.tokens[1:-3]
    else:
        if lt.tokens[-2] != "times":
            raise ParseError(f"Expected 'times' in repeat statement on line {lt.line_no}")
        times_tokens = lt.tokens[1:-2]

    times_expr = _parse_expr_from_tokens(times_tokens, lt.line_no)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return RepeatStmt(times=times_expr, body=body, line_no=lt.line_no), next_i


def _parse_task(lines: Sequence[LineTokens], i: int) -> Tuple[TaskDefStmt, int]:
    lt = lines[i]
    # task <name> [with <p1> (and <p2> ...)] ...
    if len(lt.tokens) < 3:
        raise ParseError(f"Invalid task statement on line {lt.line_no}")
    if lt.tokens[-1] != "...":
        raise ParseError(f"Expected '...' to start task block on line {lt.line_no}")

    name = lt.tokens[1]
    params: List[str] = []
    if len(lt.tokens) == 3:
        # task <name> ...
        pass
    else:
        # task <name> with ... ...
        if lt.tokens[2] != "with":
            raise ParseError(f"Invalid task statement on line {lt.line_no}. Did you mean: task {name} with x ...")
        params = _parse_param_list(lt.tokens[3:-1], lt.line_no)

    body, next_i = _parse_block(lines, i + 1, stop_at_end=True)
    return TaskDefStmt(name=name, params=params, body=body, line_no=lt.line_no), next_i


def _parse_param_list(tokens: Sequence[str], line_no: int) -> List[str]:
    if not tokens:
        raise ParseError(f"Invalid parameter list on line {line_no}")
    params: List[str] = []
    i = 0
    expect_name = True
    while i < len(tokens):
        tok = tokens[i]
        if expect_name:
            if tok == "and":
                raise ParseError(f"Invalid parameter list on line {line_no}")
            params.append(tok)
            expect_name = False
            i += 1
            continue
        # expecting 'and' or end
        if tok != "and":
            raise ParseError(f"Invalid parameter list on line {line_no}. Use 'and' between parameter names")
        expect_name = True
        i += 1

    if expect_name:
        raise ParseError(f"Invalid parameter list on line {line_no}")
    return params


def _parse_arg_list(tokens: Sequence[str], line_no: int) -> List[Expr]:
    if not tokens:
        raise ParseError(f"Invalid argument list on line {line_no}")
    args: List[Expr] = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "and":
            raise ParseError(f"Invalid argument list on line {line_no}")

        # Arguments are single-token expressions for now (number/string/var)
        args.append(_parse_expr_from_tokens([tokens[i]], line_no))
        i += 1

        if i >= len(tokens):
            break
        if tokens[i] != "and":
            raise ParseError(f"Invalid argument list on line {line_no}. Use 'and' between arguments")
        i += 1

    return args


def _parse_expr_from_tokens(tokens: Sequence[str], line_no: int) -> Expr:
    # object instantiation: new <ClassName>
    if len(tokens) == 2 and tokens[0] == "new":
        return NewObjectExpr(class_name=tokens[1])

    # Multi-token list helpers
    # first item of <listname>
    if len(tokens) == 4 and tokens[0] == "first" and tokens[1] == "item" and tokens[2] == "of":
        return ListAccessExpr(kind="first", list_name=tokens[3])
    if len(tokens) == 4 and tokens[0] == "last" and tokens[1] == "item" and tokens[2] == "of":
        return ListAccessExpr(kind="last", list_name=tokens[3])
    if len(tokens) == 3 and tokens[0] == "count" and tokens[1] == "of":
        return CountOfExpr(list_name=tokens[2])
    if len(tokens) == 2 and tokens[0] == "all":
        # used by: show all fruits
        return VarRef(name=tokens[1])

    # random between <low> and <high>
    if (
        len(tokens) >= 5
        and tokens[0] == "random"
        and tokens[1] == "between"
        and "and" in tokens[2:]
    ):
        and_i = tokens.index("and", 2)
        low_tokens = tokens[2:and_i]
        high_tokens = tokens[and_i + 1 :]
        if not low_tokens or not high_tokens:
            raise ParseError(
                f"Invalid random statement on line {line_no}. Example: set n to random between 1 and 10"
            )
        low = _parse_expr_from_tokens(low_tokens, line_no)
        high = _parse_expr_from_tokens(high_tokens, line_no)
        return RandomBetweenExpr(low=low, high=high)

    # read from <filename>
    if len(tokens) >= 3 and tokens[0] == "read" and tokens[1] == "from":
        filename = _parse_expr_from_tokens(tokens[2:], line_no)
        return ReadFromExpr(filename=filename)

    # string operations: uppercase/lowercase/length of <expr>
    if len(tokens) >= 3 and tokens[1] == "of" and tokens[0] in ("uppercase", "lowercase", "length"):
        v = _parse_expr_from_tokens(tokens[2:], line_no)
        return StringOpExpr(op=tokens[0], value=v)

    # Handle binary operations: <expr> <op> <expr>
    if len(tokens) >= 3:
        # list literal: list a b c
        if tokens[0] == "list":
            items = [_parse_expr_from_tokens([t], line_no) for t in tokens[1:]]
            return ListLiteral(items=items)

        # run <task> with <arg1> (and <arg2> ...)
        if tokens[0] == "run" and len(tokens) >= 4 and tokens[2] == "with":
            task_name = tokens[1]
            args = _parse_arg_list(tokens[3:], line_no)
            return RunTaskExpr(task_name=task_name, args=args)

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

        # attribute reference: obj.prop
        if "." in tok:
            obj_name, attr = tok.split(".", 1)
            if not obj_name or not attr:
                raise ParseError(f"Invalid property reference on line {line_no}. Example: say john.name")
            return AttrRefExpr(obj_name=obj_name, attr=attr)

        if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
            return NumberLiteral(value=int(tok))

        # variable reference
        return VarRef(name=tok)

    raise ParseError(f"Unable to parse expression on line {line_no}")


def _error_stmt(lines: Sequence[LineTokens], i: int, msg: str) -> Tuple[Stmt, int]:
    lt = lines[i]
    raise ParseError(f"{msg} on line {lt.line_no}")
