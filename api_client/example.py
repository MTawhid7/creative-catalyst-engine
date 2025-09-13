# api_client/example.py

import requests
from pathlib import Path
from .client import CreativeCatalystClient
from .exceptions import APIClientError

# ===================================================================
#  --- TEST CONFIGURATION ---
# ===================================================================
# This is the primary variable you should change to test new prompts.
# The client will send this text to the API.

USER_PASSAGE = """
A collection of rugged, functional workwear for Martian colonists in the year 2085, inspired by vintage Carhartt and Soviet-era space suits.
"""

# ===================================================================


def download_images(image_urls: list[str], download_dir: Path):
    """
    Downloads images from a list of URLs into a specified directory.
    """
    if not image_urls:
        print("--- No image URLs provided to download. ---")
        return

    print(f"\n--- 📥 Starting Image Download to '{download_dir}' ---")
    download_dir.mkdir(exist_ok=True)

    for url in image_urls:
        try:
            filename = url.split("/")[-1]
            save_path = download_dir / filename
            print(f"Downloading {filename}...")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            print(f"✅ Successfully saved to {save_path}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to download {url}. Error: {e}")
        except Exception as e:
            print(
                f"❌ An unexpected error occurred while downloading {url}. Error: {e}"
            )


def main():
    """
    A demonstration of how to use the CreativeCatalystClient to get a report
    and download the associated images.
    """
    # --- START: ROBUST CLIENT INITIALIZATION ---
    # The client now automatically reads the API URL from the environment
    # variable defined in your .env file, falling back to localhost if not set.
    # This makes the client configurable without code changes.
    client = CreativeCatalystClient()
    # --- END: ROBUST CLIENT INITIALIZATION ---

    print("--- Starting Creative Catalyst API Client Demo ---")
    print(f"--- Target API Server: {client.base_url} ---")

    try:
        # We now use the USER_PASSAGE variable defined at the top of the file.
        response_data = client.get_creative_report(USER_PASSAGE)

        print("\n--- ✅ Final Report Received ---")

        final_report = response_data.get("final_report", {})
        if not final_report:
            print("Report content is empty. Cannot proceed.")
            return

        print(f"Theme: {final_report.get('overarching_theme')}")
        print(f"Server Artifacts Path: {response_data.get('artifacts_path')}")

        all_image_urls = []
        key_pieces = final_report.get("detailed_key_pieces", [])
        print(f"Found {len(key_pieces)} key pieces in the report.")

        for piece in key_pieces:
            garment_url = piece.get("final_garment_image_url")
            moodboard_url = piece.get("mood_board_image_url")
            if garment_url:
                all_image_urls.append(garment_url)
            if moodboard_url:
                all_image_urls.append(moodboard_url)

        download_images(all_image_urls, download_dir=Path("downloaded_images"))

    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred ---")
        print(f"Error: {e}")
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred ---")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
