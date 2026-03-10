from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lexer import LineTokens, lex


class ServerGenError(Exception):
    pass


@dataclass
class EndpointStep:
    kind: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointSpec:
    path: str
    method: str
    steps: List[EndpointStep] = field(default_factory=list)


@dataclass
class LoginSystem:
    users: Dict[str, str] = field(default_factory=dict)
    protected_paths: List[str] = field(default_factory=list)


@dataclass
class ServerSpec:
    port: int = 3000
    db_name: Optional[str] = None
    endpoints: List[EndpointSpec] = field(default_factory=list)
    login: LoginSystem = field(default_factory=LoginSystem)


def _unquote(tok: str) -> str:
    if len(tok) >= 2 and tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    return tok


def _require_quoted(tok: str, *, what: str, line_no: int) -> str:
    if not (len(tok) >= 2 and tok.startswith('"') and tok.endswith('"')):
        raise ServerGenError(
            f"Oops! {what} must be in quotes on line {line_no}. Example: {what.lower()} \"Text\""
        )
    return _unquote(tok)


def _parse_int(tok: str, *, what: str, line_no: int) -> int:
    try:
        return int(_unquote(tok))
    except ValueError:
        raise ServerGenError(f"Invalid {what} '{tok}' on line {line_no}. Expected a number")


def _sqlite_path(db_name: str, *, base_dir: Path) -> Path:
    name = db_name.strip()
    if not name:
        name = "readcode"
    if not name.endswith(".db"):
        name = f"{name}.db"
    return base_dir / name


def _ensure_table(conn: sqlite3.Connection, table: str, cols: Dict[str, Any]) -> None:
    table_id = "".join(c for c in table if c.isalnum() or c == "_")
    if not table_id:
        raise ServerGenError(f"Invalid table name '{table}'.")

    conn.execute(f"CREATE TABLE IF NOT EXISTS {table_id} (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_id})").fetchall()
    }
    for k, v in cols.items():
        col = "".join(c for c in k if c.isalnum() or c == "_")
        if not col or col in existing:
            continue
        t = "INTEGER" if isinstance(v, int) else "TEXT"
        conn.execute(f"ALTER TABLE {table_id} ADD COLUMN {col} {t}")


