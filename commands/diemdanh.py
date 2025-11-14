import discord
from discord.ext import commands
from discord import app_commands
import logging
import tempfile
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class Diemdanh(commands.Cog):
    """Attendance tracking command - export voice channel members to .txt file"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="diemdanh",
        description="Xuất danh sách thành viên trong phòng voice hiện tại ra file .txt",
    )
    async def diemdanh(self, interaction: discord.Interaction):
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "Bạn phải ở trong một phòng voice để sử dụng lệnh này.", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        members = voice_channel.members

        if not members:
            await interaction.response.send_message(
                "Phòng voice trống.", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Generate .txt file with member names only
        filename = f"diemdanh_{voice_channel.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                for member in members:
                    tmp.write(f"{member.display_name}\n")
                tmp_path = tmp.name

            # Send file
            file = discord.File(tmp_path, filename=filename)
            await interaction.followup.send(
                f"Danh sách {len(members)} thành viên trong phòng **{voice_channel.name}**:",
                file=file,
            )

            logger.info(
                f"Generated attendance list for {voice_channel.name} with {len(members)} members"
            )

        except Exception as e:
            logger.error(f"Error generating attendance file: {e}")
            await interaction.followup.send(
                f"Lỗi khi tạo file: {str(e)}", ephemeral=True
            )
        finally:
            # Clean up temp file
            try:
                if tmp_path is not None:
                    os.unlink(tmp_path)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Diemdanh(bot))
