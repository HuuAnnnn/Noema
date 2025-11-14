import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta, date
import re
import io

logger = logging.getLogger(__name__)

# Reuse same log channel
LOG_CHANNEL_ID = 1426956645342384190
MAX_MESSAGES_SCAN = 2000


class ThongKeBeNgoan(commands.Cog):
    """Aggregate 'phiếu bé ngoan' records similarly to `thongkebehu` but for bé ngoan."""

    def __init__(self, bot):
        self.bot = bot
        self._mention_re = re.compile(r"<@!?(?P<id>\d+)>")

    async def _week_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        today = date.today()
        for i in range(0, 16):
            wk = today - timedelta(weeks=i)
            y, w, _ = wk.isocalendar()
            val = f"{y}-W{w:02d}"
            if current.lower() in val.lower():
                choices.append(app_commands.Choice(name=val, value=val))
            if len(choices) >= 25:
                break
        return choices

    async def _month_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        today = date.today()
        for i in range(0, 12):
            m = (today.month - i - 1) % 12 + 1
            y = today.year - ((today.month - i - 1) // 12)
            val = f"{y}-{m:02d}"
            if current.lower() in val.lower():
                choices.append(app_commands.Choice(name=val, value=val))
            if len(choices) >= 25:
                break
        return choices

    async def _user_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        try:
            guild = interaction.guild
            if not guild:
                return choices
            prefix = (current or "").lower()
            for member in guild.members:
                display = member.display_name
                if prefix in display.lower() or prefix in member.name.lower():
                    choices.append(
                        app_commands.Choice(name=f"{display}", value=str(member.id))
                    )
                if len(choices) >= 25:
                    break
        except Exception:
            pass
        return choices

    @app_commands.command(
        name="thongkebengoan",
        description="Thống kê số phiếu bé ngoan theo tuần/tháng",
    )
    @app_commands.autocomplete(
        week=_week_autocomplete, month=_month_autocomplete, user=_user_autocomplete
    )
    async def thongkebengoan(
        self,
        interaction: discord.Interaction,
        week: str | None = None,
        month: str | None = None,
        user: str | None = None,
    ):
        await interaction.response.defer(thinking=True)

        # get log channel
        try:
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel is None:
                log_channel = await self.bot.fetch_channel(LOG_CHANNEL_ID)
        except Exception as e:
            logger.exception(f"Cannot access log channel {LOG_CHANNEL_ID}: {e}")
            await interaction.followup.send(
                f"Không thể truy cập kênh log (ID {LOG_CHANNEL_ID})."
            )
            return

        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            await interaction.followup.send(
                "Kênh log không phải là kênh text/thread hợp lệ."
            )
            return

        pattern = re.compile(
            r"(?P<username>.+?)\s+đã được tặng 1 phiếu bé ngoan(?:.*vào(?:ngày|lúc)?\s*(?P<date>\d{1,2}/\d{1,2}/\d{4}))?",
            re.I,
        )

        counts: dict = {}
        scanned = 0

        try:
            async for msg in log_channel.history(limit=MAX_MESSAGES_SCAN):
                scanned += 1
                content = (msg.content or "").strip()
                if not content:
                    continue
                m = pattern.search(content)
                if not m:
                    continue

                username = m.group("username").strip()
                date_str = m.group("date")
                if date_str:
                    try:
                        dt = datetime.strptime(date_str, "%d/%m/%Y")
                    except Exception:
                        continue
                else:
                    dt = msg.created_at

                # user filter
                if user:
                    try:
                        uid = int(user)
                        member = (
                            interaction.guild.get_member(uid)
                            if interaction.guild
                            else None
                        )
                        if member:
                            if (
                                member.display_name != username
                                and member.name != username
                                and f"<@{uid}>" not in content
                                and f"<@!{uid}>" not in content
                            ):
                                continue
                        else:
                            if (
                                str(uid) not in content
                                and f"<@{uid}>" not in content
                                and f"<@!{uid}>" not in content
                            ):
                                continue
                    except Exception:
                        pass

                if month:
                    try:
                        y_s, m_s = month.split("-")
                        yv = int(y_s)
                        mv = int(m_s)
                    except Exception:
                        yv = dt.year
                        mv = dt.month
                    key = ("month", yv, mv)
                else:
                    yv, wk, _ = dt.isocalendar()
                    if week:
                        try:
                            wparts = week.split("-W")
                            wy = int(wparts[0])
                            ww = int(wparts[1])
                            if not (wy == yv and ww == wk):
                                continue
                        except Exception:
                            pass
                    key = ("week", yv, wk)

                counts.setdefault(key, {})
                counts[key][username] = counts[key].get(username, 0) + 1
        except Exception as e:
            logger.exception(f"Error while scanning log channel: {e}")
            await interaction.followup.send("Lỗi khi đọc dữ liệu từ kênh log.")
            return

        if not counts:
            await interaction.followup.send(
                "Không tìm thấy bản ghi phiếu bé ngoan trong kênh log."
            )
            return

        def _display_name(raw_name: str) -> str:
            if not raw_name:
                return raw_name
            m = self._mention_re.search(raw_name)
            if m and interaction.guild:
                try:
                    mid = int(m.group("id"))
                    member = interaction.guild.get_member(mid) or self.bot.get_user(mid)
                    if member:
                        return getattr(member, "display_name", str(member))
                except Exception:
                    pass
            return re.sub(r"[<>]", "", raw_name).replace("@", "")

        # Build report
        lines: list[str] = []
        for key in sorted(counts.keys(), reverse=True):
            kind, year, num = key
            if kind == "week":
                try:
                    week_start = date.fromisocalendar(year, num, 1)
                    week_end = week_start + timedelta(days=6)
                    header = f"Tuần {year}-W{num:02d} ({week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})"
                except Exception:
                    header = f"Tuần {year}-W{num}"
            else:
                try:
                    header = f"Tháng {year}-{num:02d}"
                except Exception:
                    header = f"Tháng {year}-{num}"

            lines.append(header)
            users = sorted(counts[key].items(), key=lambda kv: kv[1], reverse=True)
            for uname, cnt in users:
                lines.append(f" - {_display_name(uname)}: {cnt}")
            lines.append("")

        report = "\n".join(lines).strip()

        embed = discord.Embed(title="Thống kê phiếu bé ngoan", color=0x2ECC71)
        embed.set_footer(text=f"Quét {scanned} tin nhắn từ kênh log")

        for key in sorted(counts.keys(), reverse=True):
            kind, year, num = key
            if kind == "week":
                try:
                    week_start = date.fromisocalendar(year, num, 1)
                    week_end = week_start + timedelta(days=6)
                    header = f"Tuần {year}-W{num:02d} ({week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})"
                except Exception:
                    header = f"Tuần {year}-W{num}"
            else:
                header = f"Tháng {year}-{num:02d}"

            users = sorted(counts[key].items(), key=lambda kv: kv[1], reverse=True)
            short_lines = [
                f"{i+1}. {_display_name(uname)}: {cnt}"
                for i, (uname, cnt) in enumerate(users[:10])
            ]
            value = "\n".join(short_lines) if short_lines else "Không có"
            embed.add_field(name=header, value=value, inline=False)

        try:
            if sum(len(field.value or "") for field in embed.fields) < 3500:
                await interaction.followup.send(embed=embed)
            else:
                bio = io.BytesIO(report.encode("utf-8"))
                bio.seek(0)
                file = discord.File(bio, filename="thongke_bengoan.txt")
                compact = discord.Embed(
                    title="Thống kê phiếu bé ngoan (tóm tắt)", color=0x2ECC71
                )
                compact.set_footer(text=f"Quét {scanned} tin nhắn từ kênh log")
                for key in sorted(counts.keys(), reverse=True)[:3]:
                    kind, year, num = key
                    users = sorted(
                        counts[key].items(), key=lambda kv: kv[1], reverse=True
                    )
                    top = ", ".join([f"{_display_name(u)}:{c}" for u, c in users[:5]])
                    if kind == "week":
                        name = f"{year}-W{num}"
                    else:
                        name = f"{year}-{num:02d}"
                    compact.add_field(name=name, value=top or "Không có", inline=False)
                await interaction.followup.send(embed=compact, file=file)
        except Exception as e:
            logger.exception(f"Failed to send statistics: {e}")
            await interaction.followup.send("Không thể gửi thống kê do lỗi nội bộ.")


async def setup(bot):
    await bot.add_cog(ThongKeBeNgoan(bot))
