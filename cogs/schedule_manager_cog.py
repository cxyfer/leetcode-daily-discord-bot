# cogs/schedule_manager_cog.py
import asyncio
import discord
from discord.ext import commands
import pytz
from datetime import datetime, timedelta
import os # For os.getenv

# Default values, similar to how they are defined in bot.py
# These are used if a server doesn't have specific settings.
DEFAULT_POST_TIME = os.getenv('POST_TIME', '00:00')
DEFAULT_TIMEZONE = os.getenv('TIMEZONE', 'UTC')

class ScheduleManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger

    async def initialize_schedules(self):
        """Schedule daily LeetCode challenges for all servers."""
        self.logger.info("Initializing daily challenge schedules for all servers...")
        servers = self.bot.db.get_all_servers()
        
        count = 0
        for server_settings in servers:
            server_id = server_settings.get("server_id")
            if not server_id:
                self.logger.warning(f"Server settings found with no server_id: {server_settings}")
                continue
            
            if not server_settings.get("channel_id"):
                self.logger.info(f"Server {server_id} has no channel_id set, skipping schedule.")
                continue

            # If there is already a running task, cancel it before creating a new one
            if server_id in self.bot.schedule_tasks:
                task = self.bot.schedule_tasks[server_id]
                if not task.done():
                    task.cancel()
                    self.logger.info(f"Cancelled existing schedule task for server {server_id} to reschedule.")
            
            task = asyncio.create_task(self.schedule_server_daily_challenge(server_settings))
            self.bot.schedule_tasks[server_id] = task
            self.logger.info(f"Scheduled daily challenge for server {server_id} in channel {server_settings.get('channel_id')}.")
            count += 1
        
        self.logger.info(f"Total {count} server schedule tasks created/updated.")

    async def reschedule_daily_challenge(self, server_id: int = None):
        """Reschedule the daily challenge task for a specific server or all servers."""
        if server_id is not None:
            self.logger.info(f"Rescheduling daily challenge for server {server_id}...")
            if server_id in self.bot.schedule_tasks:
                task = self.bot.schedule_tasks[server_id]
                if not task.done():
                    task.cancel()
                    self.logger.info(f"Server {server_id} existing schedule task cancelled for rescheduling.")
                # Remove from dict, will be re-added if settings are valid
                self.bot.schedule_tasks.pop(server_id, None) 
            
            server_settings = self.bot.db.get_server_settings(server_id)
            if server_settings and server_settings.get("channel_id"):
                new_task = asyncio.create_task(self.schedule_server_daily_challenge(server_settings))
                self.bot.schedule_tasks[server_id] = new_task
                self.logger.info(f"Server {server_id} daily challenge has been rescheduled.")
            else:
                self.logger.info(f"Server {server_id} has no channel_id set or settings not found, schedule removed/not created.")
        else:
            self.logger.info("Rescheduling daily challenges for ALL servers...")
            # Cancel all existing tasks
            for sid, task in list(self.bot.schedule_tasks.items()): # Iterate over a copy
                if not task.done():
                    task.cancel()
                    self.logger.info(f"Server {sid} schedule task cancelled for full reschedule.")
            self.bot.schedule_tasks.clear()
            await self.initialize_schedules() # Re-initialize all schedules
            self.logger.info("All server daily challenges have been rescheduled.")

    async def schedule_server_daily_challenge(self, server_config: dict, offset_seconds: int = 10):
        """Continuously schedule daily LeetCode challenges for a single server."""
        server_id = server_config.get("server_id")
        channel_id = server_config.get("channel_id")
        
        if not channel_id: # Should be caught by initialize_schedules, but as a safeguard
            self.logger.error(f"Attempted to schedule for server {server_id} but no channel_id was provided in config.")
            return

        self.logger.info(f"Starting schedule loop for server {server_id} (Channel: {channel_id}).")
        try:
            while True:
                # These fall back to global defaults if not in server_config
                post_time_str = server_config.get("post_time", DEFAULT_POST_TIME)
                timezone_str = server_config.get("timezone", DEFAULT_TIMEZONE)
                role_id = server_config.get("role_id") # Can be None

                try:
                    target_timezone = pytz.timezone(timezone_str)
                    now_in_target_tz = datetime.now(pytz.UTC).astimezone(target_timezone)
                    
                    hour, minute = map(int, post_time_str.split(':'))
                    
                    target_datetime_today = now_in_target_tz.replace(hour=hour, minute=minute, second=offset_seconds, microsecond=0)
                    
                    if now_in_target_tz >= target_datetime_today:
                        target_datetime = target_datetime_today + timedelta(days=1)
                    else:
                        target_datetime = target_datetime_today
                    
                    target_datetime_utc = target_datetime.astimezone(pytz.UTC)
                    now_utc = datetime.now(pytz.UTC)
                    
                    wait_seconds = (target_datetime_utc - now_utc).total_seconds()

                    if wait_seconds < 0: # Should not happen if logic is correct, but as a safeguard
                        self.logger.warning(f"Server {server_id}: Calculated wait_seconds is negative ({wait_seconds}s). Scheduling for next day + 5 mins.")
                        wait_seconds = ((target_datetime_today + timedelta(days=1)).astimezone(pytz.UTC) - now_utc).total_seconds() + 300
                        if wait_seconds < 0: wait_seconds = 300 # Absolute fallback

                    wait_h = int(wait_seconds // 3600)
                    wait_m = int((wait_seconds % 3600) // 60)
                    wait_s = int(wait_seconds % 60)
                    self.logger.info(f"Server {server_id}: Next challenge at {target_datetime.strftime('%Y-%m-%d %H:%M:%S')} {timezone_str}. Waiting for {wait_h}h {wait_m}m {wait_s}s.")
                    
                    await asyncio.sleep(wait_seconds)
                    
                    self.logger.info(f"Server {server_id}: Time to send daily challenge in channel {channel_id}.")
                    await self.send_daily_challenge(
                        channel_id=int(channel_id), # Ensure channel_id is int
                        role_id=int(role_id) if role_id else None # Ensure role_id is int or None
                    )
                
                except asyncio.CancelledError:
                    self.logger.info(f"Schedule task for server {server_id} was cancelled normally.")
                    raise # Re-raise to stop the loop
                except pytz.exceptions.UnknownTimeZoneError:
                    self.logger.error(f"Server {server_id}: Invalid timezone '{timezone_str}'. Using UTC as fallback. Please correct server settings.")
                    server_config["timezone"] = "UTC" # Use UTC for next iteration to avoid loop error
                    await asyncio.sleep(60) # Wait a bit before retrying with UTC
                except ValueError: # For post_time split
                    self.logger.error(f"Server {server_id}: Invalid post_time format '{post_time_str}'. Using '00:00' as fallback. Please correct server settings.")
                    server_config["post_time"] = "00:00"
                    await asyncio.sleep(60)
                except Exception as e:
                    self.logger.error(f"Server {server_id}: Error in scheduling loop: {e}", exc_info=True)
                    await asyncio.sleep(60) # Wait 1 minute after an unexpected error
        
        except asyncio.CancelledError:
            self.logger.info(f"Schedule task for server {server_id} has been definitively cancelled.")
        except Exception as e: # Catch-all for unexpected exit from while True
            self.logger.error(f"Server {server_id}: Schedule task CRASHED: {e}", exc_info=True)
            # Optionally, try to reschedule itself after a delay if it's a persistent error
            # For now, it will just exit. A new reschedule command would be needed.
            if server_id in self.bot.schedule_tasks:
                 del self.bot.schedule_tasks[server_id] # Remove broken task

    async def send_daily_challenge(self, channel_id: int = None, role_id: int = None, interaction: discord.Interaction = None, domain: str = "com"):
        """Fetches and sends the LeetCode daily challenge."""
        try:
            self.logger.info(f"Attempting to send daily challenge. Domain: {domain}, Channel: {channel_id}, Interaction: {'Yes' if interaction else 'No'}")
            
            current_client = self.bot.lcus if domain == "com" else self.bot.lccn
            
            # Determine date string based on LeetCode's server timezone for daily challenges
            # LeetCode daily challenges reset at UTC 00:00.
            # So, we can just use UTC date.
            now_utc = datetime.now(pytz.UTC)
            date_str = now_utc.strftime("%Y-%m-%d")
            # If it's just past midnight UTC, LC might not have updated its daily Q for the *new* day yet.
            # It's safer to get "today's" question based on its own API for "daily challenge"
            # The get_daily_challenge method in LeetCodeClient should handle this.
            # We pass date_str for consistency if the API allows specific date fetching,
            # but typically get_daily_challenge gets the *current* one.

            self.logger.debug(f"Fetching daily challenge for date: {date_str} (UTC), domain: {domain}")
            challenge_info = await current_client.get_daily_challenge() # Simplified: get current daily

            if not challenge_info:
                self.logger.error(f"Failed to get daily challenge info for domain {domain}.")
                if interaction: await interaction.followup.send("Could not fetch daily challenge.", ephemeral=True)
                return

            self.logger.info(f"Got daily challenge: {challenge_info['id']}. {challenge_info['title']} for domain {domain}")

            color_map = {'Easy': 0x00FF00, 'Medium': 0xFFA500, 'Hard': 0xFF0000}
            emoji_map = {'Easy': '🟢', 'Medium': '🟡', 'Hard': '🔴'}
            embed_color = color_map.get(challenge_info['difficulty'], 0x0099FF)

            embed = discord.Embed(
                title=f"🔗 {challenge_info['id']}. {challenge_info['title']}",
                color=embed_color,
                url=challenge_info['link']
            )

            if domain == "com":
                alt_link = challenge_info['link'].replace("leetcode.com", "leetcode.cn")
                embed.description = f"Solve on [LCCN (leetcode.cn)]({alt_link})."
            else: # cn
                alt_link = challenge_info['link'].replace("leetcode.cn", "leetcode.com")
                embed.description = f"Solve on [LCUS (leetcode.com)]({alt_link})."

            embed.add_field(name="🔥 Difficulty", value=f"**{challenge_info['difficulty']}**", inline=True)
            if challenge_info.get('rating') and round(challenge_info['rating']) > 0:
                embed.add_field(name="⭐ Rating", value=f"**{round(challenge_info['rating'])}**", inline=True)
            if challenge_info.get('ac_rate'):
                embed.add_field(name="📈 AC Rate", value=f"**{round(challenge_info['ac_rate'], 2)}%**", inline=True)
            
            if challenge_info.get('tags'):    
                tags_str = ", ".join([f"||`{tag}`||" for tag in challenge_info['tags']])
                embed.add_field(name="🏷️ Tags", value=tags_str if tags_str else "N/A", inline=False)
            
            # Similar questions can be intensive, consider making it optional or less frequent
            # For now, keeping it as per original logic if present
            if challenge_info.get('similar_questions'):
                similar_q_list = []
                for sq_slug_info in challenge_info['similar_questions'][:3]: # Limit to 3 to avoid too much text/API calls
                    sq_detail = await current_client.get_problem(slug=sq_slug_info['titleSlug'])
                    if sq_detail:
                        sq_text = f"- {emoji_map.get(sq_detail['difficulty'], '')} [{sq_detail['id']}. {sq_detail['title']}]({sq_detail['link']})"
                        if sq_detail.get('rating') and sq_detail['rating'] > 0 : sq_text += f" *{int(sq_detail['rating'])}*"
                        similar_q_list.append(sq_text)
                if similar_q_list:
                    embed.add_field(name="🔍 Similar Questions", value="\n".join(similar_q_list), inline=False)

            embed.set_footer(text=f"LeetCode Daily Challenge | {challenge_info.get('date', date_str)}", icon_url="https://leetcode.com/static/images/LeetCode_logo.png")

            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="題目描述",
                emoji="📖",
                custom_id=f"{self.bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX}{challenge_info['id']}_{domain}"
            ))
            if self.bot.llm:
                view.add_item(discord.ui.Button(
                    style=discord.ButtonStyle.success,
                    label="LLM 翻譯",
                    emoji="🤖",
                    custom_id=f"{self.bot.LEETCODE_TRANSLATE_BUTTON_PREFIX}{challenge_info['id']}_{domain}"
                ))
            if self.bot.llm_pro:
                 view.add_item(discord.ui.Button(
                    style=discord.ButtonStyle.danger,
                    label="靈感啟發",
                    emoji="💡",
                    custom_id=f"{self.bot.LEETCODE_INSPIRE_BUTTON_PREFIX}{challenge_info['id']}_{domain}"
                ))

            if interaction:
                # If called from a slash command, use followup if deferred, or send_message if not.
                # Assuming slash commands will defer, so using followup.
                await interaction.followup.send(embed=embed, view=view)
                self.logger.info(f"Sent daily challenge via interaction {interaction.id}")
            elif channel_id:
                target_channel = self.bot.get_channel(channel_id)
                if target_channel:
                    content_msg = ""
                    if role_id:
                        # Ensure role exists in guild before mentioning
                        guild = target_channel.guild
                        role = guild.get_role(role_id)
                        if role:
                            content_msg = f"{role.mention}"
                        else:
                            self.logger.warning(f"Role ID {role_id} not found in guild {guild.id} for channel {channel_id}.")
                    await target_channel.send(content=content_msg if content_msg else None, embed=embed, view=view)
                    self.logger.info(f"Sent daily challenge to channel {channel_id}")
                else:
                    self.logger.error(f"Could not find channel {channel_id} to send daily challenge.")
            else:
                self.logger.error("send_daily_challenge called without channel_id or interaction.")

        except Exception as e:
            self.logger.error(f"Error in send_daily_challenge: {e}", exc_info=True)
            if interaction:
                try:
                    await interaction.followup.send(f"An error occurred while sending the daily challenge: {e}", ephemeral=True)
                except: # noqa
                    pass # Ignore if followup fails

async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleManagerCog(bot))