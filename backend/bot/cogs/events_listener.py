"""Discord ↔ DB sync hub.

Strategy:
- The Discord channels are *projections* of the DB, not append-only logs.
- We keep at most one message per pending Vote / pending Upload, and a single
  persistent server-status message.
- Resolved items are deleted from Discord (the web app keeps the history).
- Live Redis events trigger immediate refreshes; a periodic full sync acts as
  a safety net so things stay correct even if events were missed.
"""

import asyncio
import contextlib
import io
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import discord
from discord.ext import commands, tasks

from bot import images as banner
from bot.theme import (
    mod_card_embed,
    mod_update_embed,
    server_status_embed,
    upload_embed,
    vote_embed,
)
from bot.views import RemoveModView, UploadApprovalView, VoteView
from core.config import get_settings
from core.database import SessionLocal
from core.events import (
    CHANNEL_MOD_ADDED,
    CHANNEL_MOD_REMOVED,
    CHANNEL_MOD_UPDATED,
    CHANNEL_SERVER_UPDATE,
    CHANNEL_UPLOAD_PENDING,
    CHANNEL_UPLOAD_RESOLVED,
    CHANNEL_VOTE_CAST,
    CHANNEL_VOTE_CREATED,
    CHANNEL_VOTE_RESOLVED,
    get_event_bus,
)
from core.server_manager import ServerManager
from core.vote_manager import VoteManager
from core.whitelist_manager import WhitelistManager
from models import (
    Mod,
    ModStatus,
    ModUpload,
    ServerHeartbeat,
    UploadStatus,
    User,
    UserRole,
    Vote,
    VoteStatus,
)

logger = logging.getLogger(__name__)


class EventsListenerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
        self._sync_lock = asyncio.Lock()
        self._status_message_id: int | None = None
        self._server_mgr = ServerManager()

    # ── Lifecycle ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("EventsListenerCog ready, starting background tasks")
        if not self.listen_events.is_running():
            self.listen_events.start()
        if not self.periodic_sync.is_running():
            self.periodic_sync.start()
        if not self.status_refresh.is_running():
            self.status_refresh.start()

        # Fire one immediate full sync so the channels look right at boot.
        async def _kickoff():
            try:
                logger.info("Running initial full sync...")
                await self.full_sync()
                logger.info("Initial full sync done")
            except Exception:
                logger.exception("Initial full sync failed")

        self.bot.loop.create_task(_kickoff())

    def cog_unload(self):
        self.listen_events.cancel()
        self.periodic_sync.cancel()
        self.status_refresh.cancel()

    # ── Channel helpers ──────────────────────────────────────────────

    async def _get_channel(self, setting_name: str) -> discord.TextChannel | None:
        channel_id = getattr(self.settings, setting_name, "")
        if not channel_id:
            return None
        try:
            ch = self.bot.get_channel(int(channel_id))
            if ch is None:
                ch = await self.bot.fetch_channel(int(channel_id))
            return ch  # type: ignore[return-value]
        except Exception:
            logger.exception("Could not resolve channel %s", setting_name)
            return None

    async def _safe_fetch_message(
        self, channel: discord.TextChannel, message_id: int | str | None
    ) -> discord.Message | None:
        if not message_id:
            return None
        try:
            return await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def _safe_delete(self, msg: discord.Message | None) -> None:
        if not msg:
            return
        with contextlib.suppress(discord.NotFound, discord.Forbidden, discord.HTTPException):
            await msg.delete()

    # ── Live event subscription ──────────────────────────────────────

    @tasks.loop(count=1)
    async def listen_events(self):
        bus = get_event_bus()
        channels = [
            CHANNEL_VOTE_CREATED,
            CHANNEL_VOTE_CAST,
            CHANNEL_VOTE_RESOLVED,
            CHANNEL_UPLOAD_PENDING,
            CHANNEL_UPLOAD_RESOLVED,
            CHANNEL_SERVER_UPDATE,
            CHANNEL_MOD_ADDED,
            CHANNEL_MOD_REMOVED,
            CHANNEL_MOD_UPDATED,
        ]
        try:
            async for event in bus.subscribe(*channels):
                ch = event["channel"]
                data = event["data"]
                try:
                    if ch in (
                        CHANNEL_VOTE_CREATED,
                        CHANNEL_VOTE_CAST,
                        CHANNEL_VOTE_RESOLVED,
                    ):
                        await self.sync_votes()
                        if ch == CHANNEL_VOTE_RESOLVED:
                            await self.sync_mod_list()
                    elif ch in (CHANNEL_UPLOAD_PENDING, CHANNEL_UPLOAD_RESOLVED):
                        await self.sync_uploads()
                    elif ch == CHANNEL_SERVER_UPDATE:
                        await self.refresh_status()
                    elif ch == CHANNEL_MOD_UPDATED:
                        await self.sync_mod_list()
                        await self._post_mod_update(data)
                    elif ch in (CHANNEL_MOD_ADDED, CHANNEL_MOD_REMOVED):
                        await self.sync_mod_list()
                except Exception:
                    logger.exception("Failed handling event %s: %s", ch, data)
        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
        except Exception:
            logger.exception("Event listener crashed; restarting in 5s")
            await asyncio.sleep(5)
            if not self.listen_events.is_running():
                self.listen_events.restart()

    # ── Periodic safety-net sync ─────────────────────────────────────

    @tasks.loop(minutes=2)
    async def periodic_sync(self):
        try:
            await self.full_sync()
        except Exception:
            logger.exception("Periodic sync failed")

    @periodic_sync.before_loop
    async def _wait_periodic(self):
        await self.bot.wait_until_ready()

    async def full_sync(self):
        async with self._sync_lock:
            for name, fn in (
                ("sync_votes", self.sync_votes),
                ("sync_uploads", self.sync_uploads),
                ("sync_mod_list", self.sync_mod_list),
                ("refresh_status", self.refresh_status),
            ):
                try:
                    await fn()
                except Exception:
                    logger.exception("%s failed", name)

    # ── Vote sync ────────────────────────────────────────────────────

    async def sync_votes(self) -> None:
        channel = await self._get_channel("channel_active_votes")
        if channel is None:
            logger.warning("sync_votes: channel_active_votes not configured/resolvable")
            return

        # Quick permission probe so failures are obvious in the log
        me = channel.guild.me if channel.guild else None
        if me:
            perms = channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links and perms.read_message_history and perms.manage_messages):
                logger.warning(
                    "sync_votes: bot lacks perms in #%s (send=%s embed=%s history=%s manage=%s)",
                    channel.name,
                    perms.send_messages,
                    perms.embed_links,
                    perms.read_message_history,
                    perms.manage_messages,
                )

        db = SessionLocal()
        try:
            # 1. Expire stale votes first so we don't keep dead messages around
            VoteManager().expire_stale_votes(db)

            pending = db.query(Vote).filter(Vote.status == VoteStatus.PENDING).order_by(Vote.created_at.asc()).all()
            logger.info("sync_votes: %d pending votes in DB", len(pending))
            pending_ids = {v.id for v in pending}

            # 2. Sweep channel: delete bot messages whose vote is no longer pending
            tracked_msg_ids: set[int] = set()
            for v in pending:
                if v.discord_message_id and v.discord_channel_id == str(channel.id):
                    with contextlib.suppress(ValueError):
                        tracked_msg_ids.add(int(v.discord_message_id))

            try:
                async for msg in channel.history(limit=200):
                    if msg.author.id != self.bot.user.id:
                        continue
                    if msg.id in tracked_msg_ids:
                        continue
                    # Orphan bot message — wipe it
                    await self._safe_delete(msg)
            except discord.Forbidden:
                logger.warning("Missing read history permission in #active-votes")

            # 3. Make sure each pending vote has a current message
            vote_mgr = VoteManager()
            for v in pending:
                tally = vote_mgr.get_tally(db, v)
                expires = (
                    v.expires_at.replace(tzinfo=UTC) if v.expires_at and v.expires_at.tzinfo is None else v.expires_at
                )

                # Vary filename by tally so Discord CDN/clients refresh
                img_name = f"vote_{v.id}_{tally['yes']}y_{tally['no']}n.png"
                png = banner.vote_banner(
                    vote_type=v.vote_type.value,
                    mod_name=v.mod.name,
                    author=v.mod.author,
                    yes=tally["yes"],
                    no=tally["no"],
                )
                file = discord.File(io.BytesIO(png), filename=img_name)

                embed = vote_embed(
                    vote_type=v.vote_type.value,
                    mod_name=v.mod.name,
                    mod_description=v.mod.description,
                    mod_author=v.mod.author,
                    mod_source=v.mod.source.value if v.mod.source else None,
                    initiated_by=v.initiated_by_user.discord_username if v.initiated_by_user else "Unknown",
                    expires_at=expires,
                    yes=tally["yes"],
                    no=tally["no"],
                    image_filename=img_name,
                )

                existing = (
                    await self._safe_fetch_message(channel, v.discord_message_id)
                    if v.discord_channel_id == str(channel.id)
                    else None
                )

                view = VoteView(v.id)
                if existing:
                    try:
                        await existing.edit(embed=embed, view=view, attachments=[file])
                    except discord.HTTPException:
                        existing = None
                        # Re-create the file because it was consumed
                        file = discord.File(io.BytesIO(png), filename=img_name)

                if not existing:
                    msg = await channel.send(embed=embed, view=view, file=file)
                    v.discord_message_id = str(msg.id)
                    v.discord_channel_id = str(msg.channel.id)
                    db.commit()

            _ = pending_ids  # silence linter
        finally:
            db.close()

    # ── Upload sync ──────────────────────────────────────────────────

    async def sync_uploads(self) -> None:
        channel = await self._get_channel("channel_mod_uploads")
        if channel is None:
            logger.warning("sync_uploads: channel_mod_uploads not configured/resolvable")
            return

        me = channel.guild.me if channel.guild else None
        if me:
            perms = channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links and perms.read_message_history and perms.manage_messages):
                logger.warning(
                    "sync_uploads: bot lacks perms in #%s (send=%s embed=%s history=%s manage=%s)",
                    channel.name,
                    perms.send_messages,
                    perms.embed_links,
                    perms.read_message_history,
                    perms.manage_messages,
                )

        db = SessionLocal()
        try:
            pending = (
                db.query(ModUpload)
                .filter(ModUpload.status == UploadStatus.PENDING_APPROVAL)
                .order_by(ModUpload.created_at.asc())
                .all()
            )
            logger.info("sync_uploads: %d pending uploads in DB", len(pending))

            tracked_msg_ids: set[int] = set()
            for u in pending:
                if u.discord_message_id and u.discord_channel_id == str(channel.id):
                    with contextlib.suppress(ValueError):
                        tracked_msg_ids.add(int(u.discord_message_id))

            try:
                async for msg in channel.history(limit=200):
                    if msg.author.id != self.bot.user.id:
                        continue
                    if msg.id in tracked_msg_ids:
                        continue
                    await self._safe_delete(msg)
            except discord.Forbidden:
                logger.warning("Missing read history permission in #mod-uploads")

            for u in pending:
                linked_mod = None
                if u.mod_id:
                    linked_mod = db.query(Mod).filter(Mod.id == u.mod_id).first()

                uploader = u.uploaded_by_user.discord_username if u.uploaded_by_user else "Unknown"
                img_name = f"upload_{u.id}.png"
                png = banner.upload_banner(
                    filename=u.original_filename,
                    is_update=bool(u.mod_id),
                    mod_name=linked_mod.name if linked_mod else None,
                    uploader=uploader,
                )
                file = discord.File(io.BytesIO(png), filename=img_name)

                embed = upload_embed(
                    filename=u.original_filename,
                    uploader=uploader,
                    is_update=bool(u.mod_id),
                    mod_name=linked_mod.name if linked_mod else None,
                    file_size=u.file_size,
                    image_filename=img_name,
                )
                view = UploadApprovalView(u.id)

                existing = (
                    await self._safe_fetch_message(channel, u.discord_message_id)
                    if u.discord_channel_id == str(channel.id)
                    else None
                )

                if existing:
                    try:
                        await existing.edit(embed=embed, view=view, attachments=[file])
                    except discord.HTTPException:
                        existing = None
                        file = discord.File(io.BytesIO(png), filename=img_name)

                if not existing:
                    msg = await channel.send(embed=embed, view=view, file=file)
                    u.discord_message_id = str(msg.id)
                    u.discord_channel_id = str(msg.channel.id)
                    db.commit()
        finally:
            db.close()

    # ── Mod catalogue sync ─────────────────────────────────────────

    async def sync_mod_list(self) -> None:
        channel = await self._get_channel("channel_mod_proposals")
        if channel is None:
            logger.warning("sync_mod_list: channel_mod_proposals not configured")
            return

        db = SessionLocal()
        try:
            active = db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).order_by(Mod.name.asc()).all()
            logger.info("sync_mod_list: %d active mods in DB", len(active))

            # Build set of tracked message IDs for active mods
            tracked_msg_ids: set[int] = set()
            for m in active:
                if m.discord_message_id and m.discord_channel_id == str(channel.id):
                    with contextlib.suppress(ValueError):
                        tracked_msg_ids.add(int(m.discord_message_id))

            # Sweep: delete bot messages that no longer match an active mod
            try:
                async for msg in channel.history(limit=500):
                    if msg.author.id != self.bot.user.id:
                        continue
                    if msg.id in tracked_msg_ids:
                        continue
                    await self._safe_delete(msg)
            except discord.Forbidden:
                logger.warning("Missing read history permission in mod-list channel")

            # Upsert a message per active mod
            for m in active:
                img_name = f"mod_{m.id}.png"
                png = banner.mod_card_banner(
                    mod_name=m.name,
                    author=m.author,
                    source=m.source.value if m.source else "unknown",
                    version=m.current_version,
                )
                file = discord.File(io.BytesIO(png), filename=img_name)

                embed = mod_card_embed(
                    mod_name=m.name,
                    description=m.description,
                    source=m.source.value if m.source else "unknown",
                    source_url=m.source_url,
                    added_by=m.added_by_user.discord_username if m.added_by_user else None,
                    image_filename=img_name,
                )
                view = RemoveModView(m.id)

                existing = (
                    await self._safe_fetch_message(channel, m.discord_message_id)
                    if m.discord_channel_id == str(channel.id)
                    else None
                )

                if existing:
                    try:
                        await existing.edit(embed=embed, view=view, attachments=[file])
                    except discord.HTTPException:
                        existing = None
                        file = discord.File(io.BytesIO(png), filename=img_name)

                if not existing:
                    msg = await channel.send(embed=embed, view=view, file=file)
                    m.discord_message_id = str(msg.id)
                    m.discord_channel_id = str(msg.channel.id)
                    db.commit()
        finally:
            db.close()

    # ── Server status ────────────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def status_refresh(self):
        try:
            await self.refresh_status()
        except Exception:
            logger.exception("Status refresh failed")

    @status_refresh.before_loop
    async def _wait_status(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def _bucket_now() -> datetime:
        """Round current UTC time down to the nearest 10-minute boundary.

        Returns a NAIVE datetime (no tzinfo) because PostgreSQL DateTime
        without timezone=True strips tz, and we need dict lookups to match.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        return now.replace(minute=now.minute // 10 * 10, second=0, microsecond=0)

    def _record_heartbeat(self, db, *, online: bool, player_count: int) -> None:
        bucket = self._bucket_now()
        existing = db.query(ServerHeartbeat).filter(ServerHeartbeat.bucket == bucket).first()
        if existing:
            # If any check in the bucket saw online, keep it online
            if online:
                existing.online = True
            existing.player_count = max(existing.player_count, player_count)
            existing.checked_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            db.add(
                ServerHeartbeat(
                    bucket=bucket,
                    online=online,
                    player_count=player_count,
                    checked_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
        db.commit()

    def _get_uptime_buckets(self, db, hours: int = 720) -> list[dict]:
        """Return the last N hours of 10-minute buckets for uptime display.
        Default 720h = 30 days.

        All datetimes are naive UTC to match what PostgreSQL stores.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        cutoff = now - timedelta(hours=hours)
        rows = (
            db.query(ServerHeartbeat)
            .filter(ServerHeartbeat.bucket >= cutoff)
            .order_by(ServerHeartbeat.bucket.asc())
            .all()
        )

        # Build lookup — strip tzinfo from DB values in case some have it
        lookup = {}
        for r in rows:
            key = r.bucket.replace(tzinfo=None) if r.bucket.tzinfo else r.bucket
            lookup[key] = r

        buckets = []
        b = cutoff.replace(minute=cutoff.minute // 10 * 10, second=0, microsecond=0)
        while b <= now:
            row = lookup.get(b)
            buckets.append(
                {
                    "bucket": b.isoformat(),
                    "online": row.online if row else None,
                    "players": row.player_count if row else 0,
                }
            )
            b += timedelta(minutes=10)
        return buckets

    def _get_world_size_mb(self) -> float | None:
        """Return world directory size in MB, or None if not found."""
        try:
            world_path = Path(self.settings.server_path) / "world"
            if not world_path.exists():
                return None
            total = sum(f.stat().st_size for f in world_path.rglob("*") if f.is_file())
            return total / (1024 * 1024)
        except Exception:
            return None

    async def refresh_status(self) -> None:
        channel = await self._get_channel("channel_server_status")
        if channel is None:
            logger.warning("refresh_status: channel_server_status not configured/resolvable")
            return

        me = channel.guild.me if channel.guild else None
        if me:
            perms = channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links and perms.read_message_history):
                logger.warning(
                    "refresh_status: bot lacks perms in #%s (send=%s embed=%s history=%s)",
                    channel.name,
                    perms.send_messages,
                    perms.embed_links,
                    perms.read_message_history,
                )
                return

        # Fetch fresh data — RCON can block, so push it to a thread
        loop = asyncio.get_running_loop()
        try:
            status = await loop.run_in_executor(None, self._server_mgr.get_status)
        except Exception:
            logger.exception("Failed to fetch server status")
            status = {"online": False, "players": [], "player_count": 0}

        is_online = status.get("online", False)
        player_count = status.get("player_count", 0)

        # World size (can be slow, run in executor)
        world_size_mb = await loop.run_in_executor(None, self._get_world_size_mb)

        db = SessionLocal()
        try:
            active_mods = db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).count()
            # Record heartbeat
            self._record_heartbeat(db, online=is_online, player_count=player_count)
            # Get uptime history for 30 days
            buckets = self._get_uptime_buckets(db, hours=720)
        finally:
            db.close()

        # Calculate uptime percentage from full 30-day window
        recent = [b for b in buckets if b["online"] is not None]
        if recent:
            up_count = sum(1 for b in recent if b["online"])
            uptime_pct = round(100 * up_count / len(recent), 1)
        else:
            uptime_pct = 0.0

        img_name = "status.png"
        png = banner.status_banner(
            online=is_online,
            player_count=player_count,
            active_mods=active_mods,
            uptime_pct=uptime_pct,
            uptime_buckets=buckets,
            world_size_mb=world_size_mb,
        )

        embed = server_status_embed(
            online=is_online,
            players=status.get("players", []),
            last_checked=datetime.now(UTC),
            active_mods=active_mods,
            uptime_pct=uptime_pct,
            world_size_mb=world_size_mb,
            image_filename=img_name,
        )

        def _make_file() -> discord.File:
            return discord.File(io.BytesIO(png), filename=img_name)

        # Find or create the single status message
        msg: discord.Message | None = None
        if self._status_message_id:
            msg = await self._safe_fetch_message(channel, self._status_message_id)

        if msg is None:
            try:
                async for m in channel.history(limit=50):
                    if m.author.id == self.bot.user.id:
                        if msg is None:
                            msg = m
                            self._status_message_id = m.id
                        else:
                            await self._safe_delete(m)
            except discord.Forbidden:
                logger.warning("Missing read history permission in #server-status")

        if msg is None:
            try:
                msg = await channel.send(embed=embed, file=_make_file())
                self._status_message_id = msg.id
            except discord.HTTPException:
                logger.exception("Failed to send status message")
            return

        try:
            await msg.edit(embed=embed, attachments=[_make_file()])
        except discord.HTTPException:
            logger.exception("Failed to edit status message")

    # ── Mod update channel ────────────────────────────────────────────

    async def _post_mod_update(self, data: dict) -> None:
        """Post a mod update notification to the mod-updates channel."""
        channel = await self._get_channel("channel_mod_updates")
        if channel is None:
            return

        mod_name = data.get("name", "Unknown Mod")
        old_version = data.get("old_version")
        new_version = data.get("new_version")
        changelog = data.get("changelog")

        # Look up source URL from DB
        source_url = None
        db = SessionLocal()
        try:
            mod_id = data.get("mod_id")
            if mod_id:
                mod = db.query(Mod).filter(Mod.id == mod_id).first()
                if mod:
                    source_url = mod.source_url
        finally:
            db.close()

        img_name = f"update_{mod_name[:20].replace(' ', '_')}.png"
        png = banner.update_log_banner(
            mod_name=mod_name,
            old_version=old_version,
            new_version=new_version,
        )
        file = discord.File(io.BytesIO(png), filename=img_name)

        embed = mod_update_embed(
            mod_name=mod_name,
            old_version=old_version,
            new_version=new_version,
            changelog=changelog,
            source_url=source_url,
            image_filename=img_name,
        )

        try:
            await channel.send(embed=embed, file=file)
        except discord.HTTPException:
            logger.exception("Failed to post mod update for %s", mod_name)

    # ── Mod export command ──────────────────────────────────────────

    @commands.command(name="modlist")
    async def modlist_command(self, ctx: commands.Context):
        """Send a text file listing all active mods."""
        db = SessionLocal()
        try:
            active = db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).order_by(Mod.name.asc()).all()

            if not active:
                await ctx.reply("No active mods on the server.")
                return

            lines = [f"MineShare Active Mod List ({len(active)} mods)", "=" * 50, ""]
            for m in active:
                line = f"• {m.name}"
                if m.author:
                    line += f" (by {m.author})"
                if m.current_version:
                    line += f" — {m.current_version}"
                if m.source_url:
                    line += f"\n  {m.source_url}"
                lines.append(line)

            text = "\n".join(lines)

            # Also create a JSON manifest for easy importing
            manifest = {
                "name": "MineShare Modpack",
                "mods": [
                    {
                        "name": m.name,
                        "author": m.author,
                        "source": m.source.value if m.source else "unknown",
                        "curse_project_id": m.curse_project_id,
                        "file_name": m.file_name,
                        "source_url": m.source_url,
                    }
                    for m in active
                ],
            }

            txt_file = discord.File(
                io.BytesIO(text.encode("utf-8")),
                filename="mineshare_modlist.txt",
            )
            json_file = discord.File(
                io.BytesIO(json.dumps(manifest, indent=2).encode("utf-8")),
                filename="mineshare_modlist.json",
            )

            await ctx.reply(
                f"Here's the current mod list ({len(active)} active mods):",
                files=[txt_file, json_file],
            )
        finally:
            db.close()

    # ── Live Discord role sync ───────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if {r.id for r in before.roles} == {r.id for r in after.roles}:
            return
        await self._sync_member_roles(after)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._sync_member_roles(member, removed=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._sync_member_roles(member)

    async def _sync_member_roles(self, member: discord.Member, *, removed: bool = False) -> None:
        role1_id = self.settings.discord_role1_id
        role2_id = self.settings.discord_role2_id
        if not role1_id and not role2_id:
            return

        member_role_ids = {str(r.id) for r in member.roles}
        if removed:
            new_role = UserRole.GUEST
        elif role2_id and role2_id in member_role_ids:
            new_role = UserRole.ADMIN
        elif role1_id and role1_id in member_role_ids:
            new_role = UserRole.MEMBER
        else:
            new_role = UserRole.GUEST

        loop = asyncio.get_running_loop()

        def _apply() -> str | None:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.discord_id == str(member.id)).first()
                if not user:
                    return None
                if user.role == new_role:
                    return None
                old = user.role.value
                user.role = new_role
                db.commit()
                db.refresh(user)
                # Sync whitelist/OP immediately
                wl = WhitelistManager(self._server_mgr)
                wl._sync_user(db, user)
                db.commit()
                return f"{user.discord_username} {old} -> {new_role.value}"
            finally:
                db.close()

        try:
            result = await loop.run_in_executor(None, _apply)
            if result:
                logger.info("Live role sync: %s", result)
        except Exception:
            logger.exception("Live role sync failed for %s", member.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsListenerCog(bot))
