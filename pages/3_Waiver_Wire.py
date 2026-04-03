import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.waiver import rank_waivers

st.set_page_config(page_title="Waiver Wire", page_icon="📋", layout="wide")
st.title("📋 Waiver Wire")

platform = st.session_state.get("platform", "Sleeper")
dynasty = st.session_state.get("dynasty", False)

# ── Load available players ────────────────────────────────────────────────────
available = []

if platform == "ESPN":
    league_id = st.session_state.get("espn_league_id", "")
    if not league_id:
        st.warning("Enter your ESPN League ID in the sidebar.")
        st.stop()
    try:
        from api.espn import get_league, get_free_agents
        from api.ktc import build_value_map
        league = get_league(
            league_id=int(league_id),
            year=st.session_state.get("espn_year", 2025),
            espn_s2=st.session_state.get("espn_s2"),
            swid=st.session_state.get("espn_swid"),
        )
        value_map = build_value_map(dynasty)
        raw = get_free_agents(league, size=100)
        for p in raw:
            available.append({
                "name": p["name"],
                "position": p["position"],
                "projected_points": p.get("projected_total_points", 0),
                "value": value_map.get(p["name"].lower(), 0),
                "percent_owned": p.get("percent_owned", 0),
            })
    except Exception as e:
        st.error(f"Error loading ESPN data: {e}")
        st.stop()

elif platform == "Sleeper":
    league_id = st.session_state.get("sleeper_league_id", "")
    if not league_id:
        st.warning("Enter your Sleeper League ID in the sidebar.")
        st.stop()
    try:
        from api.sleeper import build_roster_map, get_all_players, get_trending_players
        from api.ktc import get_dynasty_values, get_redraft_values

        roster_map = build_roster_map(league_id)
        all_players = get_all_players()
        rostered_ids = set()
        for roster in roster_map.values():
            rostered_ids.update(roster["players"])

        try:
            value_data = get_dynasty_values() if dynasty else get_redraft_values()
        except RuntimeError as ktc_err:
            st.error(f"Could not load KTC player values: {ktc_err}")
            st.stop()
        value_map = {p["name"].lower(): p for p in value_data}

        for pid, p in all_players.items():
            if pid in rostered_ids:
                continue
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            pos = p.get("position", "")
            if not name or pos not in ("QB", "RB", "WR", "TE", "K"):
                continue
            ktc = value_map.get(name.lower(), {})
            if ktc.get("value", 0) < 500:
                continue  # skip very low-value players
            available.append({
                "name": name,
                "position": pos,
                "projected_points": 0,
                "value": ktc.get("value", 0),
            })
    except Exception as e:
        st.error(f"Error loading Sleeper data: {e}")
        st.stop()

# ── Filter controls ───────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])
with col1:
    pos_filter = st.multiselect(
        "Filter by position", ["QB", "RB", "WR", "TE", "K"],
        default=["QB", "RB", "WR", "TE"]
    )
with col2:
    team_weaknesses = st.multiselect(
        "My weak positions (boosts ranking)",
        ["QB", "RB", "WR", "TE", "K"],
    )

filtered = [p for p in available if p["position"] in pos_filter] if pos_filter else available

# ── Rank and display ─────────────────────────────────────────────────────────
df = rank_waivers(filtered, team_weaknesses, top_n=50)

if df.empty:
    st.info("No available players found.")
else:
    def highlight_need(row):
        color = "background-color: #1a4a2e" if row["need_boost"] == "Yes" else ""
        return [color] * len(row)

    st.dataframe(
        df.style.apply(highlight_need, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Highlighted rows fill one of your weak positions.")
