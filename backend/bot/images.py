"""Generates themed banner PNGs for Discord embeds.

Mirrors the frontend's space-dark + gold aesthetic so embed images feel like
they were rendered by the web app.
"""

from __future__ import annotations

import io
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── Palette ────────────────────────────────────────────────────────────
SPACE_DARK = (1, 3, 16)
SPACE_GRAY = (10, 10, 26)
GOLD = (192, 152, 80)
GOLD_LIGHT = (212, 176, 109)
WHITE_DIM = (255, 255, 255, 60)

WIDTH = 1100
HEIGHT = 280

# ── Font discovery ─────────────────────────────────────────────────────
FONT_CANDIDATES_SERIF = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
FONT_CANDIDATES_MONO = [
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Background painter ────────────────────────────────────────────────

def _starfield(seed: int) -> Image.Image:
    """Vertical gradient + scattered star dots, deterministic per seed."""
    img = Image.new("RGB", (WIDTH, HEIGHT), SPACE_DARK)
    draw = ImageDraw.Draw(img)

    # vertical gradient space-dark → space-gray
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(SPACE_DARK[0] * (1 - t) + SPACE_GRAY[0] * t)
        g = int(SPACE_DARK[1] * (1 - t) + SPACE_GRAY[1] * t)
        b = int(SPACE_DARK[2] * (1 - t) + SPACE_GRAY[2] * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    rng = random.Random(seed)
    for _ in range(180):
        x = rng.randint(0, WIDTH - 1)
        y = rng.randint(0, HEIGHT - 1)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        bright = rng.randint(120, 230)
        draw.ellipse(
            [(x, y), (x + size, y + size)],
            fill=(bright, bright, bright),
        )

    # gold haze in upper-right corner
    haze = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze)
    cx, cy = int(WIDTH * 0.85), int(HEIGHT * 0.2)
    for r in range(220, 0, -10):
        alpha = max(0, 30 - r // 10)
        haze_draw.ellipse(
            [(cx - r, cy - r), (cx + r, cy + r)],
            fill=(*GOLD, alpha),
        )
    haze = haze.filter(ImageFilter.GaussianBlur(radius=14))
    img = Image.alpha_composite(img.convert("RGBA"), haze)
    return img.convert("RGB")


def _draw_border(img: Image.Image, accent: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(img)
    # Outer thin gold rule
    draw.rectangle([(0, 0), (WIDTH - 1, HEIGHT - 1)], outline=GOLD, width=2)
    # Inner accent rule
    draw.rectangle(
        [(8, 8), (WIDTH - 9, HEIGHT - 9)], outline=accent, width=1
    )
    # Corner ticks
    tick = 18
    for (x, y) in [
        (12, 12), (WIDTH - 13, 12), (12, HEIGHT - 13), (WIDTH - 13, HEIGHT - 13)
    ]:
        dx = tick if x < WIDTH / 2 else -tick
        dy = tick if y < HEIGHT / 2 else -tick
        draw.line([(x, y), (x + dx, y)], fill=GOLD_LIGHT, width=2)
        draw.line([(x, y), (x, y + dy)], fill=GOLD_LIGHT, width=2)


def _truncate(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return text + "…"


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
):
    w = font.getlength(text)
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)


def _to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ── Public banner builders ────────────────────────────────────────────

def vote_banner(
    *,
    vote_type: str,
    mod_name: str,
    author: str | None,
    yes: int,
    no: int,
) -> bytes:
    accent = (16, 185, 129) if vote_type == "add" else (239, 68, 68)
    img = _starfield(seed=hash(mod_name) & 0xFFFFFFFF)
    _draw_border(img, accent)
    draw = ImageDraw.Draw(img)

    label_font = _font(FONT_CANDIDATES_MONO, 22)
    title_font = _font(FONT_CANDIDATES_SERIF, 64)
    sub_font = _font(FONT_CANDIDATES_MONO, 22)
    bar_font = _font(FONT_CANDIDATES_MONO, 26)

    label = ("VOTE TO ADD" if vote_type == "add" else "VOTE TO REMOVE")
    _draw_text_centered(draw, 36, label, label_font, GOLD_LIGHT)

    title = _truncate(mod_name, title_font, WIDTH - 120)
    _draw_text_centered(draw, 78, title, title_font, (255, 255, 255))

    if author:
        sub = _truncate(f"by {author}", sub_font, WIDTH - 120)
        _draw_text_centered(draw, 158, sub, sub_font, (255, 255, 255, 150))

    # tally bar
    total = yes + no
    bar_w = WIDTH - 180
    bar_h = 22
    bar_x = (WIDTH - bar_w) // 2
    bar_y = HEIGHT - 70
    # background
    draw.rectangle(
        [(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
        fill=(20, 20, 35),
        outline=GOLD,
        width=1,
    )
    if total > 0:
        yes_w = int(bar_w * yes / total)
        # yes (green)
        if yes_w > 0:
            draw.rectangle(
                [(bar_x + 1, bar_y + 1), (bar_x + 1 + yes_w, bar_y + bar_h - 1)],
                fill=(16, 185, 129),
            )
        # no (red)
        no_x0 = bar_x + 1 + yes_w
        no_x1 = bar_x + bar_w - 1
        if no_x1 > no_x0:
            draw.rectangle(
                [(no_x0, bar_y + 1), (no_x1, bar_y + bar_h - 1)],
                fill=(239, 68, 68),
            )
    tally_text = f"{yes} YES   /   {no} NO"
    tw = bar_font.getlength(tally_text)
    draw.text(
        ((WIDTH - tw) / 2, bar_y + bar_h + 8),
        tally_text,
        font=bar_font,
        fill=GOLD_LIGHT,
    )

    return _to_png_bytes(img)


def upload_banner(
    *,
    filename: str,
    is_update: bool,
    mod_name: str | None,
    uploader: str,
) -> bytes:
    accent = (59, 130, 246) if is_update else (245, 158, 11)
    img = _starfield(seed=hash(filename) & 0xFFFFFFFF)
    _draw_border(img, accent)
    draw = ImageDraw.Draw(img)

    label_font = _font(FONT_CANDIDATES_MONO, 22)
    title_font = _font(FONT_CANDIDATES_SERIF, 56)
    sub_font = _font(FONT_CANDIDATES_MONO, 22)

    label = "MOD UPDATE PENDING" if is_update else "NEW MOD UPLOAD"
    _draw_text_centered(draw, 40, label, label_font, GOLD_LIGHT)

    headline = mod_name if (is_update and mod_name) else filename
    headline = _truncate(headline, title_font, WIDTH - 120)
    _draw_text_centered(draw, 84, headline, title_font, (255, 255, 255))

    sub_text = (
        f"updated · {filename}" if is_update else f"awaiting admin approval"
    )
    sub_text = _truncate(sub_text, sub_font, WIDTH - 120)
    _draw_text_centered(draw, 168, sub_text, sub_font, (255, 255, 255, 160))

    uploader_text = _truncate(f"uploaded by {uploader}", sub_font, WIDTH - 120)
    _draw_text_centered(draw, 200, uploader_text, sub_font, GOLD_LIGHT)

    return _to_png_bytes(img)


def status_banner(
    *,
    online: bool,
    player_count: int,
    active_mods: int,
) -> bytes:
    accent = (16, 185, 129) if online else (239, 68, 68)
    img = _starfield(seed=42)
    _draw_border(img, accent)
    draw = ImageDraw.Draw(img)

    label_font = _font(FONT_CANDIDATES_MONO, 22)
    title_font = _font(FONT_CANDIDATES_SERIF, 72)
    stat_label_font = _font(FONT_CANDIDATES_MONO, 18)
    stat_value_font = _font(FONT_CANDIDATES_SERIF, 44)

    _draw_text_centered(draw, 32, "MINESHARE SERVER", label_font, GOLD_LIGHT)

    title = "ONLINE" if online else "OFFLINE"
    _draw_text_centered(draw, 70, title, title_font, accent)

    # Stat tiles
    tiles = [
        ("PLAYERS", str(player_count) if online else "—"),
        ("ACTIVE MODS", str(active_mods)),
    ]
    tile_w = 180
    gap = 40
    total_w = len(tiles) * tile_w + (len(tiles) - 1) * gap
    start_x = (WIDTH - total_w) // 2
    y_top = HEIGHT - 95

    for i, (label, value) in enumerate(tiles):
        x = start_x + i * (tile_w + gap)
        draw.rectangle(
            [(x, y_top), (x + tile_w, y_top + 76)],
            outline=GOLD,
            width=1,
        )
        lw = stat_label_font.getlength(label)
        draw.text(
            (x + (tile_w - lw) / 2, y_top + 8),
            label,
            font=stat_label_font,
            fill=GOLD_LIGHT,
        )
        vw = stat_value_font.getlength(value)
        draw.text(
            (x + (tile_w - vw) / 2, y_top + 26),
            value,
            font=stat_value_font,
            fill=(255, 255, 255),
        )

    return _to_png_bytes(img)
