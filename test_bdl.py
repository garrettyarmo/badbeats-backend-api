from balldontlie import BalldontlieAPI

api = BalldontlieAPI(api_key="f11af932-e775-45a0-a47e-10823a2e041b")
teams = api.nba.teams.list()

for team in teams:
    print(team)

