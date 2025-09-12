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

from .worker import create_creative_report

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SENTRY_DSN = os.getenv("SENTRY_DSN")


async def on_startup(ctx):
    """
    A function that runs when the ARQ worker starts. This is the ideal place
    to initialize services that the worker needs, like Sentry.
    """
    # --- START: Sentry Initialization for ARQ Worker ---
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            # The ArqIntegration automatically hooks into the ARQ worker
            # to capture errors and performance data from background jobs.
            integrations=[
                ArqIntegration(),
            ],
        )
        print("✅ Sentry configured for ARQ worker.")
    # --- END: Sentry Initialization for ARQ Worker ---
    print("ARQ worker started. Ready to process creative jobs.")


async def on_shutdown(ctx):
    """A function that runs when the ARQ worker shuts down."""
    print("ARQ worker shutting down.")


# This is the main configuration class for the ARQ worker.
class WorkerSettings:
    """
    Defines the settings for the ARQ worker.
    """

    functions = [create_creative_report]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 60 * 30
    on_startup = on_startup
    on_shutdown = on_shutdown
