import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from leetcode import LeetCodeClient  # html_to_text 會在 cog 中使用
from llms import GeminiLLM
from utils import SettingsDatabaseManager
from utils.config import (
    EmbeddingModelConfig,
    RewriteModelConfig,
    SimilarConfig,
    get_config,
)
from utils.database import LLMInspireDatabaseManager, LLMTranslateDatabaseManager
from utils.logger import get_core_logger

# from discord.ui import View, Button # Button 和 View 會在 cog 中使用

# Load configuration
try:
    config = get_config()
    logger = get_core_logger()
    logger.info("Configuration loaded from config.toml")

    # Get configuration values
    DISCORD_TOKEN = config.discord_token
    POST_TIME = config.post_time
    TIMEZONE = config.timezone

except FileNotFoundError:
    # Fallback to .env if config.toml doesn't exist
    logger = get_core_logger()
    logger.warning("config.toml not found, falling back to .env file")

    # Load environment variables
    load_dotenv(dotenv_path=".env", verbose=True, override=True)
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    POST_TIME = os.getenv("POST_TIME", "00:00")
    TIMEZONE = os.getenv("TIMEZONE", "UTC")

    # Create a dummy config object for .env compatibility
    class DummyConfig:
        """Compatibility wrapper for .env configuration"""

        def get(self, key, default=None):
            """Get configuration value with .env fallback"""
            if key == "database.path":
                return "data/data.db"
            elif key == "schedule.post_time":
                return POST_TIME
            elif key == "schedule.timezone":
                return TIMEZONE
            return default

        def get_section(self, section):
            """Get configuration section"""
            if section == "logging":
                return {
                    "level": "INFO",
                    "directory": "./logs",
                    "modules": {
                        "bot": "DEBUG",
                        "bot.discord": "DEBUG",
                        "bot.lcus": "DEBUG",
                        "bot.db": "DEBUG",
                        "discord": "WARNING",
                        "discord.gateway": "WARNING",
                        "discord.client": "WARNING",
                        "requests": "WARNING",
                    },
                }
            return {}

        def get_llm_model_config(self, model_type):
            """Get LLM model configuration"""
            if model_type == "standard":
                return {"name": "gemini-2.5-flash", "temperature": 0.0}
            else:
                return {"name": "gemini-2.5-pro", "temperature": 0.0}

        def get_cache_expire_seconds(self, cache_type):
            """Get cache expiration time"""
            return 3600 if cache_type == "translation" else 86400

        def get_embedding_model_config(self):
            """Get embedding model configuration"""
            return EmbeddingModelConfig()

        def get_rewrite_model_config(self):
            """Get rewrite model configuration"""
            return RewriteModelConfig()

        def get_similar_config(self):
            """Get similar problem search configuration"""
            return SimilarConfig()

        @property
        def database_path(self):
            return self.get("database.path", "data/data.db")

        @property
        def discord_token(self):
            return DISCORD_TOKEN

        @property
        def gemini_api_key(self):
            return os.getenv("GOOGLE_GEMINI_API_KEY")

        @property
        def post_time(self):
            return POST_TIME

        @property
        def timezone(self):
            return TIMEZONE

    config = DummyConfig()

# Initialize the database manager
db_path = config.get("database.path", "data/data.db")
db = SettingsDatabaseManager(db_path=db_path)
llm_translate_db = LLMTranslateDatabaseManager(
    db_path=db_path, expire_seconds=config.get_cache_expire_seconds("translation")
)
llm_inspire_db = LLMInspireDatabaseManager(
    db_path=db_path, expire_seconds=config.get_cache_expire_seconds("inspiration")
)

# Initialize LeetCode client
lcus = LeetCodeClient()
lccn = LeetCodeClient(domain="cn")

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True  # Enable message content permission
command_prefix = config.get("bot.command_prefix", "!")
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

# LLM
try:
    gemini_api_key = config.gemini_api_key
    if gemini_api_key and gemini_api_key != "your_google_gemini_api_key_here":
        # Initialize standard model
        standard_config = config.get_llm_model_config("standard")
        llm = GeminiLLM(
            api_key=gemini_api_key,
            model=standard_config.get("name", "gemini-2.5-flash"),
            temperature=standard_config.get("temperature", 0.0),
            max_tokens=standard_config.get("max_tokens"),
            timeout=standard_config.get("timeout"),
            max_retries=standard_config.get("max_retries", 2),
        )

        # Initialize pro model
        pro_config = config.get_llm_model_config("pro")
        llm_pro = GeminiLLM(
            api_key=gemini_api_key,
            model=pro_config.get("name", "gemini-2.5-pro"),
            temperature=pro_config.get("temperature", 0.0),
            max_tokens=pro_config.get("max_tokens"),
            timeout=pro_config.get("timeout"),
            max_retries=pro_config.get("max_retries", 2),
        )
        logger.info("LLM models initialized successfully")
    else:
        logger.warning("Google Gemini API key not configured, LLM features will be disabled")
        llm = None
        llm_pro = None
