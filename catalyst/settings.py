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
# Load environment variables from a .env file at the project root.
load_dotenv()

# Define the absolute base directory of the project.
BASE_DIR = Path(__file__).resolve().parent.parent

# Define key sub-directories
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_cache"
# A new, permanent directory for storing cached artifacts that will not be cleaned up.
ARTIFACT_CACHE_DIR = BASE_DIR / "artifact_cache"

# Ensure that the directories for logs, results, and the cache exist.
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# --- 2. API Keys & Secrets ---
# Load from environment and fail fast if a critical key is missing.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is not set in the .env file.")

DALLE_API_KEY = os.getenv("DALLE_API_KEY")
if not DALLE_API_KEY:
    raise ValueError("CRITICAL ERROR: DALLE_API_KEY is not set in the .env file.")

# --- 3. LLM Configuration ---
# Tunable parameters for the AI.
GEMINI_MODEL_NAME = "gemini-2.5-flash"
GEMINI_MAX_RETRIES = 3
GEMINI_DEFAULT_TIMEOUT_SECONDS = 60


# --- 4. Caching Configuration ---
EMBEDDING_MODEL_NAME = "embedding-001"
CHROMA_COLLECTION_NAME = "creative_catalyst_reports"
CACHE_DISTANCE_THRESHOLD = 0.10

# Load the ChromaDB server configuration from environment variables.
# The port MUST be cast to an integer here to ensure it is correctly typed
# for the entire application. This is the single source of truth.
CHROMA_SERVER_HOST = os.getenv("CHROMA_SERVER_HOST", "localhost")
CHROMA_SERVER_PORT = int(os.getenv("CHROMA_SERVER_PORT", "8000"))


# --- 5. File & Logging Configuration ---
LOG_FILE_PATH = LOGS_DIR / "catalyst_engine.log"
TREND_REPORT_FILENAME = "itemized_fashion_trends.json"
PROMPTS_FILENAME = "generated_prompts.json"


# --- 6. Results Management ---
KEEP_N_RESULTS = 3  # Keep the 3 most recent result folders

# --- 7. Feature Flags ---
# A master switch to enable or disable costly features like image generation.
# Reads from the .env file, defaulting to True if not specified.
ENABLE_IMAGE_GENERATION = os.getenv("ENABLE_IMAGE_GENERATION", "True").lower() == "true"
IMAGE_GENERATION_MODEL = os.getenv("IMAGE_GENERATION_MODEL", "nano-banana")
