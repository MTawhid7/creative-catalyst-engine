"""
A utility script to completely clear the ChromaDB cache for the
Creative Catalyst Engine.

This script permanently deletes the cache directory defined in the project settings.
It should be used when you want to force the engine to re-process all
information from scratch, for example, after making major changes to the
prompts or the underlying data models.
"""

import shutil
import sys
from pathlib import Path

# This allows the script to import from the 'catalyst' package
# by adding the project's root directory to the Python path.
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

try:
    from catalyst import settings
except ImportError:
    print("Error: Could not import project settings.")
    print(
        "Please ensure you are running this script from the root of your 'CreativeCatalystEngine' project directory."
    )
    sys.exit(1)


def clear_chroma_cache():
    """
    Finds the ChromaDB persistence directory from the project settings
    and safely deletes it after user confirmation.
    """
    cache_dir = settings.CHROMA_PERSIST_DIR
    print("-" * 50)
    print("Creative Catalyst Engine - Cache Clearing Utility")
    print("-" * 50)
    print(f"This script will permanently delete the following directory:")
    print(f"  -> {cache_dir}")
    print(
        "\nThis action cannot be undone and will erase all cached reports, sources, and concepts."
    )

    if not cache_dir.exists():
        print("\nCache directory does not exist. Nothing to clear.")
        return

    # Safety check: Ask for explicit user confirmation.
    try:
        confirm = input("\nAre you sure you want to proceed? [y/N]: ")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    if confirm.lower() != "y":
        print("Operation cancelled.")
        return

    try:
        print(f"\nDeleting cache directory: {cache_dir}...")
        shutil.rmtree(cache_dir)
        print("✅ Cache cleared successfully.")
    except Exception as e:
        print(f"\n❌ An error occurred while clearing the cache: {e}")
        print("Please check file permissions and try again.")


if __name__ == "__main__":
    clear_chroma_cache()
