# catalyst/pipeline/processors/synthesis.py

"""
This module contains the core processors for the synthesis stage of the pipeline.
This version is refactored for efficiency by consolidating multiple analytical
builders into a single, powerful step.
"""

import asyncio
import json
from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ... import settings
from ...resilience import invoke_with_resilience, MaxRetriesExceededError

# --- START: THE DEFINITIVE, CONSOLIDATED REFACTOR ---
# Import the new consolidated builder and remove the old ones
from ..synthesis_strategies.synthesis_models import ResearchDossierModel
from ..synthesis_strategies.section_builders import (
    NarrativeSynthesisBuilder,
    CreativeAnalysisBuilder,  # New
    AccessoriesBuilder,
    NarrativeSettingBuilder,
    SingleGarmentBuilder,
)

# --- END: THE DEFINITIVE, CONSOLIDATED REFACTOR ---
from ...utilities.config_loader import FORMATTED_SOURCES


class WebResearchProcessor(BaseProcessor):
    """
    Phase 1: Executes a comprehensive, multi-vector search to produce a
    structured, fact-based ResearchDossier.
    """

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
    """
    Phase 2: Orchestrates the creative synthesis of the report using a more
    efficient, consolidated set of concurrent builder tasks.
    """

    async def process(self, context: RunContext) -> RunContext:
        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Research dossier is empty. Skipping concurrent builders."
            )
            return context

        self.logger.info("🚀 Launching consolidated synthesis builders...")
        dossier = context.structured_research_context

        # --- START: THE DEFINITIVE, CONSOLIDATED REFACTOR ---
        # The list of builders is now shorter and more efficient (4 calls instead of 6).
        builders = [
            NarrativeSynthesisBuilder(context, dossier),
            CreativeAnalysisBuilder(context, dossier),  # The new, efficient builder
            AccessoriesBuilder(context, dossier),
            NarrativeSettingBuilder(context, dossier),
        ]
        # --- END: THE DEFINITIVE, CONSOLIDATED REFACTOR ---

        builder_tasks = [builder.build() for builder in builders]
        results = await asyncio.gather(*builder_tasks)

        self.logger.info("🤝 Assembling results from concurrent builders...")
        for result_dict in results:
            if result_dict:
                context.final_report.update(result_dict)

        return context


class KeyGarmentsProcessor(BaseProcessor):
    """
    Phase 3: Executes the sequential, iterative process of designing the key
    garments, ensuring a cohesive final collection.
    """

    async def process(self, context: RunContext) -> RunContext:
        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Research dossier is empty. Skipping key garment generation."
            )
            return context

        self.logger.info(" sequential garment design process...")
        dossier = context.structured_research_context
        garment_builder = SingleGarmentBuilder(context, dossier)

        designed_garments = []
        for i in range(3):
            self.logger.info(f"Designing garment #{i+1} of 3...")
            garment_data = await garment_builder.build(designed_garments)
            if garment_data and "key_piece" in garment_data:
                designed_garments.append(garment_data["key_piece"])
                self.logger.info(f"✅ Successfully designed garment #{i+1}.")
            else:
                self.logger.error(
                    f"❌ Failed to generate garment #{i+1}. The collection may be incomplete."
                )

        context.final_report["detailed_key_pieces"] = designed_garments
        return context
