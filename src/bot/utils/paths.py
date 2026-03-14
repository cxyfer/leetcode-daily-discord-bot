from __future__ import annotations

import os
from pathlib import Path


class RepoRootNotFoundError(RuntimeError):
    """Raised when the repository root cannot be determined."""


def _normalize_path(value: str | Path | None) -> Path:
    path = Path(value).expanduser() if value is not None else Path.cwd()
    return path.resolve()


def _candidate_directories(start: str | Path | None) -> list[Path]:
    current = _normalize_path(start)
    if current.is_file():
        current = current.parent
    return [current, *current.parents]


def find_repo_root(start: str | Path | None = None) -> Path:
    candidates = _candidate_directories(start)

    for marker in ("pyproject.toml", ".git"):
        for directory in candidates:
            if (directory / marker).exists():
                return directory

    override = os.getenv("BOT_REPO_ROOT")
    if override:
        override_path = _normalize_path(override)
        if override_path.exists():
            return override_path
        raise RepoRootNotFoundError(f"BOT_REPO_ROOT points to a missing path: {override_path}")

    raise RepoRootNotFoundError(
        "Unable to determine repository root. Set BOT_REPO_ROOT or ensure pyproject.toml/.git exists."
    )


def get_repo_root() -> Path:
    return find_repo_root(Path(__file__))


def resolve_repo_path(path: str | Path, repo_root: str | Path | None = None) -> Path:
    raw_path = Path(path).expanduser()
    if raw_path.is_absolute():
        return raw_path.resolve()

    base = _normalize_path(repo_root) if repo_root is not None else get_repo_root()
    return (base / raw_path).resolve()
