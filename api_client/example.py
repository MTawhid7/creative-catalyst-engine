# api_client/example.py

# Use explicit relative imports by adding a '.' before the module name
from .client import CreativeCatalystClient
from .exceptions import APIClientError


def main():
    """
    A demonstration of how to use the CreativeCatalystClient.
    """
    # Initialize the client. In a real application, the URL might
    # come from a configuration file or environment variable.
    client = CreativeCatalystClient(base_url="http://127.0.0.1:8000")

    # Define the creative brief
    creative_brief = "A report on the 'Gorpcore' aesthetic, focusing on technical outerwear for the luxury market."

    print("--- Starting Creative Catalyst API Client Demo ---")
    try:
        # This one line handles submission, polling, and error checking.
        final_report = client.get_creative_report(creative_brief)

        print("\n--- ✅ Final Report Received ---")
        # Pretty-print the main parts of the report
        print(f"Theme: {final_report.get('final_report', {}).get('overarching_theme')}")
        print(f"Artifacts saved at: {final_report.get('artifacts_path')}")

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
