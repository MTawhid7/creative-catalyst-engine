# api/config.py

"""
Configuration constants for the API service layer.
"""

# --- L0 Cache Configuration ---
L0_CACHE_PREFIX = "l0_cache:intent"
L0_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours

# --- START: URL PATH REFACTOR ---
# The public-facing path where static result files are served.
# This MUST match the mount path in `api/main.py`.
RESULTS_MOUNT_PATH = "results"
# --- END: URL PATH REFACTOR ---
