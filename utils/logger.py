import logging
import colorlog
import os
from datetime import datetime
from typing import Dict, Optional

# Global configuration - load once at module import time
try:
    from utils.config import get_config
    config = get_config()
    logger_config = config.get_section("logging")
    GLOBAL_LOG_LEVEL = getattr(logging, logger_config.get("level", "INFO"))
    GLOBAL_LOG_DIR = logger_config.get("directory", "./logs")
    GLOBAL_MODULE_LEVELS = {
        module: getattr(logging, level)
        for module, level in logger_config.get("modules", {}).items()
    }
except Exception:
    # Use default values if config loading fails
    GLOBAL_LOG_LEVEL = logging.INFO
    GLOBAL_LOG_DIR = "./logs"
    GLOBAL_MODULE_LEVELS = {
        "core": logging.DEBUG,
        "commands": logging.DEBUG,
        "leetcode": logging.DEBUG,
        "database": logging.DEBUG,
        "scheduler": logging.DEBUG,
        "llm": logging.DEBUG,
        "config": logging.DEBUG,
        "ui": logging.DEBUG,
        "discord": logging.WARNING,
        "discord.gateway": logging.WARNING,
        "discord.client": logging.WARNING,
        "requests": logging.WARNING,
    }


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter that includes file location information."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[32m',      # Green
        'INFO': '\033[36m',       # Cyan
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[31;47m',  # Red background
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add file location information to the record
        record.fileloc = f"[{record.filename}:{record.lineno}]"

        # Add color to the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        # Call parent format method
        result = super().format(record)

        # Restore original levelname for other handlers
        record.levelname = levelname

        return result


class Logger:
    """Logger management class with static methods for creating and retrieving loggers."""

    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False

    @staticmethod
    def setup_logger(name: str) -> logging.Logger:
        """
        Create or return an existing logger with global configuration.
        
        Args:
            name (str): Logger name
        
        Returns:
            logging.Logger: The configured logger instance
        """
        # Return existing logger if already created
        if name in Logger._loggers:
            return Logger._loggers[name]

        # Initialize logging system if not done yet
        if not Logger._initialized:
            Logger._setup_logging_system()

        # Create or get the logger
        logger = logging.getLogger(name)
        Logger._loggers[name] = logger

        return logger

    @staticmethod
    def get_logger(name: str) -> Optional[logging.Logger]:
        """
        Get an existing logger by name.
        
        Args:
            name (str): Logger name
        
        Returns:
            logging.Logger or None: The logger instance if exists, None otherwise
        """
        return Logger._loggers.get(name)

    @staticmethod
    def _setup_logging_system():
        """
        Set up the logging system with global configuration.
        """
        # Create logs directory if it doesn't exist
        os.makedirs(GLOBAL_LOG_DIR, exist_ok=True)

        # Create formatters
        stream_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-17s | %(fileloc)-32s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(fileloc)-32s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Set up stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(stream_formatter)

        # Set up file handler with daily rotating files
        current_date = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            filename=f"{GLOBAL_LOG_DIR}/{current_date}.log", encoding="utf-8"
        )
        file_handler.setFormatter(file_formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(GLOBAL_LOG_LEVEL)

        # Remove existing handlers to avoid duplicates
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # Add the handlers
        root_logger.addHandler(stream_handler)
        root_logger.addHandler(file_handler)

        # Set levels for specific modules
        for module_name, module_level in GLOBAL_MODULE_LEVELS.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(module_level)

        Logger._initialized = True

        # Log initialization
        logging.info("Logging system initialized")

    @staticmethod
    def set_module_level(module_name: str, level: int) -> bool:
        """
        Set the log level for a specific module.
        
        Args:
            module_name (str): The name of the module to configure
            level (int): The logging level to set
        
        Returns:
            bool: True if successful, False if logging hasn't been initialized yet
        """
        if not Logger._initialized:
            return False

        logger = logging.getLogger(module_name)
        logger.setLevel(level)
        logging.info(f"Set log level for '{module_name}' to {level}")
        return True


# Convenience methods for getting specific loggers
def get_core_logger() -> logging.Logger:
    """Get the core bot logger - for bot.py, main application logic."""
    return Logger.setup_logger("core")


def get_commands_logger() -> logging.Logger:
    """Get the commands/interactions logger - for cogs, slash commands."""
    return Logger.setup_logger("commands")


def get_leetcode_logger() -> logging.Logger:
    """Get the LeetCode API logger - for leetcode.py."""
    return Logger.setup_logger("leetcode")


def get_database_logger() -> logging.Logger:
    """Get the database operations logger - for database.py."""
    return Logger.setup_logger("database")


def get_scheduler_logger() -> logging.Logger:
    """Get the scheduler logger - for schedule_manager_cog.py."""
    return Logger.setup_logger("scheduler")


def get_llm_logger() -> logging.Logger:
    """Get the LLM services logger - for llms/."""
    return Logger.setup_logger("llm")


def get_config_logger() -> logging.Logger:
    """Get the configuration logger - for config.py."""
    return Logger.setup_logger("config")


def get_ui_logger() -> logging.Logger:
    """Get the UI helpers logger - for ui_helpers.py."""
    return Logger.setup_logger("ui")


if __name__ == "__main__":
    # Example usage
    logger = get_core_logger()
    database_logger = get_database_logger()
    llm_logger = get_llm_logger()

    logger.debug("This is a debug message from main logger")
    logger.info("This is an info message from main logger")
    logger.warning("This is a warning message from main logger")
    logger.error("This is an error message from main logger")
    logger.critical("This is a critical message from main logger")

    database_logger.info("This is a message from database logger")
    llm_logger.info("This is a message from LLM logger")
