import discord
from discord.ext import commands
from discord import app_commands
import logging
import tempfile
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import openpyxl

    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False
    logger.warning("openpyxl not installed. Install with: pip install openpyxl")


class Validity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="validity",
        description="Kiểm tra thành viên không có role hoặc không có trong danh sách Excel",
    )
    async def validity(
        self, interaction: discord.Interaction, file: discord.Attachment
    ):
        if not HAVE_OPENPYXL:
            await interaction.response.send_message(
                "Chưa cài đặt openpyxl. Hãy chạy: pip install openpyxl", ephemeral=True
            )
            return

        if not file.filename.endswith((".xlsx", ".xlsm")):
            await interaction.response.send_message(
                "File phải có định dạng Excel (.xlsx hoặc .xlsm)", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Download and read Excel file
        excel_names = set()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            try:
                # Download attachment
                await file.save(tmp.name)

                # Read first column
                wb = openpyxl.load_workbook(tmp.name, read_only=True)
                sheet = wb.active
                for row in sheet.iter_rows(min_row=1, max_col=1):
                    if row[0].value:  # Skip empty cells
                        excel_names.add(str(row[0].value).strip().lower())
                wb.close()
            except Exception as e:
                logger.error(f"Failed to read Excel file: {e}")
                await interaction.followup.send(
                    f"Lỗi khi đọc file Excel: {str(e)}", ephemeral=True
                )
                return
            finally:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass

        if not interaction.guild:
            await interaction.followup.send(
                "Lệnh này chỉ dùng được trong server", ephemeral=True
            )
            return

        # Get all members
        members_no_roles = []
        members_not_in_excel = []

        for member in interaction.guild.members:
            member_name = member.display_name.lower()

            # Check for no roles (except @everyone)
            if len(member.roles) <= 1:  # 1 because @everyone is always present
                members_no_roles.append(member.mention)

            # Check if in Excel list
            if member_name not in excel_names:
                members_not_in_excel.append(member.mention)

        # Build response embed
        embed = discord.Embed(title="Kiểm tra thành viên", color=discord.Color.blue())

        if members_no_roles:
            embed.add_field(
                name="Thành viên không có role:",
                value="\n".join(members_no_roles) or "Không có",
                inline=False,
            )

        if members_not_in_excel:
            embed.add_field(
                name="Thành viên không có trong danh sách Excel:",
                value="\n".join(members_not_in_excel) or "Không có",
                inline=False,
            )

        if not members_no_roles and not members_not_in_excel:
            embed.description = "Không tìm thấy vấn đề: tất cả thành viên đều có role và có trong danh sách."

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Validity(bot))
