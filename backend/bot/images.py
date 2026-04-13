"""Generates themed banner PNGs for Discord embeds.

Mirrors the frontend's space-dark + gold aesthetic so embed images feel like
they were rendered by the web app.
"""

from __future__ import annotations

import io
import random
from datetime import UTC
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
    draw.rectangle([(8, 8), (WIDTH - 9, HEIGHT - 9)], outline=accent, width=1)
    # Corner ticks
    tick = 18
    for x, y in [(12, 12), (WIDTH - 13, 12), (12, HEIGHT - 13), (WIDTH - 13, HEIGHT - 13)]:
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

    label = "VOTE TO ADD" if vote_type == "add" else "VOTE TO REMOVE"
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

    sub_text = f"updated · {filename}" if is_update else "awaiting admin approval"
    sub_text = _truncate(sub_text, sub_font, WIDTH - 120)
    _draw_text_centered(draw, 168, sub_text, sub_font, (255, 255, 255, 160))

    uploader_text = _truncate(f"uploaded by {uploader}", sub_font, WIDTH - 120)
    _draw_text_centered(draw, 200, uploader_text, sub_font, GOLD_LIGHT)

    return _to_png_bytes(img)


STATUS_HEIGHT = 520  # taller banner for graphs


def _starfield_sized(seed: int, w: int, h: int) -> Image.Image:
    """Like _starfield but for arbitrary dimensions."""
    img = Image.new("RGB", (w, h), SPACE_DARK)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(SPACE_DARK[0] * (1 - t) + SPACE_GRAY[0] * t)
        g = int(SPACE_DARK[1] * (1 - t) + SPACE_GRAY[1] * t)
        b = int(SPACE_DARK[2] * (1 - t) + SPACE_GRAY[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    rng = random.Random(seed)
    for _ in range(int(w * h * 0.0003)):
        x = rng.randint(0, w - 1)
        y2 = rng.randint(0, h - 1)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        bright = rng.randint(120, 230)
        draw.ellipse([(x, y2), (x + size, y2 + size)], fill=(bright, bright, bright))
    haze = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze)
    cx, cy = int(w * 0.85), int(h * 0.1)
    for rad in range(220, 0, -10):
        alpha = max(0, 30 - rad // 10)
        haze_draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], fill=(*GOLD, alpha))
    haze = haze.filter(ImageFilter.GaussianBlur(radius=14))
    img = Image.alpha_composite(img.convert("RGBA"), haze)
    return img.convert("RGB")


def _draw_border_sized(img: Image.Image, accent: tuple[int, int, int]) -> None:
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline=GOLD, width=2)
    draw.rectangle([(8, 8), (w - 9, h - 9)], outline=accent, width=1)
    tick = 18
    for x, y in [(12, 12), (w - 13, 12), (12, h - 13), (w - 13, h - 13)]:
        dx = tick if x < w / 2 else -tick
        dy = tick if y < h / 2 else -tick
        draw.line([(x, y), (x + dx, y)], fill=GOLD_LIGHT, width=2)
        draw.line([(x, y), (x, y + dy)], fill=GOLD_LIGHT, width=2)


