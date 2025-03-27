# Plan: Unify Project Logging

This document outlines the plan to unify the logging format across the project using a shared configuration module.

## Goal

Standardize logging format and configuration across all Python files (`.py`) in the project, using `colorlog` for colored output.

## Steps

1.  **Create Shared Logging Configuration Module (`utils/logger.py`)**
    *   Create a new file `utils/logger.py` (the `utils` directory will be created if it doesn't exist).
    *   Define a function `setup_logging(level=logging.INFO)` within this file.
    *   This function will configure the root logger with the specified `colorlog` handler and formatter:
        ```python
        import logging
        import colorlog
        import os # Potentially needed if log file path is involved, though not requested yet

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

            # Remove existing handlers (optional but good practice to avoid duplicates)
            # if root_logger.hasHandlers():
            #     root_logger.handlers.clear()

            # Add the new handler
            root_logger.addHandler(handler)

            # Optional: Prevent propagation to avoid duplicate logs if other libraries configure logging
            # root_logger.propagate = False
        ```
    *   Ensure necessary imports (`logging`, `colorlog`) are included.

2.  **Verify Dependency (`colorlog`)**
    *   Check `pyproject.toml` to confirm `colorlog` is listed as a dependency. (Already confirmed: `colorlog>=6.9.0` exists).

3.  **Refactor `leetcode_daily.py`**
    *   Remove the existing logging setup code (lines 21-23).
    *   Add imports: `import logging` and `from utils.logger import setup_logging`.
    *   Call `setup_logging()` once at the top level (after imports).
    *   Replace all direct `logging.info`, `logging.error`, etc., calls with:
        ```python
        logger = logging.getLogger(__name__)
        logger.info("...")
        logger.error("...")
        # etc.
        ```

4.  **Integrate `discord_bot.py`**
    *   Add imports: `import logging` and `from utils.logger import setup_logging`.
    *   Call `setup_logging()` once at the application entry point (e.g., before the bot starts or in `if __name__ == "__main__":`).
    *   In functions/methods where logging is needed, get the logger instance: `logger = logging.getLogger(__name__)` and use it (`logger.info`, etc.).

5.  **Integrate `db_manager.py`**
    *   Add import: `import logging`.
    *   In functions/methods where logging is needed, get the logger instance: `logger = logging.getLogger(__name__)` and use it (`logger.info`, etc.). (Do *not* call `setup_logging()` here).

## Flowchart (Mermaid)

```mermaid
graph TD
    subgraph Initialization
        A[Create utils/logger.py] --> B(Define setup_logging function);
        B -- Contains colorlog setup --> C{Check pyproject.toml};
        C -- colorlog missing --> D[Prompt to install colorlog];
        C -- colorlog present --> E[Setup Complete];
    end

    subgraph Application Entry Point (e.g., discord_bot.py)
        F[Import setup_logging from utils.logger] --> G[Call setup_logging() once];
    end

    subgraph Module Usage (All .py files)
        H[Import logging] --> I[Get logger = logging.getLogger(__name__)];
        I --> J[Use logger.info(), logger.error(), etc.];
    end

    subgraph Refactoring (leetcode_daily.py)
        K[Remove old logging setup] --> L[Import setup_logging from utils.logger];
        L --> M[Use getLogger(__name__)];
    end

    Initialization --> Application Entry Point;
    Application Entry Point --> Module Usage;
    Initialization --> Refactoring;
```

## Notes

*   The `setup_logging()` function should only be called *once* at the application's entry point.
*   Using `logging.getLogger(__name__)` in each module allows for more granular control and better traceability of log messages.
*   The `colorlog` dependency is confirmed to be present in `pyproject.toml`.