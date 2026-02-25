# cogs/slash_commands_cog.py
import re  # For date format validation
import time  # For caching submissions with timestamp

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE, parse_timezone
from utils.logger import get_commands_logger
from utils.source_detector import detect_source
from utils.ui_constants import ATCODER_LOGO_URL, LEETCODE_LOGO_URL

# Import UI helpers
from utils.ui_helpers import (
    create_problem_embed,
    create_problem_view,
    create_problems_overview_embed,
    create_problems_overview_view,
    create_settings_embed,
    create_submission_embed,
    create_submission_view,
    send_daily_challenge,
)


class SlashCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()

    async def _reschedule_if_available(self, server_id: int, context: str = ""):
        await self.bot.reschedule_daily_challenge(server_id, context)

    @app_commands.command(name="daily", description="取得 LeetCode 每日挑戰 (LCUS)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def daily_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        """
        Get LeetCode daily challenge (LCUS)

        Args:
            interaction: Discord interaction object
            date: Optional date string in YYYY-MM-DD format. If None, returns today's challenge.
        """
        await interaction.response.defer(ephemeral=not public)  # Defer as it involves API calls

        if date:
            # Validate date format
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                await interaction.followup.send(
                    "日期格式錯誤，請使用 YYYY-MM-DD 格式（例如：2025-07-01）",
                    ephemeral=not public,
                )
                return

            try:
                current_client = self.bot.lcus  # Use LCUS for historical daily challenges
                challenge_info = await current_client.get_daily_challenge(date_str=date)

                if not challenge_info:
                    await interaction.followup.send(f"找不到 {date} 的每日挑戰資料。", ephemeral=not public)
                    return

                history_problems = await current_client.get_daily_history(date)

                embed = await create_problem_embed(
                    problem_info=challenge_info,
                    bot=self.bot,
                    domain="com",
                    is_daily=True,
                    date_str=date,
                    history_problems=history_problems,
                )
                view = await create_problem_view(problem_info=challenge_info, bot=self.bot, domain="com")

                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent daily challenge for {date} to user {interaction.user.name}")

            except ValueError as e:
                await interaction.followup.send(f"日期錯誤：{e}", ephemeral=not public)
            except Exception as e:
                self.logger.error(f"Error in daily_command with date {date}: {e}", exc_info=True)
                await interaction.followup.send(f"查詢每日挑戰時發生錯誤：{e}", ephemeral=not public)
        else:
            await send_daily_challenge(
                bot=self.bot,
                interaction=interaction,
                domain="com",
                ephemeral=not public,
            )

    @app_commands.command(name="daily_cn", description="取得 LeetCode 每日挑戰 (LCCN)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def daily_cn_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        """Get LeetCode daily challenge (LCCN)"""
        await interaction.response.defer(ephemeral=not public)  # Defer as it involves API calls

        if date:
            # Validate date format
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                await interaction.followup.send(
                    "日期格式錯誤，請使用 YYYY-MM-DD 格式（例如：2024-01-15）",
                    ephemeral=not public,
                )
                return

            try:
                current_client = self.bot.lccn  # Use LCCN for historical daily challenges
                challenge_info = await current_client.get_daily_challenge(date_str=date)

                if not challenge_info:
                    await interaction.followup.send(f"找不到 {date} 的每日挑戰資料。", ephemeral=not public)
                    return

                history_problems = await current_client.get_daily_history(date)

                embed = await create_problem_embed(
                    problem_info=challenge_info,
                    bot=self.bot,
                    domain="cn",
                    is_daily=True,
                    date_str=date,
                    history_problems=history_problems,
                )
                view = await create_problem_view(problem_info=challenge_info, bot=self.bot, domain="cn")

                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent daily challenge for {date} (CN) to user {interaction.user.name}")

            except ValueError as e:
                await interaction.followup.send(f"日期錯誤：{e}", ephemeral=not public)
            except Exception as e:
                self.logger.error(f"Error in daily_cn_command with date {date}: {e}", exc_info=True)
                await interaction.followup.send(f"查詢每日挑戰時發生錯誤：{e}", ephemeral=not public)
        else:
            await send_daily_challenge(
                bot=self.bot,
                interaction=interaction,
                domain="cn",
                ephemeral=not public,
            )

    @app_commands.command(name="problem", description="根據題號查詢 LeetCode 題目資訊")
    @app_commands.describe(
        problem_ids="題目編號，可用逗號分隔 (例如: 1, abc321_a, 2179A, atcoder:abc321_a, codeforces:2179A)",
        domain="選擇 LeetCode 網域（已棄用）",
        public="是否公開顯示回覆 (預設為私密回覆)",
        title="自定義標題 (多題模式下替換預設標題，最多 100 個字元)",
        message="可選的個人訊息或備註 (最多 500 個字元)",
        source="題庫來源 (例如 leetcode/atcoder/codeforces)，也可以在題號前加上 source: 前綴",
    )
    async def problem_command(
        self,
        interaction: discord.Interaction,
        problem_ids: str,
        domain: str = "com",
        public: bool = False,
        message: str = None,
        title: str = None,
        source: str = None,
    ):
        """
        Get LeetCode problem information by problem IDs

        Args:
            interaction: Discord interaction object
            problem_ids: LeetCode problem IDs (comma-separated string)
            domain: LeetCode domain ('com' or 'cn'), defaults to 'com'
            public: Whether to show reply publicly (defaults to private)
            message: Optional user message or note (max 500 characters)
            title: Custom title for multi-problem mode (max 100 characters)
            source: Optional problem source override
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
            id_strings = [id_str.strip() for id_str in problem_ids.split(",")]
            id_strings = [id_str for id_str in id_strings if id_str]
            resolved_problem_ids = []

            for id_str in id_strings:
                detected_source, normalized_id = detect_source(id_str, explicit_source=source)
                if detected_source == "unknown":
                    await interaction.response.send_message(
                        f"無法判斷 '{id_str}' 的來源。請使用 source:id 格式（如 atcoder:abc001_a）、"
                        "題目 URL，或指定 source 參數",
                        ephemeral=not public,
                    )
                    return
                if detected_source == "leetcode" and normalized_id.isdigit():
                    problem_id_value = int(normalized_id)
                    if problem_id_value < 1:
                        await interaction.response.send_message(
                            f"題目編號 {problem_id_value} 必須是正整數",
                            ephemeral=not public,
                        )
                        return
                resolved_problem_ids.append((detected_source, normalized_id))

            # Limit number of problems to prevent abuse
            if len(resolved_problem_ids) > 20:
                await interaction.response.send_message("一次最多只能查詢 20 個題目", ephemeral=not public)
                return

        except ValueError:
            await interaction.response.send_message(
                "題目編號格式錯誤，請輸入有效格式（例如：1,2,3 或 atcoder:abc001_a）",
                ephemeral=not public,
            )
            return

        await interaction.response.defer(ephemeral=not public)

        try:
            current_client = self.bot.lcus if domain == "com" else self.bot.lccn

            # Fetch all problems
            problems = []
            for detected_source, normalized_id in resolved_problem_ids:
                if detected_source == "leetcode":
                    if normalized_id.isdigit():
                        problem_info = await current_client.get_problem(problem_id=normalized_id)
                    else:
                        problem_info = await current_client.get_problem(slug=normalized_id)
                else:
                    problem_info = current_client.problems_db.get_problem(id=normalized_id, source=detected_source)
                if problem_info:
                    problems.append(problem_info)
                else:
                    self.logger.warning(
                        "Problem not found: source=%s id=%s",
                        detected_source,
                        normalized_id,
                    )

            if not problems:
                await interaction.followup.send(
                    "找不到任何有效的題目，請確認題目編號是否正確或是否為公開題目。",
                    ephemeral=not public,
                )
                return

            sources = {problem.get("source", "leetcode") for problem in problems}
            leetcode_only = sources == {"leetcode"}
            atcoder_only = sources == {"atcoder"}

            # If only one problem, display normally without overview
            if len(problems) == 1:
                embed = await create_problem_embed(
                    problem_info=problems[0],
                    bot=self.bot,
                    domain=domain,
                    is_daily=False,
                    user=interaction.user,
                    title=title,
                    message=message,
                )
                view = await create_problem_view(problem_info=problems[0], bot=self.bot, domain=domain)
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                self.logger.info(f"Sent single problem {problems[0]['id']} info to user {interaction.user.name}")
                return

            # Multiple problems - show overview with detail buttons
            if atcoder_only:
                source_label = "AtCoder"
                footer_icon_url = ATCODER_LOGO_URL
            elif leetcode_only:
                source_label = "LeetCode"
                footer_icon_url = LEETCODE_LOGO_URL
            else:
                source_label = "Mixed Sources"
                footer_icon_url = None

            embed = create_problems_overview_embed(
                problems,
                domain,
                interaction.user,
                message,
                title,
                source_label=source_label,
                show_instructions=True,
                footer_icon_url=footer_icon_url,
            )
            view = create_problems_overview_view(problems, domain)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info(f"Sent {len(problems)} problems overview to user {interaction.user.name}")

        except Exception as e:
            self.logger.error(f"Error in problem_command: {e}", exc_info=True)
            await interaction.followup.send(f"查詢題目時發生錯誤：{e}", ephemeral=not public)

    @problem_command.autocomplete("domain")
    async def problem_domain_autocomplete(self, interaction: discord.Interaction, current: str):
        domains = ["com", "cn"]
        return [
            app_commands.Choice(name=domain, value=domain) for domain in domains if current.lower() in domain.lower()
        ]

    # ── Unified /config command ──────────────────────────────────────

    _TZ_CHOICES: list[str] = (
        [f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)]
        + ["UTC+3:30", "UTC+4:30", "UTC+5:30", "UTC+5:45", "UTC+6:30",
           "UTC+8:45", "UTC+9:30", "UTC+10:30", "UTC+12:45"]
        + ["UTC", "Asia/Taipei", "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
           "America/New_York", "America/Los_Angeles", "America/Chicago",
           "Europe/London", "Europe/Berlin"]
    )

    @app_commands.command(name="config", description="設定 LeetCode 每日挑戰的所有配置")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="發送每日挑戰的頻道",
        role="要標記的身分組",
        time="發送時間 (HH:MM 或 H:MM，例如 08:00)",
        timezone="時區 (例如 Asia/Taipei 或 UTC+8)",
        clear_role="清除身分組標記設定",
        reset="重置所有設定並停止排程（需確認）",
    )
    async def config_command(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        role: discord.Role = None,
        time: str = None,
        timezone: str = None,
        clear_role: bool = False,
        reset: bool = False,
    ):
        server_id = interaction.guild.id
        import time as time_mod

        # ── Reset conflict check ──
        if reset and any([channel, role, time is not None, timezone is not None, clear_role]):
            await interaction.response.send_message(
                "`reset` 不可與其他設定參數同時使用。", ephemeral=True
            )
            return

        # ── Show mode (no params) ──
        has_update = any([channel, role, time is not None, timezone is not None, clear_role, reset])
        if not has_update:
            settings = self.bot.db.get_server_settings(server_id)
            if not settings or not settings.get("channel_id"):
                await interaction.response.send_message(
                    "尚未設定 LeetCode 每日挑戰頻道。使用 /config channel:<頻道> 開始設定。",
                    ephemeral=True,
                )
                return
            ch = self.bot.get_channel(settings["channel_id"])
            ch_mention = ch.mention if ch else f"未知頻道 (ID: {settings['channel_id']})"
            role_mention = "未設定"
            if settings.get("role_id"):
                r = interaction.guild.get_role(int(settings["role_id"]))
                role_mention = r.mention if r else f"未知身分組 (ID: {settings['role_id']})"
            post_time = settings.get("post_time", DEFAULT_POST_TIME)
            tz = settings.get("timezone", DEFAULT_TIMEZONE)
            embed = create_settings_embed(interaction.guild.name, ch_mention, role_mention, post_time, tz)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ── Reset mode ──
        if reset:
            settings = self.bot.db.get_server_settings(server_id)
            if not settings:
                await interaction.response.send_message(
                    "此伺服器尚未設定，無需重置。", ephemeral=True
                )
                return
            # Build preview embed
            ch = self.bot.get_channel(settings["channel_id"])
            ch_mention = ch.mention if ch else f"未知頻道 (ID: {settings['channel_id']})"
            role_mention = "未設定"
            if settings.get("role_id"):
                r = interaction.guild.get_role(int(settings["role_id"]))
                role_mention = r.mention if r else f"未知身分組 (ID: {settings['role_id']})"
            post_time = settings.get("post_time", DEFAULT_POST_TIME)
            tz = settings.get("timezone", DEFAULT_TIMEZONE)
            preview_embed = create_settings_embed(interaction.guild.name, ch_mention, role_mention, post_time, tz)

            exp_unix = int(time_mod.time()) + 180
            view = discord.ui.View(timeout=180)
            view.add_item(discord.ui.Button(
                label="確認重置", style=discord.ButtonStyle.danger,
                custom_id=f"config_reset_confirm|{server_id}|{interaction.user.id}|{exp_unix}",
            ))
            view.add_item(discord.ui.Button(
                label="取消", style=discord.ButtonStyle.secondary,
                custom_id=f"config_reset_cancel|{server_id}|{interaction.user.id}|{exp_unix}",
            ))
            await interaction.response.send_message(
                content="⚠️ 確定要重置此伺服器的所有設定嗎？這將停止每日挑戰排程。",
                embed=preview_embed, view=view, ephemeral=True,
            )
            return

        # Mutual exclusion: role + clear_role
        if role and clear_role:
            await interaction.response.send_message(
                "`role` 與 `clear_role` 不可同時使用。", ephemeral=True
            )
            return

        # Validate time format
        validated_time = None
        if time is not None:
            try:
                if not re.match(r"^\d{1,2}:\d{2}$", time):
                    raise ValueError
                hour, minute = int(time.split(":")[0]), int(time.split(":")[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
                validated_time = f"{hour:02d}:{minute:02d}"
            except (ValueError, IndexError):
                await interaction.response.send_message(
                    "時間格式錯誤，請使用 HH:MM 格式（例如 08:00 或 23:59）。", ephemeral=True
                )
                return

        # Validate timezone
        if timezone is not None:
            try:
                parse_timezone(timezone)
            except ValueError as e:
                await interaction.response.send_message(
                    f"無效的時區：{e}", ephemeral=True
                )
                return

        # First-time setup requires channel
        settings = self.bot.db.get_server_settings(server_id)
        if not settings and not channel:
            await interaction.response.send_message(
                "首次設定時必須指定 `channel` 參數。\n"
                "範例：`/config channel:#general time:08:00 timezone:UTC+8`",
                ephemeral=True,
            )
            return

        # Merge with existing settings
        base = {
            "channel_id": settings["channel_id"] if settings else None,
            "role_id": settings.get("role_id") if settings else None,
            "post_time": settings.get("post_time", DEFAULT_POST_TIME) if settings else DEFAULT_POST_TIME,
            "timezone": settings.get("timezone", DEFAULT_TIMEZONE) if settings else DEFAULT_TIMEZONE,
        }
        if channel:
            base["channel_id"] = channel.id
        if role:
            base["role_id"] = role.id
        if clear_role:
            base["role_id"] = None
        if validated_time is not None:
            base["post_time"] = validated_time
        if timezone is not None:
            base["timezone"] = timezone

        success = self.bot.db.set_server_settings(
            server_id, base["channel_id"], base["role_id"], base["post_time"], base["timezone"]
        )

        if not success:
            await interaction.response.send_message("設定時發生錯誤，請稍後再試。", ephemeral=True)
            return

        # Build success response with embed
        ch_obj = self.bot.get_channel(base["channel_id"])
        ch_display = ch_obj.mention if ch_obj else f"ID: {base['channel_id']}"
        role_display = "未設定"
        if base["role_id"]:
            r = interaction.guild.get_role(base["role_id"])
            role_display = r.mention if r else f"ID: {base['role_id']}"

        embed = create_settings_embed(
            interaction.guild.name, ch_display, role_display, base["post_time"], base["timezone"]
        )
        await interaction.response.send_message(
            content="✅ 設定已更新", embed=embed, ephemeral=True
        )

        await self._reschedule_if_available(server_id, "config")

    @config_command.autocomplete("timezone")
    async def config_timezone_autocomplete(self, interaction: discord.Interaction, current: str):
        lowered = current.lower()
        return [
            app_commands.Choice(name=tz, value=tz)
            for tz in self._TZ_CHOICES
            if lowered in tz.lower()
        ][:25]

    @config_command.error
    async def config_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能使用此指令。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error(f"Error in config_command: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"設定時發生錯誤: {error}", ephemeral=True)

    @app_commands.command(name="recent", description="查看 LeetCode 使用者的近期解題紀錄 (僅限 LCUS)")
    @app_commands.describe(
        username="LeetCode 使用者名稱",
        limit="顯示的題目數量 (預設 20，最多 50)",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def recent_command(
        self,
        interaction: discord.Interaction,
        username: str,
        limit: int = 20,
        public: bool = False,
    ):
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
                await interaction.followup.send(
                    f"找不到使用者 **{username}** 的解題紀錄，請確認使用者名稱是否正確。",
                    ephemeral=not public,
                )
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
                interaction_cog.submissions_cache[cache_key] = (
                    submissions,
                    time.time(),
                    limit,
                )

            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info(f"Sent user submissions for {username} to {interaction.user.name}")

        except Exception as e:
            self.logger.error(f"Error in recent_command: {e}", exc_info=True)
            await interaction.followup.send(f"查詢解題紀錄時發生錯誤：{e}", ephemeral=not public)

    async def _get_submission_details(self, basic_submission: dict) -> dict:
        """Get detailed problem information for a submission"""
        try:
            problem = await self.bot.lcus.get_problem(slug=basic_submission["slug"])
            if problem:
                return {
                    "id": problem["id"],
                    "title": problem["title"],
                    "slug": basic_submission["slug"],
                    "link": problem["link"],
                    "difficulty": problem["difficulty"],
                    "rating": problem.get("rating", 0),
                    "tags": problem.get("tags", []),
                    "ac_rate": problem.get("ac_rate", 0),
                    "submission_time": basic_submission["submission_time"],
                    "submission_id": basic_submission["submission_id"],
                }
        except Exception as e:
            self.logger.error(f"Error getting submission details: {e}", exc_info=True)
        return None



async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommandsCog(bot))
