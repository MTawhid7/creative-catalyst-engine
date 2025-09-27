# api/services/streaming.py

"""
Contains the core business logic for the real-time job status streaming service.
"""

import json
import asyncio
from typing import Dict, Any, AsyncGenerator

from arq.connections import ArqRedis
from arq.jobs import Job, JobStatus


async def create_event_generator(
    job_id: str, redis: ArqRedis
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    The core async generator logic, extracted for direct testability.
    This function yields Server-Sent Event (SSE) compatible dictionaries.
    """
    job = Job(job_id, redis)
    initial_status = await job.status()
    if initial_status == JobStatus.not_found:
        yield {"event": "error", "data": json.dumps({"detail": "Job not found"})}
        return

    progress_key = f"job_progress:{job_id}"

    while True:
        current_job_status = await job.status()
        if current_job_status == JobStatus.complete:
            try:
                result = await job.result()
                yield {
                    "event": "complete",
                    "data": json.dumps(
                        {"status": "complete", "result": result, "error": None}
                    ),
                }
            except Exception as e:
                yield {
                    "event": "complete",
                    "data": json.dumps(
                        {"status": "failed", "result": None, "error": str(e)}
                    ),
                }
            break

        granular_status = await redis.get(progress_key)
        if granular_status:
            yield {
                "event": "progress",
                "data": json.dumps({"status": granular_status.decode()}),
            }
        else:
            yield {
                "event": "progress",
                "data": json.dumps({"status": current_job_status.value}),
            }

        await asyncio.sleep(2)
