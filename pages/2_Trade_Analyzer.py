import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.trade import evaluate_trade

st.set_page_config(page_title="Trade Analyzer", page_icon="🔄", layout="wide")
st.title("🔄 Trade Analyzer")

dynasty = st.session_state.get("dynasty", False)
st.caption(f"Using {'dynasty' if dynasty else 'redraft'} KTC values. Change league type in the sidebar.")

# ── Load player list from KTC ─────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Loading player values...")
def load_players(dynasty: bool) -> list[dict]:
    from api.ktc import get_dynasty_values, get_redraft_values
    return get_dynasty_values() if dynasty else get_redraft_values()

try:
    all_players = load_players(dynasty)
except RuntimeError as e:
    st.error(f"Could not load KTC player values: {e}")
    st.stop()

if not all_players:
    st.error("No player data returned from KTC. The service may be temporarily unavailable.")
    st.stop()

# Format options for display: "Patrick Mahomes (QB - 8500)"
player_options = [
    f"{p['name']} ({p['position']} - {p['value']:,})"
    for p in sorted(all_players, key=lambda x: x["value"], reverse=True)
]
# Map display string back to name
option_to_name = {opt: opt.split(" (")[0] for opt in player_options}

# ── Trade input (multiselect has built-in search — type to filter) ────────────
st.info("Type a player name in either box below to search. Select all players involved in the trade, then click Evaluate.")

col_give, col_recv = st.columns(2)

with col_give:
    st.subheader("You Give")
    giving_opts = st.multiselect(
        "Search and select players to trade away",
        options=player_options,
        key="giving_players",
        placeholder="Type a name to search...",
    )

with col_recv:
    st.subheader("You Receive")
    receiving_opts = st.multiselect(
        "Search and select players to receive",
        options=player_options,
        key="receiving_players",
        placeholder="Type a name to search...",
    )

giving = [option_to_name[o] for o in giving_opts]
receiving = [option_to_name[o] for o in receiving_opts]

st.divider()

if not giving and not receiving:
    st.info("Use the boxes above to build your trade proposal, then click Evaluate Trade.")

if st.button(
    "Evaluate Trade",
    type="primary",
    disabled=not (giving and receiving),
    help="Select at least one player on each side to evaluate.",
):
    result = evaluate_trade(giving, receiving, dynasty=dynasty)

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict_color = {
        "Strong Win": "green",
        "Win": "green",
        "Fair": "blue",
        "Loss": "red",
        "Strong Loss": "red",
    }
    color = verdict_color.get(result["verdict"], "gray")
    st.markdown(f"## Verdict: :{color}[{result['verdict']}]")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("You Give", f"{result['give_total']:,}")
    m2.metric("You Receive", f"{result['receive_total']:,}")
    delta_val = result["delta"]
    sign = "+" if delta_val >= 0 else ""
    m3.metric("Value Delta", f"{sign}{delta_val:,}", delta=str(delta_val))
    m4.metric("Fairness", f"{result['fairness_pct']}%")

    # ── Player breakdown ──────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Trading Away")
        for p in result["giving"]:
            st.markdown(f"- **{p['name']}** — {p['value']:,}")
    with col_r:
        st.subheader("Receiving")
        for p in result["receiving"]:
            st.markdown(f"- **{p['name']}** — {p['value']:,}")

    # ── Bar chart ─────────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="You Give",
        x=[p["name"] for p in result["giving"]],
        y=[p["value"] for p in result["giving"]],
        marker_color="tomato",
    ))
    fig.add_trace(go.Bar(
        name="You Receive",
        x=[p["name"] for p in result["receiving"]],
        y=[p["value"] for p in result["receiving"]],
        marker_color="mediumseagreen",
    ))
    fig.update_layout(barmode="group", yaxis_title="KTC Value", height=350)
    st.plotly_chart(fig, use_container_width=True)
