"""
Team strength and weakness analysis.
Works with a normalized list of player dicts:
  {name, position, value, projected_points, age (optional)}
"""
import pandas as pd
from config import POSITION_ORDER, STARTER_SLOTS


def analyze_roster(players: list[dict], dynasty: bool = False) -> dict:
    """
    Given a list of player dicts, return a breakdown of team strengths/weaknesses.

    Returns:
        {
          "by_position": {pos: {"players": [...], "total_value": int, "grade": str}},
          "strengths": [pos, ...],
          "weaknesses": [pos, ...],
          "summary": str,
        }
    """
    df = pd.DataFrame(players)
    if df.empty:
        return {}

    positions = ["QB", "RB", "WR", "TE"]
    if "K" in df["position"].values:
        positions.append("K")

    by_position = {}
    scores = {}

    for pos in positions:
        pos_df = df[df["position"] == pos].sort_values("value", ascending=False)
        starter_count = STARTER_SLOTS.get(pos, 1)
        starters = pos_df.head(starter_count)
        bench = pos_df.iloc[starter_count:]

        starter_value = int(starters["value"].sum())
        bench_value = int(bench["value"].sum())
        total_value = starter_value + bench_value

        grade = _grade(starter_value, pos, starter_count)

        entry = {
            "starters": starters.to_dict("records"),
            "bench": bench.to_dict("records"),
            "starter_value": starter_value,
            "bench_value": bench_value,
            "total_value": total_value,
            "grade": grade,
            "depth": len(pos_df),
        }

        if dynasty and "age" in df.columns:
            ages = pos_df["age"].dropna()
            entry["avg_age"] = round(ages.mean(), 1) if not ages.empty else None

        by_position[pos] = entry
        scores[pos] = starter_value

    if scores:
        avg = sum(scores.values()) / len(scores)
        strengths = [p for p, v in scores.items() if v >= avg * 1.15]
        weaknesses = [p for p, v in scores.items() if v <= avg * 0.85]
    else:
        strengths, weaknesses = [], []

    return {
        "by_position": by_position,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def _grade(value: int, position: str, starter_count: int) -> str:
    """Rough letter grade based on KTC value thresholds."""
    per_starter = value / max(starter_count, 1)
    thresholds = {
        "QB": [(7000, "A+"), (5500, "A"), (4000, "B"), (2500, "C"), (0, "D")],
        "RB": [(6000, "A+"), (4500, "A"), (3000, "B"), (1500, "C"), (0, "D")],
        "WR": [(6000, "A+"), (4500, "A"), (3000, "B"), (1500, "C"), (0, "D")],
        "TE": [(6000, "A+"), (4500, "A"), (3000, "B"), (1500, "C"), (0, "D")],
        "K":  [(500,  "A+"), (300,  "A"), (200,  "B"), (100,  "C"), (0, "D")],
    }
    for threshold, grade in thresholds.get(position, [(0, "N/A")]):
        if per_starter >= threshold:
            return grade
    return "N/A"
