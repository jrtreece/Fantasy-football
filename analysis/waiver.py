"""
Waiver wire recommendations: rank available players by value vs. team need.
"""
import pandas as pd


def rank_waivers(
    available_players: list[dict],
    team_weaknesses: list[str],
    top_n: int = 30,
) -> pd.DataFrame:
    """
    Rank available players, boosting those who fill team weaknesses.

    Args:
        available_players: List of {name, position, value, projected_points, ...}
        team_weaknesses: Positions the team is weak at (from team analysis).
        top_n: How many players to return.

    Returns:
        DataFrame sorted by priority score.
    """
    if not available_players:
        return pd.DataFrame()

    df = pd.DataFrame(available_players)

    # Normalize value to 0-100 scale for scoring
    max_val = df["value"].max() if "value" in df.columns and df["value"].max() > 0 else 1
    df["value_score"] = df.get("value", 0) / max_val * 100

    max_proj = df["projected_points"].max() if "projected_points" in df.columns and df["projected_points"].max() > 0 else 1
    df["proj_score"] = df.get("projected_points", 0) / max_proj * 100

    # Weighted composite: 60% trade value, 40% projected points
    df["composite_score"] = df["value_score"] * 0.6 + df["proj_score"] * 0.4

    # Boost players who fill team weaknesses
    df["need_boost"] = df["position"].apply(lambda p: 15 if p in team_weaknesses else 0)
    df["priority_score"] = df["composite_score"] + df["need_boost"]

    df = df.sort_values("priority_score", ascending=False).head(top_n)
    df["need_boost"] = df["need_boost"].apply(lambda x: "Yes" if x > 0 else "No")

    cols = ["name", "position", "priority_score", "need_boost"]
    if "projected_points" in df.columns:
        cols.insert(3, "projected_points")
    if "value" in df.columns:
        cols.insert(3, "value")

    return df[cols].reset_index(drop=True)
