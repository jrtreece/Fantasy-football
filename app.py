import streamlit as st

st.set_page_config(
    page_title="Fantasy Football Edge",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Fantasy Football Edge")
st.markdown(
    """
    Welcome to your personal fantasy football dashboard. Use the sidebar to navigate between tools.

    | Page | What it does |
    |---|---|
    | **Team Analysis** | Positional grades, strengths & weaknesses |
    | **Trade Analyzer** | Evaluate trade proposals using KTC values |
    | **Waiver Wire** | Top available players ranked by need |
    | **Start / Sit** | Weekly lineup optimizer |

    ---
    ### Setup
    Before using, copy `.env.example` to `.env` and fill in your league credentials.
    """
)

with st.sidebar:
    st.header("⚙️ League Settings")

    platform = st.selectbox("Platform", ["Sleeper", "ESPN"])
    st.session_state["platform"] = platform

    if platform == "Sleeper":
        league_id = st.text_input("Sleeper League ID", value="")
        st.session_state["sleeper_league_id"] = league_id
        st.caption("Find this in your Sleeper league URL.")
    else:
        league_id = st.text_input("ESPN League ID", value="")
        espn_s2 = st.text_input("ESPN S2 Cookie", type="password")
        swid = st.text_input("ESPN SWID Cookie", type="password")
        year = st.number_input("Season Year", value=2025, step=1)
        st.session_state["espn_league_id"] = league_id
        st.session_state["espn_s2"] = espn_s2
        st.session_state["espn_swid"] = swid
        st.session_state["espn_year"] = int(year)
        st.caption("Get S2 and SWID from your browser cookies on espn.com.")

    league_type = st.radio("League Type", ["Redraft", "Dynasty"])
    st.session_state["dynasty"] = league_type == "Dynasty"
