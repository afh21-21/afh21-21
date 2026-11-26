import base64
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "assets"
USER = "afh21-21"
W = 840
WIB = datetime.timezone(datetime.timedelta(hours=7))

PALETTE = json.loads((ROOT / "data/palette.json").read_text(encoding="utf-8"))
ICONS = json.loads((ROOT / "data/icons.json").read_text(encoding="utf-8"))
METRICS = json.loads((ROOT / "data/metrics.json").read_text(encoding="utf-8"))
FONT = base64.b64encode((ROOT / "fonts/GoogleSansFlex-subset.woff2").read_bytes()).decode()
FONT_CYR = base64.b64encode((ROOT / "fonts/RobotoFlex-cyrillic.woff2").read_bytes()).decode()

SHAPES = ["cookie", "clover", "sunny", "flower"]

ICON_RULES = [
    (("wolfie", "bot", "whatsapp", "wa", "baileys"), "smart_toy"),
    (("zip", "archive", "7-zip", "rar"), "folder_zip"),
    (("music", "audio", "spotify", "player", "sound"), "music_note"),
    (("tracker", "screen time", "activity", "monitor", "stats"), "monitoring"),
    (("discord",), "brand:discord"),
    (("android", "apk", "adb", "graphene"), "adb"),
    (("site", "website", "web ", "landing", "portfolio", "github.io"), "language"),
    (("theme", "design", "ui kit", "palette", "imperial"), "palette"),
    (("terminal", "cli", "shell", "dotfiles", "arch", "linux", "nvim"), "terminal"),
]

LANG_ICONS = {
    "TypeScript": "brand:typescript",
    "JavaScript": "brand:javascript",
    "Python": "brand:python",
    "Kotlin": "brand:kotlin",
    "HTML": "brand:html5",
    "Shell": "brand:shell",
    "Rust": "brand:rust",
    "C#": "desktop_windows",
    "Java": "brand:openjdk",
}

STACK = [
    (
        "Main",
        [
            ("brand:javascript", "JavaScript"),
            ("brand:typescript", "TypeScript"),
            ("brand:python", "Python"),
            ("brand:nodedotjs", "NodeJS"),
            ("brand:html5", "HTML5"),
            ("brand:kotlin", "Kotlin"),
            ("brand:shell", "Shell"),
        ],
    ),
    (
        "Systems & Environment",
        [
            ("brand:archlinux", "ArchLinux"),
            ("brand:android", "Android"),
            ("brand:linux", "Linux"),
            ("brand:macos", "macOS"),
            ("desktop_windows", "Windows"),
        ],
    ),
    (
        "Tools",
        [
            ("brand:git", "Git"),
            ("brand:github", "GitHub"),
            ("brand:gitlab", "GitLab"),
            ("adb", "ADB / Android Studio"),
            ("brand:googlegemini", "Gemini AI"),
            ("brand:neovim", "Neovim"),
            ("brand:vim", "Vim"),
            ("brand:grapheneos", "GrapheneOS"),
        ],
    ),
]

ABOUT = [
    ("code", "Building WolfieMD & Automated Digital Realms"),
    ("person", "Independent Bot Crafter & System Tinkerer"),
    ("bolt", "The Chaos Control — Gotta Go Fast!"),
    ("nest_clock_farsight_analog", "Fix The Past, Not Change Future."),
    ("work", "Business is Business, Learn That."),
    ("favorite", "Pain is my ally • Game On • VIII."),
    ("workspace_premium", "All You Touch You Change It"),
    ("trophy", "Old But Gold."),
]

BUTTONS = [
    ("site", "LinkTree", "language", "filled", "https://afh21-21.github.io"),
    ("repos", "All repositories", "book_2", "tonal", f"https://github.com/{USER}?tab=repositories"),
]

SOCIALS = [
    ("telegram", "Telegram", "brand:telegram", "https://t.me/LeonardoFlynn"),
    ("discord", "Discord", "brand:discord", "https://discord.com/users/1352214863895728128"),
    ("github", "GitHub", "brand:github", f"https://github.com/{USER}"),
]


# Helpers
def text_width(s, size, weight=400):
    table = METRICS[str(min((400, 500, 600, 700), key=lambda w: abs(w - weight)))]
    return sum(table.get(c, 0.55) for c in s) * size


def wrap(s, size, width, weight=400, lines=2):
    out, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if text_width(trial, size, weight) <= width:
            cur = trial
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        while text_width(out[-1] + "…", size, weight) > width:
            out[-1] = out[-1].rsplit(" ", 1)[0]
        out[-1] += "…"
    return out


def mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def shape(kind, cx, cy, r):
    n, a, sharp = {
        "cookie": (9, 0.07, 1.0),
        "cookie12": (12, 0.05, 1.0),
        "clover": (4, 0.2, 1.0),
        "sunny": (8, 0.1, 2.2),
        "flower": (8, 0.16, 1.0),
        "pill": (2, 0.0, 1.0),
    }[kind]
    pts = []
    steps = 180
    for i in range(steps):
        t = 2 * math.pi * i / steps
        wave = math.cos(n * t)
        wave = math.copysign(abs(wave) ** (1 / sharp), wave)
        rr = r * (1 - a + a * wave)
        pts.append((cx + rr * math.cos(t - math.pi / 2), cy + rr * math.sin(t - math.pi / 2)))
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"


