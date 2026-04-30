from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from bot import app


class DummyLogger:
    def debug(self, *_args, **_kwargs):
        return None

    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def critical(self, *_args, **_kwargs):
        return None


def test_discover_cog_extensions_uses_package_namespace_and_sorted_order(tmp_path, monkeypatch):
    package_root = tmp_path / "samplepkg"
    cogs_root = package_root / "cogs"
    cogs_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (cogs_root / "__init__.py").write_text("", encoding="utf-8")
    (cogs_root / "zeta_cog.py").write_text("", encoding="utf-8")
    (cogs_root / "alpha_cog.py").write_text("", encoding="utf-8")
    (cogs_root / "_internal.py").write_text("", encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))

    assert app.discover_cog_extensions("samplepkg.cogs") == [
        "samplepkg.cogs.alpha_cog",
        "samplepkg.cogs.zeta_cog",
    ]


@pytest.mark.asyncio
async def test_load_extensions_uses_canonical_extension_names(monkeypatch):
    bot = SimpleNamespace(load_extension=AsyncMock(), logger=DummyLogger())
    expected_extensions = ["bot.cogs.alpha_cog", "bot.cogs.beta_cog"]
    monkeypatch.setattr(app, "discover_cog_extensions", lambda package_name=app.COGS_PACKAGE: expected_extensions)

    await app.load_extensions(bot)

    assert [call.args[0] for call in bot.load_extension.await_args_list] == expected_extensions


@pytest.mark.parametrize(
    ("command_name", "bot_method"),
    [("load", "load_extension"), ("unload", "unload_extension"), ("reload", "reload_extension")],
)
@pytest.mark.asyncio
async def test_owner_commands_normalize_bare_cog_names(command_name, bot_method):
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    bot.logger = DummyLogger()
    setattr(bot, bot_method, AsyncMock())

    app._register_runtime_handlers(bot)

    ctx = SimpleNamespace(send=AsyncMock())
    command = bot.get_command(command_name)

    await command.callback(ctx, "similar_cog")

    getattr(bot, bot_method).assert_awaited_once_with("bot.cogs.similar_cog")


@pytest.mark.parametrize(
    "invalid_name",
    ["", "../similar_cog", "cogs/similar_cog", "cogs.similar_cog", "bot.cogs.similar_cog.extra"],
)
@pytest.mark.asyncio
async def test_owner_commands_reject_path_like_extension_names(invalid_name):
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    bot.logger = DummyLogger()
    bot.load_extension = AsyncMock()

    app._register_runtime_handlers(bot)

    ctx = SimpleNamespace(send=AsyncMock())
    command = bot.get_command("load")

    await command.callback(ctx, invalid_name)

    bot.load_extension.assert_not_awaited()
    assert ctx.send.await_count == 1
    assert "Invalid extension" in ctx.send.await_args.args[0]


@pytest.mark.asyncio
async def test_core_cog_listener_does_not_reprocess_commands(monkeypatch):
    import bot.cogs.core_cog as core_cog

    monkeypatch.setattr(core_cog, "get_commands_logger", lambda: DummyLogger())
    bot = SimpleNamespace(user=object(), process_commands=AsyncMock())
    cog = core_cog.CoreCog(bot)
    message = SimpleNamespace(author=SimpleNamespace(name="tester"))

    await cog.on_message(message)

    bot.process_commands.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_bot_runtime_checks_token_before_starting_api(monkeypatch):
    import bot.api_client as api_client
    import bot.leetcode as leetcode
    import bot.utils as bot_utils
    import bot.utils.database as database_module

    class DummyConfig:
        database_path = "data/data.db"
        discord_token = None
        gemini_api_key = None
        gemini_base_url = None
        api_base_url = "https://example.com"
        api_token = None
        api_timeout = 10
        default_locale = "zh-TW"
        supported_locales = ["zh-TW", "en-US", "zh-CN"]

        def get(self, _key, default=None):
            return default

        def get_cache_expire_seconds(self, _cache_type):
            return 60

        def get_llm_model_config(self, _model_type):
            return {}

    class DummyBot:
        def __init__(self):
            self.tree = SimpleNamespace(sync=AsyncMock(return_value=[]))
            self.start = AsyncMock()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def get_cog(self, _name):
            return None

    api = SimpleNamespace(start=AsyncMock(), close=AsyncMock())
    bot = DummyBot()

    monkeypatch.setattr(api_client, "OjApiClient", lambda *args, **kwargs: api)
    monkeypatch.setattr(leetcode, "LeetCodeClient", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(bot_utils, "SettingsDatabaseManager", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(database_module, "LLMTranslateDatabaseManager", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(database_module, "LLMInspireDatabaseManager", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(app.commands, "Bot", lambda *args, **kwargs: bot)
    monkeypatch.setattr(app, "_register_runtime_handlers", lambda _bot: None)
    monkeypatch.setattr(app, "load_extensions", AsyncMock())
    monkeypatch.setattr(app, "_create_reschedule_helper", lambda _bot: AsyncMock())

    await app.create_bot_runtime(config=DummyConfig(), logger=DummyLogger())

    api.start.assert_not_awaited()
    bot.start.assert_not_awaited()
