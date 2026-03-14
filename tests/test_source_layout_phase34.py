from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from bot import app


class DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
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
