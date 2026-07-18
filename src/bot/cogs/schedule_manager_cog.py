# cogs/schedule_manager_cog.py
import asyncio
import random
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext import commands

from bot.api_client import ApiDailyNotFoundError, ApiProcessingError, ApiRateLimitError
from bot.utils.config import DEFAULT_POST_TIME, DEFAULT_TIMEZONE, parse_timezone
from bot.utils.daily_sources import DAILY_PUSH_SOURCE_LABELS, validate_daily_push_source
from bot.utils.logger import get_scheduler_logger
from bot.utils.ui_helpers import send_daily_challenge


class ScheduleManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_scheduler_logger()
        self.scheduled_delivery_lock = asyncio.Lock()
        self.scheduled_deliveries_in_progress = set()

        # Setup APScheduler (uses MemoryJobStore by default, avoiding Discord object serialization issues)
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,  # 5 minutes grace time
        }

        self.scheduler = AsyncIOScheduler(job_defaults=job_defaults, timezone=pytz.UTC)

    @staticmethod
    def _job_id(server_id: int, source: str) -> str:
        return f"daily_challenge:{server_id}:{source}"

    async def initialize_schedules(self):
        """
        Initialize daily LeetCode challenge schedules for all servers.

        Note: Uses MemoryJobStore which means:
        - Jobs are lost on bot restart (but will be recreated from database settings)
        - No persistence issues with Discord object serialization
        - Lightweight and fast for simple recurring tasks
        """
        self.logger.info("Initializing APScheduler-based daily challenge schedules...")

        # Start the scheduler once; whole-runtime reschedules reuse the same instance.
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("APScheduler started successfully")

        # Clear any existing jobs to avoid duplicates
        self.scheduler.remove_all_jobs()

        # Get all source-specific push settings and create schedules.
        pushes = self.bot.db.get_all_daily_pushes()
        count = 0

        for push_settings in pushes:
            server_id = push_settings.get("server_id")
            if not server_id:
                self.logger.warning(f"Daily push settings found with no server_id: {push_settings}")
                continue

            if not push_settings.get("channel_id"):
                self.logger.info(f"Server {server_id} push has no channel_id set, skipping schedule.")
                continue

            if await self.add_server_schedule(push_settings):
                count += 1

        self.logger.info(f"Total {count} source-specific schedules created with APScheduler.")

    async def add_server_schedule(self, server_settings):
        """Add one server/source schedule using APScheduler."""
        server_id = server_settings.get("server_id")
        source = server_settings.get("source")
        channel_id = server_settings.get("channel_id")

        if not channel_id:
            self.logger.error(f"Attempted to schedule for server {server_id} but no channel_id was provided.")
            return False

        post_time_str = server_settings.get("post_time", DEFAULT_POST_TIME)
        timezone_str = server_settings.get("timezone", DEFAULT_TIMEZONE)
        role_id = server_settings.get("role_id")

        try:
            validate_daily_push_source(source)
            hour, minute = map(int, post_time_str.split(":"))
            target_timezone = parse_timezone(timezone_str)

            # Create cron trigger for daily execution
            trigger = CronTrigger(hour=hour, minute=minute, timezone=target_timezone)

            job_id = self._job_id(server_id, source)

            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Add new job
            self.scheduler.add_job(
                func=self.send_daily_challenge_job,
                trigger=trigger,
                id=job_id,
                args=[server_id, source, channel_id, role_id, timezone_str],
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace time
                name=f"Daily Challenge for Server {server_id} ({source})",
            )

            self.logger.info(
                "Scheduled daily challenge for server %s, source %s at %s %s",
                server_id,
                source,
                post_time_str,
                timezone_str,
            )
            return True

        except ValueError as e:
            self.logger.error(
                f"Server {server_id}, source {source}: Invalid schedule config "
                f"(time={post_time_str}, tz={timezone_str}): {e}"
            )
        except Exception as e:
            self.logger.error(f"Server {server_id}, source {source}: Error adding schedule: {e}", exc_info=True)
        return False

    async def _mark_scheduled_delivery_started(self, delivery_key: tuple[int, int, str, str]) -> bool:
        async with self.scheduled_delivery_lock:
            if delivery_key in self.scheduled_deliveries_in_progress:
                return False
            self.scheduled_deliveries_in_progress.add(delivery_key)
            return True

    async def _cleanup_scheduled_delivery(self, delivery_key: tuple[int, int, str, str]) -> None:
        async with self.scheduled_delivery_lock:
            self.scheduled_deliveries_in_progress.discard(delivery_key)

    async def send_daily_challenge_job(
        self,
        server_id: int,
        source: str,
        channel_id: int,
        role_id: int = None,
        timezone_str: str = DEFAULT_TIMEZONE,
    ):
        """Job function called by APScheduler to send daily challenges"""
        self.logger.info(
            "APScheduler triggered: Sending daily challenge for server %s, source %s",
            server_id,
            source,
        )

        # Resolve guild locale: DB setting → config default → zh-TW
        guild_locale = self.bot.i18n.resolve_locale(
            guild_id=server_id,
            config_default=self.bot.config.default_locale,
        )

        delays = [2, 4, 8]

        scheduled_timezone = parse_timezone(timezone_str)
        daily_date = datetime.now(scheduled_timezone).strftime("%Y-%m-%d")
        delivery_key = (server_id, channel_id, source, daily_date)
        if not await self._mark_scheduled_delivery_started(delivery_key):
            self.logger.info(
                "Scheduled daily delivery already in progress for server %s, channel %s, source %s, "
                "date %s; skipping duplicate",
                server_id,
                channel_id,
                source,
                daily_date,
            )
            return

        try:
            for attempt in range(len(delays) + 1):
                try:
                    result = await send_daily_challenge(
                        bot=self.bot,
                        channel_id=channel_id,
                        role_id=role_id,
                        guild_locale=guild_locale,
                        daily_source=source,
                    )
                    if result:
                        self.logger.info(
                            "Sent daily challenge for server %s, source %s: %s",
                            server_id,
                            source,
                            result.get("title"),
                        )
                    else:
                        self.logger.warning(f"Failed to send daily challenge for server {server_id}, source {source}")
                    return
                except ApiDailyNotFoundError:
                    self.logger.info("Server %s, source %s: no daily challenge available", server_id, source)
                    return
                except ApiProcessingError:
                    if attempt < len(delays):
                        delay = delays[attempt] + random.uniform(-0.5, 0.5)
                        self.logger.warning(
                            f"Server {server_id}, source {source}: API processing "
                            f"(attempt {attempt + 1}/{len(delays) + 1}), "
                            f"retry in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                except ApiRateLimitError:
                    self.logger.warning(f"Server {server_id}, source {source}: rate limited, skipping daily challenge")
                    return
                except Exception as e:
                    self.logger.error(
                        f"Error in send_daily_challenge_job for server {server_id}, source {source}: {e}",
                        exc_info=True,
                    )
                    return

            self.logger.warning(
                f"Server {server_id}, source {source}: API still processing after {len(delays) + 1} attempts, skipping"
            )
        finally:
            await self._cleanup_scheduled_delivery(delivery_key)

    def _remove_source_job(self, server_id: int, source: str) -> None:
        job_id = self._job_id(server_id, source)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            self.logger.info("Removed schedule for server %s, source %s", server_id, source)

    async def reschedule_daily_challenge(self, server_id: int = None, source: str = None):
        """Reschedule one source, every source for a server, or every push."""
        if server_id is not None:
            if source is not None:
                validate_daily_push_source(source)
                self.logger.info("Rescheduling daily challenge for server %s, source %s", server_id, source)
                self._remove_source_job(server_id, source)
                push_settings = self.bot.db.get_daily_push(server_id, source)
                if push_settings and push_settings.get("channel_id"):
                    await self.add_server_schedule(push_settings)
                    self.logger.info("Server %s, source %s has been rescheduled", server_id, source)
                else:
                    self.logger.info("Server %s, source %s has no settings; schedule removed", server_id, source)
            else:
                self.logger.info("Rescheduling every daily source for server %s", server_id)
                for daily_source in DAILY_PUSH_SOURCE_LABELS:
                    self._remove_source_job(server_id, daily_source)
                for push_settings in self.bot.db.get_daily_pushes(server_id):
                    if push_settings.get("channel_id"):
                        await self.add_server_schedule(push_settings)
                self.logger.info("Every daily source for server %s has been rescheduled", server_id)
        else:
            if source is not None:
                raise ValueError("source requires server_id for targeted rescheduling")
            self.logger.info("Rescheduling daily challenges for ALL servers...")
            # Remove all existing jobs
            self.scheduler.remove_all_jobs()
            # Re-initialize all schedules
            await self.initialize_schedules()
            self.logger.info("All server daily challenges have been rescheduled")

    def get_scheduled_jobs(self):
        """Get information about all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    async def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if hasattr(self, "scheduler") and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info("APScheduler shutdown complete")


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleManagerCog(bot))
