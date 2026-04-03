import requests
from utils.cache import ttl_cache

SLEEPER_BASE = "https://api.sleeper.app/v1"


def _get(path: str) -> dict | list:
    resp = requests.get(f"{SLEEPER_BASE}{path}", timeout=10)
    resp.raise_for_status()
    return resp.json()


@ttl_cache(ttl_seconds=300)
def get_league(league_id: str) -> dict:
    return _get(f"/league/{league_id}")


@ttl_cache(ttl_seconds=300)
def get_rosters(league_id: str) -> list:
    return _get(f"/league/{league_id}/rosters")


@ttl_cache(ttl_seconds=300)
def get_users(league_id: str) -> list:
    return _get(f"/league/{league_id}/users")


@ttl_cache(ttl_seconds=300)
def get_matchups(league_id: str, week: int) -> list:
    return _get(f"/league/{league_id}/matchups/{week}")


@ttl_cache(ttl_seconds=3600)
def get_all_players() -> dict:
    """Returns the full Sleeper player database (~5MB, cache for 1 hour)."""
    return _get("/players/nfl")


@ttl_cache(ttl_seconds=300)
def get_transactions(league_id: str, week: int) -> list:
    return _get(f"/league/{league_id}/transactions/{week}")


def get_trending_players(sport: str = "nfl", type: str = "add", limit: int = 25) -> list:
    return _get(f"/players/{sport}/trending/{type}?limit={limit}")


def build_roster_map(league_id: str) -> dict:
    """Returns {roster_id: {'owner': username, 'players': [player_id, ...]}}"""
    rosters = get_rosters(league_id)
    users = get_users(league_id)
    user_map = {u["user_id"]: u.get("display_name", "Unknown") for u in users}
    result = {}
    for r in rosters:
        result[r["roster_id"]] = {
            "owner": user_map.get(r.get("owner_id"), "Unknown"),
            "owner_id": r.get("owner_id"),
            "players": r.get("players") or [],
            "starters": r.get("starters") or [],
        }
    return result
