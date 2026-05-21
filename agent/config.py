import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the deep research agent
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(dotenv_path=BASE_DIR / ".env")

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Model Configuration
# We default to gemini-1.5-flash for speed, reasoning ability, and massive context budget
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")

# Search & Fetch Defaults
MAX_SEARCH_RESULTS = 5
FETCH_TIMEOUT = 8  # seconds

# Token / Context Window Management
# Standard Gemini context window is huge, but to save token overhead, latency, and cost on free-tier, 
# we set a local context window threshold. If session context exceeds this, we trigger rolling summary compressions.
MAX_CONTEXT_CHAR_LIMIT = 45000  # ~12,000 to 15,000 tokens
MAX_SNIPPET_SIZE = 1200          # Maximum characters per chunk/snippet

# DB path
DB_PATH = BASE_DIR / "research_sessions.db"

def is_mock_mode():
    """Determines if keys are missing, triggering a fully interactive mock mode."""
    return not (GEMINI_API_KEY and TAVILY_API_KEY)

def print_status():
    """Prints configuration load status for debugging."""
    print("=== Configuration Status ===")
    print(f"Gemini Key Present: {bool(GEMINI_API_KEY)}")
    print(f"Tavily Key Present: {bool(TAVILY_API_KEY)}")
    print(f"Selected Model: {LLM_MODEL}")
    print(f"Mock Mode Active: {is_mock_mode()}")
    print("============================")
