import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import pytz
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import logging
from utils.logger import setup_logging, get_logger

from leetcode import LeetCodeClient # html_to_text 會在 cog 中使用
from llms import GeminiLLM
from utils import SettingsDatabaseManager
from utils.database import LLMTranslateDatabaseManager, LLMInspireDatabaseManager
# from discord.ui import View, Button # Button 和 View 會在 cog 中使用

# Set up logging
setup_logging()
logger = get_logger("bot")

# Load environment variables
load_dotenv(dotenv_path='.env', verbose=True, override=True)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
POST_TIME = os.getenv('POST_TIME', '00:00')  # Default to 00:00
TIMEZONE = os.getenv('TIMEZONE', 'UTC')  # Default to UTC

# Initialize the database manager
db = SettingsDatabaseManager()
llm_translate_db = LLMTranslateDatabaseManager(expire_seconds=3600)
llm_inspire_db = LLMInspireDatabaseManager(expire_seconds=86400)

# Initialize LeetCode client
lcus = LeetCodeClient()
lccn = LeetCodeClient(domain="cn")

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True  # Enable message content permission
bot = commands.Bot(command_prefix="!", intents=intents)

# LLM
try:
    llm = GeminiLLM(model="gemini-2.0-flash")
    llm_pro = GeminiLLM(model="gemini-2.5-pro-preview-05-06")
except Exception as e:
    logger.error(f"Error while initializing LLM: {e}")
    llm = None
    llm_pro = None

# Define a fixed custom ID prefix (這些將作為 bot 的屬性)
LEETCODE_DISCRIPTION_BUTTON_PREFIX = "leetcode_problem_"
LEETCODE_TRANSLATE_BUTTON_PREFIX = "leetcode_translate_"
LEETCODE_INSPIRE_BUTTON_PREFIX = "leetcode_inspire_"

@bot.event
async def on_ready():
    bot.logger.info(f'{bot.user} has connected to Discord!')
    try:
        # 確保 Cogs 已載入 (load_extensions 在 main() 中 bot.start() 前呼叫)
        synced = await bot.tree.sync()
        bot.logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        bot.logger.error(f"Failed to sync commands: {e}", exc_info=True)

    # 初始化每日挑戰排程
    schedule_cog = bot.get_cog("ScheduleManagerCog") # Cog 的類別名稱
    if schedule_cog:
        bot.logger.info(f'Starting daily challenge scheduling...')
        await schedule_cog.initialize_schedules() # 假設 ScheduleManagerCog 中有此方法
        bot.logger.info(f'Daily challenge scheduling initiated.')
    else:
        bot.logger.warning("ScheduleManagerCog not found. Daily challenges will not be scheduled automatically.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message) # 處理前綴指令

@bot.command()
@commands.is_owner() # 建議加上權限控管
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
        if filename.endswith(".py") and not filename.startswith("_"): # 忽略如 __init__.py
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
        bot.logger = logger # logger 已在全域初始化
        bot.schedule_tasks = {} # 初始化空的排程任務字典
        bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX = LEETCODE_DISCRIPTION_BUTTON_PREFIX
        bot.LEETCODE_TRANSLATE_BUTTON_PREFIX = LEETCODE_TRANSLATE_BUTTON_PREFIX
        bot.LEETCODE_INSPIRE_BUTTON_PREFIX = LEETCODE_INSPIRE_BUTTON_PREFIX
        
        await load_extensions()
        if not DISCORD_TOKEN:
            bot.logger.critical("DISCORD_TOKEN is not set. Bot cannot start.")
            return
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())