def icon(name, x, y, size, fill):
    if name.startswith("brand:"):
        key = name[6:]
        brand_item = ICONS.get("brand", {}).get(key)
        if brand_item:
            d = brand_item["d"] if isinstance(brand_item, dict) else brand_item
            s = size / 24
            return f'<path d="{d}" fill="{fill}" transform="translate({x:.1f} {y:.1f}) scale({s:.4f})"/>'
        name = "code"
    sym = ICONS["symbol"].get(name) or ICONS["symbol"]["code"]
    if isinstance(sym, dict):
        vb = sym.get("vb", "0 -960 960 960")
        d = sym["d"]
    else:
        vb = "0 -960 960 960"
        d = sym
    vx, vy, vw, vh = [float(v) for v in vb.split()]
    s = size / vw
    return f'<path d="{d}" fill="{fill}" transform="translate({x - vx * s:.1f} {y - vy * s:.1f}) scale({s:.4f})"/>'


def txt(x, y, s, size, fill, weight=400, cls="", delay=None, anchor="start", extra=""):
    style = f"font-size:{size}px;font-weight:{weight};"
    if delay is not None:
        style += f"animation-delay:{delay:.2f}s;"
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" text-anchor="{anchor}" style="{style}"{c}{extra}>{escape(s)}</text>'


def svg(w, h, body, title):
    cyr = ""
    if any("\u0400" <= c <= "\u04ff" for c in body):
        cyr = f"@font-face{{font-family:R;src:url(data:font/woff2;base64,{FONT_CYR}) format('woff2');font-weight:400 800}}"
    css = f"""
@font-face{{font-family:G;src:url(data:font/woff2;base64,{FONT}) format('woff2');font-weight:400 800}}
{cyr}text{{font-family:G,R,'Google Sans','Segoe UI',Roboto,sans-serif;font-variation-settings:'ROND' 100}}
.up{{animation:up .8s cubic-bezier(.05,.7,.1,1) both}}
.pop{{transform-box:fill-box;transform-origin:center;animation:pop .6s cubic-bezier(.34,1.56,.64,1) both}}
.fade{{animation:fade .9s ease both}}
.spin{{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}}
.spin-r{{transform-box:fill-box;transform-origin:center;animation:spin 28s linear infinite reverse}}
.bob{{transform-box:fill-box;transform-origin:center;animation:bob 7s ease-in-out infinite}}
.breathe{{transform-box:fill-box;transform-origin:center;animation:breathe 6s ease-in-out infinite}}
.grow{{transform-box:fill-box;transform-origin:left center;animation:grow 1.1s cubic-bezier(.2,0,0,1) both}}
.wght{{animation:wght 1.6s cubic-bezier(.2,0,0,1) .2s both}}
.wave{{animation:wave 2.4s linear infinite}}
@keyframes up{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.6)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes bob{{0%,100%{{transform:translateY(0) rotate(0)}}50%{{transform:translateY(-10px) rotate(12deg)}}}}
@keyframes breathe{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.06)}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes wght{{from{{font-variation-settings:'ROND' 100,'wght' 400}}to{{font-variation-settings:'ROND' 100,'wght' 760}}}}
@keyframes wave{{from{{transform:translateX(0)}}to{{transform:translateX(-48px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title><style>{css}</style>{body}</svg>"
    )


def chip(x, y, label, p, ic=None, delay=0.0, h=36, size=15, style="outlined"):
    pad = 14
    iw = 18 if ic else 0
    gap = 8 if ic else 0
    w = pad * 2 + iw + gap + text_width(label, size, 500)
    if style == "tonal":
        bg = f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="10" fill="{p["secondaryContainer"]}"/>'
        fg = p["onSecondaryContainer"]
    else:
        bg = f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1:.1f}" height="{h - 1}" rx="10" fill="{p["surfaceContainerLow"]}" stroke="{p["outlineVariant"]}"/>'
        fg = p["onSurfaceVariant"]
    parts = [bg]
    if ic:
        parts.append(icon(ic, x + pad, y + (h - 18) / 2, 18, p["primary"]))
    parts.append(txt(x + pad + iw + gap, y + h / 2 + size * 0.36, label, size, fg, 500))
    return f'<g class="pop" style="animation-delay:{delay:.2f}s">{"".join(parts)}</g>', w


def avatar_data():
    try:
        req = urllib.request.Request(f"https://github.com/{USER}.png?size=320", headers={"User-Agent": "profile"})
        with urllib.request.urlopen(req, timeout=20) as r:
            kind = r.headers.get_content_type()
            return f"data:{kind};base64,{base64.b64encode(r.read()).decode()}"
    except Exception:
        return None


# Blocks
def hero(p, avatar):
    h = 300
    b = [f'<clipPath id="card"><rect width="{W}" height="{h}" rx="32"/></clipPath>']
    b.append(f'<rect width="{W}" height="{h}" rx="32" fill="{p["surfaceContainer"]}"/>')
    b.append('<g clip-path="url(#card)">')
    b.append(f'<path class="spin" d="{shape("flower", 780, 30, 150)}" fill="{p["primaryContainer"]}"/>')
    b
