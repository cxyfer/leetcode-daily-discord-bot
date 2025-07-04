"""
Configuration management module for loading and accessing settings from config.toml
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Try to use tomllib from Python 3.11+, otherwise fall back to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError(
            "tomli is required for Python < 3.11. "
            "Please install it with: pip install tomli"
        )

from utils.logger import get_logger

logger = get_logger("bot.config")

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
        self.config_path = Path(config_path)
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
        - GOOGLE_GEMINI_API_KEY -> llm.gemini.api_key
        - POST_TIME -> schedule.post_time
        - TIMEZONE -> schedule.timezone
        """
        env_mappings = {
            "DISCORD_TOKEN": ("discord", "token"),
            "GOOGLE_GEMINI_API_KEY": ("llm", "gemini", "api_key"),
            "POST_TIME": ("schedule", "post_time"),
            "TIMEZONE": ("schedule", "timezone"),
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
        return self.get("database.path", "data/data.db")
    
    @property
    def log_level(self) -> str:
        """Get logging level"""
        return self.get("logging.level", "INFO")
    
    @property
    def log_directory(self) -> str:
        """Get logging directory"""
        return self.get("logging.directory", "./logs")
    
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