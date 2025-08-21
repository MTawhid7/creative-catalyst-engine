"""
The Main Entry Point for the Creative Catalyst Engine.

This file serves as the single, user-facing entry point to run the application.
It is responsible for:
1.  Setting up the structured, traceable logging for the run.
2.  Capturing the user's high-level creative request.
3.  Initiating the main creative workflow via the orchestrator.
4.  Logging the final outcome and total execution time.
"""

import asyncio
import time

# Import the high-level orchestrator and the logger setup utility
from .services import orchestrator
from .utilities.logger import get_logger, setup_logging_run_id

# Initialize a logger specific to this main module
logger = get_logger(__name__)

# --- USER INTERFACE: The Natural Language Brief -----------------------------
# This is the single point of interaction for the user.
# The user provides a high-level creative goal in natural language.
# The system's "Intelligent Brief" engine will handle the rest.
USER_PASSAGE = """
I need to design a collection of women's outerwear for Fall/Winter 2026.
The core theme is 'Arctic Minimalism', inspired by the stark beauty of polar landscapes
and the functional design of Inuit clothing. The brand category is luxury, and the
target audience is a sophisticated, urban consumer who values both style and sustainability.
"""

# --- Main Application Logic --------------------------------------------------


async def main():
    """The main asynchronous function that orchestrates the application run."""

    # --- 1. Setup Logging ---
    # This is the very first step. It generates a unique ID for this specific run,
    # which will be attached to every log message for easy tracing.
    run_id = setup_logging_run_id()

    logger.info(f"================== RUN ID: {run_id} ==================")
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")
    logger.info("=========================================================")

    start_time = time.time()

    try:
        # --- 2. Initiate the Workflow ---
        # The main entry point calls the high-level 'run' function in the orchestrator,
        # passing the raw user passage. All complexity is handled by the services.
        await orchestrator.run(USER_PASSAGE)

    except Exception as e:
        # This is a final safety net. The orchestrator should handle its own
        # errors, but this will catch any truly catastrophic, unhandled failures.
        logger.critical(
            "A critical, unhandled error propagated up to the main entry point.",
            exc_info=True,
        )
    finally:
        # --- 3. Log Final Outcome ---
        duration = time.time() - start_time
        logger.info("=========================================================")
        logger.info(f"      CREATIVE PROCESS FINISHED in {duration:.2f} seconds")
        logger.info(f"================== END RUN ID: {run_id} ==================")


if __name__ == "__main__":
    # Standard, robust way to run the main async function.
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
