import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
import re
import io

logger = logging.getLogger(__name__)

LOG_CHANNEL_ID = 1426956645342384190
MAX_MESSAGES_SCAN = 2000


class ThongKeGiayChe(commands.Cog):
    """Aggregate 'giấy chê' logs and list entries per user with date and reason."""

    def __init__(self, bot):
        self.bot = bot
        self._mention_re = re.compile(r"<@!?(?P<id>\d+)>")

    def _resolve_name(self, raw: str, guild: discord.Guild | None) -> str:
        """Resolve a mention like <@123> to the guild member's display name when possible.

        If resolution fails, strip mention syntax and return a cleaned string.
        """
        if not raw:
            return ""
        m = self._mention_re.search(raw)
        if m:
            try:
                member_id = int(m.group("id"))
                if guild:
                    member = guild.get_member(member_id)
                    if member:
                        return member.display_name
                # fallback: remove mention markers
                return re.sub(self._mention_re, "", raw).strip()
            except Exception:
                return re.sub(self._mention_re, "", raw).strip()
        # not a mention; return raw cleaned
        return raw.strip()

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
        name="thongkegiayche",
        description="Danh sách giấy chê cho từng user (có ngày & lý do)",
    )
    @app_commands.autocomplete(user=_user_autocomplete)
    async def thongkegiayche(
        self, interaction: discord.Interaction, user: str
    ):
        """Scan the centralized log channel for 'giấy chê' entries and report results.

        The `user` parameter may be a member ID (from autocomplete) or free-text to match display names.
        """
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
            await interaction.followup.send(
                "Kênh log không phải là kênh text/thread hợp lệ."
            )
            return

        # Capture the entire reason text after 'Lý do:' (up to optional '. ID:...')
        pattern = re.compile(
            r"(?P<target>.+?)\s+bị ghi giấy chê bởi\s+(?P<sender>.+?)\s+vào ngày\s+(?P<date>\d{1,2}/\d{1,2}/\d{4})(?:\.\s*Lý do:\s*(?P<reason>.*?)(?=(?:\.\s*ID:\d+:\d+)|$))?(?:\.\s*ID:(?P<tid>\d+):(?P<sid>\d+))?",
            re.I | re.S,
        )

        entries: dict[str, list[tuple[str, str, str | None]]] = {}

        guild = interaction.guild

        try:
            async for msg in log_channel.history(limit=MAX_MESSAGES_SCAN):
                content = (msg.content or "").strip()
                if not content:
                    continue

                # Try strict regex first
                m = pattern.search(content)

                target_raw = sender_raw = date_str = reason = None
                target_id = None

                if m:
                    target_raw = m.group("target").strip()
                    sender_raw = m.group("sender").strip()
                    date_str = m.group("date").strip()
                    reason = m.group("reason")
                    if reason:
                        reason = reason.strip()
                    tid = m.group("tid")
                    target_id = int(tid) if tid and tid.isdigit() else None
                else:
                    # tolerant fallback
                    if "bị ghi giấy chê" not in content:
                        continue
                    try:
                        left, _, right = content.partition("bị ghi giấy chê bởi")
                        target_raw = left.strip()
                        if "vào ngày" in right:
                            sender_part, _, after_date = right.partition("vào ngày")
                            sender_raw = sender_part.strip()
                            date_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", after_date)
                            date_str = date_match.group(0) if date_match else ""
                            ridx = after_date.lower().find("lý do:")
                            if ridx != -1:
                                reason = after_date[ridx + len("lý do:") :].strip()
                                id_match = re.search(r"\.\s*ID:\d+:\d+", reason)
                                if id_match:
                                    reason = reason[: id_match.start()].strip()
                            else:
                                reason = None
                            id_search = re.search(
                                r"\.\s*ID:(?P<tid>\d+):(?P<sid>\d+)", content
                            )
                            if id_search:
                                tid = id_search.group("tid")
                                target_id = int(tid) if tid and tid.isdigit() else None
                        else:
                            continue
                    except Exception:
                        continue

                # Resolve names (no tags)
                resolved_target = self._resolve_name(target_raw or "", guild)
                resolved_sender = self._resolve_name(sender_raw or "", guild)

                # Filtering
                if user:
                    matched = False
                    try:
                        uid = int(user)
                        if target_id and uid == target_id:
                            matched = True
                        if (
                            f"<@{uid}>" in content
                            or f"<@!{uid}>" in content
                            or str(uid) in content
                        ):
                            matched = True
                    except Exception:
                        if (
                            user.lower() in (target_raw or "").lower()
                            or user.lower() in content.lower()
                            or user.lower() in resolved_target.lower()
                        ):
                            matched = True
                    if not matched:
                        continue

                display_target = resolved_target
                entries.setdefault(display_target, []).append(
                    (date_str or "", resolved_sender, reason)
                )
        except Exception as e:
            logger.exception(f"Error while scanning giay che logs: {e}")
            await interaction.followup.send("Lỗi khi đọc dữ liệu từ kênh log.")
            return

        if not entries:
            await interaction.followup.send("Không tìm thấy giấy chê cho yêu cầu.")
            return

        # Build embeds for output. If embeds would become too large, attach full report as file.
        embed = discord.Embed(title="Thống kê giấy chê", color=0xE74C3C)
        embed.set_footer(
            text=f"Quét {len(entries)} người, tối đa {MAX_MESSAGES_SCAN} tin nhắn"
        )

        too_long = False
        # For each target add a field with up to first 8 records (full list will be attached if needed)
        for target, recs in sorted(
            entries.items(), key=lambda kv: (-len(kv[1]), kv[0])
        ):
            header = f"{target} ({len(recs)} giấy chê)"
            lines = []
            for idx, (date_str, sender_raw, reason) in enumerate(recs[:8], start=1):
                reason_text = reason if reason and reason.strip() else "Không có"
                lines.append(f"{idx}. {date_str} — {sender_raw}\nLý do: {reason_text}")
            value = "\n\n".join(lines) if lines else "Không có"
            # Discord embed field value length limit is 1024; if any value exceeds, we'll fallback to file
            if len(value) > 1000:
                too_long = True
                break
            embed.add_field(name=header, value=value, inline=False)

        try:
            if not too_long and sum(len(f.value or "") for f in embed.fields) < 6000:
                await interaction.followup.send(embed=embed)
            else:
                # Prepare full text report and attach
                report_lines: list[str] = []
                for target, recs in sorted(
                    entries.items(), key=lambda kv: (-len(kv[1]), kv[0])
                ):
                    report_lines.append(f"{target} ({len(recs)} giấy chê):")
                    for idx, (date_str, sender_raw, reason) in enumerate(recs, start=1):
                        reason_text = (
                            reason if reason and reason.strip() else "Không có"
                        )
                        report_lines.append(
                            f" {idx}. Ngày: {date_str} — Người ghi: {sender_raw}"
                        )
                        report_lines.append(f"     Lý do: {reason_text}")
                    report_lines.append("")
                report = "\n".join(report_lines).strip()
                bio = io.BytesIO(report.encode("utf-8"))
                bio.seek(0)
                file = discord.File(bio, filename="thongke_giayche.txt")
                compact = discord.Embed(
                    title="Thống kê giấy chê (tệp đính kèm)", color=0xE74C3C
                )
                compact.set_footer(
                    text=f"Quét {len(entries)} người, tối đa {MAX_MESSAGES_SCAN} tin nhắn"
                )
                # add small summary: top 3 most-chê people
                top_summary = []
                for target, recs in sorted(
                    entries.items(), key=lambda kv: (-len(kv[1]), kv[0])
                )[:3]:
                    top_summary.append(f"{target}: {len(recs)}")
                compact.add_field(
                    name="Top 3",
                    value="\n".join(top_summary) or "Không có",
                    inline=False,
                )
                await interaction.followup.send(embed=compact, file=file)
        except Exception as e:
            logger.exception(f"Failed to send giay che statistics: {e}")
            await interaction.followup.send(
                "Không thể gửi thống kê giấy chê do lỗi nội bộ."
            )


async def setup(bot):
    await bot.add_cog(ThongKeGiayChe(bot))
