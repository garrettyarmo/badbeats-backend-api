"""
@file: ball_dont_lie_api.py
@description:
This module provides services for interacting with the BallDontLie API using the official
Python SDK (https://github.com/balldontlie-api/python) to fetch NBA-related data such as teams,
players, games, and statistics. It serves as the primary data source for structured NBA data used
in prediction models.

API Documentation: https://docs.balldontlie.io/#nba-api

@dependencies:
- balldontlie: Official Python SDK for BallDontLie API
- python-dotenv: For environment variable loading
- datetime: For date handling and formatting
- typing: For type annotations
- app.core.logger: For component-specific logging

@notes:
- This module uses the official synchronous SDK.
- Rate limiting is automatically handled by the SDK.
- All functions are designed to be async-compatible with FastAPI.
- Error handling is consistent across all functions with proper logging.
- The SDK returns custom model objects that have attribute-based access.
"""

import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
import inspect

from app.core.logger import setup_logger
from balldontlie import BalldontlieAPI

# Create a component-specific logger
logger = setup_logger("app.services.ball_dont_lie_api")

# Load environment variables (in case they haven't been loaded yet)
load_dotenv()

# API configuration
BALL_DONT_LIE_API_KEY = os.getenv("BALL_DONT_LIE_API_KEY", "")

# Pagination defaults
DEFAULT_PER_PAGE = 100  # Maximum allowed by the API


class BallDontLieAPIError(Exception):
    """Custom exception for BallDontLie API errors."""
    pass


class BDLAPIClientFactory:
    """
    Factory class for creating BallDontLie API clients.
    
    This ensures we don't create too many client instances and allows
    for better testing through mocking.
    """
    _instance = None
    
    @classmethod
    def get_client(cls) -> BalldontlieAPI:
        """
        Get a BallDontLie API client instance.
        
        Returns:
            BalldontlieAPI: Configured client instance
        """
        if cls._instance is None:
            cls._instance = BalldontlieAPI(api_key=BALL_DONT_LIE_API_KEY)
            logger.debug("Initialized BallDontLie API client")
        return cls._instance


async def get_all_teams() -> List[Any]:
    """
    Fetch all NBA teams from the BallDontLie API.

    Returns:
        List[Any]: List of team objects containing team information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info("Fetching all NBA teams")
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.teams.list()
        )
        
        # The response is a ListResponse object with a data attribute
        # that contains the list of team objects
        teams = response.data
        
        logger.info(f"Successfully fetched {len(teams)} teams from BallDontLie API")
        return teams
        
    except Exception as e:
        logger.error(f"Failed to fetch teams: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch teams: {str(e)}")


async def get_team_by_id(team_id: int) -> Any:
    """
    Fetch a specific NBA team by its ID.

    Args:
        team_id: The BallDontLie API team ID

    Returns:
        Any: Team object containing team information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching team with ID {team_id}")
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        team = await loop.run_in_executor(
            None, lambda: client.nba.teams.retrieve(team_id)
        )
        
        logger.info(f"Successfully fetched team with ID {team_id}")
        return team
        
    except Exception as e:
        logger.error(f"Failed to fetch team with ID {team_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team with ID {team_id}: {str(e)}")


async def get_games(
    date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    team_ids: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE
) -> List[Any]:
    """
    Fetch games based on various filters.

    Args:
        date: Specific date to get games for (format: YYYY-MM-DD)
        start_date: Start date for date range query
        end_date: End date for date range query
        team_ids: List of team IDs to filter by
        per_page: Number of results per page

    Returns:
        List[Any]: List of game objects containing game information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        # Prepare parameters - removed brackets notation from parameter names
        params = {}
        
        # Only add per_page if it's not None
        if per_page is not None:
            params["per_page"] = per_page
            
        # Add date filters
        if date:
            params["dates"] = date.strftime("%Y-%m-%d")
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")
            
        # Add team filter
        if team_ids:
            params["team_ids"] = team_ids

        logger.info(f"Fetching games with filters: {params}")
        
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.games.list(**params)
        )
        
        # Extract games from ListResponse
        games = response.data
        
        logger.info(f"Successfully fetched {len(games)} games with specified filters")
        return games
        
    except Exception as e:
        logger.error(f"Failed to fetch games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch games: {str(e)}")


async def get_game_by_id(game_id: int) -> Any:
    """
    Fetch a specific game by its ID.

    Args:
        game_id: The BallDontLie API game ID

    Returns:
        Any: Game object containing game information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching game with ID {game_id}")
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        game = await loop.run_in_executor(
            None, lambda: client.nba.games.retrieve(game_id)
        )
        
        logger.info(f"Successfully fetched game with ID {game_id}")
        return game
        
    except Exception as e:
        logger.error(f"Failed to fetch game with ID {game_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch game with ID {game_id}: {str(e)}")


