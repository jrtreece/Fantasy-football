"""
Start/Sit optimizer: compare projected points to find the optimal lineup.
"""
import pandas as pd


FLEX_POSITIONS = {"RB", "WR", "TE"}


def optimize_lineup(
    roster: list[dict],
    starter_slots: dict,
) -> dict:
    """
    Determine the optimal starting lineup based on projected points.

    Args:
        roster: List of {name, position, projected_points, ...}
        starter_slots: {position: count} e.g. {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1}

    Returns:
        {
          "starters": [{name, position, projected_points, slot}, ...],
          "bench": [{name, position, projected_points}, ...],
          "total_projected": float,
          "recommendations": [str, ...],
        }
    """
    df = pd.DataFrame(roster)
    if df.empty:
        return {"starters": [], "bench": [], "total_projected": 0, "recommendations": []}

    df = df.sort_values("projected_points", ascending=False)
    used = set()
    starters = []

    # Fill positional slots first (QB, RB, WR, TE, K, DEF)
    for pos, count in starter_slots.items():
        if pos == "FLEX":
            continue
        eligible = df[(df["position"] == pos) & (~df.index.isin(used))]
        for _, row in eligible.head(count).iterrows():
            starters.append({**row.to_dict(), "slot": pos})
            used.add(row.name)

    # Fill FLEX slot with best remaining flex-eligible player
    flex_count = starter_slots.get("FLEX", 0)
    if flex_count:
        flex_eligible = df[(df["position"].isin(FLEX_POSITIONS)) & (~df.index.isin(used))]
        for _, row in flex_eligible.head(flex_count).iterrows():
            starters.append({**row.to_dict(), "slot": "FLEX"})
            used.add(row.name)

    bench = df[~df.index.isin(used)].to_dict("records")
    total = sum(s.get("projected_points", 0) for s in starters)

    recommendations = _generate_recommendations(starters, bench)

    return {
        "starters": starters,
        "bench": bench,
        "total_projected": round(total, 1),
        "recommendations": recommendations,
    }


def _generate_recommendations(starters: list[dict], bench: list[dict]) -> list[str]:
    """Flag cases where a bench player outprojects a starter at the same position."""
    recs = []
    starter_df = pd.DataFrame(starters) if starters else pd.DataFrame()
    bench_df = pd.DataFrame(bench) if bench else pd.DataFrame()

    if starter_df.empty or bench_df.empty:
        return recs

    for pos in ["QB", "RB", "WR", "TE", "K"]:
        s_pos = starter_df[starter_df["position"] == pos].sort_values("projected_points")
        b_pos = bench_df[bench_df["position"] == pos].sort_values("projected_points", ascending=False)

        if s_pos.empty or b_pos.empty:
            continue

        worst_starter = s_pos.iloc[0]
        best_bench = b_pos.iloc[0]

        if best_bench["projected_points"] > worst_starter["projected_points"] + 2:
            recs.append(
                f"Start {best_bench['name']} ({best_bench['projected_points']:.1f} pts) "
                f"over {worst_starter['name']} ({worst_starter['projected_points']:.1f} pts) at {pos}"
            )

    return recs
