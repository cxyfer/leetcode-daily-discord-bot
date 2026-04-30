import random
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError, OjApiClient
from bot.cogs.slash_commands_cog import SlashCommandsCog

# -- helpers --


def _make_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    user = MagicMock()
    user.name = "tester"
    user.display_name = "tester"
    user.display_avatar = MagicMock(url="https://example.com/avatar.png")
    interaction.user = user
    return interaction


def _make_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.api = AsyncMock()
    bot.llm = MagicMock()
    bot.llm_pro = MagicMock()
    bot.i18n = MagicMock()
    bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key)
    bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
    return bot


def _sample_problem(problem_id: str = "1", difficulty: str = "Easy") -> dict:
    return {
        "id": problem_id,
        "source": "leetcode",
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": difficulty,
        "ac_rate": 52.34,
        "rating": 1234,
        "tags": ["Array", "Hash Table"],
        "link": "https://leetcode.com/problems/two-sum/",
        "content": None,
        "content_cn": None,
        "similar_questions": None,
    }


# -- get_random_problem tests --


@pytest.mark.asyncio
async def test_get_random_problem_returns_none_on_zero_count():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"total": 0, "results": []})

    result = await api.get_random_problem()
    assert result is None


@pytest.mark.asyncio
async def test_get_random_problem_returns_none_on_empty_response():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value=None)

    result = await api.get_random_problem()
    assert result is None


@pytest.mark.asyncio
async def test_get_random_problem_swaps_rating_when_min_exceeds_max():
    api = OjApiClient("http://test")
    api._session = AsyncMock()

    captured_params = []

    async def fake_request(method, path, **kwargs):
        params = kwargs.get("params", {})
        captured_params.append(params)
        if "page" not in params:
            return {"total": 5, "results": []}
        return {"total": 5, "results": [_sample_problem()]}

    api._request = AsyncMock(side_effect=fake_request)

    await api.get_random_problem(rating_min=2000, rating_max=1500)

    # First call (count) should have swapped values
    assert captured_params[0]["rating_min"] == 1500
    assert captured_params[0]["rating_max"] == 2000


@pytest.mark.asyncio
async def test_get_random_problem_passes_all_filters():
    api = OjApiClient("http://test")
    api._session = AsyncMock()

    captured_params = []

    async def fake_request(method, path, **kwargs):
        params = kwargs.get("params", {})
        captured_params.append(params)
        if "page" not in params:
            return {"total": 3, "results": []}
        return {"total": 3, "results": [_sample_problem()]}

    api._request = AsyncMock(side_effect=fake_request)

    await api.get_random_problem(difficulty="Medium", tags="Array", rating_min=1500, rating_max=2000)

    assert captured_params[0]["difficulty"] == "Medium"
    assert captured_params[0]["tags"] == "Array"
    assert captured_params[0]["rating_min"] == 1500
    assert captured_params[0]["rating_max"] == 2000
    assert captured_params[0]["per_page"] == 1


@pytest.mark.asyncio
async def test_get_random_problem_uses_random_page(monkeypatch):
    api = OjApiClient("http://test")
    api._session = AsyncMock()

    captured_params = []

    async def fake_request(method, path, **kwargs):
        params = kwargs.get("params", {})
        captured_params.append(params)
        if "page" not in params:
            return {"total": 10, "results": []}
        return {"total": 10, "results": [_sample_problem()]}

    api._request = AsyncMock(side_effect=fake_request)
    monkeypatch.setattr(random, "randint", lambda a, b: 7)

    result = await api.get_random_problem()

    assert result is not None
    assert captured_params[1]["page"] == 7


@pytest.mark.asyncio
async def test_get_random_problem_propagates_api_error():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiNetworkError("timeout"))

    with pytest.raises(ApiNetworkError):
        await api.get_random_problem()


@pytest.mark.asyncio
async def test_get_random_problem_propagates_rate_limit():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiRateLimitError(5.0))

    with pytest.raises(ApiRateLimitError):
        await api.get_random_problem()


