# catalyst/pipeline/synthesis_strategies/section_builders.py

"""
This module contains the self-contained, single-responsibility "Builder"
strategies for the report.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

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
)

logger = get_logger(__name__)


class BaseSectionBuilder(ABC):
    # ... (This class remains unchanged) ...
    def __init__(self, context: RunContext, research_dossier: Dict[str, Any]):
        self.context = context
        self.brief = context.enriched_brief
        self.dossier = research_dossier
        self.logger = get_logger(self.__class__.__name__)
        self.base_prompt_args = {
            "research_dossier": json.dumps(self.dossier, indent=2),
            "enriched_brief": json.dumps(self.brief, indent=2),
        }

    @abstractmethod
    async def build(self) -> Dict[str, Any] | None:
        pass


class NarrativeSynthesisBuilder(BaseSectionBuilder):
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
            self.logger.warning("Narrative synthesis failed.")
            return None


class CreativeAnalysisBuilder(BaseSectionBuilder):
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
            self.logger.warning("Consolidated creative analysis failed.")
            return {
                "cultural_drivers": [],
                "influential_models": [],
                "commercial_strategy_summary": "",
            }


class AccessoriesBuilder(BaseSectionBuilder):
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
            self.logger.warning("Accessories synthesis failed.")
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
        }

    async def build(
        self,
        previously_designed_garments: List[Dict[str, Any]],
        variation_seed_override: Optional[int] = None,
        specific_garment_override: Optional[str] = None,
    ) -> Dict[str, Any] | None:
        seed_to_use = (
            variation_seed_override
            if variation_seed_override is not None
            else self.context.variation_seed
        )

        self.logger.info(
            f"Synthesizing garment #{len(previously_designed_garments) + 1} with effective seed {seed_to_use}..."
        )

        try:
            if seed_to_use == 0:
                prompt_template = prompt_library.SINGLE_GARMENT_SYNTHESIS_PROMPT
                prompt_args = self.base_prompt_args.copy()
            else:
                prompt_template = prompt_library.VARIANT_GARMENT_SYNTHESIS_PROMPT
                prompt_args = self.base_prompt_args.copy()
                # --- START: DEFINITIVE FIX for TypeError ---
                # The prompt's .format() method expects string values. The integer
                # seed is converted to a string to prevent a TypeError.
                prompt_args["variation_seed"] = str(seed_to_use)
                # --- END: DEFINITIVE FIX ---

            prompt_args["previously_designed_garments"] = json.dumps(
                previously_designed_garments, indent=2
            )
            prompt_args["single_garment_schema"] = json.dumps(
                SingleGarmentModel.model_json_schema(), indent=2
            )
            prompt_args["specific_garment_to_design"] = (
                specific_garment_override
                or "None. You have the creative freedom to invent a suitable garment."
            )

            model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_template.format(**prompt_args),
                SingleGarmentModel,
                model_name=settings.GEMINI_PRO_MODEL_NAME,
            )
            return model.model_dump(mode="json")

        except MaxRetriesExceededError:
            self.logger.error(
                "Failed to synthesize a single garment after all retries."
            )
            return None
