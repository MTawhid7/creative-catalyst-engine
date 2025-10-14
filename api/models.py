# api/models.py

"""
Contains all API-specific Pydantic data models for request and response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class JobRequest(BaseModel):
    user_passage: str
    variation_seed: int = 0


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# --- START: HYBRID REGENERATION REFACTOR ---
class ImageRegenerationRequest(BaseModel):
    """The request model for regenerating images for an existing job."""

    seed: int = Field(
        ...,
        gt=0,
        description="The variation seed. Increment this (1, 2, 3...) to get a new, different image.",
    )
    temperature: Optional[float] = Field(
        default=None,
        gt=0,
        le=2.0,
        description="Optional: Override the creativity level. Higher values (e.g., 1.5) are more experimental.",
    )


# --- END: HYBRID REGENERATION REFACTOR ---
