"""Project settings. Secrets are read from the .env file (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- market data ---------------------------------------------------------
TOKENS = ["NEAR-USDT", "IMX-USDT", "LDO-USDT"]

CANDLES = {
    "interval": "15m",
    "timezone": 8,
    "limit": "100",
}
POLL_INTERVAL_SEC = 60 * 60  # how often all tokens are re-checked

# --- strategy ------------------------------------------------------------
ATR_PERIOD = 14
ZIGZAG_ATR_MULTIPLIER = 0.04
SL_ATR_BUFFER = 0.25

# --- paper trading -------------------------------------------------------
PAPER_MAX_POSITIONS = 100
PAPER_MAX_SIGNAL_AGE = 4  # candles
PAPER_FEE_PCT = 0.05

# --- live orders (BingX) -------------------------------------------------
BINGX_API_URL = "https://open-api.bingx.com"
BINGX_API_KEY = os.getenv("BING_SWING_API", "")
BINGX_SECRET_KEY = os.getenv("BING_SWING_SECRET", "")
POSITION_BASE_USDT = 20
POSITION_REFERENCE_ATR_PCT = 2
POSITION_MIN_USDT = 5
POSITION_MAX_USDT = 50

# --- database ------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "swing_trade_edition_2"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# --- telegram ------------------------------------------------------------
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_REPORT_INTERVAL_SEC = 15 * 60

# --- google drive --------------------------------------------------------
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_DIR = ROOT_DIR / "credentials"
GOOGLE_CLIENT_SECRET_FILE = Path(
    os.getenv("GOOGLE_CLIENT_SECRET_FILE", CREDENTIALS_DIR / "client_secret.json")
)
GOOGLE_TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", CREDENTIALS_DIR / "token.json"))
DRIVE_REPORT_INTERVAL_SEC = 15 * 60

# --- generated files -----------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))
GRAPHS_DIR = DATA_DIR / "graphs"
SWINGS_DIR = DATA_DIR / "swings_dfs"
CANDLES_DIR = DATA_DIR / "candles_dfs"
PAPER_STATE_FILE = DATA_DIR / "paper_state.json"
STRUCTURES_FILE = DATA_DIR / "history_of_structures.csv"
GRAPHS_KEEP_DAYS = 2
