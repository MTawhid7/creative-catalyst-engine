# catalyst/models/trend_report.py

"""
Pydantic Models for the Creative Catalyst Engine.
This is the definitive, enhanced version for a professional-grade output.
This version has been made hyper-flexible to gracefully handle the natural
variations in LLM responses, following an "Accept, then Normalize" strategy.
"""

from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, Field, ConfigDict

strict_config = ConfigDict(extra="forbid")


class PromptMetadata(BaseModel):
    """Contains metadata about the generation request for traceability."""

    model_config = strict_config
    run_id: str = Field(...)
    user_passage: str = Field(...)


class PatternDetail(BaseModel):
    """Describes a print or pattern with technical and creative details."""

    model_config = strict_config
    motif: str = Field(...)
    placement: str = Field(...)
    scale_cm: Optional[Union[float, str]] = Field(None)  # Can be "approx. 5cm"


class FabricDetail(BaseModel):
    """Describes a fabric with technical and textural properties."""

    model_config = strict_config
    material: str = Field(...)
    texture: str = Field(...)
    sustainable: Optional[bool] = Field(None)
    weight_gsm: Optional[Union[int, str]] = Field(None)  # Can be "120 gsm" or "120-150"
    drape: Optional[str] = Field(None)
    finish: Optional[str] = Field(None)


class ColorDetail(BaseModel):
    """Describes a color with its name and technical codes."""

    model_config = strict_config
    name: str = Field(...)
    pantone_code: str = Field(...)
    hex_value: str = Field(...)


class KeyPieceDetail(BaseModel):
    """Describes a single core garment in the collection with deep detail."""

    model_config = strict_config
    key_piece_name: str = Field(...)
    description: str = Field(...)
    # --- START: HYPER-FLEXIBILITY REFACTOR ---
    # These fields can be returned as a single item or a list.
    inspired_by_designers: Union[str, List[str]] = Field(default=[])
    silhouettes: Union[str, List[str]] = Field(default=[])
    details_trims: Union[str, List[str]] = Field(default=[])
    suggested_pairings: Union[str, List[str]] = Field(default=[])
    # --- END: HYPER-FLEXIBILITY REFACTOR ---
    wearer_profile: str = Field(default="")
    patterns: List[PatternDetail] = Field(default=[])
    fabrics: List[FabricDetail] = Field(default=[])
    colors: List[ColorDetail] = Field(default=[])
    lining: Optional[str] = Field(None)
    final_garment_image_url: Optional[str] = Field(default=None)
    mood_board_image_url: Optional[str] = Field(default=None)
    final_garment_relative_path: Optional[str] = Field(default=None)
    mood_board_relative_path: Optional[str] = Field(default=None)
    mood_board_prompt: Optional[str] = Field(default=None)
    final_garment_prompt: Optional[str] = Field(default=None)


class FashionTrendReport(BaseModel):
    """The root model for the entire fashion trend report."""

    model_config = strict_config
    prompt_metadata: PromptMetadata = Field(...)
    # --- START: THE FIX ---
    # Make these fields flexible to match the StructuredBriefModel.
    season: Union[str, List[str]] = Field(...)
    year: Union[str, int, List[Union[str, int]]] = Field(...)
    region: Optional[Union[str, List[str]]] = Field(None)
    # --- END: THE FIX ---
    target_gender: str = Field(...)
    target_age_group: Optional[str] = Field(None)
    target_model_ethnicity: str = Field(...)
    desired_mood: Optional[List[str]] = Field(default=[])
    narrative_setting_description: str = Field(...)
    overarching_theme: str = Field(...)
    antagonist_synthesis: Optional[str] = Field(None)
    color_palette_strategy: Optional[str] = Field(None)
    accessory_strategy: Optional[str] = Field(None)
    cultural_drivers: Union[str, List[str]] = Field(default=[])
    influential_models: Union[str, List[str]] = Field(default=[])
    accessories: Dict[str, List[str]] = Field(default={})
    detailed_key_pieces: List[KeyPieceDetail] = Field(default=[])
