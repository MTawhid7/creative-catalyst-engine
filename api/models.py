# api/models.py

"""
Contains all API-specific Pydantic data models for request and response validation.
"""

from pydantic import BaseModel
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
