import importlib
import importlib.util
import inspect
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"


def _load_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_path_authority_module_exists():
    spec = importlib.util.find_spec("bot.utils.paths")
    assert spec is not None, "Expected bot.utils.paths shared path authority module to exist"


def test_config_manager_loads_repo_root_config_when_cwd_changes(monkeypatch):
    from bot.utils.config import ConfigManager

    monkeypatch.chdir(PROJECT_ROOT / "tests")

    try:
        manager = ConfigManager()
    except FileNotFoundError as exc:
        pytest.fail(f"ConfigManager should load repository-root config.toml independent of cwd: {exc}")

    assert Path(manager.config_path).resolve() == (PROJECT_ROOT / "config.toml").resolve()


def test_database_manager_resolves_relative_path_from_repo_root(monkeypatch, tmp_path):
    from bot.utils.database import SettingsDatabaseManager

    monkeypatch.chdir(tmp_path)

    manager = SettingsDatabaseManager(db_path="data/test-settings.db")

    assert Path(manager.db_path).resolve() == (PROJECT_ROOT / "data/test-settings.db").resolve()


def test_importing_bot_package_is_side_effect_free(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    for name in ["bot", "bot.cogs", "bot.llms", "bot.utils"]:
        sys.modules.pop(name, None)

    try:
        importlib.import_module("bot")
        importlib.import_module("bot.cogs")
        importlib.import_module("bot.llms")
        importlib.import_module("bot.utils")
    except Exception as exc:
        pytest.fail(f"Expected src/bot package skeleton to be importable without startup side effects: {exc}")

    assert not (tmp_path / "logs").exists(), "Importing bot package should not create logs/ in cwd"
    assert not (tmp_path / "data").exists(), "Importing bot package should not create data/ in cwd"


def test_root_launcher_delegates_to_package_bootstrap(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    launcher = _load_module_from_path("root_launcher_module", PROJECT_ROOT / "bot.py")

    delegated = {"called": False}

    fake_bot_package = types.ModuleType("bot")
    fake_bootstrap = types.ModuleType("bot.bootstrap")

    def fake_main():
        delegated["called"] = True

    fake_bootstrap.main = fake_main
    fake_bot_package.bootstrap = fake_bootstrap

    monkeypatch.setitem(sys.modules, "bot", fake_bot_package)
    monkeypatch.setitem(sys.modules, "bot.bootstrap", fake_bootstrap)

    result = launcher.main()
    if inspect.isawaitable(result):
        result.close()

    assert delegated["called"], "Expected repository-root bot.py launcher to delegate to bot.bootstrap.main()"
