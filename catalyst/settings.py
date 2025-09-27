# catalyst/settings.py

"""
The Settings Module: The Central Configuration for the Creative Catalyst Engine.

This module is the single source of truth for all application settings. It handles:
1.  Loading secrets and API keys from the .env file.
2.  Defining core application constants (file paths, model names, etc.).

It is designed to fail fast with clear errors if critical configurations are missing.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --- 1. Path Configuration ---
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_cache"
ARTIFACT_CACHE_DIR = BASE_DIR / "artifact_cache"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# --- 2. API Keys & Secrets ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is not set in the .env file.")

DALLE_API_KEY = os.getenv("DALLE_API_KEY")
if not DALLE_API_KEY:
    raise ValueError("CRITICAL ERROR: DALLE_API_KEY is not set in the .env file.")

# --- 3. LLM Configuration ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"
GEMINI_PRO_MODEL_NAME = "gemini-2.5-pro"
GEMINI_DEFAULT_TIMEOUT_SECONDS = 60


# --- 4. Unified Resilience & Retry Configuration ---
# --- START: THE DEFINITIVE REFACTOR ---
# The number of times to retry a low-level, transient network or server error.
RETRY_NETWORK_ATTEMPTS = 5

# The number of times to retry a high-level, expensive AI content generation
# that fails validation or returns an empty response.
RETRY_AI_CONTENT_ATTEMPTS = 3

# The base delay (in seconds) for the exponential backoff calculation.
RETRY_BACKOFF_DELAY_SECONDS = 5
# --- END: THE DEFINITIVE REFACTOR ---


# --- 5. Caching Configuration ---
EMBEDDING_MODEL_NAME = "embedding-001"
CHROMA_COLLECTION_NAME = "creative_catalyst_reports"
CACHE_DISTANCE_THRESHOLD = 0.10
CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "localhost")
CHROMA_SERVER_PORT = int(os.getenv("CHROMA_SERVER_PORT", "8000"))


# --- 6. File & Logging Configuration ---
LOG_FILE_PATH = LOGS_DIR / "catalyst_engine.log"
TREND_REPORT_FILENAME = "itemized_fashion_trends.json"
PROMPTS_FILENAME = "generated_prompts.json"


# --- 7. Results Management ---
KEEP_N_RESULTS = 3


# --- 8. Feature Flags ---
ENABLE_IMAGE_GENERATION = os.getenv("ENABLE_IMAGE_GENERATION", "True").lower() == "true"
IMAGE_GENERATION_MODEL = os.getenv("IMAGE_GENERATION_MODEL", "nano-banana")
