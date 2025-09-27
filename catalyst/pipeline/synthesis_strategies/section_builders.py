# catalyst/pipeline/synthesis_strategies/section_builders.py

"""
This module contains the self-contained, single-responsibility "Builder"
strategies for the report. Each builder is responsible for generating a
specific section of the final report by using the factual Research Dossier
as a foundation for a focused, schema-driven AI call.
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
    CulturalDriversModel,
    InfluentialModelsModel,
    CommercialStrategyModel,
    AccessoriesModel,
    SingleGarmentModel,
    NarrativeSettingModel,
)

logger = get_logger(__name__)

# --- Base Builder Class ---


class BaseSectionBuilder(ABC):
    """
    Abstract base class for a dossier-informed report section builder.
    """

    def __init__(self, context: RunContext, research_dossier: Dict[str, Any]):
        self.context = context
        self.brief = context.enriched_brief
        self.dossier = research_dossier
        self.logger = get_logger(self.__class__.__name__)
        self.base_prompt_args = {
            "research_dossier": json.dumps(self.dossier, indent=2),
            "enriched_brief": json.dumps(self.brief, indent=2),
            "brand_ethos": self.context.brand_ethos,
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


class CulturalDriversBuilder(BaseSectionBuilder):
    """Extracts and enhances the cultural drivers for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing structured cultural drivers...")
        try:
            prompt_args = self.base_prompt_args | {
                "cultural_drivers_schema": json.dumps(
                    CulturalDriversModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.CULTURAL_DRIVERS_PROMPT.format(**prompt_args),
                CulturalDriversModel,
            )
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Cultural drivers synthesis failed. Using empty list as fallback."
            )
            # We still return the correct key to prevent validation errors downstream.
            return {"cultural_drivers": []}


class InfluentialModelsBuilder(BaseSectionBuilder):
    """Extracts and enhances the influential models and muses for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing structured influential models...")
        try:
            prompt_args = self.base_prompt_args | {
                "influential_models_schema": json.dumps(
                    InfluentialModelsModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.INFLUENTIAL_MODELS_PROMPT.format(**prompt_args),
                InfluentialModelsModel,
            )
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Influential models synthesis failed. Using empty list as fallback."
            )
            # Return the correct key to prevent validation errors downstream.
            return {"influential_models": []}


class CommercialStrategyBuilder(BaseSectionBuilder):
    """Synthesizes the high-level commercial strategy summary for the report."""

    async def build(self) -> Dict[str, Any] | None:
        self.logger.info("Synthesizing commercial strategy summary...")
        try:
            prompt_args = self.base_prompt_args | {
                "commercial_strategy_schema": json.dumps(
                    CommercialStrategyModel.model_json_schema(), indent=2
                )
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.COMMERCIAL_STRATEGY_PROMPT.format(**prompt_args),
                CommercialStrategyModel,
            )
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Commercial strategy synthesis failed. This section will be missing."
            )
            return None


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
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Accessories synthesis failed. Using empty dict as fallback."
            )
            return {"accessories": {}}


class SingleGarmentBuilder:
    def __init__(self, context: RunContext, research_dossier: Dict[str, Any]):
        self.context = context
        self.dossier = research_dossier
        self.brief = context.enriched_brief
        self.logger = get_logger(self.__class__.__name__)
        # It builds its own prompt args, as it has unique requirements.
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
            return model.model_dump()
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
                ),
            }
            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.NARRATIVE_SETTING_PROMPT.format(**prompt_args),
                NarrativeSettingModel,
            )
            return model.model_dump()
        except MaxRetriesExceededError:
            self.logger.warning(
                "Narrative setting synthesis failed. This section will be missing."
            )
            return None
