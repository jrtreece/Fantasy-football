"""
Trade recommendation engine.

Algorithm:
1. Score every team's roster by position (starter + bench depth value)
2. Identify your positional needs (below your own average) and surpluses
3. For each opponent: find their surplus positions and their needs
4. Match: opponent surplus at your need + your surplus at their need = trade opportunity
5. Generate specific player proposals that are roughly value-balanced
6. Score each proposal and return the best ones
"""
import pandas as pd
from itertools import product


FLEX_POSITIONS = {"RB", "WR", "TE"}
SCORED_POSITIONS = ["QB", "RB", "WR", "TE"]


def score_roster_by_position(players: list[dict], starter_slots: dict) -> dict:
    """
    Returns {position: {"starter_value": int, "depth_value": int, "players": [...]}}
    Players must have: name, position, value
    """
    df = pd.DataFrame(players)
    if df.empty:
        return {}
    result = {}
    for pos in SCORED_POSITIONS:
        pos_players = df[df["position"] == pos].sort_values("value", ascending=False)
        n_starters = starter_slots.get(pos, 1)
        starters = pos_players.head(n_starters)
        bench = pos_players.iloc[n_starters:]
        result[pos] = {
            "starter_value": int(starters["value"].sum()),
            "depth_value": int(bench["value"].sum()),
            "starters": starters.to_dict("records"),
            "bench": bench.to_dict("records"),
            "all": pos_players.to_dict("records"),
        }
    return result


def identify_needs_and_surpluses(scores: dict, threshold: float = 0.80) -> tuple[list, list]:
    """
    Returns (needs, surpluses) as lists of positions.
    A position is a need if starter_value < threshold * avg_starter_value.
    A position is a surplus if it has meaningful bench depth.
    """
    starter_vals = {p: s["starter_value"] for p, s in scores.items() if s["starter_value"] > 0}
    if not starter_vals:
        return [], []
    avg = sum(starter_vals.values()) / len(starter_vals)

    needs = [p for p, v in starter_vals.items() if v < avg * threshold]
    # Surplus = strong starters AND bench players with real value
    surpluses = [
        p for p, s in scores.items()
        if s["starter_value"] >= avg * 1.0 and len(s["bench"]) > 0 and s["bench"][0]["value"] > 1000
    ]
    return needs, surpluses


def generate_recommendations(
    my_team_name: str,
    my_players: list[dict],
    all_rosters: dict,          # {team_name: [player dicts]}
    starter_slots: dict,
    dynasty: bool = True,
    max_results: int = 10,
    fairness_window: float = 0.30,
) -> list[dict]:
    """
    Generate trade recommendations for the selected team.

    Returns list of recommendation dicts sorted by score (best first):
    {
      partner, give, receive,
      give_value, receive_value, value_delta,
      my_need_filled, their_need_filled,
      reason, score
    }
    """
    my_scores = score_roster_by_position(my_players, starter_slots)
    my_needs, my_surpluses = identify_needs_and_surpluses(my_scores)

    recommendations = []

    for team_name, their_players in all_rosters.items():
        if team_name == my_team_name:
            continue
        if not their_players:
            continue

        their_scores = score_roster_by_position(their_players, starter_slots)
        their_needs, their_surpluses = identify_needs_and_surpluses(their_scores)

        # Positions I can receive from (their surplus at my need)
        recv_positions = [p for p in my_needs if p in their_surpluses]
        # Positions I can give from (my surplus at their need)
        give_positions = [p for p in their_needs if p in my_surpluses]

        if not recv_positions or not give_positions:
            continue

        # Try combinations of give/receive positions
        for give_pos, recv_pos in product(give_positions[:2], recv_positions[:2]):
            # Candidate players I can give (my bench at give_pos)
            give_candidates = my_scores[give_pos]["bench"][:3]
            if not give_candidates:
                give_candidates = my_scores[give_pos]["starters"][-1:]

            # Candidate players I can receive (their bench at recv_pos, or their weakest starter)
            recv_candidates = their_scores[recv_pos]["bench"][:3]
            if not recv_candidates:
                recv_candidates = their_scores[recv_pos]["starters"][-1:]

            for give_player, recv_player in product(give_candidates[:2], recv_candidates[:2]):
                gv = give_player.get("value", 0)
                rv = recv_player.get("value", 0)
                if gv == 0 or rv == 0:
                    continue

                # Skip if values are too far apart
                spread = abs(rv - gv) / max(gv, rv)
                if spread > fairness_window:
                    continue

                delta = rv - gv
                improvement = _position_improvement(my_scores, recv_pos, recv_player, starter_slots)
                their_improvement = _position_improvement(their_scores, give_pos, give_player, starter_slots)

                score = (
                    improvement * 0.5
                    + their_improvement * 0.3       # more realistic if it helps them too
                    + (1 - spread) * 100 * 0.2      # bonus for fairness
                )

                reason = _build_reason(
                    give_player, recv_player, give_pos, recv_pos,
                    my_needs, their_needs, delta
                )

                recommendations.append({
                    "partner": team_name,
                    "give": give_player["name"],
                    "give_position": give_pos,
                    "give_value": gv,
                    "receive": recv_player["name"],
                    "receive_position": recv_pos,
                    "receive_value": rv,
                    "value_delta": delta,
                    "fairness_pct": round((1 - spread) * 100, 1),
                    "my_need_filled": recv_pos,
                    "their_need_filled": give_pos,
                    "reason": reason,
                    "score": round(score, 1),
                })

    # Deduplicate (same give+receive player pair from multiple paths)
    seen = set()
    unique = []
    for r in sorted(recommendations, key=lambda x: x["score"], reverse=True):
        key = (r["give"], r["receive"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:max_results]


def _position_improvement(scores: dict, pos: str, new_player: dict, starter_slots: dict) -> float:
    """How much does adding new_player improve the starter at pos? (0-100 scale)"""
    if pos not in scores or not scores[pos]["starters"]:
        return 50.0  # unknown, moderate score
    weakest_starter_val = scores[pos]["starters"][-1].get("value", 0)
    new_val = new_player.get("value", 0)
    if weakest_starter_val == 0:
        return 50.0
    improvement = (new_val - weakest_starter_val) / weakest_starter_val * 100
    return max(0.0, min(100.0, improvement))


def _build_reason(give_player, recv_player, give_pos, recv_pos,
                  my_needs, their_needs, delta) -> str:
    gname = give_player["name"]
    rname = recv_player["name"]
    parts = []
    parts.append(f"You upgrade your **{recv_pos}** by adding {rname}")
    if delta > 200:
        parts.append(f"and come out ahead in value (+{delta:,})")
    elif delta < -200:
        parts.append(f"giving up slight value ({delta:,}) to fill a need")
    else:
        parts.append("in a fair swap")
    if their_needs:
        parts.append(f"— {gname} fills their **{give_pos}** need, making this realistic")
    return ", ".join(parts) + "."
