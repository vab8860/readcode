from __future__ import annotations

import argparse
from pathlib import Path
import sys

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

        # Web mode: generate an HTML site if the file uses the web DSL
        if "create page" in src.lower():
            out_dir = src_path.parent / f"{src_path.stem}_site"
            html_path = generate_from_source(src, out_dir=out_dir)
            open_in_browser(html_path)
            return 0

        lines = lex(src)
        program = parse(lines)
        execute(program)
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
