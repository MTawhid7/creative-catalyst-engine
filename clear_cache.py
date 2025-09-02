# clear_cache.py

"""
A utility script to completely clear all caches for the
Creative Catalyst Engine.

This script permanently deletes both the ChromaDB vector index and the
cached artifact directory defined in the project settings.

It should be used when you want to force the engine to re-process all
information from scratch, for example, after making major changes to the
prompts, models, or the underlying data logic.
"""

import shutil
import sys
from pathlib import Path

# This allows the script to import from the 'catalyst' package
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

try:
    from catalyst import settings
except ImportError:
    print("❌ Error: Could not import project settings.")
    print(
        "⚠️ Please ensure you are running this script from the root of your project directory."
    )
    sys.exit(1)


def clear_all_caches():
    """
    Finds all cache directories from the project settings
    and safely deletes them after user confirmation.
    """
    # --- START OF FIX ---
    # Create a list of all cache directories to be cleared.
    cache_dirs_to_clear = [
        settings.CHROMA_PERSIST_DIR,
        settings.ARTIFACT_CACHE_DIR,
    ]
    # --- END OF FIX ---

    print("-" * 50)
    print("⚙️ Creative Catalyst Engine - Master Cache Clearing Utility")
    print("-" * 50)
    print(f"🗑️ This script will permanently delete the following directories:")
    for dir_path in cache_dirs_to_clear:
        print(f"  -> {dir_path}")
    print(
        "\n⚠️ This action cannot be undone and will erase all cached reports, images, and vector indexes."
    )

    # Check if any of the directories exist to avoid asking for confirmation unnecessarily.
    if not any(d.exists() for d in cache_dirs_to_clear):
        print("\n✅ All cache directories are already clear. Nothing to do.")
        return

    # Safety check: Ask for explicit user confirmation.
    try:
        confirm = input("\n⚖️ Are you sure you want to proceed? [y/N]: ")
    except KeyboardInterrupt:
        print("\n🚫 Operation cancelled by user.")
        return

    if confirm.lower() != "y":
        print("🚫 Operation cancelled.")
        return

    # --- START OF FIX ---
    # Loop through the list and delete each directory.
    for cache_dir in cache_dirs_to_clear:
        try:
            if cache_dir.exists():
                print(f"\n🗑️ Deleting cache directory: {cache_dir}...")
                shutil.rmtree(cache_dir)
                print(f"✅ Successfully cleared {cache_dir.name}.")
            else:
                print(f"\nℹ️ Cache directory {cache_dir} does not exist. Skipping.")
        except Exception as e:
            print(f"\n❌ An error occurred while clearing {cache_dir.name}: {e}")
            print("⚠️ Please check file permissions and try again.")
    # --- END OF FIX ---

    print(
        "\n\n✅ All caches cleared successfully. Future runs will perform full synthesis."
    )


if __name__ == "__main__":
    clear_all_caches()
