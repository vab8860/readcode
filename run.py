from __future__ import annotations

import argparse
import sys

from executor import RuntimeErrorRC, execute
from lexer import LexError, lex
from parser import ParseError, parse


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="readcode", description="ReadCode interpreter")
    ap.add_argument("file", help="Path to .read file")
    args = ap.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            src = f.read()

        lines = lex(src)
        program = parse(lines)
        execute(program)
        return 0

    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2
    except (LexError, ParseError, RuntimeErrorRC) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
