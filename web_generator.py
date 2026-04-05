from __future__ import annotations

import os
import json
import re
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from lexer import LineTokens, lex


class WebGenError(Exception):
    pass


@dataclass
class WebLink:
    text: str
    href: str


@dataclass
class WebForm:
    title: str
    action: Optional[str] = None
    method: str = "get"
    inputs: List[WebFormInput] = field(default_factory=list)
    textareas: List[WebFormTextarea] = field(default_factory=list)
    submit_text: str = "Submit"


@dataclass
class WebFormInput:
    label: str
    type: str = "text"
    required: bool = False


@dataclass
class WebFormTextarea:
    label: str
    rows: int = 3
    required: bool = False


@dataclass
class WebDataOp:
    op: str  # save|get|delete
    key: str
    value: Optional[str] = None
    var: Optional[str] = None


@dataclass
class WebFetch:
    url: str
    var: str


@dataclass
class WebShowAll:
    var: str


@dataclass
class WebStyle:
    font_size_px: Optional[int] = None
    color: Optional[str] = None
    align: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    background: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    radius_px: Optional[int] = None
    margin_px: Optional[int] = None
    padding_px: Optional[int] = None
    hover_background: Optional[str] = None
    gradient_from: Optional[str] = None
    gradient_to: Optional[str] = None
    shadow: Optional[str] = None
    glow: Optional[str] = None


@dataclass
class WebCard:
    title: str
    image_url: str
    link_href: str
    channel: str = "ReadCode Official"
    views: str = "1.2M views"
    time: str = "2 days ago"
    duration: str = "12:34"
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebHeading:
    text: str
    style: WebStyle = field(default_factory=WebStyle)
    shadow: bool = False


@dataclass
class WebParagraph:
    text: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebButton:
    text: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebImage:
    src: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebVideo:
    src: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebAudio:
    src: str
    controls: bool = True


@dataclass
class WebYouTube:
    url: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebButtonLink:
    text: str
    href: str
    style: WebStyle = field(default_factory=WebStyle)


@dataclass
class WebPage:
    title: str
    background_color: str = "white"
    font_color: str = "black"
    heading: Optional[WebHeading] = None
    paragraphs: List[WebParagraph] = field(default_factory=list)
    buttons: List[WebButton] = field(default_factory=list)
    button_links: List[WebButtonLink] = field(default_factory=list)
    images: List[WebImage] = field(default_factory=list)
    videos: List[WebVideo] = field(default_factory=list)
    audios: List[WebAudio] = field(default_factory=list)
    youtubes: List[WebYouTube] = field(default_factory=list)
    navbar_links: List[WebLink] = field(default_factory=list)
    navbar_inputs: List[str] = field(default_factory=list)
    navbar_buttons: List[str] = field(default_factory=list)
    forms: List[WebForm] = field(default_factory=list)
    cards: List[WebCard] = field(default_factory=list)
    data_ops: List[WebDataOp] = field(default_factory=list)
    fetches: List[WebFetch] = field(default_factory=list)
    show_alls: List[WebShowAll] = field(default_factory=list)
    theme: Optional[str] = None
    font: Optional[str] = None
    background_gradient: Optional[Tuple[str, str, str]] = None  # from, to, direction
    icons: List[WebIcon] = field(default_factory=list)
    mobile_friendly: bool = False
    installable: bool = False
    app_icon: Optional[str] = None
    app_name: Optional[str] = None
    splash_color: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None


@dataclass
class WebIcon:
    name: str
    size_px: int = 20
    color: str = "white"


@dataclass
class WebAnim:
    target: str  # heading|button|card
    name: str


@dataclass
class WebGrid:
    columns: int
    gap_px: int = 10
    children: List[object] = field(default_factory=list)


@dataclass
class WebFlex:
    direction: str  # row|column
    align: str = "left"
    gap_px: int = 10
    children: List[object] = field(default_factory=list)


@dataclass
class WebDocument:
    pages: List[WebPage] = field(default_factory=list)


def _slug_to_filename(title: str) -> str:
    s = _slug(title)
    if not s:
        s = "page"
    return f"{s}.html"


def _youtube_id_from_url(url: str) -> str:
    m = re.search(r"[?&]v=([^&]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([^?&/]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/embed/([^?&/]+)", url)
    if m:
        return m.group(1)
    return ""


def _parse_bool(tok: str, *, line_no: int) -> bool:
    t = tok.strip().lower()
    if t in ("yes", "true", "1"):
        return True
    if t in ("no", "false", "0"):
        return False
    raise WebGenError(f"Invalid boolean '{tok}' on line {line_no}. Use yes/no")


def _parse_int(tok: str, *, what: str, line_no: int) -> int:
    try:
        return int(tok)
    except ValueError:
        raise WebGenError(f"Invalid {what} '{tok}' on line {line_no}. Expected a number")


def _parse_size_value(tok: str, *, line_no: int) -> int:
    tok = _unquote(tok)
    if tok.endswith("px"):
        tok = tok[:-2]
    return _parse_int(tok, what="size", line_no=line_no)


def _parse_px_value(tok: str, *, what: str, line_no: int) -> int:
    tok = _unquote(tok)
    if tok.endswith("px"):
        tok = tok[:-2]
    return _parse_int(tok, what=what, line_no=line_no)


def _parse_dim_value(tok: str, *, line_no: int) -> str:
    t = tok.strip()
    if t.lower() == "auto":
        return "auto"
    if t.endswith("%"):
        return t
    if t.endswith("px"):
        return t
    if re.fullmatch(r"\d+", t):
        return f"{t}px"
    return t


def _parse_style_props(tokens: List[str], *, start: int, line_no: int) -> WebStyle:
    style = WebStyle()
    i = start
    while i < len(tokens):
        key = tokens[i]

        if key == "size" and i + 1 < len(tokens):
            style.font_size_px = _parse_size_value(tokens[i + 1], line_no=line_no)
            i += 2
            continue

        if key == "color" and i + 1 < len(tokens):
            style.color = _unquote(tokens[i + 1])
            i += 2
            continue
        if key == "align" and i + 1 < len(tokens):
            style.align = _unquote(tokens[i + 1])
            i += 2
            continue
        if key == "bold" and i + 1 < len(tokens):
            style.bold = _parse_bool(tokens[i + 1], line_no=line_no)
            i += 2
            continue
        if key == "italic" and i + 1 < len(tokens):
            style.italic = _parse_bool(tokens[i + 1], line_no=line_no)
            i += 2
            continue
        if key == "background" and i + 1 < len(tokens):
            style.background = _unquote(tokens[i + 1])
            i += 2
            continue
        if key == "width" and i + 1 < len(tokens):
            style.width = _parse_dim_value(_unquote(tokens[i + 1]), line_no=line_no)
            i += 2
            continue
        if key == "height" and i + 1 < len(tokens):
            style.height = _parse_dim_value(_unquote(tokens[i + 1]), line_no=line_no)
            i += 2
            continue
        if key == "radius" and i + 1 < len(tokens):
            style.radius_px = _parse_px_value(tokens[i + 1], what="radius", line_no=line_no)
            i += 2
            continue
        if key == "margin" and i + 1 < len(tokens):
            style.margin_px = _parse_px_value(tokens[i + 1], what="margin", line_no=line_no)
            i += 2
            continue
        if key == "padding" and i + 1 < len(tokens):
            style.padding_px = _parse_px_value(tokens[i + 1], what="padding", line_no=line_no)
            i += 2
            continue
        if key == "hover" and i + 2 < len(tokens) and tokens[i + 1] == "background":
            style.hover_background = _unquote(tokens[i + 2])
            i += 3
            continue

        if key == "gradient" and i + 3 < len(tokens) and tokens[i + 2] == "to":
            style.gradient_from = _unquote(tokens[i + 1])
            style.gradient_to = _unquote(tokens[i + 3])
            i += 4
            continue

        if key == "shadow" and i + 1 < len(tokens):
            style.shadow = _unquote(tokens[i + 1])
            i += 2
            continue

        if key == "glow" and i + 1 < len(tokens):
            style.glow = _unquote(tokens[i + 1])
            i += 2
            continue

        raise WebGenError(
            f"Invalid style property '{key}' on line {line_no}. Supported: size, color, align, bold, italic, background, width, height, radius, margin, padding, hover background, gradient <from> to <to>, shadow <value>, glow <color>"
        )

    return style


def _expect(tokens: List[str], expected: List[str], *, line_no: int) -> None:
    if tokens[: len(expected)] != expected:
        raise WebGenError(
            f"Oops! I expected: {' '.join(expected)} on line {line_no}. Got: {' '.join(tokens)}"
        )


def _unquote(tok: str) -> str:
    if len(tok) >= 2 and tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    return tok


