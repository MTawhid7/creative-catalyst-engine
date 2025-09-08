# catalyst/pipeline/processors/reporting.py

"""
This module contains the processor for the final reporting stage.

The FinalOutputGeneratorProcessor acts as a controller that orchestrates the
creation and saving of all final output files. It delegates the complex,
creative task of prompt generation to the specialized PromptGenerator strategy,
adhering to the Single Responsibility Principle.
"""

import json
from pathlib import Path
from pydantic import ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ... import settings
from ...models.trend_report import FashionTrendReport
from ..prompt_engineering.prompt_generator import PromptGenerator


class FinalOutputGeneratorProcessor(BaseProcessor):
    """
    Generates and saves all final output files, including the main JSON
    report and the generated image prompts.
    """

    def _save_json_file(self, data: dict, filename: str, context: RunContext):
        """A helper function to save a dictionary to a JSON file."""
        try:
            output_path = Path(context.results_dir) / filename
            self.logger.info(f"💾 Saving data to '{output_path}'...")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"✅ Successfully saved file: {filename}")
        except (IOError, TypeError) as e:
            self.logger.error(
                f"❌ Failed to save JSON file '{filename}'", exc_info=True
            )
            raise  # Re-raise to signal a critical failure in the pipeline

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the creation and saving of all final report files."""
        self.logger.info("⚙️ Starting final report and prompt generation...")

        if not context.final_report:
            self.logger.critical(
                "❌ Final report data is missing. Halting report generation."
            )
            raise ValueError("Cannot generate outputs without a final report.")

        try:
            final_dir = Path(context.results_dir)
            final_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.critical(
                f"❌ Could not create output directory {context.results_dir}: {e}",
                exc_info=True,
            )
            raise

        # 1. Save the primary trend report artifact.
        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        # 2. Delegate prompt generation to the specialized PromptGenerator.
        try:
            # First, validate the raw report dictionary into a Pydantic model.
            # This ensures the PromptGenerator receives clean, structured data.
            validated_report = FashionTrendReport.model_validate(context.final_report)
            self.logger.info(
                "🎨 Report data validated. Initializing prompt generation strategy..."
            )

            prompt_generator = PromptGenerator(
                report=validated_report,
                brand_ethos=context.brand_ethos,
                enriched_brief=context.enriched_brief,
            )
            prompts_data = await prompt_generator.generate_prompts()

            # Record the prompts for debugging and potential reuse.
            context.record_artifact(self.__class__.__name__, {"prompts": prompts_data})

            # 3. Save the generated prompts artifact.
            self._save_json_file(
                data=prompts_data,
                filename=settings.PROMPTS_FILENAME,
                context=context,
            )
            self.logger.info("✅ Success: Image prompt generation and saving complete.")

        except ValidationError:
            self.logger.error(
                "❌ Could not generate prompts due to a validation error in the final report data.",
                exc_info=True,
            )
        except Exception:
            self.logger.error(
                "❌ An unexpected error occurred during prompt generation.",
                exc_info=True,
            )

        self.logger.info("✅ Success: All reporting outputs have been generated.")
        return context
