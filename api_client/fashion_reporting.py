# your_company/services/fashion_reporting.py

"""
Service Module for Interacting with the Creative Catalyst Engine.

This file acts as an 'Adapter' or 'Bridge' to the external Creative Catalyst API.
Its purpose is to provide a simple, clean interface for the rest of the main
application to use, without needing to know the low-level details of the API client,
polling, or error handling.

Key Responsibilities:
- Manages configuration (e.g., getting the API URL from environment variables).
- Encapsulates the entire API call lifecycle into a single function.
- Provides robust, application-specific error handling.
- Processes the API response into a clean, usable format (e.g., downloading images).
"""

import os
import requests
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

# Import the client and its specific exceptions from the 'api_client' library,
# which should be placed within the main application's codebase.
from ..libs.api_client.client import CreativeCatalystClient # type: ignore
from ..libs.api_client.exceptions import ( # type: ignore
    APIClientError,
    JobFailedError,
    PollingTimeoutError,
)

# --- Configuration ---
# Best practice: The API URL should be managed via environment variables, not hardcoded.
# This allows for different URLs for development, staging, and production.
CREATIVE_CATALYST_API_URL = os.getenv(
    "CREATIVE_CATALYST_API_URL", "http://127.0.0.1:9500"
)

# Define a default location for downloaded assets. In a real app, this might
# be a cloud storage bucket path or a configured media directory.
DEFAULT_ASSET_DOWNLOAD_DIR = Path("./creative_catalyst_assets")


def _download_and_save_images(image_urls: List[str], download_dir: Path) -> List[Path]:
    """
    A helper function to download images and save them locally.

    Args:
        image_urls: A list of public URLs for the images to download.
        download_dir: The local directory where images will be saved.

    Returns:
        A list of Path objects pointing to the newly downloaded local files.
    """
    if not image_urls:
        print("INFO: No image URLs were provided in the API response.")
        return []

    print(f"INFO: Starting download of {len(image_urls)} images to '{download_dir}'...")
    download_dir.mkdir(parents=True, exist_ok=True)
    local_image_paths = []

    for url in image_urls:
        try:
            filename = url.split("/")[-1]
            save_path = download_dir / filename

            response = requests.get(url, timeout=45)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            local_image_paths.append(save_path)
            print(f"  - Success: Saved {filename}")

        except requests.exceptions.RequestException as e:
            # In a real app, you would log this to a proper logging service.
            print(f"  - ERROR: Failed to download image {url}. Reason: {e}")

    return local_image_paths


def generate_trend_report(
    creative_brief: str,
    output_directory: Path = DEFAULT_ASSET_DOWNLOAD_DIR,
) -> Optional[Tuple[Dict[str, Any], List[Path]]]:
    """
    Generates a full fashion trend report and downloads all associated images.

    This is the primary function that the main application should call. It handles
    client initialization, API interaction, error handling, and result processing.

    Args:
        creative_brief: The natural language prompt for the trend report.
        output_directory: The local directory to save the downloaded images.

    Returns:
        On success: A tuple containing:
            - A dictionary with the structured fashion trend report.
            - A list of Path objects for the locally saved images.
        On failure: None.
    """
    print(
        f"--- Initializing Creative Catalyst Service for brief: '{creative_brief[:50]}...' ---"
    )
    try:
        # 1. Initialize the client with the configured URL.
        client = CreativeCatalystClient(base_url=CREATIVE_CATALYST_API_URL)

        # 2. Call the client to handle the entire asynchronous process.
        #    This will block until the job is complete, fails, or times out.
        api_response = client.get_creative_report(
            creative_brief, timeout=600
        )  # 10 min timeout

        # 3. Process the successful response.
        report_data = api_response.get("final_report", {})
        image_urls = api_response.get("image_urls", [])

        if not report_data:
            print("ERROR: API call was successful but returned no report data.")
            return None

        # 4. Download the images and get their local paths.
        local_image_paths = _download_and_save_images(image_urls, output_directory)

        print("--- ✅ Creative Catalyst Service finished successfully. ---")
        return report_data, local_image_paths

    # 5. Handle specific, known errors gracefully.
    except JobFailedError as e:
        print(
            f"--- ❌ CRITICAL: The background job '{e.job_id}' failed on the server. ---"
        )
        print(f"    Server Error: {e.error_message}")
        return None

    except PollingTimeoutError as e:
        print(
            f"--- ❌ ERROR: Timed out after {e.timeout}s waiting for job '{e.job_id}'. ---"
        )
        print("    The job may still be running on the server, but we stopped waiting.")
        return None

    except APIClientError as e:
        print(f"--- ❌ ERROR: An API communication error occurred. ---")
        print(f"    Details: {e}")
        return None

    except Exception as e:
        print(
            f"--- ❌ ERROR: An unexpected error occurred in the reporting service. ---"
        )
        print(f"    Details: {e}")
        return None


# --- Example Usage ---
# This block demonstrates how the rest of the company's application would
# import and use the `generate_trend_report` function.
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  RUNNING FASHION REPORTING SERVICE DEMO")
    print("=" * 50 + "\n")

    # The main application just needs to provide a brief.
    example_brief = "A collection inspired by the fusion of traditional Japanese minimalism and Scandinavian functional design, focusing on outerwear."

    # Call the main service function.
    result = generate_trend_report(example_brief)

    # The application then checks if the result is valid before using it.
    if result:
        # Unpack the successful result tuple
        report, image_paths = result

        print("\n--- DEMO: Successfully Processed Report ---")
        print(f"Overarching Theme: {report.get('overarching_theme')}")
        print(f"Generated {len(report.get('detailed_key_pieces', []))} Key Pieces.")
        print(
            f"Downloaded {len(image_paths)} images to '{DEFAULT_ASSET_DOWNLOAD_DIR.resolve()}'"
        )

        # Now the application can use the 'report' dictionary and 'image_paths' list
        # to save to a database, display on a UI, etc.

    else:
        print("\n--- DEMO: Report Generation Failed ---")
        print("Please check the error messages above for details.")

    print("\n" + "=" * 50)
    print("  DEMO COMPLETE")
    print("=" * 50 + "\n")
