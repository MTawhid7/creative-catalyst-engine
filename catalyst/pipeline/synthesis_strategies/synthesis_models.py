# catalyst/pipeline/synthesis_strategies/synthesis_models.py

"""
Defines all intermediate Pydantic data models used during the synthesis phase.
This definitive version is fully aligned with our simplified, robust architecture.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from ...models.trend_report import KeyPieceDetail

# This config will be reused by all models to ignore unexpected extra fields from the AI.
resilient_config = ConfigDict(extra="ignore")


# Use json_schema_extra in the ConfigDict to provide metadata. This is a more robust
# pattern that separates validation from schema documentation and satisfies strict type checkers.
class NamedDescriptionModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "description": "A generic, Gemini-compatible model for a name/description pair."
        },
    )
    name: str = Field(
        ..., json_schema_extra={"description": "The concise name for the item."}
    )
    description: str = Field(
        ..., json_schema_extra={"description": "The detailed description for the item."}
    )


# --- Research Dossier Model ---


class ResearchDossierModel(BaseModel):
    """
    The definitive, structured output of the WebResearchProcessor. It is designed
    to be simple and robust, using flat strings for its primary fields.
    """

    model_config = resilient_config
    trend_narrative: Optional[str] = Field(default="")
    visual_language_colors: Optional[str] = Field(default="")
    visual_language_materials: Optional[str] = Field(default="")
    visual_language_silhouettes: Optional[str] = Field(default="")
    cultural_context_summary: Optional[str] = Field(default="")
    market_manifestation_summary: Optional[str] = Field(default="")
    commercial_strategy_summary: Optional[str] = Field(default="")
    emerging_trends_summary: Optional[str] = Field(default="")


# --- Builder Output Models ---


class NarrativeSynthesisModel(BaseModel):
    """The output of the NarrativeSynthesisBuilder."""

    model_config = resilient_config
    overarching_theme: Optional[str] = Field(default="")
    trend_narrative_synthesis: Optional[str] = Field(default="")


class CulturalDriversModel(BaseModel):
    """The output of the CulturalDriversBuilder."""

    model_config = resilient_config
    # --- START: THE DEFINITIVE FIX ---
    # Changed to a list of the new, more elegant structured objects.
    cultural_drivers: List[NamedDescriptionModel] = Field(default_factory=list)
    # --- END: THE DEFINITIVE FIX ---


class InfluentialModelsModel(BaseModel):
    """The output of the InfluentialModelsBuilder."""

    model_config = resilient_config
    # --- START: THE DEFINITIVE FIX ---
    # Changed to a list of the new, more elegant structured objects.
    influential_models: List[NamedDescriptionModel] = Field(default_factory=list)
    # --- END: THE DEFINITIVE FIX ---


class CommercialStrategyModel(BaseModel):
    """The output of the CommercialStrategyBuilder."""

    model_config = resilient_config
    commercial_strategy_summary: Optional[str] = Field(default="")


class AccessoriesModel(BaseModel):
    """The output of the AccessoriesBuilder."""

    model_config = resilient_config
    # --- START: THE DEFINITIVE FIX ---
    # Changed to a list of the new, more elegant structured objects.
    accessories: List[NamedDescriptionModel] = Field(default_factory=list)
    # --- END: THE DEFINITIVE FIX ---


class SingleGarmentModel(BaseModel):
    """The output of the SingleGarmentBuilder, used iteratively."""

    model_config = resilient_config
    key_piece: KeyPieceDetail


class NarrativeSettingModel(BaseModel):
    """The output of the NarrativeSettingBuilder."""

    model_config = resilient_config
    narrative_setting_description: Optional[str] = Field(default="")
