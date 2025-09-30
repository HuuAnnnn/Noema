import discord
from discord.ext import commands
import logging
import asyncio
import time

logger = logging.getLogger(__name__)


class VoiceEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}  # Track user cooldowns to prevent spam
        self.creating_for_users = set()  # Track users currently having channels created
        self.user_locks = {}  # Per-user locks để cho phép nhiều user tạo cùng lúc
        self.channels_being_created = (
            {}
        )  # Track channels being created: {user_id: creation_time}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # User joins a voice channel
        if before.channel is None and after.channel is not None:
            # Kiểm tra xem user đã đang trong quá trình tạo channel chưa
            if member.id in self.creating_for_users:
                logger.info(
                    f"User {member.name} is already creating channels, ignoring"
                )
                return

            # Anti-spam: Check cooldown
            current_time = time.time()
            if member.id in self.user_cooldowns:
                if (
                    current_time - self.user_cooldowns[member.id] < 2
                ):  # 2 second cooldown
                    logger.info(f"User {member.name} is on cooldown, ignoring join")
                    return

            logger.info(
                f"User {member.name} ({member.id}) joined voice channel {after.channel.name} ({after.channel.id})"
            )

            # Check if guild has community channels configured
            if (
                not hasattr(self.bot, "community_channels")
                or member.guild.id not in self.bot.community_channels
            ):
                return

            community_channels = self.bot.community_channels[member.guild.id]
            if not community_channels or after.channel.id not in [
                channel.id for channel in community_channels
            ]:
                return

            logger.info(
                f"User {member.name} joined community channel {after.channel.name}"
            )

            # Tạo per-user lock nếu chưa có
            if member.id not in self.user_locks:
                self.user_locks[member.id] = asyncio.Lock()

            # Sử dụng per-user lock để cho phép nhiều user tạo cùng lúc
            async with self.user_locks[member.id]:
                # Double-check để tránh race condition
                if member.id in self.creating_for_users:
                    return

                self.creating_for_users.add(member.id)
                self.user_cooldowns[member.id] = current_time

                try:
                    await self._create_user_room(member, after.channel)
                finally:
                    # Luôn remove khỏi creating_for_users
                    self.creating_for_users.discard(member.id)

        # User leaves a voice channel
        elif before.channel is not None and after.channel is None:
            # Chỉ xử lý nếu là auto-created channels (có trong pairs)
            if (
                len(before.channel.members) == 0
                and before.channel.id in self.bot.channel_pairs
            ):
                logger.info(
                    f"Auto-created channel {before.channel.name} is empty, scheduling deletion"
                )
                # Sử dụng asyncio.create_task để không block event handler
                asyncio.create_task(
                    self._cleanup_empty_room(before.channel, member.guild)
                )

    async def _create_user_room(self, member, community_channel):
        """Tạo room riêng cho user một cách tối ưu"""
        category = community_channel.category

        # Kiểm tra toàn diện để tránh duplicate:
        # 1. Channels có tên giống user
        # 2. Channels đã được track trong pairs
        # 3. Channels còn tồn tại và không rỗng
        existing_voice_channels = []

        for ch in member.guild.channels:
            if (
                isinstance(ch, discord.VoiceChannel)
                and ch.name == member.display_name
                and (ch.id in self.bot.channel_pairs or ch.category == category)
            ):
                existing_voice_channels.append(ch)

        # Lọc channels còn hoạt động
        active_voice_channels = []
        for ch in existing_voice_channels:
            try:
                # Refresh channel info
                updated_ch = member.guild.get_channel(ch.id)
                if updated_ch and isinstance(updated_ch, discord.VoiceChannel):
                    active_voice_channels.append(updated_ch)
            except:
                continue

        if active_voice_channels:
            # Ưu tiên channel có user ít nhất hoặc rỗng
            target_channel = min(active_voice_channels, key=lambda ch: len(ch.members))
            logger.info(
                f"User {member.display_name} already has personal rooms, moving to existing: {target_channel.name}"
            )
            try:
                await member.move_to(target_channel)
                logger.info(f"Moved {member.name} to existing personal room")
                return
            except Exception as e:
                logger.warning(f"Failed to move {member.name} to existing room: {e}")
                # Nếu không move được, vẫn tiếp tục tạo room mới

        # Kiểm tra thêm: có ai đang tạo room cùng tên không?
        potential_duplicates = [
            ch
            for ch in member.guild.channels
            if ch.name == member.display_name and ch.category == category
        ]

        if potential_duplicates:
            logger.info(
                f"Found potential duplicate channels for {member.display_name}, attempting to use existing"
            )
            voice_ch = next(
                (
                    ch
                    for ch in potential_duplicates
                    if isinstance(ch, discord.VoiceChannel)
                ),
                None,
            )
            if voice_ch:
                try:
                    await member.move_to(voice_ch)
                    # Thêm vào pairs nếu chưa có
                    text_ch = next(
                        (
                            ch
                            for ch in potential_duplicates
                            if isinstance(ch, discord.TextChannel)
                        ),
                        None,
                    )
                    if text_ch and voice_ch.id not in self.bot.channel_pairs:
                        self.bot.channel_pairs[voice_ch.id] = text_ch.id
                        self.bot.channel_pairs[text_ch.id] = voice_ch.id
                    logger.info(
                        f"Successfully used existing room for {member.display_name}"
                    )
                    return
                except Exception as e:
                    logger.warning(f"Failed to use existing room: {e}")
                    # Tiếp tục tạo mới nếu không dùng được existing

        # Final check: Ai đó đang tạo channels cho user này không?
        current_time = time.time()
        if member.id in self.channels_being_created:
            time_diff = current_time - self.channels_being_created[member.id]
            if time_diff < 10:  # Trong vòng 10 giây
                logger.info(
                    f"Channels for {member.display_name} are already being created, skipping"
                )
                return
            else:
                # Quá 10 giây rồi, có thể là stuck, remove và tiếp tục
                del self.channels_being_created[member.id]

        # Mark rằng đang tạo channels cho user này
        self.channels_being_created[member.id] = current_time

        try:
            # Tạo cả 2 channels cùng lúc để giảm thời gian chờ
            voice_task = member.guild.create_voice_channel(
                name=f"{member.display_name}", category=category
            )

            text_task = member.guild.create_text_channel(
                name=f"{member.display_name}", category=category
            )

            # Chạy song song để giảm thời gian
            voice_channel, text_channel = await asyncio.gather(voice_task, text_task)

            logger.info(
                f"Created channels for {member.display_name}: Voice={voice_channel.id}, Text={text_channel.id}"
            )

            # Chỉ sửa position nếu cần thiết
            if text_channel.position != voice_channel.position + 1:
                try:
                    await text_channel.edit(position=voice_channel.position + 1)
                except discord.HTTPException:
                    pass  # Ignore position errors to avoid blocking

            # Move user trước khi store channel pairs
            move_success = False
            try:
                await asyncio.wait_for(member.move_to(voice_channel), timeout=5.0)
                logger.info(f"Successfully moved {member.name} to personal room")
                move_success = True
            except (discord.HTTPException, asyncio.TimeoutError) as e:
                logger.error(f"Failed to move {member.name} to voice channel: {str(e)}")
                move_success = False

            # Nếu move thành công thì store channel pairs, nếu không thì xóa channels
            if move_success:
                # Store channel pairs
                self.bot.channel_pairs[voice_channel.id] = text_channel.id
                self.bot.channel_pairs[text_channel.id] = voice_channel.id
                logger.info(
                    f"Successfully created and set up room for {member.display_name}"
                )
            else:
                # Xóa cả 2 channels vì không move được user
                logger.warning(
                    f"Cannot move user to voice channel, cleaning up created channels for {member.display_name}"
                )
                try:
                    # Xóa cả 2 channels song song
                    await asyncio.gather(
                        voice_channel.delete(),
                        text_channel.delete(),
                        return_exceptions=True,
                    )
                    logger.info(f"Cleaned up unused channels for {member.display_name}")
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up channels: {str(cleanup_error)}")

        except discord.Forbidden:
            logger.error(
                f"Permission denied to create channels for {member.display_name}"
            )
        except Exception as e:
            logger.error(f"Error creating channels for {member.display_name}: {str(e)}")
        finally:
            # Luôn cleanup channels_being_created
            if member.id in self.channels_being_created:
                del self.channels_being_created[member.id]

    async def _cleanup_empty_room(self, voice_channel, guild):
        """Xóa room rỗng một cách tối ưu (chạy trong background)"""
        try:
            # Đợi 2 giây để đảm bảo user thật sự đã rời
            await asyncio.sleep(2)

            # Kiểm tra lại xem channel có thật sự rỗng không
            updated_channel = guild.get_channel(voice_channel.id)
            if not updated_channel or len(updated_channel.members) > 0:
                logger.info(
                    f"Channel {voice_channel.name} is no longer empty, skipping deletion"
                )
                return

            # Lấy paired text channel
            text_channel_id = self.bot.channel_pairs.get(voice_channel.id)
            text_channel = (
                guild.get_channel(text_channel_id) if text_channel_id else None
            )

            # Xóa cả 2 channels song song
            delete_tasks = []
            if updated_channel:
                delete_tasks.append(updated_channel.delete())
            if text_channel:
                delete_tasks.append(text_channel.delete())

            if delete_tasks:
                await asyncio.gather(*delete_tasks, return_exceptions=True)
                logger.info(f"Deleted auto-created room: {voice_channel.name}")

            # Dọn dẹp channel pairs
            if voice_channel.id in self.bot.channel_pairs:
                del self.bot.channel_pairs[voice_channel.id]
            if text_channel_id and text_channel_id in self.bot.channel_pairs:
                del self.bot.channel_pairs[text_channel_id]

        except discord.Forbidden:
            logger.error(
                f"Permission denied to delete channels for {voice_channel.name}"
            )
        except Exception as e:
            logger.error(f"Error deleting channels for {voice_channel.name}: {str(e)}")

    async def cleanup_cooldowns(self):
        """Dọn dẹp các cooldowns và locks cũ (chạy định kỳ)"""
        current_time = time.time()
        expired_users = [
            user_id
            for user_id, timestamp in self.user_cooldowns.items()
            if current_time - timestamp > 60
        ]  # Xóa sau 60s

        # Cleanup expired channels_being_created (over 30 seconds old)
        expired_creating = [
            user_id
            for user_id, timestamp in self.channels_being_created.items()
            if current_time - timestamp > 30
        ]

        for user_id in expired_users:
            if user_id in self.user_cooldowns:
                del self.user_cooldowns[user_id]
            if user_id in self.user_locks:
                del self.user_locks[user_id]

        for user_id in expired_creating:
            if user_id in self.channels_being_created:
                del self.channels_being_created[user_id]

        total_cleaned = len(expired_users) + len(expired_creating)
        if total_cleaned > 0:
            logger.info(
                f"Cleaned up {len(expired_users)} expired cooldowns/locks and {len(expired_creating)} stuck creations"
            )


async def setup(bot):
    await bot.add_cog(VoiceEvents(bot))
