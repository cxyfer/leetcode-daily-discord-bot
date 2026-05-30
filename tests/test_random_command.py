import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from discord.ext import commands

from bot.api_client import (
    ApiEmbeddingError,
    ApiEmbeddingTimeoutError,
    ApiError,
    ApiNetworkError,
    ApiProcessingError,
    ApiRateLimitError,
    OjApiClient,
)
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


def _problem_list_response(total: int, problems: list[dict] | None = None, page: int = 1) -> dict:
    return {
        "data": problems or [],
        "meta": {
            "total": total,
            "page": page,
            "per_page": 1,
            "total_pages": total,
        },
    }


# -- similar search tests --


@pytest.mark.asyncio
async def test_search_similar_by_text_uses_post_json_body():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    await api.search_similar_by_text("graph dp", source="leetcode", top_k=7, min_similarity=0.82, timeout=123)

    api._request.assert_awaited_once()
    args, kwargs = api._request.await_args
    assert args == ("POST", "similar")
    assert kwargs["json"] == {"query": "graph dp", "limit": 7, "threshold": 0.82, "source": "leetcode"}
    assert kwargs["timeout"].total == 123


@pytest.mark.asyncio
async def test_search_similar_by_id_keeps_existing_get_endpoint():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    await api.search_similar_by_id("atcoder", "abc100_a", top_k=3, min_similarity=0.91, timeout=456)

    api._request.assert_awaited_once()
    args, kwargs = api._request.await_args
    assert args == ("GET", "similar/atcoder/abc100_a")
    assert kwargs["params"] == {"limit": "3", "threshold": "0.91"}
    assert kwargs["timeout"].total == 456


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (502, ApiEmbeddingError),
        (504, ApiEmbeddingTimeoutError),
    ],
)
async def test_do_request_raises_embedding_specific_errors(status, expected_error):
    api = OjApiClient("http://test")
    response = AsyncMock()
    response.status = status
    response.json.return_value = {"detail": "embedding failed"}
    request_context = AsyncMock()
    request_context.__aenter__.return_value = response
    session = MagicMock()
    session.request.return_value = request_context
    api._session = session

    with pytest.raises(expected_error) as exc_info:
        await api._do_request("GET", "similar/leetcode/1")

    assert str(exc_info.value) == "embedding failed"


@pytest.mark.asyncio
async def test_do_request_raises_api_error_for_similar_404():
    api = OjApiClient("http://test")
    response = AsyncMock()
    response.status = 404
    response.json.return_value = {"detail": "not indexed"}
    request_context = AsyncMock()
    request_context.__aenter__.return_value = response
    session = MagicMock()
    session.request.return_value = request_context
    api._session = session

    with pytest.raises(ApiError) as exc_info:
        await api._do_request("GET", "similar/leetcode/1")

    assert exc_info.value.status == 404
    assert exc_info.value.detail == "not indexed"


@pytest.mark.asyncio
async def test_do_request_keeps_non_similar_404_as_none():
    api = OjApiClient("http://test")
    response = AsyncMock()
    response.status = 404
    request_context = AsyncMock()
    request_context.__aenter__.return_value = response
    session = MagicMock()
    session.request.return_value = request_context
    api._session = session

    assert await api._do_request("GET", "problems/leetcode/1") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [502, 504])
async def test_do_request_keeps_non_similar_gateway_errors_generic(status):
    api = OjApiClient("http://test")
    response = AsyncMock()
    response.status = status
    response.json.return_value = {"detail": "gateway error"}
    request_context = AsyncMock()
    request_context.__aenter__.return_value = response
    session = MagicMock()
    session.request.return_value = request_context
    api._session = session

    with pytest.raises(ApiError) as exc_info:
        await api._do_request("GET", "daily")

    assert exc_info.value.status == status
    assert exc_info.value.detail == "gateway error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (502, ApiEmbeddingError),
        (504, ApiEmbeddingTimeoutError),
    ],
)
async def test_do_request_retry_uses_embedding_specific_errors(status, expected_error, monkeypatch):
    api = OjApiClient("http://test")
    monkeypatch.setattr("bot.api_client.asyncio.sleep", AsyncMock())

    first_response = AsyncMock()
    first_response.status = 429
    first_response.headers = {"Retry-After": "0"}
    retry_response = AsyncMock()
    retry_response.status = status
    retry_response.json.return_value = {"detail": "embedding failed after retry"}

    first_context = AsyncMock()
    first_context.__aenter__.return_value = first_response
    retry_context = AsyncMock()
    retry_context.__aenter__.return_value = retry_response
    session = MagicMock()
    session.request.side_effect = [first_context, retry_context]
    api._session = session

    with pytest.raises(expected_error) as exc_info:
        await api._do_request("GET", "similar/leetcode/1")

    assert str(exc_info.value) == "embedding failed after retry"


