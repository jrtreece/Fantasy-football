import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.ktc import get_dynasty_values, get_redraft_values
from analysis.team import analyze_roster

st.set_page_config(page_title="Team Analysis", page_icon="📊", layout="wide")
st.title("📊 Team Analysis")

platform = st.session_state.get("platform", "Sleeper")
dynasty = st.session_state.get("dynasty", False)

# ── Load roster ──────────────────────────────────────────────────────────────
players = []

if platform == "Sleeper":
    league_id = st.session_state.get("sleeper_league_id", "")
    if not league_id:
        st.warning("Enter your Sleeper League ID in the sidebar.")
        st.stop()
    try:
        from api.sleeper import build_roster_map, get_all_players
        roster_map = build_roster_map(league_id)
        all_players = get_all_players()

        owner_options = {v["owner"]: k for k, v in roster_map.items()}
        selected_owner = st.selectbox("Select your team", list(owner_options.keys()))
        roster_id = owner_options[selected_owner]
        player_ids = roster_map[roster_id]["players"]

        try:
            value_data = get_dynasty_values() if dynasty else get_redraft_values()
        except RuntimeError as ktc_err:
            st.error(f"Could not load KTC player values: {ktc_err}")
            st.stop()
        value_map = {p["name"].lower(): p for p in value_data}

        for pid in player_ids:
            p = all_players.get(pid, {})
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            pos = p.get("position", "")
            if not name or not pos:
                continue
            ktc = value_map.get(name.lower(), {})
            players.append({
                "name": name,
                "position": pos,
                "value": ktc.get("value", 0),
                "age": ktc.get("age") or p.get("age"),
                "projected_points": 0,
            })
    except Exception as e:
        st.error(f"Error loading Sleeper data: {e}")
        st.stop()

else:  # ESPN
    league_id = st.session_state.get("espn_league_id", "")
    if not league_id:
        st.warning("Enter your ESPN League ID in the sidebar.")
        st.stop()
    try:
        from api.espn import get_league, get_roster_players
        from api.ktc import build_value_map
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
        value_map = build_value_map(dynasty)
        for p in raw:
            players.append({
                "name": p["name"],
                "position": p["position"],
                "value": value_map.get(p["name"].lower(), 0),
                "projected_points": p.get("projected_total_points", 0),
                "age": None,
            })
    except Exception as e:
        st.error(f"Error loading ESPN data: {e}")
        st.stop()

if not players:
    st.info("No player data found.")
    st.stop()

# ── Analysis ──────────────────────────────────────────────────────────────────
result = analyze_roster(players, dynasty=dynasty)
by_pos = result.get("by_position", {})
strengths = result.get("strengths", [])
weaknesses = result.get("weaknesses", [])

col1, col2 = st.columns(2)
with col1:
    st.success(f"**Strengths:** {', '.join(strengths) if strengths else 'None identified'}")
with col2:
    st.error(f"**Weaknesses:** {', '.join(weaknesses) if weaknesses else 'None identified'}")

# ── Positional grade cards ────────────────────────────────────────────────────
st.subheader("Positional Grades")
grade_cols = st.columns(len(by_pos))
grade_color = {"A+": "green", "A": "green", "B": "blue", "C": "orange", "D": "red", "N/A": "gray"}
for i, (pos, data) in enumerate(by_pos.items()):
    with grade_cols[i]:
        color = grade_color.get(data["grade"], "gray")
        st.markdown(f"### :{color}[{data['grade']}]")
        st.markdown(f"**{pos}**")
        st.caption(f"Value: {data['starter_value']:,}")
        if dynasty and data.get("avg_age"):
            st.caption(f"Avg age: {data['avg_age']}")

# ── Roster table ─────────────────────────────────────────────────────────────
st.subheader("Full Roster")
df = pd.DataFrame(players).sort_values(["position", "value"], ascending=[True, False])
cols = ["name", "position", "value"]
if dynasty and "age" in df.columns:
    cols.append("age")
st.dataframe(df[cols], use_container_width=True, hide_index=True)

# ── Bar chart: value by position ─────────────────────────────────────────────
st.subheader("Starter Value by Position")
positions = list(by_pos.keys())
values = [by_pos[p]["starter_value"] for p in positions]
colors = ["red" if p in weaknesses else "green" if p in strengths else "steelblue" for p in positions]

fig = go.Figure(go.Bar(x=positions, y=values, marker_color=colors))
fig.update_layout(yaxis_title="KTC Value", xaxis_title="Position", height=350)
st.plotly_chart(fig, use_container_width=True)
