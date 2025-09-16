import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class VoiceEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            logger.info(f"User {member.name} ({member.id}) joined voice channel {after.channel.name} ({after.channel.id})")
            print(self.bot.community_channels)
            community_channel = self.bot.community_channels[member.guild.id]
            if community_channel and after.channel.id in [channel.id for channel in community_channel]:
                logger.info(f"User {member.name} joined community channel {after.channel.name}")
                category = after.channel.category
                try:
                    # Create voice channel first
                    voice_channel = await member.guild.create_voice_channel(
                        name=f"{member.display_name}",
                        category=category
                    )
                    logger.info(f"Created voice channel {voice_channel.name} in category: {voice_channel.category.name if voice_channel.category else 'None'}")
                    
                    # Create text channel with category and position
                    text_channel = await member.guild.create_text_channel(
                        name=f"{member.display_name}",
                        category=category,
                        position=voice_channel.position + 1
                    )
                    logger.info(f"Created text channel {text_channel.name} in category: {text_channel.category.name if text_channel.category else 'None'}")
                    
                    # Force text channel into category if it's not there
                    if category and text_channel.category != category:
                        logger.warning(f"Text channel not in correct category, attempting to fix...")
                        try:
                            await text_channel.edit(category=category, position=voice_channel.position + 1)
                            logger.info(f"Fixed text channel category: {text_channel.category.name if text_channel.category else 'None'}")
                        except Exception as e:
                            logger.error(f"Failed to fix text channel category: {str(e)}")
                    elif category:
                        # Even if category is correct, ensure position is right
                        try:
                            await text_channel.edit(position=voice_channel.position + 1)
                            logger.info(f"Updated text channel position to be after voice channel")
                        except Exception as e:
                            logger.error(f"Failed to update text channel position: {str(e)}")
                    
                    # Store the channel pair
                    self.bot.channel_pairs[voice_channel.id] = text_channel.id
                    self.bot.channel_pairs[text_channel.id] = voice_channel.id
                    
                    logger.info(f"Created room for {member.display_name}: Voice={voice_channel.name} ({voice_channel.id}), Text={text_channel.name} ({text_channel.id})")
                    
                    await member.move_to(voice_channel)
                    await text_channel.send(f"Welcome to {member.display_name}'s room!")
                    logger.info(f"Moved {member.name} to their personal room {voice_channel.name}")

                except discord.Forbidden:
                    logger.error(f"Permission denied to create channels for {member.display_name}")
                except Exception as e:
                    logger.error(f"Error creating channels for {member.display_name}: {str(e)}")

        # When someone leaves a voice channel
        elif before.channel is not None and after.channel is None:
            logger.info(f"User {member.name} ({member.id}) left voice channel {before.channel.name} ({before.channel.id})")
            # Check if they left their personal room (auto-created by bot)
            if before.channel.name == member.display_name:
                logger.info(f"User {member.name} left their personal room {before.channel.name}")
                # Check if the room is now empty
                if len(before.channel.members) == 0:
                    logger.info(f"Personal room {before.channel.name} is now empty, deleting auto-created channels")
                    try:
                        # Get paired text channel from stored pairs
                        text_channel_id = self.bot.channel_pairs.get(before.channel.id)
                        text_channel = None
                        if text_channel_id:
                            text_channel = member.guild.get_channel(text_channel_id)
                            logger.info(f"Found paired text channel: {text_channel.name} ({text_channel.id})")
                        
                        # Delete voice channel
                        await before.channel.delete()
                        logger.info(f"Deleted auto-created voice channel: {before.channel.name} ({before.channel.id})")
                        
                        # Delete text channel if found
                        if text_channel:
                            await text_channel.delete()
                            logger.info(f"Deleted auto-created text channel: {text_channel.name} ({text_channel.id})")
                            # Remove from pairs
                            if before.channel.id in self.bot.channel_pairs:
                                del self.bot.channel_pairs[before.channel.id]
                            if text_channel.id in self.bot.channel_pairs:
                                del self.bot.channel_pairs[text_channel.id]
                            logger.info(f"Removed channel pairs for {member.display_name}")
                            
                        logger.info(f"Successfully deleted auto-created room for {member.display_name}")
                        
                    except discord.Forbidden:
                        logger.error(f"Permission denied to delete channels for {member.display_name}")
                    except Exception as e:
                        logger.error(f"Error deleting channels for {member.display_name}: {str(e)}")
            
            # Only delete auto-created channels that are in our pairs
            elif len(before.channel.members) == 0 and before.channel.id in self.bot.channel_pairs:
                logger.info(f"Auto-created voice channel {before.channel.name} is now empty, checking for paired channels")
                try:
                    # Get paired text channel from stored pairs
                    text_channel_id = self.bot.channel_pairs.get(before.channel.id)
                    text_channel = None
                    if text_channel_id:
                        text_channel = member.guild.get_channel(text_channel_id)
                        logger.info(f"Found paired text channel: {text_channel.name} ({text_channel.id})")
                    
                    # Delete voice channel
                    await before.channel.delete()
                    logger.info(f"Deleted auto-created voice channel: {before.channel.name} ({before.channel.id})")
                    
                    # Delete text channel if found
                    if text_channel:
                        await text_channel.delete()
                        logger.info(f"Deleted auto-created text channel: {text_channel.name} ({text_channel.id})")
                        # Remove from pairs
                        if before.channel.id in self.bot.channel_pairs:
                            del self.bot.channel_pairs[before.channel.id]
                        if text_channel.id in self.bot.channel_pairs:
                            del self.bot.channel_pairs[text_channel.id]
                        logger.info(f"Removed channel pairs for {before.channel.name}")
                        
                    logger.info(f"Successfully deleted auto-created room: {before.channel.name}")
                    
                except discord.Forbidden:
                    logger.error(f"Permission denied to delete channels for {before.channel.name}")
                except Exception as e:
                    logger.error(f"Error deleting channels for {before.channel.name}: {str(e)}")

async def setup(bot):
    await bot.add_cog(VoiceEvents(bot)) 