import os
from dotenv import load_dotenv

load_dotenv()

ESPN_S2 = os.getenv("ESPN_S2")
ESPN_SWID = os.getenv("ESPN_SWID")
ESPN_LEAGUE_ID = int(os.getenv("ESPN_LEAGUE_ID", 0))
ESPN_YEAR = int(os.getenv("ESPN_YEAR", 2025))
SLEEPER_LEAGUE_ID = os.getenv("SLEEPER_LEAGUE_ID")

POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "DEF", "FLEX"]

# Positions counted as "starters" for strength scoring
STARTER_SLOTS = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "K": 1,
    "DEF": 1,
}
