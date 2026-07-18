import asyncio
import re
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE, parse_timezone
from bot.utils.daily_sources import (
    DAILY_PUSH_SOURCE_LABELS,
    DEFAULT_DAILY_PUSH_SOURCE,
    validate_daily_push_source,
)
from bot.utils.logger import get_commands_logger
from bot.utils.ui_helpers import (
    _get_locale,
    create_problem_embed,
    create_problem_view,
    create_problems_overview_embed,
    create_problems_overview_view,
    create_settings_embed,
    create_submission_embed,
    create_submission_view,
    get_daily_payload,
    get_source_label,
    get_source_logo_url,
    send_api_error,
    send_daily_challenge,
)


class SlashCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()

    async def _reschedule_if_available(self, server_id: int, context: str = "", source: str | None = None):
        await self.bot.reschedule_daily_challenge(server_id, context, source=source)

    # ── /daily ────────────────────────────────────────────────────────

    @app_commands.command(name="daily", description=app_commands.locale_str("daily.description"))
    @app_commands.describe(
        date=app_commands.locale_str("daily.date"),
        public=app_commands.locale_str("daily.public"),
    )
    async def daily_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)
        if date:
            await self._daily_by_date(interaction, "com", date, public)
        else:
            await send_daily_challenge(bot=self.bot, interaction=interaction, domain="com", ephemeral=not public)

    @app_commands.command(name="daily_cn", description=app_commands.locale_str("daily_cn.description"))
    @app_commands.describe(
        date=app_commands.locale_str("daily.date"),
        public=app_commands.locale_str("daily.public"),
    )
    async def daily_cn_command(self, interaction: discord.Interaction, date: str = None, public: bool = False):
        await interaction.response.defer(ephemeral=not public)
        if date:
            await self._daily_by_date(interaction, "cn", date, public)
        else:
            await send_daily_challenge(bot=self.bot, interaction=interaction, domain="cn", ephemeral=not public)

    async def _daily_by_date(self, interaction: discord.Interaction, domain: str, date: str, public: bool):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            await interaction.followup.send(i18n.t("errors.validation.date_format", locale), ephemeral=not public)
            return
        try:
            payload = await get_daily_payload(self.bot, domain, date)
            if not payload:
                await interaction.followup.send(
                    i18n.t("errors.validation.not_found_for_date", locale, date=date), ephemeral=not public
                )
                return

            challenge_info = payload["challenge_info"]
            embed = await create_problem_embed(
                problem_info=challenge_info,
                bot=self.bot,
                domain=domain,
                is_daily=True,
                date_str=date,
                history_problems=payload["history_problems"],
                locale=locale,
            )
            view = await create_problem_view(problem_info=challenge_info, bot=self.bot, domain=domain, locale=locale)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent daily challenge for %s (%s) to user %s", date, domain, interaction.user.name)

        except ApiProcessingError:
            await send_api_error(interaction, "processing", self.bot, ephemeral=not public)
        except ApiNetworkError:
            await send_api_error(interaction, "network", self.bot, ephemeral=not public)
        except ApiRateLimitError:
            await send_api_error(interaction, "rate_limit", self.bot, ephemeral=not public)
        except ApiError as e:
            self.logger.error("API error in daily command: %s", e)
            await send_api_error(interaction, "generic", self.bot, ephemeral=not public)
        except Exception as e:
            self.logger.error("Error in daily command with date %s: %s", date, e, exc_info=True)
            await interaction.followup.send(i18n.t("daily.error", locale, error=e), ephemeral=not public)

    # ── /random ────────────────────────────────────────────────────────

    @app_commands.command(name="random", description=app_commands.locale_str("random.description"))
    @app_commands.describe(
        source=app_commands.locale_str("random.source"),
        difficulty=app_commands.locale_str("random.difficulty"),
        tags=app_commands.locale_str("random.tags"),
        rating_min=app_commands.locale_str("random.rating_min"),
        rating_max=app_commands.locale_str("random.rating_max"),
        public=app_commands.locale_str("random.public"),
    )
    @app_commands.choices(
        source=[
            app_commands.Choice(name="All", value="all"),
            app_commands.Choice(name="LeetCode", value="leetcode"),
            app_commands.Choice(name="AtCoder", value="atcoder"),
            app_commands.Choice(name="Codeforces", value="codeforces"),
            app_commands.Choice(name="Luogu", value="luogu"),
            app_commands.Choice(name="SPOJ", value="spoj"),
        ],
        difficulty=[
            app_commands.Choice(name="Easy", value="Easy"),
            app_commands.Choice(name="Medium", value="Medium"),
            app_commands.Choice(name="Hard", value="Hard"),
        ],
    )
    async def random_command(
        self,
        interaction: discord.Interaction,
        source: str = "leetcode",
        difficulty: str = None,
        tags: str = None,
        rating_min: int = None,
        rating_max: int = None,
        public: bool = False,
    ):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if rating_min is not None and rating_max is not None and rating_min > rating_max:
            rating_min, rating_max = rating_max, rating_min

        await interaction.response.defer(ephemeral=not public)

        try:
            problem = await self.bot.api.get_random_problem(
                source=source,
                difficulty=difficulty,
                tags=tags,
                rating_min=rating_min,
                rating_max=rating_max,
            )
            if not problem:
                filters = []
                if difficulty:
                    filters.append(f"difficulty:{difficulty}")
                if tags:
                    filters.append(f"tags:{discord.utils.escape_markdown(tags)}")
                if rating_min is not None or rating_max is not None:
                    r_min = str(rating_min) if rating_min is not None else "\u221e"
                    r_max = str(rating_max) if rating_max is not None else "\u221e"
                    filters.append(f"rating:{r_min}-{r_max}")
                filter_text = ", ".join(filters) if filters else i18n.t("errors.validation.random_no_filter", locale)
                await interaction.followup.send(
                    i18n.t("errors.validation.random_not_found", locale, filters=filter_text),
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return

            source = problem.get("source", "leetcode")
            domain = "cn" if source == "leetcode" and problem.get("domain") == "cn" else "com"
            embed = await create_problem_embed(
                problem_info=problem,
                bot=self.bot,
                domain=domain,
                is_daily=False,
                user=interaction.user,
                locale=locale,
                footer_text=i18n.t("ui.embed.random_footer", locale),
            )
            view = await create_problem_view(problem_info=problem, bot=self.bot, domain=domain, locale=locale)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent random problem to user %s", interaction.user.name)

        except ApiProcessingError:
            await send_api_error(interaction, "processing", self.bot, ephemeral=not public)
        except ApiNetworkError:
            await send_api_error(interaction, "network", self.bot, ephemeral=not public)
        except ApiRateLimitError:
            await send_api_error(interaction, "rate_limit", self.bot, ephemeral=not public)
        except ApiError as e:
            self.logger.error("API error in random command: %s", e)
            await send_api_error(interaction, "generic", self.bot, ephemeral=not public)
        except Exception as e:
            self.logger.error("Error in random_command: %s", e, exc_info=True)
            await interaction.followup.send(
                i18n.t("errors.validation.random_error", locale),
                ephemeral=not public,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @random_command.autocomplete("tags")
    async def random_tags_autocomplete(self, interaction: discord.Interaction, current: str):
        source = (interaction.namespace.source if interaction.namespace else None) or "leetcode"
        if source == "all":
            source = "leetcode"
        try:
            tags = await self.bot.api.get_tags_cached(source)
        except Exception:
            tags = []
        filtered = [t for t in tags if current.lower() in t.lower()]
        return [app_commands.Choice(name=t, value=t) for t in filtered[:25]]

    # ── /problem ──────────────────────────────────────────────────────

    @app_commands.command(name="problem", description=app_commands.locale_str("problem.description"))
    @app_commands.describe(
        problem_ids=app_commands.locale_str("problem.problem_ids"),
        domain=app_commands.locale_str("problem.domain"),
        public=app_commands.locale_str("problem.public"),
        title=app_commands.locale_str("problem.title"),
        message=app_commands.locale_str("problem.message"),
        source=app_commands.locale_str("problem.source"),
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
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if domain not in ["com", "cn"]:
            await interaction.response.send_message(
                i18n.t("errors.validation.domain_invalid", locale), ephemeral=not public
            )
            return
        if title and len(title) > 100:
            await interaction.response.send_message(
                i18n.t("errors.validation.title_too_long", locale), ephemeral=not public
            )
            return
        if message and len(message) > 500:
            await interaction.response.send_message(
                i18n.t("errors.validation.message_too_long", locale), ephemeral=not public
            )
            return

        id_strings = [s.strip() for s in problem_ids.split(",") if s.strip()]
        if not id_strings:
            await interaction.response.send_message(
                i18n.t("errors.validation.problem_ids_empty", locale), ephemeral=not public
            )
            return
        if len(id_strings) > 20:
            await interaction.response.send_message(
                i18n.t("errors.validation.too_many_problems", locale), ephemeral=not public
            )
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
                    i18n.t("errors.validation.problem_not_found", locale),
                    ephemeral=not public,
                )
                return

            if len(problems) == 1:
                embed = await create_problem_embed(
                    problem_info=problems[0],
                    bot=self.bot,
                    domain=domain,
                    is_daily=False,
                    user=interaction.user,
                    title=title,
                    message=message,
                    locale=locale,
                )
                view = await create_problem_view(problem_info=problems[0], bot=self.bot, domain=domain, locale=locale)
                await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
                return

            sources = {problem.get("source", "leetcode") for problem in problems}
            if len(sources) == 1:
                problem_source = next(iter(sources))
                source_label = get_source_label(problem_source)
                footer_icon = get_source_logo_url(problem_source)
            else:
                source_label, footer_icon = "Mixed Sources", None

            embed = create_problems_overview_embed(
                problems,
                domain,
                interaction.user,
                message,
                title,
                source_label=source_label,
                show_instructions=True,
                footer_icon_url=footer_icon,
                bot=self.bot,
                locale=locale,
            )
            view = create_problems_overview_view(problems, domain)
            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent %d problems to user %s", len(problems), interaction.user.name)

        except ApiProcessingError:
            await send_api_error(interaction, "processing", self.bot, ephemeral=not public)
        except ApiNetworkError:
            await send_api_error(interaction, "network", self.bot, ephemeral=not public)
        except ApiRateLimitError:
            await send_api_error(interaction, "rate_limit", self.bot, ephemeral=not public)
        except ApiError as e:
            self.logger.error("API error in problem command: %s", e)
            await send_api_error(interaction, "generic", self.bot, ephemeral=not public)
        except Exception as e:
            self.logger.error("Error in problem_command: %s", e, exc_info=True)
            await interaction.followup.send(i18n.t("errors.unexpected", locale, error=e), ephemeral=not public)

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

    _LANGUAGE_CHOICES = [
        app_commands.Choice(name="繁體中文", value="zh-TW"),
        app_commands.Choice(name="English", value="en-US"),
        app_commands.Choice(name="简体中文", value="zh-CN"),
    ]

    _DAILY_SOURCE_CHOICES = [
        app_commands.Choice(name=label, value=source) for source, label in DAILY_PUSH_SOURCE_LABELS.items()
    ]

    def _create_config_embed(
        self,
        interaction: discord.Interaction,
        language: str,
        pushes: list[dict],
        locale: str,
    ) -> discord.Embed:
        i18n = self.bot.i18n
        display_pushes = []
        for push in pushes:
            display_push = dict(push)
            channel_id = push["channel_id"]
            channel = self.bot.get_channel(channel_id)
            display_push["channel_mention"] = (
                channel.mention if channel else i18n.t("ui.settings.unknown_channel", locale, id=channel_id)
            )
            role_id = push.get("role_id")
            if role_id:
                role = interaction.guild.get_role(int(role_id))
                display_push["role_mention"] = (
                    role.mention if role else i18n.t("ui.settings.unknown_role", locale, id=role_id)
                )
            else:
                display_push["role_mention"] = i18n.t("ui.settings.not_set", locale)
            display_pushes.append(display_push)

        return create_settings_embed(
            interaction.guild.name,
            pushes=display_pushes,
            language=language,
            bot=self.bot,
            locale=locale,
        )

    @app_commands.command(name="config", description=app_commands.locale_str("config.description"))
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel=app_commands.locale_str("config.channel"),
        role=app_commands.locale_str("config.role"),
        post_time=app_commands.locale_str("config.time"),
        timezone=app_commands.locale_str("config.timezone"),
        clear_role=app_commands.locale_str("config.clear_role"),
        language=app_commands.locale_str("config.language"),
        reset=app_commands.locale_str("config.reset"),
        source=app_commands.locale_str("config.source"),
        remove=app_commands.locale_str("config.remove"),
    )
    @app_commands.choices(
        language=_LANGUAGE_CHOICES,
        source=_DAILY_SOURCE_CHOICES,
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
        language: str = None,
        reset: bool = False,
        source: str = None,
        remove: bool = False,
    ):
        server_id = interaction.guild.id

        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if source is not None:
            try:
                validate_daily_push_source(source)
            except ValueError:
                await interaction.response.send_message(i18n.t("errors.config.source_invalid", locale), ephemeral=True)
                return

        push_update_requested = any([channel, role, post_time is not None, timezone is not None, clear_role])

        if remove and any([reset, channel, role, post_time is not None, timezone is not None, clear_role, language]):
            await interaction.response.send_message(i18n.t("errors.config.remove_conflict", locale), ephemeral=True)
            return
        if remove and source is None:
            await interaction.response.send_message(
                i18n.t("errors.config.remove_source_required", locale),
                ephemeral=True,
            )
            return

        if reset and any([channel, role, post_time is not None, timezone is not None, clear_role, language, source]):
            await interaction.response.send_message(i18n.t("errors.config.reset_conflict", locale), ephemeral=True)
            return

        has_update = push_update_requested or language is not None or reset or remove
        if not has_update:
            settings = self.bot.db.get_server_settings(server_id)
            pushes = self.bot.db.get_daily_pushes(server_id)
            if not settings and not pushes:
                await interaction.response.send_message(
                    i18n.t("errors.config.not_configured", locale),
                    ephemeral=True,
                )
                return
            lang = settings.get("language", "zh-TW") if settings else "zh-TW"
            embed = self._create_config_embed(interaction, lang, pushes, locale)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if reset:
            settings = self.bot.db.get_server_settings(server_id)
            if not settings:
                await interaction.response.send_message(i18n.t("errors.config.not_setup", locale), ephemeral=True)
                return
            preview_embed = self._create_config_embed(
                interaction,
                settings.get("language", "zh-TW"),
                self.bot.db.get_daily_pushes(server_id),
                locale,
            )

            exp_unix = int(time.time()) + 180
            view = discord.ui.View(timeout=180)
            view.add_item(
                discord.ui.Button(
                    label=i18n.t("ui.buttons.confirm_reset", locale),
                    style=discord.ButtonStyle.danger,
                    custom_id=f"config_reset_confirm|{server_id}|{interaction.user.id}|{exp_unix}",
                )
            )
            view.add_item(
                discord.ui.Button(
                    label=i18n.t("ui.buttons.cancel", locale),
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"config_reset_cancel|{server_id}|{interaction.user.id}|{exp_unix}",
                )
            )
            await interaction.response.send_message(
                content=i18n.t("errors.reset.confirm_message", locale),
                embed=preview_embed,
                view=view,
                ephemeral=True,
            )
            return

        if remove:
            push = self.bot.db.get_daily_push(server_id, source)
            if not push:
                await interaction.response.send_message(
                    i18n.t(
                        "errors.config.source_not_configured",
                        locale,
                        source=DAILY_PUSH_SOURCE_LABELS[source],
                    ),
                    ephemeral=True,
                )
                return

            settings = self.bot.db.get_server_settings(server_id) or {}
            preview_embed = self._create_config_embed(
                interaction,
                settings.get("language", "zh-TW"),
                [push],
                locale,
            )
            exp_unix = int(time.time()) + 180
            view = discord.ui.View(timeout=180)
            view.add_item(
                discord.ui.Button(
                    label=i18n.t("ui.buttons.confirm_remove", locale),
                    style=discord.ButtonStyle.danger,
                    custom_id=f"config_remove_confirm|{server_id}|{interaction.user.id}|{exp_unix}|{source}",
                )
            )
            view.add_item(
                discord.ui.Button(
                    label=i18n.t("ui.buttons.cancel", locale),
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"config_remove_cancel|{server_id}|{interaction.user.id}|{exp_unix}|{source}",
                )
            )
            await interaction.response.send_message(
                content=i18n.t(
                    "errors.config.remove_confirm_message",
                    locale,
                    source=DAILY_PUSH_SOURCE_LABELS[source],
                ),
                embed=preview_embed,
                view=view,
                ephemeral=True,
            )
            return

        if role and clear_role:
            await interaction.response.send_message(i18n.t("errors.config.role_clear_conflict", locale), ephemeral=True)
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
                time_err_msg = i18n.t("errors.config.time_format_error", locale)
                await interaction.response.send_message(time_err_msg, ephemeral=True)
                return

        if timezone is not None:
            try:
                parse_timezone(timezone)
            except ValueError as e:
                tz_err_msg = i18n.t("errors.config.timezone_error", locale, error=e)
                await interaction.response.send_message(tz_err_msg, ephemeral=True)
                return

        if language:
            supported = self.bot.i18n.get_supported_locales()
            if language not in supported:
                await interaction.response.send_message(
                    i18n.t("errors.config.language_invalid", locale, supported=", ".join(supported)),
                    ephemeral=True,
                )
                return

        selected_source = source or DEFAULT_DAILY_PUSH_SOURCE
        push_success = True
        if push_update_requested:
            current_push = self.bot.db.get_daily_push(server_id, selected_source)
            if not current_push and not channel:
                await interaction.response.send_message(
                    i18n.t("errors.config.first_setup_required", locale),
                    ephemeral=True,
                )
                return

            base = {
                "channel_id": current_push["channel_id"] if current_push else channel.id,
                "role_id": current_push.get("role_id") if current_push else None,
                "post_time": current_push.get("post_time", DEFAULT_POST_TIME) if current_push else DEFAULT_POST_TIME,
                "timezone": current_push.get("timezone", DEFAULT_TIMEZONE) if current_push else DEFAULT_TIMEZONE,
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

            push_success = self.bot.db.set_daily_push(
                server_id,
                selected_source,
                base["channel_id"],
                base["role_id"],
                base["post_time"],
                base["timezone"],
            )

        language_success = self.bot.db.set_server_language(server_id, language) if language else True
        if not push_success or not language_success:
            await interaction.response.send_message(i18n.t("errors.config.settings_error", locale), ephemeral=True)
            return

        settings = self.bot.db.get_server_settings(server_id) or {}
        current_language = language or settings.get("language", "zh-TW")
        embed = self._create_config_embed(
            interaction,
            current_language,
            self.bot.db.get_daily_pushes(server_id),
            locale,
        )
        updated_msg = i18n.t("errors.config.settings_updated", locale)
        await interaction.response.send_message(content=updated_msg, embed=embed, ephemeral=True)
        if push_update_requested:
            await self._reschedule_if_available(server_id, "config", selected_source)

    @config_command.autocomplete("timezone")
    async def config_timezone_autocomplete(self, interaction: discord.Interaction, current: str):
        lowered = current.lower()
        return [app_commands.Choice(name=tz, value=tz) for tz in self._TZ_CHOICES if lowered in tz.lower()][:25]

    @config_command.error
    async def config_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(i18n.t("errors.config.permission_denied", locale), ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(i18n.t("errors.config.dm_restricted", locale), ephemeral=True)
        else:
            self.logger.error("Error in config_command: %s", error, exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(i18n.t("errors.config.settings_error", locale), ephemeral=True)

    # ── /recent ───────────────────────────────────────────────────────

    @app_commands.command(name="recent", description=app_commands.locale_str("recent.description"))
    @app_commands.describe(
        username=app_commands.locale_str("recent.username"),
        limit=app_commands.locale_str("recent.limit"),
        public=app_commands.locale_str("recent.public"),
    )
    async def recent_command(
        self,
        interaction: discord.Interaction,
        username: str,
        limit: int = 20,
        public: bool = False,
    ):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if limit < 1:
            invalid_limit_msg = i18n.t("errors.validation.invalid_limit", locale)
            await interaction.response.send_message(invalid_limit_msg, ephemeral=not public)
            return
        if limit > 50:
            limit = 50

        await interaction.response.defer(ephemeral=not public)

        try:
            submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, limit)
            if not submissions:
                await interaction.followup.send(
                    i18n.t("errors.validation.no_submissions", locale, username=username),
                    ephemeral=not public,
                )
                return

            first_submission = await self._get_submission_details(submissions[0])
            if not first_submission:
                detail_err_msg = i18n.t("errors.validation.submission_detail_error", locale)
                await interaction.followup.send(detail_err_msg, ephemeral=not public)
                return

            embed = create_submission_embed(
                first_submission, 0, len(submissions), username, bot=self.bot, locale=locale
            )
            view = create_submission_view(first_submission, self.bot, 0, username, len(submissions))

            interaction_cog = self.bot.get_cog("InteractionHandlerCog")
            if interaction_cog:
                cache_key = f"{username}_{interaction.user.id}"
                interaction_cog.submissions_cache[cache_key] = (submissions, time.time(), limit)

            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)
            self.logger.info("Sent user submissions for %s to %s", username, interaction.user.name)

        except Exception as e:
            self.logger.error("Error in recent_command: %s", e, exc_info=True)
            await interaction.followup.send(i18n.t("errors.unexpected", locale, error=e), ephemeral=not public)

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
