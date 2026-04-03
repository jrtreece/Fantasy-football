import streamlit as st
import subprocess


def get_build_version() -> str:
    try:
        commit_hash = subprocess.check_output(
            ["git", "log", "-1", "--format=%h"], text=True
        ).strip()
        commit_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M UTC"],
            text=True,
        ).strip()
        return f"v{commit_date} ({commit_hash})"
    except Exception:
        return "version unknown"


st.set_page_config(
    page_title="Fantasy Football Edge",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Fantasy Football Edge")
st.markdown(
    """
    Welcome to your personal fantasy football dashboard. Use the sidebar to select a league and navigate between tools.

    | Page | What it does |
    |---|---|
    | **Team Analysis** | Positional grades, strengths & weaknesses |
    | **Trade Analyzer** | Evaluate trade proposals using KTC values |
    | **Waiver Wire** | Top available players ranked by need |
    | **Start / Sit** | Weekly lineup optimizer |
    """
)

# ── Load configured leagues from secrets ──────────────────────────────────────
def _load_configured_leagues() -> dict:
    """Read leagues from st.secrets if available."""
    try:
        return dict(st.secrets.get("leagues", {}))
    except Exception:
        return {}


configured_leagues = _load_configured_leagues()

with st.sidebar:
    st.header("⚙️ League Settings")

    if configured_leagues:
        # ── Dropdown mode: leagues pre-configured in secrets ──────────────────
        league_names = {key: cfg["name"] for key, cfg in configured_leagues.items()}
        selected_key = st.selectbox(
            "Select league",
            options=list(league_names.keys()),
            format_func=lambda k: league_names[k],
        )
        cfg = configured_leagues[selected_key]

        platform = cfg["platform"]
        league_type = cfg.get("type", "redraft").capitalize()

        st.caption(f"Platform: **{platform}** | Type: **{league_type}**")

        # Push config into session state
        st.session_state["platform"] = platform
        st.session_state["dynasty"] = league_type.lower() == "dynasty"

        if platform == "Sleeper":
            st.session_state["sleeper_league_id"] = str(cfg["league_id"])
        else:
            st.session_state["espn_league_id"] = str(cfg["league_id"])
            st.session_state["espn_s2"] = cfg.get("espn_s2", "")
            st.session_state["espn_swid"] = cfg.get("swid", "")
            st.session_state["espn_year"] = int(cfg.get("year", 2025))

        st.divider()
        with st.expander("Add more leagues"):
            st.markdown(
                "Edit `.streamlit/secrets.toml` (local) or **App Settings → Secrets** "
                "(Streamlit Cloud) to add more leagues. See `secrets.toml.example` for the format."
            )

    else:
        # ── Manual mode: no secrets configured yet ────────────────────────────
        st.info("No leagues configured. Enter credentials below, or add them to `.streamlit/secrets.toml` to skip this step.")

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

    st.divider()
    st.caption(get_build_version())
