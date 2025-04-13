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

from leetcode import LeetCodeClient, html_to_text
from llms import GeminiLLM
from utils import SettingsDatabaseManager
from utils.database import LLMTranslateDatabaseManager, LLMInspireDatabaseManager
from discord.ui import View, Button

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
llm_translate_db = LLMTranslateDatabaseManager()
llm_inspire_db = LLMInspireDatabaseManager()

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
    llm_pro = GeminiLLM(model="gemini-2.5-pro-preview-03-25")
except Exception as e:
    logger.error(f"Error while initializing LLM: {e}")
    llm = None
    llm_pro = None

# Schedule tasks are stored here to be cancelled later
schedule_tasks = {}

# Define a fixed custom ID prefix
# LEETCODE_DISCRIPTION_BUTTON_PREFIX = "leetcode_problem_"
LEETCODE_DISCRIPTION_BUTTON_PREFIX = "leetcode_problem_"
LEETCODE_TRANSLATE_BUTTON_PREFIX = "leetcode_translate_"
LEETCODE_INSPIRE_BUTTON_PREFIX = "leetcode_inspire_"
# Global interaction event handler
@bot.event
async def on_interaction(interaction):
    # Ignore non-button interactions
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "")

    # Button for LLM translation
    if custom_id.startswith(LEETCODE_TRANSLATE_BUTTON_PREFIX):
        logger.debug(f"接收到LeetCode LLM翻譯按鈕交互: custom_id={custom_id}")
        try:
            # 先 defer，避免 interaction 過期
            await interaction.response.defer(ephemeral=True)
            parts = custom_id.split("_")
            # 格式: leetcode_translate_{problem_id}_{domain}
            problem_id = parts[2]
            domain = parts[3] if len(parts) > 3 else "com"

            logger.debug(f"嘗試獲取題目並進行LLM翻譯: problem_id={problem_id}, domain={domain}")

            client = lcus if domain == "com" else lccn

            if problem_id and problem_id.isdigit():
                # 先查詢 DB cache
                translation = llm_translate_db.get_translation(int(problem_id), domain)
                if translation:
                    logger.debug(f"從DB取得LLM翻譯: problem_id={problem_id}")
                    await interaction.followup.send(translation, ephemeral=True)
                    return

                problem_info = await client.get_problem(problem_id=problem_id)
                if problem_info and problem_info.get("content"):
                    problem_content = html_to_text(problem_info["content"])
                    # LLM 翻譯
                    try:
                        translation = llm.translate(problem_content, "zh-TW")
                        # 長度限制
                        if len(translation) > 1900:
                            translation = translation[:1900] + "...\n(翻譯內容已截斷)"
                        # 寫入 DB
                        llm_translate_db.save_translation(int(problem_id), domain, translation)
                        await interaction.followup.send(translation, ephemeral=True)
                        logger.debug(f"成功發送LLM翻譯並寫入DB: problem_id={problem_id}")
                    except Exception as llm_e:
                        logger.error(f"LLM 翻譯失敗: {llm_e}", exc_info=True)
                        await interaction.followup.send(f"LLM 翻譯失敗：{str(llm_e)}", ephemeral=True)
                else:
                    logger.warning(f"題目沒有內容: problem_id={problem_id}")
                    await interaction.followup.send("無法獲取題目描述，請前往 LeetCode 網站查看。", ephemeral=True)
            else:
                logger.warning(f"無效的題目ID: {problem_id}")
                await interaction.followup.send("無效的題目ID，無法顯示翻譯。", ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
        except Exception as e:
            logger.error(f"處理LLM翻譯按鈕交互時發生錯誤: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"LLM 翻譯時發生錯誤：{str(e)}", ephemeral=True)
            except:
                pass
        return
    
    # Button for LLM inspire
    def format_inspire_field(val):
        if isinstance(val, list):
            return '\n'.join(f"- {x}" for x in val)
        return str(val)

    INSPIRE_FIELDS = [
        ("thinking", "🧠 思路"),
        ("traps", "⚠️ 陷阱"),
        ("algorithms", "🛠️ 推薦演算法"),
        ("inspiration", "✨ 其他靈感"),
    ]

    if custom_id.startswith(LEETCODE_INSPIRE_BUTTON_PREFIX):
        logger.debug(f"接收到LeetCode 靈感啟發按鈕交互: custom_id={custom_id}")
        try:
            await interaction.response.defer(ephemeral=True)
            parts = custom_id.split("_")
            # 格式: leetcode_inspire_{problem_id}_{domain}
            problem_id = parts[2]
            domain = parts[3] if len(parts) > 3 else "com"

            logger.debug(f"嘗試獲取題目並進行LLM靈感啟發: problem_id={problem_id}, domain={domain}")

            if not problem_id or not problem_id.isdigit():
                logger.warning(f"無效的題目ID: {problem_id}")
                await interaction.followup.send("無效的題目ID，無法顯示靈感啟發。", ephemeral=True)
                return

            inspire_result = llm_inspire_db.get_inspire(int(problem_id), domain)
            if inspire_result:
                logger.debug(f"Get inspire result from DB: problem_id={problem_id}")
            else:
                client = lcus if domain == "com" else lccn
                problem_info = await client.get_problem(problem_id=problem_id)
                if problem_info and problem_info.get("content"):
                    problem_content = html_to_text(problem_info["content"])
                    tags = problem_info.get("tags", [])
                    difficulty = problem_info.get("difficulty", "")
                else:
                    logger.warning(f"題目沒有內容: problem_id={problem_id}")
                    await interaction.followup.send("無法獲取題目資訊。", ephemeral=True)
                    return
                
                # Get inspire result from LLM
                try:
                    inspire_result = llm_pro.inspire(problem_content, tags, difficulty)
                    if not isinstance(inspire_result, dict) or not all(k in inspire_result for k in ["thinking", "traps", "algorithms", "inspiration"]):
                        # 回傳原始 LLM 回覆
                        raw = inspire_result.get("raw", inspire_result)
                        if len(str(raw)) > 1900:
                            raw = str(raw)[:1900] + "...\n(內容已截斷)"
                        await interaction.followup.send(str(raw), ephemeral=True)
                        logger.debug(f"發送原始 LLM 靈感回覆: problem_id={problem_id}")
                        return
                    # --- DB cache: save inspire result ---
                    formatted_fields = [format_inspire_field(inspire_result[k]) for k, _ in INSPIRE_FIELDS]
                    llm_inspire_db.save_inspire(
                        int(problem_id), domain,
                        *formatted_fields
                    )
                except Exception as llm_e:
                    logger.error(f"LLM 靈感啟發失敗: {llm_e}", exc_info=True)
                    await interaction.followup.send(f"LLM 靈感啟發失敗：{str(llm_e)}", ephemeral=True)
                    return
            
            embed = discord.Embed(
                title="💡 靈感啟發",
                color=0x8e44ad,
            )
            total_len = 0
            for key, field_name in INSPIRE_FIELDS:
                val = format_inspire_field(inspire_result.get(key, ""))
                embed.add_field(name=field_name, value=val, inline=False)
                total_len += len(val)
            if total_len > 1800:
                embed.set_footer(text="內容已截斷，請嘗試更精簡提示。")
            await interaction.followup.send(embed=embed, ephemeral=True)
           
        except discord.errors.InteractionResponded:
            await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
        except Exception as e:
            logger.error(f"處理LLM靈感啟發按鈕交互時發生錯誤: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"LLM 靈感啟發時發生錯誤：{str(e)}", ephemeral=True)
            except:
                pass
        return

    # Button for displaying LeetCode problem description
    if custom_id.startswith(LEETCODE_DISCRIPTION_BUTTON_PREFIX):
        logger.debug(f"接收到LeetCode按鈕交互: custom_id={custom_id}")
        
        # Parse problem ID and domain
        try:
            parts = custom_id.split("_")
            problem_id = parts[2]
            domain = parts[3] if len(parts) > 3 else "com"
            
            logger.debug(f"嘗試獲取題目: problem_id={problem_id}, domain={domain}")
            
            # Select client based on domain
            client = lcus if domain == "com" else lccn
            
            # Get problem from API
            if problem_id and problem_id.isdigit():
                problem_info = await client.get_problem(problem_id=problem_id)
                
                if problem_info and problem_info.get("content"):
                    problem_content = html_to_text(problem_info["content"])
                    
                    # Limit character count
                    if len(problem_content) > 1900:
                        problem_content = problem_content[:1900] + "...\n(內容已截斷，請前往 LeetCode 網站查看完整題目)"
                    
                    emoji = {'Easy': '🟢', 'Medium': '🟡', 'Hard': '🔴'}.get(problem_info['difficulty'], '')
                    # Add title and difficulty
                    problem_content = f"# {emoji} [{problem_info['id']}. {problem_info['title']}]({problem_info['link']}) ({problem_info['difficulty']})\n\n{problem_content}"
                    
                    logger.debug(f"成功獲取題目內容: length={len(problem_content)}")
                else:
                    problem_content = "無法獲取題目描述，請前往 LeetCode 網站查看。"
                    logger.warning(f"題目沒有內容: problem_id={problem_id}")
            else:
                problem_content = "無效的題目ID，無法顯示題目描述。"
                logger.warning(f"無效的題目ID: {problem_id}")
            
            # Respond to interaction
            await interaction.response.send_message(problem_content, ephemeral=True)
            logger.debug(f"成功發送題目描述: problem_id={problem_id}")
            
        except discord.errors.InteractionResponded:
            await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
        except Exception as e:
            logger.error(f"處理按鈕交互時發生錯誤: {e}", exc_info=True)
            try:
                await interaction.response.send_message(f"顯示題目時發生錯誤：{str(e)}", ephemeral=True)
            except:
                try:
                    await interaction.followup.send(f"顯示題目時發生錯誤：{str(e)}", ephemeral=True)
                except:
                    pass

@bot.event
async def on_ready():
    """When the bot successfully connects to Discord"""
    logger.info(f'開始同步 slash 命令...')
    slash = await bot.tree.sync()  # Sync slash commands
    
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Loaded {len(slash)} slash commands')
    
    # Start the daily schedule tasks
    logger.info(f'開始排程每日挑戰任務...')
    await schedule_daily_challenges()
    logger.info(f'排程每日挑戰任務完成')

async def reschedule_daily_challenge(server_id=None):
    """Reschedule the daily challenge task
    
    Args:
        server_id (int, optional): The server ID to reschedule, if None, reschedule all servers
    """
    global schedule_tasks
    
    if server_id is not None:
        # Only reschedule the specified server
        if server_id in schedule_tasks:
            task = schedule_tasks[server_id]
            if not task.done():
                task.cancel()
                logger.info(f"Server {server_id} schedule task cancelled")
            schedule_tasks.pop(server_id, None)
            
        server_settings = db.get_server_settings(server_id)
        if server_settings and server_settings.get("channel_id"):
            task = asyncio.create_task(schedule_server_daily_challenge(server_settings))
            schedule_tasks[server_id] = task
        else:
            logger.info(f"Server {server_id} not set channel or not exist, not create new schedule")
    else:
        # Reschedule all servers
        for sid, task in list(schedule_tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Server {sid} schedule task cancelled")
        schedule_tasks.clear()
        await schedule_daily_challenges()

async def schedule_daily_challenges():
    """Schedule daily LeetCode challenges for all servers"""
    # Get all server settings
    servers = db.get_all_servers()
    
    # Create schedule tasks for each server
    for server in servers:
        server_id = server.get("server_id")
        channel_id = server.get("channel_id")
        
        # Ensure server_id is not None
        if not server_id:
            continue
            
        # If the server doesn't have a channel setting, skip
        if not channel_id:
            logger.info(f"Server {server_id} not set channel, skip schedule")
            continue
        
        # If there is already a running task, cancel it
        if server_id in schedule_tasks and not schedule_tasks[server_id].done():
            schedule_tasks[server_id].cancel()
            logger.info(f"Server {server_id} existing schedule task cancelled")
        
        # Create task
        task = asyncio.create_task(
            schedule_server_daily_challenge(server)
        )
        schedule_tasks[server_id] = task
        logger.info(f"Server {server_id} schedule task created")
    
    logger.info(f"Total {len(schedule_tasks)} schedule tasks created")

async def schedule_server_daily_challenge(server_config, offset_seconds=10):
    """Schedule daily LeetCode challenges for a single server
    
    Args:
        server_config (dict): Server configuration, containing server_id, channel_id, role_id, post_time, timezone
    """
    server_id = server_config.get("server_id")
    channel_id = server_config.get("channel_id")
    role_id = server_config.get("role_id")
    post_time = server_config.get("post_time", POST_TIME)
    timezone_str = server_config.get("timezone", TIMEZONE)

    try:
        while True:
            # Parse timezone and time
            try:
                timezone = pytz.timezone(timezone_str)
                now = datetime.now(pytz.UTC).astimezone(timezone)
                hour, minute = map(int, post_time.split(':'))
                
                # Calculate next run time
                target_time = now.replace(hour=hour, minute=minute, second=offset_seconds, microsecond=0)
                if now >= target_time:
                    # If today's time has passed, schedule for tomorrow
                    target_time = target_time + timedelta(days=1)
                
                # Convert back to UTC for scheduling
                target_time_utc = target_time.astimezone(pytz.UTC)
                wait_seconds = (target_time_utc - datetime.now(pytz.UTC)).total_seconds()
                wait_minutes = int((wait_seconds // 60) % 60)
                wait_hours = int(wait_seconds // 3600)
                logger.info(f'Server {server_id}: Next challenge time {target_time} ({timezone_str}), waiting {wait_hours} hours {wait_minutes} minutes {int(wait_seconds % 60)} seconds')
                
                # Wait until the next schedule
                await asyncio.sleep(wait_seconds)
                
                # Send the challenge
                await send_daily_challenge(
                    channel_id=channel_id,
                    role_id=role_id
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Server {server_id} schedule task error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute after error
    except asyncio.CancelledError:
        logger.debug(f"Server {server_id} schedule task has been cancelled")
    except Exception as e:
        logger.error(f"Server {server_id} schedule task error: {e}")
        await asyncio.sleep(10)  # Wait 10 seconds before retrying
        schedule_tasks[server_id] = asyncio.create_task(schedule_server_daily_challenge(server_config))

async def send_daily_challenge(channel_id=None, role_id=None, interaction=None, domain="com"):
    """Get and send the LeetCode daily challenge to the Discord channel"""
    try:
        logger.info(f"開始獲取每日挑戰: domain={domain}, channel_id={channel_id}, interaction_id={interaction.id if interaction else None}")
        
        client = lcus if domain == "com" else lccn

        timezone = pytz.timezone(client.time_zone)
        now = datetime.now(timezone)
        date_str = now.strftime("%Y-%m-%d")
        logger.debug(f"獲取日期: {date_str}, timezone: {client.time_zone}")
        
        # Get challenge information from leetcode_daily module
        logger.debug(f"開始從 LeetCode 獲取挑戰: {date_str}")
        info = await client.get_daily_challenge(date_str)
        logger.debug(f"獲取挑戰成功: id={info['id']}, title={info['title']}")

        # Set the color based on the difficulty
        color_map = {
            'Easy': 0x00FF00,  # Green
            'Medium': 0xFFA500,  # Orange
            'Hard': 0xFF0000,  # Red
        }
        emoji_map = {
            'Easy': '🟢',
            'Medium': '🟡',
            'Hard': '🔴',
        }
        embed_color = color_map.get(info['difficulty'], 0x0099FF)
        
        # Create a Discord embed message
        embed = discord.Embed(
            title=f"🔗 {info['id']}. {info['title']}",
            color=embed_color,
            url=info['link']
        )

        # Add links to solve on both platforms
        if domain == "com":
            cn_link = info['link'].replace("leetcode.com", "leetcode.cn")
            embed.description = f"You can also solve it on [LCCN (leetcode.cn)]({cn_link}) !"
        else:
            us_link = info['link'].replace("leetcode.cn", "leetcode.com")
            embed.description = f"You can also solve it on [LCUS (leetcode.com)]({us_link}) !"

        # Add fields
        embed.add_field(name="🔥 Difficulty", value=f"**{info['difficulty']}**", inline=True)
        if round(info['rating']) > 0:
            embed.add_field(name="⭐ Rating", value=f"**{round(info['rating'])}**", inline=True)
        embed.add_field(name="📈 AC Rate", value=f"**{round(info['ac_rate'], 2)}%**", inline=True)
        if info['tags']:    
            tags = ", ".join([f"|| *{tag}* ||" for tag in info['tags']])
            embed.add_field(name="🏷️ Tags", value=tags, inline=False)
        if info['similar_questions']:
            similar_questions = []
            for question in info['similar_questions']:
                sqi = await client.get_problem(slug=question['titleSlug'])
                similar_questions.append(f"- {emoji_map[sqi['difficulty']]} [{sqi['id']}. {sqi['title']}]({sqi['link']})" + (f" *{round(sqi['rating'], 2)}*" if sqi['rating'] > 0 else ""))
            embed.add_field(name="🔍 Similar Questions", value="\n".join(similar_questions), inline=False)

        embed.set_footer(text=f"LeetCode Daily Challenge ｜ {info['date']}", icon_url="https://leetcode.com/static/images/LeetCode_logo.png")

        # Create a view containing the button
        view = discord.ui.View(timeout=None)

        # Create a button for displaying the problem description
        description_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="題目描述",
            emoji="📖",
            custom_id=f"{LEETCODE_DISCRIPTION_BUTTON_PREFIX}{info['id']}_{domain}"
        )
        view.add_item(description_button)

        # Add LLM translation button
        translate_custom_id = f"{LEETCODE_TRANSLATE_BUTTON_PREFIX}{info['id']}_{domain}"
        translate_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="LLM 翻譯",
            emoji="🌐",
            custom_id=translate_custom_id
        )
        view.add_item(translate_button)
    
        # Add LLM inspire button
        inspire_custom_id = f"{LEETCODE_INSPIRE_BUTTON_PREFIX}{info['id']}_{domain}"
        inspire_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="靈感啟發",
            emoji="💡",
            custom_id=inspire_custom_id
        )
        view.add_item(inspire_button)

        # Determine how to send the message
        if interaction:
            logger.debug(f"通過互動發送訊息: interaction_id={interaction.id}")
            await interaction.followup.send(embed=embed, view=view)
            logger.info(f"成功發送每日挑戰到互動: interaction_id={interaction.id}")
            return
            
        # For scheduled messages
        if channel_id:
            logger.debug(f"獲取頻道: channel_id={channel_id}")
            channel = bot.get_channel(channel_id)
            if channel:
                mention_content = f"<@&{role_id}>" if role_id else None
                logger.debug(f"發送訊息到頻道: channel_id={channel_id}, mention={mention_content is not None}")
                await channel.send(content=mention_content, embed=embed, view=view)
                logger.info(f"成功發送每日挑戰到頻道: channel_id={channel_id}")
            else:
                logger.warning(f"無法獲取頻道: channel_id={channel_id}")
    
    except Exception as e:
        logger.error(f"獲取/發送每日挑戰時出錯: {e}", exc_info=True)
        if interaction:
            await interaction.followup.send("無法取得 LeetCode 每日挑戰。")

@bot.tree.command(name="daily", description="取得今天的 LeetCode 每日挑戰 (LCUS)")
async def daily_command(interaction: discord.Interaction):
    """Slash command to get today's LeetCode challenge"""
    await interaction.response.defer()  # Defer the response, because fetching data may take some time
    await send_daily_challenge(interaction=interaction, domain="com")

@bot.tree.command(name="daily_cn", description="取得今天的 LeetCode 每日挑戰 (LCCN)")
async def daily_cn_command(interaction: discord.Interaction):
    """Slash command to get today's LeetCode challenge"""
    await interaction.response.defer()  # Defer the response, because fetching data may take some time
    await send_daily_challenge(interaction=interaction, domain="cn")

@bot.tree.command(name="set_channel", description="設定 LeetCode 每日挑戰的發送頻道")
@app_commands.describe(channel="選擇要發送每日挑戰的頻道")
async def set_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel for sending the daily LeetCode challenge"""
    # Check if the user has manage channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("你需要「管理頻道」權限才能設定發送頻道。", ephemeral=True)
        return
    
    # Update the database
    success = db.set_channel(interaction.guild_id, channel.id)
    
    if success:
        await interaction.response.send_message(f"已將 LeetCode 每日挑戰的發送頻道設為 {channel.mention}。", ephemeral=True)
        # Immediately reschedule
        await reschedule_daily_challenge(interaction.guild_id)
    else:
        # If the server doesn't have a setting, create a new one
        success = db.set_server_settings(interaction.guild_id, channel.id)
        if success:
            await interaction.response.send_message(f"已將 LeetCode 每日挑戰的發送頻道設為 {channel.mention}。", ephemeral=True)
            # Immediately reschedule
            await reschedule_daily_challenge(interaction.guild_id)
        else:
            await interaction.response.send_message("設定頻道時發生錯誤，請稍後再試。", ephemeral=True)

@bot.tree.command(name="set_role", description="設定 LeetCode 每日挑戰要標記的身分組")
@app_commands.describe(role="選擇要標記的身分組")
async def set_role_command(interaction: discord.Interaction, role: discord.Role):
    """Set the role to mention for the daily LeetCode challenge"""
    # Check if the user has manage roles permission
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("你需要「管理身分組」權限才能設定標記的身分組。", ephemeral=True)
        return
    
    # Check if the channel is set
    settings = db.get_server_settings(interaction.guild_id)
    if not settings:
        await interaction.response.send_message("請先使用 `/set_channel` 設定發送頻道。", ephemeral=True)
        return
    
    # Update the database
    success = db.set_role(interaction.guild_id, role.id)
    
    if success:
        await interaction.response.send_message(f"已將 LeetCode 每日挑戰要標記的身分組設為 {role.mention}。", ephemeral=True)
        # Immediately reschedule
        await reschedule_daily_challenge(interaction.guild_id)
    else:
        await interaction.response.send_message("設定身分組時發生錯誤，請稍後再試。", ephemeral=True)

@bot.tree.command(name="set_post_time", description="設定 LeetCode 每日挑戰的發送時間")
@app_commands.describe(time="發送時間 (格式: HH:MM，例如 08:00)")
async def set_post_time_command(interaction: discord.Interaction, time: str):
    """Set the time for sending the daily LeetCode challenge"""
    # Check if the user has manage guild permission
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("你需要「管理伺服器」權限才能設定發送時間。", ephemeral=True)
        return
    
    # Validate the time format
    try:
        hour, minute = map(int, time.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time")
    except:
        await interaction.response.send_message("時間格式無效，請使用 HH:MM 格式（例如 08:00）。", ephemeral=True)
        return
    
    # Check if the channel is set
    settings = db.get_server_settings(interaction.guild_id)
    if not settings:
        await interaction.response.send_message("請先使用 `/set_channel` 設定發送頻道。", ephemeral=True)
        return
    
    # Update the database
    success = db.set_post_time(interaction.guild_id, time)
    
    if success:
        await interaction.response.send_message(f"已將 LeetCode 每日挑戰的發送時間設為 {time}。", ephemeral=True)
        # Immediately reschedule
        await reschedule_daily_challenge(interaction.guild_id)
    else:
        await interaction.response.send_message("設定發送時間時發生錯誤，請稍後再試。", ephemeral=True)

@bot.tree.command(name="set_timezone", description="設定 LeetCode 每日挑戰的發送時區")
@app_commands.describe(timezone="時區名稱 (例如: Asia/Taipei)")
async def set_timezone_command(interaction: discord.Interaction, timezone: str):
    """Set the timezone for sending the daily LeetCode challenge"""
    # Check if the user has manage guild permission
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("你需要「管理伺服器」權限才能設定時區。", ephemeral=True)
        return
    
    # Validate the timezone name
    try:
        tz = pytz.timezone(timezone)
    except:
        await interaction.response.send_message("時區名稱無效，請使用有效的時區名稱（例如 Asia/Taipei）。", ephemeral=True)
        return
    
    # Check if the channel is set
    settings = db.get_server_settings(interaction.guild_id)
    if not settings:
        await interaction.response.send_message("請先使用 `/set_channel` 設定發送頻道。", ephemeral=True)
        return
    
    # Update the database
    success = db.set_timezone(interaction.guild_id, timezone)
    
    if success:
        await interaction.response.send_message(f"已將 LeetCode 每日挑戰的發送時區設為 {timezone}。", ephemeral=True)
        # Immediately reschedule
        await reschedule_daily_challenge(interaction.guild_id)
    else:
        await interaction.response.send_message("設定時區時發生錯誤，請稍後再試。", ephemeral=True)

@bot.tree.command(name="show_settings", description="顯示目前伺服器的 LeetCode 挑戰設定")
async def show_settings_command(interaction: discord.Interaction):
    """Show the current server settings for the LeetCode challenge"""
    settings = db.get_server_settings(interaction.guild_id)
    
    if not settings:
        await interaction.response.send_message("此伺服器尚未設定 LeetCode 每日挑戰。使用 `/set_channel` 開始設定。", ephemeral=True)
        return
    
    channel = bot.get_channel(settings["channel_id"])
    channel_mention = channel.mention if channel else f"找不到頻道 (ID: {settings['channel_id']})"
    
    role_mention = "未設定"
    if settings["role_id"]:
        role = interaction.guild.get_role(settings["role_id"])
        role_mention = role.mention if role else f"找不到身分組 (ID: {settings['role_id']})"
    
    embed = discord.Embed(
        title="LeetCode 每日一題挑戰設定",
        color=0x3498db,
        description=f"此伺服器的 LeetCode 每日一題挑戰設定如下："
    )
    
    embed.add_field(name="發送頻道", value=channel_mention, inline=False)
    embed.add_field(name="標記身分組", value=role_mention, inline=False)
    embed.add_field(name="發送時間", value=f"{settings['post_time']} ({settings['timezone']})", inline=False)

    logger.debug(f"Server {interaction.guild_id} settings: {settings}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="remove_channel", description="移除頻道設定，停止在此伺服器發送 LeetCode 每日挑戰")
async def remove_channel_command(interaction: discord.Interaction):
    """Remove the channel setting for this server, stopping daily challenges"""
    # Check if the user has manage channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("你需要「管理頻道」權限才能移除發送頻道設定。", ephemeral=True)
        return
    
    # Check if there is already a setting
    settings = db.get_server_settings(interaction.guild_id)
    if not settings:
        await interaction.response.send_message("此伺服器尚未設定 LeetCode 每日挑戰，無需移除。", ephemeral=True)
        return
    
    # Get the server ID
    server_id = interaction.guild_id
    
    # If there is a running schedule task, cancel it
    global schedule_tasks
    if server_id in schedule_tasks and not schedule_tasks[server_id].done():
        schedule_tasks[server_id].cancel()
        schedule_tasks.pop(server_id)
        logger.info(f"Server {server_id} schedule task cancelled")
    
    # Delete the server setting
    success = db.delete_server_settings(server_id)
    
    if success:
        logger.info(f"Server {server_id} settings removed")
        await interaction.response.send_message("已移除 LeetCode 每日挑戰的設定，將不再在此伺服器發送挑戰。", ephemeral=True)
    else:
        await interaction.response.send_message("移除設定時發生錯誤，請稍後再試。", ephemeral=True)

@bot.event
async def on_message(message):
    """Process user messages"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Keep the original command functionality
    await bot.process_commands(message)

# Run the bot
def run_bot():
    """Run the Discord bot"""
    logger.info("Starting LeetCode Daily Discord Bot...")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_bot()