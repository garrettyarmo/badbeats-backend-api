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
- This module now uses the official synchronous SDK.
- Rate limiting, error handling, and retries should be handled by the SDK or externally if required.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

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

# Instantiate the official BallDontLie API client
client = BalldontlieAPI(api_key=BALL_DONT_LIE_API_KEY)


def get_all_teams() -> List[Dict[str, Any]]:
    """
    Fetch all NBA teams from the BallDontLie API.

    Returns:
        List of dictionaries containing team information.
    """
    try:
        logger.info("Fetching all NBA teams")
        response = client.nba.teams.list()
        # If response is a tuple, assume the first element is the actual data.
        print(f"Response: {response}")
        # if isinstance(response, tuple):
        #     teams = response[0]
        # elif hasattr(response, "get"):
        #     teams = response.get("data", response)
        # else:
        #     teams = list(response)
        # logger.info(f"Successfully fetched {len(teams)} teams from BallDontLie API")
        # return teams
    except Exception as e:
        logger.error(f"Failed to fetch teams: {str(e)}")
        raise Exception(f"Failed to fetch teams: {str(e)}")


def get_team_by_id(team_id: int) -> Dict[str, Any]:
    """
    Fetch a specific NBA team by its ID.

    Args:
        team_id: The BallDontLie API team ID

    Returns:
        Dictionary containing team information.
    """
    try:
        logger.info(f"Fetching team with ID {team_id}")
        team = client.nba.teams.retrieve(team_id)
        logger.info(f"Successfully fetched team with ID {team_id}")
        return team
    except Exception as e:
        logger.error(f"Failed to fetch team with ID {team_id}: {str(e)}")
        raise Exception(f"Failed to fetch team with ID {team_id}: {str(e)}")


