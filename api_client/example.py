# api_client/example.py

from .client import CreativeCatalystClient
from .exceptions import APIClientError

# ===================================================================
#  MASTER WORKFLOW DEMONSTRATION
# ===================================================================
# This script demonstrates the three primary ways to generate and vary
# creative content with the API:
#
# 1.  **Canonical Generation (variation_seed=0):**
#     The first, default, and cacheable result for a creative brief.
#
# 2.  **Conceptual Variation (variation_seed > 0):**
#     Requests a completely new creative direction (new research, new text,
#     new garments, new images) based on the same initial prompt.
#
# 3.  **Visual Variation (regenerate_images_stream):**
#     Takes an existing report and regenerates ONLY the images with a new
#     visual seed, providing a fast, new look for the same concept.
# ===================================================================

PROMPT = """
A men's velvet tailcoat for a Venetian masquerade ball set in the Baroque era.
"""


def main():
    """
    Demonstrates the full three-stage variation workflow.
    """
    client = CreativeCatalystClient()
    original_job_id = None

    # ===================================================================
    #  PART 1: Canonical Creative Report (variation_seed = 0)
    # ===================================================================
    print(
        "--- 🚀 PART 1: Requesting the Canonical Creative Report (variation_seed=0) ---"
    )
    try:
        stream = client.get_creative_report_stream(PROMPT, variation_seed=0)

        for update in stream:
            event_type = update.get("event")
            if event_type == "job_submitted":
                original_job_id = update.get("job_id")
                print(f"✅ Canonical job submitted with ID: {original_job_id}")
            elif event_type == "progress":
                print(f"   Progress: {update.get('status')}")
            elif event_type == "complete":
                print("\n--- ✅ Canonical Report Received ---")
                break

    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred During Part 1 ---")
        print(f"   Error: {e}")
        return  # Stop if the first part fails
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred During Part 1 ---")
        print(f"   Error: {e}")
        return

    # ===================================================================
    #  PART 2: Conceptual Variation (variation_seed = 1)
    # ===================================================================
    print("\n" + "=" * 70)
    input("✅ Part 1 complete. Press Enter to request a new CONCEPTUAL variation...")
    print("=" * 70 + "\n")

    print("--- 🚀 PART 2: Requesting a Conceptual Variation (variation_seed=1) ---")
    print(
        "   (This will run the full pipeline again to generate a new creative direction)"
    )
    try:
        stream = client.get_creative_report_stream(PROMPT, variation_seed=1)

        for update in stream:
            event_type = update.get("event")
            if event_type == "job_submitted":
                print(
                    f"✅ Conceptual variation job submitted with ID: {update.get('job_id')}"
                )
            elif event_type == "progress":
                print(f"   Progress: {update.get('status')}")
            elif event_type == "complete":
                print("\n--- ✅ New Conceptual Report Received ---")
                break

    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred During Part 2 ---")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred During Part 2 ---")
        print(f"   Error: {e}")

    # ===================================================================
    #  PART 3: Visual Variation (Regenerate Images)
    # ===================================================================
    if not original_job_id:
        print(
            "\n--- ⚠️ Could not proceed to Part 3: No original job ID was captured. ---"
        )
        return

    print("\n" + "=" * 70)
    input(
        "✅ Part 2 complete. Press Enter to request a new VISUAL variation for the original report..."
    )
    print("=" * 70 + "\n")

    print(
        f"--- 🚀 PART 3: Requesting a Visual Variation for Original Job '{original_job_id}' ---"
    )
    print("   (This will be much faster as it only regenerates the images)")
    try:
        regen_stream = client.regenerate_images_stream(
            original_job_id=original_job_id,
            seed=1,
            temperature=1.2,  # Optional: make it a bit more creative
        )

        for update in regen_stream:
            event_type = update.get("event")
            if event_type == "job_submitted":
                print(
                    f"✅ Visual variation job submitted with NEW ID: {update.get('job_id')}"
                )
            elif event_type == "progress":
                print(f"   Regeneration Progress: {update.get('status')}")
            elif event_type == "complete":
                print("\n--- ✅ New Visual Report Received ---")
                break

    except APIClientError as e:
        print(f"\n--- ❌ An API Client Error Occurred During Part 3 ---")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"\n--- ❌ An Unexpected Error Occurred During Part 3 ---")
        print(f"   Error: {e}")

    print("\n--- 🎉 Workflow Demonstration Complete ---")


if __name__ == "__main__":
    main()
