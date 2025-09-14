# catalyst/pipeline/processors/reporting.py

import json
from pathlib import Path
from pydantic import ValidationError

from ...context import RunContext
from ..base_processor import BaseProcessor
from ... import settings
from ...models.trend_report import FashionTrendReport
from ..prompt_engineering.prompt_generator import PromptGenerator


class FinalOutputGeneratorProcessor(BaseProcessor):
    """
    Generates and saves all final output files, including the main JSON
    report and the generated image prompts. This version is hardened to
    ensure the output directory exists before writing files.
    """

    def _save_json_file(self, data: dict, filename: str, context: RunContext):
        """A helper function to save a dictionary to a JSON file."""
        try:
            output_path = context.results_dir / filename
            self.logger.info(f"💾 Saving data to '{output_path}'...")

            # --- START: DEFINITIVE FILE NOT FOUND FIX ---
            # Ensure the parent directory exists before attempting to write the file.
            # This is the crucial fix for the FileNotFoundError.
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # --- END: DEFINITIVE FILE NOT FOUND FIX ---

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"✅ Successfully saved file: {filename}")

        except (IOError, TypeError) as e:
            # Catching specific errors is better than a generic Exception.
            self.logger.error(
                f"❌ Failed to save JSON file '{filename}'", exc_info=True
            )
            # We don't re-raise here to allow the process to continue if possible.

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the creation, merging, and saving of all final report files."""
        self.logger.info("⚙️ Starting final report and prompt generation...")

        if not context.final_report:
            self.logger.critical(
                "❌ Final report data is missing. Halting report generation."
            )
            raise ValueError("Cannot generate outputs without a final report.")

        # This top-level directory creation is still useful, but the
        # mkdir call in _save_json_file is the definitive fix.
        try:
            final_dir = Path(context.results_dir)
            final_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.critical(
                f"❌ Could not create output directory {context.results_dir}: {e}",
                exc_info=True,
            )
            raise

        try:
            validated_report = FashionTrendReport.model_validate(context.final_report)
            self.logger.info(
                "🎨 Report data validated. Initializing prompt generation strategy..."
            )

            prompt_generator = PromptGenerator(report=validated_report)
            prompts_data = await prompt_generator.generate_prompts()

            self.logger.info("💉 Injecting image prompts into the final report...")
            for piece in context.final_report.get("detailed_key_pieces", []):
                piece_name = piece.get("key_piece_name")
                if piece_name and piece_name in prompts_data:
                    piece_prompts = prompts_data[piece_name]
                    piece["mood_board_prompt"] = piece_prompts.get("mood_board")
                    piece["final_garment_prompt"] = piece_prompts.get("final_garment")
            self.logger.info("✅ Successfully injected prompts.")

            self._save_json_file(
                data=prompts_data,
                filename=settings.PROMPTS_FILENAME,
                context=context,
            )
        except ValidationError:
            self.logger.error(
                "❌ Could not generate or inject prompts due to a validation error.",
                exc_info=True,
            )
        except Exception:
            self.logger.error(
                "❌ An unexpected error occurred during prompt generation or injection.",
                exc_info=True,
            )

        # Save the primary trend report artifact LAST.
        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        self.logger.info("✅ Success: All reporting outputs have been generated.")
        return context
