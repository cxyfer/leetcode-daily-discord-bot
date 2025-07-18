# cogs/slash_commands_cog.py
import discord
from discord import app_commands
from discord.ext import commands
import pytz # For timezone validation in set_timezone
import os   # For os.getenv to get default POST_TIME and TIMEZONE
import re   # For date format validation
import time  # For caching submissions with timestamp
from datetime import datetime, timezone

# Import UI helpers
from utils.ui_helpers import (
    create_problems_overview_embed,
    create_problems_overview_view,
    create_submission_embed,
    create_submission_view,
    create_settings_embed
)

# Default values, similar to how they are defined in bot.py or schedule_manager_cog.py
# These are used for display in show_settings if a server doesn't have specific settings.
DEFAULT_POST_TIME = os.getenv('POST_TIME', '00:00')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'UTC')

class SlashCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger

    @app_commands.command(name="daily", description="取得 LeetCode 每日挑戰 (LCUS)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)"
    )
    async def daily_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        """
        Get LeetCode daily challenge (LCUS)
        
        Args:
            interaction: Discord interaction object
            date: Optional date string in YYYY-MM-DD format. If None, returns today's challenge.
        """
        schedule_cog = self.bot.get_cog("ScheduleManagerCog")
        if not schedule_cog:
            await interaction.response.send_message("排程模組目前無法使用，請稍後再試。", ephemeral=True)
            self.logger.error("ScheduleManagerCog not found when trying to execute /daily command.")
            return
        
        await interaction.response.defer(ephemeral=not public) # Defer as it involves API calls
        
        if date:
            # Validate date format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
                await interaction.followup.send("日期格式錯誤，請使用 YYYY-MM-DD 格式（例如：2025-07-01）", ephemeral=not public)
                return
            
            try:
                current_client = self.bot.lcus  # Use LCUS for historical daily challenges
                challenge_info = await current_client.get_daily_challenge(date_str=date)
                
                if not challenge_info:
                    await interaction.followup.send(f"找不到 {date} 的每日挑戰資料。", ephemeral=not public)
                    return
                
                embed = await schedule_cog.create_problem_embed(challenge_info, "com", is_daily=True, date_str=date)
                view = await schedule_cog.create_problem_view(challenge_info, "com")
                
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent daily challenge for {date} to user {interaction.user.name}")
                
            except ValueError as e:
                await interaction.followup.send(f"日期錯誤：{e}", ephemeral=not public)
            except Exception as e:
                self.logger.error(f"Error in daily_command with date {date}: {e}", exc_info=True)
                await interaction.followup.send(f"查詢每日挑戰時發生錯誤：{e}", ephemeral=not public)
        else:
            await schedule_cog.send_daily_challenge(interaction=interaction, domain="com", ephemeral=not public)

    @app_commands.command(name="daily_cn", description="取得 LeetCode 每日挑戰 (LCCN)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)"
    )
    async def daily_cn_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        """Get LeetCode daily challenge (LCCN)"""
        schedule_cog = self.bot.get_cog("ScheduleManagerCog")
        if not schedule_cog:
            await interaction.response.send_message("排程模組目前無法使用，請稍後再試。", ephemeral=True)
            self.logger.error("ScheduleManagerCog not found when trying to execute /daily_cn command.")
            return

        await interaction.response.defer(ephemeral=not public) # Defer as it involves API calls
        
        if date:
            # Validate date format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
                await interaction.followup.send("日期格式錯誤，請使用 YYYY-MM-DD 格式（例如：2024-01-15）", ephemeral=not public)
                return
            
            try:
                current_client = self.bot.lccn  # Use LCCN for historical daily challenges
                challenge_info = await current_client.get_daily_challenge(date_str=date)
                
                if not challenge_info:
                    await interaction.followup.send(f"找不到 {date} 的每日挑戰資料。", ephemeral=not public)
                    return
                
                embed = await schedule_cog.create_problem_embed(challenge_info, "cn", is_daily=True, date_str=date)
                view = await schedule_cog.create_problem_view(challenge_info, "cn")
                
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent daily challenge for {date} (CN) to user {interaction.user.name}")
                
            except ValueError as e:
                await interaction.followup.send(f"日期錯誤：{e}", ephemeral=not public)
            except Exception as e:
                self.logger.error(f"Error in daily_cn_command with date {date}: {e}", exc_info=True)
                await interaction.followup.send(f"查詢每日挑戰時發生錯誤：{e}", ephemeral=not public)
        else:
            await schedule_cog.send_daily_challenge(interaction=interaction, domain="cn", ephemeral=not public)

    @app_commands.command(name="problem", description="根據題號查詢 LeetCode 題目資訊")
    @app_commands.describe(
        problem_ids="題目編號 (1-3500+)，可用逗號分隔多個 (例如: 1,2,3)",
        domain="選擇 LeetCode 網域",
        public="是否公開顯示回覆 (預設為私密回覆)",
        title="自定義標題 (多題模式下替換預設標題，最多 100 個字元)",
        message="可選的個人訊息或備註 (最多 500 個字元)"
    )
    async def problem_command(self, interaction: discord.Interaction, problem_ids: str, domain: str = "com", public: bool = False, message: str = None, title: str = None):
        """
        Get LeetCode problem information by problem IDs
        
        Args:
            interaction: Discord interaction object
            problem_ids: LeetCode problem IDs (comma-separated string)
            domain: LeetCode domain ('com' or 'cn'), defaults to 'com'
            public: Whether to show reply publicly (defaults to private)
            message: Optional user message or note (max 500 characters)
            title: Custom title for multi-problem mode (max 100 characters)
        """
        if domain not in ["com", "cn"]:
            await interaction.response.send_message("網域參數只能是 'com' 或 'cn'", ephemeral=not public)
            return

        # Validate title length if provided
        if title and len(title) > 100:
            await interaction.response.send_message("自定義標題不能超過 100 個字元", ephemeral=not public)
            return

        # Validate message length if provided
        if message and len(message) > 500:
            await interaction.response.send_message("個人訊息不能超過 500 個字元", ephemeral=not public)
            return
        
        # Parse and validate problem IDs
        try:
            id_strings = [id_str.strip() for id_str in problem_ids.split(',')]
            problem_id_list = []
            
            for id_str in id_strings:
                if not id_str.isdigit():
                    await interaction.response.send_message(f"題目編號 '{id_str}' 不是有效的數字", ephemeral=not public)
                    return
                
                problem_id = int(id_str)
                if problem_id < 1:
                    await interaction.response.send_message(f"題目編號 {problem_id} 必須是正整數", ephemeral=not public)
                    return
                
                problem_id_list.append(problem_id)
                
            # Limit number of problems to prevent abuse
            if len(problem_id_list) > 20:
                await interaction.response.send_message("一次最多只能查詢 20 個題目", ephemeral=not public)
                return
                
        except ValueError:
            await interaction.response.send_message("題目編號格式錯誤，請輸入有效的數字（例如：1,2,3）", ephemeral=not public)
            return
        
        schedule_cog = self.bot.get_cog("ScheduleManagerCog")
        if not schedule_cog:
            await interaction.response.send_message("排程模組目前無法使用，請稍後再試。", ephemeral=not public)
            self.logger.error("ScheduleManagerCog not found when trying to execute /problem command.")
            return

        await interaction.response.defer(ephemeral=not public)
        
        try:
            current_client = self.bot.lcus if domain == "com" else self.bot.lccn
            
            # Fetch all problems
            problems = []
            for problem_id in problem_id_list:
                problem_info = await current_client.get_problem(problem_id=str(problem_id))
                if problem_info:
                    problems.append(problem_info)
                else:
                    self.logger.warning(f"Problem {problem_id} not found")
            
            if not problems:
                await interaction.followup.send("找不到任何有效的題目，請確認題目編號是否正確或是否為公開題目。", ephemeral=not public)
                return
            
            # If only one problem, display normally without overview
            if len(problems) == 1:
                embed = await schedule_cog.create_problem_embed(problems[0], domain, is_daily=False, user=interaction.user, title=title, message=message)
                view = await schedule_cog.create_problem_view(problems[0], domain)
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent single problem {problems[0]['id']} info to user {interaction.user.name}")
                return
            
            # Multiple problems - show overview with detail buttons
            embed = create_problems_overview_embed(problems, domain, interaction.user, message, title)
            view = create_problems_overview_view(problems, domain)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info(f"Sent {len(problems)} problems overview to user {interaction.user.name}")
            
        except Exception as e:
            self.logger.error(f"Error in problem_command: {e}", exc_info=True)
            await interaction.followup.send(f"查詢題目時發生錯誤：{e}", ephemeral=not public)

    @problem_command.autocomplete('domain')
    async def problem_domain_autocomplete(self, interaction: discord.Interaction, current: str):
        domains = ["com", "cn"]
        return [app_commands.Choice(name=domain, value=domain) for domain in domains if current.lower() in domain.lower()]

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
        
        embed = create_settings_embed(interaction.guild.name, channel_mention, role_mention, post_time, timezone)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="recent", description="查看 LeetCode 使用者的近期解題紀錄 (僅限 LCUS)")
    @app_commands.describe(
        username="LeetCode 使用者名稱",
        limit="顯示的題目數量 (預設 20，最多 50)",
        public="是否公開顯示回覆 (預設為私密回覆)"
    )
    async def recent_command(self, interaction: discord.Interaction, username: str, limit: int = 20, public: bool = False):
        """
        View recent accepted submissions for a LeetCode user (LCUS only)
        
        Args:
            interaction: Discord interaction object
            username: LeetCode username
            limit: Number of submissions to show (default 20, max 50)
        """
        # Validate limit
        if limit < 1:
            await interaction.response.send_message("顯示數量必須至少為 1", ephemeral=not public)
            return
        if limit > 50:
            limit = 50
            
        await interaction.response.defer(ephemeral=not public)
        
        try:
            # Fetch user submissions
            submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, limit)
            
            if not submissions:
                await interaction.followup.send(f"找不到使用者 **{username}** 的解題紀錄，請確認使用者名稱是否正確。", ephemeral=not public)
                return
            
            # Create initial embed for the first submission
            current_page = 0
            
            # Get detailed info for the first submission
            first_submission = await self._get_submission_details(submissions[current_page])
            if not first_submission:
                await interaction.followup.send("無法載入題目詳細資訊", ephemeral=not public)
                return
                
            embed = create_submission_embed(first_submission, current_page, len(submissions), username)
            view = create_submission_view(first_submission, self.bot, current_page, username, len(submissions))
            
            # Cache submissions in interaction handler for navigation
            interaction_cog = self.bot.get_cog("InteractionHandlerCog")
            if interaction_cog:
                cache_key = f"{username}_{interaction.user.id}"
                interaction_cog.submissions_cache[cache_key] = (submissions, time.time(), limit)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info(f"Sent user submissions for {username} to {interaction.user.name}")
            
        except Exception as e:
            self.logger.error(f"Error in recent_command: {e}", exc_info=True)
            await interaction.followup.send(f"查詢解題紀錄時發生錯誤：{e}", ephemeral=not public)
    
    async def _get_submission_details(self, basic_submission: dict) -> dict:
        """Get detailed problem information for a submission"""
        try:
            problem = await self.bot.lcus.get_problem(slug=basic_submission['slug'])
            if problem:
                return {
                    'id': problem['id'],
                    'title': problem['title'],
                    'slug': basic_submission['slug'],
                    'link': problem['link'],
                    'difficulty': problem['difficulty'],
                    'rating': problem.get('rating', 0),
                    'tags': problem.get('tags', []),
                    'ac_rate': problem.get('ac_rate', 0),
                    'submission_time': basic_submission['submission_time'],
                    'submission_id': basic_submission['submission_id']
                }
        except Exception as e:
            self.logger.error(f"Error getting submission details: {e}", exc_info=True)
        return None
    
    # Function removed - now using utils.ui_helpers.create_submission_embed
    
    # Function removed - now using utils.ui_helpers.create_submission_view

    # Function removed - now using utils.ui_helpers.create_problems_overview_embed

    # Function removed - now using utils.ui_helpers.create_problems_overview_view

    # Function removed - now using utils.ui_helpers.get_user_color

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