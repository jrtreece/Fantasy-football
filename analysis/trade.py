"""
Trade analyzer: evaluate a proposed trade using KTC values.
"""
from api.ktc import get_player_value, get_dynasty_values, get_redraft_values


def evaluate_trade(
    giving: list[str],
    receiving: list[str],
    dynasty: bool = True,
) -> dict:
    """
    Evaluate a trade proposal.

    Args:
        giving: List of player names you are trading away.
        receiving: List of player names you are receiving.
        dynasty: Use dynasty values if True, redraft if False.

    Returns:
        {
          "giving": [{name, value}, ...],
          "receiving": [{name, value}, ...],
          "give_total": int,
          "receive_total": int,
          "delta": int,           # positive = you win the trade
          "verdict": str,
          "fairness_pct": float,  # how close to 50/50 (100 = perfectly fair)
        }
    """
    give_details = [{"name": p, "value": get_player_value(p, dynasty)} for p in giving]
    recv_details = [{"name": p, "value": get_player_value(p, dynasty)} for p in receiving]

    give_total = sum(d["value"] for d in give_details)
    recv_total = sum(d["value"] for d in recv_details)
    delta = recv_total - give_total

    total = give_total + recv_total
    fairness_pct = round(100 - abs(delta) / max(total, 1) * 100, 1) if total else 100.0

    if delta > 1000:
        verdict = "Strong Win"
    elif delta > 300:
        verdict = "Win"
    elif delta >= -300:
        verdict = "Fair"
    elif delta >= -1000:
        verdict = "Loss"
    else:
        verdict = "Strong Loss"

    return {
        "giving": give_details,
        "receiving": recv_details,
        "give_total": give_total,
        "receive_total": recv_total,
        "delta": delta,
        "verdict": verdict,
        "fairness_pct": fairness_pct,
    }


def search_players(query: str, dynasty: bool = True, limit: int = 10) -> list[dict]:
    """Search KTC player list by name for autocomplete."""
    players = get_dynasty_values() if dynasty else get_redraft_values()
    query_lower = query.lower()
    matches = [p for p in players if query_lower in p["name"].lower()]
    return matches[:limit]
