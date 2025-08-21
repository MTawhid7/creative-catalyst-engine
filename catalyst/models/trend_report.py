"""
Pydantic Models for the Creative Catalyst Engine.
(Final, generation-friendly version with complex constraints removed for API compatibility)
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

# This strict configuration is still essential to prevent additional properties.
strict_config = ConfigDict(extra="forbid")


class ColorTrend(BaseModel):
    model_config = strict_config
    name: str = Field(..., description="The common name of the color.")
    pantone_code: Optional[str] = Field(
        None, description="The official Pantone TCX code."
    )
    hex_value: Optional[str] = Field(
        None, description="The hexadecimal representation."
    )


class FabricTrend(BaseModel):
    model_config = strict_config
    material: str = Field(..., description="The base material of the fabric.")
    texture: Optional[str] = Field(
        None, description="The surface texture of the fabric."
    )
    sustainable: bool = Field(
        ..., description="Indicates if the primary material is sustainable."
    )
    sustainability_comment: Optional[str] = Field(
        None, description="An insightful comment on the fabric's sustainability."
    )


class ImageAnalysis(BaseModel):
    model_config = strict_config
    source_url: str = Field(..., description="The URL of the analyzed image.")
    image_description: str = Field(
        ..., description="A concise description of the fashion item."
    )
    garment_type: str = Field(..., description="The primary type of garment.")
    style_keywords: List[str] = Field(
        ..., description="Keywords describing the aesthetic."
    )
    main_colors: List[ColorTrend] = Field(
        ..., description="List of main colors detected."
    )
    detected_fabrics: List[str] = Field(..., description="Inferred fabrics.")
    silhouette: str = Field(..., description="The overall shape and cut.")


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
        default=[],
        description="Specific cultural or heritage patterns identified for this piece (e.g., 'Batik', 'Tartan').",
    )
    fabrics: List[FabricTrend] = Field(
        ..., description="Recommended fabrics for the piece."
    )
    colors: List[ColorTrend] = Field(
        ..., description="Curated list of suitable colors."
    )
    silhouettes: List[str] = Field(..., description="Specific cuts and shapes.")
    details_trims: List[str] = Field(
        ..., description="Specific design details or trims."
    )
    suggested_pairings: List[str] = Field(
        ..., description="Other items to style with this piece."
    )


class FashionTrendReport(BaseModel):
    model_config = strict_config
    season: str = Field(..., description="The target season (e.g., 'Fall/Winter').")
    year: int = Field(..., description="The target year for the collection.")
    region: Optional[str] = Field(
        None, description="The geographical region for the trend report."
    )
    target_model_ethnicity: str = Field(
        ...,
        description="The appropriate model ethnicity for the target region (e.g., 'Indonesian or Southeast Asian').",
    )
    overarching_theme: str = Field(
        ..., description="The high-level, evocative theme of the collection."
    )
    cultural_drivers: List[str] = Field(
        ..., description="The high-level socio-cultural influences driving the theme."
    )
    influential_models: List[str] = Field(
        ..., description="Style icons or archetypes who embody the trend."
    )
    accessories: Dict[str, List[str]] = Field(
        ...,
        description="Key accessories grouped by category (Bags, Footwear, Jewelry, Other).",
    )
    detailed_key_pieces: List[KeyPieceDetail] = Field(
        ...,
        description="A detailed breakdown of each of the core garments in the collection.",
    )
    visual_analysis: List[ImageAnalysis] = Field(
        default=[],
        description="Structured analysis of key inspirational images found during research.",
    )
