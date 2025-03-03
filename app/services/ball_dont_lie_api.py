"""
@file: ball_dont_lie_api.py
@description:
This module provides an asynchronous service layer for interacting with the Ball Don't Lie API
using the official Python SDK (https://github.com/balldontlie-api/python). It fetches NBA data
such as teams, players, games, stats, and season averages for use in prediction models and storage
in Supabase.

API Documentation: https://docs.balldontlie.io/#nba-api

Key features:
- Full endpoint coverage: Supports all core API endpoints (teams, players, games, stats, season_averages)
- Pagination: Handles multi-page responses for large datasets
- Async compatibility: Integrates with FastAPI’s async framework
- Error handling: Robust logging and custom exceptions
- Data preparation: Returns data ready for Supabase insertion

@dependencies:
- balldontlie: Official Python SDK for Ball Don't Lie API
- asyncio: For asynchronous execution of synchronous API calls
- dotenv: For loading environment variables (e.g., API key)
- typing: For type hints and clarity
- app.core.logger: For component-specific logging

@notes:
- The service uses a singleton client factory to manage API connections.
- Pagination is optional via `fetch_all_pages` parameters; use wisely to avoid API rate limits.
- Some requested data (e.g., Player Injuries, Live Betting Odds) isn’t directly available; see
  `app/services/news_ingestion.py` for supplementary data sources.
- Responses maintain the SDK’s structure (attribute-accessible objects); additional preprocessing
  may be needed for Supabase storage depending on table schemas.
"""

import os
from typing import List, Any, Optional, Dict
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv

from balldontlie import BalldontlieAPI
from app.core.logger import setup_logger

# Initialize logger
logger = setup_logger("app.services.ball_dont_lie_api")

# Load environment variables
load_dotenv()
BALL_DONT_LIE_API_KEY = os.getenv("BALL_DONT_LIE_API_KEY", "")

# Pagination defaults
DEFAULT_PER_PAGE = 100  # Maximum allowed by API


class BallDontLieAPIError(Exception):
    """Custom exception for Ball Don't Lie API errors."""
    pass


class BDLAPIClientFactory:
    """Factory for creating and managing a singleton BallDontLie API client."""
    _instance: Optional[BalldontlieAPI] = None

    @classmethod
    def get_client(cls) -> BalldontlieAPI:
        """
        Retrieve or create a BallDontLie API client instance.

        Returns:
            BalldontlieAPI: Configured API client.

        Raises:
            BallDontLieAPIError: If client initialization fails.
        """
        if cls._instance is None:
            try:
                cls._instance = BalldontlieAPI(api_key=BALL_DONT_LIE_API_KEY)
                logger.debug("Initialized BallDontLie API client")
            except Exception as e:
                logger.error(f"Failed to initialize BallDontLie API client: {str(e)}")
                raise BallDontLieAPIError(f"Failed to initialize API client: {str(e)}")
        return cls._instance


async def fetch_all_pages(endpoint_func, **kwargs) -> List[Any]:
    """
    Fetch all pages of data from a paginated Ball Don't Lie API endpoint.

    Args:
        endpoint_func: The API method to call (e.g., client.nba.teams.list).
        **kwargs: Additional parameters for the endpoint (e.g., search, team_ids).

    Returns:
        List[Any]: Combined list of all items across pages.

    Raises:
        BallDontLieAPIError: If data fetching fails.
    """
    client = BDLAPIClientFactory.get_client()
    all_items = []
    page = 1
    per_page = kwargs.pop("per_page", DEFAULT_PER_PAGE)

    try:
        while True:
            # Run synchronous API call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: endpoint_func(page=page, per_page=per_page, **kwargs)
            )
            items = response.data
            all_items.extend(items)
            total_pages = response.meta.get("total_pages", 1)
            logger.debug(f"Fetched page {page}/{total_pages}: {len(items)} items")
            if page >= total_pages:
                break
            page += 1
        return all_items
    except Exception as e:
        logger.error(f"Error fetching all pages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch paginated data: {str(e)}")