def _require_quoted(tok: str, *, what: str, line_no: int) -> str:
    if not (len(tok) >= 2 and tok.startswith('"') and tok.endswith('"')):
        raise WebGenError(
            f"Oops! {what} must be in quotes on line {line_no}. Example: {what.lower()} \"Text\""
        )
    return tok[1:-1]


def _parse_goes_to(tokens: List[str], *, line_no: int) -> Tuple[str, str]:
    # add link "Home" goes to "/"
    _expect(tokens, ["add", "link"], line_no=line_no)
    if len(tokens) < 6:
        raise WebGenError(
            f"Invalid link on line {line_no}. Example: add link \"Home\" goes to \"/\""
        )
    text = _require_quoted(tokens[2], what="Link text", line_no=line_no)
    if tokens[3:6] != ["goes", "to", tokens[5]]:
        pass
    if tokens[3] != "goes" or tokens[4] != "to":
        raise WebGenError(
            f"Invalid link on line {line_no}. Example: add link \"Home\" goes to \"/\""
        )
    href = _require_quoted(tokens[5], what="Link URL", line_no=line_no)
    return text, href


def _parse_card(tokens: List[str], *, line_no: int) -> WebCard:
    # Base:
    # add card "Title" with image "url" with link "/"
    # Optional (any order after base):
    # by "Channel" views "1.2M views" time "2 days ago" duration "12:34"
    # width "300" radius "12" margin "10" padding "10" hover background "#222"

    if tokens[0:2] != ["add", "card"]:
        raise WebGenError(f"Invalid card on line {line_no}.")
    if len(tokens) < 9:
        raise WebGenError(
            f"Invalid card on line {line_no}. Example: add card \"Title\" with image \"url\" with link \"/\""
        )

    if tokens[3:5] != ["with", "image"] or tokens[6:8] != ["with", "link"]:
        raise WebGenError(
            f"Invalid card on line {line_no}. Example: add card \"Title\" with image \"url\" with link \"/\""
        )

    title = _require_quoted(tokens[2], what="Card title", line_no=line_no)
    image_url = _require_quoted(tokens[5], what="Image URL", line_no=line_no)
    link_href = _require_quoted(tokens[8], what="Link", line_no=line_no)

    card = WebCard(title=title, image_url=image_url, link_href=link_href)

    i = 9
    while i < len(tokens):
        key = tokens[i]
        if key == "by" and i + 1 < len(tokens):
            card.channel = _require_quoted(tokens[i + 1], what="Channel", line_no=line_no)
            i += 2
            continue
        if key == "views" and i + 1 < len(tokens):
            card.views = _require_quoted(tokens[i + 1], what="Views", line_no=line_no)
            i += 2
            continue
        if key == "time" and i + 1 < len(tokens):
            card.time = _require_quoted(tokens[i + 1], what="Time", line_no=line_no)
            i += 2
            continue
        if key == "duration" and i + 1 < len(tokens):
            card.duration = _require_quoted(tokens[i + 1], what="Duration", line_no=line_no)
            i += 2
            continue

        if tokens[i] in {
            "size",
            "color",
            "align",
            "bold",
            "italic",
            "background",
            "width",
            "height",
            "radius",
            "margin",
            "padding",
            "hover",
            "gradient",
            "shadow",
            "glow",
        }:
            card.style = _parse_style_props(tokens, start=i, line_no=line_no)
            return card

        raise WebGenError(
            f"Invalid card details on line {line_no}. Supported: by, views, time, duration"
        )

    return card


def generate_from_source(source: str, *, out_dir: str | Path) -> Path:
    lines = lex(source)
    doc = _parse_web_document(lines)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pages_html, css, js = _render_document(doc)

    for filename, html in pages_html:
        (out_dir / filename).write_text(html, encoding="utf-8")
    (out_dir / "styles.css").write_text(css, encoding="utf-8")
    (out_dir / "script.js").write_text(js, encoding="utf-8")

    installable_pages = [p for p in doc.pages if getattr(p, "installable", False)]
    if installable_pages:
        p0 = installable_pages[0]
        app_name = p0.app_name or p0.title
        icon = p0.app_icon or "icon.png"
        theme_color = p0.splash_color or "#0f0f0f"
        manifest = {
            "name": app_name,
            "short_name": app_name,
            "start_url": "index.html",
            "display": "standalone",
            "background_color": theme_color,
            "theme_color": theme_color,
            "icons": [
                {"src": icon, "sizes": "192x192", "type": "image/png"},
                {"src": icon, "sizes": "512x512", "type": "image/png"},
            ],
        }
        (out_dir / "manifest.json").write_text(_js_json(manifest), encoding="utf-8")

        sw = """
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('readcode-v1').then((cache) =>
      cache.addAll(['./', './index.html', './styles.css', './script.js', './manifest.json'])
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
""".strip() + "\n"
        (out_dir / "service-worker.js").write_text(sw, encoding="utf-8")

    return out_dir / (pages_html[0][0] if pages_html else "index.html")


def generate_from_file(file_path: str | Path, *, out_dir: str | Path) -> Path:
    p = Path(file_path)
    source = p.read_text(encoding="utf-8")
    return generate_from_source(source, out_dir=out_dir)


def open_in_browser(html_path: str | Path) -> None:
    p = Path(html_path).resolve()
    webbrowser.open(p.as_uri())


def _parse_web_document(lines: List[LineTokens]) -> WebDocument:
    doc = WebDocument()
    i = 0
    current_page: Optional[WebPage] = None

    while i < len(lines):
        lt = lines[i]
        toks = lt.tokens
        if not toks:
            i += 1
            continue

        if toks[:2] == ["create", "page"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid create page on line {lt.line_no}. Example: create page \"Home\""
                )
            title = _require_quoted(toks[2], what="Page title", line_no=lt.line_no)
            current_page = WebPage(title=title)
            doc.pages.append(current_page)
            i += 1
            continue

        if current_page is None:
            raise WebGenError(
                f"Oops! Start by creating a page first. Example: create page \"Home\" (line {lt.line_no})"
            )

        consumed, new_i = _parse_web_into_page(
            lines,
            start=i,
            page=current_page,
        )
        if not consumed and new_i == i:
            raise WebGenError(
                f"Oops! I don't understand '{toks[0]}' on line {lt.line_no}."
            )
        i = new_i

    if not doc.pages:
        raise WebGenError("No page created. Example: create page \"Home\"")
    return doc


