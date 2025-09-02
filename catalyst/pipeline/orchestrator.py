# catalyst/pipeline/orchestrator.py

"""
This module contains the PipelineOrchestrator, which executes the final,
robust, multi-step synthesis pipeline with enhanced, readable logging and
a comprehensive, two-level caching strategy.
"""

import json
import shutil
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
from .processors.generation import get_image_generator


# --- START OF FIX ---
# The orchestrator is the manager of the pipeline, not a step within it.
# It should not inherit from BaseProcessor.
class PipelineOrchestrator:
    # --- END OF FIX ---
    """
    Manages the pipeline execution, including a high-level cache check,
    artifact restoration, intelligent fallback logic, and configurable
    feature flags for expensive steps.
    """

    def __init__(self):
        # We can't use super() here anymore as there is no parent class.
        self.logger = get_logger(self.__class__.__name__)

    async def run(self, context: RunContext) -> bool:
        """
        Executes the full pipeline. Returns a boolean indicating if the result
        was successfully served from cache.
        """
        self.logger.info(f"▶️ PIPELINE START | Run ID: {context.run_id}")
        is_from_cache = False

        try:
            # STAGE 1: BRIEFING (Always runs to get a stable cache key)
            briefing_pipeline: list[BaseProcessor] = [
                BriefDeconstructionProcessor(),
                EthosClarificationProcessor(),
                BriefEnrichmentProcessor(),
            ]
            for processor in briefing_pipeline:
                context = await self._run_step(processor, context)

            # STAGE 2: CACHE CHECK & ARTIFACT RESTORATION
            self.logger.info(
                "⚙️ Caching: Checking L0/L1 cache for completed report and images..."
            )
            cached_payload_json = await cache_manager.check_report_cache_async(
                context.enriched_brief
            )

            if cached_payload_json:
                self.logger.warning(
                    "🎯 CACHE HIT! Payload found. Attempting to restore artifacts."
                )
                cached_payload = json.loads(cached_payload_json)
                cached_folder_name = cached_payload.get("cached_results_path")

                if cached_folder_name:
                    source_path = settings.ARTIFACT_CACHE_DIR / cached_folder_name
                    dest_path = context.results_dir

                    if source_path.exists() and source_path.is_dir():
                        self.logger.info(
                            f"Copying cached artifacts from '{source_path}' to '{dest_path}'..."
                        )
                        try:
                            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                            context.final_report = cached_payload.get(
                                "final_report", {}
                            )
                            self.logger.info(
                                "✅ Successfully restored all artifacts from cache."
                            )
                            is_from_cache = True
                            return is_from_cache
                        except Exception as e:
                            self.logger.error(
                                f"❌ Failed to copy cached artifacts: {e}",
                                exc_info=True,
                            )
                            self.logger.warning(
                                "⚠️ Proceeding with full regeneration due to copy failure."
                            )
                    else:
                        self.logger.warning(
                            f"⚠️ Cached artifact path '{source_path}' does not exist. Regenerating."
                        )
                else:
                    self.logger.warning(
                        "⚠️ Cache payload is missing artifact path. Regenerating."
                    )

            # STAGES 3 & 4: SYNTHESIS (Runs only on cache miss or restoration failure)
            self.logger.info(
                "💨 CACHE MISS or invalid cache. Proceeding with full synthesis."
            )
            primary_synthesis_pipeline: list[BaseProcessor] = [
                WebResearchProcessor(),
                ContextStructuringProcessor(),
                ReportSynthesisProcessor(),
            ]
            for processor in primary_synthesis_pipeline:
                context = await self._run_step(processor, context)

            if not context.final_report:
                self.logger.warning(
                    "⚠️ Primary synthesis path failed. Activating Direct Knowledge Fallback."
                )
                fallback_processor = DirectKnowledgeSynthesisProcessor()
                context = await self._run_step(fallback_processor, context)

            # STAGES 5 & 6: FINAL OUTPUT GENERATION (Runs only on cache miss)
            if context.final_report:
                final_processor = FinalOutputGeneratorProcessor()
                context = await self._run_step(final_processor, context)

                if settings.ENABLE_IMAGE_GENERATION:
                    self.logger.info(
                        f"🚀 Initializing '{settings.IMAGE_GENERATION_MODEL}' image generator..."
                    )
                    image_generator = get_image_generator()
                    self.logger.info(
                        f"--- ▶️ START: {image_generator.__class__.__name__} ---"
                    )
                    context = await image_generator.generate_images(context)
                    self.logger.info(
                        f"--- ✅ END: {image_generator.__class__.__name__} ---"
                    )
                else:
                    self.logger.warning(
                        "⚠️ Image generation is disabled via settings. Skipping."
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

        return is_from_cache

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
        try:
            processed_context.record_artifact(step_name, processed_context.to_dict())
        except Exception as e:
            self.logger.warning(
                f"⚠️ Could not record artifact for step {step_name} due to a serialization error: {e}"
            )
        return processed_context
