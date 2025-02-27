import asyncio
from app.services.ball_dont_lie_api import get_all_teams
from app.services.news_ingestion import get_recent_news_for_team, get_team_injury_report

async def main():
    # Test fetching all NBA teams from the BallDontLie API
    print("Testing get_all_teams()...")
    try:
        teams = get_all_teams()
        print(f"Fetched {len(teams)} teams:")
        for team in teams:
            print(f"  {team.get('full_name', team.get('name', 'Unknown'))}")
    except Exception as e:
        print(f"Error in get_all_teams: {e}")

    # Choose a team name for testing news and injury reports
    team_name = "Lakers"

    # # Test fetching recent news articles for the chosen team
    # print(f"\nTesting get_recent_news_for_team('{team_name}', days=7)...")
    # try:
    #     news_articles = await get_recent_news_for_team(team_name, days=7)
    #     print(f"Fetched {len(news_articles)} news articles for {team_name}:")
    #     for article in news_articles:
    #         title = article.get('title', 'No Title')
    #         pub_date = article.get('published_date', 'N/A')
    #         print(f"  - {title} (Published: {pub_date})")
    # except Exception as e:
    #     print(f"Error in get_recent_news_for_team: {e}")

    # # Test fetching injury reports for the chosen team
    # print(f"\nTesting get_team_injury_report('{team_name}')...")
    # try:
    #     injuries = await get_team_injury_report(team_name)
    #     print(f"Fetched {len(injuries)} injury reports for {team_name}:")
    #     for injury in injuries:
    #         player = injury.get('player', 'Unknown Player')
    #         injury_type = injury.get('injury', 'Unknown Injury')
    #         status = injury.get('status', 'Unknown Status')
    #         print(f"  - {player}: {status} ({injury_type})")
    # except Exception as e:
    #     print(f"Error in get_team_injury_report: {e}")

if __name__ == '__main__':
    asyncio.run(main())