def _parse_web_into_page(
    lines: List[LineTokens],
    *,
    start: int,
    page: WebPage,
    parse_one: bool = False,
) -> Tuple[bool, int]:
    i = start
    in_navbar = False
    in_form = False
    current_form: Optional[WebForm] = None
    any_consumed = False

    while i < len(lines):
        lt = lines[i]
        toks = lt.tokens
        if not toks:
            i += 1
            continue

        # stop at next page
        if toks[:2] == ["create", "page"]:
            return (any_consumed or i > start), i

        # stop at end page
        if toks == ["end", "page"]:
            return True, i + 1

        # set title to "..."
        if toks[:2] == ["set", "title"] and len(toks) >= 4 and toks[2] == "to":
            page.title = _require_quoted(toks[3], what="Title", line_no=lt.line_no)
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # set background color to "blue"
        if toks[:3] == ["set", "background", "color"]:
            if len(toks) != 5 or toks[3] != "to":
                raise WebGenError(
                    f"Invalid background color on line {lt.line_no}. Example: set background color to \"blue\""
                )
            page.background_color = _require_quoted(
                toks[4], what="Background color", line_no=lt.line_no
            )
            i += 1
            if parse_one:
                return True, i
            continue

        # set font color to "white"
        if toks[:3] == ["set", "font", "color"]:
            if len(toks) != 5 or toks[3] != "to":
                raise WebGenError(
                    f"Invalid font color on line {lt.line_no}. Example: set font color to \"white\""
                )
            page.font_color = _require_quoted(toks[4], what="Font color", line_no=lt.line_no)
            i += 1
            if parse_one:
                return True, i
            continue

        # handle generic set statements (ignore them)
        if toks[0] == "set":
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # set background gradient "blue" to "purple" [direction "diagonal"]
        if toks[:3] == ["set", "background", "gradient"]:
            if len(toks) < 6 or toks[4] != "to":
                raise WebGenError(
                    f"Invalid background gradient on line {lt.line_no}. Example: set background gradient \"blue\" to \"purple\" direction \"diagonal\""
                )
            c1 = _require_quoted(toks[3], what="Gradient color", line_no=lt.line_no)
            c2 = _require_quoted(toks[5], what="Gradient color", line_no=lt.line_no)
            direction = "vertical"
            if len(toks) >= 8 and toks[6] == "direction":
                direction = _require_quoted(
                    toks[7], what="Gradient direction", line_no=lt.line_no
                ).lower()
            page.background_gradient = (c1, c2, direction)
            i += 1
            if parse_one:
                return True, i
            continue

        # add heading "Welcome"
        if toks[:2] == ["add", "heading"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid heading on line {lt.line_no}. Example: add heading \"Welcome\""
                )
            text = _require_quoted(toks[2], what="Heading", line_no=lt.line_no)
            shadow = False
            filtered = toks[:3]
            j = 3
            while j < len(toks):
                if j + 1 < len(toks) and toks[j] == "shadow":
                    shadow = _parse_bool(toks[j + 1], line_no=lt.line_no)
                    j += 2
                    continue
                filtered.append(toks[j])
                j += 1
            style = _parse_style_props(filtered, start=3, line_no=lt.line_no) if len(filtered) > 3 else WebStyle()
            page.heading = WebHeading(text=text, style=style, shadow=shadow)
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # design layer
        if toks[:2] == ["use", "theme"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid use theme on line {lt.line_no}. Example: use theme \"dark\""
                )
            theme = _require_quoted(toks[2], what="Theme", line_no=lt.line_no).lower()
            if theme not in ("dark", "light", "modern", "minimal"):
                raise WebGenError(
                    f"Unsupported theme '{theme}' on line {lt.line_no}. Supported: dark, light, modern, minimal"
                )
            page.theme = theme
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["use", "font"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid use font on line {lt.line_no}. Example: use font \"Poppins\""
                )
            font = _require_quoted(toks[2], what="Font", line_no=lt.line_no)
            if font not in ("Poppins", "Roboto", "Montserrat"):
                raise WebGenError(
                    f"Unsupported font '{font}' on line {lt.line_no}. Supported: Poppins, Roboto, Montserrat"
                )
            page.font = font
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["add", "icon"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid icon on line {lt.line_no}. Example: add icon \"home\" size \"24\" color \"white\""
                )
            name = _require_quoted(toks[2], what="Icon name", line_no=lt.line_no)
            size_px = 20
            color = "white"
            j = 3
            while j < len(toks):
                if j + 1 < len(toks) and toks[j] == "size":
                    size_px = _parse_int(_unquote(toks[j + 1]), what="size", line_no=lt.line_no)
                    j += 2
                    continue
                if j + 1 < len(toks) and toks[j] == "color":
                    color = _require_quoted(toks[j + 1], what="Color", line_no=lt.line_no)
                    j += 2
                    continue
                raise WebGenError(
                    f"Invalid icon options on line {lt.line_no}. Supported: size, color"
                )
            page.icons.append(WebIcon(name=name, size_px=size_px, color=color))
            i += 1
            if parse_one:
                return True, i
            continue

        # mobile + PWA + meta
        if toks[:4] == ["make", "page", "mobile", "friendly"]:
            page.mobile_friendly = True
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["make", "page", "installable"]:
            page.installable = True
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["add", "app", "icon"]:
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid app icon on line {lt.line_no}. Example: add app icon \"icon.png\""
                )
            page.app_icon = _require_quoted(toks[3], what="App icon", line_no=lt.line_no)
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["add", "app", "name"]:
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid app name on line {lt.line_no}. Example: add app name \"My App\""
                )
            page.app_name = _require_quoted(toks[3], what="App name", line_no=lt.line_no)
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["add", "splash", "screen"]:
            if len(toks) != 5 or toks[3] != "color":
                raise WebGenError(
                    f"Invalid splash screen on line {lt.line_no}. Example: add splash screen color \"blue\""
                )
            page.splash_color = _require_quoted(
                toks[4], what="Splash color", line_no=lt.line_no
            )
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["add", "meta", "description"]:
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid meta description on line {lt.line_no}. Example: add meta description \"My awesome website\""
                )
            page.meta_description = _require_quoted(
                toks[3], what="Meta description", line_no=lt.line_no
            )
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:3] == ["add", "meta", "keywords"]:
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid meta keywords on line {lt.line_no}. Example: add meta keywords \"readcode, website\""
                )
            page.meta_keywords = _require_quoted(
                toks[3], what="Meta keywords", line_no=lt.line_no
            )
            i += 1
            if parse_one:
                return True, i
            continue

        # add text "..." (synonym for paragraph)
        if toks[:2] == ["add", "text"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid add text on line {lt.line_no}. Example: add text \"Hello\""
                )
            text = _require_quoted(toks[2], what="Text", line_no=lt.line_no)
            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.paragraphs.append(WebParagraph(text=text, style=style))
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # add paragraph "..."
        if toks[:2] == ["add", "paragraph"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid paragraph on line {lt.line_no}. Example: add paragraph \"This is my site\""
                )
            text = _require_quoted(toks[2], what="Paragraph", line_no=lt.line_no)
            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.paragraphs.append(WebParagraph(text=text, style=style))
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # add button "Click Me" [optional goes to "file.html"]
        if toks[:2] == ["add", "button"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid button on line {lt.line_no}. Example: add button \"Click Me\""
                )
            text = _require_quoted(toks[2], what="Button", line_no=lt.line_no)
            # button navigation: add button "Contact Us" goes to "contact.html"
            if len(toks) >= 6 and toks[3] == "goes" and toks[4] == "to":
                href = _require_quoted(toks[5], what="Link URL", line_no=lt.line_no)
                style = _parse_style_props(toks, start=6, line_no=lt.line_no) if len(toks) > 6 else WebStyle()
                page.button_links.append(WebButtonLink(text=text, href=href, style=style))
                i += 1
                any_consumed = True
                if parse_one:
                    return True, i
                continue

            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.buttons.append(WebButton(text=text, style=style))
            i += 1
            any_consumed = True
            if parse_one:
                return True, i
            continue

        # add image "pic.jpg"
        if toks[:2] == ["add", "image"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid image on line {lt.line_no}. Example: add image \"pic.jpg\""
                )
            src = _require_quoted(toks[2], what="Image", line_no=lt.line_no)
            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.images.append(WebImage(src=src, style=style))
            i += 1
            if parse_one:
                return True, i
            continue

        # add video "video.mp4" width "600" height "400"
        if toks[:2] == ["add", "video"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid video on line {lt.line_no}. Example: add video \"video.mp4\""
                )
            src = _require_quoted(toks[2], what="Video", line_no=lt.line_no)
            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.videos.append(WebVideo(src=src, style=style))
            i += 1
            if parse_one:
                return True, i
            continue

        # add audio "song.mp3" controls yes
        if toks[:2] == ["add", "audio"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid audio on line {lt.line_no}. Example: add audio \"song.mp3\""
                )
            src = _require_quoted(toks[2], what="Audio", line_no=lt.line_no)
            controls = True
            if len(toks) >= 5 and toks[3] == "controls":
                controls = _parse_bool(toks[4], line_no=lt.line_no)
                if len(toks) != 5:
                    raise WebGenError(
                        f"Invalid audio on line {lt.line_no}. Example: add audio \"song.mp3\" controls yes"
                    )
            elif len(toks) != 3:
                raise WebGenError(
                    f"Invalid audio on line {lt.line_no}. Example: add audio \"song.mp3\" controls yes"
                )
            page.audios.append(WebAudio(src=src, controls=controls))
            i += 1
            if parse_one:
                return True, i
            continue

        # add youtube "https://youtube.com/watch?v=xxx"
        if toks[:2] == ["add", "youtube"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid youtube on line {lt.line_no}. Example: add youtube \"https://youtube.com/watch?v=xxx\""
                )
            url = _require_quoted(toks[2], what="YouTube URL", line_no=lt.line_no)
            style = _parse_style_props(toks, start=3, line_no=lt.line_no) if len(toks) > 3 else WebStyle()
            page.youtubes.append(WebYouTube(url=url, style=style))
            i += 1
            if parse_one:
                return True, i
            continue

        # navbar
        if toks == ["create", "navbar"]:
            in_navbar = True
            i += 1
            if parse_one:
                return True, i
            continue

        if toks == ["end", "navbar"]:
            in_navbar = False
            i += 1
            if parse_one:
                return True, i
            continue

        if in_navbar and toks[:2] == ["add", "link"]:
            text, href = _parse_goes_to(toks, line_no=lt.line_no)
            page.navbar_links.append(WebLink(text=text, href=href))
            i += 1
            if parse_one:
                return True, i
            continue

        if in_navbar and toks[:2] == ["add", "input"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid navbar input on line {lt.line_no}. Example: add input \"Search...\""
                )
            page.navbar_inputs.append(
                _require_quoted(toks[2], what="Input", line_no=lt.line_no)
            )
            i += 1
            if parse_one:
                return True, i
            continue

        if in_navbar and toks[:2] == ["add", "button"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid navbar button on line {lt.line_no}. Example: add button \"Search\""
                )
            page.navbar_buttons.append(
                _require_quoted(toks[2], what="Button", line_no=lt.line_no)
            )
            i += 1
            if parse_one:
                return True, i
            continue

        # cards
        if toks[:2] == ["add", "card"]:
            page.cards.append(_parse_card(toks, line_no=lt.line_no))
            i += 1
            if parse_one:
                return True, i
            continue

        # animations
        if toks[:2] == ["animate", "heading"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid animate heading on line {lt.line_no}. Example: animate heading \"fadeIn\""
                )
            if not hasattr(page, "anims"):
                page.anims = []  # type: ignore[attr-defined]
            page.anims.append(WebAnim(target="heading", name=_require_quoted(toks[2], what="Animation", line_no=lt.line_no)))  # type: ignore[attr-defined]
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["animate", "button"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid animate button on line {lt.line_no}. Example: animate button \"slideUp\""
                )
            if not hasattr(page, "anims"):
                page.anims = []  # type: ignore[attr-defined]
            page.anims.append(WebAnim(target="button", name=_require_quoted(toks[2], what="Animation", line_no=lt.line_no)))  # type: ignore[attr-defined]
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["animate", "card"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid animate card on line {lt.line_no}. Example: animate card \"zoomIn\""
                )
            if not hasattr(page, "anims"):
                page.anims = []  # type: ignore[attr-defined]
            page.anims.append(WebAnim(target="card", name=_require_quoted(toks[2], what="Animation", line_no=lt.line_no)))  # type: ignore[attr-defined]
            i += 1
            if parse_one:
                return True, i
            continue

        # grid/flex blocks are parsed by capturing raw children as strings for now
        if toks[:2] == ["add", "grid"]:
            if len(toks) < 4 or toks[3] != "columns":
                raise WebGenError(
                    f"Invalid grid on line {lt.line_no}. Example: add grid 3 columns"
                )
            cols = _parse_int(_unquote(toks[2]), what="columns", line_no=lt.line_no)
            gap_px = 10
            if len(toks) >= 6 and toks[4] == "gap":
                gap_px = _parse_px_value(toks[5], what="gap", line_no=lt.line_no)
            block = WebGrid(columns=cols, gap_px=gap_px)
            if not hasattr(page, "blocks"):
                page.blocks = []  # type: ignore[attr-defined]
            page.blocks.append(block)  # type: ignore[attr-defined]
            i += 1
            # consume children until end grid
            while i < len(lines):
                lt2 = lines[i]
                t2 = lt2.tokens
                if t2 == ["end", "grid"]:
                    i += 1
                    return True, i
                consumed2, new_i2 = _parse_web_into_block(lines, start=i, page=page, block=block)
                if not consumed2:
                    raise WebGenError(
                        f"Oops! I don't understand '{t2[0]}' inside grid on line {lt2.line_no}."
                    )
                i = new_i2

            raise WebGenError(f"Missing 'end grid' for grid starting on line {lt.line_no}.")

        if toks[:2] == ["add", "flex"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid flex on line {lt.line_no}. Example: add flex row align \"center\""
                )
            direction = toks[2]
            if direction not in ("row", "column"):
                raise WebGenError(
                    f"Invalid flex direction on line {lt.line_no}. Use row or column"
                )
            align = "left"
            if len(toks) >= 5 and toks[3] == "align":
                align = _require_quoted(toks[4], what="Align", line_no=lt.line_no)
            block = WebFlex(direction=direction, align=align)
            if not hasattr(page, "blocks"):
                page.blocks = []  # type: ignore[attr-defined]
            page.blocks.append(block)  # type: ignore[attr-defined]
            i += 1
            while i < len(lines):
                lt2 = lines[i]
                t2 = lt2.tokens
                if t2 == ["end", "flex"]:
                    i += 1
                    return True, i
                consumed2, new_i2 = _parse_web_into_block(lines, start=i, page=page, block=block)
                if not consumed2:
                    raise WebGenError(
                        f"Oops! I don't understand '{t2[0]}' inside flex on line {lt2.line_no}."
                    )
                i = new_i2
            raise WebGenError(f"Missing 'end flex' for flex starting on line {lt.line_no}.")

        # form
        if toks[:2] == ["add", "form"]:
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid form on line {lt.line_no}. Example: add form \"Contact Us\" action \"submit.php\" method \"post\""
                )
            title = _require_quoted(toks[2], what="Form title", line_no=lt.line_no)
            action: Optional[str] = None
            method = "get"
            j = 3
            while j < len(toks):
                if j + 1 < len(toks) and toks[j] == "action":
                    action = _require_quoted(toks[j + 1], what="Form action", line_no=lt.line_no)
                    j += 2
                    continue
                if j + 1 < len(toks) and toks[j] == "method":
                    method_tok = _require_quoted(toks[j + 1], what="Form method", line_no=lt.line_no).lower()
                    if method_tok not in ("get", "post"):
                        raise WebGenError(
                            f"Invalid form method '{method_tok}' on line {lt.line_no}. Use get or post"
                        )
                    method = method_tok
                    j += 2
                    continue
                raise WebGenError(
                    f"Invalid form options on line {lt.line_no}. Supported: action, method"
                )

            in_form = True
            current_form = WebForm(title=title, action=action, method=method)
            i += 1
            continue

        if toks == ["end", "form"]:
            if not in_form or current_form is None:
                raise WebGenError(f"Unexpected 'end form' on line {lt.line_no}.")
            page.forms.append(current_form)
            current_form = None
            in_form = False
            i += 1
            continue

        if in_form and toks[:2] == ["add", "input"]:
            if current_form is None:
                raise WebGenError(f"Internal error: form missing on line {lt.line_no}.")
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid input on line {lt.line_no}. Example: add input \"Your Name\" type \"email\" required yes"
                )
            label = _require_quoted(toks[2], what="Input label", line_no=lt.line_no)
            itype = "text"
            required = False
            j = 3
            while j < len(toks):
                if j + 1 < len(toks) and toks[j] == "type":
                    itype = _require_quoted(toks[j + 1], what="Input type", line_no=lt.line_no)
                    j += 2
                    continue
                if j + 1 < len(toks) and toks[j] == "required":
                    required = _parse_bool(toks[j + 1], line_no=lt.line_no)
                    j += 2
                    continue
                raise WebGenError(
                    f"Invalid input options on line {lt.line_no}. Supported: type, required"
                )
            current_form.inputs.append(WebFormInput(label=label, type=itype, required=required))
            i += 1
            continue

        if in_form and toks[:2] == ["add", "textarea"]:
            if current_form is None:
                raise WebGenError(f"Internal error: form missing on line {lt.line_no}.")
            if len(toks) < 3:
                raise WebGenError(
                    f"Invalid textarea on line {lt.line_no}. Example: add textarea \"Your Message\" rows \"5\""
                )
            label = _require_quoted(toks[2], what="Textarea label", line_no=lt.line_no)
            rows = 3
            required = False
            j = 3
            while j < len(toks):
                if j + 1 < len(toks) and toks[j] == "rows":
                    rows = _parse_int(_unquote(toks[j + 1]), what="rows", line_no=lt.line_no)
                    j += 2
                    continue
                if j + 1 < len(toks) and toks[j] == "required":
                    required = _parse_bool(toks[j + 1], line_no=lt.line_no)
                    j += 2
                    continue
                raise WebGenError(
                    f"Invalid textarea options on line {lt.line_no}. Supported: rows, required"
                )
            current_form.textareas.append(WebFormTextarea(label=label, rows=rows, required=required))
            i += 1
            continue

        if in_form and toks[:3] == ["add", "submit", "button"]:
            if current_form is None:
                raise WebGenError(f"Internal error: form missing on line {lt.line_no}.")
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid submit button on line {lt.line_no}. Example: add submit button \"Send\""
                )
            current_form.submit_text = _require_quoted(toks[3], what="Submit text", line_no=lt.line_no)
            i += 1
            continue

        # local storage
        if toks[:2] == ["save", "data"]:
            if len(toks) != 5 or toks[3] != "as":
                raise WebGenError(
                    f"Invalid save data on line {lt.line_no}. Example: save data \"username\" as \"John\""
                )
            key = _require_quoted(toks[2], what="Storage key", line_no=lt.line_no)
            value = _require_quoted(toks[4], what="Storage value", line_no=lt.line_no)
            page.data_ops.append(WebDataOp(op="save", key=key, value=value))
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["get", "data"]:
            if len(toks) != 5 or toks[3] != "into":
                raise WebGenError(
                    f"Invalid get data on line {lt.line_no}. Example: get data \"username\" into name"
                )
            key = _require_quoted(toks[2], what="Storage key", line_no=lt.line_no)
            var = toks[4]
            page.data_ops.append(WebDataOp(op="get", key=key, var=var))
            i += 1
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["delete", "data"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid delete data on line {lt.line_no}. Example: delete data \"username\""
                )
            key = _require_quoted(toks[2], what="Storage key", line_no=lt.line_no)
            page.data_ops.append(WebDataOp(op="delete", key=key))
            i += 1
            if parse_one:
                return True, i
            continue

        # api calls
        if toks[:3] == ["fetch", "data", "from"]:
            if len(toks) != 4:
                raise WebGenError(
                    f"Invalid fetch data on line {lt.line_no}. Example: fetch data from \"https://api.example.com/users\""
                )
            url = _require_quoted(toks[3], what="Fetch URL", line_no=lt.line_no)
            # Expect the next line to be: store result in users
            if i + 1 >= len(lines):
                raise WebGenError(
                    f"Missing 'store result in <var>' after fetch on line {lt.line_no}."
                )
            lt2 = lines[i + 1]
            t2 = lt2.tokens
            if t2[:3] != ["store", "result", "in"] or len(t2) != 4:
                raise WebGenError(
                    f"Expected 'store result in <var>' after fetch on line {lt.line_no}."
                )
            var = t2[3]
            page.fetches.append(WebFetch(url=url, var=var))
            i += 2
            if parse_one:
                return True, i
            continue

        if toks[:2] == ["show", "all"]:
            if len(toks) != 3:
                raise WebGenError(
                    f"Invalid show all on line {lt.line_no}. Example: show all users"
                )
            page.show_alls.append(WebShowAll(var=toks[2]))
            i += 1
            if parse_one:
                return True, i
            continue

        if toks == ["show", "page"]:
            # handled by CLI; parser stops here
            return True, i + 1

        return False, i

    return True, i


