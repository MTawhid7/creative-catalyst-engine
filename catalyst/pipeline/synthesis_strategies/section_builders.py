# catalyst/pipeline/synthesis_strategies/section_builders.py

"""
This module contains the self-contained, single-responsibility "Builder"
strategies for the report, now fully decoupled from the `brand_ethos` context.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from catalyst import settings
from ...clients import gemini
from ...context import RunContext
from ...prompts import prompt_library
from ...utilities.logger import get_logger
from ...resilience import invoke_with_resilience, MaxRetriesExceededError

from .synthesis_models import (
    NarrativeSynthesisModel,
    CreativeAnalysisModel,
    AccessoriesModel,
    SingleGarmentModel,
    NarrativeSettingModel,
)

logger = get_logger(__name__)


class BaseSectionBuilder(ABC):
    """Abstract base class for a dossier-informed report section builder."""

    def __init__(self, context: RunContext, research_dossier: Dict[str, Any]):
        self.context = context
        self.brief = context.enriched_brief
        self.dossier = research_dossier
        self.logger = get_logger(self.__class__.__name__)
        # The base arguments are now simplified and decoupled from the context's attributes.
        self.base_prompt_args = {
            "research_dossier": json.dumps(self.dossier, indent=2),
            "enriched_brief": json.dumps(self.brief, indent=2),
        }

    @abstractmethod
    async def build(self) -> Dict[str, Any] | None:
        """Builds a specific section of the report."""
        pass


# --- Concrete Builder Implementations ---


class NarrativeSynthesisBuilder(BaseSectionBuilder):
    """Synthesizes the comprehensive strategic narrative for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing strategic narrative...")
        try:
            prompt_args = self.base_prompt_args | {
                "narrative_synthesis_schema": json.dumps(
                    NarrativeSynthesisModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.NARRATIVE_SYNTHESIS_PROMPT.format(**prompt_args),
                NarrativeSynthesisModel,
            )
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Narrative synthesis failed. This section will be missing critical data."
            )
            return None


class CreativeAnalysisBuilder(BaseSectionBuilder):
    """
    An efficient, consolidated builder that synthesizes cultural drivers,
    influential models, and commercial strategy in a single AI call.
    """

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing consolidated creative analysis...")
        try:
            prompt_args = self.base_prompt_args | {
                "analysis_schema": json.dumps(
                    CreativeAnalysisModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.CREATIVE_ANALYSIS_PROMPT.format(**prompt_args),
                CreativeAnalysisModel,
            )
            return model.model_dump(mode="json")
        except MaxRetriesExceededError:
            self.logger.warning(
                "Consolidated creative analysis failed. Using safe defaults."
            )
            # Return a valid structure with empty values to prevent downstream errors
            return {
                "cultural_drivers": [],
                "influential_models": [],
                "commercial_strategy_summary": "",
            }


class AccessoriesBuilder(BaseSectionBuilder):
    """Synthesizes the full suite of accessories for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing accessories suite...")
        try:
            prompt_args = self.base_prompt_args | {
                "accessories_schema": json.dumps(
                    AccessoriesModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(**prompt_args),
                AccessoriesModel,
            )
            return model.model_dump(mode="json")
        except MaxRetriesExceededError:
            self.logger.warning(
                "Accessories synthesis failed. Using empty list as fallback."
            )
            return {"accessories": []}


class SingleGarmentBuilder:
    """Synthesizes a single, visionary key garment for the collection."""

    def __init__(self, context: RunContext, research_dossier: Dict[str, Any]):
        self.context = context
        self.dossier = research_dossier
        self.brief = context.enriched_brief
        self.logger = get_logger(self.__class__.__name__)
        self.base_prompt_args = {
            "research_dossier": json.dumps(self.dossier, indent=2),
            "enriched_brief": json.dumps(self.brief, indent=2),
            "brand_ethos": self.context.brand_ethos,
        }

    async def build(
        self, previously_designed_garments: List[Dict[str, Any]]
    ) -> Dict[str, Any] | None:
        self.logger.info(
            f"Synthesizing garment #{len(previously_designed_garments) + 1}..."
        )
        try:
            prompt_args = self.base_prompt_args | {
                "previously_designed_garments": json.dumps(
                    previously_designed_garments, indent=2
                ),
                "single_garment_schema": json.dumps(
                    SingleGarmentModel.model_json_schema(), indent=2
                ),
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.SINGLE_GARMENT_SYNTHESIS_PROMPT.format(**prompt_args),
                SingleGarmentModel,
                model_name=settings.GEMINI_PRO_MODEL_NAME,
            )
            return model.model_dump(mode="json")
        except MaxRetriesExceededError:
            self.logger.error(
                "Failed to synthesize a single garment after all retries."
            )
            return None


class NarrativeSettingBuilder(BaseSectionBuilder):
    """Synthesizes the atmospheric narrative setting for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing narrative setting...")
        try:
            prompt_args = self.base_prompt_args | {
                "narrative_setting_schema": json.dumps(
                    NarrativeSettingModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.NARRATIVE_SETTING_PROMPT.format(**prompt_args),
                NarrativeSettingModel,
            )
            return model.model_dump(mode="json")
        except MaxRetriesExceededError:
            self.logger.warning(
                "Narrative setting synthesis failed. This section will be missing."
            )
            return None
