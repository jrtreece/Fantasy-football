"""
Trade recommendation engine.

Algorithm:
- For every position combination (give/receive), find value-balanced swaps
  across all opponent rosters that upgrade your starting lineup.
- Does NOT require mutual need/surplus overlap — any team could accept
  a good value offer regardless of their roster shape.
- Always returns results by widening search automatically if needed.
"""
import pandas as pd
from itertools import product as iproduct

SCORED_POSITIONS = ["QB", "RB", "WR", "TE"]


def score_roster_by_position(players: list[dict], starter_slots: dict) -> dict:
    """
    Returns {position: {"starters": [...], "bench": [...], "all": [...], "starter_value": int}}
    """
    df = pd.DataFrame(players) if players else pd.DataFrame()
    result = {}
    for pos in SCORED_POSITIONS:
        if df.empty:
            result[pos] = {"starters": [], "bench": [], "all": [], "starter_value": 0}
            continue
        pos_df = df[df["position"] == pos].sort_values("value", ascending=False)
        n = starter_slots.get(pos, 1)
        starters = pos_df.head(n).to_dict("records")
        bench = pos_df.iloc[n:].to_dict("records")
        result[pos] = {
            "starters": starters,
            "bench": bench,
            "all": pos_df.to_dict("records"),
            "starter_value": int(pos_df.head(n)["value"].sum()) if not pos_df.empty else 0,
        }
    return result


def generate_recommendations(
    my_team_name: str,
    my_players: list[dict],
    all_rosters: dict,
    starter_slots: dict,
    dynasty: bool = True,
    max_results: int = 10,
    fairness_window: float = 0.30,
) -> list[dict]:
    """
    Always returns trade recommendations by progressively relaxing constraints
    until results are found.

    Returns list sorted by score (best first).
    """
    for window in [fairness_window, 0.40, 0.55, 0.70]:
        recs = _find_trades(
            my_team_name, my_players, all_rosters,
            starter_slots, window
        )
        if recs:
            return recs[:max_results]
    return []


def _find_trades(my_team_name, my_players, all_rosters, starter_slots, fairness_window):
    my_scores = score_roster_by_position(my_players, starter_slots)

    # My weakest starter value per position → how much room for improvement
    my_weakest = {
        pos: (s["starters"][-1]["value"] if s["starters"] else 0)
        for pos, s in my_scores.items()
    }

    # All my tradeable players (I can give any of them)
    my_all = {pos: s["all"] for pos, s in my_scores.items()}

    candidates = []

    for team_name, their_players in all_rosters.items():
        if team_name == my_team_name or not their_players:
            continue

        their_scores = score_roster_by_position(their_players, starter_slots)

        # Try every give_pos × recv_pos combination
        for recv_pos in SCORED_POSITIONS:
            their_at_recv = their_scores.get(recv_pos, {}).get("all", [])
            if not their_at_recv:
                continue

            for give_pos in SCORED_POSITIONS:
                my_at_give = my_all.get(give_pos, [])
                if not my_at_give:
                    continue

                for give_player, recv_player in iproduct(my_at_give, their_at_recv):
                    gv = give_player.get("value", 0)
                    rv = recv_player.get("value", 0)
                    if gv < 500 or rv < 500:
                        continue

                    # Value balance check
                    spread = abs(rv - gv) / max(gv, rv)
                    if spread > fairness_window:
                        continue

                    # Does receiving this player upgrade my starter at recv_pos?
                    my_worst_starter_at_recv = my_weakest.get(recv_pos, 0)
                    upgrades_starter = rv > my_worst_starter_at_recv

                    # Score: prioritize upgrades, then value gain, then fairness
                    upgrade_bonus = (rv - my_worst_starter_at_recv) if upgrades_starter else 0
                    delta = rv - gv
                    score = (
                        upgrade_bonus * 0.5
                        + max(delta, 0) * 0.3
                        + (1 - spread) * 2000 * 0.2
                    )

                    candidates.append({
                        "partner": team_name,
                        "give": give_player["name"],
                        "give_position": give_pos,
                        "give_value": gv,
                        "receive": recv_player["name"],
                        "receive_position": recv_pos,
                        "receive_value": rv,
                        "value_delta": delta,
                        "fairness_pct": round((1 - spread) * 100, 1),
                        "upgrades_starter": upgrades_starter,
                        "my_need_filled": recv_pos,
                        "score": round(score, 1),
                        "reason": _reason(give_player, recv_player, give_pos, recv_pos,
                                          upgrades_starter, delta, my_worst_starter_at_recv),
                    })

    # Deduplicate: keep best score per (give, receive) pair
    best = {}
    for c in candidates:
        key = (c["give"], c["receive"])
        if key not in best or c["score"] > best[key]["score"]:
            best[key] = c

    return sorted(best.values(), key=lambda x: x["score"], reverse=True)


def _reason(give_player, recv_player, give_pos, recv_pos,
            upgrades_starter, delta, current_worst_starter_val) -> str:
    gname = give_player["name"]
    rname = recv_player["name"]

    if upgrades_starter:
        gap = recv_player["value"] - current_worst_starter_val
        upgrade_str = f"upgrades your starting {recv_pos} (+'{ gap:,}' value over current starter)"
    else:
        upgrade_str = f"adds depth at {recv_pos}"

    if delta > 300:
        value_str = f"and you come out ahead in value (+{delta:,})"
    elif delta < -300:
        value_str = f"giving up slight value ({delta:,}) for the positional upgrade"
    else:
        value_str = "in a roughly even swap"

    return f"Getting {rname} {upgrade_str}, {value_str}. Offer {gname} from your {give_pos} depth."
