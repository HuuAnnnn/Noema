import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
import re
import io

logger = logging.getLogger(__name__)

LOG_CHANNEL_ID = 1426956645342384190
MAX_MESSAGES_SCAN = 3000


class BXHMentee(commands.Cog):
    """Compute leaderboard from mentee logs: khen +1, che -1."""

    def __init__(self, bot):
        self.bot = bot
        self._mention_re = re.compile(r"<@!?(?P<id>\d+)>")

    def _resolve_name(self, raw: str, guild: discord.Guild | None) -> str:
        if not raw:
            return ""
        m = self._mention_re.search(raw)
        if m:
            try:
                mid = int(m.group("id"))
                if guild:
                    member = guild.get_member(mid)
                    if member:
                        return member.display_name
                return re.sub(self._mention_re, "", raw).strip()
            except Exception:
                return re.sub(self._mention_re, "", raw).strip()
        return raw.strip()

    @app_commands.command(
        name="bxh_mentee", description="Bảng xếp hạng khen/chê (khen +1, chê -1)"
    )
    async def bxh_mentee(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        # fetch log channel
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
            await interaction.followup.send("Kênh log không hợp lệ.")
            return

        # Pattern: we logged messages as either "[mentee] <text>" where <text> contains either "được khen" or "bị chê"
        # We'll just inspect content and look for keywords.
        scores: dict[str, int] = {}
        counts: dict[str, dict[str, int]] = {}
        guild = interaction.guild

        # compute current ISO year-week
        now = datetime.utcnow()
        cur_year, cur_week, _ = now.isocalendar()

        try:
            async for msg in log_channel.history(limit=MAX_MESSAGES_SCAN):
                content = (msg.content or "").strip()
                if not content:
                    continue
                # Accept if message contains [mentee]
                if "[mentee]" not in content.lower():
                    continue

                # check if message date is in current ISO week
                try:
                    m_year, m_week, _ = msg.created_at.isocalendar()
                    if (m_year, m_week) != (cur_year, cur_week):
                        continue
                except Exception:
                    # if created_at not available, skip
                    continue

                # Remove the tag
                after = content.split("]", 1)[-1].strip() if "]" in content else content

                # crude detection: 'được khen' or 'được khen bởi' or 'khen'
                lowered = after.lower()
                is_khen = (
                    "khen" in lowered
                    and "bị chê" not in lowered
                    and "chê" not in lowered
                )
                is_che = "chê" in lowered or "ché" in lowered or "bị chê" in lowered

                # try to extract target: take left part before 'được' or 'bị'
                target_raw = None
                if "được" in lowered:
                    target_raw = after.split("được", 1)[0].strip()
                elif "bị" in lowered:
                    target_raw = after.split("bị", 1)[0].strip()
                else:
                    # fallback: take first token
                    target_raw = after.split()[0] if after.split() else after

                target_name = self._resolve_name(target_raw, guild)
                if not target_name:
                    continue

                scores.setdefault(target_name, 0)
                counts.setdefault(target_name, {"khen": 0, "che": 0})
                if is_khen:
                    scores[target_name] += 1
                    counts[target_name]["khen"] += 1
                elif is_che:
                    scores[target_name] -= 1
                    counts[target_name]["che"] += 1

        except Exception as e:
            logger.exception(f"Error scanning mentee logs: {e}")
            await interaction.followup.send("Lỗi khi đọc kênh log.")
            return

        if not scores:
            await interaction.followup.send(
                "Không tìm thấy dữ liệu mentee trong kênh log."
            )
            return

        # Build leaderboard sorted by score desc
        rows = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))

        embed = discord.Embed(title="Bảng xếp hạng bé ngoan Mentee", color=0x3498DB)
        embed.set_footer(text=f"Quét tối đa {MAX_MESSAGES_SCAN} tin nhắn")

        too_long = False
        lines = []
        for rank, (name, score) in enumerate(rows, start=1):
            k = counts.get(name, {}).get("khen", 0)
            c = counts.get(name, {}).get("che", 0)
            lines.append(f"{rank}. {name}: {score} (khen: {k}, chê: {c})")
            if len(lines) >= 25:
                too_long = True
                break

        if not too_long:
            embed.add_field(
                name="Bảng xếp hạng (top)", value="\n".join(lines), inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        # If too long, attach full report
        report_lines = [f"BXH Mentee - quét {MAX_MESSAGES_SCAN} tin nhắn\n"]
        for rank, (name, score) in enumerate(rows, start=1):
            k = counts.get(name, {}).get("khen", 0)
            c = counts.get(name, {}).get("che", 0)
            report_lines.append(f"{rank}. {name}: {score} (khen: {k}, chê: {c})")

        report = "\n".join(report_lines)
        bio = io.BytesIO(report.encode("utf-8"))
        bio.seek(0)
        file = discord.File(bio, filename="bxh_mentee.txt")
        compact = discord.Embed(title="BXH Mentee (tệp đính kèm)", color=0x3498DB)
        compact.add_field(
            name="Ghi chú", value="Báo cáo đầy đủ đính kèm.", inline=False
        )
        await interaction.followup.send(embed=compact, file=file)


async def setup(bot):
    await bot.add_cog(BXHMentee(bot))
