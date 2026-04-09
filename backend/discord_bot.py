import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional
import requests
from core import ModManager, VoteManager, ServerManager
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
mod_manager = ModManager()
vote_manager = VoteManager()
server_manager = ServerManager(
    server_path="/opt/minecraft/server",
    backup_path="/opt/minecraft/backups",
    rcon_host="localhost",
    rcon_port=25575,
    rcon_password="rconpassword"
)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Bot events
@bot.event
async def on_ready():
    logger.info(f'{bot.user} has logged in!')
    await bot.change_presence(activity=discord.Game(name="Managing mods"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found")
    else:
        logger.error(f"Error: {error}")
        await ctx.send("An error occurred")

# Slash commands
@bot.slash_command(name="addmod", description="Add a mod from CurseForge")
async def addmod(ctx, url: str):
    await ctx.respond(f"Adding mod from: {url}")
    
    # Resolve CurseForge URL
    curse_mod = mod_manager.resolve_curseforge_url(url)
    if not curse_mod:
        await ctx.followup.send("Invalid CurseForge URL")
        return
    
    # Simulate adding the mod
    await ctx.followup.send(f"Mod '{curse_mod.name}' added successfully!")

@bot.slash_command(name="removemod", description="Remove a mod")
async def removemod(ctx, mod_name: str):
    await ctx.respond(f"Removing mod: {mod_name}")
    # Simulate removal
    await ctx.followup.send(f"Mod '{mod_name}' removed successfully!")

@bot.slash_command(name="vote", description="Vote on a mod")
async def vote(ctx, mod_name: str, vote_type: str):
    await ctx.respond(f"Voting on {mod_name} with {vote_type}")
    # Simulate voting
    await ctx.followup.send(f"Vote recorded for {mod_name}")

@bot.slash_command(name="forceadd", description="Force add a mod (Role 2)")
async def forceadd(ctx, url: str):
    await ctx.respond("Force adding mod...")
    # Simulate force adding
    await ctx.followup.send("Mod force added successfully!")

@bot.slash_command(name="veto", description="Veto a vote (Role 2)")
async def veto(ctx, mod_name: str):
    await ctx.respond("Vetoing vote...")
    # Simulate veto
    await ctx.followup.send(f"Vote vetoed for {mod_name}")

@bot.slash_command(name="forceupdate", description="Force server update (Role 2)")
async def forceupdate(ctx):
    await ctx.respond("Force updating server...")
    # Simulate force update
    success = server_manager.run_update_loop()
    if success:
        await ctx.followup.send("Server update completed successfully!")
    else:
        await ctx.followup.send("Server update failed!")

@bot.slash_command(name="status", description="Check server status")
async def status(ctx):
    await ctx.respond("Checking server status...")
    # Simulate status check
    await ctx.followup.send("Server is online with 12 players")

@bot.slash_command(name="backup", description="Create world backup")
async def backup(ctx):
    await ctx.respond("Creating world backup...")
    backup_file = server_manager.backup_world()
    if backup_file:
        await ctx.followup.send(f"Backup created: {backup_file}")
    else:
        await ctx.followup.send("Backup failed!")

# Button components for voting
class VoteView(discord.ui.View):
    def __init__(self, mod_id: int):
        super().__init__(timeout=None)
        self.mod_id = mod_id
    
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Voted Yes!")
        # Add logic to record vote
    
    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Voted No!")
        # Add logic to record vote

# Start the bot
if __name__ == "__main__":
    # Bot token from environment variable
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        exit(1)
    
    bot.run(token)
