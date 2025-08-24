"""
This module contains the PipelineOrchestrator, which executes the final,
robust, multi-step synthesis pipeline with enhanced, readable logging.
"""

import json
from catalyst.context import RunContext
from .base_processor import BaseProcessor
from ..utilities.logger import get_logger
from ..caching import cache_manager

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


class PipelineOrchestrator:
    """
    Manages the pipeline execution, including a high-level cache check
    and intelligent fallback logic, with clear, structured logging.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def run(self, context: RunContext):
        """Executes the full, final pipeline with all architectural improvements."""
        self.logger.info(f"▶️ PIPELINE START | Run ID: {context.run_id}")

        try:
            # STAGE 1: BRIEFING (NOW WITH ETHOS CLARIFICATION)
            briefing_pipeline: list[BaseProcessor] = [
                BriefDeconstructionProcessor(),
                EthosClarificationProcessor(),
                BriefEnrichmentProcessor(),
            ]
            for processor in briefing_pipeline:
                context = await self._run_step(processor, context)

            # STAGE 2: L1 CACHE CHECK
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
                    "💨 ... L1 CACHE MISS. Proceeding with full synthesis pipeline."
                )

                # STAGE 3: PRIMARY SYNTHESIS PATH
                primary_synthesis_pipeline: list[BaseProcessor] = [
                    WebResearchProcessor(),
                    ContextStructuringProcessor(),
                    ReportSynthesisProcessor(),
                ]
                for processor in primary_synthesis_pipeline:
                    context = await self._run_step(processor, context)

                # STAGE 4: DECISION POINT & FALLBACK
                if not context.final_report:
                    self.logger.warning(
                        "⚠️ Primary synthesis path failed. Activating Direct Knowledge Fallback."
                    )
                    fallback_processor = DirectKnowledgeSynthesisProcessor()
                    context = await self._run_step(fallback_processor, context)

                # After a successful synthesis (either primary or fallback), add the new report to the cache.
                if context.final_report:
                    self.logger.info(
                        "⚙️ Caching: Adding newly synthesized report to L1 cache..."
                    )
                    await cache_manager.add_to_report_cache_async(
                        context.enriched_brief, context.final_report
                    )

            # STAGE 5: REPORTING
            if context.final_report:
                final_processor = FinalOutputGeneratorProcessor()
                context = await self._run_step(final_processor, context)
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
        """Helper method to run a single processor and handle logging/artifacts."""
        step_name = processor.__class__.__name__
        self.logger.info(f"--- ▶️ START: {step_name} ---")
        processed_context = await processor.process(context)
        self.logger.info(f"--- ✅ END: {step_name} ---")
        processed_context.record_artifact(step_name, processed_context.to_dict())
        return processed_context
