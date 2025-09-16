# catalyst/pipeline/orchestrator.py

"""
This module contains the PipelineOrchestrator, which executes the final,
robust, multi-step synthesis pipeline with enhanced, readable logging and
granular, stage-aware exception handling.
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


class PipelineOrchestrator:
    """
    Manages the pipeline execution with a two-level caching strategy and
    stage-specific exception handling to maximize resilience.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def _run_step(
        self, processor: BaseProcessor, context: RunContext
    ) -> RunContext:
        """
        Helper to run a single processor, handling logging, artifact recording,
        and re-raising exceptions for the main loop to handle.
        """
        step_name = processor.__class__.__name__

        # --- START: GRANULAR STATUS UPDATE ---
        # Update the context with a human-readable status before each step.
        # This message will be published to Redis by the worker.
        context.current_status = f"Running: {step_name}"
        # --- END: GRANULAR STATUS UPDATE ---

        self.logger.info(f"--- ▶️ START: {step_name} ---")
        try:
            processed_context = await processor.process(context)
            self.logger.info(f"--- ✅ END: {step_name} ---")
            processed_context.record_artifact(step_name, processed_context.to_dict())
            return processed_context
        except Exception:
            # Log the specific step that failed and then propagate the exception.
            self.logger.error(f"--- ❌ FAILED: {step_name} ---", exc_info=True)
            raise

    async def run(self, context: RunContext) -> bool:
        """
        Executes the full pipeline with granular error handling at each stage.
        Returns a boolean indicating if the result was served from cache.
        """
        self.logger.info(f"▶️ PIPELINE START | Run ID: {context.run_id}")
        is_from_cache = False

        try:
            # --- STAGE 1: BRIEFING (CRITICAL) ---
            context.current_status = "Phase 1: Creative Briefing"
            briefing_pipeline: list[BaseProcessor] = [
                BriefDeconstructionProcessor(),
                EthosClarificationProcessor(),
                BriefEnrichmentProcessor(),
            ]
            for processor in briefing_pipeline:
                context = await self._run_step(processor, context)

            # --- STAGE 2: CACHE CHECK & ARTIFACT RESTORATION ---
            context.current_status = "Phase 2: Checking Semantic Cache"
            try:
                cached_payload_json = await cache_manager.check_report_cache_async(
                    context.enriched_brief
                )
                if cached_payload_json:
                    self.logger.warning(
                        "🎯 L1 CACHE HIT! Payload found. Attempting to restore artifacts."
                    )
                    cached_payload = json.loads(cached_payload_json)
                    cached_folder_name = cached_payload.get("cached_results_path")
                    if cached_folder_name:
                        source_path = settings.ARTIFACT_CACHE_DIR / cached_folder_name
                        dest_path = context.results_dir
                        if source_path.exists() and source_path.is_dir():
                            context.current_status = "Restoring from cache..."
                            self.logger.info(
                                f"Restoring artifacts from '{source_path}' to '{dest_path}'..."
                            )
                            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                            context.final_report = cached_payload.get(
                                "final_report", {}
                            )
                            self.logger.info(
                                "✅ Successfully restored all artifacts from cache."
                            )
                            is_from_cache = True
                            return is_from_cache
                        else:
                            self.logger.warning(
                                f"⚠️ Cached artifact path '{source_path}' does not exist. Regenerating."
                            )
                    else:
                        self.logger.warning(
                            "⚠️ Cache payload is missing artifact path. Regenerating."
                        )
            except Exception as e:
                self.logger.warning(
                    f"⚠️ L1 Cache check or restoration failed: {e}. Proceeding with full regeneration.",
                    exc_info=True,
                )

            # --- STAGE 3: SYNTHESIS (CRITICAL, WITH FALLBACK) ---
            context.current_status = "Phase 3: Synthesis"
            self.logger.info("💨 L1 CACHE MISS. Proceeding with full synthesis.")
            try:
                synthesis_pipeline: list[BaseProcessor] = [
                    WebResearchProcessor(),
                    ContextStructuringProcessor(),
                    ReportSynthesisProcessor(),
                ]
                for processor in synthesis_pipeline:
                    context = await self._run_step(processor, context)

                if not context.final_report:
                    self.logger.warning(
                        "⚠️ Primary synthesis path failed to produce a report. Activating Direct Knowledge Fallback."
                    )
                    fallback_processor = DirectKnowledgeSynthesisProcessor()
                    context = await self._run_step(fallback_processor, context)

            except Exception as e:
                self.logger.critical(
                    f"❌ A catastrophic, unrecoverable error occurred during the synthesis stage: {e}",
                    exc_info=True,
                )

            # --- STAGE 4: FINAL OUTPUT GENERATION (NON-CRITICAL) ---
            if context.final_report:
                context.current_status = "Phase 4: Finalizing Output"
                try:
                    final_output_pipeline: list[BaseProcessor] = [
                        FinalOutputGeneratorProcessor()
                    ]
                    if settings.ENABLE_IMAGE_GENERATION:
                        context.current_status = "Phase 5: Generating Images"
                        final_output_pipeline.append(get_image_generator())
                    else:
                        self.logger.warning(
                            "⚠️ Image generation is disabled via settings. Skipping."
                        )

                    for processor in final_output_pipeline:
                        context = await self._run_step(processor, context)
                except Exception as e:
                    self.logger.error(
                        f"❌ Final output generation failed, but the core report was created successfully: {e}",
                        exc_info=True,
                    )

        except Exception as e:
            self.logger.critical(
                f"❌ PIPELINE HALTED due to a critical, unrecoverable error in a core stage: {e}",
                exc_info=True,
            )

        finally:
            context.current_status = "Finishing..."
            self.logger.info("⚙️ Saving all debug artifacts for the run...")
            try:
                context.save_artifacts()
                self.logger.info("✅ Success: Debug artifacts saved successfully.")
            except Exception:
                self.logger.critical(
                    "❌ CRITICAL: Failed to save debug artifacts.", exc_info=True
                )

            if not context.final_report and not is_from_cache:
                self.logger.critical(
                    "❌ PIPELINE FINISHED BUT PRODUCED AN EMPTY REPORT. THIS IS A CRITICAL FAILURE."
                )
                raise RuntimeError(
                    "Pipeline finished but produced an empty final report."
                )

            self.logger.info(f"⏹️ PIPELINE FINISHED | Run ID: {context.run_id}")
            # --- START: GRANULAR STATUS UPDATE ---
            # Signal that the pipeline is complete.
            context.is_complete = True
            # --- END: GRANULAR STATUS UPDATE ---

        return is_from_cache
