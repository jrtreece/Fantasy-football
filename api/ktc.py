"""
KeepTradeCut (KTC) player trade values.
Fetches dynasty and redraft values from KTC's public data endpoint.
"""
import requests
from utils.cache import ttl_cache

KTC_URL = "https://keeptradecut.com/api/players?format=2"
KTC_REDRAFT_URL = "https://keeptradecut.com/api/players?format=1"


@ttl_cache(ttl_seconds=3600)
def get_dynasty_values() -> list[dict]:
    """Returns list of {name, position, team, value, age} for dynasty format."""
    return _fetch_ktc(KTC_URL)


@ttl_cache(ttl_seconds=3600)
def get_redraft_values() -> list[dict]:
    """Returns list of {name, position, team, value} for redraft format."""
    return _fetch_ktc(KTC_REDRAFT_URL)


def _fetch_ktc(url: str) -> list[dict]:
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        players = []
        for p in data:
            players.append({
                "name": p.get("playerName", ""),
                "slug": p.get("slug", ""),
                "position": p.get("position", ""),
                "team": p.get("team", ""),
                "value": p.get("value", 0),
                "age": p.get("age"),
                "rank": p.get("rank"),
            })
        return players
    except Exception:
        return []


def build_value_map(dynasty: bool = True) -> dict[str, int]:
    """Returns {player_name_lower: value} for quick lookup."""
    players = get_dynasty_values() if dynasty else get_redraft_values()
    return {p["name"].lower(): p["value"] for p in players}


def get_player_value(name: str, dynasty: bool = True) -> int:
    value_map = build_value_map(dynasty)
    return value_map.get(name.lower(), 0)
