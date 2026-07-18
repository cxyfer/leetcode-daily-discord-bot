from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from bot.cogs import slash_commands_cog as slash_module
from bot.cogs.slash_commands_cog import SlashCommandsCog
from bot.utils.ui_helpers import create_settings_embed


def _push(source: str, *, channel_id: int = 100, role_id: int | None = None) -> dict:
    return {
        "server_id": 123,
        "source": source,
        "channel_id": channel_id,
        "role_id": role_id,
        "post_time": "08:00",
        "timezone": "Asia/Taipei",
    }


def _make_bot(*, settings: dict | None = None, pushes: list[dict] | None = None):
    bot = MagicMock()
    bot.config = SimpleNamespace(default_locale="zh-TW")
    bot.i18n = MagicMock()
    bot.i18n.resolve_locale.return_value = "zh-TW"
    bot.i18n.get_supported_locales.return_value = ["zh-TW", "en-US", "zh-CN"]
    bot.i18n.t.side_effect = lambda key, _locale, **kwargs: key + (f":{kwargs}" if kwargs else "")
    bot.db = MagicMock()
    bot.db.get_server_settings.return_value = settings
    bot.db.get_daily_pushes.return_value = pushes or []
    bot.db.get_daily_push.side_effect = lambda _server_id, source: next(
        (push for push in (pushes or []) if push["source"] == source),
        None,
    )
    bot.db.set_server_language.return_value = True
    bot.db.set_daily_push.return_value = True
    bot.get_channel.side_effect = lambda channel_id: SimpleNamespace(mention=f"<#{channel_id}>")
    bot.reschedule_daily_challenge = AsyncMock()
    return bot


def _make_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 123
    interaction.guild.name = "Test Guild"
    interaction.guild.get_role.side_effect = lambda role_id: SimpleNamespace(mention=f"<@&{role_id}>")
    interaction.user = MagicMock()
    interaction.user.id = 9_999_999_999_999_999_999
    interaction.user.guild_permissions.manage_guild = True
    interaction.guild_locale = None
    interaction.locale = discord.Locale.taiwan_chinese
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    return interaction


async def _invoke_config(cog, interaction, **overrides):
    params = {
        "channel": None,
        "role": None,
        "post_time": None,
        "timezone": None,
        "clear_role": False,
        "language": None,
        "reset": False,
        "source": None,
        "remove": False,
    }
    params.update(overrides)
    await cog.config_command.callback(cog, interaction, **params)


def test_config_source_choices_are_fixed_to_supported_daily_sources():
    source_param = next(param for param in SlashCommandsCog.config_command.parameters if param.name == "source")

    assert [choice.value for choice in source_param.choices] == ["leetcode.com", "sheep", "0x3f"]


def test_settings_embed_displays_language_and_each_independent_push():
    pushes = []
    for index, source in enumerate(("leetcode.com", "sheep", "0x3f"), start=1):
        push = _push(source, channel_id=index, role_id=index + 10)
        push["channel_mention"] = f"<#{index}>"
        push["role_mention"] = f"<@&{index + 10}>"
        pushes.append(push)

    embed = create_settings_embed("Test Guild", pushes=pushes, language="en-US")

    assert [field.name for field in embed.fields] == ["Language", "LeetCode", "Sheep", "0x3f"]
    assert "<#2>" in embed.fields[2].value
    assert "08:00 (Asia/Taipei)" in embed.fields[3].value


@pytest.mark.asyncio
async def test_config_without_updates_displays_language_and_all_pushes(monkeypatch):
    pushes = [_push("leetcode.com"), _push("sheep", channel_id=200)]
    bot = _make_bot(settings={"server_id": 123, "language": "en-US"}, pushes=pushes)
    interaction = _make_interaction()
    embed = discord.Embed(title="settings")
    create_embed = MagicMock(return_value=embed)
    monkeypatch.setattr(slash_module, "create_settings_embed", create_embed)

    await _invoke_config(SlashCommandsCog(bot), interaction)

    kwargs = create_embed.call_args.kwargs
    assert kwargs["language"] == "en-US"
    assert [push["source"] for push in kwargs["pushes"]] == ["leetcode.com", "sheep"]
    interaction.response.send_message.assert_awaited_once_with(embed=embed, ephemeral=True)


