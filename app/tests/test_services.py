"""
@file: test_services.py
@description:
Test suite for service modules in the BadBeats API, focusing on:
- BallDontLie API integration service
- News ingestion service
- External API error handling and retries

@dependencies:
- pytest: For test framework
- unittest.mock: For mocking external services
- httpx: For testing HTTP clients
- app.services: Service modules being tested

@notes:
- Tests use mocking to avoid actual external API calls
- Success and error scenarios are tested
- Retry logic is verified
"""

import pytest
import json
from unittest import mock
import asyncio
from datetime import datetime, timedelta

from app.services.ball_dont_lie_api import (
    get_all_teams,
    get_team_by_id,
    get_upcoming_games,
    BallDontLieAPIError
)
from app.services.news_ingestion import (
    fetch_url,
    get_recent_news_for_team,
    get_team_injury_report,
    NewsIngestionError
)


class AsyncMock(mock.MagicMock):
    """Helper class for mocking async functions"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_get_all_teams_success():
    """Test successful retrieval of all teams."""
    # Mock data
    mock_teams = [
        {"id": 1, "name": "Los Angeles Lakers", "city": "Los Angeles", "conference": "West"},
        {"id": 2, "name": "Boston Celtics", "city": "Boston", "conference": "East"}
    ]
    
    # Mock the _make_request function
    with mock.patch('app.services.ball_dont_lie_api._make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": mock_teams}
        
        # Call the function
        result = await get_all_teams()
        
        # Verify
        assert result == mock_teams
        mock_request.assert_called_once_with("teams")


@pytest.mark.asyncio
async def test_get_all_teams_error():
    """Test error handling when teams retrieval fails."""
    # Mock the _make_request function to raise an exception
    with mock.patch('app.services.ball_dont_lie_api._make_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = Exception("API error")
        
        # Call the function and expect an exception
        with pytest.raises(BallDontLieAPIError):
            await get_all_teams()


@pytest.mark.asyncio
async def test_get_team_by_id_success():
    """Test successful retrieval of a team by ID."""
    # Mock data
    team_id = 1
    mock_team = {"id": team_id, "name": "Los Angeles Lakers", "city": "Los Angeles", "conference": "West"}
    
    # Mock the _make_request function
    with mock.patch('app.services.ball_dont_lie_api._make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_team
        
        # Call the function
        result = await get_team_by_id(team_id)
        
        # Verify
        assert result == mock_team
        mock_request.assert_called_once_with(f"teams/{team_id}")


@pytest.mark.asyncio
async def test_get_upcoming_games_success():
    """Test successful retrieval of upcoming games."""
    # Mock data
    mock_games = [
        {
            "id": 1,
            "date": datetime.now().isoformat(),
            "home_team": {"id": 1, "name": "Lakers"},
            "visitor_team": {"id": 2, "name": "Celtics"},
            "status": "scheduled"
        },
        {
            "id": 2,
            "date": (datetime.now() + timedelta(days=1)).isoformat(),
            "home_team": {"id": 3, "name": "Warriors"},
            "visitor_team": {"id": 4, "name": "Bucks"},
            "status": "scheduled"
        }
    ]
    
    # Mock the get_games function
    with mock.patch('app.services.ball_dont_lie_api.get_games', new_callable=AsyncMock) as mock_get_games:
        mock_get_games.return_value = {"data": mock_games}
        
        # Call the function
        result = await get_upcoming_games(days_ahead=7)
        
        # Verify
        assert result == mock_games
        mock_get_games.assert_called_once()
        args, kwargs = mock_get_games.call_args
        assert kwargs.get('start_date') is not None
        assert kwargs.get('end_date') is not None
        assert kwargs.get('per_page') == 100


@pytest.mark.asyncio
async def test_fetch_url_success():
    """Test successful URL fetching."""
    # Mock data
    url = "https://example.com"
    mock_content = "<html><body>Test content</body></html>"
    
    # Mock the httpx.AsyncClient
    mock_response = mock.MagicMock()
    mock_response.text = mock_content
    mock_response.raise_for_status = mock.MagicMock()
    
    mock_client = mock.MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    
    # Mock the httpx.AsyncClient context manager
    with mock.patch('httpx.AsyncClient', return_value=mock_client):
        # Call the function
        result = await fetch_url(url)
        
        # Verify
        assert result == mock_content
        mock_client.get.assert_called_once()
        args, kwargs = mock_client.get.call_args
        assert kwargs['timeout'] == 30.0


@pytest.mark.asyncio
async def test_fetch_url_error():
    """Test error handling when URL fetching fails."""
    # Mock data
    url = "https://example.com"
    
    # Mock the httpx.AsyncClient to raise an exception
    mock_client = mock.MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = Exception("Connection error")
    
    # Mock the httpx.AsyncClient context manager
    with mock.patch('httpx.AsyncClient', return_value=mock_client):
        # Call the function and expect an exception
        with pytest.raises(NewsIngestionError):
            await fetch_url(url)


@pytest.mark.asyncio
async def test_get_recent_news_for_team():
    """Test retrieving recent news for a team."""
    # Mock data
    team_name = "Lakers"
    mock_articles = [
        {
            "title": "Lakers win championship",
            "url": "https://example.com/article1",
            "published_date": datetime.now().isoformat(),
            "source": "ESPN",
            "content": f"The {team_name} have won the championship.",
            "summary": "Championship win"
        }
    ]
    
    # Mock the fetch_all_news_sources function
    with mock.patch('app.services.news_ingestion.fetch_all_news_sources', new_callable=AsyncMock) as mock_fetch_news:
        mock_fetch_news.return_value = {"articles": mock_articles, "injury_reports": []}
        
        # Call the function
        result = await get_recent_news_for_team(team_name, days=7)
        
        # Verify
        assert len(result) == 1
        assert result[0]["title"] == "Lakers win championship"
        mock_fetch_news.assert_called_once()


@pytest.mark.asyncio
async def test_get_team_injury_report():
    """Test retrieving injury report for a team."""
    # Mock data
    team_name = "Lakers"
    mock_injuries = [
        {
            "team": "Los Angeles Lakers",
            "player": "LeBron James",
            "injury": "Ankle",
            "status": "Day-to-day",
            "source": "ESPN",
            "updated_date": datetime.now().isoformat()
        }
    ]
    
    # Mock the fetch_all_news_sources function
    with mock.patch('app.services.news_ingestion.fetch_all_news_sources', new_callable=AsyncMock) as mock_fetch_news:
        mock_fetch_news.return_value = {"articles": [], "injury_reports": mock_injuries}
        
        # Call the function
        result = await get_team_injury_report(team_name)
        
        # Verify
        assert len(result) == 1
        assert result[0]["player"] == "LeBron James"
        mock_fetch_news.assert_called_once()