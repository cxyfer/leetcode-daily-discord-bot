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
import logging # Added import
from utils.logger import setup_logging # Added import

from leetcode_daily import LeetCodeClient, extract_challenge_info # Updated import
from db_manager import SettingsDatabaseManager

# Get a logger for this module
logger = logging.getLogger(__name__) # Added module logger

load_dotenv(dotenv_path='.env', verbose=True, override=True)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
POST_TIME = os.getenv('POST_TIME', '00:00')  # Default to 00:00
TIMEZONE = os.getenv('TIMEZONE', 'UTC')  # Default to UTC

# Initialize the database manager
db = SettingsDatabaseManager()

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True  # Enable message content permission
bot = commands.Bot(command_prefix="!", intents=intents)

# Schedule tasks are stored here to be cancelled later
schedule_tasks = {}

@bot.event
async def on_ready():
    """When the bot successfully connects to Discord"""
    slash = await bot.tree.sync()  # Sync slash commands

    logger.info(f'{bot.user} has connected to Discord!') # Changed to logger.info
    logger.info(f'Loaded {len(slash)} slash commands') # Changed to logger.info

    # Start the daily schedule tasks
    await schedule_daily_challenges()

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
                logger.info(f"已取消伺服器 {server_id} 的排程任務") # Changed to logger.info
            schedule_tasks.pop(server_id, None)

        # Only create a new schedule for this server, without rescheduling all servers
        server_settings = db.get_server_settings(server_id)
        if server_settings and server_settings.get("channel_id"):
            # 使用 schedule_server_daily_challenge 來建立排程任務
            task = asyncio.create_task(schedule_server_daily_challenge(server_settings))
            schedule_tasks[server_id] = task
        else:
            logger.warning(f"伺服器 {server_id} 未設定頻道或不存在，不創建新排程") # Changed to logger.warning
    else:
        # Reschedule all servers
        for sid, task in list(schedule_tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"已取消伺服器 {sid} 的排程任務") # Changed to logger.info
        schedule_tasks.clear()

        # 使用現有的 schedule_daily_challenges 函數來為所有伺服器建立排程
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
            logger.warning(f"伺服器 {server_id} 未設定頻道，跳過排程") # Changed to logger.warning
            continue

        # If there is already a running task, cancel it
        if server_id in schedule_tasks and not schedule_tasks[server_id].done():
            schedule_tasks[server_id].cancel()
            logger.info(f"已取消伺服器 {server_id} 現有的排程任務") # Changed to logger.info

        # Create task
        task = asyncio.create_task(
            schedule_server_daily_challenge(server)
        )
        schedule_tasks[server_id] = task
        logger.info(f"已為伺服器 {server_id} 創建排程任務") # Changed to logger.info

    logger.info(f"總共為 {len(schedule_tasks)} 個伺服器設定了排程任務") # Changed to logger.info

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
                logger.info(f'伺服器 {server_id}: 下次挑戰時間 {target_time} ({timezone_str})，等待 {wait_hours} 小時 {wait_minutes} 分鐘 {int(wait_seconds % 60)} 秒') # Changed to logger.info

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
                logger.error(f"Server {server_id} schedule task error: {e}", exc_info=True) # Changed to logger.error, added exc_info
                await asyncio.sleep(60)  # Wait 1 minute after error
    except asyncio.CancelledError:
        logger.info(f"Server {server_id} schedule task has been cancelled") # Changed to logger.info
    except Exception as e:
        logger.error(f"Server {server_id} schedule task error: {e}", exc_info=True) # Changed to logger.error, added exc_info
        await asyncio.sleep(10)  # Wait 10 seconds before retrying
        schedule_tasks[server_id] = asyncio.create_task(schedule_server_daily_challenge(server_config))