except Exception as e:
    logger.error(f"Error while initializing LLM: {e}")
    llm = None
    llm_pro = None

# Define a fixed custom ID prefix (這些將作為 bot 的屬性)
LEETCODE_DISCRIPTION_BUTTON_PREFIX = "leetcode_problem_"
LEETCODE_TRANSLATE_BUTTON_PREFIX = "leetcode_translate_"
LEETCODE_INSPIRE_BUTTON_PREFIX = "leetcode_inspire_"
ATCODER_DESCRIPTION_BUTTON_PREFIX = "atcoder_problem|"
ATCODER_TRANSLATE_BUTTON_PREFIX = "atcoder_translate|"
ATCODER_INSPIRE_BUTTON_PREFIX = "atcoder_inspire|"


@bot.event
async def on_ready():
    """Called when the bot is ready"""
    bot.logger.info(f"{bot.user} has connected to Discord!")
    bot.logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    bot.logger.info(f"Discord.py version: {discord.__version__}")
    bot.logger.info(f"Connected to {len(bot.guilds)} guilds")

    try:
        # 確保 Cogs 已載入 (load_extensions 在 main() 中 bot.start() 前呼叫)
        synced = await bot.tree.sync()
        bot.logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        bot.logger.error(f"Failed to sync commands: {e}", exc_info=True)

    # 初始化每日挑戰排程（使用新的 APScheduler 系統）
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
    await bot.process_commands(message)  # 處理前綴指令


@bot.command()
@commands.is_owner()  # 建議加上權限控管
async def load(ctx, extension):
    try:
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"Loaded `{extension}` done.")
        bot.logger.info(f"Loaded extension cogs.{extension} by command.")
    except Exception as e:
        await ctx.send(f"Error loading `{extension}`: {e}")
        bot.logger.error(f"Error loading extension cogs.{extension}: {e}", exc_info=True)


@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    try:
        await bot.unload_extension(f"cogs.{extension}")
        await ctx.send(f"UnLoaded `{extension}` done.")
        bot.logger.info(f"Unloaded extension cogs.{extension} by command.")
    except Exception as e:
        await ctx.send(f"Error unloading `{extension}`: {e}")
        bot.logger.error(f"Error unloading extension cogs.{extension}: {e}", exc_info=True)


@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"ReLoaded `{extension}` done.")
        bot.logger.info(f"Reloaded extension cogs.{extension} by command.")
    except Exception as e:
        await ctx.send(f"Error reloading `{extension}`: {e}")
        bot.logger.error(f"Error reloading extension cogs.{extension}: {e}", exc_info=True)


async def load_extensions():
    if not os.path.exists("./cogs"):
        os.makedirs("./cogs")
        bot.logger.info("Created cogs directory.")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):  # 忽略如 __init__.py
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                bot.logger.info(f"Successfully loaded extension: cogs.{filename[:-3]}")
            except Exception as e:
                bot.logger.error(f"Failed to load extension cogs.{filename[:-3]}: {e}", exc_info=True)


async def main():
    # 全域初始化已在頂部完成
    async with bot:
        # 將共享物件設為 bot 的屬性
        bot.lcus = lcus
        bot.lccn = lccn
        bot.db = db
        bot.llm_translate_db = llm_translate_db
        bot.llm_inspire_db = llm_inspire_db
        bot.llm = llm
        bot.llm_pro = llm_pro
        bot.logger = logger  # logger 已在全域初始化
        # 移除舊的排程任務字典，現在使用 APScheduler
        bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX = LEETCODE_DISCRIPTION_BUTTON_PREFIX
        bot.LEETCODE_TRANSLATE_BUTTON_PREFIX = LEETCODE_TRANSLATE_BUTTON_PREFIX
        bot.LEETCODE_INSPIRE_BUTTON_PREFIX = LEETCODE_INSPIRE_BUTTON_PREFIX
        bot.ATCODER_DESCRIPTION_BUTTON_PREFIX = ATCODER_DESCRIPTION_BUTTON_PREFIX
        bot.ATCODER_TRANSLATE_BUTTON_PREFIX = ATCODER_TRANSLATE_BUTTON_PREFIX
        bot.ATCODER_INSPIRE_BUTTON_PREFIX = ATCODER_INSPIRE_BUTTON_PREFIX

        await load_extensions()
        if not DISCORD_TOKEN:
            bot.logger.critical("DISCORD_TOKEN is not set. Bot cannot start.")
            return

        try:
            await bot.start(DISCORD_TOKEN)
        finally:
            # 確保 APScheduler 優雅關閉
            schedule_cog = bot.get_cog("ScheduleManagerCog")
            if schedule_cog and hasattr(schedule_cog, "shutdown"):
                await schedule_cog.shutdown()
                bot.logger.info("Scheduler shutdown completed.")


if __name__ == "__main__":
    asyncio.run(main())
