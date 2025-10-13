# catalyst/pipeline/processors/synthesis.py

"""
This module contains the core processors for the synthesis stage of the pipeline.
"""

import asyncio
import json
import copy
from typing import Optional
from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ... import settings
from ...resilience import invoke_with_resilience, MaxRetriesExceededError

from ..synthesis_strategies.synthesis_models import ResearchDossierModel
from ..synthesis_strategies.section_builders import (
    NarrativeSynthesisBuilder,
    CreativeAnalysisBuilder,
    AccessoriesBuilder,
    SingleGarmentBuilder,
)
from ...utilities.config_loader import FORMATTED_SOURCES


class WebResearchProcessor(BaseProcessor):
    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("🌐 Starting strategic web research (using gemini-2.5-pro)...")
        prompt_args = {
            "user_passage": context.user_passage,
            "enriched_brief": json.dumps(context.enriched_brief, indent=2),
            "brand_ethos": context.brand_ethos or "No ethos provided.",
            "antagonist_synthesis": context.antagonist_synthesis
            or "No synthesis provided.",
            "curated_sources": FORMATTED_SOURCES,
            "dossier_schema": json.dumps(
                ResearchDossierModel.model_json_schema(), indent=2
            ),
        }
        try:
            dossier_model = await invoke_with_resilience(
                gemini.generate_content_async,
                prompt_library.STRATEGIC_RESEARCH_PROMPT.format(**prompt_args),
                ResearchDossierModel,
                model_name=settings.GEMINI_PRO_MODEL_NAME,
            )
            context.structured_research_context = dossier_model.model_dump(mode="json")
            self.logger.info(
                "✅ Successfully generated the professional research dossier."
            )
        except MaxRetriesExceededError:
            self.logger.critical(
                "❌ Dossier generation failed after all retries. Halting pipeline."
            )
            context.structured_research_context = {}
            raise
        return context


class ReportSynthesisProcessor(BaseProcessor):
    async def process(self, context: RunContext) -> RunContext:
        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Research dossier is empty. Skipping concurrent builders."
            )
            return context
        self.logger.info("🚀 Launching consolidated synthesis builders...")
        dossier = context.structured_research_context
        builders = [
            NarrativeSynthesisBuilder(context, dossier),
            CreativeAnalysisBuilder(context, dossier),
            AccessoriesBuilder(context, dossier),
        ]
        builder_tasks = [builder.build() for builder in builders]
        results = await asyncio.gather(*builder_tasks)
        self.logger.info("🤝 Assembling results from concurrent builders...")
        for result_dict in results:
            if result_dict:
                context.final_report.update(result_dict)
        return context


class KeyGarmentsProcessor(BaseProcessor):
    """
    Phase 3: Executes the dynamic, strategy-aware process of designing the key
    garments to match the user's specific request.
    """

    async def process(self, context: RunContext) -> RunContext:
        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Research dossier is empty. Skipping key garment generation."
            )
            return context

        self.logger.info("⚙️ Starting dynamic garment design process...")
        dossier = context.structured_research_context
        garment_builder = SingleGarmentBuilder(context, dossier)
        designed_garments = []

        strategy = context.enriched_brief.get("generation_strategy", "collection")
        self.logger.info(f"Executing garment generation with strategy: '{strategy}'")

        if strategy == "variations":
            for i in range(3):
                self.logger.info(f"Designing variation #{i+1} of 3...")
                current_history = copy.deepcopy(designed_garments)
                # FIX: Pass the first argument positionally
                garment_data = await garment_builder.build(
                    current_history,
                    variation_seed_override=i,
                    specific_garment_override=None,
                )
                if garment_data and "key_piece" in garment_data:
                    designed_garments.append(garment_data["key_piece"])
                else:
                    self.logger.error(f"❌ Failed to generate variation #{i+1}.")

        elif strategy == "specified_items":
            garments_to_design = context.enriched_brief.get("explicit_garments", [])
            for garment_name in garments_to_design:
                self.logger.info(f"Designing specified garment: '{garment_name}'...")
                current_history = copy.deepcopy(designed_garments)
                # FIX: Pass the first argument positionally
                garment_data = await garment_builder.build(
                    current_history,
                    variation_seed_override=None,
                    specific_garment_override=garment_name,
                )
                if garment_data and "key_piece" in garment_data:
                    designed_garments.append(garment_data["key_piece"])
                else:
                    self.logger.error(
                        f"❌ Failed to generate specified garment: '{garment_name}'."
                    )

        else:  # Default "collection" strategy
            for i in range(3):
                self.logger.info(f"Designing collection piece #{i+1} of 3...")
                current_history = copy.deepcopy(designed_garments)
                # FIX: Pass the first argument positionally
                garment_data = await garment_builder.build(
                    current_history,
                    variation_seed_override=i,
                    specific_garment_override=None,
                )
                if garment_data and "key_piece" in garment_data:
                    designed_garments.append(garment_data["key_piece"])
                else:
                    self.logger.error(f"❌ Failed to generate collection piece #{i+1}.")

        context.final_report["detailed_key_pieces"] = designed_garments
        return context
