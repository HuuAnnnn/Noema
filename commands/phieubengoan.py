import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Logging destination channel ID (reuse same channel)
LOG_CHANNEL_ID = 1426956645342384190


class PhieuBeNgoan(commands.Cog):
    """Cog cung cấp slash command `/phieubengoan <tên người dùng>` để ghi nhận bé ngoan."""

    IMAGE_PATH = os.path.join("images", "PhieuBeNgoan.png")

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="phieubengoan",
        description="Ghi nhận 1 phiếu bé ngoan cho tên được cung cấp",
    )
    async def phieubengoan(self, interaction: discord.Interaction, ten_nguoi_dung: str):
        """Record a 'phiếu bé ngoan' by logging to the central channel and replying with an image."""
        await interaction.response.defer()

        username = ten_nguoi_dung.strip()
        timestamp = datetime.utcnow().strftime("%d/%m/%Y")

        log_text = f"{username} đã được tặng 1 phiếu bé ngoan vào ngày {timestamp}"

        # Send log to central channel
        try:
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel is None:
                try:
                    log_channel = await self.bot.fetch_channel(LOG_CHANNEL_ID)
                except Exception:
                    log_channel = None

            if log_channel is not None:
                try:
                    await log_channel.send(log_text)
                    logger.info(
                        f"Sent phieubengoan log to channel {LOG_CHANNEL_ID} for {username}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send phieubengoan log to channel: {e}")
            else:
                logger.error(f"Log channel with ID {LOG_CHANNEL_ID} not found")
        except Exception as e:
            logger.exception(f"Unexpected error while sending phieubengoan log: {e}")

        reply_text = f"{username} đã được ghi nhận 1 phiếu bé ngoan"

        files = []
        try:
            if os.path.exists(self.IMAGE_PATH):
                files = [discord.File(self.IMAGE_PATH)]
            else:
                logger.warning(f"Image not found at {self.IMAGE_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load image file: {e}")

        try:
            await interaction.followup.send(reply_text, files=files)
        except Exception as e:
            logger.error(f"Failed to send followup message: {e}")
            try:
                await interaction.followup.send(reply_text)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(PhieuBeNgoan(bot))
