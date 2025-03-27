import logging
import colorlog

def setup_logging(level=logging.INFO):
    """Sets up the root logger with a colored stream handler."""
    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        fmt='%(asctime)s %(log_color)s%(levelname)-8s%(reset)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    handler.setFormatter(formatter)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates if setup is called multiple times
    # or if other libraries configure the root logger.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Add the new handler
    root_logger.addHandler(handler)

    # Optional: Prevent propagation to avoid duplicate logs if other libraries
    # also configure logging and add handlers to the root logger.
    # root_logger.propagate = False

# You can add other logging related utilities here if needed in the future.
if __name__ == "__main__":
    # Example usage
    setup_logging(logging.DEBUG)
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")