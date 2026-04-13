import discord
from discord import app_commands
from discord.ext import commands

from core.database import SessionLocal
from core.vote_manager import VoteManager
from models import User, Vote, VoteStatus


def _get_user(db, discord_id) -> User | None:
    return db.query(User).filter(User.discord_id == str(discord_id)).first()


class VotesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="votes", description="Show all active votes")
    async def active_votes(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            mgr = VoteManager()
            votes = mgr.get_active_votes(db)

            if not votes:
                await interaction.response.send_message("No active votes right now.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"Active Votes ({len(votes)})",
                color=discord.Color.gold(),
            )

            for vote in votes[:10]:  # Cap at 10 to avoid embed limits
                tally = mgr.get_tally(db, vote)
                embed.add_field(
                    name=f"{vote.vote_type.value.upper()}: {vote.mod.name}",
                    value=(
                        f"Yes: {tally['yes']} / No: {tally['no']}\nExpires <t:{int(vote.expires_at.timestamp())}:R>"
                    ),
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)
        finally:
            db.close()

    @app_commands.command(name="voteinfo", description="Get details on a specific vote")
    @app_commands.describe(vote_id="The vote ID number")
    async def vote_info(self, interaction: discord.Interaction, vote_id: int):
        db = SessionLocal()
        try:
            vote = db.query(Vote).filter(Vote.id == vote_id).first()
            if not vote:
                await interaction.response.send_message("Vote not found.", ephemeral=True)
                return

            mgr = VoteManager()
            tally = mgr.get_tally(db, vote)

            status_emoji = {
                VoteStatus.PENDING: "\U0001f7e1",
                VoteStatus.APPROVED: "\u2705",
                VoteStatus.REJECTED: "\u274c",
                VoteStatus.VETOED: "\U0001f6ab",
                VoteStatus.FORCE_APPROVED: "\u26a1",
                VoteStatus.EXPIRED: "\u23f0",
            }

            color = discord.Color.gold()
            if vote.status in (VoteStatus.APPROVED, VoteStatus.FORCE_APPROVED):
                color = discord.Color.green()
            elif vote.status in (VoteStatus.REJECTED, VoteStatus.VETOED):
                color = discord.Color.red()

            embed = discord.Embed(
                title=f"{status_emoji.get(vote.status, '')} {vote.vote_type.value.upper()}: {vote.mod.name}",
                color=color,
            )
            embed.add_field(name="Status", value=vote.status.value)
            embed.add_field(name="Yes", value=str(tally["yes"]))
            embed.add_field(name="No", value=str(tally["no"]))
            embed.add_field(name="Total", value=str(tally["total"]))

            if vote.status == VoteStatus.PENDING:
                embed.add_field(
                    name="Expires",
                    value=f"<t:{int(vote.expires_at.timestamp())}:R>",
                )

            # List voters
            if vote.ballots:
                voter_lines = []
                for b in vote.ballots:
                    icon = "\u2705" if b.in_favor else "\u274c"
                    voter_lines.append(f"{icon} {b.user.discord_username}")
                embed.add_field(
                    name="Voters",
                    value="\n".join(voter_lines),
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)
        finally:
            db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(VotesCog(bot))
