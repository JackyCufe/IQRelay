"""
config.py — Centralized configuration management
Supports .env file + environment variable overrides.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Azure AI Search (Foundry IQ) ──────────────────────
AI_SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT", "")
AI_SEARCH_KEY = os.getenv("AI_SEARCH_KEY", "")
AI_SEARCH_INDEX = os.getenv("AI_SEARCH_INDEX", "foundry-iq-index")

# ─── DeepSeek API (OpenAI compatible) ────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ─── Teams Bot ─────────────────────────────────────────
TEAMS_APP_ID = os.getenv("TEAMS_APP_ID", "")
TEAMS_APP_PASSWORD = os.getenv("TEAMS_APP_PASSWORD", "")
TEAMS_APP_TENANT_ID = os.getenv("TEAMS_APP_TENANT_ID", "")

# ─── Azure Storage ─────────────────────────────────────
STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING", "")
STORAGE_CONTAINER = os.getenv("STORAGE_CONTAINER", "pipeline-archive")

# ─── Pipeline Settings ─────────────────────────────────
MAX_GATEKEEPING_ROUNDS = int(os.getenv("MAX_GATEKEEPING_ROUNDS", "3"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
PIPELINE_CONFIG_PATH = os.getenv(
    "PIPELINE_CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "pipeline_config.yaml"),
)


def validate() -> list[str]:
    """Check required configuration, returns list of missing items."""
    missing = []
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if not AI_SEARCH_ENDPOINT:
        missing.append("AI_SEARCH_ENDPOINT")
    if not AI_SEARCH_KEY:
        missing.append("AI_SEARCH_KEY")
    return missing
