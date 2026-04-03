import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.recommend import generate_recommendations
from config import STARTER_SLOTS

st.set_page_config(page_title="Trade Recommendations", page_icon="💡", layout="wide")
st.title("💡 Trade Recommendations")
st.caption("Finds realistic trade targets based on your roster needs and other teams' depth.")

platform = st.session_state.get("platform", "Sleeper")
dynasty = st.session_state.get("dynasty", False)


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Loading league rosters...")
def load_all_rosters_sleeper(league_id: str, dynasty: bool) -> dict:
    from api.sleeper import build_roster_map, get_all_players
    from api.ktc import get_dynasty_values, get_redraft_values

    roster_map = build_roster_map(league_id)
    all_players = get_all_players()
    value_data = get_dynasty_values() if dynasty else get_redraft_values()
    value_map = {p["name"].lower(): p["value"] for p in value_data}

    rosters = {}
    for info in roster_map.values():
        players = []
        for pid in (info.get("players") or []):
            p = all_players.get(pid, {})
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            pos = p.get("position", "")
            if not name or pos not in ("QB", "RB", "WR", "TE"):
                continue
            players.append({"name": name, "position": pos, "value": value_map.get(name.lower(), 0)})
        rosters[info["owner"]] = players
    return rosters


@st.cache_data(ttl=300, show_spinner="Loading league rosters...")
def load_all_rosters_espn(league_id: int, year: int, espn_s2: str, swid: str, dynasty: bool) -> dict:
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
            players.append({"name": p["name"], "position": p["position"],
                            "value": value_map.get(p["name"].lower(), 0)})
        rosters[team.team_name] = players
    return rosters


# ── Load rosters ──────────────────────────────────────────────────────────────
try:
    if platform == "Sleeper":
        league_id = st.session_state.get("sleeper_league_id", "")
        if not league_id:
            st.warning("Enter your Sleeper League ID in the sidebar.")
            st.stop()
        all_rosters = load_all_rosters_sleeper(league_id, dynasty)
    else:
        league_id = st.session_state.get("espn_league_id", "")
        if not league_id:
            st.warning("Enter your ESPN League ID in the sidebar.")
            st.stop()
        all_rosters = load_all_rosters_espn(
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

# ── Controls (always visible, auto-apply on change) ───────────────────────────
col_team, col_results, col_fair = st.columns([2, 1, 1])
with col_team:
    my_team = st.selectbox("Your team", sorted(all_rosters.keys()))
with col_results:
    max_results = st.slider("# of results", 3, 20, 10)
with col_fair:
    fairness = st.slider("Fairness window %", 10, 70, 30,
                         help="Max allowed value difference between players. Settings apply instantly.")

st.divider()

my_players = all_rosters.get(my_team, [])
if not my_players:
    st.warning("No players found for this team.")
    st.stop()

# ── Generate (always runs, auto-widens until results found) ───────────────────
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
    st.warning("Could not find any trades — this likely means player values failed to load. Check the Team Analysis page for errors.")
    st.stop()

# Show effective fairness window if it was auto-widened
actual_max_spread = max(1 - r["fairness_pct"] / 100 for r in recs)
if actual_max_spread > fairness / 100 + 0.01:
    st.info(f"Fairness window was automatically widened to {actual_max_spread*100:.0f}% to find results.")

st.success(f"**{len(recs)} trade opportunities** found for {my_team}")

# ── Recommendation cards ──────────────────────────────────────────────────────
for i, rec in enumerate(recs, 1):
    delta = rec["value_delta"]
    sign = "+" if delta >= 0 else ""
    delta_color = "green" if delta >= 0 else "orange"
    upgrade_badge = "⬆️ Upgrades starter" if rec["upgrades_starter"] else "📦 Adds depth"

    with st.container(border=True):
        top, bottom = st.columns([5, 1])
        with top:
            st.markdown(
                f"**#{i} &nbsp; Target: {rec['partner']}**  \n"
                f"Give &nbsp;**{rec['give']}** ({rec['give_position']}, {rec['give_value']:,}) "
                f"&nbsp;→&nbsp; "
                f"Get &nbsp;**{rec['receive']}** ({rec['receive_position']}, {rec['receive_value']:,})"
                f"&nbsp; &nbsp;{upgrade_badge}"
            )
            st.caption(rec["reason"])
        with bottom:
            st.metric("Delta", f"{sign}{delta:,}", delta=f"{sign}{delta:,}")
            st.caption(f"Fair: {rec['fairness_pct']}%")

# ── Summary table ─────────────────────────────────────────────────────────────
with st.expander("Full table"):
    df = pd.DataFrame(recs)[[
        "partner", "give", "give_value", "receive", "receive_value",
        "value_delta", "fairness_pct", "upgrades_starter", "my_need_filled"
    ]]
    df.columns = ["Partner", "You Give", "Give Val", "You Get", "Get Val",
                  "Delta", "Fairness %", "Upgrades Starter", "Position"]
    st.dataframe(df, use_container_width=True, hide_index=True)
