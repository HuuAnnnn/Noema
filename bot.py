import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NoemaBot(commands.Bot):
    def __init__(self, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        super().__init__(command_prefix=commands.when_mentioned_or('/'), description='Noema, your helpful Discord bot.', intents=intents, **kwargs)
        self.community_channels = {}
        # Store voice-text channel pairs
        self.channel_pairs = {}

    async def setup_hook(self):
        # Load all command Cogs
        for filename in os.listdir('./commands'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'commands.{filename[:-3]}')
                    logger.info(f"Loaded extension: commands.{filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension commands.{filename[:-3]}: {e}")

    async def on_ready(self):
        logger.info(f"Bot logged in as {self.user.name} (ID: {self.user.id})")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

def run_bot():
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        return
    bot = NoemaBot()
    bot.run(token)

if __name__ == '__main__':
    run_bot() 