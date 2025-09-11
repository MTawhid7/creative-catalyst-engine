# catalyst/pipeline/synthesis_strategies/synthesis_models.py

"""
Defines the intermediate Pydantic data models used exclusively during the
"divide and conquer" synthesis process within the ReportAssembler.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


# --- START: ADD NEW MODEL ---
class ColorPaletteStrategyModel(BaseModel):
    tonal_story: str = Field(
        ...,
        description="A short, evocative paragraph describing the overall mood and psychology of the color direction.",
    )


# --- END: ADD NEW MODEL ---

# --- START OF DEFINITIVE FIX ---
# Move the NarrativeSettingModel here to its correct, centralized location.
class NarrativeSettingModel(BaseModel):
    narrative_setting: str = Field(
        ..., description="A single, atmospheric paragraph under 50 words."
    )


# --- END OF DEFINITIVE FIX ---


class OverarchingThemeModel(BaseModel):
    """A model to structure the overarching theme of the report."""

    overarching_theme: str = Field(
        ...,
        description="A single, concise string summarizing the core theme of the collection.",
    )


class CulturalDriversModel(BaseModel):
    """A model to structure the list of cultural drivers."""

    cultural_drivers: List[str] = Field(
        ...,
        description="A list of strings, where each string is a cultural driver and its impact explanation.",
    )


class InfluentialModelsModel(BaseModel):
    """A model to structure the list of influential models or archetypes."""

    influential_models: List[str] = Field(
        ...,
        description="A list of timeless archetypes or subcultures that embody the trend.",
    )


class AccessoriesModel(BaseModel):
    """A model for the inner dictionary of accessories."""

    Bags: List[str] = Field(default=[], description="List of bag accessories.")
    Footwear: List[str] = Field(default=[], description="List of footwear accessories.")
    Jewelry: List[str] = Field(default=[], description="List of jewelry accessories.")
    Other: List[str] = Field(default=[], description="List of other accessories.")


class KeyPieceNamesModel(BaseModel):
    """
    A model to structure the list of creative names for the key garments,
    used specifically in the direct knowledge fallback path.
    """

    names: List[str] = Field(...)
