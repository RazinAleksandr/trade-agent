import os
from dotenv import load_dotenv

load_dotenv()


# Wallet & Auth
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Polymarket endpoints
POLYMARKET_HOST = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))

# Trading mode
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# Risk parameters
MAX_POSITION_SIZE_USDC = float(os.getenv("MAX_POSITION_SIZE_USDC", "50"))
MAX_TOTAL_EXPOSURE_USDC = float(os.getenv("MAX_TOTAL_EXPOSURE_USDC", "200"))
MIN_EDGE_THRESHOLD = float(os.getenv("MIN_EDGE_THRESHOLD", "0.10"))
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.25"))

# Market discovery filters
MIN_VOLUME_24H = float(os.getenv("MIN_VOLUME_24H", "1000"))
MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "500"))
MAX_MARKETS_PER_CYCLE = int(os.getenv("MAX_MARKETS_PER_CYCLE", "10"))

# Loop timing (seconds)
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "300"))  # 5 minutes
ORDER_CHECK_INTERVAL = int(os.getenv("ORDER_CHECK_INTERVAL", "60"))

# Database
DB_PATH = os.getenv("DB_PATH", "trading.db")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "trading.log")

# OpenAI model for analysis
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Web search for market analysis
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
