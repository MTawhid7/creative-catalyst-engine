"""
This module contains the PipelineOrchestrator, which executes the final,
robust, multi-step synthesis pipeline.
"""

from catalyst.context import RunContext
from .base_processor import BaseProcessor
from ..utilities.logger import get_logger

# Import all processors for the final, definitive pipeline
from .processors.briefing import BriefDeconstructionProcessor, BriefEnrichmentProcessor
from .processors.synthesis import (
    WebResearchProcessor,  # <-- NEW
    ContextStructuringProcessor,
    ReportSynthesisProcessor,
    DirectKnowledgeSynthesisProcessor,
)
from .processors.reporting import FinalOutputGeneratorProcessor


class PipelineOrchestrator:
    """
    Manages the execution of the full pipeline, including the multi-step
    web synthesis path and the direct knowledge fallback path.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    async def run(self, context: RunContext):
        """Executes the full, final pipeline."""
        self.logger.info(f"--- PIPELINE STARTED for Run ID: {context.run_id} ---")

        try:
            # STAGE 1: Briefing (Always run)
            briefing_pipeline: list[BaseProcessor] = [
                BriefDeconstructionProcessor(),
                BriefEnrichmentProcessor(),
            ]
            for processor in briefing_pipeline:
                context = await self._run_step(processor, context)

            # STAGE 2: Primary Synthesis Path (Multi-step)
            primary_synthesis_pipeline: list[BaseProcessor] = [
                WebResearchProcessor(),
                ContextStructuringProcessor(),
                ReportSynthesisProcessor(),
            ]
            for processor in primary_synthesis_pipeline:
                context = await self._run_step(processor, context)

            # STAGE 3: DECISION POINT & Fallback
            if not context.final_report:
                self.logger.warning(
                    "Primary web synthesis path failed. Activating knowledge fallback."
                )
                fallback_processor = DirectKnowledgeSynthesisProcessor()
                context = await self._run_step(fallback_processor, context)

            # STAGE 4: Reporting
            if context.final_report:
                final_processor = FinalOutputGeneratorProcessor()
                context = await self._run_step(final_processor, context)
            else:
                self.logger.critical(
                    "All synthesis paths failed. Cannot generate a final report."
                )

        except Exception as e:
            self.logger.critical(
                f"Pipeline failed catastrophically: {e}", exc_info=True
            )
            self.logger.error("Debug artifacts for the run will be saved.")
        finally:
            self.logger.info("Attempting to save all debug artifacts...")
            try:
                context.save_artifacts()
                self.logger.info("Debug artifacts saved successfully.")
            except Exception:
                self.logger.critical(
                    "CRITICAL: Failed to save debug artifacts.", exc_info=True
                )
            self.logger.info(f"--- PIPELINE FINISHED for Run ID: {context.run_id} ---")

    async def _run_step(
        self, processor: BaseProcessor, context: RunContext
    ) -> RunContext:
        """Helper to run a single step and handle logging/artifacts."""
        step_name = processor.__class__.__name__
        self.logger.info(f"--- [START] Step: {step_name} ---")
        processed_context = await processor.process(context)
        self.logger.info(f"--- [END] Step: {step_name} ---")
        processed_context.record_artifact(step_name, processed_context.to_dict())
        return processed_context