def _parse_kv_pairs(toks: List[str], *, start: int, line_no: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    i = start
    if (len(toks) - start) % 2 != 0:
        raise ServerGenError(
            f"Invalid key/value pairs on line {line_no}. Example: name \"John\" age 25"
        )
    while i < len(toks):
        key = toks[i]
        val_tok = toks[i + 1]
        if val_tok.startswith('"') and val_tok.endswith('"'):
            out[key] = _unquote(val_tok)
        else:
            try:
                out[key] = int(val_tok)
            except ValueError:
                out[key] = val_tok
        i += 2
    return out


def _parse_server(lines: List[LineTokens]) -> ServerSpec:
    spec = ServerSpec()
    i = 0
    in_endpoint = False
    current_ep: Optional[EndpointSpec] = None
    in_login = False

    while i < len(lines):
        lt = lines[i]
        toks = lt.tokens
        if not toks:
            i += 1
            continue

        if toks[:4] == ["create", "server", "on", "port"]:
            if len(toks) != 5:
                raise ServerGenError(
                    f"Invalid create server on line {lt.line_no}. Example: create server on port 3000"
                )
            spec.port = _parse_int(toks[4], what="port", line_no=lt.line_no)
            i += 1
            continue

        if toks[:3] == ["connect", "to", "database"]:
            if len(toks) != 4:
                raise ServerGenError(
                    f"Invalid connect to database on line {lt.line_no}. Example: connect to database \"mydb\""
                )
            spec.db_name = _require_quoted(toks[3], what="Database name", line_no=lt.line_no)
            i += 1
            continue

        if toks[:2] == ["create", "login"] and toks[2:] == ["system"]:
            in_login = True
            i += 1
            continue

        if in_login and toks[:2] == ["add", "user"]:
            # add user "admin" password "1234"
            if len(toks) != 5 or toks[3] != "password":
                raise ServerGenError(
                    f"Invalid add user on line {lt.line_no}. Example: add user \"admin\" password \"1234\""
                )
            u = _require_quoted(toks[2], what="Username", line_no=lt.line_no)
            pw = _require_quoted(toks[4], what="Password", line_no=lt.line_no)
            spec.login.users[u] = pw
            i += 1
            continue

        if in_login and toks[:2] == ["protect", "endpoint"]:
            if len(toks) != 3:
                raise ServerGenError(
                    f"Invalid protect endpoint on line {lt.line_no}. Example: protect endpoint \"/dashboard\""
                )
            path = _require_quoted(toks[2], what="Endpoint path", line_no=lt.line_no)
            spec.login.protected_paths.append(path)
            i += 1
            continue

        if in_login and toks[:2] == ["end", "login"] and toks[2:] == ["system"]:
            in_login = False
            i += 1
            continue

        if toks[:2] == ["create", "endpoint"]:
            if len(toks) != 5 or toks[3] != "method":
                raise ServerGenError(
                    f"Invalid create endpoint on line {lt.line_no}. Example: create endpoint \"/users\" method \"GET\""
                )
            path = _require_quoted(toks[2], what="Endpoint path", line_no=lt.line_no)
            method = _require_quoted(toks[4], what="Method", line_no=lt.line_no).upper()
            current_ep = EndpointSpec(path=path, method=method)
            spec.endpoints.append(current_ep)
            in_endpoint = True
            i += 1
            continue

        if toks[:2] == ["end", "endpoint"]:
            if not in_endpoint or current_ep is None:
                raise ServerGenError(f"Unexpected 'end endpoint' on line {lt.line_no}.")
            current_ep = None
            in_endpoint = False
            i += 1
            continue

        if in_endpoint and current_ep is not None:
            if toks[:3] == ["show", "all", "users"]:
                current_ep.steps.append(EndpointStep(kind="show_all", args={"table": "users"}))
                i += 1
                continue
            if toks[:2] == ["show", "all"] and len(toks) == 3:
                current_ep.steps.append(EndpointStep(kind="show_all", args={"table": toks[2]}))
                i += 1
                continue
            if toks[:2] == ["ask", "username"]:
                current_ep.steps.append(EndpointStep(kind="ask", args={"var": "username"}))
                i += 1
                continue
            if toks[:2] == ["ask", "password"]:
                current_ep.steps.append(EndpointStep(kind="ask", args={"var": "password"}))
                i += 1
                continue
            if toks[0] == "say" and len(toks) == 2:
                current_ep.steps.append(
                    EndpointStep(kind="say", args={"text": _require_quoted(toks[1], what="Text", line_no=lt.line_no)})
                )
                i += 1
                continue
            if toks[:2] == ["check", "if"]:
                # check if username is "admin" and password is "1234"
                if len(toks) != 9 or toks[3] != "is" or toks[5] != "and" or toks[7] != "is":
                    raise ServerGenError(
                        f"Invalid check if on line {lt.line_no}. Example: check if username is \"admin\" and password is \"1234\""
                    )
                var1 = toks[2]
                val1 = _require_quoted(toks[4], what="Value", line_no=lt.line_no)
                var2 = toks[6]
                val2 = _require_quoted(toks[8], what="Value", line_no=lt.line_no)
                current_ep.steps.append(
                    EndpointStep(
                        kind="check_and",
                        args={"var1": var1, "val1": val1, "var2": var2, "val2": val2},
                    )
                )
                i += 1
                continue

            raise ServerGenError(
                f"Oops! I don't understand '{toks[0]}' inside endpoint on line {lt.line_no}."
            )

        # database ops (global)
        if toks[:3] == ["save", "to", "database"]:
            if len(toks) < 5:
                raise ServerGenError(
                    f"Invalid save to database on line {lt.line_no}. Example: save to database \"users\" name \"John\" age 25"
                )
            table = _require_quoted(toks[3], what="Table", line_no=lt.line_no)
            cols = _parse_kv_pairs(toks, start=4, line_no=lt.line_no)
            spec.endpoints.append(
                EndpointSpec(
                    path="__db__",
                    method="__init__",
                    steps=[EndpointStep(kind="db_save", args={"table": table, "cols": cols})],
                )
            )
            i += 1
            continue

        if toks[:3] == ["get", "from", "database"]:
            # get from database "users" where name is "John"
            if len(toks) != 8 or toks[4] != "where" or toks[6] != "is":
                raise ServerGenError(
                    f"Invalid get from database on line {lt.line_no}. Example: get from database \"users\" where name is \"John\""
                )
            table = _require_quoted(toks[3], what="Table", line_no=lt.line_no)
            col = toks[5]
            val = _require_quoted(toks[7], what="Value", line_no=lt.line_no)
            spec.endpoints.append(
                EndpointSpec(
                    path="__db__",
                    method="__init__",
                    steps=[EndpointStep(kind="db_get", args={"table": table, "col": col, "val": val})],
                )
            )
            i += 1
            continue

        if toks[:3] == ["delete", "from", "database"]:
            if len(toks) != 8 or toks[4] != "where" or toks[6] != "is":
                raise ServerGenError(
                    f"Invalid delete from database on line {lt.line_no}. Example: delete from database \"users\" where name is \"John\""
                )
            table = _require_quoted(toks[3], what="Table", line_no=lt.line_no)
            col = toks[5]
            val = _require_quoted(toks[7], what="Value", line_no=lt.line_no)
            spec.endpoints.append(
                EndpointSpec(
                    path="__db__",
                    method="__init__",
                    steps=[EndpointStep(kind="db_delete", args={"table": table, "col": col, "val": val})],
                )
            )
            i += 1
            continue

        raise ServerGenError(f"Oops! I don't understand '{toks[0]}' on line {lt.line_no}.")

    return spec


def _apply_db_init_steps(spec: ServerSpec, *, base_dir: Path) -> None:
    init_steps: List[EndpointStep] = []
    real_eps: List[EndpointSpec] = []
    for ep in spec.endpoints:
        if ep.path == "__db__" and ep.method == "__init__":
            init_steps.extend(ep.steps)
        else:
            real_eps.append(ep)
    spec.endpoints = real_eps

    if not init_steps:
        return
    if not spec.db_name:
        raise ServerGenError(
            "Database operations require: connect to database \"mydb\""
        )

    db_path = _sqlite_path(spec.db_name, base_dir=base_dir)
    conn = sqlite3.connect(db_path)
    try:
        for st in init_steps:
            if st.kind == "db_save":
                table = st.args["table"]
                cols = st.args["cols"]
                _ensure_table(conn, table, cols)
                keys = list(cols.keys())
                placeholders = ",".join(["?"] * len(keys))
                table_id = "".join(c for c in table if c.isalnum() or c == "_")
                col_ids = ["".join(c for c in k if c.isalnum() or c == "_") for k in keys]
                conn.execute(
                    f"INSERT INTO {table_id} ({','.join(col_ids)}) VALUES ({placeholders})",
                    [cols[k] for k in keys],
                )
            elif st.kind == "db_delete":
                table = st.args["table"]
                table_id = "".join(c for c in table if c.isalnum() or c == "_")
                col = "".join(c for c in st.args["col"] if c.isalnum() or c == "_")
                conn.execute(
                    f"DELETE FROM {table_id} WHERE {col} = ?", [st.args["val"]]
                )
            elif st.kind == "db_get":
                # no side effects; ignore for init
                pass
        conn.commit()
    finally:
        conn.close()


def parse_server_source(source: str) -> ServerSpec:
    lines = lex(source)
    return _parse_server(lines)


def build_flask_app(spec: ServerSpec, *, base_dir: str | Path | None = None):
    try:
        from flask import Flask, jsonify, redirect, request, session
    except Exception as e:  # pragma: no cover
        raise ServerGenError(
            "Flask is required for server generation. Install with: pip install flask"
        ) from e

    if base_dir is None:
        base = Path.cwd()
    else:
        base = Path(base_dir)

    _apply_db_init_steps(spec, base_dir=base)

    app = Flask("readcode_server")
    app.secret_key = "readcode-secret"  # demo only

    db_path: Optional[Path] = None
    if spec.db_name:
        db_path = _sqlite_path(spec.db_name, base_dir=base)

    def db_conn() -> sqlite3.Connection:
        if db_path is None:
            raise ServerGenError("No database connected")
        return sqlite3.connect(db_path)

    @app.before_request
    def _protect() -> None:
        if request.path in spec.login.protected_paths:
            if not session.get("rc_logged_in"):
                return redirect("/login")

    has_custom_login = any(ep.path == "/login" for ep in spec.endpoints)
    if spec.login.users and not has_custom_login:
        @app.route("/login", methods=["GET", "POST"])
        def _login_default():
            if request.method == "GET":
                return (
                    "<form method='post'>"
                    "<input name='username' placeholder='username'/>"
                    "<input name='password' type='password' placeholder='password'/>"
                    "<button type='submit'>Login</button>"
                    "</form>"
                )
            u = request.form.get("username") or (request.json or {}).get("username")
            p = request.form.get("password") or (request.json or {}).get("password")
            if u in spec.login.users and spec.login.users[u] == p:
                session["rc_logged_in"] = True
                return jsonify({"ok": True})
            return jsonify({"ok": False}), 401

    def _fetch_request_value(var: str) -> Optional[str]:
        if request.is_json:
            data = request.get_json(silent=True) or {}
            v = data.get(var)
            return None if v is None else str(v)
        v = request.form.get(var)
        if v is not None:
            return v
        v = request.args.get(var)
        if v is not None:
            return v
        return None

    def _db_select_all(table: str) -> List[Dict[str, Any]]:
        if db_path is None:
            return []
        table_id = "".join(c for c in table if c.isalnum() or c == "_")
        conn = db_conn()
        try:
            try:
                cur = conn.execute(f"SELECT * FROM {table_id}")
            except sqlite3.OperationalError:
                return []
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    for ep in spec.endpoints:
        path = ep.path
        method = ep.method.upper()

        def _make_handler(eps: EndpointSpec):
            def handler():
                ctx: Dict[str, Any] = {}
                say_text: Optional[str] = None
                check_ok: Optional[bool] = None

                for st in eps.steps:
                    if st.kind == "show_all":
                        return jsonify(_db_select_all(st.args["table"]))
                    if st.kind == "ask":
                        v = _fetch_request_value(st.args["var"])
                        ctx[st.args["var"]] = v
                        continue
                    if st.kind == "check_and":
                        v1 = ctx.get(st.args["var1"]) or _fetch_request_value(st.args["var1"])
                        v2 = ctx.get(st.args["var2"]) or _fetch_request_value(st.args["var2"])
                        check_ok = (v1 == st.args["val1"]) and (v2 == st.args["val2"])
                        continue
                    if st.kind == "say":
                        say_text = st.args["text"]
                        continue

                if check_ok is False:
                    return jsonify({"ok": False, "error": "Unauthorized"}), 401
                if say_text is not None:
                    # if a login system exists and credentials match a known user, mark session
                    u = ctx.get("username")
                    p = ctx.get("password")
                    if isinstance(u, str) and isinstance(p, str) and u in spec.login.users and spec.login.users[u] == p:
                        session["rc_logged_in"] = True
                    return jsonify({"ok": True, "message": say_text})
                return jsonify({"ok": True})

            handler.__name__ = f"rc_ep_{abs(hash((eps.path, eps.method))) }"
            return handler

        app.add_url_rule(path, view_func=_make_handler(ep), methods=[method])

    return app


def start_from_source(
    source: str,
    *,
    base_dir: str | Path | None = None,
    run: bool = True,
) -> None:
    spec = parse_server_source(source)
    app = build_flask_app(spec, base_dir=base_dir)
    if run:
        app.run(port=spec.port, debug=False)