async def send_daily_challenge(channel_id=None, role_id=None, interaction=None):
    """Get and send the LeetCode daily challenge to the Discord channel"""
    try:
        # Get the current date to create the file path
        timezone = pytz.timezone("UTC")  # **Fix timezone to UTC**
        now = datetime.now(timezone)
        date_str = now.strftime("%Y-%m-%d")
        yy, mm, _ = date_str.split('-')

        # Create the file path and directory
        file_dir = Path(f"data/daily/{yy}/{mm}")
        file_path = file_dir / f"{date_str}.json"

        # Check if there is already a file for today
        info = None
        if file_path.exists():
            logger.info(f"Found existing challenge data at {file_path}") # Changed to logger.info
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing file: {e}", exc_info=True) # Changed to logger.error, added exc_info
                info = None

        # If no valid file is found, fetch the data
        if info is None:
            logger.info("Fetching new challenge data...") # Changed to logger.info
            # Use the new LeetCodeClient
            leetcode_client = LeetCodeClient()
            challenge_data = leetcode_client.fetch_daily_challenge_raw()
            info = extract_challenge_info(challenge_data)
            file_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            logger.info(f"Challenge data saved to {file_path}") # Changed to logger.info

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
            title=f"{info['qid']}. {info['title']}",
            color=embed_color,
            url=info['link']
        )

        # Add fields
        embed.add_field(name="Difficulty", value=info['difficulty'], inline=True)
        embed.add_field(name="Rating", value=f"|| {round(info['rating'])} ||", inline=True)
        if info['tags']:
            tags = ", ".join([f"||{tag}||" for tag in info['tags']])
            embed.add_field(name="Tags", value=tags, inline=True)

        embed.set_footer(text=f"LeetCode Daily Challenge | {info['date']}")

        # Determine how to send the message based on whether there is an interaction object
        if interaction:
            await interaction.followup.send(embed=embed)
            logger.info(f"Sent LeetCode daily challenge as response to slash command") # Changed to logger.info
            return

        # For scheduled messages
        if channel_id:
            channel = bot.get_channel(channel_id)
            if channel:
                # Only mention the role if it's set and not None
                if role_id:
                    await channel.send(f"<@&{role_id}>")

                await channel.send(embed=embed)
                logger.info(f"Sent LeetCode daily challenge to channel {channel_id}") # Changed to logger.info
            else:
                logger.error(f"Failed to get channel {channel_id}") # Changed to logger.error

    except Exception as e:
        logger.error(f"Error sending daily challenge: {e}", exc_info=True) # Changed to logger.error, added exc_info
        if interaction:
            await interaction.followup.send("無法取得 LeetCode 每日挑戰。")

@bot.tree.command(name="daily", description="取得今天的 LeetCode 每日挑戰")
async def daily_command(interaction: discord.Interaction):
    """Slash command to get today's LeetCode challenge"""
    await interaction.response.defer()  # Defer the response, because fetching data may take some time
    await send_daily_challenge(interaction=interaction)

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
            logger.error(f"Failed to set channel for server {interaction.guild_id}") # Added logger.error

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
        logger.error(f"Failed to set role for server {interaction.guild_id}") # Added logger.error

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
        logger.error(f"Failed to set post time for server {interaction.guild_id}") # Added logger.error

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
        logger.error(f"Failed to set timezone for server {interaction.guild_id}") # Added logger.error

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
        title="LeetCode 每日挑戰設定",
        color=0x3498db,
        description=f"此伺服器的 LeetCode 每日挑戰設定如下："
    )

    embed.add_field(name="發送頻道", value=channel_mention, inline=False)
    embed.add_field(name="標記身分組", value=role_mention, inline=False)
    embed.add_field(name="發送時間", value=f"{settings['post_time']} ({settings['timezone']})", inline=False)

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
        logger.info(f"已取消伺服器 {server_id} 的排程任務") # Changed to logger.info

    # Delete the server setting
    success = db.delete_server_settings(server_id)

    if success:
        await interaction.response.send_message("已移除 LeetCode 每日挑戰的設定，將不再在此伺服器發送挑戰。", ephemeral=True)
    else:
        await interaction.response.send_message("移除設定時發生錯誤，請稍後再試。", ephemeral=True)
        logger.error(f"Failed to remove settings for server {server_id}") # Added logger.error

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
    # Setup logging configuration before running the bot
    setup_logging() # Added call
    logger.info("Starting Discord bot...") # Added logger.info
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_bot()