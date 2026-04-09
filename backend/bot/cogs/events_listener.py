"""Listens to Redis pub/sub events and posts notifications to Discord channels."""

import asyncio
import logging

import discord
from discord.ext import commands, tasks

from bot.views import VoteView, UploadApprovalView
from core.config import get_settings
from core.events import (
    CHANNEL_MOD_ADDED,
    CHANNEL_MOD_UPDATED,
    CHANNEL_SERVER_UPDATE,
    CHANNEL_UPLOAD_PENDING,
    CHANNEL_VOTE_RESOLVED,
    get_event_bus,
)

logger = logging.getLogger(__name__)


class EventsListenerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.listen_events.is_running():
            self.listen_events.start()

    def cog_unload(self):
        self.listen_events.cancel()

    @tasks.loop(count=1)
    async def listen_events(self):
        """Subscribe to all Redis channels and dispatch Discord notifications."""
        bus = get_event_bus()
        channels = [
            CHANNEL_MOD_ADDED,
            CHANNEL_MOD_UPDATED,
            CHANNEL_VOTE_RESOLVED,
            CHANNEL_UPLOAD_PENDING,
            CHANNEL_SERVER_UPDATE,
        ]

        try:
            async for event in bus.subscribe(*channels):
                ch = event["channel"]
                data = event["data"]

                try:
                    if ch == CHANNEL_MOD_ADDED:
                        await self._notify_mod_added(data)
                    elif ch == CHANNEL_MOD_UPDATED:
                        await self._notify_mod_updated(data)
                    elif ch == CHANNEL_VOTE_RESOLVED:
                        await self._notify_vote_resolved(data)
                    elif ch == CHANNEL_UPLOAD_PENDING:
                        await self._notify_upload_pending(data)
                    elif ch == CHANNEL_SERVER_UPDATE:
                        await self._notify_server_update(data)
                except Exception:
                    logger.exception("Error handling event %s", ch)

        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
        except Exception:
            logger.exception("Event listener crashed, will restart")
            await asyncio.sleep(5)
            if not self.listen_events.is_running():
                self.listen_events.restart()

    async def _get_channel(self, channel_id_setting: str) -> discord.TextChannel | None:
        channel_id = getattr(self.settings, channel_id_setting, "")
        if not channel_id:
            return None
        try:
            return self.bot.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))
        except Exception:
            return None

    async def _notify_mod_added(self, data: dict):
        channel = await self._get_channel("channel_mod_proposals")
        if not channel:
            return

        status = data.get("status", "")
        color = discord.Color.green() if status == "active" else discord.Color.gold()
        title = "Mod Added" if status == "active" else "Mod Proposed"

        embed = discord.Embed(
            title=f"{title}: {data.get('name', '?')}",
            color=color,
        )
        embed.add_field(name="Status", value=status)
        await channel.send(embed=embed)

    async def _notify_mod_updated(self, data: dict):
        channel = await self._get_channel("channel_server_status")
        if not channel:
            return

        embed = discord.Embed(
            title=f"Mod Updated: {data.get('name', '?')}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Old Version", value=data.get("old_version", "?"))
        embed.add_field(name="New Version", value=data.get("new_version", "?"))
        await channel.send(embed=embed)

    async def _notify_vote_resolved(self, data: dict):
        channel = await self._get_channel("channel_mod_proposals")
        if not channel:
            return

        status = data.get("status", "")
        color = discord.Color.green() if "approved" in status else discord.Color.red()

        embed = discord.Embed(
            title=f"Vote Resolved: {data.get('mod_name', '?')}",
            color=color,
        )
        embed.add_field(name="Result", value=status.upper())
        if data.get("by"):
            embed.add_field(name="By", value=data["by"])
        await channel.send(embed=embed)

    async def _notify_upload_pending(self, data: dict):
        channel = await self._get_channel("channel_mod_uploads")
        if not channel:
            return

        embed = discord.Embed(
            title=f"New Upload: {data.get('filename', '?')}",
            description=f"Uploaded by {data.get('user', '?')}",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Scan Status", value=data.get("status", "?"))

        upload_id = data.get("upload_id")
        view = UploadApprovalView(upload_id) if upload_id else None
        await channel.send(embed=embed, view=view)

    async def _notify_server_update(self, data: dict):
        channel = await self._get_channel("channel_server_status")
        if not channel:
            return

        status = data.get("status", "")
        if status == "starting":
            embed = discord.Embed(
                title="Server Update Starting",
                description=f"Applying {data.get('updates', 0)} mod update(s)...",
                color=discord.Color.orange(),
            )
        elif status == "success":
            embed = discord.Embed(
                title="Server Update Complete",
                description=f"{data.get('updates', 0)} mod(s) updated successfully!",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="Server Update Failed",
                description="The update cycle encountered an error. Check logs.",
                color=discord.Color.red(),
            )
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsListenerCog(bot))
