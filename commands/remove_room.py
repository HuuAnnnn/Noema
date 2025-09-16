import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class RemoveRoom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="remove_room", description="Remove a room by selection (Founder/Co-founder only)")
    async def remove_room(self, interaction: discord.Interaction, room: discord.VoiceChannel | discord.TextChannel):
        logger.info(f"Remove room command used by {interaction.user.name} ({interaction.user.id}) in {interaction.guild.name} - Target room: {room.name}")
        founder_roles = ["founder", "co-founder", "cofounder"]
        user_roles = [role.name.lower() for role in interaction.user.roles]
        
        if not any(role in user_roles for role in founder_roles):
            logger.warning(f"Unauthorized access attempt by {interaction.user.name} ({interaction.user.id}) for remove_room command")
            await interaction.response.send_message("You need to be a Founder or Co-founder to use this command!", ephemeral=True)
            return

        try:
            # Check if the selected channel is a voice or text channel
            if not isinstance(room, (discord.VoiceChannel, discord.TextChannel)):
                logger.warning(f"Invalid channel type selected by {interaction.user.name}: {type(room)}")
                await interaction.response.send_message("Please select a voice or text channel!", ephemeral=True)
                return

            room_name = room.name
            voice_channel = None
            text_channel = None
            
            # Get the paired channel from stored pairs
            paired_channel_id = self.bot.channel_pairs.get(room.id)
            if paired_channel_id:
                paired_channel = interaction.guild.get_channel(paired_channel_id)
                if paired_channel:
                    if isinstance(room, discord.VoiceChannel):
                        voice_channel = room
                        text_channel = paired_channel
                    else:
                        voice_channel = paired_channel
                        text_channel = room
                    logger.info(f"Found paired channels for {room_name}: Voice={voice_channel.name}, Text={text_channel.name}")
            else:
                # Fallback: find channels by name if not in pairs
                logger.info(f"No paired channels found for {room_name}, searching by name")
                for channel in interaction.guild.channels:
                    if channel.name == room_name:
                        if isinstance(channel, discord.VoiceChannel):
                            voice_channel = channel
                        elif isinstance(channel, discord.TextChannel):
                            text_channel = channel

            deleted_channels = []
            
            # Delete voice channel if found
            if voice_channel:
                await voice_channel.delete()
                deleted_channels.append(f"Voice: {voice_channel.name}")
                logger.info(f"Deleted voice channel: {voice_channel.name} ({voice_channel.id})")
                # Remove from pairs
                if voice_channel.id in self.bot.channel_pairs:
                    del self.bot.channel_pairs[voice_channel.id]
            
            # Delete text channel if found
            if text_channel:
                await text_channel.delete()
                deleted_channels.append(f"Text: {text_channel.name}")
                logger.info(f"Deleted text channel: {text_channel.name} ({text_channel.id})")
                # Remove from pairs
                if text_channel.id in self.bot.channel_pairs:
                    del self.bot.channel_pairs[text_channel.id]

            if deleted_channels:
                logger.info(f"Successfully removed room {room_name} by {interaction.user.name}: {', '.join(deleted_channels)}")
                await interaction.response.send_message(
                    f"Successfully removed {room_name}: {', '.join(deleted_channels)}",
                    ephemeral=True
                )
            else:
                logger.warning(f"No channels found to delete for room name: {room_name}")
                await interaction.response.send_message(f"No channels found with name '{room_name}'!", ephemeral=True)

        except discord.Forbidden:
            logger.error(f"Permission denied for {interaction.user.name} to delete channels")
            await interaction.response.send_message("I don't have permission to delete channels!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in remove_room command: {str(e)}")
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RemoveRoom(bot)) 