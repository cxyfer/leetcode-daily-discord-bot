# tests/test_interaction_handler.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from discord.ext import commands

# Import the cog we're testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cogs.interaction_handler_cog import InteractionHandlerCog


class TestInteractionHandler:
    """Test cases for InteractionHandlerCog duplicate request prevention"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance"""
        bot = MagicMock(spec=commands.Bot)
        bot.logger = MagicMock()
        bot.LEETCODE_TRANSLATE_BUTTON_PREFIX = "leetcode_translate_"
        bot.LEETCODE_INSPIRE_BUTTON_PREFIX = "leetcode_inspire_"
        bot.llm_translate_db = MagicMock()
        bot.llm_inspire_db = MagicMock()
        bot.lcus = AsyncMock()
        bot.lccn = AsyncMock()
        bot.llm = AsyncMock()
        bot.llm_pro = AsyncMock()
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
        return interaction
    
    @pytest.mark.asyncio
    async def test_duplicate_request_prevention_translate(self, cog, mock_interaction):
        """Test that duplicate translation requests are prevented"""
        # Setup
        mock_interaction.data = {"custom_id": "leetcode_translate_1234_com"}
        
        # First request should succeed
        result1 = await cog._handle_duplicate_request(mock_interaction, (123456789, "1234", "translate"), "translate")
        assert result1 is False  # Not a duplicate
        assert (123456789, "1234", "translate") in cog.ongoing_llm_requests
        
        # Second request should be blocked
        result2 = await cog._handle_duplicate_request(mock_interaction, (123456789, "1234", "translate"), "translate")
        assert result2 is True  # Is a duplicate
        mock_interaction.response.send_message.assert_called_with("正在處理您的翻譯請求，請稍候...", ephemeral=True)
    
    @pytest.mark.asyncio
    async def test_duplicate_request_prevention_inspire(self, cog, mock_interaction):
        """Test that duplicate inspiration requests are prevented"""
        # Setup
        mock_interaction.data = {"custom_id": "leetcode_inspire_1234_com"}
        
        # First request should succeed
        result1 = await cog._handle_duplicate_request(mock_interaction, (123456789, "1234", "inspire"), "inspire")
        assert result1 is False  # Not a duplicate
        assert (123456789, "1234", "inspire") in cog.ongoing_llm_requests
        
        # Second request should be blocked
        result2 = await cog._handle_duplicate_request(mock_interaction, (123456789, "1234", "inspire"), "inspire")
        assert result2 is True  # Is a duplicate
        mock_interaction.response.send_message.assert_called_with("正在處理您的靈感啟發請求，請稍候...", ephemeral=True)
    
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
            result = await cog._handle_duplicate_request(mock_interaction, request_key, "translate")
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
        
        result1 = await cog._handle_duplicate_request(interaction1, key1, "translate")
        result2 = await cog._handle_duplicate_request(interaction2, key2, "translate")
        
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
        
        result1 = await cog._handle_duplicate_request(mock_interaction, key1, "translate")
        result2 = await cog._handle_duplicate_request(mock_interaction, key2, "translate")
        
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
        tasks = [cog._handle_duplicate_request(mock_interaction, request_key, "translate") for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Only one check should have found the set empty
        assert check_count == 1, f"Expected 1 successful check, got {check_count}"
        assert add_count == 1, f"Expected 1 add operation, got {add_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])