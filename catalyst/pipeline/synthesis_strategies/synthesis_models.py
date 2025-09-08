# catalyst/pipeline/synthesis_strategies/synthesis_models.py

"""
Defines the intermediate Pydantic data models used exclusively during the
"divide and conquer" synthesis process within the ReportAssembler.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class TopLevelModel(BaseModel):
    """
    A model to structure the high-level, thematic outputs of the initial
    synthesis step.
    """

    overarching_theme: str = Field(...)
    cultural_drivers: List[str] = Field(...)
    influential_models: List[str] = Field(...)


# --- START OF FIX: Simplify the model to be more direct ---
# This schema is simpler for the LLM to follow reliably.
class AccessoriesModel(BaseModel):
    """A model for the inner dictionary of accessories."""

    Bags: List[str] = Field(default=[], description="List of bag accessories.")
    Footwear: List[str] = Field(default=[], description="List of footwear accessories.")
    Jewelry: List[str] = Field(default=[], description="List of jewelry accessories.")
    Other: List[str] = Field(default=[], description="List of other accessories.")


# --- END OF FIX ---


class KeyPieceNamesModel(BaseModel):
    """
    A model to structure the list of creative names for the key garments,
    used specifically in the direct knowledge fallback path.
    """

    names: List[str] = Field(...)
