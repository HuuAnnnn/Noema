import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Reload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="reload", description="Reloads the bot commands (Admin only)")
    async def reload(self, interaction: discord.Interaction):
        """Reloads the bot commands (Admin only)."""
        logger.info(f"Reload command used by {interaction.user.name} ({interaction.user.id}) in {interaction.guild.name}")
        
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Unauthorized access attempt by {interaction.user.name} ({interaction.user.id}) for reload command")
            await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)
            return

        try:
            await self.bot.tree.sync()
            logger.info(f"Commands reloaded successfully by {interaction.user.name}")
            await interaction.response.send_message("Commands reloaded successfully!", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to reload commands: {str(e)}")
            await interaction.response.send_message(f"Failed to reload commands: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Reload(bot)) 