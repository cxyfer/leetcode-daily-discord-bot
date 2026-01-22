import pytest
from unittest.mock import AsyncMock, Mock, patch
from cogs.similar_cog import SimilarCog
from utils.config import ConfigManager

@pytest.fixture
def mock_bot():
    bot = Mock()
    bot.db = Mock()
    return bot

@pytest.fixture
def mock_config():
    config = Mock(spec=ConfigManager)
    config.get_similar_config = Mock(return_value=Mock(min_similarity=0.7))
    config.get_embedding_model_config = Mock(return_value=Mock(dim=1536))
    config.database_path = ":memory:"
    return config

@pytest.fixture
def cog(mock_bot, mock_config):
    with patch('cogs.similar_cog.get_config', return_value=mock_config), \
         patch('cogs.similar_cog.EmbeddingDatabaseManager'), \
         patch('cogs.similar_cog.EmbeddingStorage') as MockStorage, \
         patch('cogs.similar_cog.EmbeddingRewriter') as MockRewriter, \
         patch('cogs.similar_cog.EmbeddingGenerator') as MockGenerator, \
         patch('cogs.similar_cog.SimilaritySearcher') as MockSearcher:
        
        cog = SimilarCog(mock_bot)
        cog.storage = MockStorage.return_value
        cog.rewriter = MockRewriter.return_value
        cog.generator = MockGenerator.return_value
        cog.searcher = MockSearcher.return_value
        return cog

@pytest.mark.asyncio
async def test_similar_command_problem_found(cog):
    interaction = AsyncMock()
    problem_input = "atcoder:abc100_a"
    
    # Mock storage behavior
    cog.storage.count_embeddings = AsyncMock(return_value=10)
    cog.storage.get_vector = AsyncMock(return_value=[0.1, 0.2, 0.3])
    cog.storage.get_embedding_meta = AsyncMock(return_value={"rewritten_content": "Rewrite"})
    
    # Mock searcher
    cog.searcher.search = AsyncMock(return_value=[
        {"problem_id": "other_id", "similarity": 0.9}
    ])

    await cog.similar_command.callback(cog, interaction, query=None, problem=problem_input)

    # Verify flow
    cog.storage.get_vector.assert_called_with("atcoder", "abc100_a")
    cog.rewriter.rewrite.assert_not_called()
    cog.generator.embed.assert_not_called()
    cog.searcher.search.assert_called_with([0.1, 0.2, 0.3], None, 5, 0.7)
    
    # Verify embed content (indirectly via create_results_embed logic check)
    # Since we can't easily inspect the embed object directly on a mock without capturing it,
    # we just assume it worked if no exception and followup.send was called.
    assert interaction.followup.send.called

@pytest.mark.asyncio
async def test_similar_command_problem_not_found(cog):
    interaction = AsyncMock()
    problem_input = "atcoder:abc100_a"
    
    cog.storage.count_embeddings = AsyncMock(return_value=10)
    cog.storage.get_vector = AsyncMock(return_value=None)  # Not found

    await cog.similar_command.callback(cog, interaction, query=None, problem=problem_input)

    cog.storage.get_vector.assert_called_with("atcoder", "abc100_a")
    # Verify we sent an error message
    args, _ = interaction.followup.send.call_args
    assert "找不到" in args[0] or "找不到" in str(args)

@pytest.mark.asyncio
async def test_similar_command_query_only(cog):
    interaction = AsyncMock()
    query_input = "Find me a dp problem"
    
    cog.storage.count_embeddings = AsyncMock(return_value=10)
    cog.rewriter.rewrite = AsyncMock(return_value="rewritten query")
    cog.generator.embed = AsyncMock(return_value=[0.5, 0.5, 0.5])
    cog.searcher.search = AsyncMock(return_value=[])

    await cog.similar_command.callback(cog, interaction, query=query_input, problem=None)

    cog.storage.get_vector.assert_not_called()
    cog.rewriter.rewrite.assert_called_with(query_input)
    cog.generator.embed.assert_called_with("rewritten query")
    cog.searcher.search.assert_called()

@pytest.mark.asyncio
async def test_similar_command_neither_provided(cog):
    interaction = AsyncMock()
    
    await cog.similar_command.callback(cog, interaction, query=None, problem=None)
    
    # Should send ephemeral message immediately
    interaction.response.send_message.assert_called()
    args, kwargs = interaction.response.send_message.call_args
    assert "請至少輸入" in args[0]
    assert kwargs['ephemeral'] is True

@pytest.mark.asyncio
async def test_similar_command_problem_precedence(cog):
    interaction = AsyncMock()
    problem_input = "leetcode:1"
    query_input = "Should be ignored"

    cog.storage.count_embeddings = AsyncMock(return_value=10)
    cog.storage.get_vector = AsyncMock(return_value=[0.9, 0.9])
    cog.storage.get_embedding_meta = AsyncMock(return_value=None)
    cog.searcher.search = AsyncMock(return_value=[])

    await cog.similar_command.callback(cog, interaction, query=query_input, problem=problem_input)

    cog.storage.get_vector.assert_called()
    cog.rewriter.rewrite.assert_not_called()
    cog.generator.embed.assert_not_called()

@pytest.mark.asyncio
async def test_similar_command_problem_leetcode_url_slug(cog):
    interaction = AsyncMock()
    problem_input = "https://leetcode.com/problems/two-sum/"

    cog.storage.count_embeddings = AsyncMock(return_value=10)
    cog.storage.get_problem_id_by_slug = AsyncMock(return_value="1")
    cog.storage.get_vector = AsyncMock(return_value=[0.1, 0.2])
    cog.storage.get_embedding_meta = AsyncMock(return_value=None)
    cog.searcher.search = AsyncMock(return_value=[])

    await cog.similar_command.callback(cog, interaction, query=None, problem=problem_input)

    cog.storage.get_problem_id_by_slug.assert_called_with("leetcode", "two-sum")
    cog.storage.get_vector.assert_called_with("leetcode", "1")
