# api_client/example.py

from typing import Generator, Dict, Any, Optional
from .client import CreativeCatalystClient
from .exceptions import APIClientError

PROMPT = """
A futuristic, eco-friendly denim jacket inspired by bioluminescent fungi.
"""

# The progressive list of temperatures to cycle through for visual variations.
TEMPERATURE_PROGRESSION = [1.0, 1.5, 2.0]


def _handle_stream(stream: Generator[Dict[str, Any], None, None]) -> Optional[str]:
    # ... (this helper function is unchanged) ...
    job_id = None
    try:
        for update in stream:
            event_type = update.get("event")
            if event_type == "job_submitted":
                job_id = update.get("job_id")
                print(f"✅ Job successfully submitted with ID: {job_id}")
            elif event_type == "progress":
                print(f"   Progress: {update.get('status')}")
            elif event_type == "complete":
                print("\n--- ✅ Final Report Received ---")
                break
        return job_id
    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred ---")
        print(f"   Error: {e}")
        return None
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred ---")
        print(f"   Error: {e}")
        return None


def main():
    """Runs the interactive CLI loop for the simplified workflow."""
    client = CreativeCatalystClient()
    last_job_id = None
    visual_variation_count = 0

    print("\n" + "=" * 70)
    print("          CREATIVE CATALYST INTERACTIVE CLIENT")
    print("=" * 70)
    print(f'  Using Prompt: "{PROMPT.strip()}"')

    while True:
        print("\n" + "-" * 70)
        print(f"  Last Successful Job ID: {last_job_id or 'None'}")
        print("-" * 70)

        print("  [1] Generate New Report (Canonical, default temp)")
        print("  [2] Check Cache (run again)")
        if last_job_id:
            print("  [3] Generate Visual Variation (Images only, new temperature)")
        print("  [4] Quit")
        print("-" * 70)

        choice = input("Enter your choice: ")

        if choice == "1":
            print("\n--- 🚀 [1] Requesting Canonical Report ---")
            stream = client.get_creative_report_stream(PROMPT, variation_seed=0)
            job_id = _handle_stream(stream)
            if job_id:
                last_job_id = job_id
                visual_variation_count = 0  # Reset counter on new report

        elif choice == "2":
            print(f"\n--- 🚀 [2] Re-running prompt to check cache ---")
            stream = client.get_creative_report_stream(PROMPT, variation_seed=0)
            _handle_stream(stream)

        elif choice == "3" and last_job_id:
            if visual_variation_count >= len(TEMPERATURE_PROGRESSION):
                print(
                    f"--- ⚠️ All visual variations attempted. Max temperature {TEMPERATURE_PROGRESSION[-1]} reached. ---"
                )
                continue

            temp_to_use = TEMPERATURE_PROGRESSION[visual_variation_count]
            print(
                f"\n--- 🚀 [3] Requesting Visual Variation #{visual_variation_count + 1} for Job '{last_job_id}' (temp={temp_to_use}) ---"
            )
            stream = client.regenerate_images_stream(
                original_job_id=last_job_id, temperature=temp_to_use
            )
            # We don't capture the new job_id, we just get the result
            _handle_stream(stream)
            visual_variation_count += 1

        elif choice == "4":
            print("--- 👋 Exiting client. ---")
            break

        else:
            print(
                "--- ⚠️ Invalid choice. Please select a valid option from the menu. ---"
            )


if __name__ == "__main__":
    main()
