import asyncio
import time

import discord
from discord.ext import commands

from api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from leetcode import html_to_text
from utils.logger import get_commands_logger
from utils.ui_helpers import (
    create_inspiration_embed,
    create_problem_description_embed,
    create_submission_embed,
    create_submission_view,
    get_difficulty_emoji,
)


class InteractionHandlerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()
        self.submissions_cache = {}
        self.ongoing_llm_requests: set[tuple] = set()
        self.ongoing_llm_requests_lock = asyncio.Lock()

    async def _cleanup_request(self, request_key: tuple):
        async with self.ongoing_llm_requests_lock:
            self.ongoing_llm_requests.discard(request_key)

    async def _check_duplicate_llm(self, interaction: discord.Interaction, request_key: tuple, label: str) -> bool:
        async with self.ongoing_llm_requests_lock:
            if request_key in self.ongoing_llm_requests:
                await interaction.followup.send(f"正在處理您的{label}請求，請稍候...", ephemeral=True)
                return True
            self.ongoing_llm_requests.add(request_key)
            return False

    # -- Config reset (preserved) --

    async def _handle_config_reset(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        parts = custom_id.split("|")
        try:
            if len(parts) != 4:
                raise ValueError
            action, raw_guild_id, raw_user_id, raw_exp_unix = parts
            guild_id = int(raw_guild_id)
            user_id = int(raw_user_id)
            exp_unix = int(raw_exp_unix)
        except (ValueError, TypeError):
            await interaction.response.send_message("無效的操作。", ephemeral=True)
            return

        if action not in ("config_reset_cancel", "config_reset_confirm"):
            await interaction.response.send_message("無效的操作。", ephemeral=True)
            return
        if not interaction.guild or guild_id != interaction.guild.id:
            await interaction.response.send_message("無效的操作。", ephemeral=True)
            return
        if user_id != interaction.user.id:
            await interaction.response.send_message("此操作僅限原發起者使用。", ephemeral=True)
            return
        if int(time.time()) > exp_unix:
            await interaction.response.send_message("此確認已過期，請重新使用 /config reset:True。", ephemeral=True)
            return

        if action == "config_reset_cancel":
            await interaction.response.edit_message(content="已取消重置操作。", embed=None, view=None)
            return

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("您需要「管理伺服器」權限才能執行此操作。", ephemeral=True)
            return
        if not self.bot.db.delete_server_settings(guild_id):
            await interaction.response.send_message("重置設定時發生錯誤，請稍後再試。", ephemeral=True)
            return
        await self.bot.reschedule_daily_challenge(guild_id, "config_reset")
        await interaction.response.edit_message(content="✅ 已重置所有設定並停止排程。", embed=None, view=None)

    # -- Submission navigation (preserved) --

    async def _handle_submission_nav(self, interaction: discord.Interaction, custom_id: str):
        try:
            parts = custom_id.split("_")
            direction = parts[2]
            username = "_".join(parts[3:-1])
            current_page = int(parts[-1])
            new_page = current_page - 1 if direction == "prev" else current_page + 1

            cache_key = f"{username}_{interaction.user.id}"
            cached = self.submissions_cache.get(cache_key)

            if cached and (time.time() - cached[1]) < 300:
                submissions = cached[0]
            else:
                await interaction.response.defer(ephemeral=True)
                limit = cached[2] if cached and len(cached) > 2 else 50
                submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, limit)
                if not submissions:
                    await interaction.followup.send(f"找不到使用者 **{username}** 的解題紀錄。", ephemeral=True)
                    return
                self.submissions_cache[cache_key] = (submissions, time.time(), limit)

            if new_page < 0 or new_page >= len(submissions):
                await interaction.response.send_message("無效的頁面", ephemeral=True)
                return

            slash_cog = self.bot.get_cog("SlashCommandsCog")
            if not slash_cog:
                await interaction.response.send_message("無法載入指令模組", ephemeral=True)
                return

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            detailed = await slash_cog._get_submission_details(submissions[new_page])
            if not detailed:
                await interaction.followup.send("無法載入題目詳細資訊", ephemeral=True)
                return

            embed = create_submission_embed(detailed, new_page, len(submissions), username)
            view = create_submission_view(detailed, self.bot, new_page, username, len(submissions))
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            self.logger.error("Submission nav error: %s", e, exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"導航時發生錯誤：{e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"導航時發生錯誤：{e}", ephemeral=True)
            except Exception:
                pass

    # -- Unified problem action handler --

    async def _handle_problem_action(self, interaction: discord.Interaction, source: str, pid: str, action: str):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            self.logger.warning("Failed to defer interaction %s", interaction.id)
            return

        try:
            if action == "desc":
                await self._action_desc(interaction, source, pid)
            elif action == "translate":
                await self._action_translate(interaction, source, pid)
            elif action == "inspire":
                await self._action_inspire(interaction, source, pid)
            elif action == "similar":
                await self._action_similar(interaction, source, pid)
            else:
                self.logger.debug("Unknown action: %s", action)
        except ApiProcessingError:
            await interaction.followup.send("⏳ 資料準備中，請稍後重試。", ephemeral=True)
        except ApiNetworkError:
            await interaction.followup.send("🔌 API 連線失敗，請稍後重試。", ephemeral=True)
        except ApiRateLimitError:
            await interaction.followup.send("⏱️ 請求頻率過高，請稍後重試。", ephemeral=True)
        except ApiError as e:
            self.logger.error("API error %s:%s/%s: %s", source, pid, action, e)
            await interaction.followup.send("❌ 查詢失敗，請稍後重試。", ephemeral=True)
        except Exception as e:
            self.logger.error("Error %s:%s/%s: %s", source, pid, action, e, exc_info=True)
            try:
                await interaction.followup.send(f"發生錯誤：{e}", ephemeral=True)
            except Exception:
                pass

    async def _action_desc(self, interaction: discord.Interaction, source: str, pid: str):
        problem = await self.bot.api.get_problem(source, pid)
        if not problem or not problem.get("content"):
            await interaction.followup.send("找不到題目或題目無描述內容。", ephemeral=True)
            return

        content = html_to_text(problem["content"])
        sep = ". " if source == "leetcode" else ": "
        header = f"[{problem['id']}{sep}{problem['title']}]({problem['link']})"

        if len(content) < 1900:
            await interaction.followup.send(f"# {header}\n\n{content}", ephemeral=True)
        else:
            if len(content) > 4000:
                content = content[:4000] + "...\n(內容已截斷，請前往網站查看完整題目)"
            info = problem.copy()
            info["description"] = content
            embed = create_problem_description_embed(info, domain="com", source=source)
            await interaction.followup.send(
                "由於題目內容過長，使用嵌入式訊息的方式顯示。", embed=embed, ephemeral=True
            )

    async def _action_translate(self, interaction: discord.Interaction, source: str, pid: str):
        if not self.bot.llm:
            await interaction.followup.send("LLM 翻譯功能尚未啟用。", ephemeral=True)
            return

        request_key = (interaction.user.id, pid, "translate")
        if await self._check_duplicate_llm(interaction, request_key, "翻譯"):
            return

        try:
            cached = self.bot.llm_translate_db.get_translation(source, pid)
            if cached:
                translation = cached["translation"]
                model_name = cached.get("model_name", "Unknown Model")
                footer = f"\n\n✨ 由 `{model_name}` 提供翻譯"
                if len(translation) + len(footer) > 2000:
                    translation = translation[: 2000 - len(footer)]
                await interaction.followup.send(translation + footer, ephemeral=True)
                return

            problem = await self.bot.api.get_problem(source, pid)
            if not problem or not problem.get("content"):
                await interaction.followup.send("無法獲取題目描述。", ephemeral=True)
                return

            text = html_to_text(problem["content"])
            translation = await self.bot.llm.translate(text, "zh-TW")
            model_name = getattr(self.bot.llm, "model_name", "Unknown Model")
            footer = f"\n\n✨ 由 `{model_name}` 提供翻譯"
            max_len = 2000 - len(footer)
            if len(translation) > max_len:
                translation = translation[: max_len - 10] + "...\n(翻譯內容已截斷)"

            self.bot.llm_translate_db.save_translation(source, pid, translation, model_name)
            await interaction.followup.send(translation + footer, ephemeral=True)
        except (ApiProcessingError, ApiNetworkError, ApiRateLimitError, ApiError):
            raise
        except Exception as e:
            self.logger.error("LLM translate error: %s", e, exc_info=True)
            await interaction.followup.send(f"LLM 翻譯失敗：{e}", ephemeral=True)
        finally:
            await self._cleanup_request(request_key)

    async def _action_inspire(self, interaction: discord.Interaction, source: str, pid: str):
        if not self.bot.llm_pro:
            await interaction.followup.send("LLM 靈感啟發功能尚未啟用。", ephemeral=True)
            return

        request_key = (interaction.user.id, pid, "inspire")
        if await self._check_duplicate_llm(interaction, request_key, "靈感啟發"):
            return

        def fmt(val):
            return "\n".join(f"- {x}" for x in val) if isinstance(val, list) else str(val)

        try:
            cached = self.bot.llm_inspire_db.get_inspire(source, pid)
            problem = await self.bot.api.get_problem(source, pid)
            if not problem:
                await interaction.followup.send("無法獲取題目資訊。", ephemeral=True)
                return

            if cached:
                model_name = cached.get("model_name", "Unknown Model")
                inspiration_data = cached.copy()
            else:
                if not problem.get("content"):
                    await interaction.followup.send("無法獲取題目內容。", ephemeral=True)
                    return

                text = html_to_text(problem["content"])
                tags = problem.get("tags") or []
                difficulty = problem.get("difficulty", "")

                llm_output = await self.bot.llm_pro.inspire(text, tags, difficulty)
                model_name = getattr(self.bot.llm_pro, "model_name", "Unknown Model")

                if not isinstance(llm_output, dict) or not all(
                    k in llm_output for k in ["thinking", "traps", "algorithms", "inspiration"]
                ):
                    raw = str(llm_output.get("raw", llm_output))[:1900]
                    await interaction.followup.send(raw, ephemeral=True)
                    return

                self.bot.llm_inspire_db.save_inspire(
                    source, pid,
                    fmt(llm_output.get("thinking", "")),
                    fmt(llm_output.get("traps", "")),
                    fmt(llm_output.get("algorithms", "")),
                    fmt(llm_output.get("inspiration", "")),
                    model_name=model_name,
                )
                inspiration_data = llm_output.copy()

            inspiration_data["footer"] = f"由 {model_name} 提供靈感"
            embed = create_inspiration_embed(inspiration_data, problem)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except (ApiProcessingError, ApiNetworkError, ApiRateLimitError, ApiError):
            raise
        except Exception as e:
            self.logger.error("LLM inspire error: %s", e, exc_info=True)
            await interaction.followup.send(f"LLM 靈感啟發失敗：{e}", ephemeral=True)
        finally:
            await self._cleanup_request(request_key)

    async def _action_similar(self, interaction: discord.Interaction, source: str, pid: str):
        cfg = self.bot.config.get_similar_config()
        result = await self.bot.api.search_similar_by_id(source, pid, cfg.top_k, cfg.min_similarity)
        if not result or not result.get("results"):
            await interaction.followup.send("找不到相似題目。", ephemeral=True)
            return

        embed = discord.Embed(title="🔍 相似題目", color=0x3498DB)
        lines = []
        for r in result["results"]:
            diff = r.get("difficulty") or "Unknown"
            emoji = get_difficulty_emoji(diff)
            sim = f"{r['similarity']:.2f}"
            lines.append(f"- {emoji} [{r['title']}]({r['link']}) `{sim}`")
        embed.description = "\n".join(lines)

        if result.get("rewritten_query"):
            embed.set_footer(text=f"Rewritten: {result['rewritten_query']}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # -- Main listener --

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        # Config reset (preserved)
        if custom_id.startswith("config_reset_confirm|") or custom_id.startswith("config_reset_cancel|"):
            await self._handle_config_reset(interaction)
            return

        # Submission navigation (preserved)
        if custom_id.startswith("user_sub_prev_") or custom_id.startswith("user_sub_next_"):
            await self._handle_submission_nav(interaction, custom_id)
            return

        # Unified problem button: problem|{source}|{id}|{action}
        if custom_id.startswith("problem|"):
            parts = custom_id.split("|")
            if len(parts) == 4:
                _, source, pid, action = parts
                await self._handle_problem_action(interaction, source, pid, action)
            else:
                self.logger.debug("Invalid problem button format: %s", custom_id)
            return

        # Silently ignore old/unrecognized custom_ids
        self.logger.debug("Ignoring unrecognized custom_id: %s", custom_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionHandlerCog(bot))
