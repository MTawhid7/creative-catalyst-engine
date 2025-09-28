# catalyst/models/trend_report.py

"""
Pydantic Models for the Creative Catalyst Engine. This is the definitive,
final, and fully hardened version. It is designed to be hyper-flexible,
gracefully handling variations or failures from upstream AI builders.
"""

from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, Field, ConfigDict

# Use a consistent and descriptive config name.
resilient_config = ConfigDict(extra="ignore")


class ReportNamedDescription(BaseModel):
    """A generic, Gemini-compatible model for a name/description pair in the final report."""

    model_config = resilient_config
    name: str = Field(...)
    description: str = Field(...)


class PromptMetadata(BaseModel):
    model_config = resilient_config
    run_id: str = Field(...)
    user_passage: str = Field(...)


class PatternDetail(BaseModel):
    """Describes a print or pattern with technical and creative details."""

    model_config = resilient_config
    motif: Optional[str] = Field(default="")
    placement: Optional[str] = Field(default="")
    # Make this a standard optional field. The prompt will be responsible for
    # only providing a value for repeating patterns.
    scale_cm: Optional[Union[float, str]] = None


class FabricDetail(BaseModel):
    """Describes a fabric with technical and textural properties."""

    model_config = resilient_config
    material: Optional[str] = Field(default="")
    texture: Optional[str] = Field(default="")
    sustainable: Optional[bool] = Field(default=None)
    weight_gsm: Optional[Union[int, str]] = Field(default=None)
    drape: Optional[str] = Field(default=None)
    finish: Optional[str] = Field(default=None)


class ColorDetail(BaseModel):
    """Describes a color with its name and technical codes."""

    model_config = resilient_config
    name: Optional[str] = Field(default="")
    pantone_code: Optional[str] = Field(default="")
    hex_value: Optional[str] = Field(default="")


class KeyPieceDetail(BaseModel):
    """Describes a single core garment in the collection with deep detail."""

    model_config = resilient_config
    key_piece_name: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")
    wearer_profile: Optional[str] = Field(default="")
    lining: Optional[str] = Field(default=None)
    inspired_by_designers: List[str] = Field(default_factory=list)
    silhouettes: List[str] = Field(default_factory=list)
    details_trims: List[str] = Field(default_factory=list)
    suggested_pairings: List[str] = Field(default_factory=list)
    patterns: List[PatternDetail] = Field(default_factory=list)
    fabrics: List[FabricDetail] = Field(default_factory=list)
    colors: List[ColorDetail] = Field(default_factory=list)
    final_garment_image_url: Optional[str] = Field(default=None)
    mood_board_image_url: Optional[str] = Field(default=None)
    final_garment_relative_path: Optional[str] = Field(default=None)
    mood_board_relative_path: Optional[str] = Field(default=None)
    mood_board_prompt: Optional[str] = Field(default=None)
    final_garment_prompt: Optional[str] = Field(default=None)


class FashionTrendReport(BaseModel):
    """The root model for the entire fashion trend report."""

    model_config = resilient_config

    # 1. High-Level Metadata
    prompt_metadata: PromptMetadata

    # 2. Core Creative & Brief Parameters (Moved from the end)
    overarching_theme: Optional[str] = Field(default="")
    trend_narrative_synthesis: Optional[str] = Field(default="")
    season: List[str]
    year: List[Union[str, int]]
    region: Optional[List[str]] = None
    target_gender: str
    target_age_group: Optional[str] = None
    target_model_ethnicity: str
    desired_mood: List[str] = Field(default_factory=list)
    antagonist_synthesis: Optional[str] = None

    # 3. Detailed AI-Generated Creative Sections
    cultural_drivers: List[ReportNamedDescription] = Field(default_factory=list)
    influential_models: List[ReportNamedDescription] = Field(default_factory=list)
    commercial_strategy_summary: Optional[str] = Field(default="")
    narrative_setting_description: Optional[str] = Field(default="")
    accessories: List[ReportNamedDescription] = Field(default_factory=list)

    # 4. The Most Detailed Section: The Garments
    detailed_key_pieces: List[KeyPieceDetail] = Field(default_factory=list)