@pytest.mark.asyncio
async def test_source_less_push_update_targets_leetcode_and_preserves_other_fields(monkeypatch):
    current = _push("leetcode.com", channel_id=100, role_id=300)
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"}, pushes=[current])
    interaction = _make_interaction()
    monkeypatch.setattr(slash_module, "create_settings_embed", MagicMock(return_value=discord.Embed()))

    await _invoke_config(SlashCommandsCog(bot), interaction, post_time="9:05")

    bot.db.set_daily_push.assert_called_once_with(123, "leetcode.com", 100, 300, "09:05", "Asia/Taipei")
    bot.reschedule_daily_challenge.assert_awaited_once_with(123, "config", source="leetcode.com")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["leetcode.com", "sheep", "0x3f"])
async def test_config_creates_each_supported_source(source, monkeypatch):
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"})
    interaction = _make_interaction()
    channel = SimpleNamespace(id=555)
    monkeypatch.setattr(slash_module, "create_settings_embed", MagicMock(return_value=discord.Embed()))

    await _invoke_config(SlashCommandsCog(bot), interaction, source=source, channel=channel)

    bot.db.set_daily_push.assert_called_once_with(123, source, 555, None, "00:00", "UTC")
    bot.reschedule_daily_challenge.assert_awaited_once_with(123, "config", source=source)


@pytest.mark.asyncio
async def test_language_only_update_does_not_require_or_create_push(monkeypatch):
    bot = _make_bot()
    interaction = _make_interaction()
    monkeypatch.setattr(slash_module, "create_settings_embed", MagicMock(return_value=discord.Embed()))

    await _invoke_config(SlashCommandsCog(bot), interaction, language="en-US")

    bot.db.set_server_language.assert_called_once_with(123, "en-US")
    bot.db.set_daily_push.assert_not_called()
    bot.reschedule_daily_challenge.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_selected_source_requires_channel():
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"})
    interaction = _make_interaction()

    await _invoke_config(SlashCommandsCog(bot), interaction, source="sheep", timezone="UTC+8")

    bot.db.set_daily_push.assert_not_called()
    assert interaction.response.send_message.await_args.args[0].startswith("errors.config.first_setup_required")


@pytest.mark.asyncio
async def test_config_rejects_role_and_clear_role_conflict():
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"}, pushes=[_push("leetcode.com")])
    interaction = _make_interaction()

    await _invoke_config(SlashCommandsCog(bot), interaction, role=SimpleNamespace(id=42), clear_role=True)

    bot.db.set_daily_push.assert_not_called()
    assert interaction.response.send_message.await_args.args[0].startswith("errors.config.role_clear_conflict")


@pytest.mark.asyncio
async def test_remove_requires_explicit_source():
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"}, pushes=[_push("leetcode.com")])
    interaction = _make_interaction()

    await _invoke_config(SlashCommandsCog(bot), interaction, remove=True)

    assert interaction.response.send_message.await_args.args[0].startswith("errors.config.remove_source_required")


@pytest.mark.asyncio
async def test_remove_and_reset_conflict():
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"}, pushes=[_push("sheep")])
    interaction = _make_interaction()

    await _invoke_config(SlashCommandsCog(bot), interaction, source="sheep", remove=True, reset=True)

    assert interaction.response.send_message.await_args.args[0].startswith("errors.config.remove_conflict")


@pytest.mark.asyncio
async def test_remove_builds_source_specific_confirmation_under_custom_id_limit(monkeypatch):
    bot = _make_bot(settings={"server_id": 123, "language": "zh-TW"}, pushes=[_push("0x3f")])
    interaction = _make_interaction()
    monkeypatch.setattr(slash_module.time, "time", lambda: 9_999_999_999)
    monkeypatch.setattr(slash_module, "create_settings_embed", MagicMock(return_value=discord.Embed()))

    await _invoke_config(SlashCommandsCog(bot), interaction, source="0x3f", remove=True)

    view = interaction.response.send_message.await_args.kwargs["view"]
    custom_ids = [item.custom_id for item in view.children]
    assert custom_ids == [
        "config_remove_confirm|123|9999999999999999999|10000000179|0x3f",
        "config_remove_cancel|123|9999999999999999999|10000000179|0x3f",
    ]
    assert max(map(len, custom_ids)) <= 100
