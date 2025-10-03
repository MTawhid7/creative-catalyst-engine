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


class NamedDescriptionModel(BaseModel):
    """A generic, Gemini-compatible model for a name/description pair."""
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"description": "A generic name/description pair."},
    )
    name: str = Field(..., json_schema_extra={"description": "The concise name for the item."})
    description: str = Field(..., json_schema_extra={"description": "The detailed description for the item."})


# --- Research Dossier Model ---

class ResearchDossierModel(BaseModel):
    """The definitive, structured output of the WebResearchProcessor."""
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



class CreativeAnalysisModel(BaseModel):
    """The new, consolidated output of the CreativeAnalysisBuilder."""
    model_config = resilient_config
    cultural_drivers: List[NamedDescriptionModel] = Field(..., description="A list of 3-4 key cultural drivers.")
    influential_models: List[NamedDescriptionModel] = Field(..., description="A list of 3-4 key influential models or muses.")
    commercial_strategy_summary: str = Field(..., description="A single, concise paragraph summarizing the commercial strategy.")



class AccessoriesModel(BaseModel):
    """The output of the AccessoriesBuilder."""
    model_config = resilient_config
    accessories: List[NamedDescriptionModel] = Field(default_factory=list)


class SingleGarmentModel(BaseModel):
    """The output of the SingleGarmentBuilder, used iteratively."""
    model_config = resilient_config
    key_piece: KeyPieceDetail


class NarrativeSettingModel(BaseModel):
    """The output of the NarrativeSettingBuilder."""
    model_config = resilient_config
    narrative_setting_description: Optional[str] = Field(default="")