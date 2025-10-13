# api_client/example.py

import requests
from pathlib import Path
from .client import CreativeCatalystClient
from .exceptions import APIClientError

# ===================================================================
#  --- TEST CONFIGURATION ---
# ===================================================================
# This script can now test all generation strategies and variations.
#    CHOOSE YOUR SEED: Set the variation_seed to get different creative results.
#    - Seed 0 is the default, canonical collection.
#    - Seeds 1, 2, 3... will generate creative alternatives.


PROMPT = """
Which graphic T-shirts are trending this summer among Gen Z?
"""


# --- VARIATION SEED ---
VARIATION_SEED = 1  # Change this to 1, 2, etc., to get new creative variations

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
    and download the associated images, now with support for variation seeds.
    """
    client = CreativeCatalystClient()
    print("--- 🚀 Starting Creative Catalyst API Client Demo ---")
    print(f"--- 🎯 Target API Server: {client.base_url} ---")
    final_report = None
    all_image_urls = []

    try:
        # --- UPDATED: The client now sends the prompt AND the variation seed ---
        print("\n--- 📤 Submitting Job ---")
        stream = client.get_creative_report_stream(
            PROMPT, variation_seed=VARIATION_SEED
        )

        for update in stream:
            event_type = update.get("event")
            if event_type == "job_submitted":
                print(f"Job submitted with ID: {update.get('job_id')}")
            elif event_type == "progress":
                print(f"Progress: {update.get('status')}")
            elif event_type == "complete":
                final_report = update.get("result")
                print("\n--- ✅ Final Report Received ---")
                break

        if not final_report:
            print("Stream finished without a final report.")
            return

        report_content = final_report.get("final_report", {})
        strategy = report_content.get("enriched_brief", {}).get("generation_strategy")

        print("\n--- 📊 Job Summary ---")
        print(f"Theme: {report_content.get('overarching_theme')}")
        print(f"Generation Strategy Used: {strategy}")
        print(f"Server Artifacts Path: {final_report.get('artifacts_path')}")

        key_pieces = report_content.get("detailed_key_pieces", [])
        print(f"Generated {len(key_pieces)} key piece(s):")
        for i, piece in enumerate(key_pieces):
            piece_name = piece.get("key_piece_name", f"Untitled Piece {i+1}")
            print(f"  - {piece_name}")
            if piece.get("final_garment_image_url"):
                all_image_urls.append(piece["final_garment_image_url"])
            if piece.get("mood_board_image_url"):
                all_image_urls.append(piece["mood_board_image_url"])

        download_images(all_image_urls, download_dir=Path("downloaded_images"))

    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred ---")
        print(f"Error: {e}")
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred ---")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
