# api/main.py

import os
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from arq.connections import ArqRedis, create_pool

from .worker_settings import WorkerSettings
from .routes.jobs import router as jobs_router  # Import the new router
from catalyst.utilities.logger import get_logger
from . import config as api_config  # Import the api config

# Sentry, logging, etc. remains the same
load_dotenv()
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[FastApiIntegration()])
    print("✅ Sentry configured for FastAPI.")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's lifespan, creating a Redis pool on startup."""
    app.state.redis: ArqRedis = await create_pool(WorkerSettings.redis_settings)  # type: ignore
    logger.info("ARQ Redis connection pool created.")
    yield
    await app.state.redis.close()
    logger.info("ARQ Redis connection pool closed.")


app = FastAPI(
    title="Creative Catalyst Engine API",
    description="An API for generating fashion trend reports and images.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files for serving results
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
# --- START: URL PATH REFACTOR ---
# Use the constant from the config for the mount path and name.
app.mount(
    f"/{api_config.RESULTS_MOUNT_PATH}",
    StaticFiles(directory=RESULTS_DIR),
    name=api_config.RESULTS_MOUNT_PATH,
)
# --- END: URL PATH REFACTOR ---

# Include the job routes
app.include_router(jobs_router)
