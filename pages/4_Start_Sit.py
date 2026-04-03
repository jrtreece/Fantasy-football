import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.lineup import optimize_lineup
from config import STARTER_SLOTS

st.set_page_config(page_title="Start / Sit", page_icon="🏆", layout="wide")
st.title("🏆 Start / Sit")

platform = st.session_state.get("platform", "Sleeper")
dynasty = st.session_state.get("dynasty", False)

roster = []

if platform == "ESPN":
    league_id = st.session_state.get("espn_league_id", "")
    if not league_id:
        st.warning("Enter your ESPN League ID in the sidebar.")
        st.stop()
    try:
        from api.espn import get_league, get_roster_players
        league = get_league(
            league_id=int(league_id),
            year=st.session_state.get("espn_year", 2025),
            espn_s2=st.session_state.get("espn_s2"),
            swid=st.session_state.get("espn_swid"),
        )
        team_options = {t.team_name: t for t in league.teams}
        selected_team_name = st.selectbox("Select your team", list(team_options.keys()))
        team = team_options[selected_team_name]
        raw = get_roster_players(team)
        for p in raw:
            roster.append({
                "name": p["name"],
                "position": p["position"],
                "projected_points": p.get("projected_total_points", 0),
            })
    except Exception as e:
        st.error(f"Error loading ESPN data: {e}")
        st.stop()

elif platform == "Sleeper":
    league_id = st.session_state.get("sleeper_league_id", "")
    if not league_id:
        st.warning("Enter your Sleeper League ID in the sidebar.")
        st.stop()

    st.info(
        "Sleeper does not provide weekly projections via their public API. "
        "Projections below are set to 0. For best results, use ESPN which includes projections."
    )
    try:
        from api.sleeper import build_roster_map, get_all_players
        roster_map = build_roster_map(league_id)
        all_players = get_all_players()

        owner_options = {v["owner"]: k for k, v in roster_map.items()}
        selected_owner = st.selectbox("Select your team", list(owner_options.keys()))
        roster_id = owner_options[selected_owner]
        player_ids = roster_map[roster_id]["players"]

        for pid in player_ids:
            p = all_players.get(pid, {})
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            pos = p.get("position", "")
            if not name or not pos:
                continue
            roster.append({"name": name, "position": pos, "projected_points": 0})
    except Exception as e:
        st.error(f"Error loading Sleeper data: {e}")
        st.stop()

if not roster:
    st.info("No roster data loaded.")
    st.stop()

# ── Starter slot customization ────────────────────────────────────────────────
with st.expander("Customize starter slots"):
    cols = st.columns(len(STARTER_SLOTS))
    custom_slots = {}
    for i, (pos, default) in enumerate(STARTER_SLOTS.items()):
        with cols[i]:
            custom_slots[pos] = st.number_input(pos, min_value=0, max_value=5, value=default, step=1)

# ── Optimize ──────────────────────────────────────────────────────────────────
result = optimize_lineup(roster, custom_slots)

# ── Recommendations ───────────────────────────────────────────────────────────
if result["recommendations"]:
    st.subheader("Recommendations")
    for rec in result["recommendations"]:
        st.warning(f"⚡ {rec}")
else:
    st.success("Your lineup looks optimal!")

st.metric("Total Projected Points", result["total_projected"])

# ── Starters table ────────────────────────────────────────────────────────────
st.subheader("Optimal Starters")
if result["starters"]:
    starters_df = pd.DataFrame(result["starters"])[["slot", "name", "position", "projected_points"]]
    starters_df.columns = ["Slot", "Player", "Position", "Proj. Pts"]
    st.dataframe(starters_df, use_container_width=True, hide_index=True)

# ── Bench table ───────────────────────────────────────────────────────────────
st.subheader("Bench")
if result["bench"]:
    bench_df = pd.DataFrame(result["bench"])[["name", "position", "projected_points"]]
    bench_df.columns = ["Player", "Position", "Proj. Pts"]
    st.dataframe(bench_df, use_container_width=True, hide_index=True)