@pytest.mark.asyncio
async def test_do_request_wraps_timeout_as_timeout_network_error():
    api = OjApiClient("http://test")
    session = MagicMock()
    session.request.side_effect = asyncio.TimeoutError("request timed out")
    api._session = session

    with pytest.raises(ApiNetworkError) as exc_info:
        await api._do_request("GET", "daily")

    assert exc_info.value.is_timeout is True


@pytest.mark.asyncio
async def test_do_request_wraps_client_error_as_non_timeout_network_error():
    api = OjApiClient("http://test")
    session = MagicMock()
    session.request.side_effect = aiohttp.ClientConnectionError("connection reset")
    api._session = session

    with pytest.raises(ApiNetworkError) as exc_info:
        await api._do_request("GET", "daily")

    assert exc_info.value.is_timeout is False


@pytest.mark.asyncio
async def test_request_omits_none_timeout_for_session_default():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._do_request = AsyncMock(return_value={"ok": True})

    await api._request("GET", "daily", timeout=None)

    api._do_request.assert_awaited_once_with("GET", "daily")


@pytest.mark.asyncio
async def test_do_request_raises_api_error_for_similar_text_404():
    api = OjApiClient("http://test")
    response = AsyncMock()
    response.status = 404
    response.json.return_value = {"detail": "not indexed"}
    request_context = AsyncMock()
    request_context.__aenter__.return_value = response
    session = MagicMock()
    session.request.return_value = request_context
    api._session = session

    with pytest.raises(ApiError) as exc_info:
        await api._do_request("POST", "similar")

    assert exc_info.value.status == 404
    assert exc_info.value.detail == "not indexed"


@pytest.mark.asyncio
async def test_request_inflight_key_includes_timeout():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._inflight["GET:similar/leetcode/1?limit=5&threshold=0.7|timeout=300"] = asyncio.get_event_loop().create_future()
    api._do_request = AsyncMock(return_value={"results": []})

    await api._request(
        "GET",
        "similar/leetcode/1",
        params={"limit": "5", "threshold": "0.7"},
        timeout=MagicMock(total=600),
    )

    api._do_request.assert_awaited_once()


# -- get_random_problem tests --


@pytest.mark.asyncio
async def test_get_random_problem_returns_none_on_empty_results():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    result = await api.get_random_problem()

    assert result is None
    api._request.assert_called_once_with("GET", "random", params={"count": 1})


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
    api._request = AsyncMock(return_value={"results": []})

    await api.get_random_problem(rating_min=2000, rating_max=1500)

    api._request.assert_called_once_with(
        "GET",
        "random",
        params={"count": 1, "rating_min": 1500, "rating_max": 2000},
    )


@pytest.mark.asyncio
async def test_get_random_problem_passes_all_filters():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    await api.get_random_problem(source="leetcode", difficulty="Medium", tags="Array", rating_min=1500, rating_max=2000)

    api._request.assert_called_once_with(
        "GET",
        "random",
        params={
            "count": 1,
            "source": "leetcode",
            "difficulty": "medium",
            "tags": "Array",
            "rating_min": 1500,
            "rating_max": 2000,
        },
    )


@pytest.mark.asyncio
async def test_get_random_problem_source_default_omitted():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    await api.get_random_problem()

    api._request.assert_called_once_with("GET", "random", params={"count": 1})