def status_banner(
    *,
    online: bool,
    player_count: int,
    active_mods: int,
    uptime_pct: float = 0.0,
    uptime_buckets: list | None = None,
    world_size_mb: float | None = None,
) -> bytes:
    accent = (16, 185, 129) if online else (239, 68, 68)
    img = _starfield_sized(seed=42, w=WIDTH, h=STATUS_HEIGHT)
    _draw_border_sized(img, accent)
    draw = ImageDraw.Draw(img)

    label_font = _font(FONT_CANDIDATES_MONO, 20)
    title_font = _font(FONT_CANDIDATES_SERIF, 56)
    stat_label_font = _font(FONT_CANDIDATES_MONO, 14)
    stat_value_font = _font(FONT_CANDIDATES_SERIF, 32)
    section_font = _font(FONT_CANDIDATES_MONO, 12)
    tiny_font = _font(FONT_CANDIDATES_MONO, 11)

    # -- Header (y 20-100) --
    _draw_text_centered(draw, 20, "MINESHARE SERVER", label_font, GOLD_LIGHT)
    title = "ONLINE" if online else "OFFLINE"
    _draw_text_centered(draw, 48, title, title_font, accent)

    # -- Stat tiles (y 110-166) --
    tiles = [
        ("PLAYERS", str(player_count) if online else "—"),
        ("MODS", str(active_mods)),
        ("UPTIME", f"{uptime_pct:.1f}%"),
    ]
    if world_size_mb is not None:
        if world_size_mb >= 1024:
            tiles.append(("WORLD", f"{world_size_mb / 1024:.1f} GB"))
        else:
            tiles.append(("WORLD", f"{world_size_mb:.0f} MB"))

    tile_w = 140
    gap = 20
    total_w = len(tiles) * tile_w + (len(tiles) - 1) * gap
    start_x = (WIDTH - total_w) // 2
    y_top = 110

    for i, (lbl, val) in enumerate(tiles):
        x = start_x + i * (tile_w + gap)
        draw.rectangle([(x, y_top), (x + tile_w, y_top + 56)], outline=GOLD, width=1)
        lw = stat_label_font.getlength(lbl)
        draw.text((x + (tile_w - lw) / 2, y_top + 5), lbl, font=stat_label_font, fill=GOLD_LIGHT)
        vw = stat_value_font.getlength(val)
        draw.text((x + (tile_w - vw) / 2, y_top + 22), val, font=stat_value_font, fill=(255, 255, 255))

    buckets = uptime_buckets or []
    bar_left = 60
    bar_right = WIDTH - 60
    bar_w = bar_right - bar_left

    # -- Uptime bar (y 185-215) --
    bar_y = 185
    bar_h = 20

    draw.text((bar_left, bar_y - 16), "UPTIME  (30 DAYS)", font=section_font, fill=GOLD_LIGHT)

    # Legend — to the right of the section title
    legend_x = bar_left + 160
    legend_y_l = bar_y - 16
    draw.rectangle([(legend_x, legend_y_l + 2), (legend_x + 8, legend_y_l + 10)], fill=(16, 185, 129))
    draw.text((legend_x + 11, legend_y_l), "Online", font=tiny_font, fill=(140, 140, 160))
    draw.rectangle([(legend_x + 58, legend_y_l + 2), (legend_x + 66, legend_y_l + 10)], fill=(239, 68, 68))
    draw.text((legend_x + 69, legend_y_l), "Offline", font=tiny_font, fill=(140, 140, 160))
    draw.rectangle([(legend_x + 118, legend_y_l + 2), (legend_x + 126, legend_y_l + 10)], fill=(40, 40, 60))
    draw.text((legend_x + 129, legend_y_l), "No data", font=tiny_font, fill=(140, 140, 160))

    if buckets:
        n = len(buckets)
        for i, b in enumerate(buckets):
            x0 = int(bar_left + i * bar_w / n)
            x1 = int(bar_left + (i + 1) * bar_w / n)
            if x1 <= x0:
                x1 = x0 + 1
            if b.get("online") is True:
                color = (16, 185, 129)
            elif b.get("online") is False:
                color = (239, 68, 68)
            else:
                color = (40, 40, 60)
            draw.rectangle([(x0, bar_y), (x1, bar_y + bar_h)], fill=color)
    else:
        draw.rectangle([(bar_left, bar_y), (bar_right, bar_y + bar_h)], fill=(40, 40, 60))

    # Time labels under bar
    draw.text((bar_left, bar_y + bar_h + 2), "30d ago", font=tiny_font, fill=(100, 100, 120))
    nw = tiny_font.getlength("now")
    draw.text((bar_right - nw, bar_y + bar_h + 2), "now", font=tiny_font, fill=(100, 100, 120))

    # -- Player count graph (y 228-378) --
    graph_y = 228
    graph_h = 120
    graph_left = 60
    graph_right = WIDTH - 60
    graph_w = graph_right - graph_left

    draw.text((graph_left, graph_y - 16), "PLAYER COUNT  (30 DAYS)", font=section_font, fill=GOLD_LIGHT)

    draw.rectangle(
        [(graph_left, graph_y), (graph_right, graph_y + graph_h)],
        fill=(8, 8, 22),
        outline=(40, 40, 60),
        width=1,
    )

    if buckets:
        players_data = [b.get("players", 0) or 0 for b in buckets]
        max_players = max(max(players_data), 1)

        # Grid lines
        for frac in (0.25, 0.5, 0.75):
            gy = int(graph_y + graph_h * (1 - frac))
            draw.line([(graph_left, gy), (graph_right, gy)], fill=(30, 30, 50), width=1)

        # Draw filled area + line
        n = len(players_data)
        points = []
        for i, pc in enumerate(players_data):
            x = graph_left + int(i * graph_w / n)
            y = graph_y + graph_h - int((pc / max_players) * (graph_h - 4)) - 2
            points.append((x, y))

        if len(points) >= 2:
            fill_points = [
                *points,
                (graph_right, graph_y + graph_h),
                (graph_left, graph_y + graph_h),
            ]
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.polygon(fill_points, fill=(*GOLD, 30))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            for j in range(len(points) - 1):
                draw.line([points[j], points[j + 1]], fill=GOLD_LIGHT, width=2)

    # Graph time labels
    draw.text((graph_left, graph_y + graph_h + 2), "30d ago", font=tiny_font, fill=(100, 100, 120))
    nw2 = tiny_font.getlength("now")
    draw.text((graph_right - nw2, graph_y + graph_h + 2), "now", font=tiny_font, fill=(100, 100, 120))

    # -- Daily uptime bars (y 370-420) --
    daily_y = 370
    draw.text((bar_left, daily_y), "DAILY UPTIME (LAST 7 DAYS)", font=section_font, fill=GOLD_LIGHT)
    if buckets:
        bpd = 144
        n = len(buckets)
        days_to_show = min(7, max(1, n // bpd))
        day_bar_y = daily_y + 16
        day_bar_h = 16
        day_w = (bar_w - (days_to_show - 1) * 4) // max(days_to_show, 1)

        for d in range(days_to_show):
            start_idx = n - (days_to_show - d) * bpd
            end_idx = start_idx + bpd
            day_buckets = buckets[max(0, start_idx) : min(n, end_idx)]

            known = [b for b in day_buckets if b.get("online") is not None]
            pct = (100 * sum(1 for b in known if b["online"]) / len(known)) if known else 0

            x0 = bar_left + d * (day_w + 4)
            x1 = x0 + day_w
            c = (16, 185, 129) if pct >= 99 else (245, 158, 11) if pct >= 90 else (239, 68, 68)
            draw.rectangle([(x0, day_bar_y), (x1, day_bar_y + day_bar_h)], fill=c)
            pct_text = f"{pct:.0f}%"
            pw = tiny_font.getlength(pct_text)
            if day_w > pw + 4:
                draw.text((x0 + (day_w - pw) / 2, day_bar_y + 2), pct_text, font=tiny_font, fill=(255, 255, 255))

    # ── Stats summary line (y 410) ──
    if buckets:
        peak = max(b.get("players", 0) or 0 for b in buckets)
        avg_data = [b.get("players", 0) or 0 for b in buckets if b.get("online")]
        avg = sum(avg_data) / len(avg_data) if avg_data else 0
        stats_y = 410
        draw.text((bar_left, stats_y), f"PEAK: {peak}", font=section_font, fill=GOLD_LIGHT)
        draw.text((bar_left + 120, stats_y), f"AVG: {avg:.1f}", font=section_font, fill=GOLD_LIGHT)
        up_color = (16, 185, 129) if uptime_pct >= 95 else (245, 158, 11) if uptime_pct >= 80 else (239, 68, 68)
        draw.text((bar_left + 250, stats_y), f"30-DAY UPTIME: {uptime_pct:.1f}%", font=section_font, fill=up_color)

    # ── Footer (y ~492) ──
    footer_font = _font(FONT_CANDIDATES_MONO, 11)
    _draw_text_centered(draw, STATUS_HEIGHT - 26, "⛏  MINESHARE", footer_font, (100, 100, 120))

    return _to_png_bytes(img)


# ── Mod catalogue card ────────────────────────────────────────────────

MOD_CARD_W = 1100
MOD_CARD_H = 180


def mod_card_banner(
    *,
    mod_name: str,
    author: str | None,
    source: str,
    version: str | None,
) -> bytes:
    """Smaller banner for a single mod in the catalogue channel."""
    img = _starfield(seed=hash(mod_name) & 0xFFFFFFFF)
    # Crop to shorter height
    img = img.crop((0, 0, MOD_CARD_W, MOD_CARD_H))
    _draw_border(img, GOLD)
    draw = ImageDraw.Draw(img)

    title_font = _font(FONT_CANDIDATES_SERIF, 48)
    sub_font = _font(FONT_CANDIDATES_MONO, 20)
    tag_font = _font(FONT_CANDIDATES_MONO, 16)

    # Mod name
    title = _truncate(mod_name, title_font, MOD_CARD_W - 120)
    _draw_text_centered(draw, 28, title, title_font, (255, 255, 255))

    # Author line
    if author:
        author_text = _truncate(f"by {author}", sub_font, MOD_CARD_W - 120)
        _draw_text_centered(draw, 90, author_text, sub_font, GOLD_LIGHT)

    # Source + version tags at bottom
    tags = source.upper()
    if version:
        v_short = version[:40]
        tags += f"  ·  {v_short}"
    tags = _truncate(tags, tag_font, MOD_CARD_W - 120)
    _draw_text_centered(draw, MOD_CARD_H - 40, tags, tag_font, (180, 180, 200))

    return _to_png_bytes(img)


def update_log_banner(
    *,
    mod_name: str,
    old_version: str | None,
    new_version: str | None,
) -> bytes:
    """Banner for the mod-updates channel showing a version change."""
    img = _starfield(seed=hash(f"upd_{mod_name}") & 0xFFFFFFFF)
    _draw_border(img, (59, 130, 246))  # blue accent
    draw = ImageDraw.Draw(img)

    label_font = _font(FONT_CANDIDATES_MONO, 20)
    title_font = _font(FONT_CANDIDATES_SERIF, 52)
    ver_font = _font(FONT_CANDIDATES_MONO, 22)
    arrow_font = _font(FONT_CANDIDATES_SERIF, 28)

    _draw_text_centered(draw, 32, "MOD UPDATE", label_font, GOLD_LIGHT)

    title = _truncate(mod_name, title_font, WIDTH - 120)
    _draw_text_centered(draw, 72, title, title_font, (255, 255, 255))

    # Version change: old → new
    old_text = _truncate(old_version or "unknown", ver_font, WIDTH // 2 - 100)
    new_text = _truncate(new_version or "unknown", ver_font, WIDTH // 2 - 100)
    arrow = "  →  "

    full_w = ver_font.getlength(old_text) + arrow_font.getlength(arrow) + ver_font.getlength(new_text)
    start_x = (WIDTH - full_w) / 2
    y = 160

    draw.text((start_x, y), old_text, font=ver_font, fill=(239, 68, 68, 180))
    x2 = start_x + ver_font.getlength(old_text)
    draw.text((x2, y - 3), arrow, font=arrow_font, fill=GOLD_LIGHT)
    x3 = x2 + arrow_font.getlength(arrow)
    draw.text((x3, y), new_text, font=ver_font, fill=(16, 185, 129))

    # Timestamp
    ts_font = _font(FONT_CANDIDATES_MONO, 14)
    from datetime import datetime

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    _draw_text_centered(draw, HEIGHT - 40, ts, ts_font, (120, 120, 140))

    return _to_png_bytes(img)
