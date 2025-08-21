"""
The Settings Module: The Central Configuration for the Creative Catalyst Engine.

This module is the single source of truth for all application settings. It handles:
1.  Loading secrets and API keys from the .env file.
2.  Defining core application constants (file paths, model names, etc.).
3.  Loading external data configurations (like sources.yaml).

It is designed to fail fast with clear errors if critical configurations are missing.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# --- 1. Path Configuration ---
# Load environment variables from a .env file at the project root.
load_dotenv()

# Define the absolute base directory of the project (CreativeCatalystEngine/)
# This makes all path definitions robust and independent of the current working directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# Define key sub-directories
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_cache"
CONFIG_DIR = BASE_DIR / "catalyst" / "config"  # Path to the new config/ folder

# Ensure that the directories for logs, results, and the cache exist.
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)


# --- 2. API Keys & Secrets ---
# Load from environment and fail fast if a critical key is missing.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is not set in the .env file.")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("CRITICAL ERROR: GOOGLE_API_KEY is not set in the .env file.")

SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
if not SEARCH_ENGINE_ID:
    raise ValueError("CRITICAL ERROR: SEARCH_ENGINE_ID is not set in the .env file.")

# --- 3. LLM & Search Configuration ---
# Tunable parameters for the AI and research engine.
GEMINI_MODEL_NAME = "gemini-2.5-flash"
SEARCH_NUM_RESULTS = 2
# Add a new setting to control the maximum number of search queries per run.
MAX_QUERIES = 10

# --- 4. Embedding & Caching Configuration ---
# --- START OF CORRECTION ---
# Corrected the model name to the official API identifier for the embedding model.
EMBEDDING_MODEL_NAME = "embedding-001"
# --- END OF CORRECTION ---
CHROMA_COLLECTION_NAME = "creative_catalyst_reports"
CACHE_DISTANCE_THRESHOLD = 0.25

# --- 5. Concurrency & Performance Configuration ---
GEMINI_API_CONCURRENCY_LIMIT = 10

# --- 6. File & Logging Configuration ---
LOG_FILE_PATH = LOGS_DIR / "catalyst_engine.log"
TREND_REPORT_FILENAME = "itemized_fashion_trends.json"
PROMPTS_FILENAME = "generated_prompts.json"


# --- 7. External Data Configuration (sources.yaml) ---
def _load_sources_config() -> dict:
    """A resilient function to load the sources.yaml configuration file."""
    config_path = CONFIG_DIR / "sources.yaml"
    logger.info(f"Loading sources configuration from: {config_path}")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.warning(f"Could not load sources.yaml: {e}. Using minimal defaults.")
        return {
            "global_authorities": ["Vogue", "WWD"],
            "regional_authorities": {},
            "fashion_weeks": ["Paris Fashion Week"],
            "visual_platforms": ["Pinterest Trends"],
            "cultural_concepts": ["contemporary art movements"],
        }


# We need to import the logger at the end to avoid a circular dependency,
# as the logger itself needs to import settings.LOG_FILE_PATH.
from .utilities.logger import get_logger

# Now, create the logger instance.
logger = get_logger(__name__)

# With the logger now defined, we can safely call the function that uses it.
# This constant is now available to any module that imports 'settings'.
SOURCES_CONFIG = _load_sources_config()
