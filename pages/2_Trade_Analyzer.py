import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from analysis.trade import evaluate_trade, search_players

st.set_page_config(page_title="Trade Analyzer", page_icon="🔄", layout="wide")
st.title("🔄 Trade Analyzer")

dynasty = st.session_state.get("dynasty", False)
st.caption(f"Using {'dynasty' if dynasty else 'redraft'} KTC values. Change in the sidebar.")

# ── Player search helper ──────────────────────────────────────────────────────
def player_search_box(label: str, key: str) -> list[str]:
    query = st.text_input(label, key=f"query_{key}")
    if query and len(query) >= 2:
        results = search_players(query, dynasty=dynasty, limit=8)
        if results:
            options = [f"{p['name']} ({p['position']}, {p['value']} pts)" for p in results]
            selected = st.multiselect("Select players", options, key=f"select_{key}")
            return [opt.split(" (")[0] for opt in selected]
    return []


col_give, col_recv = st.columns(2)

with col_give:
    st.subheader("You Give")
    giving = player_search_box("Search players to trade away", "give")

with col_recv:
    st.subheader("You Receive")
    receiving = player_search_box("Search players to receive", "recv")

st.divider()

if st.button("Evaluate Trade", type="primary", disabled=not (giving and receiving)):
    result = evaluate_trade(giving, receiving, dynasty=dynasty)

    # ── Summary metrics ───────────────────────────────────────────────────────
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
    m1.metric("You Give (total)", f"{result['give_total']:,}")
    m2.metric("You Receive (total)", f"{result['receive_total']:,}")
    delta_val = result["delta"]
    m3.metric("Delta", f"{'+' if delta_val >= 0 else ''}{delta_val:,}", delta=str(delta_val))
    m4.metric("Fairness", f"{result['fairness_pct']}%")

    # ── Player breakdown ──────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Trading Away")
        for p in result["giving"]:
            st.markdown(f"- **{p['name']}** — {p['value']:,} pts")

    with col_r:
        st.subheader("Receiving")
        for p in result["receiving"]:
            st.markdown(f"- **{p['name']}** — {p['value']:,} pts")

    # ── Bar chart comparison ──────────────────────────────────────────────────
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

elif not (giving or receiving):
    st.info("Search for players above to build your trade proposal.")