@pytest.mark.asyncio
async def test_get_random_problem_source_all_omitted():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": []})

    await api.get_random_problem(source="all")

    api._request.assert_called_once_with("GET", "random", params={"count": 1})


@pytest.mark.asyncio
async def test_get_random_problem_returns_first_result():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": [_sample_problem(), _sample_problem("2")]})

    result = await api.get_random_problem()

    assert result == _sample_problem()


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
async def test_get_random_problem_accepts_legacy_results_shape():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value={"results": [_sample_problem()]})

    result = await api.get_random_problem()

    assert result == _sample_problem()


# -- /random command tests --


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

    bot.api.get_random_problem.assert_called_once_with(
        source="leetcode", difficulty="Medium", tags=None, rating_min=None, rating_max=None
    )


@pytest.mark.asyncio
async def test_random_command_with_source():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, source="atcoder")

    bot.api.get_random_problem.assert_called_once_with(
        source="atcoder", difficulty=None, tags=None, rating_min=None, rating_max=None
    )


@pytest.mark.asyncio
async def test_random_command_with_all_filters():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(
        cog, interaction, source="codeforces", difficulty="Hard", tags="DP", rating_min=1500, rating_max=2500
    )

    bot.api.get_random_problem.assert_called_once_with(
        source="codeforces", difficulty="Hard", tags="DP", rating_min=1500, rating_max=2500
    )


@pytest.mark.asyncio
async def test_random_command_swaps_rating_before_api():
    bot = _make_bot()
    bot.api.get_random_problem.return_value = _sample_problem()
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()

    await cog.random_command.callback(cog, interaction, rating_min=2000, rating_max=1500)

    bot.api.get_random_problem.assert_called_once_with(
        source="leetcode", difficulty=None, tags=None, rating_min=1500, rating_max=2000
    )


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

    bot.api.get_random_problem.assert_called_once_with(
        source="leetcode", difficulty=None, tags=None, rating_min=1500, rating_max=1500
    )


# -- get_tags tests --


@pytest.mark.asyncio
async def test_get_tags_returns_list_on_200():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value=["Array", "DP", "Graph"])

    result = await api.get_tags("leetcode")

    assert result == ["Array", "DP", "Graph"]
    api._request.assert_awaited_once_with("GET", "tags/leetcode")


@pytest.mark.asyncio
async def test_get_tags_returns_empty_on_400():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiError(400, "Bad Request"))

    result = await api.get_tags("invalid")

    assert result == []


@pytest.mark.asyncio
async def test_get_tags_returns_empty_on_404():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value=None)

    result = await api.get_tags("nonexistent")

    assert result == []


@pytest.mark.asyncio
async def test_get_tags_propagates_api_error_500():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiError(500, "Internal Server Error"))

    with pytest.raises(ApiError):
        await api.get_tags("leetcode")


@pytest.mark.asyncio
async def test_get_tags_propagates_network_error():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiNetworkError("timeout"))

    with pytest.raises(ApiNetworkError):
        await api.get_tags("leetcode")


# -- get_tags_cached tests --


@pytest.mark.asyncio
async def test_get_tags_cached_hit_skips_api():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock()
    api._tags_cache["leetcode"] = (1000000.0, ["Array", "DP"])

    with patch("time.time", return_value=1000100.0):
        result = await api.get_tags_cached("leetcode")

    assert result == ["Array", "DP"]
    api._request.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_tags_cached_miss_calls_api():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(return_value=["Graph", "Tree"])

    with patch("time.time", return_value=2000000.0):
        result = await api.get_tags_cached("leetcode")

    assert result == ["Graph", "Tree"]
    assert api._tags_cache["leetcode"] == (2000000.0, ["Graph", "Tree"])


@pytest.mark.asyncio
async def test_get_tags_cached_expired_refreshes():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._tags_cache["leetcode"] = (3000000.0, ["Old"])
    api._request = AsyncMock(return_value=["New"])

    with patch("time.time", return_value=3000000.0 + 86401):
        result = await api.get_tags_cached("leetcode")

    assert result == ["New"]
    assert api._tags_cache["leetcode"] == (3000000.0 + 86401, ["New"])


