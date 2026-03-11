from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import smtplib
import ssl
import urllib.parse
import urllib.request
import os
from typing import Any, Callable, Dict, List, Optional, Tuple


class IntegrationError(Exception):
    pass


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True


def _load_email_config_from_env() -> EmailConfig:
    host = os.environ.get("READCODE_SMTP_HOST", "")
    port_s = os.environ.get("READCODE_SMTP_PORT", "")
    username = os.environ.get("READCODE_SMTP_USER", "")
    password = os.environ.get("READCODE_SMTP_PASS", "")
    use_tls_s = os.environ.get("READCODE_SMTP_TLS", "true")

    if not host or not port_s or not username or not password:
        raise IntegrationError(
            "Email is not configured. Set env vars: READCODE_SMTP_HOST, READCODE_SMTP_PORT, READCODE_SMTP_USER, READCODE_SMTP_PASS"
        )
    try:
        port = int(port_s)
    except ValueError as e:
        raise IntegrationError("READCODE_SMTP_PORT must be a number") from e

    use_tls = use_tls_s.strip().lower() not in ("0", "false", "no")
    return EmailConfig(host=host, port=port, username=username, password=password, use_tls=use_tls)


def send_email(to_addr: str, subject: str, message: str) -> None:
    cfg = _load_email_config_from_env()

    email_body = (
        f"From: {cfg.username}\r\n"
        f"To: {to_addr}\r\n"
        f"Subject: {subject}\r\n"
        f"\r\n"
        f"{message}\r\n"
    )

    context = ssl.create_default_context()
    try:
        if cfg.use_tls:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=10) as server:
                server.starttls(context=context)
                server.login(cfg.username, cfg.password)
                server.sendmail(cfg.username, [to_addr], email_body)
        else:
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=10, context=context) as server:
                server.login(cfg.username, cfg.password)
                server.sendmail(cfg.username, [to_addr], email_body)
    except Exception as e:
        raise IntegrationError(f"Failed to send email to '{to_addr}'.") from e


def create_file(path: str, *, base_dir: Path) -> None:
    p = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("", encoding="utf-8")


def write_file(path: str, content: str, *, base_dir: Path) -> None:
    p = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def read_file(path: str, *, base_dir: Path) -> str:
    p = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        raise IntegrationError(f"Failed to read file '{path}'.") from e


def delete_file(path: str, *, base_dir: Path) -> None:
    p = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    try:
        p.unlink(missing_ok=True)
    except Exception as e:
        raise IntegrationError(f"Failed to delete file '{path}'.") from e


def list_files(path: str, *, base_dir: Path) -> List[str]:
    p = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    try:
        if not p.exists() or not p.is_dir():
            return []
        return sorted([c.name for c in p.iterdir()])
    except Exception as e:
        raise IntegrationError(f"Failed to list files in '{path}'.") from e


def call_api(
    url: str,
    *,
    method: str,
    headers: Dict[str, str],
    params: Dict[str, str],
    timeout_seconds: int = 5,
) -> str:
    m = method.strip().upper()
    if m not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        raise IntegrationError(f"Unsupported HTTP method: {method}")

    final_url = url
    data: Optional[bytes] = None

    if params:
        if m == "GET":
            parsed = urllib.parse.urlparse(url)
            q = dict(urllib.parse.parse_qsl(parsed.query))
            q.update(params)
            parsed = parsed._replace(query=urllib.parse.urlencode(q))
            final_url = urllib.parse.urlunparse(parsed)
        else:
            data = urllib.parse.urlencode(params).encode("utf-8")

    req = urllib.request.Request(final_url, method=m)
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout_seconds) as resp:
            raw = resp.read()
            try:
                return raw.decode("utf-8")
            except Exception:
                return raw.decode("latin-1", errors="replace")
    except Exception as e:
        raise IntegrationError(f"API call failed: {final_url}") from e


def start_websocket_server(
    *,
    port: int,
    on_message: Callable[[str], Optional[str]],
) -> None:
    try:
        import asyncio
        import websockets
    except ModuleNotFoundError as e:
        raise IntegrationError(
            "websockets is required for websocket servers. Install with: pip install websockets"
        ) from e

    async def handler(ws):
        async for msg in ws:
            reply = on_message(str(msg))
            if reply is not None:
                await ws.send(reply)

    async def main():
        async with websockets.serve(handler, "0.0.0.0", port):
            await asyncio.Future()  # run forever

    asyncio.run(main())
