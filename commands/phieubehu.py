import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime
import csv

logger = logging.getLogger(__name__)

# Logging destination channel ID for phieubehu records
LOG_CHANNEL_ID = 1426956645342384190


class PhieuBeHu(commands.Cog):
    """Cog cung cấp slash command `/phieubehu <tên người dùng>` để ghi nhận vào Google Sheet."""

    SHEET_URL = "https://docs.google.com/spreadsheets/d/1O214N712iDcRFOXkZN2sE5kElZen8RxgiQe-oq3ZtKc/edit?usp=sharing"
    LOCAL_CSV = "phieubehu_log.csv"
    ICON_PATH = os.path.join("images", "ICON_PhieuBeHu.png")

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="phieubehu", description="Ghi nhận 1 phiếu bé hư cho tên được cung cấp"
    )
    async def phieubehu(self, interaction: discord.Interaction, ten_nguoi_dung: str):
        """Slash command to record a report into Google Sheets and reply with image."""
        await interaction.response.defer()

        username = ten_nguoi_dung.strip()
        # Only date (day/month/year) as requested
        timestamp = datetime.utcnow().strftime("%d/%m/%Y")

        # Prepare log message to the designated channel
        log_channel_id = LOG_CHANNEL_ID
        log_text = f"{username} đã bị phạt 1 phiếu bé hư vào ngày {timestamp}"

        # Try to send the log message to the specified channel
        try:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel is None:
                # Try fetching the channel
                try:
                    log_channel = await self.bot.fetch_channel(log_channel_id)
                except Exception:
                    log_channel = None

            if log_channel is not None:
                try:
                    await log_channel.send(log_text)
                    logger.info(
                        f"Sent phieubehu log to channel {log_channel_id} for {username}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send phieubehu log to channel: {e}")
            else:
                logger.error(f"Log channel with ID {log_channel_id} not found")
        except Exception as e:
            logger.exception(f"Unexpected error while sending log to channel: {e}")

        reply_text = f"{username} đã được ghi nhận 1 phiếu bé hư"

        files = []
        try:
            if os.path.exists(self.ICON_PATH):
                files = [discord.File(self.ICON_PATH)]
            else:
                logger.warning(f"Icon not found at {self.ICON_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load icon file: {e}")

        # Send the response
        try:
            await interaction.followup.send(reply_text, files=files)
        except Exception as e:
            logger.error(f"Failed to send followup message: {e}")
            # As final fallback, try to send plain text
            try:
                await interaction.followup.send(reply_text)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(PhieuBeHu(bot))
