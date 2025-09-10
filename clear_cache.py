# clear_cache.py

"""
A utility script to completely clear ALL caches and user-facing results for the
Creative Catalyst Engine, including the L0 Redis cache.
"""

import shutil
import sys
import os
import redis
from pathlib import Path
from dotenv import load_dotenv

# This allows the script to import from the 'catalyst' package
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Load environment variables to find the REDIS_URL
load_dotenv(project_root / ".env")
REDIS_URL = os.getenv("REDIS_URL")

try:
    from catalyst import settings
except ImportError:
    print("❌ Error: Could not import project settings.")
    print(
        "⚠️ Please ensure you are running this script from the root of your project directory."
    )
    sys.exit(1)


def clear_redis_cache():
    """Connects to Redis and flushes the current database."""
    print("\n" + "-" * 20)
    print("⚡ Clearing L0 Intent Cache (Redis)")
    print("-" * 20)

    if not REDIS_URL:
        print("⚠️ REDIS_URL not found in .env file. Cannot clear Redis cache.")
        return

    try:
        print(f"Connecting to Redis at {REDIS_URL}...")
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("Connection successful. Flushing database...")
        redis_client.flushdb()
        print("✅ Successfully flushed Redis database.")
    # --- START OF FIX: Correct the exception path ---
    except redis.ConnectionError as e:
        # --- END OF FIX ---
        print(f"❌ Error: Could not connect to Redis. Is the Docker container running?")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while clearing Redis: {e}")


def clear_file_caches():
    """Finds all file-based cache and results directories and deletes them."""
    print("\n" + "-" * 20)
    print("🗑️ Clearing File Caches & Results")
    print("-" * 20)

    dirs_to_clear = [
        settings.CHROMA_PERSIST_DIR,
        settings.ARTIFACT_CACHE_DIR,
        settings.RESULTS_DIR,
    ]

    print("This will permanently delete the following directories:")
    for dir_path in dirs_to_clear:
        print(f"  -> {dir_path}")

    if not any(d.exists() for d in dirs_to_clear):
        print(
            "\n✅ All file-based caches and results are already clear. Nothing to do."
        )
        return

    for cache_dir in dirs_to_clear:
        try:
            if cache_dir.exists():
                print(f"Deleting directory: {cache_dir.name}...")
                shutil.rmtree(cache_dir)
                print(f"✅ Cleared {cache_dir.name}.")
            else:
                print(f"ℹ️ Directory {cache_dir.name} does not exist. Skipping.")
        except Exception as e:
            print(f"❌ An error occurred while clearing {cache_dir.name}: {e}")

    print("\n⚙️ Re-creating essential empty directories...")
    settings.RESULTS_DIR.mkdir(exist_ok=True)
    settings.ARTIFACT_CACHE_DIR.mkdir(exist_ok=True)
    settings.CHROMA_PERSIST_DIR.mkdir(exist_ok=True)
    print("✅ File cache clearing complete.")


if __name__ == "__main__":
    print("=" * 50)
    print("⚙️ Creative Catalyst Engine - MASTER CLEARING UTILITY")
    print("=" * 50)
    print(
        "\n⚠️ This action cannot be undone and will erase all file caches, results, AND the Redis L0 cache."
    )

    try:
        confirm = input("\n⚖️ Are you sure you want to proceed? [y/N]: ")
    except KeyboardInterrupt:
        print("\n🚫 Operation cancelled by user.")
        sys.exit(0)

    if confirm.lower() != "y":
        print("🚫 Operation cancelled.")
        sys.exit(0)

    clear_file_caches()
    clear_redis_cache()

    print("\n\n✅ ALL CACHES CLEARED. The next run will be completely fresh.")
