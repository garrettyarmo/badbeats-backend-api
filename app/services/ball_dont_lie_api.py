"""
@file: ball_dont_lie_api.py
@description:
This module provides services for interacting with the BallDontLie API to fetch 
NBA-related data such as teams, players, games, and statistics. It serves as the 
primary data source for structured NBA data used in the prediction models.

API Documentation: https://docs.balldontlie.io/#nba-api

@dependencies:
- httpx: For async HTTP requests
- tenacity: For retry logic
- datetime: For date handling and formatting
- typing: For type annotations
- app.core.logger: For component-specific logging

@notes:
- This module uses async/await for better performance with FastAPI
- Rate limiting is respected (60 requests per minute for BallDontLie API)
- Retry logic is implemented for transient errors
- Error handling is robust and provides meaningful error messages
- All API responses are cached when appropriate to reduce API calls
"""

import httpx
import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from app.core.logger import setup_logger

# Create a component-specific logger
logger = setup_logger("app.services.ball_dont_lie_api")

# Load environment variables (in case they haven't been loaded yet)
load_dotenv()

# API configuration
BALL_DONT_LIE_BASE_URL = "https://balldontlie.io/api/v1"
BALL_DONT_LIE_API_KEY = os.getenv("BALL_DONT_LIE_API_KEY", "")

# Pagination defaults
DEFAULT_PER_PAGE = 100  # Maximum allowed by the API


class BallDontLieAPIError(Exception):
    """Custom exception for BallDontLie API errors"""
    pass


