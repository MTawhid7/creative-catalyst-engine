"""
The Main Entry Point for the Creative Catalyst Engine.

This file initializes the pipeline, creates the RunContext, and starts the
orchestrator to execute the end-to-end workflow.
"""

import asyncio
import time

from . import settings
from .context import RunContext
from .pipeline.orchestrator import PipelineOrchestrator
from .utilities.logger import get_logger, setup_logging_run_id

# --- START OF FIX ---
# Initialize the logger at the module level, as recommended for best practice.
# This makes it available for the top-level exception handler.
# It will initially log with the default 'init' run_id.
logger = get_logger(__name__)
# --- END OF FIX ---

# This is the single point of interaction for the user.
USER_PASSAGE = """
Kid's shirt inspired by marvel superheroes
"""


async def main():
    """The main asynchronous function that sets up and runs the pipeline."""

    # 1. Create the RunContext to hold all data for this run
    context = RunContext(user_passage=USER_PASSAGE, results_dir=settings.RESULTS_DIR)

    # 2. Setup the logging context IMMEDIATELY. After this line, all subsequent
    #    logs from our module-level 'logger' will correctly use the run_id.
    setup_logging_run_id(context.run_id)

    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")
    logger.info("=========================================================")

    # 3. Instantiate the orchestrator.
    orchestrator = PipelineOrchestrator()

    # 4. Run the orchestrator's main process
    start_time = time.time()
    await orchestrator.run(context)
    duration = time.time() - start_time

    logger.info("=========================================================")
    logger.info("      CREATIVE PROCESS FINISHED in %.2f seconds", duration)
    logger.info("================== END RUN ID: %s ==================", context.run_id)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Process interrupted by user.")
    except Exception as e:
        # The module-level logger is now available to catch any catastrophic
        # failures that happen during the asyncio.run() call itself.
        logger.critical(
            "❌ A top-level, unhandled exception occurred: %s", e, exc_info=True
        )
