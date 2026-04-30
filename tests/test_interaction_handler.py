# tests/test_interaction_handler.py
import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from bot.cogs import interaction_handler_cog as interaction_handler_module
from bot.cogs.interaction_handler_cog import InteractionHandlerCog
from bot.utils.ui_helpers import create_similar_results_message


class TestInteractionHandler:
    """Test cases for InteractionHandlerCog duplicate request prevention"""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance"""
        bot = MagicMock(spec=commands.Bot)
        bot.logger = MagicMock()
        bot.llm_translate_db = MagicMock()
        bot.llm_inspire_db = MagicMock()
        bot.api = AsyncMock()
        bot.lcus = AsyncMock()
        bot.lcus.problems_db = MagicMock()
        bot.llm = AsyncMock()
        bot.llm_pro = AsyncMock()
        bot.config = MagicMock()
        bot.config.default_locale = "zh-TW"
        bot.i18n = MagicMock()
        bot.i18n.t = MagicMock(side_effect=lambda key, locale, **kwargs: key.replace(".", "_"))
        bot.i18n.resolve_locale = MagicMock(return_value="zh-TW")
        return bot

    @pytest.fixture
    def cog(self, mock_bot):
        """Create an InteractionHandlerCog instance"""
        return InteractionHandlerCog(mock_bot)

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction"""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.user = MagicMock()
        interaction.user.id = 123456789
        interaction.user.name = "test_user"
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.type = discord.InteractionType.component
        interaction.guild = MagicMock()
        interaction.guild.id = 987654321
        interaction.guild_locale = None
        interaction.locale = discord.Locale.taiwan_chinese
        return interaction

    @pytest.mark.asyncio
    async def test_duplicate_request_prevention_translate(self, cog, mock_interaction):
        """Test that duplicate translation requests are prevented"""
        # Setup
        mock_interaction.data = {"custom_id": "leetcode_translate_1234_com"}
        msg = "正在處理您的翻譯請求，請稍候..."

        # First request should succeed
        result1 = await cog._check_duplicate_llm(mock_interaction, (123456789, "1234", "translate"), msg)
        assert result1 is False  # Not a duplicate
        assert (123456789, "1234", "translate") in cog.ongoing_llm_requests

        # Second request should be blocked
        result2 = await cog._check_duplicate_llm(mock_interaction, (123456789, "1234", "translate"), msg)
        assert result2 is True  # Is a duplicate
        mock_interaction.followup.send.assert_called_with(msg, ephemeral=True)

    @pytest.mark.asyncio
    async def test_duplicate_request_prevention_inspire(self, cog, mock_interaction):
        """Test that duplicate inspiration requests are prevented"""
        # Setup
        mock_interaction.data = {"custom_id": "leetcode_inspire_1234_com"}
        msg = "正在處理您的靈感啟發請求，請稍候..."

        # First request should succeed
        result1 = await cog._check_duplicate_llm(mock_interaction, (123456789, "1234", "inspire"), msg)
        assert result1 is False  # Not a duplicate
        assert (123456789, "1234", "inspire") in cog.ongoing_llm_requests

        # Second request should be blocked
        result2 = await cog._check_duplicate_llm(mock_interaction, (123456789, "1234", "inspire"), msg)
        assert result2 is True  # Is a duplicate
        mock_interaction.followup.send.assert_called_with(msg, ephemeral=True)

    @pytest.mark.asyncio
    async def test_cleanup_request(self, cog):
        """Test that cleanup properly removes requests"""
        # Add a request
        request_key = (123456789, "1234", "translate")
        cog.ongoing_llm_requests.add(request_key)
        assert request_key in cog.ongoing_llm_requests

        # Clean it up
        await cog._cleanup_request(request_key)
        assert request_key not in cog.ongoing_llm_requests

        # Cleanup non-existent request should not raise error
        await cog._cleanup_request(request_key)  # Should use discard, not remove

    @pytest.mark.asyncio
    async def test_concurrent_requests_atomic(self, cog, mock_interaction):
        """Test that concurrent requests are handled atomically"""
        request_key = (123456789, "1234", "translate")
        results = []

        async def make_request():
            result = await cog._check_duplicate_llm(mock_interaction, request_key, "translate")
            results.append(result)

        # Run 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Only one should succeed (return False), others should be duplicates (return True)
        false_count = results.count(False)
        true_count = results.count(True)

        assert false_count == 1, f"Expected exactly 1 non-duplicate, got {false_count}"
        assert true_count == 9, f"Expected exactly 9 duplicates, got {true_count}"
        assert request_key in cog.ongoing_llm_requests

    @pytest.mark.asyncio
    async def test_different_users_can_request_same_problem(self, cog, mock_interaction):
        """Test that different users can request the same problem simultaneously"""
        # User 1
        interaction1 = AsyncMock(spec=discord.Interaction)
        interaction1.user = MagicMock(id=111, name="user1")
        interaction1.response = AsyncMock()

        # User 2
        interaction2 = AsyncMock(spec=discord.Interaction)
        interaction2.user = MagicMock(id=222, name="user2")
        interaction2.response = AsyncMock()

        # Both users request the same problem
        key1 = (111, "1234", "translate")
        key2 = (222, "1234", "translate")

        result1 = await cog._check_duplicate_llm(interaction1, key1, "translate")
        result2 = await cog._check_duplicate_llm(interaction2, key2, "translate")

        # Both should succeed as they are different users
        assert result1 is False
        assert result2 is False
        assert key1 in cog.ongoing_llm_requests
        assert key2 in cog.ongoing_llm_requests

    @pytest.mark.asyncio
    async def test_same_user_different_problems(self, cog, mock_interaction):
        """Test that same user can request different problems simultaneously"""
        key1 = (123456789, "1234", "translate")
        key2 = (123456789, "5678", "translate")

        result1 = await cog._check_duplicate_llm(mock_interaction, key1, "translate")
        result2 = await cog._check_duplicate_llm(mock_interaction, key2, "translate")

        # Both should succeed as they are different problems
        assert result1 is False
        assert result2 is False
        assert key1 in cog.ongoing_llm_requests
        assert key2 in cog.ongoing_llm_requests

    @pytest.mark.asyncio
    async def test_cleanup_after_error(self, cog, mock_bot, mock_interaction):
        """Test that cleanup happens even after LLM errors"""
        # Setup mock to simulate LLM error
        mock_interaction.data = {"custom_id": "leetcode_translate_1234_com"}
        mock_bot.llm_translate_db.get_translation.return_value = None
        mock_bot.lcus.get_problem.return_value = {"content": "test content"}
        mock_bot.llm.translate.side_effect = Exception("LLM API Error")

        # Simulate the translate button handler with error
        request_key = (123456789, "1234", "translate")
        cog.ongoing_llm_requests.add(request_key)

        # The cleanup should happen in finally block
        await cog._cleanup_request(request_key)
        assert request_key not in cog.ongoing_llm_requests

    @pytest.mark.asyncio
    async def test_lock_prevents_race_condition(self, cog, mock_interaction):
        """Test that the lock prevents race conditions in check-and-add"""
        request_key = (123456789, "1234", "translate")
        check_count = 0
        add_count = 0

        # Patch the lock to track operations
        original_lock = cog.ongoing_llm_requests_lock

        class TrackedLock:
            def __init__(self, lock):
                self.lock = lock

            async def __aenter__(self):
                await self.lock.__aenter__()
                nonlocal check_count
                if request_key not in cog.ongoing_llm_requests:
                    check_count += 1

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal add_count
                if request_key in cog.ongoing_llm_requests and check_count > add_count:
                    add_count += 1
                await self.lock.__aexit__(exc_type, exc_val, exc_tb)

        cog.ongoing_llm_requests_lock = TrackedLock(original_lock)

        # Run concurrent requests
        tasks = [cog._check_duplicate_llm(mock_interaction, request_key, "translate") for _ in range(5)]
        await asyncio.gather(*tasks)

        # Only one check should have found the set empty
        assert check_count == 1, f"Expected 1 successful check, got {check_count}"
        assert add_count == 1, f"Expected 1 add operation, got {add_count}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("custom_id", "expected"),
        [
            ("problem_detail_1290_com", ("leetcode", "1290", "view")),
            ("leetcode_problem_3544_com", ("leetcode", "3544", "desc")),
            ("leetcode_translate_1234_com", ("leetcode", "1234", "translate")),
            ("leetcode_inspire_1234_com", ("leetcode", "1234", "inspire")),
            ("leetcode_similar_1234_com", ("leetcode", "1234", "similar")),
        ],
    )
    async def test_legacy_problem_custom_ids_route_to_unified_handler(
        self, cog, mock_interaction, monkeypatch, custom_id, expected
    ):
        handler = AsyncMock()
        monkeypatch.setattr(cog, "_handle_problem_action", handler)
        mock_interaction.data = {"custom_id": custom_id}

        await cog.on_interaction(mock_interaction)

        handler.assert_awaited_once_with(mock_interaction, *expected)

    @pytest.mark.asyncio
    async def test_malformed_legacy_problem_custom_id_is_ignored(self, cog, mock_interaction, monkeypatch):
        handler = AsyncMock()
        logger_debug = MagicMock()
        monkeypatch.setattr(cog, "_handle_problem_action", handler)
        monkeypatch.setattr(cog.logger, "debug", logger_debug)
        mock_interaction.data = {"custom_id": "leetcode_problem_bad_com"}

        await cog.on_interaction(mock_interaction)

        handler.assert_not_awaited()
        logger_debug.assert_called_once_with("Ignoring unrecognized custom_id: %s", "leetcode_problem_bad_com")

    @pytest.mark.asyncio
    async def test_action_similar_uses_shared_message_builder_and_configured_top_k(
        self, cog, mock_bot, mock_interaction, monkeypatch
    ):
        """題目卡片的 similar flow 應保留 config-driven fetch，並重用 shared builder"""
        mock_bot.config.get_similar_config.return_value = MagicMock(top_k=25, min_similarity=0.82)
        mock_bot.api.search_similar_by_id.return_value = {
            "results": [
                {
                    "id": "1",
                    "source": "leetcode",
                    "title": "Two Sum",
                    "difficulty": "Easy",
                    "similarity": 0.91,
                    "link": "https://example.com/1",
                }
            ]
        }
        sentinel_embed = discord.Embed(title="similar")
        sentinel_view = MagicMock(children=[])
        helper_calls = []

        def fake_create_similar_results_message(result, *, base_source=None, base_id=None, **kwargs):
            helper_calls.append((result, base_source, base_id))
            return sentinel_embed, sentinel_view

        monkeypatch.setattr(
            interaction_handler_module,
            "create_similar_results_message",
            fake_create_similar_results_message,
            raising=False,
        )

        await cog._action_similar(mock_interaction, "leetcode", "42")

        mock_bot.api.search_similar_by_id.assert_awaited_once_with("leetcode", "42", 25, 0.82)
        assert helper_calls == [(mock_bot.api.search_similar_by_id.return_value, "leetcode", "42")]
        mock_interaction.followup.send.assert_awaited_once_with(
            embed=sentinel_embed, view=sentinel_view, ephemeral=True
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "results",
        [
            [
                {
                    "id": "bad|id",
                    "source": "leetcode",
                    "title": "Bad",
                    "difficulty": "Easy",
                    "similarity": 0.91,
                    "link": "https://example.com/bad",
                }
            ],
            [
                {
                    "id": str(i),
                    "source": "leetcode",
                    "title": f"P{i}",
                    "difficulty": "Easy",
                    "similarity": 0.91,
                    "link": f"https://example.com/{i}",
                }
                for i in range(1, 27)
            ],
        ],
    )
    async def test_action_similar_unsafe_results_degrade_to_embed_only(self, cog, mock_bot, mock_interaction, results):
        mock_bot.config.get_similar_config.return_value = MagicMock(top_k=25, min_similarity=0.82)
        mock_bot.api.search_similar_by_id.return_value = {"results": results}

        await cog._action_similar(mock_interaction, "leetcode", "42")

        _, kwargs = mock_interaction.followup.send.call_args
        assert kwargs["view"] is None

    @pytest.mark.asyncio
    async def test_similar_result_detail_button_routes_to_existing_full_problem_card_flow(
        self, cog, mock_bot, mock_interaction
    ):
        _, view = create_similar_results_message(
            {
                "results": [
                    {
                        "id": "P1001",
                        "source": "luogu",
                        "title": "Luogu P1001",
                        "difficulty": "入门",
                        "similarity": 0.91,
                        "link": "https://www.luogu.com.cn/problem/P1001",
                    }
                ]
            }
        )
        mock_interaction.data = {"custom_id": view.children[0].custom_id}
        mock_bot.api.get_problem.return_value = {
            "id": "P1001",
            "source": "luogu",
            "slug": "P1001",
            "title": "Luogu P1001",
            "title_cn": "",
            "difficulty": "入门",
            "ac_rate": None,
            "rating": None,
            "tags": None,
            "link": "https://www.luogu.com.cn/problem/P1001",
            "content": None,
            "content_cn": None,
            "similar_questions": None,
        }

        await cog.on_interaction(mock_interaction)

        mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        _, kwargs = mock_interaction.followup.send.call_args
        assert kwargs["view"].children[0].custom_id == "problem|luogu|P1001|desc"
        assert kwargs["embed"].title.startswith("🔴 P1001:")

    @pytest.mark.asyncio
    async def test_problem_view_button_for_luogu_returns_full_problem_card(self, cog, mock_bot, mock_interaction):
        """多題 overview 的 Luogu 按鈕應回到完整卡片，而不是 description-only 回覆"""
        mock_interaction.data = {"custom_id": "problem|luogu|P1001|view"}
        mock_bot.api.get_problem.return_value = {
            "id": "P1001",
            "source": "luogu",
            "slug": "P1001",
            "title": "Luogu P1001",
            "title_cn": "",
            "difficulty": "入门",
            "ac_rate": None,
            "rating": None,
            "tags": None,
            "link": "https://www.luogu.com.cn/problem/P1001",
            "content": None,
            "content_cn": None,
            "similar_questions": None,
        }

        await cog.on_interaction(mock_interaction)

        mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        _, kwargs = mock_interaction.followup.send.call_args
        assert "embed" in kwargs
        assert "view" in kwargs
        assert kwargs["embed"].title.startswith("🔴 P1001:")
        assert kwargs["view"].children[0].custom_id == "problem|luogu|P1001|desc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
