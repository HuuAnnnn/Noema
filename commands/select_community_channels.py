import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class SelectCommunityChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="select_community_channels", description="Select a voice channel as community channel (Founder/Co-founder only)")
    async def select_community_channels(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        print(self.bot.community_channels)
        """Select a voice channel as community channel (Founder/Co-founder only)."""
        try:
            # Defer the response immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            logger.info(f"Selection community channels command used by {interaction.user.name} ({interaction.user.id}) in {interaction.guild.name} - Selected channel: {channel.name}")

            founder_roles = ["founder", "co-founder", "admin", "Admin"]
            user_roles = [role.name.lower() for role in interaction.user.roles]
            
            if not any(role in user_roles for role in founder_roles):
                logger.warning(f"Unauthorized access attempt by {interaction.user.name} ({interaction.user.id}) for select_community_channels command")
                await interaction.followup.send("You need to be a Founder or Co-founder to use this command!", ephemeral=True)
                return

            # Set the community channel immediately
            self.bot.community_channels[interaction.guild.id] = [channel]
            logger.info(f"Community channel set to {channel.name} ({channel.id}) by {interaction.user.name}")
            
            # Send the response using followup since we deferred
            await interaction.followup.send(
                f"Community channel set to: {channel.mention}!",
                ephemeral=True
            )
            
        except discord.NotFound as e:
            print(e)
            logger.error(f"Interaction not found for select_community_channels command by {interaction.user.name}")
        except Exception as e:
            logger.error(f"Error in select_community_channels command: {str(e)}")
            try:
                # Try to send a followup message if the interaction is still valid
                await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
            except:
                logger.error("Could not send error response for select_community_channels")

async def setup(bot):
    await bot.add_cog(SelectCommunityChannels(bot)) 