from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _src_root() -> Path:
    return Path(__file__).resolve().parent / "src"


def _ensure_src_on_path() -> Path:
    src_root = _src_root()
    src_root_str = str(src_root)
    if src_root_str in sys.path:
        sys.path.remove(src_root_str)
    sys.path.insert(0, src_root_str)
    return src_root


def _load_bootstrap_main():
    return importlib.import_module("bot.bootstrap").main


def main():
    _ensure_src_on_path()
    bootstrap_main = _load_bootstrap_main()
    return bootstrap_main()


if __name__ == "__main__":
    main()
