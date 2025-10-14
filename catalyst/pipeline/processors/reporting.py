# catalyst/pipeline/processors/reporting.py

import json
from pathlib import Path
from pydantic import ValidationError

from ...context import RunContext
from ..base_processor import BaseProcessor
from ... import settings
from ...models.trend_report import FashionTrendReport, PromptMetadata
from ..prompt_engineering.prompt_generator import PromptGenerator


# --- START: ASSEMBLER REFACTOR ---
class FinalValidationProcessor(BaseProcessor):
    """
    A dedicated pipeline step that injects final metadata and performs a
    rigorous Pydantic validation on the complete report object before any
    files are written. This is the final quality gate.
    """

    def _normalize_lists(self, report_data: dict) -> dict:
        """
        Explicitly normalizes fields that should be lists but might be returned
        as single values by the AI to prevent validation errors.
        """
        for key in ["season", "year", "region"]:
            if (
                key in report_data
                and report_data[key]
                and not isinstance(report_data[key], list)
            ):
                report_data[key] = [report_data[key]]
        return report_data

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Performing final validation and metadata injection...")
        if not context.final_report:
            raise ValueError(
                "Final report data is missing before final validation step."
            )

        report_data = context.final_report
        report_data["prompt_metadata"] = PromptMetadata(
            run_id=context.run_id, user_passage=context.user_passage
        ).model_dump(mode="json")
        report_data["antagonist_synthesis"] = context.antagonist_synthesis

        brief_keys_to_copy = [
            "season",
            "year",
            "region",
            "target_gender",
            "target_age_group",
            "target_model_ethnicity",
            "desired_mood",
        ]
        for key in brief_keys_to_copy:
            if key not in report_data or not report_data[key]:
                report_data[key] = context.enriched_brief.get(key)

        report_data = self._normalize_lists(report_data)

        try:
            validated_report = FashionTrendReport.model_validate(report_data)
            context.final_report = validated_report.model_dump(mode="json")
            self.logger.info("✅ Success: Final report has been validated.")
        except ValidationError as e:
            self.logger.critical(
                f"❌ CRITICAL: The final assembled report failed Pydantic validation: {e}"
            )
            raise RuntimeError(
                "The final assembled report failed Pydantic validation."
            ) from e

        return context


# --- END: ASSEMBLER REFACTOR ---


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
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"✅ Successfully saved file: {filename}")

        except (IOError, TypeError) as e:
            self.logger.error(
                f"❌ Failed to save JSON file '{filename}'", exc_info=True
            )

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the creation, merging, and saving of all final report files."""
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

        try:
            # The report is already validated, so we just load it into the model
            validated_report = FashionTrendReport.model_validate(context.final_report)
            self.logger.info(
                "🎨 Report data loaded. Initializing prompt generation strategy..."
            )

            prompt_generator = PromptGenerator(
                report=validated_report,
                research_dossier=context.structured_research_context,
            )
            prompts_data, art_direction_model = (
                await prompt_generator.generate_prompts()
            )

            if (
                art_direction_model
                and art_direction_model.narrative_setting_description
            ):
                context.final_report["narrative_setting_description"] = (
                    art_direction_model.narrative_setting_description
                )

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
        except Exception:
            self.logger.error(
                "❌ An unexpected error occurred during prompt generation or injection.",
                exc_info=True,
            )

        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        self.logger.info("✅ Success: All reporting outputs have been generated.")
        return context
