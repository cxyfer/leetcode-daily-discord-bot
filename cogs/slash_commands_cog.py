import asyncio
import re
import time

import discord
from discord import app_commands
from discord.ext import commands

from api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE, parse_timezone
from utils.logger import get_commands_logger
from utils.ui_constants import ATCODER_LOGO_URL, LEETCODE_LOGO_URL
from utils.ui_helpers import (
    _fetch_daily_history,
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

    # ── /daily ────────────────────────────────────────────────────────

    @app_commands.command(name="daily", description="取得 LeetCode 每日挑戰 (LCUS)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def daily_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)
        if date:
            await self._daily_by_date(interaction, "com", date, public)
        else:
            await send_daily_challenge(bot=self.bot, interaction=interaction, domain="com", ephemeral=not public)

    @app_commands.command(name="daily_cn", description="取得 LeetCode 每日挑戰 (LCCN)")
    @app_commands.describe(
        date="查詢指定日期的每日挑戰 (YYYY-MM-DD 格式)，不填則為今天，最早為 2020-04-01",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def daily_cn_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)
        if date:
            await self._daily_by_date(interaction, "cn", date, public)
        else:
            await send_daily_challenge(bot=self.bot, interaction=interaction, domain="cn", ephemeral=not public)

    async def _daily_by_date(self, interaction: discord.Interaction, domain: str, date: str, public: bool):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            await interaction.followup.send(
                "日期格式錯誤，請使用 YYYY-MM-DD 格式（例如：2025-07-01）", ephemeral=not public
            )
            return
        try:
            challenge_info = await self.bot.api.get_daily(domain, date)
            if not challenge_info:
                await interaction.followup.send(f"找不到 {date} 的每日挑戰資料。", ephemeral=not public)
                return

            history_problems = await _fetch_daily_history(self.bot, domain, date)
            embed = await create_problem_embed(
                problem_info=challenge_info, bot=self.bot, domain=domain,
                is_daily=True, date_str=date, history_problems=history_problems,
            )
            view = await create_problem_view(problem_info=challenge_info, bot=self.bot, domain=domain)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent daily challenge for %s (%s) to user %s", date, domain, interaction.user.name)

        except ApiProcessingError:
            await interaction.followup.send("⏳ 資料準備中，請稍後重試。", ephemeral=not public)
        except ApiNetworkError:
            await interaction.followup.send("🔌 API 連線失敗，請稍後重試。", ephemeral=not public)
        except ApiRateLimitError:
            await interaction.followup.send("⏱️ 請求頻率過高，請稍後重試。", ephemeral=not public)
        except ApiError as e:
            self.logger.error("API error in daily command: %s", e)
            await interaction.followup.send("❌ 查詢失敗，請稍後重試。", ephemeral=not public)
        except Exception as e:
            self.logger.error("Error in daily command with date %s: %s", date, e, exc_info=True)
            await interaction.followup.send(f"查詢每日挑戰時發生錯誤：{e}", ephemeral=not public)

    # ── /problem ──────────────────────────────────────────────────────

    @app_commands.command(name="problem", description="根據題號查詢題目資訊")
    @app_commands.describe(
        problem_ids="題目編號，可用逗號分隔 (例如: 1, two-sum, abc321_a, atcoder:abc321_a)",
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
        if domain not in ["com", "cn"]:
            await interaction.response.send_message("網域參數只能是 'com' 或 'cn'", ephemeral=not public)
            return
        if title and len(title) > 100:
            await interaction.response.send_message("自定義標題不能超過 100 個字元", ephemeral=not public)
            return
        if message and len(message) > 500:
            await interaction.response.send_message("個人訊息不能超過 500 個字元", ephemeral=not public)
            return

        id_strings = [s.strip() for s in problem_ids.split(",") if s.strip()]
        if not id_strings:
            await interaction.response.send_message("請提供至少一個題目編號", ephemeral=not public)
            return
        if len(id_strings) > 20:
            await interaction.response.send_message("一次最多只能查詢 20 個題目", ephemeral=not public)
            return

        await interaction.response.defer(ephemeral=not public)

        try:
            sem = asyncio.Semaphore(5)

            async def resolve_one(query: str):
                async with sem:
                    full_query = f"{source}:{query}" if source and source != "leetcode" else query
                    result = await self.bot.api.resolve(full_query)
                    if result and result.get("problem"):
                        return result["problem"]
                    if not source or source == "leetcode":
                        problem = await self.bot.api.get_problem("leetcode", query)
                        if problem:
                            return problem
                    return None

            results = await asyncio.gather(*[resolve_one(q) for q in id_strings])
            problems = [r for r in results if r is not None]

            if not problems:
                await interaction.followup.send(
                    "找不到任何有效的題目，請確認題目編號是否正確或是否為公開題目。",
                    ephemeral=not public,
                )
                return

            if len(problems) == 1:
                embed = await create_problem_embed(
                    problem_info=problems[0], bot=self.bot, domain=domain,
                    is_daily=False, user=interaction.user, title=title, message=message,
                )
                view = await create_problem_view(problem_info=problems[0], bot=self.bot, domain=domain)
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                return

            # Multiple problems
            sources = {p.get("source", "leetcode") for p in problems}
            if sources == {"leetcode"}:
                source_label, footer_icon = "LeetCode", LEETCODE_LOGO_URL
            elif sources == {"atcoder"}:
                source_label, footer_icon = "AtCoder", ATCODER_LOGO_URL
            else:
                source_label, footer_icon = "Mixed Sources", None

            embed = create_problems_overview_embed(
                problems, domain, interaction.user, message, title,
                source_label=source_label, show_instructions=True, footer_icon_url=footer_icon,
            )
            view = create_problems_overview_view(problems, domain)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent %d problems to user %s", len(problems), interaction.user.name)

        except ApiProcessingError:
            await interaction.followup.send("⏳ 資料準備中，請稍後重試。", ephemeral=not public)
        except ApiNetworkError:
            await interaction.followup.send("🔌 API 連線失敗，請稍後重試。", ephemeral=not public)
        except ApiRateLimitError:
            await interaction.followup.send("⏱️ 請求頻率過高，請稍後重試。", ephemeral=not public)
        except ApiError as e:
            self.logger.error("API error in problem command: %s", e)
            await interaction.followup.send("❌ 查詢失敗，請稍後重試。", ephemeral=not public)
        except Exception as e:
            self.logger.error("Error in problem_command: %s", e, exc_info=True)
            await interaction.followup.send(f"查詢題目時發生錯誤：{e}", ephemeral=not public)

    @problem_command.autocomplete("domain")
    async def problem_domain_autocomplete(self, interaction: discord.Interaction, current: str):
        domains = ["com", "cn"]
        return [
            app_commands.Choice(name=domain, value=domain) for domain in domains if current.lower() in domain.lower()
        ]

    # ── /config ───────────────────────────────────────────────────────

    _TZ_CHOICES: list[str] = (
        [f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)]
        + ["UTC+3:30", "UTC+4:30", "UTC+5:30", "UTC+5:45", "UTC+6:30", "UTC+8:45", "UTC+9:30", "UTC+10:30", "UTC+12:45"]
        + [
            "UTC",
            "Asia/Taipei",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Kolkata",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Berlin",
        ]
    )

    @app_commands.command(name="config", description="設定 LeetCode 每日挑戰的所有配置")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="發送每日挑戰的頻道",
        role="要標記的身分組",
        post_time="發送時間 (HH:MM 或 H:MM，例如 08:00)",
        timezone="時區 (例如 Asia/Taipei 或 UTC+8)",
        clear_role="清除身分組標記設定",
        reset="重置所有設定並停止排程（需確認）",
    )
    @app_commands.rename(post_time="time")
    async def config_command(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        role: discord.Role = None,
        post_time: str = None,
        timezone: str = None,
        clear_role: bool = False,
        reset: bool = False,
    ):
        server_id = interaction.guild.id

        if reset and any([channel, role, post_time is not None, timezone is not None, clear_role]):
            await interaction.response.send_message("`reset` 不可與其他設定參數同時使用。", ephemeral=True)
            return

        has_update = any([channel, role, post_time is not None, timezone is not None, clear_role, reset])
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

        if reset:
            settings = self.bot.db.get_server_settings(server_id)
            if not settings:
                await interaction.response.send_message("此伺服器尚未設定，無需重置。", ephemeral=True)
                return
            ch = self.bot.get_channel(settings["channel_id"])
            ch_mention = ch.mention if ch else f"未知頻道 (ID: {settings['channel_id']})"
            role_mention = "未設定"
            if settings.get("role_id"):
                r = interaction.guild.get_role(int(settings["role_id"]))
                role_mention = r.mention if r else f"未知身分組 (ID: {settings['role_id']})"
            post_time = settings.get("post_time", DEFAULT_POST_TIME)
            tz = settings.get("timezone", DEFAULT_TIMEZONE)
            preview_embed = create_settings_embed(interaction.guild.name, ch_mention, role_mention, post_time, tz)

            exp_unix = int(time.time()) + 180
            view = discord.ui.View(timeout=180)
            view.add_item(
                discord.ui.Button(
                    label="確認重置",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"config_reset_confirm|{server_id}|{interaction.user.id}|{exp_unix}",
                )
            )
            view.add_item(
                discord.ui.Button(
                    label="取消",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"config_reset_cancel|{server_id}|{interaction.user.id}|{exp_unix}",
                )
            )
            await interaction.response.send_message(
                content="⚠️ 確定要重置此伺服器的所有設定嗎？這將停止每日挑戰排程。",
                embed=preview_embed,
                view=view,
                ephemeral=True,
            )
            return

        if role and clear_role:
            await interaction.response.send_message("`role` 與 `clear_role` 不可同時使用。", ephemeral=True)
            return

        validated_time = None
        if post_time is not None:
            try:
                if not re.match(r"^\d{1,2}:\d{2}$", post_time):
                    raise ValueError
                hour, minute = int(post_time.split(":")[0]), int(post_time.split(":")[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
                validated_time = f"{hour:02d}:{minute:02d}"
            except (ValueError, IndexError):
                await interaction.response.send_message(
                    "時間格式錯誤，請使用 HH:MM 格式（例如 08:00 或 23:59）。", ephemeral=True
                )
                return

        if timezone is not None:
            try:
                parse_timezone(timezone)
            except ValueError as e:
                await interaction.response.send_message(f"無效的時區：{e}", ephemeral=True)
                return

        settings = self.bot.db.get_server_settings(server_id)
        if not settings and not channel:
            await interaction.response.send_message(
                "首次設定時必須指定 `channel` 參數。\n範例：`/config channel:#general time:08:00 timezone:UTC+8`",
                ephemeral=True,
            )
            return

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

        ch_obj = self.bot.get_channel(base["channel_id"])
        ch_display = ch_obj.mention if ch_obj else f"ID: {base['channel_id']}"
        role_display = "未設定"
        if base["role_id"]:
            r = interaction.guild.get_role(base["role_id"])
            role_display = r.mention if r else f"ID: {base['role_id']}"

        embed = create_settings_embed(
            interaction.guild.name, ch_display, role_display, base["post_time"], base["timezone"]
        )
        await interaction.response.send_message(content="✅ 設定已更新", embed=embed, ephemeral=True)
        await self._reschedule_if_available(server_id, "config")

    @config_command.autocomplete("timezone")
    async def config_timezone_autocomplete(self, interaction: discord.Interaction, current: str):
        lowered = current.lower()
        return [app_commands.Choice(name=tz, value=tz) for tz in self._TZ_CHOICES if lowered in tz.lower()][:25]

    @config_command.error
    async def config_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("您需要「管理伺服器」權限才能使用此指令。", ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("此指令不能在私訊中使用。", ephemeral=True)
        else:
            self.logger.error("Error in config_command: %s", error, exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"設定時發生錯誤: {error}", ephemeral=True)

    # ── /recent ───────────────────────────────────────────────────────

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
        if limit < 1:
            await interaction.response.send_message("顯示數量必須至少為 1", ephemeral=not public)
            return
        if limit > 50:
            limit = 50

        await interaction.response.defer(ephemeral=not public)

        try:
            submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, limit)
            if not submissions:
                await interaction.followup.send(
                    f"找不到使用者 **{username}** 的解題紀錄，請確認使用者名稱是否正確。",
                    ephemeral=not public,
                )
                return

            first_submission = await self._get_submission_details(submissions[0])
            if not first_submission:
                await interaction.followup.send("無法載入題目詳細資訊", ephemeral=not public)
                return

            embed = create_submission_embed(first_submission, 0, len(submissions), username)
            view = create_submission_view(first_submission, self.bot, 0, username, len(submissions))

            interaction_cog = self.bot.get_cog("InteractionHandlerCog")
            if interaction_cog:
                cache_key = f"{username}_{interaction.user.id}"
                interaction_cog.submissions_cache[cache_key] = (submissions, time.time(), limit)

            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent user submissions for %s to %s", username, interaction.user.name)

        except Exception as e:
            self.logger.error("Error in recent_command: %s", e, exc_info=True)
            await interaction.followup.send(f"查詢解題紀錄時發生錯誤：{e}", ephemeral=not public)

    async def _get_submission_details(self, basic_submission: dict) -> dict:
        try:
            result = await self.bot.api.resolve(basic_submission["slug"])
            if result and result.get("problem"):
                p = result["problem"]
                return {
                    "id": p["id"],
                    "title": p["title"],
                    "slug": basic_submission["slug"],
                    "link": p["link"],
                    "difficulty": p.get("difficulty", "Unknown"),
                    "rating": p.get("rating", 0),
                    "tags": p.get("tags", []),
                    "ac_rate": p.get("ac_rate", 0),
                    "source": p.get("source", "leetcode"),
                    "submission_time": basic_submission["submission_time"],
                    "submission_id": basic_submission["submission_id"],
                }
        except Exception as e:
            self.logger.error("Error getting submission details: %s", e, exc_info=True)
        return None


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommandsCog(bot))
