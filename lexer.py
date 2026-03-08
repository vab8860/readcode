from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LineTokens:
    line_no: int
    raw: str
    tokens: List[str]


class LexError(Exception):
    pass


def lex(source: str) -> List[LineTokens]:
    """Lex ReadCode source into per-line tokens.

    This language is intentionally line-oriented. Blocks are introduced by a line
    ending with '...' and terminated by a line equal to 'and end'.

    Tokenization rules:
    - Split on whitespace.
    - Keep quoted strings ("...") together (no escapes for now).
    - Ignore empty lines.
    - Strip leading/trailing whitespace.
    """

    lines: List[LineTokens] = []
    for idx, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        tokens: List[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch.isspace():
                i += 1
                continue

            if ch == '"':
                j = i + 1
                while j < len(line) and line[j] != '"':
                    j += 1
                if j >= len(line) or line[j] != '"':
                    raise LexError(f"Unterminated string on line {idx}")
                tokens.append(line[i : j + 1])
                i = j + 1
                continue

            # normal token
            j = i
            while j < len(line) and (not line[j].isspace()):
                j += 1
            tokens.append(line[i:j])
            i = j

        lines.append(LineTokens(line_no=idx, raw=raw_line, tokens=tokens))

    return lines
