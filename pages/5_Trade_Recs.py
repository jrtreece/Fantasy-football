import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.recommend import generate_recommendations
from config import STARTER_SLOTS

st.set_page_config(page_title="Trade Recommendations", page_icon="💡", layout="wide")
st.title("💡 Trade Recommendations")
st.caption("Based on your roster's needs and other teams' surpluses, here are realistic trades to target.")

platform = st.session_state.get("platform", "Sleeper")
dynasty = st.session_state.get("dynasty", False)

# ── Load all rosters ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Loading league rosters...")
def load_all_rosters_sleeper(league_id: str, dynasty: bool) -> tuple[dict, dict]:
    """Returns (roster_map, value_map)"""
    from api.sleeper import build_roster_map, get_all_players
    from api.ktc import get_dynasty_values, get_redraft_values

    roster_map = build_roster_map(league_id)
    all_players = get_all_players()
    value_data = get_dynasty_values() if dynasty else get_redraft_values()
    value_map = {p["name"].lower(): p["value"] for p in value_data}

    rosters = {}
    for roster_id, info in roster_map.items():
        players = []
        for pid in (info.get("players") or []):
            p = all_players.get(pid, {})
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            pos = p.get("position", "")
            if not name or pos not in ("QB", "RB", "WR", "TE"):
                continue
            players.append({
                "name": name,
                "position": pos,
                "value": value_map.get(name.lower(), 0),
            })
        rosters[info["owner"]] = players

    return rosters, value_map


@st.cache_data(ttl=300, show_spinner="Loading league rosters...")
def load_all_rosters_espn(league_id: int, year: int, espn_s2: str, swid: str, dynasty: bool) -> tuple[dict, dict]:
    """Returns (roster_map, value_map)"""
    from api.espn import get_league, get_roster_players
    from api.ktc import build_value_map

    league = get_league(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    value_map = build_value_map(dynasty)

    rosters = {}
    for team in league.teams:
        players = []
        for p in get_roster_players(team):
            if p["position"] not in ("QB", "RB", "WR", "TE"):
                continue
            players.append({
                "name": p["name"],
                "position": p["position"],
                "value": value_map.get(p["name"].lower(), 0),
            })
        rosters[team.team_name] = players

    return rosters, value_map


# ── Fetch data based on platform ──────────────────────────────────────────────
try:
    if platform == "Sleeper":
        league_id = st.session_state.get("sleeper_league_id", "")
        if not league_id:
            st.warning("Enter your Sleeper League ID in the sidebar.")
            st.stop()
        all_rosters, value_map = load_all_rosters_sleeper(league_id, dynasty)
    else:
        league_id = st.session_state.get("espn_league_id", "")
        if not league_id:
            st.warning("Enter your ESPN League ID in the sidebar.")
            st.stop()
        all_rosters, value_map = load_all_rosters_espn(
            int(league_id),
            st.session_state.get("espn_year", 2025),
            st.session_state.get("espn_s2", ""),
            st.session_state.get("espn_swid", ""),
            dynasty,
        )
except RuntimeError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Error loading rosters: {e}")
    st.stop()

if not all_rosters:
    st.info("No roster data found.")
    st.stop()

# ── Team selector ─────────────────────────────────────────────────────────────
my_team = st.selectbox("Select your team", sorted(all_rosters.keys()))
my_players = all_rosters.get(my_team, [])

if not my_players:
    st.warning("No players found for this team.")
    st.stop()

# ── Settings ──────────────────────────────────────────────────────────────────
with st.expander("Settings"):
    col1, col2 = st.columns(2)
    with col1:
        max_results = st.slider("Max recommendations", 3, 20, 10)
    with col2:
        fairness = st.slider(
            "Fairness window (%)",
            10, 50, 30,
            help="How close in value the trade needs to be (lower = stricter)."
        )

# ── Generate recommendations ──────────────────────────────────────────────────
with st.spinner("Analyzing all rosters..."):
    recs = generate_recommendations(
        my_team_name=my_team,
        my_players=my_players,
        all_rosters=all_rosters,
        starter_slots=STARTER_SLOTS,
        dynasty=dynasty,
        max_results=max_results,
        fairness_window=fairness / 100,
    )

if not recs:
    st.info(
        "No strong trade recommendations found. This usually means your roster is "
        "well-balanced or other teams don't have surplus at your weak positions. "
        "Try widening the fairness window in Settings."
    )
    st.stop()

st.success(f"Found **{len(recs)}** trade opportunities")

# ── Display recommendations ───────────────────────────────────────────────────
for i, rec in enumerate(recs, 1):
    verdict_color = "green" if rec["value_delta"] >= 0 else "orange"
    sign = "+" if rec["value_delta"] >= 0 else ""

    with st.container(border=True):
        col_num, col_main, col_vals = st.columns([0.5, 4, 2])

        with col_num:
            st.markdown(f"### #{i}")

        with col_main:
            st.markdown(
                f"**Target:** {rec['partner']}  \n"
                f"**Give:** {rec['give']} ({rec['give_position']})"
                f" &nbsp;→&nbsp; "
                f"**Get:** {rec['receive']} ({rec['receive_position']})"
            )
            st.caption(rec["reason"])

        with col_vals:
            st.metric(
                "Value Delta",
                f"{sign}{rec['value_delta']:,}",
                delta=f"{sign}{rec['value_delta']:,}",
            )
            st.caption(f"Fairness: {rec['fairness_pct']}%")

# ── Summary table ─────────────────────────────────────────────────────────────
st.subheader("All Recommendations at a Glance")
df = pd.DataFrame(recs)[[
    "partner", "give", "give_value", "receive", "receive_value", "value_delta", "fairness_pct", "my_need_filled"
]]
df.columns = ["Trade Partner", "You Give", "Give Value", "You Receive", "Receive Value", "Delta", "Fairness %", "Fills Need"]
st.dataframe(df, use_container_width=True, hide_index=True)