async def get_upcoming_games(days_ahead: int = 7) -> List[Any]:
    """
    Fetch upcoming games for the next specified number of days.

    Args:
        days_ahead: Number of days in the future to fetch games for

    Returns:
        List[Any]: List of game objects containing game information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching upcoming games for the next {days_ahead} days")
        
        # Calculate date range
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        # Use the get_games function we've already defined - removed page parameter
        games = await get_games(start_date=today, end_date=end_date, per_page=100)
        
        logger.info(f"Successfully fetched {len(games)} upcoming games for the next {days_ahead} days")
        return games
        
    except Exception as e:
        logger.error(f"Failed to fetch upcoming games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch upcoming games: {str(e)}")


async def get_players(
    search: Optional[str] = None,
    team_ids: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE
) -> List[Any]:
    """
    Fetch players based on search criteria and filters.

    Args:
        search: Player name to search for
        team_ids: List of team IDs to filter by
        per_page: Number of results per page

    Returns:
        List[Any]: List of player objects containing player information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        # Prepare parameters - removed [] suffix from parameter names
        params = {}
        
        # Only add per_page if it's not None
        if per_page is not None:
            params["per_page"] = per_page
        
        # Add search filter
        if search:
            params["search"] = search
            
        # Add team filter - removed [] suffix from parameter name
        if team_ids:
            params["team_ids"] = team_ids

        logger.info(f"Fetching players with filters: {params}")
        
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.players.list(**params)
        )
        
        # Extract players from ListResponse
        players = response.data
        
        logger.info(f"Successfully fetched {len(players)} players with specified filters")
        return players
        
    except Exception as e:
        logger.error(f"Failed to fetch players: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch players: {str(e)}")


async def get_player_by_id(player_id: int) -> Any:
    """
    Fetch a specific player by their ID.

    Args:
        player_id: The BallDontLie API player ID

    Returns:
        Any: Player object containing player information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching player with ID {player_id}")
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        player = await loop.run_in_executor(
            None, lambda: client.nba.players.retrieve(player_id)
        )
        
        logger.info(f"Successfully fetched player with ID {player_id}")
        return player
        
    except Exception as e:
        logger.error(f"Failed to fetch player with ID {player_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player with ID {player_id}: {str(e)}")


async def get_player_stats(
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
    team_ids: Optional[List[int]] = None,
    seasons: Optional[List[int]] = None,
    per_page: int = DEFAULT_PER_PAGE
) -> List[Any]:
    """
    Fetch player statistics based on various filters.

    Args:
        player_ids: List of player IDs to filter by
        game_ids: List of game IDs to filter by
        team_ids: List of team IDs to filter by
        seasons: List of seasons to filter by
        per_page: Number of results per page

    Returns:
        List[Any]: List of stat objects containing player statistics.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        # Prepare parameters - removed [] suffix from parameter names
        params = {}
        
        # Only add per_page if it's not None
        if per_page is not None:
            params["per_page"] = per_page
        
        # Add filters - removed [] suffix from parameter names
        if player_ids:
            params["player_ids"] = player_ids
        if game_ids:
            params["game_ids"] = game_ids
        if team_ids:
            params["team_ids"] = team_ids
        if seasons:
            params["seasons"] = seasons

        logger.info(f"Fetching player stats with filters: {params}")
        
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.stats.list(**params)
        )
        
        # Extract stats from ListResponse
        stats = response.data
        
        logger.info(f"Successfully fetched {len(stats)} player stats with specified filters")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to fetch player stats: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player stats: {str(e)}")


async def get_team_stats_averages(team_id: int, season: Optional[int] = None) -> Any:
    """
    Fetch team statistics averages for a specific team and season.
    
    Note: The season_averages endpoint returns a different structure than
    other endpoints, so we're returning the raw response.

    Args:
        team_id: The team ID to get stats for
        season: Season to get stats for; if not provided, uses the current/most recent season

    Returns:
        Any: Response object containing team statistics averages.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching team stats averages for team ID {team_id}, season {season}")
        
        # Prepare minimal parameters (since the API doesn't accept team_ids directly)
        params = {}
        if season:
            params["season"] = season
        
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Inspect available methods for debugging
        available_methods = [method for method in dir(client.nba.season_averages) 
                            if not method.startswith('_')]
        logger.debug(f"Available methods on season_averages: {available_methods}")
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.season_averages.get(**params)
        )
        
        # Filter the results manually to find the team we want
        # First check if we got a valid response with data
        if hasattr(response, 'data'):
            # Create a filtered response with the same structure
            # but only containing stats for the requested team
            filtered_data = []
            
            # Loop through all season averages
            for stat in response.data:
                # Check if this stat is for our team
                if hasattr(stat, 'team') and hasattr(stat.team, 'id') and stat.team.id == team_id:
                    filtered_data.append(stat)
            
            # Create a wrapper object with the same structure as the original response
            class FilteredResponse:
                def __init__(self, data):
                    self.data = data
            
            filtered_response = FilteredResponse(filtered_data)
            logger.info(f"Found {len(filtered_data)} stat entries for team ID {team_id}")
            return filtered_response
        else:
            logger.warning(f"Response doesn't have expected 'data' attribute")
            return response
        
    except Exception as e:
        logger.error(f"Failed to fetch team stats averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team stats averages: {str(e)}")


async def get_player_season_averages(player_ids: List[int], season: Optional[int] = None) -> Any:
    """
    Fetch season averages for specific players.
    
    Note: The season_averages endpoint returns a different structure than
    other endpoints, so we're returning the raw response.

    Args:
        player_ids: List of player IDs to get season averages for
        season: Season to get stats for; if not provided, uses the current/most recent season

    Returns:
        Any: Response object containing player season averages.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        logger.info(f"Fetching season averages for {len(player_ids)} players, season {season}")
        
        # Prepare parameters
        params = {"player_ids": player_ids}
        if season:
            params["season"] = season
        
        # Get client from factory
        client = BDLAPIClientFactory.get_client()
        
        # Use an asyncio-friendly approach
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.season_averages.get(**params)
        )
        
        logger.info(f"Successfully fetched season averages for {len(player_ids)} players")
        return response
        
    except Exception as e:
        logger.error(f"Failed to fetch player season averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player season averages: {str(e)}")


