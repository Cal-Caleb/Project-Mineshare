import discord
from discord import app_commands
from discord.ext import commands

from core.database import SessionLocal
from core.events import CHANNEL_MOD_ADDED, get_event_bus
from core.mod_manager import ModManager
from core.vote_manager import VoteManager
from models import EventSource, Mod, ModStatus, User, UserRole, VoteType


def _get_user(db, discord_id) -> User | None:
    return db.query(User).filter(User.discord_id == str(discord_id)).first()


class ModsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="addmod", description="Add a mod from CurseForge")
    @app_commands.describe(
        url="CurseForge mod URL",
        force="(Admin) Skip voting and add instantly",
    )
    async def addmod(
        self,
        interaction: discord.Interaction,
        url: str,
        force: bool = False,
    ):
        await interaction.response.defer()
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user:
                await interaction.followup.send("Register on the web app first.", ephemeral=True)
                return
            if not user.mc_username:
                await interaction.followup.send("Set your MC username first (`/setmc`).", ephemeral=True)
                return
            if force and user.role != UserRole.ADMIN:
                await interaction.followup.send("Only admins can force-add.", ephemeral=True)
                return

            mgr = ModManager()
            info = await mgr.resolve_curseforge_url(url)
            if not info:
                await interaction.followup.send("Could not resolve that CurseForge URL.", ephemeral=True)
                return

            try:
                mod = mgr.add_mod_from_curseforge(db, info, user, url, force=force)
            except ValueError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

            if mod.status == ModStatus.ACTIVE:
                await interaction.followup.send(f"✅ **{mod.name}** added directly (admin force).")
            else:
                vote_mgr = VoteManager()
                vote_mgr.create_vote(db, mod, VoteType.ADD, user, source=EventSource.DISCORD)
                await interaction.followup.send(
                    f"🗳️ Vote started for **{mod.name}** — check the votes channel.",
                    ephemeral=True,
                )

            bus = get_event_bus()
            await bus.publish(
                CHANNEL_MOD_ADDED,
                {"mod_id": mod.id, "name": mod.name, "status": mod.status.value},
            )
        finally:
            db.close()

    @app_commands.command(name="removemod", description="Start a vote to remove a mod")
    @app_commands.describe(
        name="Name of the mod to remove",
        force="(Admin) Remove instantly without voting",
    )
    async def removemod(
        self,
        interaction: discord.Interaction,
        name: str,
        force: bool = False,
    ):
        await interaction.response.defer()
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user:
                await interaction.followup.send("Register on the web app first.", ephemeral=True)
                return

            mod = db.query(Mod).filter(Mod.name.ilike(f"%{name}%"), Mod.status == ModStatus.ACTIVE).first()
            if not mod:
                await interaction.followup.send(f"No active mod matching '{name}' found.", ephemeral=True)
                return

            if force and user.role == UserRole.ADMIN:
                mgr = ModManager()
                mgr.remove_mod(db, mod, user)
                await interaction.followup.send(f"Mod **{mod.name}** removed.")
                return

            if mod.added_by_id != user.id and user.role != UserRole.ADMIN:
                await interaction.followup.send(
                    "Only the original adder or an admin can initiate removal.", ephemeral=True
                )
                return

            vote_mgr = VoteManager()
            try:
                vote_mgr.create_vote(db, mod, VoteType.REMOVE, user, source=EventSource.DISCORD)
            except ValueError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

            await interaction.followup.send(
                f"🗳️ Removal vote started for **{mod.name}** — check the votes channel.",
                ephemeral=True,
            )
        finally:
            db.close()

    @app_commands.command(name="mods", description="List all active mods")
    async def list_mods(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            mods = db.query(Mod).filter(Mod.status == ModStatus.ACTIVE).order_by(Mod.name).all()
            if not mods:
                await interaction.response.send_message("No active mods.", ephemeral=True)
                return

            lines = [f"**{m.name}** — {m.current_version or 'N/A'} ({m.source.value})" for m in mods]
            embed = discord.Embed(
                title=f"Active Mods ({len(mods)})",
                description="\n".join(lines),
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(embed=embed)
        finally:
            db.close()

    @app_commands.command(name="setmc", description="Set your Minecraft username")
    @app_commands.describe(username="Your Minecraft Java Edition username")
    async def setmc(self, interaction: discord.Interaction, username: str):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user:
                await interaction.response.send_message("Register on the web app first.", ephemeral=True)
                return

            from core.server_manager import ServerManager
            from core.whitelist_manager import WhitelistManager

            wl = WhitelistManager(ServerManager())

            existing = db.query(User).filter(User.mc_username == username, User.id != user.id).first()
            if existing:
                await interaction.response.send_message("That username is already claimed.", ephemeral=True)
                return

            wl.set_minecraft_username(db, user, username)
            await interaction.response.send_message(
                f"Minecraft username set to **{username}**! You've been whitelisted."
            )
        finally:
            db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(ModsCog(bot))
