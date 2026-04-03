"""
Player trade values via FantasyCalc's public API.
Replaces KTC which removed their public endpoint.

FantasyCalc API: https://fantasycalc.com/api/values/current
  numQbs=1  → 1QB league
  numQbs=2  → Superflex league
  ppr=1     → full PPR
  numTeams  → league size (default 12)
"""
import requests
from utils.cache import ttl_cache

FANTASYCALC_BASE = "https://fantasycalc.com/api/values/current"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


@ttl_cache(ttl_seconds=3600)
def get_dynasty_values(superflex: bool = False) -> list[dict]:
    """Dynasty player values. superflex=True for SF leagues."""
    return _fetch(num_qbs=2 if superflex else 1, dynasty=True)


@ttl_cache(ttl_seconds=3600)
def get_redraft_values() -> list[dict]:
    """Redraft player values."""
    return _fetch(num_qbs=1, dynasty=False)


def _fetch(num_qbs: int, dynasty: bool) -> list[dict]:
    params = {
        "numQbs": num_qbs,
        "ppr": 1,
        "numTeams": 12,
        "type": "dynasty" if dynasty else "redraft",
    }
    try:
        resp = requests.get(FANTASYCALC_BASE, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"Unexpected response: {str(data)[:200]}")
        players = []
        for entry in data:
            p = entry.get("player", {})
            name = p.get("name", "")
            if not name:
                continue
            players.append({
                "name": name,
                "position": p.get("position", ""),
                "team": p.get("maybeTeam", ""),
                "age": p.get("maybeAge"),
                "value": entry.get("value", 0),
                "rank": entry.get("overallRank"),
                "sleeper_id": p.get("sleeperId"),
            })
        return players
    except Exception as e:
        raise RuntimeError(f"Failed to fetch FantasyCalc data: {e}") from e


def build_value_map(dynasty: bool = True, superflex: bool = False) -> dict[str, int]:
    """Returns {player_name_lower: value} for quick lookup."""
    players = get_dynasty_values(superflex) if dynasty else get_redraft_values()
    return {p["name"].lower(): p["value"] for p in players}


def get_player_value(name: str, dynasty: bool = True, superflex: bool = False) -> int:
    value_map = build_value_map(dynasty, superflex)
    return value_map.get(name.lower(), 0)
