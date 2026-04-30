from __future__ import annotations

import importlib
import pkgutil
import re

import discord
from discord.ext import commands

COGS_PACKAGE = "bot.cogs"
_EXTENSION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def discover_cog_extensions(package_name: str = COGS_PACKAGE) -> list[str]:
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return []
    return [
        f"{package_name}.{module_info.name}"
        for module_info in sorted(pkgutil.iter_modules(package_path), key=lambda item: item.name)
        if not module_info.name.startswith("_")
    ]


def normalize_cog_extension_name(extension: str) -> str:
    if not isinstance(extension, str):
        raise ValueError(f"Invalid extension: {extension}")

    candidate = extension.strip()
    if not candidate or "/" in candidate or "\\" in candidate:
        raise ValueError(f"Invalid extension: {extension}")

    parts = candidate.split(".")
    if len(parts) == 1:
        module_name = parts[0]
    elif len(parts) == 3 and parts[0] == "bot" and parts[1] == "cogs":
        module_name = parts[2]
    else:
        raise ValueError(f"Invalid extension: {extension}")

    if not _EXTENSION_NAME_RE.fullmatch(module_name):
        raise ValueError(f"Invalid extension: {extension}")

    return f"{COGS_PACKAGE}.{module_name}"


async def load_extensions(bot: commands.Bot) -> None:
    for extension in discover_cog_extensions():
        try:
            await bot.load_extension(extension)
            bot.logger.info(f"Successfully loaded extension: {extension}")
        except Exception as e:
            bot.logger.error(f"Failed to load extension {extension}: {e}", exc_info=True)


def _create_reschedule_helper(bot: commands.Bot):
    async def reschedule_daily_challenge(server_id: int, context: str = ""):
        schedule_cog = bot.get_cog("ScheduleManagerCog")
        if schedule_cog:
            await schedule_cog.reschedule_daily_challenge(server_id)
        else:
            bot.logger.warning(
                f"ScheduleManagerCog not found during {context} for server {server_id}. "
                "Scheduling may not update immediately."
            )

    return reschedule_daily_challenge


def _register_runtime_handlers(bot: commands.Bot) -> None:
    async def _run_extension_command(
        ctx,
        extension: str,
        method_name: str,
        success_verb: str,
        error_verb: str,
    ) -> None:
        try:
            normalized_extension = normalize_cog_extension_name(extension)
        except ValueError as exc:
            await ctx.send(str(exc))
            return

        try:
            await getattr(bot, method_name)(normalized_extension)
            await ctx.send(f"{success_verb} `{normalized_extension}` done.")
            bot.logger.info(f"{success_verb} extension {normalized_extension} by command.")
        except Exception as e:
            await ctx.send(f"Error {error_verb} `{normalized_extension}`: {e}")
            bot.logger.error(f"Error {error_verb} extension {normalized_extension}: {e}", exc_info=True)

    @bot.event
    async def on_ready():
        bot.logger.info(f"{bot.user} has connected to Discord!")
        bot.logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
        bot.logger.info(f"Discord.py version: {discord.__version__}")
        bot.logger.info(f"Connected to {len(bot.guilds)} guilds")

        try:
            from bot.i18n.translator import BotTranslator

            await bot.tree.set_translator(BotTranslator(bot.i18n))
            synced = await bot.tree.sync()
            bot.logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            bot.logger.error(f"Failed to sync commands: {e}", exc_info=True)

        schedule_cog = bot.get_cog("ScheduleManagerCog")
        if schedule_cog:
            bot.logger.info("Starting APScheduler-based daily challenge scheduling...")
            await schedule_cog.initialize_schedules()
            bot.logger.info("APScheduler daily challenge scheduling initiated.")
        else:
            bot.logger.warning("ScheduleManagerCog not found. Daily challenges will not be scheduled automatically.")

        bot.logger.info("Bot is ready and operational!")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        await bot.process_commands(message)

    @bot.command()
    @commands.is_owner()
    async def load(ctx, extension):
        await _run_extension_command(ctx, extension, "load_extension", "Loaded", "loading")

    @bot.command()
    @commands.is_owner()
    async def unload(ctx, extension):
        await _run_extension_command(ctx, extension, "unload_extension", "Unloaded", "unloading")

    @bot.command()
    @commands.is_owner()
    async def reload(ctx, extension):
        await _run_extension_command(ctx, extension, "reload_extension", "Reloaded", "reloading")