async def get_current_season_games(team_id: Optional[int] = None) -> List[Any]:
    """
    Fetch all games for the current NBA season, optionally filtered by team.

    Args:
        team_id: Optional team ID to filter games by

    Returns:
        List[Any]: List of game objects containing game information.
        
    Raises:
        BallDontLieAPIError: If the API request fails or returns an error.
    """
    try:
        # Determine current season dates
        current_date = datetime.now()
        # NBA season typically runs from October to June
        if current_date.month >= 10:
            season_start_year = current_date.year
        else:
            season_start_year = current_date.year - 1
            
        season_start = datetime(season_start_year, 10, 1)
        season_end = datetime(season_start_year + 1, 6, 30)
        
        team_ids = [team_id] if team_id else None
        
        logger.info(f"Fetching current season games for season {season_start_year}-{season_start_year + 1}" +
                   (f" for team ID {team_id}" if team_id else ""))
        
        # Gather all pages of results manually since pagination is handled differently
        all_games = []
        has_more = True
        per_page = 100
        
        while has_more:
            # Fetch games for this chunk
            response = await get_games(
                start_date=season_start,
                end_date=season_end,
                team_ids=team_ids,
                per_page=per_page
            )
            
            # Add games to our list
            all_games.extend(response)
            
            # Check if we've fetched all games
            # If we got fewer than requested, we're done
            if len(response) < per_page:
                has_more = False
        
        logger.info(f"Successfully fetched {len(all_games)} games for the current season")
        return all_games
        
    except Exception as e:
        logger.error(f"Failed to fetch current season games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch current season games: {str(e)}")


# Additional utility functions

async def get_all_data_paginated(fetch_function, **kwargs) -> List[Any]:
    """
    Helper function to fetch all pages of data from a paginated API endpoint.
    
    Args:
        fetch_function: The API function to call for each page
        **kwargs: Parameters to pass to the fetch function
        
    Returns:
        List[Any]: Combined list of items from all pages
    """
    all_items = []
    has_more = True
    per_page = kwargs.get('per_page', 100)
    
    # Remove 'page' if it exists in kwargs
    if 'page' in kwargs:
        del kwargs['page']
    
    while has_more:
        # Fetch items
        items = await fetch_function(**kwargs)
        
        # Add items to our list
        all_items.extend(items)
        
        # Check if we've fetched all items (if we got fewer than requested, we're done)
        if len(items) < per_page:
            has_more = False
        
    return all_items


async def get_team_by_name(team_name: str) -> Optional[Any]:
    """
    Find a team by its name or city.
    
    Args:
        team_name: Full or partial team name to search for
        
    Returns:
        Optional[Any]: Team object if found, None otherwise
    """
    try:
        logger.info(f"Searching for team by name: {team_name}")
        
        # Get all teams
        teams = await get_all_teams()
        
        # Normalize the search name
        search_name = team_name.lower()
        
        # Search for matching team
        for team in teams:
            # Check against full_name, name, city, and abbreviation
            full_name = getattr(team, 'full_name', '').lower()
            name = getattr(team, 'name', '').lower()
            city = getattr(team, 'city', '').lower()
            abbreviation = getattr(team, 'abbreviation', '').lower()
            
            if (search_name in full_name or 
                search_name in name or
                search_name in city or
                search_name == abbreviation):
                logger.info(f"Found team matching '{team_name}': {getattr(team, 'full_name', '')}")
                return team
                
        logger.warning(f"No team found matching '{team_name}'")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for team by name: {str(e)}")
        return None


async def get_team_schedule(team_id: int, days_ahead: int = 30) -> List[Any]:
    """
    Get the upcoming schedule for a specific team.
    
    Args:
        team_id: The team ID to get schedule for
        days_ahead: Number of days to look ahead
        
    Returns:
        List[Any]: List of upcoming games for the team
    """
    try:
        logger.info(f"Fetching upcoming schedule for team ID {team_id}")
        
        # Get current date
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        # Fetch games for this team - removed [] suffix from parameter name
        games = await get_games(
            start_date=today,
            end_date=end_date,
            team_ids=[team_id],
            per_page=100
        )
        
        logger.info(f"Found {len(games)} upcoming games for team ID {team_id}")
        return games
        
    except Exception as e:
        logger.error(f"Error fetching team schedule: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team schedule: {str(e)}")