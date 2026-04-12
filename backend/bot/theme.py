"""MineShare Discord theming — colors, embed builders, asset constants.

Mirrors the frontend's gold-on-space palette so Discord embeds feel like
a natural extension of the web app.
"""

from datetime import datetime, timezone

import discord

# ── Palette (mirrors frontend/tailwind.config) ─────────────────────────
GOLD = discord.Color.from_str("#c09850")
GOLD_LIGHT = discord.Color.from_str("#d4b06d")
SPACE_DARK = discord.Color.from_str("#010310")
SPACE_GRAY = discord.Color.from_str("#0a0a1a")

# Status accents
ACCENT_GREEN = discord.Color.from_str("#10b981")
ACCENT_RED = discord.Color.from_str("#ef4444")
ACCENT_AMBER = discord.Color.from_str("#f59e0b")
ACCENT_BLUE = discord.Color.from_str("#3b82f6")

BRAND = "MineShare"
BRAND_ICON = (
    "https://cdn.discordapp.com/emojis/1019234567890123456.png"  # placeholder
)


def base_embed(
    *,
    title: str,
    description: str | None = None,
    color: discord.Color = GOLD,
) -> discord.Embed:
    """Build an embed pre-themed with MineShare branding."""
    embed = discord.Embed(
        title=title,
        description=description or None,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"⛏  {BRAND}")
    return embed


# ── Tally bar ──────────────────────────────────────────────────────────

def tally_bar(yes: int, no: int, length: int = 14) -> str:
    total = yes + no
    if total == 0:
        return "▫" * length + "  *no votes yet*"
    yes_cells = round(length * yes / total)
    return "🟩" * yes_cells + "🟥" * (length - yes_cells)


# ── Vote embed ─────────────────────────────────────────────────────────

VOTE_TYPE_VERB = {"add": "Add", "remove": "Remove"}


def vote_embed(
    *,
    vote_type: str,
    mod_name: str,
    mod_description: str | None,
    mod_author: str | None,
    mod_source: str | None,
    initiated_by: str,
    expires_at: datetime | None,
    yes: int,
    no: int,
    image_filename: str | None = None,
) -> discord.Embed:
    color = ACCENT_GREEN if vote_type == "add" else ACCENT_RED

    description = (
        (mod_description[:300] + "…")
        if (mod_description and len(mod_description) > 300)
        else (mod_description or "*No description provided.*")
    )

    embed = discord.Embed(description=description, color=color)
    if image_filename:
        embed.set_image(url=f"attachment://{image_filename}")

    if mod_source:
        embed.add_field(name="Source", value=mod_source.title(), inline=True)
    embed.add_field(
        name="Proposed by", value=initiated_by or "Unknown", inline=True
    )
    if expires_at:
        ts = int(expires_at.timestamp())
        embed.add_field(name="Closes", value=f"<t:{ts}:R>", inline=True)

    embed.set_footer(text=f"⛏  {BRAND}")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


# ── Upload embed ───────────────────────────────────────────────────────

def upload_embed(
    *,
    filename: str,
    uploader: str,
    is_update: bool,
    mod_name: str | None,
    file_size: int | None,
    image_filename: str | None = None,
) -> discord.Embed:
    color = ACCENT_BLUE if is_update else ACCENT_AMBER

    embed = discord.Embed(color=color)
    if image_filename:
        embed.set_image(url=f"attachment://{image_filename}")

    embed.add_field(name="File", value=f"`{filename}`", inline=False)
    if file_size:
        embed.add_field(name="Size", value=_fmt_size(file_size), inline=True)
    if is_update and mod_name:
        embed.add_field(name="Updates", value=mod_name, inline=True)
    elif not is_update:
        embed.add_field(
            name="Type", value="New mod (will start a vote)", inline=True
        )

    embed.set_footer(text=f"⛏  {BRAND}  ·  Admins: approve or reject below")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


# ── Server status embed ────────────────────────────────────────────────

def server_status_embed(
    *,
    online: bool,
    players: list[str],
    last_checked: datetime,
    active_mods: int | None = None,
    image_filename: str | None = None,
) -> discord.Embed:
    color = ACCENT_GREEN if online else ACCENT_RED

    embed = discord.Embed(color=color)
    if image_filename:
        embed.set_image(url=f"attachment://{image_filename}")

    embed.add_field(
        name="Last checked",
        value=f"<t:{int(last_checked.timestamp())}:R>",
        inline=True,
    )

    if online and players:
        embed.add_field(
            name=f"Online now ({len(players)})",
            value="\n".join(f"• {p}" for p in players[:20]),
            inline=False,
        )
    elif online:
        embed.add_field(name="Online now", value="*nobody yet*", inline=False)

    embed.set_footer(text=f"⛏  {BRAND}")
    embed.timestamp = last_checked
    return embed
