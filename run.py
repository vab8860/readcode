from __future__ import annotations

import argparse
from pathlib import Path
import sys


_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from executor import RuntimeErrorRC, execute
from lexer import LexError, lex
from parser import ParseError, parse

from web_generator import WebGenError, generate_from_source, open_in_browser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(prog="readcode", description="ReadCode interpreter")
    ap.add_argument("file", help="Path to .read file")
    args = ap.parse_args(argv)

    try:
        src_path = Path(args.file)
        src = src_path.read_text(encoding="utf-8")

        # ML mode: execute ML/AI building commands if the file uses the ML DSL
        ml_src = src.lower()
        if "load data from" in ml_src or "create neural network" in ml_src:
            try:
                from ml_engine import MLError, run_ml_source
            except ModuleNotFoundError:
                print(
                    "ml_engine.py is not available in your installed ReadCode environment. "
                    "Reinstall ReadCode or run: readcode <file>.read",
                    file=sys.stderr,
                )
                return 1

            try:
                run_ml_source(src, base_dir=src_path.parent)
                return 0
            except MLError as e:
                print(str(e), file=sys.stderr)
                return 1

        # Web mode: generate an HTML site if the file uses the web DSL
        if "create page" in src.lower():
            out_dir = src_path.parent / f"{src_path.stem}_site"
            html_path = generate_from_source(src, out_dir=out_dir)
            open_in_browser(html_path)
            return 0

        # Server mode: start a Flask server if the file uses the server DSL
        if "create server on port" in src.lower():
            try:
                from server_generator import ServerGenError, start_from_source as start_server_from_source
            except ModuleNotFoundError:
                print(
                    "server_generator.py is not available in your installed ReadCode environment. "
                    "Reinstall ReadCode (e.g. pip install -e .) or run: readcode <file>.read",
                    file=sys.stderr,
                )
                return 1
            try:
                start_server_from_source(src, base_dir=src_path.parent, run=True)
                return 0
            except ServerGenError as e:
                print(str(e), file=sys.stderr)
                return 1

        lines = lex(src)
        program = parse(lines)
        execute(program, base_dir=src_path.parent)
        return 0

    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2
    except WebGenError as e:
        print(str(e), file=sys.stderr)
        return 1
    except (LexError, ParseError, RuntimeErrorRC) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