def _parse_web_into_block(
    lines: List[LineTokens],
    *,
    start: int,
    page: WebPage,
    block: object,
) -> Tuple[bool, int]:
    # Reuse the page parser but store into block.children.
    lt = lines[start]
    toks = lt.tokens
    if not toks:
        return True, start + 1

    # Parse a single statement into a temporary page, then move the produced item into the block.
    tmp = WebPage(title=page.title)
    consumed, new_i = _parse_web_into_page(lines, start=start, page=tmp, parse_one=True)
    if not consumed:
        return False, start

    if tmp.heading:
        block.children.append(tmp.heading)
    if tmp.paragraphs:
        block.children.extend(tmp.paragraphs)
    if tmp.images:
        block.children.extend(tmp.images)
    if tmp.videos:
        block.children.extend(tmp.videos)
    if tmp.audios:
        block.children.extend(tmp.audios)
    if tmp.youtubes:
        block.children.extend(tmp.youtubes)
    if tmp.buttons:
        block.children.extend(tmp.buttons)
    if tmp.button_links:
        block.children.extend(tmp.button_links)
    if tmp.cards:
        block.children.extend(tmp.cards)
    if tmp.forms:
        block.children.extend(tmp.forms)

    return True, new_i


def _render(page: WebPage) -> Tuple[str, str, str]:
    def _style_to_css(
        style: WebStyle,
        *,
        defaults: WebStyle,
        extra: Optional[dict[str, str]] = None,
    ) -> str:
        s = WebStyle(
            font_size_px=style.font_size_px if style.font_size_px is not None else defaults.font_size_px,
            color=style.color if style.color is not None else defaults.color,
            align=style.align if style.align is not None else defaults.align,
            bold=style.bold if style.bold is not None else defaults.bold,
            italic=style.italic if style.italic is not None else defaults.italic,
            background=style.background if style.background is not None else defaults.background,
            width=style.width if style.width is not None else defaults.width,
            height=style.height if style.height is not None else defaults.height,
            radius_px=style.radius_px if style.radius_px is not None else defaults.radius_px,
            margin_px=style.margin_px if style.margin_px is not None else defaults.margin_px,
            padding_px=style.padding_px if style.padding_px is not None else defaults.padding_px,
            hover_background=style.hover_background
            if style.hover_background is not None
            else defaults.hover_background,
            gradient_from=style.gradient_from,
            gradient_to=style.gradient_to,
            shadow=style.shadow,
            glow=style.glow,
        )

        parts: List[str] = []
        if s.font_size_px is not None:
            parts.append(f"font-size:{s.font_size_px}px")
        if s.color:
            parts.append(f"color:{s.color}")
        if s.align:
            parts.append(f"text-align:{s.align}")
        if s.bold is not None:
            parts.append(f"font-weight:{'700' if s.bold else '400'}")
        if s.italic is not None:
            parts.append(f"font-style:{'italic' if s.italic else 'normal'}")
        if s.background:
            parts.append(f"background:{s.background}")
        if s.gradient_from is not None and s.gradient_to is not None:
            parts.append(
                f"background:linear-gradient(135deg,{s.gradient_from},{s.gradient_to})"
            )
        if s.width:
            parts.append(f"width:{s.width}")
        if s.height:
            parts.append(f"height:{s.height}")
        if s.radius_px is not None:
            parts.append(f"border-radius:{s.radius_px}px")
        if s.margin_px is not None:
            parts.append(f"margin:{s.margin_px}px")
        if s.padding_px is not None:
            parts.append(f"padding:{s.padding_px}px")
        if s.shadow:
            parts.append(f"box-shadow:{s.shadow}")
        if s.glow:
            parts.append(f"box-shadow:0 0 0 1px {s.glow}, 0 0 18px {s.glow}")
        if extra:
            for k, v in extra.items():
                parts.append(f"{k}:{v}")
        return ";".join(parts)

    def _gradient_css(from_c: str, to_c: str, direction: str) -> str:
        d = direction.lower().strip()
        if d in ("diagonal", "diag"):
            return f"linear-gradient(135deg,{from_c},{to_c})"
        if d in ("horizontal", "h", "left", "right"):
            return f"linear-gradient(90deg,{from_c},{to_c})"
        return f"linear-gradient(180deg,{from_c},{to_c})"

    def _theme_vars(theme: Optional[str]) -> dict[str, str]:
        t = (theme or "dark").lower()
        if t == "light":
            return {
                "surface": "#ffffff",
                "surface2": "#f6f6f6",
                "border": "rgba(0,0,0,0.12)",
                "hover": "rgba(0,0,0,0.06)",
                "muted": "rgba(0,0,0,0.7)",
                "muted2": "rgba(0,0,0,0.55)",
                "shadow": "0 10px 30px rgba(0,0,0,0.18)",
            }
        if t == "modern":
            return {
                "surface": "rgba(18,18,18,0.86)",
                "surface2": "rgba(18,18,18,0.72)",
                "border": "rgba(255,255,255,0.12)",
                "hover": "rgba(255,255,255,0.10)",
                "muted": "rgba(255,255,255,0.72)",
                "muted2": "rgba(255,255,255,0.58)",
                "shadow": "0 18px 44px rgba(0,0,0,0.62)",
            }
        if t == "minimal":
            return {
                "surface": "transparent",
                "surface2": "transparent",
                "border": "rgba(255,255,255,0.10)",
                "hover": "rgba(255,255,255,0.06)",
                "muted": "rgba(255,255,255,0.72)",
                "muted2": "rgba(255,255,255,0.58)",
                "shadow": "0 0 0 rgba(0,0,0,0)",
            }
        return {
            "surface": "#0f0f0f",
            "surface2": "#121212",
            "border": "rgba(255,255,255,0.12)",
            "hover": "rgba(255,255,255,0.08)",
            "muted": "rgba(255,255,255,0.7)",
            "muted2": "rgba(255,255,255,0.55)",
            "shadow": "0 10px 30px rgba(0,0,0,0.55)",
        }

    def _defaults(*, kind: str) -> WebStyle:
        if kind == "heading":
            return WebStyle(font_size_px=32, color="white", align="left", bold=True, margin_px=10, padding_px=10)
        if kind == "paragraph":
            return WebStyle(font_size_px=16, color="#aaaaaa", align="left", margin_px=10, padding_px=10)
        if kind == "button":
            return WebStyle(background="#ff0000", color="white", radius_px=8, width="auto", margin_px=10, padding_px=10)
        if kind == "image":
            return WebStyle(width="100%", height="auto", align="left", margin_px=10, padding_px=10)
        if kind == "card":
            return WebStyle(margin_px=10, padding_px=10)
        return WebStyle(margin_px=10, padding_px=10)

    hover_css_rules: List[str] = []
    anim_classes: dict[str, str] = {}

    supported_anims = {"fadeIn", "fadeOut", "slideUp", "slideDown", "zoomIn", "bounce"}
    anim_list = getattr(page, "anims", [])
    for a in anim_list:
        if a.name not in supported_anims:
            raise WebGenError(
                f"Unsupported animation '{a.name}' on page '{page.title}'. Supported: fadeIn, fadeOut, slideUp, slideDown, zoomIn, bounce"
            )
        anim_classes[a.target] = f"anim-{a.name}"

    vars = _theme_vars(page.theme)
    bg_value = page.background_color
    if page.background_gradient is not None:
        bg_value = _gradient_css(*page.background_gradient)

    css = f"""
:root {{
  --bg: {bg_value};
  --fg: {page.font_color};
  --muted: {vars["muted"]};
  --muted2: {vars["muted2"]};
  --surface: {vars["surface"]};
  --surface2: {vars["surface2"]};
  --border: {vars["border"]};
  --hover: {vars["hover"]};
  --yt-red: #ff0033;
  --shadow: {vars["shadow"]};
}}

* {{ box-sizing: border-box; }}

html, body {{ height: 100%; }}

body {{
  margin: 0;
  font-family: {(page.font or "Roboto")}, ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
  background: var(--bg);
  background-attachment: fixed;
  background-size: cover;
  color: var(--fg);
}}

/* Scrollbar */
*::-webkit-scrollbar {{ width: 10px; height: 10px; }}
*::-webkit-scrollbar-track {{ background: #0b0b0b; }}
*::-webkit-scrollbar-thumb {{ background: #303030; border-radius: 999px; }}
*::-webkit-scrollbar-thumb:hover {{ background: #3a3a3a; }}

.app {{
  display: grid;
  grid-template-rows: 56px 1fr;
  height: 100vh;
}}

.topbar {{
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--surface);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}}

.topbar .inner {{
  height: 56px;
  padding: 0 16px;
  display: grid;
  grid-template-columns: 240px 1fr 240px;
  align-items: center;
  gap: 16px;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
}}

.logo {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--fg);
  text-decoration: none;
}}

.logo-badge {{
  width: 30px;
  height: 22px;
  border-radius: 6px;
  background: var(--yt-red);
  display: grid;
  place-items: center;
  box-shadow: 0 8px 20px rgba(255,0,51,0.35);
}}

.logo-badge svg {{
  width: 12px;
  height: 12px;
  fill: white;
  transform: translateX(1px);
}}

.search {{
  display: flex;
  justify-content: center;
}}

.search .box {{
  width: min(720px, 100%);
  display: grid;
  grid-template-columns: 1fr 60px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  overflow: hidden;
  background: #121212;
}}

.search input {{
  border: none;
  outline: none;
  padding: 10px 14px;
  background: transparent;
  color: var(--fg);
}}

.search button {{
  border: none;
  background: #222;
  color: var(--fg);
  cursor: pointer;
}}

.search button:hover {{ background: #2a2a2a; }}

.actions {{
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}}

.icon-btn {{
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.06);
  display: grid;
  place-items: center;
  cursor: pointer;
}}

.icon-btn:hover {{ background: rgba(255,255,255,0.10); }}

.layout {{
  display: grid;
  grid-template-columns: 240px 1fr;
  height: calc(100vh - 56px);
}}

.sidebar {{
  background: var(--surface);
  border-right: 1px solid rgba(255,255,255,0.06);
  padding: 12px 8px;
  overflow: auto;
}}

.side-item {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  color: var(--fg);
  text-decoration: none;
  opacity: 0.95;
}}

.side-item:hover {{ background: rgba(255,255,255,0.06); }}

.side-item .ico {{
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  opacity: 0.9;
}}

.content {{
  background: var(--bg);
  overflow: auto;
}}

.content-inner {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 18px 22px 48px 22px;
}}

h1 {{
  margin: 6px 0 16px 0;
  font-size: 22px;
  font-weight: 700;
}}

p {{
  margin: 10px 0;
  color: var(--muted);
  line-height: 1.6;
}}

.rc-btn {{
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  background: var(--yt-red);
  color: white;
  cursor: pointer;
  font-weight: 700;
}}

.rc-btn:hover {{ filter: brightness(1.02); }}

.rc-image {{
  display: block;
  max-width: 100%;
}}

.video-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px 16px;
}}

/* Responsive auto */
{'' if not page.mobile_friendly else '''
@media (max-width: 1024px) {
  .content-inner { max-width: 1000px; }
}

@media (max-width: 768px) {
  .content-inner { padding: 14px 14px 42px 14px; }
  h1 { font-size: 20px; }
  .rc-btn { width: 100%; }
}

@media (max-width: 480px) {
  .content-inner { padding: 12px 12px 38px 12px; }
  .video-grid { grid-template-columns: 1fr !important; }
  h1 { font-size: 18px; }
  p { font-size: 14px; }
}
'''}

@media (max-width: 1260px) {{
  .video-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}

@media (max-width: 980px) {{
  .layout {{ grid-template-columns: 88px 1fr; }}
  .side-item span {{ display: none; }}
  .topbar .inner {{ grid-template-columns: 160px 1fr 160px; }}
  .video-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}

@media (max-width: 620px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .sidebar {{ display: none; }}
  .topbar .inner {{ grid-template-columns: 1fr; }}
  .actions {{ display: none; }}
  .search {{ justify-content: stretch; }}
  .video-grid {{ grid-template-columns: 1fr; }}
}}

.video-card {{
  display: block;
  color: var(--fg);
  text-decoration: none;
  border-radius: 14px;
  transition: transform 160ms ease, filter 160ms ease;
}}

.video-card:hover {{
  transform: translateY(-2px);
  filter: drop-shadow(var(--shadow));
}}

.thumb {{
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  background: #1a1a1a;
}}

.thumb img {{
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
}}

.duration {{
  position: absolute;
  right: 8px;
  bottom: 8px;
  font-size: 12px;
  background: rgba(0,0,0,0.75);
  padding: 2px 6px;
  border-radius: 6px;
}}

.play {{
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  opacity: 0;
  transition: opacity 160ms ease;
  background: linear-gradient(to top, rgba(0,0,0,0.35), rgba(0,0,0,0.05));
}}

.video-card:hover .play {{ opacity: 1; }}

.play .bubble {{
  width: 54px;
  height: 54px;
  border-radius: 999px;
  background: rgba(0,0,0,0.55);
  border: 1px solid rgba(255,255,255,0.16);
  display: grid;
  place-items: center;
}}

.play svg {{ width: 18px; height: 18px; fill: white; transform: translateX(1px); }}

.meta {{
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 10px;
  padding: 10px 2px 0 2px;
}}

.avatar {{
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.10);
}}

.title {{
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}

.sub {{
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted2);
  display: grid;
  gap: 2px;
}}

.sub .row {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}}

.dot::before {{ content: "•"; opacity: 0.6; margin: 0 2px; }}
""".strip() + "\n"

    # Topbar search placeholder
    search_placeholder = page.navbar_inputs[0] if page.navbar_inputs else "Search"

    content_parts: List[str] = []
    if page.heading:
        h_defaults = _defaults(kind="heading")
        h_style = _style_to_css(page.heading.style, defaults=h_defaults)
        if page.heading.shadow:
            h_style = (h_style + ";text-shadow:0 8px 18px rgba(0,0,0,0.65)").strip(";")
        cls = anim_classes.get("heading", "")
        cls_attr = f" class=\"{cls}\"" if cls else ""
        content_parts.append(
            f"<h1{cls_attr} style=\"{_html_escape(h_style)}\">{_html_escape(page.heading.text)}</h1>"
        )

    if page.icons:
        icons_html: List[str] = []
        for ic in page.icons:
            fa_name = ic.name.strip().lower()
            # Keep it simple: use Font Awesome solid set.
            icons_html.append(
                f"<i class=\"fa-solid fa-{_html_escape(fa_name)}\" style=\"font-size:{ic.size_px}px;color:{_html_escape(ic.color)};margin:10px;\"></i>"
            )
        content_parts.append("<div>" + "\n".join(icons_html) + "</div>")

    for para in page.paragraphs:
        p_defaults = _defaults(kind="paragraph")
        p_style = _style_to_css(para.style, defaults=p_defaults)
        content_parts.append(f"<p style=\"{_html_escape(p_style)}\">{_html_escape(para.text)}</p>")

    for img_idx, img in enumerate(page.images):
        i_defaults = _defaults(kind="image")

        align = img.style.align if img.style.align is not None else i_defaults.align
        extra: dict[str, str] = {}
        if align == "center":
            extra["margin-left"] = "auto"
            extra["margin-right"] = "auto"
        elif align == "right":
            extra["margin-left"] = "auto"

        i_style = _style_to_css(img.style, defaults=i_defaults, extra=extra)
        content_parts.append(
            f"<img class=\"rc-image\" src=\"{_html_escape(img.src)}\" alt=\"\" style=\"{_html_escape(i_style)}\" loading=\"lazy\" />"
        )

    for v_idx, v in enumerate(page.videos):
        v_style = _style_to_css(v.style, defaults=WebStyle(width="100%", height="auto", margin_px=10, padding_px=10))
        content_parts.append(
            f"<video src=\"{_html_escape(v.src)}\" style=\"{_html_escape(v_style)}\" controls></video>"
        )

    for a_idx, a in enumerate(page.audios):
        controls_attr = " controls" if a.controls else ""
        content_parts.append(f"<audio src=\"{_html_escape(a.src)}\"{controls_attr}></audio>")

    for y_idx, y in enumerate(page.youtubes):
        yt_id = _youtube_id_from_url(y.url)
        if not yt_id:
            raise WebGenError(f"Invalid YouTube URL '{y.url}' on page '{page.title}'")
        y_style = _style_to_css(y.style, defaults=WebStyle(width="100%", height="360px", margin_px=10, padding_px=10))
        content_parts.append(
            f"<iframe style=\"{_html_escape(y_style)}\" src=\"https://www.youtube.com/embed/{_html_escape(yt_id)}\" title=\"YouTube video\" frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\" allowfullscreen></iframe>"
        )

    for btn_idx, btn in enumerate(page.buttons):
        b_defaults = _defaults(kind="button")
        btn_id = f"rc-btn-{btn_idx}" if btn.style.hover_background else ""
        if btn.style.hover_background:
            hover_css_rules.append(
                f"#{btn_id}:hover{{background:{btn.style.hover_background};}}"
            )

        b_style = _style_to_css(
            btn.style,
            defaults=b_defaults,
            extra={"display": "inline-block"},
        )
        id_attr = f" id=\"{btn_id}\"" if btn_id else ""
        b_cls = anim_classes.get("button", "")
        cls_attr = f" {b_cls}" if b_cls else ""
        content_parts.append(
            f"<button class=\"rc-btn{_html_escape(cls_attr)}\" type=\"button\"{id_attr} style=\"{_html_escape(b_style)}\">{_html_escape(btn.text)}</button>"
        )

    for btn_idx, btn in enumerate(page.button_links):
        b_defaults = _defaults(kind="button")
        btn_id = f"rc-btn-link-{btn_idx}" if btn.style.hover_background else ""
        if btn.style.hover_background:
            hover_css_rules.append(
                f"#{btn_id}:hover{{background:{btn.style.hover_background};}}"
            )
        b_style = _style_to_css(
            btn.style,
            defaults=b_defaults,
            extra={"display": "inline-block", "text-decoration": "none"},
        )
        id_attr = f" id=\"{btn_id}\"" if btn_id else ""
        b_cls = anim_classes.get("button", "")
        cls_attr = f" {b_cls}" if b_cls else ""
        content_parts.append(
            f"<a class=\"rc-btn{_html_escape(cls_attr)}\" href=\"{_html_escape(btn.href)}\"{id_attr} style=\"{_html_escape(b_style)}\">{_html_escape(btn.text)}</a>"
        )

    if page.cards:
        cards_html = []
        for card_idx, c in enumerate(page.cards):
            c_defaults = _defaults(kind="card")
            card_id = f"rc-card-{card_idx}" if c.style.hover_background else ""
            if c.style.hover_background:
                hover_css_rules.append(
                    f"#{card_id}:hover{{background:{c.style.hover_background};}}"
                )

            c_style = _style_to_css(
                c.style,
                defaults=c_defaults,
                extra={"overflow": "hidden"} if (c.style.radius_px is not None or c_defaults.radius_px is not None) else None,
            )
            id_attr = f" id=\"{card_id}\"" if card_id else ""
            card_anim = anim_classes.get("card", "")
            cls_attr = f" {card_anim}" if card_anim else ""
            cards_html.append(
                f"""<a class=\"video-card{cls_attr}\" href=\"{_html_escape(c.link_href)}\"{id_attr} style=\"{_html_escape(c_style)}\">
  <div class=\"thumb\">
    <img src=\"{_html_escape(c.image_url)}\" alt=\"{_html_escape(c.title)}\" loading=\"lazy\" />
    <span class=\"duration\">{_html_escape(c.duration)}</span>
    <div class=\"play\">
      <div class=\"bubble\">
        <svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M8 5v14l11-7z\"/></svg>
      </div>
    </div>
  </div>
  <div class=\"meta\">
    <div class=\"avatar\"></div>
    <div>
      <p class=\"title\">{_html_escape(c.title)}</p>
      <div class=\"sub\">
        <div>{_html_escape(c.channel)}</div>
        <div class=\"row\"><span>{_html_escape(c.views)}</span><span class=\"dot\"></span><span>{_html_escape(c.time)}</span></div>
      </div>
    </div>
  </div>
</a>"""
            )
        content_parts.append(
            f"<div class=\"video-grid\">\n" + "\n".join(cards_html) + "\n</div>"
        )

    for form in page.forms:
        fields_html: List[str] = []
        field_idx = 0
        for inp in form.inputs:
            name = _slug(inp.label) or f"field_{field_idx}"
            req = " required" if inp.required else ""
            fields_html.append(
                f"""<label>
  <span>{_html_escape(inp.label)}</span>
  <input name=\"{_html_escape(name)}\" type=\"{_html_escape(inp.type)}\" placeholder=\"{_html_escape(inp.label)}\"{req} />
</label>"""
            )
            field_idx += 1

        for ta in form.textareas:
            name = _slug(ta.label) or f"field_{field_idx}"
            req = " required" if ta.required else ""
            fields_html.append(
                f"""<label>
  <span>{_html_escape(ta.label)}</span>
  <textarea name=\"{_html_escape(name)}\" rows=\"{ta.rows}\" placeholder=\"{_html_escape(ta.label)}\"{req}></textarea>
</label>"""
            )
            field_idx += 1

        attrs: List[str] = [f"data-rc-form=\"{_html_escape(_slug(form.title))}\""]
        if form.action:
            attrs.append(f"action=\"{_html_escape(form.action)}\"")
        if form.method:
            attrs.append(f"method=\"{_html_escape(form.method)}\"")
        attr_str = " ".join(attrs)
        fields = "\n".join(fields_html)
        content_parts.append(
            f"""<div class=\"card\">
  <h2>{_html_escape(form.title)}</h2>
  <form {attr_str}>
    {fields}
    <button class=\"rc-btn\" type=\"submit\">{_html_escape(form.submit_text)}</button>
    <small class=\"hint\">This form is a demo. It will try to POST to the action if provided, otherwise it will alert the data.</small>
  </form>
</div>"""
        )

    if page.show_alls:
        panels: List[str] = []
        for idx, s in enumerate(page.show_alls):
            panels.append(
                f"""<div class=\"card\">
  <h2>Data: {_html_escape(s.var)}</h2>
  <pre class=\"rc-data\" id=\"rc-show-{_html_escape(s.var)}-{idx}\">Loading...</pre>
</div>"""
            )
        content_parts.append("\n".join(panels))

    if hover_css_rules:
        css += "\n" + "\n".join(hover_css_rules) + "\n"

    main_html = "\n".join(content_parts)

    sidebar_items = [
        ("Home", "home"),
        ("Trending", "trending"),
        ("Subscriptions", "subs"),
        ("Library", "library"),
    ]
    sidebar_html = "\n".join(
        [
            f"""<a class=\"side-item\" href=\"#\">
  <span class=\"ico\">{_svg_icon(kind)}</span>
  <span>{_html_escape(label)}</span>
</a>"""
            for label, kind in sidebar_items
        ]
    )

    pwa_head = ""
    if page.installable:
        pwa_head = "\n".join(
            [
                '<link rel="manifest" href="manifest.json" />',
                '<meta name="theme-color" content="' + _html_escape(page.splash_color or "#0f0f0f") + '" />',
                '<link rel="apple-touch-icon" href="' + _html_escape(page.app_icon or "icon.png") + '" />',
            ]
        )

    meta_head = "\n".join(
        [
            (f'<meta name="description" content="{_html_escape(page.meta_description)}" />'
            if page.meta_description
            else ""),
            (f'<meta name="keywords" content="{_html_escape(page.meta_keywords)}" />'
            if page.meta_keywords
            else ""),
        ]
    ).strip()

    html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>{_html_escape(page.title)}</title>
    {meta_head}
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\" />
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin />
    <link href=\"https://fonts.googleapis.com/css2?family={_html_escape((page.font or 'Roboto').replace(' ', '+'))}:wght@400;500;700&display=swap\" rel=\"stylesheet\" />
    <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css\" />
    {pwa_head}
    <link rel=\"stylesheet\" href=\"styles.css\" />
  </head>
  <body>
    <div class=\"app\">
      <header class=\"topbar\">
        <div class=\"inner\">
          <div class=\"brand\">
            <a class=\"logo\" href=\"#\">
              <span class=\"logo-badge\"><svg viewBox=\"0 0 24 24\"><path d=\"M8 5v14l11-7z\"/></svg></span>
              <span>{_html_escape(page.title)}</span>
            </a>
          </div>
          <div class=\"search\">
            <div class=\"box\">
              <input placeholder=\"{_html_escape(search_placeholder)}\" />
              <button type=\"button\" aria-label=\"Search\">{_svg_icon("search")}</button>
            </div>
          </div>
          <div class=\"actions\">
            <button class=\"icon-btn\" type=\"button\" aria-label=\"Create\">{_svg_icon("create")}</button>
            <button class=\"icon-btn\" type=\"button\" aria-label=\"Apps\">{_svg_icon("apps")}</button>
            <button class=\"icon-btn\" type=\"button\" aria-label=\"Notifications\">{_svg_icon("bell")}</button>
            <button class=\"icon-btn\" type=\"button\" aria-label=\"Profile\">{_svg_icon("user")}</button>
          </div>
        </div>
      </header>
      <div class=\"layout\">
        <aside class=\"sidebar\">
          {sidebar_html}
        </aside>
        <main class=\"content\">
          <div class=\"content-inner\">
            {main_html}
          </div>
        </main>
      </div>
    </div>
    <script src=\"script.js\"></script>
  </body>
