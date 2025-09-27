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
I need a detailed report on the bespoke jacket tailoring process at a premier Savile Row atelier, highlighting the nuances of artisanal craftsmanship.
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
    client = CreativeCatalystClient()
    print("--- Starting Creative Catalyst API Client Demo ---")
    print(f"--- Target API Server: {client.base_url} ---")
    final_report = None
    all_image_urls = []

    try:
        # Iterate over the new generator-based stream method.
        for update in client.get_creative_report_stream(USER_PASSAGE):
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

        print(f"Theme: {final_report.get('final_report', {}).get('overarching_theme')}")
        print(f"Server Artifacts Path: {final_report.get('artifacts_path')}")

        key_pieces = final_report.get("final_report", {}).get("detailed_key_pieces", [])
        for piece in key_pieces:
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
