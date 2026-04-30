from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from bot.app import create_bot_runtime
from bot.utils.config import SimilarConfig, get_config
from bot.utils.logger import get_core_logger
from bot.utils.paths import find_repo_root, resolve_repo_path

REPO_ROOT = find_repo_root(Path(__file__))


class EnvConfig:
    def __init__(self):
        self.repo_root = REPO_ROOT

    def get(self, key, default=None):
        if key == "database.path":
            return "data/data.db"
        if key == "schedule.post_time":
            return self.post_time
        if key == "schedule.timezone":
            return self.timezone
        if key == "logging.directory":
            return "./logs"
        return default

    def get_section(self, section):
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
        if model_type == "standard":
            return {"name": "gemini-2.5-flash", "temperature": 0.0}
        return {"name": "gemini-2.5-pro", "temperature": 0.0}

    def get_cache_expire_seconds(self, cache_type):
        return 3600 if cache_type == "translation" else 86400

    def get_similar_config(self):
        return SimilarConfig()

    @property
    def database_path(self):
        return str(resolve_repo_path("data/data.db", self.repo_root))

    @property
    def log_directory(self):
        return str(resolve_repo_path("./logs", self.repo_root))

    @property
    def discord_token(self):
        return os.getenv("DISCORD_TOKEN")

    @property
    def gemini_api_key(self):
        return os.getenv("GOOGLE_GEMINI_API_KEY")

    @property
    def gemini_base_url(self):
        return os.getenv("GEMINI_BASE_URL")

    @property
    def api_base_url(self):
        return os.getenv("API_BASE_URL", "https://oj-api.gdst.dev/api/v1")

    @property
    def api_token(self):
        value = os.getenv("API_TOKEN")
        return value if value else None

    @property
    def api_timeout(self):
        return int(os.getenv("API_TIMEOUT", "10"))

    @property
    def default_locale(self):
        return "zh-TW"

    @property
    def supported_locales(self):
        return ["zh-TW", "en-US", "zh-CN"]

    @property
    def post_time(self):
        return os.getenv("POST_TIME", "00:00")

    @property
    def timezone(self):
        return os.getenv("TIMEZONE", "UTC")


def load_runtime_config():
    logger = get_core_logger()
    try:
        config = get_config()
        logger.info("Configuration loaded from config.toml")
        return config, logger
    except FileNotFoundError:
        logger.warning("config.toml not found, falling back to .env file")
        load_dotenv(dotenv_path=REPO_ROOT / ".env", verbose=True, override=True)
        return EnvConfig(), logger


def main():
    config, logger = load_runtime_config()
    return asyncio.run(create_bot_runtime(config=config, logger=logger))
