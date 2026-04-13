import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from core.database import SessionLocal
from core.scheduler import run_update_cycle
from core.server_manager import ServerManager
from core.whitelist_manager import WhitelistManager
from models import User, UserRole


def _get_user(db, discord_id) -> User | None:
    return db.query(User).filter(User.discord_id == str(discord_id)).first()


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="forceupdate", description="(Admin) Trigger a manual update cycle")
    async def forceupdate(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message("Admin access required.", ephemeral=True)
                return

            await interaction.response.send_message("Update cycle started. I'll report back when it's done.")
            await run_update_cycle()
            await interaction.followup.send("Update cycle completed.")
        finally:
            db.close()

    @app_commands.command(name="restart", description="(Admin) Restart the Minecraft server")
    async def restart(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message("Admin access required.", ephemeral=True)
                return

            await interaction.response.defer()
            mgr = ServerManager()
            mgr.announce("Server restarting by admin request!")
            await asyncio.sleep(5)

            success = mgr.restart_server(db, triggered_by_id=user.id)
            if success:
                await interaction.followup.send("Server restart initiated.")
            else:
                await interaction.followup.send("Server restart failed.")
        finally:
            db.close()

    @app_commands.command(
        name="syncwhitelist",
        description="(Admin) Sync whitelist and OP from Discord roles",
    )
    async def syncwhitelist(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message("Admin access required.", ephemeral=True)
                return

            await interaction.response.defer()
            mgr = ServerManager()
            wl = WhitelistManager(mgr)

            role_changes = await wl.sync_roles_from_discord(db)
            wl_result = wl.sync_all_users(db)

            embed = discord.Embed(title="Whitelist Sync Complete", color=discord.Color.green())
            embed.add_field(name="Role changes", value=str(role_changes))
            embed.add_field(name="Whitelisted", value=str(wl_result.get("whitelisted", 0)))
            embed.add_field(name="Unwhitelisted", value=str(wl_result.get("unwhitelisted", 0)))
            embed.add_field(name="Opped", value=str(wl_result.get("opped", 0)))
            embed.add_field(name="De-opped", value=str(wl_result.get("deopped", 0)))

            await interaction.followup.send(embed=embed)
        finally:
            db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
