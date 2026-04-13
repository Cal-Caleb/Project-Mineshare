import discord
from discord import app_commands
from discord.ext import commands

from core.database import SessionLocal
from core.server_manager import ServerManager
from models import User, UserRole


def _get_user(db, discord_id) -> User | None:
    return db.query(User).filter(User.discord_id == str(discord_id)).first()


class ServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="Check Minecraft server status")
    async def server_status(self, interaction: discord.Interaction):
        mgr = ServerManager()
        status = mgr.get_status()

        color = discord.Color.green() if status["online"] else discord.Color.red()
        embed = discord.Embed(
            title="Server Status",
            color=color,
        )
        embed.add_field(name="Status", value="Online" if status["online"] else "Offline")
        embed.add_field(name="Players", value=str(status["player_count"]))

        if status["players"]:
            embed.add_field(
                name="Online Players",
                value=", ".join(status["players"]),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="backup", description="Create a world backup (Admin)")
    async def backup(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            user = _get_user(db, interaction.user.id)
            if not user or user.role != UserRole.ADMIN:
                await interaction.response.send_message("Admin access required.", ephemeral=True)
                return

            await interaction.response.defer()
            mgr = ServerManager()
            result = mgr.backup_world(db, triggered_by_id=user.id)

            if result:
                await interaction.followup.send(f"Backup created: `{result}`")
            else:
                await interaction.followup.send("Backup failed.")
        finally:
            db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerCog(bot))
