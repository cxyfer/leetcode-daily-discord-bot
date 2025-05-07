# cogs/slash_commands_cog.py
import discord
from discord import app_commands
from discord.ext import commands
import pytz # For timezone validation in set_timezone
import os   # For os.getenv to get default POST_TIME and TIMEZONE

# Default values, similar to how they are defined in bot.py or schedule_manager_cog.py
# These are used for display in show_settings if a server doesn't have specific settings.
DEFAULT_POST_TIME = os.getenv('POST_TIME', '00:00')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'UTC')

class SlashCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger

    @app_commands.command(name="daily", description="取得今天的 LeetCode 每日挑戰 (LCUS)")
    async def daily_command(self, interaction: discord.Interaction):
        """Get today's LeetCode daily challenge (LCUS)"""
        schedule_cog = self.bot.get_cog("ScheduleManagerCog")
        if not schedule_cog:
            await interaction.response.send_message("排程模組目前無法使用，請稍後再試。", ephemeral=True)
            self.logger.error("ScheduleManagerCog not found when trying to execute /daily command.")
            return
        
        await interaction.response.defer(ephemeral=True) # Defer as it involves API calls
        await schedule_cog.send_daily_challenge(interaction=interaction, domain="com")

    @app_commands.command(name="daily_cn", description="取得今天的 LeetCode 每日挑戰 (LCCN)")
    async def daily_cn_command(self, interaction: discord.Interaction):
        """Get today's LeetCode daily challenge (LCCN)"""
        schedule_cog = self.bot.get_cog("ScheduleManagerCog")
        if not schedule_cog:
            await interaction.response.send_message("排程模組目前無法使用，請稍後再試。", ephemeral=True)
            self.logger.error("ScheduleManagerCog not found when trying to execute /daily_cn command.")
            return

        await interaction.response.defer(ephemeral=True) # Defer as it involves API calls
        await schedule_cog.send_daily_challenge(interaction=interaction, domain="cn")

    @app_commands.command(name="set_channel", description="設定 LeetCode 每日挑戰的發送頻道")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for sending the daily LeetCode challenge"""
        server_id = interaction.guild.id
        success = self.bot.db.set_channel(server_id, channel.id)
        
        if success:
            await interaction.response.send_message(f"LeetCode 每日挑戰頻道已成功設定為 {channel.mention}", ephemeral=True)
            self.logger.info(f"Server {server_id} channel set to {channel.id} by {interaction.user.name}")
            # Reschedule after successful update
            schedule_cog = self.bot.get_cog("ScheduleManagerCog")
            if schedule_cog:
                await schedule_cog.reschedule_daily_challenge(server_id)
            else:
                self.logger.warning(f"ScheduleManagerCog not found during set_channel for server {server_id}. Scheduling may not update immediately.")
        else:
            # This case might happen if set_channel itself has internal logic that can fail,
            # or if the initial set_server_settings within set_channel (for a new server) fails.
            await interaction.response.send_message("設定頻道時發生錯誤，請稍後再試。", ephemeral=True)
            self.logger.error(f"Failed to set channel for server {server_id} to {channel.id} by {interaction.user.name}")

    @set_channel_command.error
    async def set_channel_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能設定頻道。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in set_channel_command: {error}", exc_info=True)
            await interaction.response.send_message(f"設定頻道時發生錯誤: {error}", ephemeral=True)

    @app_commands.command(name="set_role", description="設定 LeetCode 每日挑戰要標記的身分組")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_role_command(self, interaction: discord.Interaction, role: discord.Role):
        """Set the role to mention for the daily LeetCode challenge"""
        server_id = interaction.guild.id
        # Check if channel is set first, as role is usually set after channel
        settings = self.bot.db.get_server_settings(server_id)
        if not settings or not settings.get("channel_id"):
            await interaction.response.send_message("請先使用 `/set_channel` 設定每日挑戰的發送頻道。", ephemeral=True)
            return

        success = self.bot.db.set_role(server_id, role.id)

        if success:
            await interaction.response.send_message(f"LeetCode 每日挑戰將成功標記 {role.mention}", ephemeral=True)
            self.logger.info(f"Server {server_id} role set to {role.id} by {interaction.user.name}")
            # Reschedule, as role change might affect notifications if the bot logic uses it before sending.
            schedule_cog = self.bot.get_cog("ScheduleManagerCog")
            if schedule_cog:
                await schedule_cog.reschedule_daily_challenge(server_id)
            else:
                self.logger.warning(f"ScheduleManagerCog not found during set_role for server {server_id}. Scheduling may not update immediately.")
        else:
            # This typically means the channel wasn't set first, which is handled by the check at lines 77-79.
            # However, if set_role itself had an internal failure, this would catch it.
            await interaction.response.send_message("設定標記身分組時發生錯誤，請確認頻道是否已設定，或稍後再試。", ephemeral=True)
            self.logger.error(f"Failed to set role for server {server_id} to {role.id} by {interaction.user.name}")

    @set_role_command.error
    async def set_role_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能設定身分組。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in set_role_command: {error}", exc_info=True)
            await interaction.response.send_message(f"設定身分組時發生錯誤: {error}", ephemeral=True)

    @app_commands.command(name="set_post_time", description="設定 LeetCode 每日挑戰的發送時間 (HH:MM)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_post_time_command(self, interaction: discord.Interaction, time: str):
        """Set the time for sending the daily LeetCode challenge"""
        server_id = interaction.guild.id
        try:
            hour, minute = map(int, time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time format")
        except ValueError:
            await interaction.response.send_message("時間格式錯誤，請使用 HH:MM 格式 (例如 08:00 或 23:59)。", ephemeral=True)
            return

        settings = self.bot.db.get_server_settings(server_id)
        if not settings or not settings.get("channel_id"):
            await interaction.response.send_message("請先使用 `/set_channel` 設定每日挑戰的發送頻道。", ephemeral=True)
            return
        
        success = self.bot.db.set_post_time(server_id, time)
        
        if success:
            await interaction.response.send_message(f"每日挑戰發送時間已成功設定為 {time}", ephemeral=True)
            self.logger.info(f"Server {server_id} post time set to {time} by {interaction.user.name}")
            # Reschedule after successful update
            schedule_cog = self.bot.get_cog("ScheduleManagerCog")
            if schedule_cog:
                await schedule_cog.reschedule_daily_challenge(server_id)
        else:
            await interaction.response.send_message("設定發送時間時發生錯誤，請確認伺服器是否已設定發送頻道，或稍後再試。", ephemeral=True)
            self.logger.error(f"Failed to set post time for server {server_id} by {interaction.user.name}")

    @set_post_time_command.error
    async def set_post_time_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能設定發送時間。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in set_post_time_command: {error}", exc_info=True)
            await interaction.response.send_message(f"設定發送時間時發生錯誤: {error}", ephemeral=True)

    @app_commands.command(name="set_timezone", description="設定 LeetCode 每日挑戰的發送時區")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_timezone_command(self, interaction: discord.Interaction, timezone: str):
        """Set the timezone for sending the daily LeetCode challenge"""
        server_id = interaction.guild.id
        try:
            pytz.timezone(timezone) # Validate timezone
        except pytz.exceptions.UnknownTimeZoneError:
            await interaction.response.send_message("無效的時區，請輸入有效的時區名稱 (例如 Asia/Taipei 或 UTC)。", ephemeral=True)
            return

        settings = self.bot.db.get_server_settings(server_id)
        if not settings or not settings.get("channel_id"):
            await interaction.response.send_message("請先使用 `/set_channel` 設定每日挑戰的發送頻道。", ephemeral=True)
            return

        success = self.bot.db.set_timezone(server_id, timezone)
        
        if success:
            await interaction.response.send_message(f"每日挑戰發送時區已成功設定為 {timezone}", ephemeral=True)
            self.logger.info(f"Server {server_id} timezone set to {timezone} by {interaction.user.name}")
            # Reschedule after successful update
            schedule_cog = self.bot.get_cog("ScheduleManagerCog")
            if schedule_cog:
                await schedule_cog.reschedule_daily_challenge(server_id)
        else:
            await interaction.response.send_message("設定時區時發生錯誤，請確認伺服器是否已設定發送頻道，或稍後再試。", ephemeral=True)
            self.logger.error(f"Failed to set timezone for server {server_id} by {interaction.user.name}")

    @set_timezone_command.error
    async def set_timezone_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能設定時區。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in set_timezone_command: {error}", exc_info=True)
            await interaction.response.send_message(f"設定時區時發生錯誤: {error}", ephemeral=True)

    @app_commands.command(name="show_settings", description="顯示目前伺服器的 LeetCode 挑戰設定")
    @app_commands.guild_only()
    async def show_settings_command(self, interaction: discord.Interaction):
        """Show the current LeetCode challenge settings for the server"""
        server_id = interaction.guild.id
        settings = self.bot.db.get_server_settings(server_id)
        
        if not settings or not settings.get("channel_id"):
            await interaction.response.send_message("尚未設定 LeetCode 每日挑戰頻道。使用 `/set_channel` 開始設定。", ephemeral=True)
            return

        channel_id = settings.get("channel_id")
        channel = self.bot.get_channel(int(channel_id)) if channel_id else None
        channel_mention = channel.mention if channel else f"未知頻道 (ID: {channel_id})"
        
        role_id = settings.get("role_id")
        role_mention = "未設定"
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            role_mention = role.mention if role else f"未知身分組 (ID: {role_id})"
            
        post_time = settings.get("post_time", DEFAULT_POST_TIME)
        timezone = settings.get("timezone", DEFAULT_TIMEZONE)
        
        embed = discord.Embed(title=f"{interaction.guild.name} 的 LeetCode 挑戰設定", color=0x0099FF)
        embed.add_field(name="發送頻道", value=channel_mention, inline=False)
        embed.add_field(name="標記身分組", value=role_mention, inline=False)
        embed.add_field(name="發送時間", value=f"{post_time} ({timezone})", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove_channel", description="移除頻道設定，停止在此伺服器發送 LeetCode 每日挑戰")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_channel_command(self, interaction: discord.Interaction):
        """Remove the channel setting and stop sending daily challenges on this server"""
        server_id = interaction.guild.id
        
        current_settings = self.bot.db.get_server_settings(server_id)
        if not current_settings or not current_settings.get("channel_id"):
            await interaction.response.send_message("此伺服器尚未設定每日挑戰頻道，無需移除。", ephemeral=True)
            return

        # Remove all settings for the server
        success = self.bot.db.delete_server_settings(server_id)
        
        if success:
            self.logger.info(f"Server {server_id} settings removed by {interaction.user.name}")
            # Attempt to cancel the scheduled task for this server
            schedule_cog = self.bot.get_cog("ScheduleManagerCog")
            if schedule_cog:
                # Rescheduling with no channel_id in DB (because it's deleted)
                # or explicitly cancelling the task if reschedule_daily_challenge handles it.
                # For now, reschedule_daily_challenge should handle the case where settings are gone.
                await schedule_cog.reschedule_daily_challenge(server_id)
            else:
                self.logger.warning(f"ScheduleManagerCog not found during remove_channel for server {server_id}. Scheduling may not stop immediately if it was running.")
            
            await interaction.response.send_message("已成功移除此伺服器的每日挑戰所有設定，將不再發送。", ephemeral=True)
        else:
            self.logger.error(f"Failed to remove server {server_id} settings by {interaction.user.name}")
            await interaction.response.send_message("移除頻道設定時發生錯誤，請稍後再試。", ephemeral=True)

    @remove_channel_command.error
    async def remove_channel_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能移除頻道設定。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in remove_channel_command: {error}", exc_info=True)
            await interaction.response.send_message(f"移除頻道設定時發生錯誤: {error}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommandsCog(bot))