@pytest.mark.asyncio
async def test_get_tags_cached_stale_fallback():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._tags_cache["leetcode"] = (4000000.0, ["Stale"])
    api._request = AsyncMock(side_effect=ApiNetworkError("timeout"))

    with patch("time.time", return_value=4000000.0 + 86401):
        result = await api.get_tags_cached("leetcode")

    assert result == ["Stale"]


@pytest.mark.asyncio
async def test_get_tags_cached_stale_fallback_on_processing_error():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._tags_cache["leetcode"] = (5000000.0, ["Stale"])
    api._request = AsyncMock(side_effect=ApiProcessingError())

    with patch("time.time", return_value=5000000.0 + 86401):
        result = await api.get_tags_cached("leetcode")

    assert result == ["Stale"]


@pytest.mark.asyncio
async def test_get_tags_cached_stale_fallback_on_rate_limit():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._tags_cache["leetcode"] = (6000000.0, ["Stale"])
    api._request = AsyncMock(side_effect=ApiRateLimitError(5.0))

    with patch("time.time", return_value=6000000.0 + 86401):
        result = await api.get_tags_cached("leetcode")

    assert result == ["Stale"]


@pytest.mark.asyncio
async def test_get_tags_cached_no_cache_api_failure_returns_empty():
    api = OjApiClient("http://test")
    api._session = AsyncMock()
    api._request = AsyncMock(side_effect=ApiNetworkError("timeout"))

    result = await api.get_tags_cached("spoj")

    assert result == []


# -- tags autocomplete tests --


@pytest.mark.asyncio
async def test_tags_autocomplete_returns_filtered_choices():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Array", "DP", "Graph", "Tree", "Sort"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "leetcode"

    result = await cog.random_tags_autocomplete(interaction, "ar")

    assert len(result) == 1
    assert result[0].name == "Array"
    assert result[0].value == "Array"


@pytest.mark.asyncio
async def test_tags_autocomplete_defaults_to_leetcode():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Array", "DP"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = None

    await cog.random_tags_autocomplete(interaction, "a")

    bot.api.get_tags_cached.assert_awaited_once_with("leetcode")


@pytest.mark.asyncio
async def test_tags_autocomplete_no_namespace_defaults_to_leetcode():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Array"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = None

    await cog.random_tags_autocomplete(interaction, "a")

    bot.api.get_tags_cached.assert_awaited_once_with("leetcode")


@pytest.mark.asyncio
async def test_tags_autocomplete_api_failure_returns_empty():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(side_effect=ApiNetworkError("timeout"))
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "leetcode"

    result = await cog.random_tags_autocomplete(interaction, "a")

    assert result == []


@pytest.mark.asyncio
async def test_tags_autocomplete_no_matches_returns_empty():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Array", "DP"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "leetcode"

    result = await cog.random_tags_autocomplete(interaction, "xyz")

    assert result == []


@pytest.mark.asyncio
async def test_tags_autocomplete_respects_source_change():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Brute Force", "Greedy"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "codeforces"

    await cog.random_tags_autocomplete(interaction, "g")

    bot.api.get_tags_cached.assert_awaited_once_with("codeforces")


@pytest.mark.asyncio
async def test_tags_autocomplete_source_all_defaults_to_leetcode():
    bot = _make_bot()
    bot.api.get_tags_cached = AsyncMock(return_value=["Array"])
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "all"

    await cog.random_tags_autocomplete(interaction, "a")

    bot.api.get_tags_cached.assert_awaited_once_with("leetcode")


@pytest.mark.asyncio
async def test_tags_autocomplete_limits_to_25():
    bot = _make_bot()
    tags = [f"Tag{i}" for i in range(50)]
    bot.api.get_tags_cached = AsyncMock(return_value=tags)
    cog = SlashCommandsCog(bot)
    interaction = _make_interaction()
    interaction.namespace = MagicMock()
    interaction.namespace.source = "leetcode"

    result = await cog.random_tags_autocomplete(interaction, "Tag")

    assert len(result) == 25
