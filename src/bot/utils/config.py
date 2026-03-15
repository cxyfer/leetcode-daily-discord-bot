"""
Configuration management module for loading and accessing settings from config.toml
"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytz

from .paths import get_repo_root, resolve_repo_path

# Try to use tomllib from Python 3.11+, otherwise fall back to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("tomli is required for Python < 3.11. Please install it with: pip install tomli")

DEFAULT_POST_TIME = "00:00"
DEFAULT_TIMEZONE = "UTC"

# Module-level logger (avoid initializing logger system during import)
logger = logging.getLogger("config")


class ConfigManager:
    """
    Manages application configuration from config.toml file
    """

    def __init__(self, config_path: str = "config.toml"):
        """
        Initialize the configuration manager

        Args:
            config_path: Path to the configuration file
        """
        self.repo_root = get_repo_root()
        raw_config_path = Path(config_path).expanduser()
        self.config_path = (
            raw_config_path.resolve()
            if raw_config_path.is_absolute()
            else resolve_repo_path(raw_config_path, self.repo_root)
        )
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._apply_env_overrides()

    def _load_config(self) -> None:
        """Load configuration from TOML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Please copy config.toml.example to config.toml and update it with your settings."
            )

        try:
            with open(self.config_path, "rb") as f:
                self._config = tomllib.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _apply_env_overrides(self) -> None:
        """
        Apply environment variable overrides to configuration

        Environment variables take precedence over config file values.
        Mapping:
        - DISCORD_TOKEN -> discord.token
        - GOOGLE_GEMINI_API_KEY / GOOGLE_API_KEY / GEMINI_API_KEY -> llm.gemini.api_key
        - POST_TIME -> schedule.post_time
        - TIMEZONE -> schedule.timezone
        """
        env_mappings = {
            "DISCORD_TOKEN": ("discord", "token"),
            "GOOGLE_API_KEY": ("llm", "gemini", "api_key"),
            "GEMINI_API_KEY": ("llm", "gemini", "api_key"),
            "GOOGLE_GEMINI_API_KEY": ("llm", "gemini", "api_key"),
            "POST_TIME": ("schedule", "post_time"),
            "TIMEZONE": ("schedule", "timezone"),
            "API_BASE_URL": ("api", "base_url"),
            "API_TOKEN": ("api", "token"),
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested(self._config, config_path, env_value)
                logger.debug(f"Applied environment override: {env_var}")

    def _set_nested(self, d: Dict[str, Any], path: tuple, value: Any) -> None:
        """Set a value in a nested dictionary using a path tuple"""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _get_nested(self, d: Dict[str, Any], path: tuple, default: Any = None) -> Any:
        """Get a value from a nested dictionary using a path tuple"""
        for key in path:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation

        Args:
            key: Configuration key in dot notation (e.g., "discord.token")
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        path = tuple(key.split("."))
        return self._get_nested(self._config, path, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section

        Args:
            section: Section name (e.g., "discord", "llm")

        Returns:
            Dictionary containing the section configuration
        """
        return self._config.get(section, {})

    @property
    def discord_token(self) -> Optional[str]:
        """Get Discord bot token"""
        return self.get("discord.token")

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Google Gemini API key"""
        return self.get("llm.gemini.api_key")

    @property
    def gemini_base_url(self) -> Optional[str]:
        """Get Google Gemini base URL for third-party proxy"""
        return self.get("llm.gemini.base_url")

    @property
    def post_time(self) -> str:
        """Get default post time"""
        return self.get("schedule.post_time", "00:00")

    @property
    def timezone(self) -> str:
        """Get default timezone"""
        return self.get("schedule.timezone", "UTC")

    @property
    def database_path(self) -> str:
        """Get database path"""
        return str(resolve_repo_path(self.get("database.path", "data/data.db"), self.repo_root))

    @property
    def log_level(self) -> str:
        """Get logging level"""
        return self.get("logging.level", "INFO")

    @property
    def log_directory(self) -> str:
        """Get logging directory"""
        return str(resolve_repo_path(self.get("logging.directory", "./logs"), self.repo_root))

    def get_llm_model_config(self, model_type: str = "standard") -> Dict[str, Any]:
        """
        Get LLM model configuration

        Args:
            model_type: "standard" or "pro"

        Returns:
            Dictionary with model configuration
        """
        return self.get(f"llm.gemini.models.{model_type}", {})

    def get_cache_expire_seconds(self, cache_type: str) -> int:
        """
        Get cache expiration time in seconds

        Args:
            cache_type: "translation" or "inspiration"

        Returns:
            Expiration time in seconds
        """
        key = f"llm.cache.{cache_type}_expire_seconds"
        default = 3600 if cache_type == "translation" else 86400
        return self.get(key, default)

    def get_similar_config(self) -> "SimilarConfig":
        """Get similar-problem search configuration"""
        section = self.get("similar", {})
        return SimilarConfig(
            top_k=section.get("top_k", 5),
            min_similarity=section.get("min_similarity", 0.70),
        )

    @property
    def api_base_url(self) -> str:
        return self.get("api.base_url", "https://craboj.zeabur.app/api/v1")

    @property
    def api_token(self) -> str | None:
        val = self.get("api.token")
        return val if val else None

    @property
    def api_timeout(self) -> int:
        return self.get("api.timeout", 10)


@dataclass
class SimilarConfig:
    """Similar problem search configuration"""

    top_k: int = 5
    min_similarity: float = 0.70


# Global configuration instance
_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get the global configuration instance

    Returns:
        ConfigManager instance
    """
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config


_UTC_OFFSET_RE = re.compile(r"^UTC([+-])(\d{1,2})(?::([0-5]\d))?$", re.IGNORECASE)


def parse_timezone(tz_string: str):
    """Parse IANA timezone name or UTC offset string into a tzinfo object."""
    try:
        return pytz.timezone(tz_string)
    except pytz.exceptions.UnknownTimeZoneError:
        pass

    m = _UTC_OFFSET_RE.match(tz_string)
    if not m:
        raise ValueError(
            f"Invalid timezone: {tz_string} (supported: IANA name e.g. Asia/Taipei, or UTC offset e.g. UTC+8, UTC-5:30)"
        )

    sign = 1 if m.group(1) == "+" else -1
    hours = int(m.group(2))
    minutes = int(m.group(3)) if m.group(3) else 0
    total = sign * (hours * 60 + minutes)

    if not (-720 <= total <= 840):
        raise ValueError(f"UTC offset out of range: {tz_string} (valid: UTC-12:00 ~ UTC+14:00)")

    return timezone(timedelta(minutes=total))
