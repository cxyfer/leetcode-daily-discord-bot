"""
Unit tests for monthly daily challenge fetching functionality
"""
import pytest
import pytest_asyncio
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the module to test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leetcode import LeetCodeClient


class TestMonthlyFetch:
    """Test cases for monthly daily challenge fetching"""
    
    @pytest_asyncio.fixture
    async def client(self, tmp_path):
        """Create a LeetCodeClient instance for testing"""
        db_path = tmp_path / "test.db"
        client = LeetCodeClient(domain="com", db_path=str(db_path))
        yield client
        # Cleanup
        await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_fetch_monthly_daily_challenges_success(self, client):
        """Test successful fetching of monthly challenges"""
        # Mock response data
        mock_response = {
            "data": {
                "dailyCodingChallengeV2": {
                    "challenges": [
                        {
                            "date": "2025-01-01",
                            "userStatus": "NotStart",
                            "link": "/problems/two-sum/",
                            "question": {
                                "questionFrontendId": "1",
                                "title": "Two Sum",
                                "titleSlug": "two-sum"
                            }
                        },
                        {
                            "date": "2025-01-02",
                            "userStatus": "NotStart",
                            "link": "/problems/add-two-numbers/",
                            "question": {
                                "questionFrontendId": "2",
                                "title": "Add Two Numbers",
                                "titleSlug": "add-two-numbers"
                            }
                        }
                    ],
                    "weeklyChallenges": []
                }
            }
        }
        
        # Mock the HTTP request
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await client.fetch_monthly_daily_challenges(2025, 1)
            
            assert result['year'] == 2025
            assert result['month'] == 1
            assert len(result['challenges']) == 2
            assert result['challenges'][0]['question_id'] == "1"
            assert result['challenges'][0]['title'] == "Two Sum"
    
    @pytest.mark.asyncio
    async def test_fetch_monthly_daily_challenges_network_error(self, client):
        """Test handling of network errors"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.side_effect = aiohttp.ClientError("Network error")
            
            result = await client.fetch_monthly_daily_challenges(2025, 1)
            
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_fetch_monthly_daily_challenges_api_error(self, client):
        """Test handling of API errors"""
        mock_response = {
            "errors": [{"message": "API Error"}]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await client.fetch_monthly_daily_challenges(2025, 1)
            
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_daily_challenge_with_monthly_fetch(self, client):
        """Test get_daily_challenge triggering monthly fetch when data not found"""
        # Mock the database to return None (no data found)
        client.daily_db.get_daily = Mock(return_value=None)
        
        # Mock fetch_daily_challenge to return None
        client.fetch_daily_challenge = AsyncMock(return_value=None)
        
        # Mock fetch_monthly_daily_challenges
        mock_monthly_data = {
            'challenges': [
                {
                    'date': '2025-01-15',
                    'question_id': '123',
                    'slug': 'test-problem'
                }
            ]
        }
        client.fetch_monthly_daily_challenges = AsyncMock(return_value=mock_monthly_data)
        
        # Mock get_problem
        mock_problem = {
            'id': '123',
            'slug': 'test-problem',
            'title': 'Test Problem',
            'difficulty': 'Medium',
            'rating': 1500
        }
        client.get_problem = AsyncMock(return_value=mock_problem)
        
        # Mock update_daily
        client.daily_db.update_daily = Mock()
        
        # Mock _process_remaining_monthly_challenges
        client._process_remaining_monthly_challenges = AsyncMock()
        
        result = await client.get_daily_challenge('2025-01-15', 'com')
        
        assert result is not None
        assert result['date'] == '2025-01-15'
        assert result['id'] == '123'
        assert result['title'] == 'Test Problem'
        assert result['rating'] == 1500
    
    @pytest.mark.asyncio
    async def test_process_remaining_monthly_challenges(self, client):
        """Test background processing of remaining challenges"""
        challenges = [
            {
                'date': '2025-01-02',
                'question_id': '2',
                'slug': 'add-two-numbers'
            },
            {
                'date': '2025-01-03',
                'question_id': '3',
                'slug': 'longest-substring'
            }
        ]
        
        # Mock get_problem
        mock_problems = {
            '2': {
                'id': '2',
                'slug': 'add-two-numbers',
                'title': 'Add Two Numbers',
                'rating': 1600
            },
            '3': {
                'id': '3',
                'slug': 'longest-substring',
                'title': 'Longest Substring',
                'rating': 1700
            }
        }
        
        async def mock_get_problem(problem_id=None, slug=None):
            return mock_problems.get(problem_id)
        
        client.get_problem = mock_get_problem
        client.daily_db.update_daily = Mock()
        
        # Mock config for delay
        with patch('leetcode.get_config') as mock_config:
            mock_config.return_value.get.return_value = 0.01  # Short delay for testing
            
            await client._process_remaining_monthly_challenges(challenges, 'com', '2025', '01')
        
        # Verify all challenges were processed
        assert client.daily_db.update_daily.call_count == 2
        
        # Verify the data structure
        first_call = client.daily_db.update_daily.call_args_list[0][0][0]
        assert first_call['date'] == '2025-01-02'
        assert first_call['id'] == '2'
        assert first_call['rating'] == 1600
    
    @pytest.mark.asyncio
    async def test_process_remaining_monthly_challenges_with_errors(self, client):
        """Test error handling in background processing"""
        challenges = [
            {
                'date': '2025-01-02',
                'question_id': '2',
                'slug': 'add-two-numbers'
            },
            {
                'date': '2025-01-03',
                'question_id': None,  # Missing question_id
                'slug': 'longest-substring'
            }
        ]
        
        # Mock get_problem to raise an error for the first challenge
        async def mock_get_problem(problem_id=None, slug=None):
            if problem_id == '2':
                raise aiohttp.ClientError("Network error")
            return None
        
        client.get_problem = mock_get_problem
        client.daily_db.update_daily = Mock()
        
        # Mock config for delay
        with patch('leetcode.get_config') as mock_config:
            mock_config.return_value.get.return_value = 0.01
            
            await client._process_remaining_monthly_challenges(challenges, 'com', '2025', '01')
        
        # Verify no updates were made due to errors
        assert client.daily_db.update_daily.call_count == 0
    
    @pytest.mark.asyncio
    async def test_background_task_cancellation(self, client):
        """Test cancellation handling in background processing"""
        challenges = [{'date': '2025-01-02', 'question_id': '2', 'slug': 'test'}]
        
        # Mock get_problem to simulate cancellation
        async def mock_get_problem(problem_id=None, slug=None):
            raise asyncio.CancelledError()
        
        client.get_problem = mock_get_problem
        
        with pytest.raises(asyncio.CancelledError):
            await client._process_remaining_monthly_challenges(challenges, 'com', '2025', '01')
    
    @pytest.mark.asyncio
    async def test_concurrent_fetch_limit(self, client):
        """Test that semaphore limits concurrent API requests"""
        # Create many challenges to test concurrency
        challenges = [
            {
                'date': f'2025-01-{i:02d}',
                'question_id': str(i),
                'slug': f'problem-{i}'
            }
            for i in range(1, 11)
        ]
        
        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent = 0
        
        async def mock_get_problem(problem_id=None, slug=None):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate API delay
            concurrent_calls -= 1
            return {'id': problem_id, 'rating': 1500}
        
        client.get_problem = mock_get_problem
        client.daily_db.update_daily = Mock()
        
        with patch('leetcode.get_config') as mock_config:
            mock_config.return_value.get.return_value = 0.01
            
            await client._process_remaining_monthly_challenges(challenges, 'com', '2025', '01')
        
        # Verify semaphore limited concurrent calls to 5
        assert max_concurrent <= 5
        assert client.daily_db.update_daily.call_count == 10
    
    @pytest.mark.asyncio
    async def test_fetch_monthly_before_april_2020(self, client):
        """Test that fetching data before April 2020 returns empty result"""
        # Test March 2020 (should fail)
        result = await client.fetch_monthly_daily_challenges(2020, 3)
        assert result == {}
        
        # Test year 2019 (should fail)
        result = await client.fetch_monthly_daily_challenges(2019, 12)
        assert result == {}
        
        # Test April 2020 (should work, but we'll mock empty response)
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "data": {"dailyCodingChallengeV2": {"challenges": [], "weeklyChallenges": []}}
            })
            
            result = await client.fetch_monthly_daily_challenges(2020, 4)
            assert result['year'] == 2020
            assert result['month'] == 4
    
    @pytest.mark.asyncio
    async def test_fetch_monthly_with_weekly_challenges(self, client):
        """Test fetching monthly challenges including weekly challenges"""
        # Mock response data with weekly challenges
        mock_response = {
            "data": {
                "dailyCodingChallengeV2": {
                    "challenges": [
                        {
                            "date": "2025-01-01",
                            "userStatus": "NotStart",
                            "link": "/problems/two-sum/",
                            "question": {
                                "questionFrontendId": "1",
                                "title": "Two Sum",
                                "titleSlug": "two-sum"
                            }
                        }
                    ],
                    "weeklyChallenges": [
                        {
                            "date": "2025-01-07",
                            "userStatus": "NotStart",
                            "link": "/problems/weekly-challenge-1/",
                            "question": {
                                "questionFrontendId": "W1",
                                "title": "Weekly Challenge 1",
                                "titleSlug": "weekly-challenge-1",
                                "isPaidOnly": False
                            }
                        },
                        {
                            "date": "2025-01-14",
                            "userStatus": "NotStart",
                            "link": "/problems/weekly-challenge-2/",
                            "question": {
                                "questionFrontendId": "W2",
                                "title": "Weekly Challenge 2",
                                "titleSlug": "weekly-challenge-2",
                                "isPaidOnly": True
                            }
                        }
                    ]
                }
            }
        }
        
        # Mock the HTTP request
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await client.fetch_monthly_daily_challenges(2025, 1)
            
            assert result['year'] == 2025
            assert result['month'] == 1
            assert len(result['challenges']) == 1
            assert len(result['weekly_challenges']) == 2
            
            # Verify weekly challenges are correctly formatted
            weekly1 = result['weekly_challenges'][0]
            assert weekly1['question_id'] == 'W1'
            assert weekly1['title'] == 'Weekly Challenge 1'
            assert weekly1['slug'] == 'weekly-challenge-1'
            assert weekly1['paid_only'] is False
            
            weekly2 = result['weekly_challenges'][1]
            assert weekly2['question_id'] == 'W2'
            assert weekly2['paid_only'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])