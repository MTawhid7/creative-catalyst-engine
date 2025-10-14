# api/worker_settings.py

"""
This file contains the settings for the ARQ (Asyncio-Redis-Queue) worker.
ARQ uses this class to configure the Redis connection, discover tasks,
and set worker behavior.
"""

import os
from arq.connections import RedisSettings
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.arq import ArqIntegration

# Load environment variables from the root .env file
load_dotenv()

# --- START: IMPORT NEW TASK ---
from .worker import create_creative_report, regenerate_images_task

# --- END: IMPORT NEW TASK ---

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SENTRY_DSN = os.getenv("SENTRY_DSN")


async def on_startup(ctx):
    """
    A function that runs when the ARQ worker starts. This is the ideal place
    to initialize services that the worker needs, like Sentry.
    """
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            integrations=[
                ArqIntegration(),
            ],
        )
        print("✅ Sentry configured for ARQ worker.")
    print("ARQ worker started. Ready to process creative jobs.")


async def on_shutdown(ctx):
    """A function that runs when the ARQ worker shuts down."""
    print("ARQ worker shutting down.")


# This is the main configuration class for the ARQ worker.
class WorkerSettings:
    """
    Defines the settings for the ARQ worker.
    """

    # --- START: REGISTER NEW TASK ---
    functions = [create_creative_report, regenerate_images_task]
    # --- END: REGISTER NEW TASK ---
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 60 * 30
    on_startup = on_startup
    on_shutdown = on_shutdown
