import logging
import colorlog
import os
from datetime import datetime

# Global flag to track if logger has been initialized
_logger_initialized = False

def get_logger(name=None):
    """
    Get a logger instance. If name is None, returns the root logger.
    Supports hierarchical logger names like 'bot.discord' or 'bot.lcus'.
    
    Args:
        name (str, optional): Logger name for module-specific logging
        
    Returns:
        logging.Logger: The logger instance
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger()

def setup_logging(level=logging.INFO, log_dir="./logs", force=False, 
                 module_levels=None):
    """
    Sets up the root logger with both colored stream handler and file handler.
    Only initializes once unless force=True.
    
    Args:
        level (int): Logging level for the root logger (default: logging.INFO)
        log_dir (str): Directory to store log files (default: ./logs)
        force (bool): Force re-initialization even if already set up
        module_levels (dict, optional): Dictionary of module name to log level mappings
                                       e.g. {'bot.discord': logging.WARNING, 'bot.lcus': logging.DEBUG}
        
    Returns:
        bool: True if logger was initialized or re-initialized, False if already initialized
    """
    global _logger_initialized
    
    # Skip if already initialized and not forced
    if _logger_initialized and not force:
        return False
        
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a formatter for both handlers
    stream_formatter = colorlog.ColoredFormatter(
        fmt='%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'green',
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set up stream handler
    stream_handler = colorlog.StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    
    # Set up file handler with daily rotating files
    current_date = datetime.now().strftime('%Y-%m-%d')
    file_handler = logging.FileHandler(
        filename=f"{log_dir}/{current_date}.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # Add the handlers
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    
    # Default module levels if none provided
    if module_levels is None:
        module_levels = {
            'bot': logging.DEBUG,                 # Main bot module
            'bot.discord': logging.DEBUG,         # Discord API related logs
            'bot.lcus': logging.DEBUG,            # LeetCode User Service
            'bot.db': logging.DEBUG,              # Database operations
            'discord': logging.WARNING,          # External discord.py library
            'discord.gateway': logging.WARNING,  # External discord.py gateway
            'discord.client': logging.WARNING,   # External discord.py client
            'requests': logging.WARNING,         # External requests library
        }
    
    # Set levels for specific modules
    for module_name, module_level in module_levels.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(module_level)
        # We'll keep propagation enabled by default
        # module_logger.propagate = False
    
    # Mark as initialized
    _logger_initialized = True
    
    # Log initialization
    logging.info("Logging system initialized")
    return True

def set_module_level(module_name, level):
    """
    Sets the log level for a specific module after logging has been initialized.
    
    Args:
        module_name (str): The name of the module to configure
        level (int): The logging level to set
        
    Returns:
        bool: True if successful, False if logging hasn't been initialized yet
    """
    if not _logger_initialized:
        return False
        
    logger = logging.getLogger(module_name)
    logger.setLevel(level)
    logging.info(f"Set log level for '{module_name}' to {level}")
    return True

if __name__ == "__main__":
    # Example usage with different submodule logging levels
    setup_logging(
        level=logging.INFO,
        module_levels={
            'bot': logging.DEBUG,
        }
    )
    
    logger = get_logger("bot")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")