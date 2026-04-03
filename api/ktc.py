"""
KeepTradeCut (KTC) player trade values.
Fetches dynasty and redraft values from KTC's public data endpoint.

KTC format values:
  0 = Dynasty 1QB
  1 = Dynasty Superflex
  2 = Redraft
"""
import requests
from utils.cache import ttl_cache

KTC_BASE = "https://keeptradecut.com/api/players"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://keeptradecut.com/",
    "Origin": "https://keeptradecut.com",
}


@ttl_cache(ttl_seconds=3600)
def get_dynasty_values(superflex: bool = False) -> list[dict]:
    """Dynasty values. superflex=False → 1QB (format=0), superflex=True → SF (format=1)."""
    fmt = 1 if superflex else 0
    return _fetch_ktc(fmt)


@ttl_cache(ttl_seconds=3600)
def get_redraft_values() -> list[dict]:
    """Redraft values (format=2)."""
    return _fetch_ktc(2)


def _fetch_ktc(format_id: int) -> list[dict]:
    url = f"{KTC_BASE}?format={format_id}"
    try:
        resp = requests.get(url, timeout=15, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"KTC returned unexpected data: {str(data)[:200]}")
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
        return [p for p in players if p["name"]]
    except Exception as e:
        # Re-raise so callers can show a useful error instead of silent empty
        raise RuntimeError(f"Failed to fetch KTC data (format={format_id}): {e}") from e


def build_value_map(dynasty: bool = True, superflex: bool = False) -> dict[str, int]:
    """Returns {player_name_lower: value} for quick lookup."""
    players = get_dynasty_values(superflex) if dynasty else get_redraft_values()
    return {p["name"].lower(): p["value"] for p in players}


def get_player_value(name: str, dynasty: bool = True, superflex: bool = False) -> int:
    value_map = build_value_map(dynasty, superflex)
    return value_map.get(name.lower(), 0)