async def create_bot_runtime(*, config, logger):
    from bot.api_client import OjApiClient
    from bot.i18n import I18nService
    from bot.leetcode import LeetCodeClient
    from bot.llms import GeminiLLM
    from bot.utils import SettingsDatabaseManager
    from bot.utils.database import LLMInspireDatabaseManager, LLMTranslateDatabaseManager

    i18n = I18nService(
        default_locale=config.default_locale,
        supported_locales=tuple(config.supported_locales),
    )

    db_path = config.database_path
    db = SettingsDatabaseManager(db_path=db_path)
    llm_translate_db = LLMTranslateDatabaseManager(
        db_path=db_path, expire_seconds=config.get_cache_expire_seconds("translation")
    )
    llm_inspire_db = LLMInspireDatabaseManager(
        db_path=db_path, expire_seconds=config.get_cache_expire_seconds("inspiration")
    )

    lcus = LeetCodeClient()
    api = OjApiClient(config.api_base_url, config.api_token, config.api_timeout)

    intents = discord.Intents.default()
    intents.message_content = True
    command_prefix = config.get("bot.command_prefix", "!")
    bot = commands.Bot(command_prefix=command_prefix, intents=intents)

    llm = None
    llm_pro = None
    try:
        gemini_api_key = config.gemini_api_key
        gemini_base_url = config.gemini_base_url
        if gemini_api_key and gemini_api_key != "your_google_gemini_api_key_here":
            standard_config = config.get_llm_model_config("standard")
            llm = GeminiLLM(
                api_key=gemini_api_key,
                model=standard_config.get("name", "gemini-2.5-flash"),
                temperature=standard_config.get("temperature", 0.0),
                max_tokens=standard_config.get("max_tokens"),
                timeout=standard_config.get("timeout"),
                max_retries=standard_config.get("max_retries", 2),
                base_url=gemini_base_url,
            )

            pro_config = config.get_llm_model_config("pro")
            llm_pro = GeminiLLM(
                api_key=gemini_api_key,
                model=pro_config.get("name", "gemini-2.5-pro"),
                temperature=pro_config.get("temperature", 0.0),
                max_tokens=pro_config.get("max_tokens"),
                timeout=pro_config.get("timeout"),
                max_retries=pro_config.get("max_retries", 2),
                base_url=gemini_base_url,
            )
            logger.info("LLM models initialized successfully")
        else:
            logger.warning("Google Gemini API key not configured, LLM features will be disabled")
    except Exception as e:
        logger.error(f"Error while initializing LLM: {e}")
        llm = None
        llm_pro = None

    _register_runtime_handlers(bot)

    async with bot:
        bot.lcus = lcus
        bot.api = api
        bot.db = db
        bot.llm_translate_db = llm_translate_db
        bot.llm_inspire_db = llm_inspire_db
        bot.llm = llm
        bot.llm_pro = llm_pro
        bot.logger = logger
        bot.config = config
        bot.i18n = i18n
        i18n.set_db_provider(db)

        if not config.discord_token:
            bot.logger.critical("DISCORD_TOKEN is not set. Bot cannot start.")
            return

        await bot.api.start()
        await load_extensions(bot)
        bot.reschedule_daily_challenge = _create_reschedule_helper(bot)

        try:
            await bot.start(config.discord_token)
        finally:
            await bot.api.close()
            schedule_cog = bot.get_cog("ScheduleManagerCog")
            if schedule_cog and hasattr(schedule_cog, "shutdown"):
                await schedule_cog.shutdown()
                bot.logger.info("Scheduler shutdown completed.")
