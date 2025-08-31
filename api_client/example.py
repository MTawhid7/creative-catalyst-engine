# api_client/example.py

import requests
from pathlib import Path

# Use explicit relative imports by adding a '.' before the module name
from .client import CreativeCatalystClient
from .exceptions import APIClientError


def download_images(image_urls: list[str], download_dir: Path):
    """
    Downloads images from a list of URLs into a specified directory.

    Args:
        image_urls: A list of strings, where each string is a URL to an image.
        download_dir: A Path object representing the directory to save images to.
    """
    if not image_urls:
        print("--- No image URLs provided. Skipping download. ---")
        return

    print(f"\n--- 📥 Starting Image Download to '{download_dir}' ---")
    # Create the directory if it doesn't exist
    download_dir.mkdir(exist_ok=True)

    for url in image_urls:
        try:
            # Get the filename from the end of the URL
            filename = url.split("/")[-1]
            save_path = download_dir / filename

            print(f"Downloading {filename} from {url}...")

            # Make the request to download the image
            response = requests.get(url, timeout=30)  # Add a timeout for safety
            response.raise_for_status()  # Raise an exception for bad status codes (like 404)

            # Save the image content to a local file in binary write mode
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
    # Initialize the client. In a real application, the URL might
    # come from a configuration file or environment variable.
    client = CreativeCatalystClient(base_url="http://127.0.0.1:9500")

    # Define the creative brief
    creative_brief = "A report on the 'Gorpcore' aesthetic, focusing on technical outerwear for the luxury market."

    print("--- Starting Creative Catalyst API Client Demo ---")
    try:
        # This one line handles submission, polling, and error checking.
        # The variable 'response_data' will contain the full dictionary from the server.
        response_data = client.get_creative_report(creative_brief)

        print("\n--- ✅ Final Report Received ---")

        # 1. Extract the main report content
        final_report = response_data.get("final_report", {})
        if final_report:
            print(f"Theme: {final_report.get('overarching_theme')}")
            print(f"Server Artifacts Path: {response_data.get('artifacts_path')}")
        else:
            print("Report content is empty.")

        # 2. Extract the image URLs
        image_urls = response_data.get("image_urls", [])

        # 3. Call the helper function to download the images
        #    We'll save them in a new folder named 'downloaded_images'
        download_images(image_urls, download_dir=Path("downloaded_images"))

    except APIClientError as e:
        # Catch any of our custom client errors and print a friendly message.
        print(f"\n--- ❌ An API Client Error Occurred ---")
        print(f"Error: {e}")
    except Exception as e:
        # Catch any other unexpected errors.
        print(f"\n--- ❌ An Unexpected Error Occurred ---")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
