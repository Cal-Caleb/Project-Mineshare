"""Discord bot entry point and setup."""

import logging

import discord
from discord.ext import commands

from core.config import get_settings

logger = logging.getLogger(__name__)


def create_bot() -> commands.Bot:
    settings = get_settings()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )

    # Attach settings for easy cog access
    bot.settings = settings  # type: ignore[attr-defined]

    @bot.event
    async def on_ready():
        logger.info("Bot logged in as %s (ID: %s)", bot.user, bot.user.id)
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the mod list",
            )
        )

        # Re-register persistent views so buttons survive restarts.
        # We need one view per active vote / upload / mod so the
        # custom_id → callback mapping is restored.
        from bot.views import RemoveModView, UploadApprovalView, VoteView
        from core.database import SessionLocal
        from models import Mod, ModStatus, ModUpload, UploadStatus, Vote, VoteStatus

        db = SessionLocal()
        try:
            for v in db.query(Vote).filter(Vote.status == VoteStatus.PENDING).all():
                bot.add_view(VoteView(v.id))
            for u in db.query(ModUpload).filter(ModUpload.status == UploadStatus.PENDING_APPROVAL).all():
                bot.add_view(UploadApprovalView(u.id))
            for m in db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).all():
                bot.add_view(RemoveModView(m.id))
            logger.info("Persistent views re-registered")
        except Exception:
            logger.exception("Failed to re-register persistent views")
        finally:
            db.close()

        # Sync slash commands
        try:
            guild = discord.Object(id=int(settings.discord_guild_id))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info("Synced %d commands to guild %s", len(synced), settings.discord_guild_id)
        except Exception:
            logger.exception("Failed to sync commands")

    return bot


async def load_cogs(bot: commands.Bot) -> None:
    cog_modules = [
        "bot.cogs.mods",
        "bot.cogs.votes",
        "bot.cogs.server",
        "bot.cogs.admin",
        "bot.cogs.events_listener",
    ]
    for module in cog_modules:
        try:
            await bot.load_extension(module)
            logger.info("Loaded cog: %s", module)
        except Exception:
            logger.exception("Failed to load cog: %s", module)
