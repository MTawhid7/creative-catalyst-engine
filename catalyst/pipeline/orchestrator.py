"""
This module contains the PipelineOrchestrator, which executes the final,
robust, multi-step synthesis pipeline with enhanced, readable logging and
configurable feature flags.
"""

import json
from catalyst.context import RunContext
from .base_processor import BaseProcessor
from ..utilities.logger import get_logger
from ..caching import cache_manager
from .. import settings

# Import all processors
from .processors.briefing import (
    BriefDeconstructionProcessor,
    EthosClarificationProcessor,
    BriefEnrichmentProcessor,
)
from .processors.synthesis import (
    WebResearchProcessor,
    ContextStructuringProcessor,
    ReportSynthesisProcessor,
    DirectKnowledgeSynthesisProcessor,
)
from .processors.reporting import FinalOutputGeneratorProcessor
from .processors.generation import DalleImageGenerationProcessor


class PipelineOrchestrator:
    """
    Manages the pipeline execution, including a high-level cache check,
    intelligent fallback logic, and configurable feature flags for expensive steps.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def run(self, context: RunContext):
        """Executes the full, final pipeline with all architectural improvements."""
        self.logger.info(f"▶️ PIPELINE START | Run ID: {context.run_id}")

        try:
            # STAGE 1: BRIEFING
            # Deconstructs the user's input into a rich, structured brief.
            briefing_pipeline: list[BaseProcessor] = [
                BriefDeconstructionProcessor(),
                EthosClarificationProcessor(),
                BriefEnrichmentProcessor(),
            ]
            for processor in briefing_pipeline:
                context = await self._run_step(processor, context)

            # STAGE 2: L1 CACHE CHECK
            # Checks for a semantically similar report to avoid re-running the expensive synthesis.
            self.logger.info(
                "⚙️ Caching: Checking L1 Report Cache for completed report..."
            )
            cached_report_json = await cache_manager.check_report_cache_async(
                context.enriched_brief
            )

            if cached_report_json:
                self.logger.warning(
                    "🎯 L1 CACHE HIT! Bypassing synthesis pipeline. A similar report was found."
                )
                context.final_report = json.loads(cached_report_json)
            else:
                self.logger.info(
                    "💨 L1 CACHE MISS. Proceeding with full synthesis pipeline."
                )

                # STAGE 3: PRIMARY SYNTHESIS PATH
                # The main path: web research -> structure -> synthesize.
                primary_synthesis_pipeline: list[BaseProcessor] = [
                    WebResearchProcessor(),
                    ContextStructuringProcessor(),
                    ReportSynthesisProcessor(),
                ]
                for processor in primary_synthesis_pipeline:
                    context = await self._run_step(processor, context)

                # STAGE 4: DECISION POINT & FALLBACK
                # If the primary path fails to produce a report, activate the fallback.
                if not context.final_report:
                    self.logger.warning(
                        "⚠️ Primary synthesis path failed. Activating Direct Knowledge Fallback."
                    )
                    fallback_processor = DirectKnowledgeSynthesisProcessor()
                    context = await self._run_step(fallback_processor, context)

                # After a successful synthesis, add the new report to the cache for future use.
                if context.final_report:
                    self.logger.info(
                        "⚙️ Caching: Adding newly synthesized report to L1 cache..."
                    )
                    await cache_manager.add_to_report_cache_async(
                        context.enriched_brief, context.final_report
                    )

            # STAGE 5 & 6: FINAL OUTPUT GENERATION
            if context.final_report:
                # Always generate the JSON files and prompts.
                final_processor = FinalOutputGeneratorProcessor()
                context = await self._run_step(final_processor, context)

                # Conditionally run the expensive image generation step based on the feature flag.
                if settings.ENABLE_IMAGE_GENERATION:
                    image_gen_processor = DalleImageGenerationProcessor()
                    context = await self._run_step(image_gen_processor, context)
                else:
                    self.logger.warning(
                        "⚠️ Image generation is disabled via settings. Skipping DALL-E step."
                    )
            else:
                self.logger.critical(
                    "❌ CRITICAL: All synthesis paths failed. Cannot generate a final report."
                )

        except Exception as e:
            self.logger.critical(
                f"❌ PIPELINE FAILED: A critical, unhandled exception occurred: {e}",
                exc_info=True,
            )
            self.logger.error("⚠️ Debug artifacts for the run will be saved.")
        finally:
            self.logger.info("⚙️ Saving all debug artifacts for the run...")
            try:
                context.save_artifacts()
                self.logger.info("✅ Success: Debug artifacts saved successfully.")
            except Exception:
                self.logger.critical(
                    "❌ CRITICAL: Failed to save debug artifacts.", exc_info=True
                )
            self.logger.info(f"⏹️ PIPELINE FINISHED | Run ID: {context.run_id}")

    async def _run_step(
        self, processor: BaseProcessor, context: RunContext
    ) -> RunContext:
        """
        Helper method to run a single processor and handle logging and artifact recording.
        """
        step_name = processor.__class__.__name__
        self.logger.info(f"--- ▶️ START: {step_name} ---")
        processed_context = await processor.process(context)
        self.logger.info(f"--- ✅ END: {step_name} ---")

        # --- START OF IMPROVEMENT: ROBUST ARTIFACT RECORDING ---
        # This ensures that a failure to serialize artifacts does not crash the entire pipeline.
        try:
            processed_context.record_artifact(step_name, processed_context.to_dict())
        except Exception as e:
            self.logger.warning(
                f"⚠️ Could not record artifact for step {step_name} due to a serialization error: {e}"
            )
        # --- END OF IMPROVEMENT ---

        return processed_context
