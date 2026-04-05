from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Optional


class AIError(Exception):
    pass


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
# Default model. Can be overridden by setting GROQ_MODEL in readcode.config.
GROQ_MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = (
    "You are a ReadCode programming language assistant.\n"
    "Generate ONLY valid ReadCode syntax.\n"
    "Never use JavaScript or any other language syntax.\n"
    "Never include explanations, headings, markdown, or code fences.\n"
    "IMPORTANT: ReadCode is line-based. Blocks ALWAYS start with a line ending in '...' and end with a line 'and end'.\n"
    "Use ONLY these statement forms:\n"
    "- set name to value\n"
    "- let name be value\n"
    "- say value\n"
    "- show value\n"
    "- ask name   (NOTE: ask takes ONLY a variable name; never use quoted text after ask)\n"
    "- if the x is equal to y ... (body) and end\n"
    "- if the x is greater than y ... (body) and end\n"
    "- repeat 5 times ... (body) and end\n"
    "- task greet ... (body) and end\n"
    "Expressions MUST use these operators (not symbols):\n"
    "- a plus b\n"
    "- a minus b\n"
    "- a times b\n"
    "- a divided by b\n"
    "- text joined with othertext\n"
    "Strings must be quoted like \"hello\". Empty string is \"\".\n"
    "Formatting rules:\n"
    "- One statement per line\n"
    "- Never put two statements on the same line\n"
    "- Never wrap a statement across multiple lines\n"
    "- Never indent blocks (no leading spaces)\n"
    "Never use: function(), var, return, print(), //, +, -, *, /, { }, ( ), or indentation-based blocks.\n"
)


def _read_config_value(config_path: Path, key: str) -> Optional[str]:
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip()
    return None


def load_groq_api_key(*, base_dir: Path) -> str:
    cur = base_dir.resolve()
    key: Optional[str] = None
    while True:
        config_path = (cur / "readcode.config")
        key = _read_config_value(config_path, "GROQ_API_KEY")
        if key:
            break
        if cur.parent == cur:
            break
        cur = cur.parent

    if not key:
        raise AIError(
            "Missing GROQ_API_KEY. Create readcode.config (in your project folder) with: GROQ_API_KEY=your_key_here"
        )
    if key.lower().startswith("your_key"):
        raise AIError(
            "GROQ_API_KEY is still the placeholder. Update readcode.config with your real Groq API key."
        )
    return key


def _find_readcode_config_dir(*, base_dir: Path) -> Optional[Path]:
    cur = base_dir.resolve()
    while True:
        config_path = cur / "readcode.config"
        if config_path.exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def load_groq_model(*, base_dir: Path) -> str:
    cfg_dir = _find_readcode_config_dir(base_dir=base_dir)
    if cfg_dir is None:
        return GROQ_MODEL
    config_path = cfg_dir / "readcode.config"
    m = _read_config_value(config_path, "GROQ_MODEL")
    return m.strip() if m else GROQ_MODEL


def _extract_groq_error(resp_text: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (code, message) if the response body matches Groq error format."""
    try:
        parsed = json.loads(resp_text)
        err = parsed.get("error") or {}
        code = err.get("code")
        msg = err.get("message")
        return (str(code) if code is not None else None, str(msg) if msg is not None else None)
    except Exception:
        return (None, None)


def groq_generate_readcode(prompt: str, *, base_dir: Path, timeout_seconds: int = 20) -> str:
    try:
        import requests
    except ModuleNotFoundError as e:
        raise AIError("requests is required for AI features. Install with: pip install requests") from e

    api_key = load_groq_api_key(base_dir=base_dir)
    preferred_model = load_groq_model(base_dir=base_dir)

    # Candidate models: try preferred first, then fall back if Groq reports decommission.
    candidates = [
        preferred_model,
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ]
    seen: set[str] = set()
    models: list[str] = []
    for m in candidates:
        if m and m not in seen:
            seen.add(m)
            models.append(m)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_status: Optional[int] = None
    last_body: Optional[str] = None
    raw: Optional[bytes] = None
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
        }

        try:
            resp = requests.post(
                GROQ_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
        except Exception as e:
            print("[Groq] Request failed with exception:", repr(e), file=sys.stderr)
            raise AIError(f"Failed to call Groq API. Exception: {e}") from e

        if 200 <= resp.status_code < 300:
            raw = resp.content
            break

        last_status = resp.status_code
        last_body = resp.text
        code, msg = _extract_groq_error(resp.text)

        print(f"[Groq] HTTP status: {resp.status_code}", file=sys.stderr)
        print(f"[Groq] Model attempted: {model}", file=sys.stderr)
        print("[Groq] Response body:", file=sys.stderr)
        print(resp.text, file=sys.stderr)

        if code == "model_decommissioned":
            continue

        # For non-decommission errors, stop and surface error.
        detail = msg or "See logs above for response body."
        raise AIError(f"Groq API returned HTTP {resp.status_code}. {detail}")

    if raw is None:
        raise AIError(
            f"Groq API returned HTTP {last_status}. All attempted models were rejected (possibly decommissioned)."
        )

    try:
        parsed = json.loads(raw.decode("utf-8"))
        content = parsed["choices"][0]["message"]["content"]
    except Exception as e:
        try:
            print("[Groq] Unexpected JSON response body:", file=sys.stderr)
            print(raw.decode("utf-8", errors="replace"), file=sys.stderr)
        except Exception:
            pass
        raise AIError("Invalid response from Groq API.") from e

    if not isinstance(content, str) or not content.strip():
        raise AIError("Groq returned empty content.")

    # Some models wrap in markdown code fences; strip them.
    out = content.strip()
    if out.startswith("```"):
        lines = out.splitlines()
        # drop first fence line
        lines = lines[1:]
        # drop last fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        out = "\n".join(lines).strip()

    # Normalize whitespace to reduce parse failures due to trailing spaces / wrapped lines.
    normalized_lines: list[str] = []
    for line in out.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = line.strip()
        if not s:
            continue
        normalized_lines.append(s)
    return "\n".join(normalized_lines).strip()
