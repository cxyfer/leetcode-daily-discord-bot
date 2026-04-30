import asyncio
import re
import time

import discord
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.leetcode import html_to_text
from bot.utils.logger import get_commands_logger
from bot.utils.ui_helpers import (
    _get_locale,
    create_inspiration_embed,
    create_problem_description_embed,
    create_problem_embed,
    create_problem_view,
    create_similar_results_message,
    create_submission_embed,
    create_submission_view,
    send_api_error,
)

LEGACY_LEETCODE_CUSTOM_ID_PATTERNS = (
    (re.compile(r"^problem_detail_(?P<pid>\d+)_(?P<domain>com|cn)$"), "leetcode", "view"),
    (re.compile(r"^leetcode_problem_(?P<pid>\d+)_(?P<domain>com|cn)$"), "leetcode", "desc"),
    (re.compile(r"^leetcode_translate_(?P<pid>\d+)_(?P<domain>com|cn)$"), "leetcode", "translate"),
    (re.compile(r"^leetcode_inspire_(?P<pid>\d+)_(?P<domain>com|cn)$"), "leetcode", "inspire"),
    (re.compile(r"^leetcode_similar_(?P<pid>\d+)_(?P<domain>com|cn)$"), "leetcode", "similar"),
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

    async def _check_duplicate_llm(self, interaction: discord.Interaction, request_key: tuple, message: str) -> bool:
        async with self.ongoing_llm_requests_lock:
            if request_key in self.ongoing_llm_requests:
                await interaction.followup.send(message, ephemeral=True)
                return True
            self.ongoing_llm_requests.add(request_key)
            return False

    # -- Config reset (preserved) --

    async def _handle_config_reset(self, interaction: discord.Interaction):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

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
            await interaction.response.send_message(i18n.t("errors.reset.invalid_action", locale), ephemeral=True)
            return

        if action not in ("config_reset_cancel", "config_reset_confirm"):
            await interaction.response.send_message(i18n.t("errors.reset.invalid_action", locale), ephemeral=True)
            return
        if not interaction.guild or guild_id != interaction.guild.id:
            await interaction.response.send_message(i18n.t("errors.reset.invalid_action", locale), ephemeral=True)
            return
        if user_id != interaction.user.id:
            await interaction.response.send_message(i18n.t("errors.reset.wrong_user", locale), ephemeral=True)
            return
        if int(time.time()) > exp_unix:
            await interaction.response.send_message(i18n.t("errors.reset.expired", locale), ephemeral=True)
            return

        if action == "config_reset_cancel":
            cancelled_msg = i18n.t("errors.reset.cancelled", locale)
            await interaction.response.edit_message(content=cancelled_msg, embed=None, view=None)
            return

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(i18n.t("errors.reset.permission_denied", locale), ephemeral=True)
            return
        if not self.bot.db.delete_server_settings(guild_id):
            await interaction.response.send_message(i18n.t("errors.reset.error", locale), ephemeral=True)
            return
        await self.bot.reschedule_daily_challenge(guild_id, "config_reset")
        await interaction.response.edit_message(content=i18n.t("errors.reset.success", locale), embed=None, view=None)

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

            locale = _get_locale(self.bot, interaction)
            i18n = self.bot.i18n

            if cached and (time.time() - cached[1]) < 300:
                submissions = cached[0]
            else:
                await interaction.response.defer(ephemeral=True)
                limit = cached[2] if cached and len(cached) > 2 else 50
                submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, limit)
                if not submissions:
                    no_sub_msg = i18n.t("errors.validation.no_submissions", locale, username=username)
                    await interaction.followup.send(no_sub_msg, ephemeral=True)
                    return
                self.submissions_cache[cache_key] = (submissions, time.time(), limit)

            if new_page < 0 or new_page >= len(submissions):
                invalid_page_msg = i18n.t("errors.validation.invalid_page", locale)
                await interaction.response.send_message(invalid_page_msg, ephemeral=True)
                return

            slash_cog = self.bot.get_cog("SlashCommandsCog")
            if not slash_cog:
                module_err_msg = i18n.t("errors.validation.module_load_error", locale)
                await interaction.response.send_message(module_err_msg, ephemeral=True)
                return

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            detailed = await slash_cog._get_submission_details(submissions[new_page])
            if not detailed:
                detail_err_msg = i18n.t("errors.validation.submission_detail_error", locale)
                await interaction.followup.send(detail_err_msg, ephemeral=True)
                return

            embed = create_submission_embed(detailed, new_page, len(submissions), username, bot=self.bot, locale=locale)
            view = create_submission_view(detailed, self.bot, new_page, username, len(submissions))
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            self.logger.error("Submission nav error: %s", e, exc_info=True)
            try:
                locale = _get_locale(self.bot, interaction)
                i18n = self.bot.i18n
                error_msg = i18n.t("errors.navigation.error", locale, error=e)
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_msg, ephemeral=True)
                else:
                    await interaction.followup.send(error_msg, ephemeral=True)
            except Exception:
                pass

    def _parse_legacy_problem_custom_id(self, custom_id: str) -> tuple[str, str, str] | None:
        for pattern, source, action in LEGACY_LEETCODE_CUSTOM_ID_PATTERNS:
            match = pattern.match(custom_id)
            if match:
                return source, match.group("pid"), action
        return None

    async def _handle_problem_action(self, interaction: discord.Interaction, source: str, pid: str, action: str):
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            self.logger.warning("Failed to defer interaction %s", interaction.id)
            return

        try:
            if action == "view":
                await self._action_view(interaction, source, pid)
            elif action == "desc":
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
            await send_api_error(interaction, "processing", self.bot)
        except ApiNetworkError:
            await send_api_error(interaction, "network", self.bot)
        except ApiRateLimitError:
            await send_api_error(interaction, "rate_limit", self.bot)
        except ApiError as e:
            self.logger.error("API error %s:%s/%s: %s", source, pid, action, e)
            await send_api_error(interaction, "generic", self.bot)
        except Exception as e:
            self.logger.error("Error %s:%s/%s: %s", source, pid, action, e, exc_info=True)
            try:
                locale = _get_locale(self.bot, interaction)
                await interaction.followup.send(self.bot.i18n.t("daily.error", locale, error=e), ephemeral=True)
            except Exception:
                pass

    async def _action_view(self, interaction: discord.Interaction, source: str, pid: str):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        problem = await self.bot.api.get_problem(source, pid)
        if not problem:
            await interaction.followup.send(i18n.t("errors.validation.problem_not_found", locale), ephemeral=True)
            return

        embed = await create_problem_embed(
            problem_info=problem,
            bot=self.bot,
            domain="com",
            is_daily=False,
            locale=locale,
        )
        view = await create_problem_view(problem_info=problem, bot=self.bot, domain="com", locale=locale)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _action_desc(self, interaction: discord.Interaction, source: str, pid: str):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        problem = await self.bot.api.get_problem(source, pid)
        if not problem or not problem.get("content"):
            await interaction.followup.send(i18n.t("errors.validation.no_description", locale), ephemeral=True)
            return

        content = html_to_text(problem["content"])
        sep = ". " if source == "leetcode" else ": "
        header = f"[{problem['id']}{sep}{problem['title']}]({problem['link']})"

        if len(content) < 1900:
            await interaction.followup.send(f"# {header}\n\n{content}", ephemeral=True)
        else:
            if len(content) > 4000:
                content = content[:4000] + "...\n" + i18n.t("errors.validation.content_truncated", locale)
            info = problem.copy()
            info["description"] = content
            embed = create_problem_description_embed(info, domain="com", source=source, bot=self.bot, locale=locale)
            truncated_msg = i18n.t("errors.validation.content_truncated", locale)
            await interaction.followup.send(truncated_msg, embed=embed, ephemeral=True)

    async def _action_translate(self, interaction: discord.Interaction, source: str, pid: str):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if not self.bot.llm:
            await interaction.followup.send(i18n.t("llm.translation_not_enabled", locale), ephemeral=True)
            return

        request_key = (interaction.user.id, pid, "translate")
        if await self._check_duplicate_llm(interaction, request_key, i18n.t("llm.duplicate_translate", locale)):
            return

        try:
            cached = self.bot.llm_translate_db.get_translation(source, pid, locale)
            if cached:
                translation = cached["translation"]
                model_name = cached.get("model_name", "Unknown Model")
                footer = i18n.t("llm.provided_by_model", locale, model=model_name)
                if len(translation) + len(footer) > 2000:
                    translation = translation[: 2000 - len(footer)]
                await interaction.followup.send(translation + footer, ephemeral=True)
                return

            problem = await self.bot.api.get_problem(source, pid)
            if not problem or not problem.get("content"):
                await interaction.followup.send(i18n.t("llm.cannot_fetch_description", locale), ephemeral=True)
                return

            text = html_to_text(problem["content"])
            translation = await self.bot.llm.translate(text, locale)
            model_name = getattr(self.bot.llm, "model_name", "Unknown Model")
            footer = i18n.t("llm.provided_by_model", locale, model=model_name)
            max_len = 2000 - len(footer)
            if len(translation) > max_len:
                translation = translation[: max_len - 10] + i18n.t("llm.translation_truncated", locale)

            self.bot.llm_translate_db.save_translation(source, pid, translation, locale, model_name)
            await interaction.followup.send(translation + footer, ephemeral=True)
        except (ApiProcessingError, ApiNetworkError, ApiRateLimitError, ApiError):
            raise
        except Exception as e:
            self.logger.error("LLM translate error: %s", e, exc_info=True)
            await interaction.followup.send(i18n.t("llm.translate_error", locale, error=e), ephemeral=True)
        finally:
            await self._cleanup_request(request_key)

    async def _action_inspire(self, interaction: discord.Interaction, source: str, pid: str):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if not self.bot.llm_pro:
            await interaction.followup.send(i18n.t("llm.inspire_not_enabled", locale), ephemeral=True)
            return

        request_key = (interaction.user.id, pid, "inspire")
        if await self._check_duplicate_llm(interaction, request_key, i18n.t("llm.duplicate_inspire", locale)):
            return

        def fmt(val):
            return "\n".join(f"- {x}" for x in val) if isinstance(val, list) else str(val)

        try:
            cached = self.bot.llm_inspire_db.get_inspire(source, pid, locale)
            problem = await self.bot.api.get_problem(source, pid)
            if not problem:
                await interaction.followup.send(i18n.t("llm.cannot_fetch_info", locale), ephemeral=True)
                return

            if cached:
                model_name = cached.get("model_name", "Unknown Model")
                inspiration_data = cached.copy()
            else:
                if not problem.get("content"):
                    await interaction.followup.send(i18n.t("llm.cannot_fetch_content", locale), ephemeral=True)
                    return

                text = html_to_text(problem["content"])
                tags = problem.get("tags") or []
                difficulty = problem.get("difficulty", "")

                llm_output = await self.bot.llm_pro.inspire(text, tags, difficulty, locale=locale)
                model_name = getattr(self.bot.llm_pro, "model_name", "Unknown Model")

                if not isinstance(llm_output, dict) or not all(
                    k in llm_output for k in ["thinking", "traps", "algorithms", "inspiration"]
                ):
                    raw = str(llm_output.get("raw", llm_output))[:1900]
                    await interaction.followup.send(raw, ephemeral=True)
                    return

                self.bot.llm_inspire_db.save_inspire(
                    source,
                    pid,
                    fmt(llm_output.get("thinking", "")),
                    fmt(llm_output.get("traps", "")),
                    fmt(llm_output.get("algorithms", "")),
                    fmt(llm_output.get("inspiration", "")),
                    locale=locale,
                    model_name=model_name,
                )
                inspiration_data = llm_output.copy()

            inspiration_data["footer"] = i18n.t("ui.inspire.footer", locale, model=model_name)
            embed = create_inspiration_embed(inspiration_data, problem, bot=self.bot, locale=locale)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except (ApiProcessingError, ApiNetworkError, ApiRateLimitError, ApiError):
            raise
        except Exception as e:
            self.logger.error("LLM inspire error: %s", e, exc_info=True)
            await interaction.followup.send(i18n.t("llm.inspire_error", locale, error=e), ephemeral=True)
        finally:
            await self._cleanup_request(request_key)

    async def _action_similar(self, interaction: discord.Interaction, source: str, pid: str):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        cfg = self.bot.config.get_similar_config()
        result = await self.bot.api.search_similar_by_id(source, pid, cfg.top_k, cfg.min_similarity)
        if not result or not result.get("results"):
            await interaction.followup.send(i18n.t("errors.validation.similar_not_found", locale), ephemeral=True)
            return

        embed, view = create_similar_results_message(
            result, base_source=source, base_id=pid, bot=self.bot, locale=locale
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

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

        legacy_problem_action = self._parse_legacy_problem_custom_id(custom_id)
        if legacy_problem_action:
            source, pid, action = legacy_problem_action
            await self._handle_problem_action(interaction, source, pid, action)
            return

        # Silently ignore old/unrecognized custom_ids
        self.logger.debug("Ignoring unrecognized custom_id: %s", custom_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionHandlerCog(bot))
