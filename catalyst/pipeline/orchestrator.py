# catalyst/pipeline/orchestrator.py

"""
This module contains the PipelineOrchestrator, which executes the final,
robust, and now more efficient multi-step synthesis pipeline.
"""

import json
import asyncio
import shutil  # <-- Import shutil
from catalyst.context import RunContext
from catalyst.pipeline.synthesis_strategies.report_assembler import ReportAssembler
from .base_processor import BaseProcessor
from ..utilities.logger import get_logger
from ..caching import cache_manager
from .. import settings

from .processors.briefing import (
    BriefDeconstructionProcessor,
    ConsolidatedBriefingProcessor,
    CreativeAntagonistProcessor,
)
from .processors.synthesis import (
    WebResearchProcessor,
    ReportSynthesisProcessor,
    KeyGarmentsProcessor,
)
from .processors.reporting import FinalOutputGeneratorProcessor
from .processors.generation import get_image_generator


class PipelineOrchestrator:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def _run_step(
        self, processor: BaseProcessor, context: RunContext
    ) -> RunContext:
        step_name = processor.__class__.__name__
        context.current_status = f"Running: {step_name}"
        self.logger.info(f"--- ▶️ START: {step_name} ---")
        try:
            processed_context = await processor.process(context)
            self.logger.info(f"--- ✅ END: {step_name} ---")
            processed_context.record_artifact(step_name, processed_context.to_dict())
            return processed_context
        except Exception:
            self.logger.error(f"--- ❌ FAILED: {step_name} ---", exc_info=True)
            raise

    async def run(self, context: RunContext) -> bool:
        """
        Executes the full pipeline with a graceful failure model.
        Returns a boolean indicating if the result was served from cache.
        """
        self.logger.info(
            f"▶️ PIPELINE START | Run ID: {context.run_id} | Seed: {context.variation_seed}"
        )
        is_from_cache = False

        try:
            # --- STAGE 1: BRIEFING ---
            context.current_status = "Phase 1: Creative Briefing"
            context = await self._run_step(BriefDeconstructionProcessor(), context)
            context = await self._run_step(ConsolidatedBriefingProcessor(), context)
            context = await self._run_step(CreativeAntagonistProcessor(), context)

            # --- STAGE 2: CACHE CHECK ---
            context.current_status = "Phase 2: Checking Semantic Cache"

            cached_payload_json = None
            if context.variation_seed == 0:
                self.logger.info("Variation seed is 0. Checking L1 semantic cache...")
                cached_payload_json = await cache_manager.check_report_cache_async(
                    context.enriched_brief, context.variation_seed
                )
            else:
                self.logger.info(
                    f"Variation seed is {context.variation_seed}. Bypassing L1 semantic cache to generate a new variation."
                )

            if cached_payload_json:
                self.logger.warning("🎯 L1 CACHE HIT! Restoring from cache.")
                cached_payload = json.loads(cached_payload_json)
                context.final_report = cached_payload.get("final_report", {})
                is_from_cache = True

                # --- START: THE DEFINITIVE ARTIFACT RESTORATION FIX ---
                # When a cache hit occurs, we must restore the physical artifacts
                # (images, etc.) from the permanent artifact_cache into the
                # current run's temporary directory so they can be served.
                cached_artifact_path_id = cached_payload.get("cached_results_path")
                if cached_artifact_path_id:
                    source_path = settings.ARTIFACT_CACHE_DIR / cached_artifact_path_id
                    dest_path = context.results_dir
                    if source_path.exists():
                        self.logger.info(
                            f"Restoring artifacts from '{source_path}' to '{dest_path}'..."
                        )
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                        self.logger.info("✅ Artifact restoration complete.")
                    else:
                        self.logger.error(
                            f"❌ Cached artifact path not found: {source_path}"
                        )
                else:
                    self.logger.warning(
                        "⚠️ Cache payload is missing 'cached_results_path'. Cannot restore artifacts."
                    )
                # --- END: THE DEFINITIVE ARTIFACT RESTORATION FIX ---

                return is_from_cache  # Now we can safely return

            # --- STAGE 3: SYNTHESIS ---
            context.current_status = "Phase 3: Research & Synthesis"
            self.logger.info("💨 L1 CACHE MISS. Proceeding with full synthesis.")
            context = await self._run_step(WebResearchProcessor(), context)
            context = await self._run_step(ReportSynthesisProcessor(), context)
            context = await self._run_step(KeyGarmentsProcessor(), context)

            assembler = ReportAssembler(context)
            final_report_dict = assembler._finalize_and_validate_report(
                context.final_report
            )
            if final_report_dict:
                context.final_report = final_report_dict
            else:
                raise RuntimeError(
                    "The final assembled report failed Pydantic validation."
                )

            # --- STAGE 4: FINAL OUTPUT GENERATION ---
            context.current_status = "Phase 4: Finalizing Output"
            try:
                output_processors: list[BaseProcessor] = [
                    FinalOutputGeneratorProcessor()
                ]
                if settings.ENABLE_IMAGE_GENERATION:
                    context.current_status = "Phase 5: Generating Images"
                    output_processors.append(get_image_generator())
                for processor in output_processors:
                    context = await self._run_step(processor, context)
            except Exception as e:
                self.logger.error(
                    f"❌ Non-critical final output generation failed: {e}",
                    exc_info=True,
                )

        except Exception as e:
            self.logger.critical(
                f"❌ PIPELINE HALTED due to a critical, unrecoverable error.",
                exc_info=True,
            )
            raise

        finally:
            context.current_status = "Finishing..."
            self.logger.info("⚙️ Saving all debug artifacts for the run...")
            try:
                context.save_artifacts()
                context.save_dossier_artifact()
            except Exception as e:
                self.logger.critical(
                    "❌ CRITICAL: Failed to save debug artifacts.", exc_info=True
                )
            self.logger.info(f"⏹️ PIPELINE FINISHED | Run ID: {context.run_id}")
            context.is_complete = True

        return is_from_cache