def get_games(
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
        Dictionary containing games data and pagination information.
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    if date:
        params["dates[]"] = date.strftime("%Y-%m-%d")
    if start_date:
        params["start_date"] = start_date.strftime("%Y-%m-%d")
    if end_date:
        params["end_date"] = end_date.strftime("%Y-%m-%d")
    if team_ids:
        params["team_ids[]"] = team_ids

    try:
        logger.info(f"Fetching games with filters: {params}")
        response = client.nba.games.list(**params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} games with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch games: {str(e)}")
        raise Exception(f"Failed to fetch games: {str(e)}")


def get_game_by_id(game_id: int) -> Dict[str, Any]:
    """
    Fetch a specific game by its ID.

    Args:
        game_id: The BallDontLie API game ID

    Returns:
        Dictionary containing game information.
    """
    try:
        logger.info(f"Fetching game with ID {game_id}")
        game = client.nba.games.retrieve(game_id)
        logger.info(f"Successfully fetched game with ID {game_id}")
        return game
    except Exception as e:
        logger.error(f"Failed to fetch game with ID {game_id}: {str(e)}")
        raise Exception(f"Failed to fetch game with ID {game_id}: {str(e)}")


def get_upcoming_games(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch upcoming games for the next specified number of days.

    Args:
        days_ahead: Number of days in the future to fetch games for

    Returns:
        List of dictionaries containing game information.
    """
    today = datetime.now()
    end_date = today + timedelta(days=days_ahead)

    try:
        logger.info(f"Fetching upcoming games for the next {days_ahead} days")
        response = get_games(start_date=today, end_date=end_date, per_page=100, page=1)
        games = response.get("data", [])
        logger.info(f"Successfully fetched {len(games)} upcoming games for the next {days_ahead} days")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch upcoming games: {str(e)}")
        raise Exception(f"Failed to fetch upcoming games: {str(e)}")


def get_players(
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
        Dictionary containing player data and pagination information.
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    if search:
        params["search"] = search
    if team_ids:
        params["team_ids[]"] = team_ids

    try:
        logger.info(f"Fetching players with filters: {params}")
        response = client.nba.players.list(**params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} players with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch players: {str(e)}")
        raise Exception(f"Failed to fetch players: {str(e)}")


def get_player_by_id(player_id: int) -> Dict[str, Any]:
    """
    Fetch a specific player by their ID.

    Args:
        player_id: The BallDontLie API player ID

    Returns:
        Dictionary containing player information.
    """
    try:
        logger.info(f"Fetching player with ID {player_id}")
        player = client.nba.players.retrieve(player_id)
        logger.info(f"Successfully fetched player with ID {player_id}")
        return player
    except Exception as e:
        logger.error(f"Failed to fetch player with ID {player_id}: {str(e)}")
        raise Exception(f"Failed to fetch player with ID {player_id}: {str(e)}")


def get_player_stats(
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
        seasons: List of seasons to filter by
        per_page: Number of results per page
        page: Page number for pagination

    Returns:
        Dictionary containing player stats and pagination information.
    """
    params = {
        "per_page": per_page,
        "page": page
    }
    if player_ids:
        params["player_ids[]"] = player_ids
    if game_ids:
        params["game_ids[]"] = game_ids
    if team_ids:
        params["team_ids[]"] = team_ids
    if seasons:
        params["seasons[]"] = seasons

    try:
        logger.info(f"Fetching player stats with filters: {params}")
        response = client.nba.stats.list(**params)
        logger.info(f"Successfully fetched {len(response.get('data', []))} player stats with specified filters")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch player stats: {str(e)}")
        raise Exception(f"Failed to fetch player stats: {str(e)}")


def get_team_stats_averages(team_id: int, season: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch team statistics averages for a specific team and season.

    Args:
        team_id: The team ID to get stats for
        season: Season to get stats for; if not provided, uses the current/most recent season

    Returns:
        Dictionary containing team statistics averages.
    """
    params = {"team_ids[]": [team_id]}
    if season:
        params["seasons[]"] = [season]

    try:
        logger.info(f"Fetching team stats averages for team ID {team_id}, season {season}")
        response = client.nba.season_averages.list(**params)
        logger.info(f"Successfully fetched stats averages for team ID {team_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch team stats averages: {str(e)}")
        raise Exception(f"Failed to fetch team stats averages: {str(e)}")


def get_player_season_averages(player_ids: List[int], season: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch season averages for specific players.

    Args:
        player_ids: List of player IDs to get season averages for
        season: Season to get stats for; if not provided, uses the current/most recent season

    Returns:
        Dictionary containing player season averages.
    """
    params = {"player_ids[]": player_ids}
    if season:
        params["season"] = season

    try:
        logger.info(f"Fetching season averages for {len(player_ids)} players, season {season}")
        response = client.nba.season_averages.list(**params)
        logger.info(f"Successfully fetched season averages for {len(player_ids)} players")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch player season averages: {str(e)}")
        raise Exception(f"Failed to fetch player season averages: {str(e)}")


def get_current_season_games(team_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch all games for the current NBA season, optionally filtered by team.

    Args:
        team_id: Optional team ID to filter games by

    Returns:
        List of dictionaries containing game information.
    """
    current_date = datetime.now()
    # NBA season typically runs from October to June
    if current_date.month >= 10:
        season_start_year = current_date.year
    else:
        season_start_year = current_date.year - 1

    season_start = datetime(season_start_year, 10, 1)
    season_end = datetime(season_start_year + 1, 6, 30)
    team_ids = [team_id] if team_id else None

    try:
        logger.info(f"Fetching current season games for season {season_start_year}-{season_start_year + 1}" +
                    (f" for team ID {team_id}" if team_id else ""))
        all_games = []
        page = 1

        while True:
            response = get_games(
                start_date=season_start,
                end_date=season_end,
                team_ids=team_ids,
                per_page=100,
                page=page
            )
            games = response.get("data", [])
            all_games.extend(games)
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
        raise Exception(f"Failed to fetch current season games: {str(e)}")