</html>
"""

    pwa_js = ""
    if page.installable:
        pwa_js = """
  // PWA: service worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('service-worker.js').catch(() => {});
    });
  }

  // PWA: Add to Home Screen prompt
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.createElement('button');
    btn.className = 'rc-btn';
    btn.textContent = 'Add to Home Screen';
    btn.style.position = 'fixed';
    btn.style.right = '16px';
    btn.style.bottom = '16px';
    btn.style.zIndex = '9999';
    btn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      try { await deferredPrompt.userChoice; } catch (_) {}
      deferredPrompt = null;
      btn.remove();
    });
    document.body.appendChild(btn);
  });
""".rstrip()

    js = f"""
(function () {{
  const rcState = {{}};
{pwa_js}

  function setValueByName(name, value) {{
    if (!name) return;
    const el = document.querySelector('[name="' + CSS.escape(name) + '"]');
    if (!el) return;
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {{
      el.value = value == null ? '' : String(value);
    }}
  }}

  function renderShowAll(varName, idx, value) {{
    const el = document.getElementById('rc-show-' + varName + '-' + idx);
    if (!el) return;
    try {{
      el.textContent = JSON.stringify(value, null, 2);
    }} catch (e) {{
      el.textContent = String(value);
    }}
  }}

  async function handleFormSubmit(form) {{
    const action = form.getAttribute('action');
    const method = (form.getAttribute('method') || 'get').toUpperCase();
    const data = new FormData(form);
    const obj = {{}};
    for (const [k, v] of data.entries()) obj[k] = v;

    if (!action) {{
      alert('Form submitted (demo):\n' + JSON.stringify(obj, null, 2));
      return;
    }}

    try {{
      const res = await fetch(action, {{ method, body: data }});
      const text = await res.text();
      alert('Submitted to ' + action + ' (status ' + res.status + '):\n' + text.slice(0, 500));
    }} catch (err) {{
      alert('Submit failed: ' + (err && err.message ? err.message : String(err)));
    }}
  }}

  function initForms() {{
    const forms = document.querySelectorAll('form[data-rc-form]');
    forms.forEach((form) => {{
      form.addEventListener('submit', (e) => {{
        e.preventDefault();
        handleFormSubmit(form);
      }});
    }});
  }}

  function runDataOps() {{
    const ops = { _js_json([{ "op": op.op, "key": op.key, "value": op.value, "var": op.var } for op in page.data_ops]) };
    ops.forEach((op) => {{
      if (op.op === 'save') {{
        localStorage.setItem(op.key, op.value);
      }} else if (op.op === 'get') {{
        const v = localStorage.getItem(op.key);
        if (op.var) {{
          rcState[op.var] = v;
          setValueByName(op.var, v);
        }}
      }} else if (op.op === 'delete') {{
        localStorage.removeItem(op.key);
      }}
    }});
  }}

  async function runFetches() {{
    const fetches = { _js_json([{ "url": f.url, "var": f.var } for f in page.fetches]) };
    for (const f of fetches) {{
      try {{
        const res = await fetch(f.url);
        const ct = res.headers.get('content-type') || '';
        const data = ct.includes('application/json') ? await res.json() : await res.text();
        rcState[f.var] = data;
      }} catch (err) {{
        rcState[f.var] = {{ error: err && err.message ? err.message : String(err) }};
      }}
    }}
  }}

  function renderAllPanels() {{
    const panels = { _js_json([{ "var": s.var } for s in page.show_alls]) };
    panels.forEach((p, idx) => {{
      renderShowAll(p.var, idx, rcState[p.var]);
    }});
  }}

  async function main() {{
    initForms();
    runDataOps();
    await runFetches();
    renderAllPanels();
  }}

  main();
}})();
""".strip() + "\n"

    return html, css, js


def _render_document(doc: WebDocument) -> Tuple[List[Tuple[str, str]], str, str]:
    pages_html: List[Tuple[str, str]] = []
    css: str = ""
    js: str = ""

    for idx, page in enumerate(doc.pages):
        html, page_css, page_js = _render(page)
        if idx == 0:
            css = page_css
            js = page_js
        filename = "index.html" if idx == 0 else _slug_to_filename(page.title)
        pages_html.append((filename, html.replace(f"<span>{_html_escape(page.title)}</span>", f"<span>{_html_escape(page.title)}</span>")))

    anim_css = """
