"""
@file: test_workers.py
@description:
Test suite for Celery task workers in the BadBeats API, focusing on:
- Task scheduling and execution
- Task retry mechanisms
- Integration with prediction models
- Game data preparation and processing

@dependencies:
- pytest: For test framework
- unittest.mock: For mocking external services
- celery.contrib.testing: For testing Celery tasks
- app.workers: Worker modules being tested

@notes:
- Tests use mocking to avoid actual task execution
- Task scheduling logic is verified
- Error handling and retry behavior is tested
"""

import pytest
from unittest import mock
import asyncio
from datetime import datetime, timedelta
import pytz

from app.workers.tasks import (
    ingest_nba_data,
    schedule_game_predictions,
    generate_prediction,
    update_game_results,
    _prepare_game_data
)
from app.llm.base_model import PredictionInput, PredictionResult
from app.schemas.predictions import PredictionCreate, PredictionOut


class AsyncMock(mock.MagicMock):
    """Helper class for mocking async functions"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.fixture
def mock_upcoming_games():
    """Fixture providing mock upcoming games data"""
    tomorrow = datetime.now(pytz.UTC) + timedelta(days=1)
    return [
        {
            "id": 12345,
            "date": tomorrow.isoformat(),
            "home_team": {"id": 1, "name": "Lakers"},
            "visitor_team": {"id": 2, "name": "Celtics"},
            "status": "scheduled"
        },
        {
            "id": 12346,
            "date": (tomorrow + timedelta(hours=3)).isoformat(),
            "home_team": {"id": 3, "name": "Warriors"},
            "visitor_team": {"id": 4, "name": "Bucks"},
            "status": "scheduled"
        }
    ]


def test_ingest_nba_data_task():
    """Test NBA data ingestion task."""
    # Mock the asyncio event loop
    mock_loop = mock.MagicMock()
    mock_loop.run_until_complete = mock.MagicMock()
    mock_loop.close = mock.MagicMock()
    
    # Mock get_upcoming_games to return sample data
    mock_get_games = AsyncMock(return_value=[
        {"id": 1, "home_team": {"name": "Lakers"}, "visitor_team": {"name": "Celtics"}},
        {"id": 2, "home_team": {"name": "Warriors"}, "visitor_team": {"name": "Bucks"}}
    ])
    
    # Set up patches
    with mock.patch('asyncio.new_event_loop', return_value=mock_loop), \
         mock.patch('asyncio.set_event_loop'), \
         mock.patch('app.workers.tasks.get_upcoming_games', mock_get_games):
        
        # Run the task
        result = ingest_nba_data()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["games_ingested"] == 2
        
        # Verify the mocks were called correctly
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()


def test_schedule_game_predictions_task(mock_upcoming_games):
    """Test game prediction scheduling task."""
    # Mock the asyncio event loop
    mock_loop = mock.MagicMock()
    mock_loop.run_until_complete = mock.MagicMock(return_value=mock_upcoming_games)
    mock_loop.close = mock.MagicMock()
    
    # Mock the generate_prediction.apply_async method
    mock_apply_async = mock.MagicMock()
    
    # Set up patches
    with mock.patch('asyncio.new_event_loop', return_value=mock_loop), \
         mock.patch('asyncio.set_event_loop'), \
         mock.patch('app.workers.tasks.generate_prediction.apply_async', mock_apply_async):
        
        # Run the task
        result = schedule_game_predictions()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["predictions_scheduled"] == 2
        
        # Verify the mocks were called correctly
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()
        assert mock_apply_async.call_count == 2


@pytest.mark.asyncio
async def test_prepare_game_data():
    """Test game data preparation for prediction."""
    # Mock game and team data
    mock_game = {
        "id": 12345,
        "date": datetime.now().isoformat(),
        "home_team": {"id": 1, "name": "Lakers"},
        "visitor_team": {"id": 2, "name": "Celtics"},
        "status": "scheduled"
    }
    
    mock_team_stats = {"data": [{"wins": 10, "losses": 5}]}
    mock_news = [{"title": "Team news", "content": "Content"}]
    mock_injuries = [{"player": "Player", "status": "Injured"}]
    
    # Set up patches
    with mock.patch('app.workers.tasks.get_game_by_id', new_callable=AsyncMock, return_value=mock_game), \
         mock.patch('app.workers.tasks.get_team_stats_averages', new_callable=AsyncMock, return_value=mock_team_stats), \
         mock.patch('app.workers.tasks.get_recent_news_for_team', new_callable=AsyncMock, return_value=mock_news), \
         mock.patch('app.workers.tasks.get_team_injury_report', new_callable=AsyncMock, return_value=mock_injuries):
        
        # Call the function
        result = await _prepare_game_data(12345)
        
        # Verify the result structure
        assert result["game_id"] == 12345
        assert result["home_team"] == "Lakers"
        assert result["away_team"] == "Celtics"
        assert isinstance(result["spread"], float)
        assert "structured_data" in result
        assert "unstructured_data" in result
        
        # Verify structured data
        assert result["structured_data"]["home_team_id"] == 1
        assert result["structured_data"]["away_team_id"] == 2
        assert result["structured_data"]["home_team_stats"] == mock_team_stats["data"]
        
        # Verify unstructured data
        assert result["unstructured_data"]["home_team_news"] == mock_news
        assert result["unstructured_data"]["away_team_news"] == mock_news
        assert result["unstructured_data"]["home_team_injuries"] == mock_injuries
        assert result["unstructured_data"]["away_team_injuries"] == mock_injuries


def test_generate_prediction_task():
    """Test prediction generation task."""
    # Mock game data
    mock_game_data = {
        "game_id": 12345,
        "home_team": "Lakers",
        "away_team": "Celtics",
        "spread": -3.5,
        "game_date": datetime.now().isoformat(),
        "structured_data": {"home_team_id": 1, "away_team_id": 2},
        "unstructured_data": {}
    }
    
    # Mock the prediction model
    mock_prediction_result = PredictionResult(
        agent_id="test-agent",
        game_id=12345,
        pick="Lakers -3.5",
        logic="Test logic",
        confidence=0.8,
        result="pending"
    )
    
    mock_prediction_model = mock.MagicMock()
    mock_prediction_model.predict = AsyncMock(return_value=mock_prediction_result)
    
    # Mock service functions
    mock_create_prediction = mock.MagicMock(return_value=PredictionOut(
        agent_id="test-agent",
        game_id=12345,
        pick="Lakers -3.5",
        logic="Test logic",
        confidence=0.8,
        result="pending"
    ))
    
    # Mock the asyncio event loop
    mock_loop = mock.MagicMock()
    mock_loop.run_until_complete = mock.MagicMock(side_effect=[
        mock_game_data,  # First call for _prepare_game_data
        mock_prediction_result  # Second call for prediction_model.predict
    ])
    mock_loop.close = mock.MagicMock()
    
    # Set up patches
    with mock.patch('asyncio.new_event_loop', return_value=mock_loop), \
         mock.patch('asyncio.set_event_loop'), \
         mock.patch('app.workers.tasks._prepare_game_data', new_callable=AsyncMock, return_value=mock_game_data), \
         mock.patch('app.workers.tasks.create_langchain_prediction_model', return_value=mock_prediction_model), \
         mock.patch('app.workers.tasks.create_prediction', mock_create_prediction):
        
        # Run the task
        result = generate_prediction(12345)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["game_id"] == 12345
        assert result["pick"] == "Lakers -3.5"
        assert result["confidence"] == 0.8
        
        # Verify the mocks were called correctly
        assert mock_loop.run_until_complete.call_count == 2
        mock_loop.close.assert_called_once()
        mock_create_prediction.assert_called_once()


def test_update_game_results_task():
    """Test game results update task."""
    # Run the task
    result = update_game_results()
    
    # Verify the result
    assert result["status"] == "success"
    assert "message" in result
    assert "timestamp" in result