import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
LAUNCHER_PATH = REPO_ROOT / "bot.py"
BOOTSTRAP_PATH = SRC_ROOT / "bot" / "bootstrap.py"


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/bot/__init__.py",
        "src/bot/cogs/__init__.py",
        "src/bot/llms/__init__.py",
        "src/bot/utils/__init__.py",
    ],
)
def test_package_skeleton_exists(relative_path):
    assert (REPO_ROOT / relative_path).is_file()


def test_find_repo_root_prefers_pyproject_before_git(tmp_path, monkeypatch):
    monkeypatch.delenv("BOT_REPO_ROOT", raising=False)

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    nested_project = repo_root / "packages" / "runtime"
    nested_project.mkdir(parents=True)
    (nested_project / "pyproject.toml").write_text("[project]\nname = 'runtime'\n", encoding="utf-8")

    from bot.utils.paths import find_repo_root

    assert find_repo_root(nested_project / "deeper") == nested_project


def test_find_repo_root_falls_back_to_git_marker(tmp_path, monkeypatch):
    monkeypatch.delenv("BOT_REPO_ROOT", raising=False)

    repo_root = tmp_path / "repo"
    nested = repo_root / "a" / "b"
    nested.mkdir(parents=True)
    (repo_root / ".git").mkdir()

    from bot.utils.paths import find_repo_root

    assert find_repo_root(nested) == repo_root


def test_find_repo_root_uses_env_override_when_markers_missing(tmp_path, monkeypatch):
    override_root = tmp_path / "override-root"
    override_root.mkdir()
    monkeypatch.setenv("BOT_REPO_ROOT", str(override_root))

    from bot.utils.paths import find_repo_root

    assert find_repo_root(tmp_path / "unmarked" / "child") == override_root


def test_find_repo_root_fails_fast_when_unresolved(tmp_path, monkeypatch):
    monkeypatch.delenv("BOT_REPO_ROOT", raising=False)

    from bot.utils.paths import RepoRootNotFoundError, find_repo_root

    with pytest.raises(RepoRootNotFoundError):
        find_repo_root(tmp_path / "missing" / "child")


def test_config_manager_resolves_repo_root_paths_from_any_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from bot.utils.config import ConfigManager

    config = ConfigManager()

    assert config.config_path == REPO_ROOT / "config.toml"
    assert Path(config.database_path) == REPO_ROOT / Path(config.get("database.path", "data/data.db"))
    assert Path(config.log_directory) == REPO_ROOT / Path(config.get("logging.directory", "./logs"))


def test_logger_directory_resolution_is_repo_root_based(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from bot.utils.logger import resolve_log_directory

    assert Path(resolve_log_directory("./logs")) == REPO_ROOT / "logs"


def test_database_manager_resolves_default_path_from_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    database_module = importlib.import_module("bot.utils.database")
    connect_calls = []

    class DummyCursor:
        def execute(self, *_args, **_kwargs):
            return None

        def fetchone(self):
            return None

    class DummyConnection:
        def cursor(self):
            return DummyCursor()

        def commit(self):
            return None

        def close(self):
            return None

    def fake_connect(db_path):
        connect_calls.append(db_path)
        return DummyConnection()

    monkeypatch.setattr(database_module.sqlite3, "connect", fake_connect)

    manager = database_module.SettingsDatabaseManager()

    assert Path(manager.db_path) == REPO_ROOT / "data" / "settings.db"
    assert connect_calls[0] == str(REPO_ROOT / "data" / "settings.db")


def test_bootstrap_env_fallback_uses_repo_root_env_path(monkeypatch):
    bootstrap = _load_module("test_bootstrap_module", BOOTSTRAP_PATH)
    dotenv_calls = {}

    class DummyLogger:
        def info(self, *_args, **_kwargs):
            return None

        def warning(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(bootstrap, "get_config", lambda: (_ for _ in ()).throw(FileNotFoundError("missing config")))
    monkeypatch.setattr(bootstrap, "get_core_logger", lambda: DummyLogger())
    monkeypatch.setattr(
        bootstrap,
        "load_dotenv",
        lambda dotenv_path, verbose, override: dotenv_calls.update(
            {"dotenv_path": Path(dotenv_path), "verbose": verbose, "override": override}
        ),
    )

    config, _logger = bootstrap.load_runtime_config()

    assert dotenv_calls == {
        "dotenv_path": REPO_ROOT / ".env",
        "verbose": True,
        "override": True,
    }
    assert Path(config.database_path) == REPO_ROOT / "data" / "data.db"


def test_root_launcher_inserts_src_and_delegates(monkeypatch):
    launcher = _load_module("test_root_launcher", LAUNCHER_PATH)
    calls = {"count": 0}

    def fake_bootstrap_main():
        calls["count"] += 1
        return "delegated"

    monkeypatch.setattr(launcher, "_load_bootstrap_main", lambda: fake_bootstrap_main)
    monkeypatch.setattr(launcher.sys, "path", [path for path in launcher.sys.path if path != str(SRC_ROOT)])

    result = launcher.main()

    assert result == "delegated"
    assert calls["count"] == 1
    assert launcher.sys.path[0] == str(SRC_ROOT)