/* Animations */
.anim-fadeIn { animation: rcFadeIn 600ms ease both; }
.anim-fadeOut { animation: rcFadeOut 600ms ease both; }
.anim-slideUp { animation: rcSlideUp 600ms ease both; }
.anim-slideDown { animation: rcSlideDown 600ms ease both; }
.anim-zoomIn { animation: rcZoomIn 600ms ease both; }
.anim-bounce { animation: rcBounce 900ms ease both; }

@keyframes rcFadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes rcFadeOut { from { opacity: 1; } to { opacity: 0; } }
@keyframes rcSlideUp { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes rcSlideDown { from { opacity: 0; transform: translateY(-18px); } to { opacity: 1; transform: translateY(0); } }
@keyframes rcZoomIn { from { opacity: 0; transform: scale(0.94); } to { opacity: 1; transform: scale(1); } }
@keyframes rcBounce {
  0% { transform: translateY(0); }
  30% { transform: translateY(-10px); }
  55% { transform: translateY(0); }
  75% { transform: translateY(-6px); }
  100% { transform: translateY(0); }
}

/* Layout blocks */
.rc-grid { display: grid; }
.rc-flex { display: flex; }
""".strip() + "\n"

    css = css + "\n" + anim_css
    return pages_html, css, js


def _slug(s: str) -> str:
    s2 = s.strip().lower()
    s2 = re.sub(r"[^a-z0-9]+", "_", s2)
    return s2.strip("_")


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _js_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _svg_icon(kind: str) -> str:
    # Tiny inline icons (not a full icon set; just enough for the YouTube-like UI)
    if kind == "search":
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
    if kind == "home":
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" stroke-width="2"><path d="M3 10.5l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>'
    if kind == "trending":
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" stroke-width="2"><path d="M3 17l7-7 4 4 7-7"/><path d="M14 7h7v7"/></svg>'
    if kind == "subs":
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" stroke-width="2"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M10 10l5 2-5 2z"/></svg>'
    if kind == "library":
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" stroke-width="2"><path d="M6 4h12"/><path d="M6 8h12"/><path d="M6 12h12"/><path d="M6 16h12"/></svg>'
    if kind == "create":
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>'
    if kind == "apps":
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="white"><path d="M5 5h4v4H5zM10 5h4v4h-4zM15 5h4v4h-4zM5 10h4v4H5zM10 10h4v4h-4zM15 10h4v4h-4zM5 15h4v4H5zM10 15h4v4h-4zM15 15h4v4h-4z"/></svg>'
    if kind == "bell":
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2"><path d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M13.7 21a2 2 0 01-3.4 0"/></svg>'
    if kind == "user":
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 14.5-4 16 0"/></svg>'
    return ''
