"""
config.py — loads env vars and sets project-wide defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# free model that handles tool-calling well enough for our use case
DEFAULT_MODEL = "mistralai/mistral-7b-instruct:free"

# ── Apify ─────────────────────────────────────────────────────────────────────
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# ── Reddit ────────────────────────────────────────────────────────────────────
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "cwt_marketing_agent/1.0")

# ── Target product ────────────────────────────────────────────────────────────
CWT_URL = "https://www.crowdwisdomtrading.com/"
CWT_NAME = "CrowdWisdomTrading"

# ── Paths ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ── Reddit subreddits to target ───────────────────────────────────────────────
REDDIT_SUBREDDITS = [
    "algotrading",
    "stocks",
    "investing",
    "wallstreetbets",
    "predictionmarkets",
    "options",
    "Daytrading",
]

# pain-point keywords we're looking for on Reddit
PAIN_KEYWORDS = [
    "prediction market",
    "crowd wisdom trading",
    "signal noise trading",
    "algo trading signal",
    "stock prediction tool",
    "trading community signal",
    "beat the market crowd",
    "retail trader edge",
]
