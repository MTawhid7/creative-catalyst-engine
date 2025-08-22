"""
Pydantic Models for the Creative Catalyst Engine.
This is the definitive, lean version for the final architecture.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

strict_config = ConfigDict(extra="forbid")


class FabricDetail(BaseModel):
    model_config = strict_config
    material: str = Field(
        ..., description="The name of the fabric material (e.g., 'Recycled Nylon')."
    )
    texture: str = Field(
        ..., description="The texture of the fabric (e.g., 'Matte', 'Slight Sheen')."
    )
    sustainable: Optional[bool] = Field(
        None, description="Whether the fabric is considered sustainable."
    )


class ColorDetail(BaseModel):
    model_config = strict_config
    name: str = Field(
        ..., description="The evocative name of the color (e.g., 'Glacial Blue')."
    )
    pantone_code: str = Field(
        ..., description="The official Pantone code (e.g., '14-4122 TCX')."
    )
    hex_value: str = Field(
        ..., description="The hex code for the color (e.g., '#A2C4D1')."
    )


class KeyPieceDetail(BaseModel):
    model_config = strict_config
    key_piece_name: str = Field(..., description="The descriptive name of the garment.")
    description: str = Field(
        ..., description="This item's role and significance in the collection."
    )
    inspired_by_designers: List[str] = Field(
        ..., description="Real-world designers known for this aesthetic."
    )
    wearer_profile: str = Field(
        ..., description="A short description of the person who would wear this piece."
    )
    cultural_patterns: List[str] = Field(
        default=[], description="Specific cultural or heritage patterns identified."
    )
    fabrics: List[FabricDetail] = Field(
        ..., description="A curated list of recommended fabrics for the piece."
    )
    colors: List[ColorDetail] = Field(
        ..., description="A curated list of suitable colors for the piece."
    )
    silhouettes: List[str] = Field(..., description="Specific cuts and shapes.")
    details_trims: List[str] = Field(
        ..., description="Specific design details or trims."
    )
    suggested_pairings: List[str] = Field(
        ..., description="Other items to style with this piece."
    )


class FashionTrendReport(BaseModel):
    """The root model for the entire fashion trend report."""

    model_config = strict_config
    season: str = Field(..., description="The target season (e.g., 'Fall/Winter').")
    year: int = Field(..., description="The target year for the collection.")
    region: Optional[str] = Field(
        None, description="The geographical region for the trend report."
    )
    target_model_ethnicity: str = Field(
        ..., description="The appropriate model ethnicity for the target region."
    )
    narrative_setting_description: str = Field(
        ...,
        description="A detailed, atmospheric description of the ideal setting or environment that tells the story of the collection.",
    )
    overarching_theme: str = Field(
        ..., description="The high-level, evocative theme of the collection."
    )
    cultural_drivers: List[str] = Field(
        ..., description="The socio-cultural influences driving the theme."
    )
    influential_models: List[str] = Field(
        ..., description="Style icons or archetypes who embody the trend."
    )
    accessories: Dict[str, List[str]] = Field(
        ..., description="Key accessories grouped by category."
    )
    detailed_key_pieces: List[KeyPieceDetail] = Field(
        ..., description="A detailed breakdown of each of the core garments."
    )
