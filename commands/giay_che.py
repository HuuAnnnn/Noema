import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GiayChe(commands.Cog):
    """Cog cung cấp slash command `/giayche <target>` để gửi giấy chê."""

    IMAGE_PATH = os.path.join("images", "giay_che.jpg")

    def __init__(self, bot):
        self.bot = bot
        # simple cog for giay che (mirrors phieubengoan behavior)

    @app_commands.command(
        name="giayche", description="Gửi giấy chê cho một thành viên (kèm lý do)"
    )
    async def giayche(
        self, interaction: discord.Interaction, target: discord.Member, ly_do: str
    ):
        """Slash command: send image and log sender, target, and required reason to the central log channel."""
        # Try to defer the interaction. If that fails (Unknown interaction),
        # record that and fall back to sending directly to the channel later.
        deferred = False
        try:
            await interaction.response.defer()
            deferred = True
        except Exception as e:
            logger.warning(
                f"Could not defer interaction (will fallback to channel send): {e}"
            )
            deferred = False

        sender = interaction.user
        target_name = (
            target.display_name if isinstance(target, discord.Member) else str(target)
        )
        sender_name = (
            sender.display_name if isinstance(sender, discord.Member) else str(sender)
        )

        # Message shown in-channel (mirror phieubengoan: plain text)
        message_text = (
            f"{target.mention} đã được ghi nhận giấy chê. Lý do: {ly_do}"
        )

        # Compose log text for the central log channel (plain name)
        timestamp = datetime.utcnow().strftime("%d/%m/%Y")
        log_text = f"{target.mention} bị ghi giấy chê bởi {sender_name} vào ngày {timestamp}. Lý do: {ly_do}"

        # Send log to central channel
        try:
            log_channel = self.bot.get_channel(1426956645342384190)
            if log_channel is None:
                try:
                    log_channel = await self.bot.fetch_channel(1426956645342384190)
                except Exception:
                    log_channel = None

            if log_channel is not None:
                try:
                    await log_channel.send(log_text)
                    logger.info(f"Logged giayche to {log_channel.id}: {log_text}")
                except Exception as e:
                    logger.error(f"Failed to send giayche log to channel: {e}")
            else:
                logger.error("Log channel for giayche not found")
        except Exception as e:
            logger.exception(f"Unexpected error while logging giayche: {e}")

        files = []
        try:
            if os.path.exists(self.IMAGE_PATH):
                files = [discord.File(self.IMAGE_PATH)]
            else:
                logger.warning(f"Giay che image not found at {self.IMAGE_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load giay che image: {e}")

        sent = False
        # If we successfully deferred, prefer followup
        if deferred:
            try:
                await interaction.followup.send(content=message_text, files=files)
                sent = True
            except Exception as e:
                logger.warning(f"Followup send failed, will attempt channel send: {e}")
                sent = False

        # Channel fallback if followup not sent
        if not sent:
            ch = None
            try:
                ch = interaction.channel
            except Exception:
                ch = None
            if ch is None and getattr(interaction, "channel_id", None):
                try:
                    ch = self.bot.get_channel(
                        interaction.channel_id
                    ) or await self.bot.fetch_channel(interaction.channel_id)
                except Exception:
                    ch = None

            if ch is not None and isinstance(ch, discord.abc.Messageable):
                try:
                    if files:
                        await ch.send(content=message_text, files=files)
                    else:
                        await ch.send(content=message_text)
                    sent = True
                except Exception as e:
                    logger.error(f"Channel fallback send failed: {e}")
            else:
                logger.error(
                    "No valid channel available for fallback send of giayche response"
                )


async def setup(bot):
    await bot.add_cog(GiayChe(bot))
