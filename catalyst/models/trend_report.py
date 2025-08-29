"""
Pydantic Models for the Creative Catalyst Engine.
This is the definitive, enhanced version for a professional-grade output,
incorporating detailed specifications for fabric, pattern, and traceability.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict

strict_config = ConfigDict(extra="forbid")


# --- NEW: Model for traceability and metadata ---
class PromptMetadata(BaseModel):
    """Contains metadata about the generation request for traceability."""

    model_config = strict_config
    run_id: str = Field(..., description="The unique ID for the generation run.")
    user_passage: str = Field(..., description="The original, unmodified user input.")


# --- NEW: Model for detailed pattern specifications ---
class PatternDetail(BaseModel):
    """Describes a print or pattern with technical and creative details."""

    model_config = strict_config
    motif: str = Field(
        ...,
        description="The name or description of the pattern's repeating element (e.g., 'Paisley Swirls', 'Art Deco Geometric').",
    )
    placement: str = Field(
        ...,
        description="How the pattern is applied to the garment (e.g., 'All-over print', 'Engineered panel', 'Border trim').",
    )
    scale_cm: Optional[float] = Field(
        None,
        description="The approximate size in centimeters of one repeat of the motif.",
    )


# --- ENHANCED: Fabric model with professional-grade details ---
class FabricDetail(BaseModel):
    """Describes a fabric with technical and textural properties."""

    model_config = strict_config
    material: str = Field(
        ...,
        description="The name of the fabric material (e.g., 'Recycled Nylon', 'Organic Cotton Twill').",
    )
    texture: str = Field(
        ...,
        description="The tactile surface texture of the fabric (e.g., 'Crinkled', 'Brushed', 'Slubby').",
    )
    sustainable: Optional[bool] = Field(
        None, description="Whether the fabric is considered sustainable."
    )
    weight_gsm: Optional[int] = Field(
        None,
        description="The weight of the fabric in grams per square meter (e.g., 120 for a shirt, 350 for a coat).",
    )
    drape: Optional[str] = Field(
        None, description="How the fabric hangs (e.g., 'Fluid', 'Structured', 'Stiff')."
    )
    finish: Optional[str] = Field(
        None,
        description="The surface finish of the fabric (e.g., 'Matte', 'Satin', 'Water-resistant').",
    )


class ColorDetail(BaseModel):
    """Describes a color with its name and technical codes."""

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


# --- ENHANCED: Key Piece model with new structured fields ---
class KeyPieceDetail(BaseModel):
    """Describes a single core garment in the collection with deep detail."""

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
    patterns: List[PatternDetail] = Field(
        default=[],
        description="A list of specific prints or patterns used on the garment.",
    )
    fabrics: List[FabricDetail] = Field(
        ..., description="A curated list of recommended fabrics for the piece."
    )
    colors: List[ColorDetail] = Field(
        ..., description="A curated list of suitable colors for the piece."
    )
    silhouettes: List[str] = Field(
        ..., description="Specific cuts and shapes that define the garment's form."
    )
    lining: Optional[str] = Field(
        None,
        description="Description of the garment's lining (e.g., 'Fully lined in silk', 'Unlined for breathability').",
    )
    details_trims: List[str] = Field(
        ..., description="Specific design details, hardware, or trims."
    )
    suggested_pairings: List[str] = Field(
        ..., description="Other items to style with this piece."
    )


# --- ENHANCED: Root model with new metadata field ---
class FashionTrendReport(BaseModel):
    """The root model for the entire fashion trend report."""

    model_config = strict_config
    prompt_metadata: PromptMetadata = Field(
        ..., description="Metadata about the original request for traceability."
    )
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
