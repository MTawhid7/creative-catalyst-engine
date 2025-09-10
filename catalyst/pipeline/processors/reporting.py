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
            # 1. Validate the report data FIRST.
            validated_report = FashionTrendReport.model_validate(context.final_report)
            self.logger.info(
                "🎨 Report data validated. Initializing prompt generation strategy..."
            )

            # 2. Generate the prompts.
            prompt_generator = PromptGenerator(report=validated_report)
            prompts_data = await prompt_generator.generate_prompts()

            # 3. (NEW) Inject the generated prompts back into the main report dictionary.
            self.logger.info("💉 Injecting image prompts into the final report...")
            for piece in context.final_report.get("detailed_key_pieces", []):
                piece_name = piece.get("key_piece_name")
                if piece_name and piece_name in prompts_data:
                    piece_prompts = prompts_data[piece_name]
                    piece["mood_board_prompt"] = piece_prompts.get("mood_board")
                    piece["final_garment_prompt"] = piece_prompts.get("final_garment")
            self.logger.info("✅ Successfully injected prompts.")

            # 4. Save the generated prompts as a separate artifact (still useful for debugging).
            self._save_json_file(
                data=prompts_data,
                filename=settings.PROMPTS_FILENAME,
                context=context,
            )

        except ValidationError:
            self.logger.error(
                "❌ Could not generate or inject prompts due to a validation error in the final report data.",
                exc_info=True,
            )
            # We will still save the main report, but it will be missing the prompts.
        except Exception:
            self.logger.error(
                "❌ An unexpected error occurred during prompt generation or injection.",
                exc_info=True,
            )

        # 5. (MOVED) Save the primary trend report artifact LAST.
        # This ensures it now contains the newly injected prompt fields.
        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        # --- END: LOGIC RE-ORDERING AND INJECTION ---

        self.logger.info("✅ Success: All reporting outputs have been generated.")
        return context