@pytest.mark.asyncio
async def test_get_random_problem_fallback_on_empty_page():
    api = OjApiClient("http://test")
    api._session = AsyncMock()

    call_count = 0

    async def fake_request(method, path, **kwargs):
        nonlocal call_count
        call_count += 1
        params = kwargs.get("params", {})
        if "page" not in params:
            return {"total": 5, "results": []}
        if call_count == 2:
            return {"total": 5, "results": []}  # random page is empty
        return {"total": 5, "results": [_sample_problem()]}  # fallback page=1

    api._request = AsyncMock(side_effect=fake_request)

    result = await api.get_random_problem()
    assert result is not None
    assert call_count == 3  # count + empty page + fallback


# -- /random command tests --


@pytest.mark.asyncio
async def test_random_command_sends_problem_embed_and_view():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    interaction.response.defer.assert_called_once_with(ephemeral=True)
    assert interaction.followup.send.call_count == 1
    _, kwargs = interaction.followup.send.call_args
    assert "embed" in kwargs
    assert "view" in kwargs


@pytest.mark.asyncio
async def test_random_command_with_difficulty_filter():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem(difficulty="Medium")
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, difficulty="Medium")

    bot.api.get_random_problem.assert_called_once_with(difficulty="Medium", tags=None, rating_min=None, rating_max=None)


@pytest.mark.asyncio
async def test_random_command_with_all_filters():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, difficulty="Hard", tags="DP", rating_min=1500, rating_max=2500)

    bot.api.get_random_problem.assert_called_once_with(difficulty="Hard", tags="DP", rating_min=1500, rating_max=2500)


@pytest.mark.asyncio
async def test_random_command_swaps_rating_before_api():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, rating_min=2000, rating_max=1500)

    bot.api.get_random_problem.assert_called_once_with(difficulty=None, tags=None, rating_min=1500, rating_max=2000)


@pytest.mark.asyncio
async def test_random_command_public_flag():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, public=True)

    interaction.response.defer.assert_called_once_with(ephemeral=False)
    interaction.followup.send.assert_called_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs["ephemeral"] is False


@pytest.mark.asyncio
async def test_random_command_no_results_shows_filter_summary():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = None
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, difficulty="Hard", tags="DP", rating_min=1500, rating_max=2000)

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["ephemeral"] is True
    # i18n.t mock returns the key; verify the key was used
    bot.i18n.t.assert_any_call(
        "errors.validation.random_not_found", "zh-TW", filters="difficulty:Hard, tags:DP, rating:1500-2000"
    )


@pytest.mark.asyncio
async def test_random_command_no_results_always_ephemeral():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = None
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, public=True)

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_random_command_no_results_no_filters():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = None
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    bot.i18n.t.assert_any_call("errors.validation.random_no_filter", "zh-TW")
    bot.i18n.t.assert_any_call(
        "errors.validation.random_not_found", "zh-TW", filters="errors.validation.random_no_filter"
    )


@pytest.mark.asyncio
async def test_random_command_no_results_disables_mentions():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = None
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, tags="@everyone")

    _, kwargs = interaction.followup.send.call_args
    mentions = kwargs["allowed_mentions"]
    assert mentions.everyone is False
    assert mentions.users is False
    assert mentions.roles is False


@pytest.mark.asyncio
async def test_random_command_handles_api_processing_error():
    bot = _make_bot()
    bot.api.get_random_problem.side_effect = ApiProcessingError()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    # send_api_error delegates to i18n.t; verify the key was used
    bot.i18n.t.assert_any_call("errors.api.processing", "zh-TW")


@pytest.mark.asyncio
async def test_random_command_handles_network_error():
    bot = _make_bot()
    bot.api.get_random_problem.side_effect = ApiNetworkError("timeout")
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    bot.i18n.t.assert_any_call("errors.api.network", "zh-TW")


@pytest.mark.asyncio
async def test_random_command_handles_rate_limit():
    bot = _make_bot()
    bot.api.get_random_problem.side_effect = ApiRateLimitError(5.0)
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    bot.i18n.t.assert_any_call("errors.api.rate_limit", "zh-TW")


@pytest.mark.asyncio
async def test_random_command_handles_generic_api_error():
    bot = _make_bot()
    bot.api.get_random_problem.side_effect = ApiError(500, "Internal Server Error")
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction)

    bot.i18n.t.assert_any_call("errors.api.generic", "zh-TW")


@pytest.mark.asyncio
async def test_random_command_rating_same_min_max():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, rating_min=1500, rating_max=1500)

    bot.api.get_random_problem.assert_called_once_with(difficulty=None, tags=None, rating_min=1500, rating_max=1500)
