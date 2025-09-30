import discord
from discord.ext import commands, tasks
import logging

logger = logging.getLogger(__name__)


class MemberCounter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_update_task.start()  # Bắt đầu task tự động cập nhật

    def cog_unload(self):
        """Dọn dẹp khi cog bị unload"""
        self.auto_update_task.cancel()

    @tasks.loop(minutes=5)  # Chạy mỗi 5 phút
    async def auto_update_task(self):
        """Task tự động cập nhật member counter mỗi 5 phút"""
        try:
            if not hasattr(self.bot, 'member_counter_channels'):
                return
                
            logger.info("Starting auto update for member counters...")
            
            for guild in self.bot.guilds:
                if guild.id in self.bot.member_counter_channels:
                    await self.update_member_count(guild)
                    
            logger.info("Auto update completed for all member counters")
        except Exception as e:
            logger.error(f"Error in auto update task: {str(e)}")

    @auto_update_task.before_loop
    async def before_auto_update_task(self):
        """Đợi bot sẵn sàng trước khi bắt đầu task"""
        await self.bot.wait_until_ready()

    @discord.app_commands.command(
        name="setup_member_counter",
        description="Thiết lập counter thành viên cho hai channel (Founder/Co-founder only)",
    )
    async def setup_member_counter(
        self,
        interaction: discord.Interaction,
        total_members_channel_id: str,
        online_members_channel_id: str,
    ):
        """Thiết lập counter thành viên cho hai channel (Founder/Co-founder only)."""
        try:
            # Defer the response immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)

            logger.info(
                f"Setup member counter command used by {interaction.user.name} ({interaction.user.id}) in {interaction.guild.name}"
            )

            # Check permissions
            founder_roles = ["founder", "co-founder", "admin", "Admin"]
            user_roles = [role.name.lower() for role in interaction.user.roles]

            if not any(role in user_roles for role in founder_roles):
                logger.warning(
                    f"Unauthorized access attempt by {interaction.user.name} ({interaction.user.id}) for setup_member_counter command"
                )
                await interaction.followup.send(
                    "Bạn cần có quyền Founder hoặc Co-founder để sử dụng lệnh này!",
                    ephemeral=True,
                )
                return

            # Validate channel IDs
            try:
                total_channel_id = int(total_members_channel_id)
                online_channel_id = int(online_members_channel_id)
            except ValueError:
                await interaction.followup.send(
                    "ID channel không hợp lệ! Vui lòng nhập số.", ephemeral=True
                )
                return

            # Check if channels exist
            total_channel = interaction.guild.get_channel(total_channel_id)
            online_channel = interaction.guild.get_channel(online_channel_id)

            if not total_channel:
                await interaction.followup.send(
                    f"Không tìm thấy channel với ID: {total_channel_id}", ephemeral=True
                )
                return

            if not online_channel:
                await interaction.followup.send(
                    f"Không tìm thấy channel với ID: {online_channel_id}",
                    ephemeral=True,
                )
                return

            # Store the channel IDs in bot's memory
            if not hasattr(self.bot, "member_counter_channels"):
                self.bot.member_counter_channels = {}

            self.bot.member_counter_channels[interaction.guild.id] = {
                "total_channel_id": total_channel_id,
                "online_channel_id": online_channel_id,
            }

            # Update channel names immediately
            await self.update_member_count(interaction.guild)

            logger.info(
                f"Member counter set up successfully for guild {interaction.guild.name}"
            )

            await interaction.followup.send(
                f"✅ Đã thiết lập thành công!\n"
                f"📊 Channel tổng thành viên: {total_channel.mention}\n"
                f"🟢 Channel thành viên online: {online_channel.mention}\n"
                f"🔄 Tự động cập nhật mỗi 5 phút",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error in setup_member_counter command: {str(e)}")
            try:
                await interaction.followup.send(
                    "Đã xảy ra lỗi khi thiết lập member counter.", ephemeral=True
                )
            except:
                logger.error("Could not send error response for setup_member_counter")

    async def update_member_count(self, guild):
        """Cập nhật số lượng thành viên trong tên channel"""
        try:
            if not hasattr(self.bot, "member_counter_channels"):
                return

            if guild.id not in self.bot.member_counter_channels:
                return

            config = self.bot.member_counter_channels[guild.id]

            # Get channels
            total_channel = guild.get_channel(int(config["total_channel_id"]))
            online_channel = guild.get_channel(int(config["online_channel_id"]))

            if not total_channel or not online_channel:
                logger.warning(
                    f"Could not find channels for member counter in guild {guild.name}"
                )
                return

            # Nếu cached members quá ít, thử fetch thêm
            if len(guild.members) < guild.member_count * 0.5:  # Nếu cache < 50% total
                logger.info(f"Guild {guild.name}: Cached members ({len(guild.members)}) much less than total ({guild.member_count}), attempting to fetch more...")
                try:
                    # Fetch members để update cache (giới hạn 1000 để tránh rate limit)
                    count = 0
                    async for member in guild.fetch_members(limit=1000):
                        count += 1
                    logger.info(f"Fetched {count} members. New cache size: {len(guild.members)}")
                except Exception as e:
                    logger.error(f"Error fetching members: {e}")

            # Count members
            total_members = guild.member_count
            
            # Đếm members online (không bao gồm offline và invisible)
            online_members = 0
            for member in guild.members:
                if member.status not in [discord.Status.offline, discord.Status.invisible]:
                    online_members += 1
            
            logger.info(f"Guild {guild.name}: Total={total_members}, Cached={len(guild.members)}, Online={online_members}")

            # Update channel names
            total_name = f"📊 Tổng: {total_members} thành viên"
            online_name = f"🟢 Online: {online_members} thành viên"

            try:
                if total_channel.name != total_name:
                    await total_channel.edit(name=total_name)
                    logger.info(f"Updated total members channel name to: {total_name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to update total members channel name: {e}")

            try:
                if online_channel.name != online_name:
                    await online_channel.edit(name=online_name)
                    logger.info(
                        f"Updated online members channel name to: {online_name}"
                    )
            except discord.HTTPException as e:
                logger.error(f"Failed to update online members channel name: {e}")

        except Exception as e:
            logger.error(f"Error updating member count: {str(e)}")

    @discord.app_commands.command(
        name="member_counter_status", 
        description="Xem trạng thái auto update member counter"
    )
    async def member_counter_status(self, interaction: discord.Interaction):
        """Xem trạng thái auto update member counter"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Check if guild has member counter setup
            if not hasattr(self.bot, 'member_counter_channels') or interaction.guild.id not in self.bot.member_counter_channels:
                await interaction.followup.send("❌ Member counter chưa được thiết lập cho server này!", ephemeral=True)
                return
            
            config = self.bot.member_counter_channels[interaction.guild.id]
            total_channel = interaction.guild.get_channel(int(config["total_channel_id"]))
            online_channel = interaction.guild.get_channel(int(config["online_channel_id"]))
            
            status_msg = f"**📊 Member Counter Status**\n\n"
            status_msg += f"🔄 **Auto Update:** {'✅ Đang chạy' if not self.auto_update_task.is_running() else '❌ Đã dừng'}\n"
            status_msg += f"⏰ **Cập nhật:** Mỗi 5 phút\n"
            status_msg += f"📊 **Channel tổng:** {total_channel.mention if total_channel else 'Không tìm thấy'}\n"
            status_msg += f"🟢 **Channel online:** {online_channel.mention if online_channel else 'Không tìm thấy'}\n\n"
            
            # Current counts
            total_members = interaction.guild.member_count
            online_members = sum(1 for member in interaction.guild.members 
                               if member.status not in [discord.Status.offline, discord.Status.invisible])
            
            status_msg += f"**📈 Số liệu hiện tại:**\n"
            status_msg += f"• Tổng thành viên: {total_members}\n"
            status_msg += f"• Cached members: {len(interaction.guild.members)}\n"
            status_msg += f"• Online: {online_members}\n"
            
            await interaction.followup.send(status_msg, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in member_counter_status: {str(e)}")
            await interaction.followup.send("Đã xảy ra lỗi khi kiểm tra status.", ephemeral=True)

    @discord.app_commands.command(
        name="force_update_counter", 
        description="Cập nhật ngay lập tức member counter (Admin only)"
    )
    async def force_update_counter(self, interaction: discord.Interaction):
        """Force update member counter ngay lập tức"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Check permissions
            founder_roles = ["founder", "co-founder", "admin", "Admin"]
            user_roles = [role.name.lower() for role in interaction.user.roles]
            
            if not any(role in user_roles for role in founder_roles):
                await interaction.followup.send("Bạn cần có quyền Admin để sử dụng lệnh này!", ephemeral=True)
                return
            
            # Check if setup
            if not hasattr(self.bot, 'member_counter_channels') or interaction.guild.id not in self.bot.member_counter_channels:
                await interaction.followup.send("❌ Member counter chưa được thiết lập!", ephemeral=True)
                return
            
            # Force update
            await self.update_member_count(interaction.guild)
            await interaction.followup.send("✅ Đã cập nhật member counter thành công!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in force_update_counter: {str(e)}")
            await interaction.followup.send("Đã xảy ra lỗi khi cập nhật.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Cập nhật khi có thành viên mới join"""
        await self.update_member_count(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Cập nhật khi có thành viên leave"""
        await self.update_member_count(member.guild)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        """Cập nhật khi trạng thái online/offline thay đổi"""
        if before.status != after.status:
            await self.update_member_count(after.guild)


async def setup(bot):
    await bot.add_cog(MemberCounter(bot))
