import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LOG_CHANNEL_ID = 1426956645342384190


class Mentee(commands.Cog):
    """/mentee <loai> <member> - loai: khen/che. When 'khen', log to central channel with [mentee] tag."""

    ICON_PHIEUBEHU = os.path.join("images", "ICON_PhieuBeHu.png")
    PHIEU_BENGOAN = os.path.join("images", "PhieuBeNgoan.png")

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mentee", description="Ghi nhận khen/ché cho thành viên")
    @app_commands.choices(
        loai=[
            app_commands.Choice(name="khen", value="khen"),
            app_commands.Choice(name="che", value="che"),
        ]
    )
    async def mentee(
        self,
        interaction: discord.Interaction,
        loai: app_commands.Choice[str],
        member: discord.Member,
    ):
        # Mirror giayche/phieubengoan behavior: defer with fallback
        deferred = False
        log_text = ""
        try:
            await interaction.response.defer()
            deferred = True
        except Exception as e:
            logger.warning(f"Could not defer interaction for /mentee: {e}")
            deferred = False

        sender = interaction.user
        sender_name = (
            sender.display_name if isinstance(sender, discord.Member) else str(sender)
        )

        target_mention = member.mention
        timestamp = datetime.utcnow().strftime("%d/%m/%Y")

        # Require the target to have a role containing 'Room' (case-insensitive)
        has_room_role = any("room" in (r.name or "").lower() for r in member.roles)
        if not has_room_role:
            do_log = False
            reply_text = f"{member.display_name} không phải mentor/mentee"
            image_path = None
        else:
            do_log = True
            # Compose log and reply
            if loai.value == "khen":
                log_text = f"[mentee] {member.mention} được khen bởi {sender_name} vào ngày {timestamp}"
                reply_text = f"{target_mention} đã được khen."
                image_path = self.PHIEU_BENGOAN
            else:
                log_text = f"[mentee] {member.mention} bị chê bởi {sender_name} vào ngày {timestamp}"
                reply_text = f"{target_mention} đã bị chê."
                image_path = self.ICON_PHIEUBEHU

        # Send log for both 'khen' and 'che' to central log channel with [mentee] tag if allowed
        if do_log:
            try:
                log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
                if log_channel is None:
                    try:
                        log_channel = await self.bot.fetch_channel(LOG_CHANNEL_ID)
                    except Exception:
                        log_channel = None

                if log_channel is not None:
                    try:
                        await log_channel.send(f"{log_text}")
                        logger.info(f"Logged mentee to {LOG_CHANNEL_ID}: {log_text}")
                    except Exception as e:
                        logger.error(f"Failed to send mentee log to channel: {e}")
                else:
                    logger.error("Log channel for mentee not found")
            except Exception as e:
                logger.exception(f"Unexpected error while logging mentee: {e}")

        files = []
        try:
            if image_path and os.path.exists(image_path):
                files = [discord.File(image_path)]
            else:
                logger.debug(f"Mentee image not found at {image_path}")
        except Exception as e:
            logger.warning(f"Failed to load mentee image: {e}")

        sent = False
        if deferred:
            try:
                await interaction.followup.send(content=reply_text, files=files)
                sent = True
            except Exception as e:
                logger.warning(
                    f"Followup send failed for /mentee, will attempt channel send: {e}"
                )
                sent = False

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
                        await ch.send(content=reply_text, files=files)
                    else:
                        await ch.send(content=reply_text)
                    sent = True
                except Exception as e:
                    logger.error(f"Channel fallback send failed for /mentee: {e}")
            else:
                logger.error(
                    "No valid channel available for fallback send of /mentee response"
                )


async def setup(bot):
    await bot.add_cog(Mentee(bot))