async def get_all_teams(fetch_all_pages: bool = False) -> List[Any]:
    """
    Fetch all NBA teams from the Ball Don't Lie API.

    Args:
        fetch_all_pages: If True, fetch all pages (though teams typically fit in one page).

    Returns:
        List[Any]: List of team objects with attributes (id, name, city, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info("Fetching all NBA teams")
        if fetch_all_pages:
            teams = await fetch_all_pages(client.nba.teams.list)
        else:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.nba.teams.list(per_page=DEFAULT_PER_PAGE)
            )
            teams = response.data
        logger.info(f"Fetched {len(teams)} teams")
        return teams
    except Exception as e:
        logger.error(f"Failed to fetch teams: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch teams: {str(e)}")


async def get_team_by_id(team_id: int) -> Any:
    """
    Fetch a specific team by its ID.

    Args:
        team_id: The Ball Don't Lie team ID.

    Returns:
        Any: Team object with attributes (id, name, city, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info(f"Fetching team ID {team_id}")
        loop = asyncio.get_event_loop()
        team = await loop.run_in_executor(
            None, lambda: client.nba.teams.retrieve(team_id)
        )
        logger.info(f"Fetched team: {team.name}")
        return team
    except Exception as e:
        logger.error(f"Failed to fetch team ID {team_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team ID {team_id}: {str(e)}")


async def get_games(
    date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    team_ids: Optional[List[int]] = None,
    fetch_all_pages: bool = False
) -> List[Any]:
    """
    Fetch games based on filters.

    Args:
        date: Specific date for games (YYYY-MM-DD).
        start_date: Start of date range.
        end_date: End of date range.
        team_ids: List of team IDs to filter by.
        fetch_all_pages: If True, fetch all pages of results.

    Returns:
        List[Any]: List of game objects with attributes (id, date, home_team, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    params = {}
    if date:
        params["dates"] = [date.strftime("%Y-%m-%d")]
    if start_date:
        params["start_date"] = start_date.strftime("%Y-%m-%d")
    if end_date:
        params["end_date"] = end_date.strftime("%Y-%m-%d")
    if team_ids:
        params["team_ids"] = team_ids

    try:
        logger.info(f"Fetching games with filters: {params}")
        if fetch_all_pages:
            games = await fetch_all_pages(client.nba.games.list, **params)
        else:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.nba.games.list(per_page=DEFAULT_PER_PAGE, **params)
            )
            games = response.data
        logger.info(f"Fetched {len(games)} games")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch games: {str(e)}")


async def get_game_by_id(game_id: int) -> Any:
    """
    Fetch a specific game by its ID.

    Args:
        game_id: The Ball Don't Lie game ID.

    Returns:
        Any: Game object with attributes (id, date, home_team, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info(f"Fetching game ID {game_id}")
        loop = asyncio.get_event_loop()
        game = await loop.run_in_executor(
            None, lambda: client.nba.games.retrieve(game_id)
        )
        logger.info(f"Fetched game ID {game_id}")
        return game
    except Exception as e:
        logger.error(f"Failed to fetch game ID {game_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch game ID {game_id}: {str(e)}")


async def get_upcoming_games(days_ahead: int = 7) -> List[Any]:
    """
    Fetch upcoming games for the next specified days.

    Args:
        days_ahead: Number of days to look ahead.

    Returns:
        List[Any]: List of upcoming game objects.

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    try:
        logger.info(f"Fetching upcoming games for next {days_ahead} days")
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        games = await get_games(start_date=today, end_date=end_date, fetch_all_pages=True)
        logger.info(f"Fetched {len(games)} upcoming games")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch upcoming games: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch upcoming games: {str(e)}")


async def get_players(
    search: Optional[str] = None,
    team_ids: Optional[List[int]] = None,
    fetch_all_pages: bool = False
) -> List[Any]:
    """
    Fetch players based on filters.

    Args:
        search: Player name to search for.
        team_ids: List of team IDs to filter by.
        fetch_all_pages: If True, fetch all pages of results.

    Returns:
        List[Any]: List of player objects with attributes (id, first_name, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    params = {}
    if search:
        params["search"] = search
    if team_ids:
        params["team_ids"] = team_ids

    try:
        logger.info(f"Fetching players with filters: {params}")
        if fetch_all_pages:
            players = await fetch_all_pages(client.nba.players.list, **params)
        else:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.nba.players.list(per_page=DEFAULT_PER_PAGE, **params)
            )
            players = response.data
        logger.info(f"Fetched {len(players)} players")
        return players
    except Exception as e:
        logger.error(f"Failed to fetch players: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch players: {str(e)}")


async def get_player_by_id(player_id: int) -> Any:
    """
    Fetch a specific player by their ID.

    Args:
        player_id: The Ball Don't Lie player ID.

    Returns:
        Any: Player object with attributes (id, first_name, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info(f"Fetching player ID {player_id}")
        loop = asyncio.get_event_loop()
        player = await loop.run_in_executor(
            None, lambda: client.nba.players.retrieve(player_id)
        )
        logger.info(f"Fetched player: {player.first_name} {player.last_name}")
        return player
    except Exception as e:
        logger.error(f"Failed to fetch player ID {player_id}: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch player ID {player_id}: {str(e)}")


async def get_stats(
    player_ids: Optional[List[int]] = None,
    game_ids: Optional[List[int]] = None,
    team_ids: Optional[List[int]] = None,
    seasons: Optional[List[int]] = None,
    fetch_all_pages: bool = False
) -> List[Any]:
    """
    Fetch player statistics based on filters.

    Args:
        player_ids: List of player IDs to filter by.
        game_ids: List of game IDs to filter by (e.g., for box scores).
        team_ids: List of team IDs to filter by.
        seasons: List of seasons to filter by.
        fetch_all_pages: If True, fetch all pages of results.

    Returns:
        List[Any]: List of stat objects with attributes (pts, reb, etc.).

    Raises:
        BallDontLieAPIError: If the request fails.

    Notes:
        - Use game_ids for box scores or game-specific stats.
    """
    client = BDLAPIClientFactory.get_client()
    params = {}
    if player_ids:
        params["player_ids"] = player_ids
    if game_ids:
        params["game_ids"] = game_ids
    if team_ids:
        params["team_ids"] = team_ids
    if seasons:
        params["seasons"] = seasons

    try:
        logger.info(f"Fetching stats with filters: {params}")
        if fetch_all_pages:
            stats = await fetch_all_pages(client.nba.stats.list, **params)
        else:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.nba.stats.list(per_page=DEFAULT_PER_PAGE, **params)
            )
            stats = response.data
        logger.info(f"Fetched {len(stats)} stat records")
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch stats: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch stats: {str(e)}")


async def get_team_stats_averages(team_id: int, season: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch season averages for all players on a team.

    Args:
        team_id: The team ID to fetch averages for.
        season: The season year (defaults to current season).

    Returns:
        Dict[str, Any]: Dictionary with 'data' key containing list of player averages.

    Raises:
        BallDontLieAPIError: If the request fails.

    Notes:
        - Returns an empty list if no players are found.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info(f"Fetching team stats averages for team ID {team_id}, season {season}")
        if season is None:
            now = datetime.now()
            season = now.year if now.month >= 7 else now.year - 1

        # Get all players for the team
        players = await get_players(team_ids=[team_id], fetch_all_pages=True)
        player_ids = [player.id for player in players if hasattr(player, 'id')]

        if not player_ids:
            logger.warning(f"No players found for team ID {team_id}")
            return {"data": []}

        # Fetch season averages for all players
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.season_averages.get(season=season, player_ids=player_ids)
        )
        stats = response.data

        # Filter stats to ensure they match the team
        filtered_stats = [stat for stat in stats if stat.team.id == team_id]
        logger.info(f"Fetched {len(filtered_stats)} player averages for team ID {team_id}")
        return {"data": filtered_stats}
    except Exception as e:
        logger.error(f"Failed to fetch team stats averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team stats averages: {str(e)}")


async def get_season_averages(
    player_ids: List[int],
    season: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch season averages for specific players.

    Args:
        player_ids: List of player IDs to fetch averages for.
        season: The season year (defaults to current season).

    Returns:
        Dict[str, Any]: Dictionary with 'data' key containing list of averages.

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    client = BDLAPIClientFactory.get_client()
    try:
        logger.info(f"Fetching season averages for {len(player_ids)} players, season {season}")
        if season is None:
            now = datetime.now()
            season = now.year if now.month >= 7 else now.year - 1

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.nba.season_averages.get(season=season, player_ids=player_ids)
        )
        logger.info(f"Fetched season averages for {len(response.data)} players")
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Failed to fetch season averages: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch season averages: {str(e)}")


async def get_team_by_name(team_name: str) -> Optional[Any]:
    """
    Find a team by its name or abbreviation.

    Args:
        team_name: Team name or abbreviation to search for.

    Returns:
        Optional[Any]: Team object if found, None otherwise.

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    try:
        logger.info(f"Searching for team: {team_name}")
        teams = await get_all_teams(fetch_all_pages=True)
        search_name = team_name.lower()

        for team in teams:
            if (search_name in team.full_name.lower() or
                search_name in team.name.lower() or
                search_name == team.abbreviation.lower()):
                logger.info(f"Found team: {team.full_name}")
                return team

        logger.warning(f"No team found matching '{team_name}'")
        return None
    except Exception as e:
        logger.error(f"Failed to find team by name: {str(e)}")
        raise BallDontLieAPIError(f"Failed to find team by name: {str(e)}")


async def get_team_schedule(team_id: int, days_ahead: int = 30) -> List[Any]:
    """
    Get the upcoming schedule for a specific team.

    Args:
        team_id: The team ID.
        days_ahead: Number of days to look ahead.

    Returns:
        List[Any]: List of upcoming game objects.

    Raises:
        BallDontLieAPIError: If the request fails.
    """
    try:
        logger.info(f"Fetching schedule for team ID {team_id} for next {days_ahead} days")
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        games = await get_games(
            start_date=today,
            end_date=end_date,
            team_ids=[team_id],
            fetch_all_pages=True
        )
        logger.info(f"Fetched {len(games)} upcoming games for team ID {team_id}")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch team schedule: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch team schedule: {str(e)}")
    
async def get_betting_odds(
    date: Optional[str] = None,
    game_id: Optional[int] = None,
    fetch_all_pages: bool = False
) -> List[Any]:
    """
    Fetch betting odds for NBA games.

    Args:
        date: Specific date for odds (YYYY-MM-DD).
        game_id: Specific game ID for odds.
        fetch_all_pages: If True, fetch all pages of results (though odds typically fit in one page).

    Returns:
        List[Any]: List of betting odds objects.

    Raises:
        BallDontLieAPIError: If the request fails.

    Notes:
        - This endpoint may require a premium API key or special access.
        - If neither date nor game_id is provided, fetches all available odds.
    """
    client = BDLAPIClientFactory.get_client()
    params = {}
    if date:
        params["date"] = date
    if game_id:
        params["game_id"] = game_id

    try:
        logger.info(f"Fetching betting odds with filters: {params}")
        if fetch_all_pages:
            odds = await fetch_all_pages(client.nba.odds.list, **params)
        else:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.nba.odds.list(per_page=DEFAULT_PER_PAGE, **params)
            )
            odds = response.data
        logger.info(f"Fetched {len(odds)} betting odds records")
        return odds
    except Exception as e:
        logger.error(f"Failed to fetch betting odds: {str(e)}")
        raise BallDontLieAPIError(f"Failed to fetch betting odds: {str(e)}")