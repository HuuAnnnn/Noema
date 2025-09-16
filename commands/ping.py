import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="Responds with pong.")
    async def ping(self, interaction: discord.Interaction):
        """Responds with pong."""
        logger.info(f"Ping command used by {interaction.user.name} ({interaction.user.id}) in {interaction.guild.name}")
        await interaction.response.send_message("Pong!")

async def setup(bot):
    await bot.add_cog(Ping(bot)) 