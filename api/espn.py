from espn_api.football import League
from utils.cache import ttl_cache
import config


@ttl_cache(ttl_seconds=300)
def get_league(league_id: int = None, year: int = None, espn_s2: str = None, swid: str = None) -> League:
    league_id = league_id or config.ESPN_LEAGUE_ID
    year = year or config.ESPN_YEAR
    espn_s2 = espn_s2 or config.ESPN_S2
    swid = swid or config.ESPN_SWID

    if espn_s2 and swid:
        return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    return League(league_id=league_id, year=year)


def get_my_team(league: League, team_name: str) -> object | None:
    """Find a team in the league by partial name match."""
    for team in league.teams:
        if team_name.lower() in team.team_name.lower():
            return team
    return None


def get_roster_players(team) -> list[dict]:
    """Return a list of player dicts from an ESPN team object."""
    players = []
    for player in team.roster:
        players.append({
            "name": player.name,
            "position": player.position,
            "pro_team": player.proTeam,
            "injured": player.injured,
            "projected_total_points": player.projected_total_points,
            "total_points": player.total_points,
            "percent_owned": player.percent_owned,
        })
    return players


def get_free_agents(league: League, position: str = None, size: int = 50) -> list[dict]:
    """Return top free agents, optionally filtered by position."""
    players = league.free_agents(size=size)
    result = []
    for p in players:
        if position and p.position != position:
            continue
        result.append({
            "name": p.name,
            "position": p.position,
            "pro_team": p.proTeam,
            "projected_total_points": p.projected_total_points,
            "percent_owned": p.percent_owned,
        })
    return result


def get_current_week(league: League) -> int:
    return league.current_week


def get_box_scores(league: League, week: int = None) -> list:
    week = week or league.current_week
    return league.box_scores(week)