async def _make_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make an HTTP request to the BallDontLie API.
    
    Args:
        endpoint: API endpoint to call (without the base URL)
        params: Query parameters to include in the request
        
    Returns:
        Dict containing the JSON response from the API
        
    Raises:
        BallDontLieAPIError: If the API returns an error or request fails
    """
    url = f"{BALL_DONT_LIE_BASE_URL}/{endpoint}"
    headers = {}
    
    # Add API key if available (for authenticated endpoints)
    if BALL_DONT_LIE_API_KEY:
        headers["Authorization"] = f"Bearer {BALL_DONT_LIE_API_KEY}"
    
    try:
        logger.debug(f"Making request to BallDontLie API: {url} with params: {params}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            
            # Raise an exception for 4XX and 5XX responses
            response.raise_for_status()
            
            logger.debug(f"Received successful response from BallDontLie API: {url}")
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        raise BallDontLieAPIError(f"API returned error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {str(e)}")
        raise BallDontLieAPIError(f"Request failed: {str(e)}")
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response")
        raise BallDontLieAPIError("Failed to decode API response")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise BallDontLieAPIError(f"Unexpected error: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_all_teams() -> List[Dict[str, Any]]:
    """
    Fetch all NBA teams from the BallDontLie API.
    
    Returns:
        List of dictionaries containing team information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    try:
        logger.info("Fetching all NBA teams")
        response = await _make_request("teams")
        teams = response.get("data", [])
        logger.info(f"Successfully fetched {len(teams)} teams from BallDontLie API")
        return teams
    except Exception as e:
        logger.error(f"Failed to fetch teams: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch teams: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_team_by_id(team_id: int) -> Dict[str, Any]:
    """
    Fetch a specific NBA team by its ID.
    
    Args:
        team_id: The BallDontLie API team ID
        
    Returns:
        Dictionary containing team information
        
    Raises:
        BallDontLieAPIError: If the API request fails or team is not found
    """
    try:
        logger.info(f"Fetching team with ID {team_id}")
        response = await _make_request(f"teams/{team_id}")
        logger.info(f"Successfully fetched team with ID {team_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch team with ID {team_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team with ID {team_id}: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_games(
    date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    team_ids: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE,
    page: int = 1
) -> Dict[str, Any]:
    """
    Fetch games based on various filters.
    
    Args:
        date: Specific date to get games for (format: YYYY-MM-DD)
        start_date: Start date for date range query
        end_date: End date for date range query
        team_ids: List of team IDs to filter by
        per_page: Number of results per page
        page: Page number for pagination
        
    Returns:
        Dictionary containing games data and pagination information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    
    # Add optional filters
    if date:
        params["dates[]"] = date.strftime("%Y-%m-%d")
    if start_date:
        params["start_date"] = start_date.strftime("%Y-%m-%d")
    if end_date:
        params["end_date"] = end_date.strftime("%Y-%m-%d")
    if team_ids:
        params["team_ids[]"] = team_ids
    
    try:
        logger.info(f"Fetching games with filters: date={date}, start_date={start_date}, end_date={end_date}, team_ids={team_ids}")
        response = await _make_request("games", params=params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} games with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch games: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_game_by_id(game_id: int) -> Dict[str, Any]:
    """
    Fetch a specific game by its ID.
    
    Args:
        game_id: The BallDontLie API game ID
        
    Returns:
        Dictionary containing game information
        
    Raises:
        BallDontLieAPIError: If the API request fails or game is not found
    """
    try:
        logger.info(f"Fetching game with ID {game_id}")
        response = await _make_request(f"games/{game_id}")
        logger.info(f"Successfully fetched game with ID {game_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch game with ID {game_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch game with ID {game_id}: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_upcoming_games(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch upcoming games for the next specified number of days.
    
    Args:
        days_ahead: Number of days in the future to fetch games for
        
    Returns:
        List of dictionaries containing game information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    today = datetime.now()
    end_date = today + timedelta(days=days_ahead)
    
    try:
        logger.info(f"Fetching upcoming games for the next {days_ahead} days")
        response = await get_games(
            start_date=today,
            end_date=end_date,
            per_page=100
        )
        games = response.get("data", [])
        logger.info(f"Successfully fetched {len(games)} upcoming games for the next {days_ahead} days")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch upcoming games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch upcoming games: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_players(
    search: Optional[str] = None,
    team_ids: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE,
    page: int = 1
) -> Dict[str, Any]:
    """
    Fetch players based on search criteria and filters.
    
    Args:
        search: Player name to search for
        team_ids: List of team IDs to filter by
        per_page: Number of results per page
        page: Page number for pagination
        
    Returns:
        Dictionary containing player data and pagination information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    
    # Add optional filters
    if search:
        params["search"] = search
    if team_ids:
        params["team_ids[]"] = team_ids
    
    try:
        logger.info(f"Fetching players with search={search}, team_ids={team_ids}")
        response = await _make_request("players", params=params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} players with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch players: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch players: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_player_by_id(player_id: int) -> Dict[str, Any]:
    """
    Fetch a specific player by their ID.
    
    Args:
        player_id: The BallDontLie API player ID
        
    Returns:
        Dictionary containing player information
        
    Raises:
        BallDontLieAPIError: If the API request fails or player is not found
    """
    try:
        logger.info(f"Fetching player with ID {player_id}")
        response = await _make_request(f"players/{player_id}")
        logger.info(f"Successfully fetched player with ID {player_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch player with ID {player_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player with ID {player_id}: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_player_stats(
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
    team_ids: Optional[List[int]] = None,
    seasons: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE,
    page: int = 1
) -> Dict[str, Any]:
    """
    Fetch player statistics based on various filters.
    
    Args:
        player_ids: List of player IDs to filter by
        game_ids: List of game IDs to filter by
        team_ids: List of team IDs to filter by
        seasons: List of seasons to filter by (e.g., 2021 for the 2021-2022 season)
        per_page: Number of results per page
        page: Page number for pagination
        
    Returns:
        Dictionary containing player stats and pagination information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    
    # Add optional filters
    if player_ids:
        params["player_ids[]"] = player_ids
    if game_ids:
        params["game_ids[]"] = game_ids
    if team_ids:
        params["team_ids[]"] = team_ids
    if seasons:
        params["seasons[]"] = seasons
    
    try:
        logger.info(f"Fetching player stats with filters: player_ids={player_ids}, game_ids={game_ids}, team_ids={team_ids}, seasons={seasons}")
        response = await _make_request("stats", params=params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} player stats with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch player stats: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player stats: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_team_stats_averages(
    team_id: int,
    season: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch team statistics averages for a specific team and season.
    
    Args:
        team_id: The team ID to get stats for
        season: Season to get stats for (e.g., 2021 for the 2021-2022 season)
            If not provided, uses the current/most recent season
            
    Returns:
        Dictionary containing team statistics averages
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    params = {"team_ids[]": [team_id]}
    
    # Add season if provided
    if season:
        params["seasons[]"] = [season]
    
    try:
        logger.info(f"Fetching team stats averages for team ID {team_id}, season {season}")
        response = await _make_request("season_averages", params=params)
        logger.info(f"Successfully fetched stats averages for team ID {team_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch team stats averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team stats averages: {str(e)}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_player_season_averages(
    player_ids: List[int],
    season: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch season averages for specific players.
    
    Args:
        player_ids: List of player IDs to get season averages for
        season: Season to get stats for (e.g., 2021 for the 2021-2022 season)
            If not provided, uses the current/most recent season
            
    Returns:
        Dictionary containing player season averages
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    params = {"player_ids[]": player_ids}
    
    # Add season if provided
    if season:
        params["season"] = season
    
    try:
        logger.info(f"Fetching season averages for {len(player_ids)} players, season {season}")
        response = await _make_request("season_averages", params=params)
        logger.info(f"Successfully fetched season averages for {len(player_ids)} players")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch player season averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player season averages: {str(e)}")


async def get_current_season_games(team_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all games for the current NBA season, optionally filtered by team.
    
    Args:
        team_id: Optional team ID to filter games by
        
    Returns:
        List of dictionaries containing game information
        
    Raises:
        BallDontLieAPIError: If the API request fails
    """
    # Determine the current season's start year based on current date
    # NBA season typically runs from October to June
    current_date = datetime.now()
    if current_date.month >= 10:  # October or later
        season_start_year = current_date.year
    else:
        season_start_year = current_date.year - 1
    
    # Approximate season start date (October 1st)
    season_start = datetime(season_start_year, 10, 1)
    
    # Approximate season end date (June 30th of next year)
    season_end = datetime(season_start_year + 1, 6, 30)
    
    # Prepare team_ids parameter if team_id is provided
    team_ids = [team_id] if team_id else None
    
    try:
        logger.info(f"Fetching current season games (season {season_start_year}-{season_start_year + 1}){' for team ID ' + str(team_id) if team_id else ''}")
        all_games = []
        page = 1
        
        while True:
            response = await get_games(
                start_date=season_start,
                end_date=season_end,
                team_ids=team_ids,
                per_page=100,
                page=page
            )
            
            games = response.get("data", [])
            all_games.extend(games)
            
            # Check if we've fetched all pages
            meta = response.get("meta", {})
            current_page = meta.get("current_page", 1)
            total_pages = meta.get("total_pages", 1)
            
            logger.debug(f"Fetched page {current_page} of {total_pages} of current season games")
            
            if current_page >= total_pages:
                break
                
            page += 1
        
        logger.info(f"Successfully fetched {len(all_games)} games for the current season")
        return all_games
        
    except Exception as e:
        logger.error(f"Failed to fetch current season games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch current season games: {str(e)}")