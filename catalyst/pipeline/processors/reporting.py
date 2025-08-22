"""
This module contains the processor responsible for the final stage of the
Creative Catalyst Engine: generating all output artifacts.
"""

import json
from typing import Dict, Any

from pydantic import ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ... import settings
from ...models.trend_report import FashionTrendReport
from ...prompts import prompt_library


class FinalOutputGeneratorProcessor(BaseProcessor):
    """
    Pipeline Step 7: Generates all final output files, including the main
    JSON report and the art-directed image prompts.
    """

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the creation and saving of all final report files."""
        self.logger.info("Starting final report generation...")

        if not context.final_report:
            self.logger.critical(
                "Final report data is missing from the context. Halting report generation."
            )
            raise ValueError("Cannot generate outputs without a final report.")

        # --- START OF FIX ---
        # Ensure the run-specific output directory exists before any file operations.
        # This is the most robust place to put this check.
        try:
            context.results_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.critical(
                f"Could not create the output directory {context.results_dir}. Error: {e}",
                exc_info=True,
            )
            raise  # Re-raise the exception to halt the pipeline
        # --- END OF FIX ---

        # 1. Save the main trend report JSON
        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        # 2. Generate and save the enriched image prompts
        try:
            validated_report = FashionTrendReport.model_validate(context.final_report)
            prompts_data = self._generate_image_prompts(validated_report)
            self._save_json_file(
                data=prompts_data, filename=settings.PROMPTS_FILENAME, context=context
            )
        except ValidationError:
            self.logger.error(
                "Could not generate image prompts due to a data validation error.",
                exc_info=True,
            )
        except Exception:
            self.logger.error(
                "An unexpected error occurred during prompt generation.", exc_info=True
            )

        # 3. (Future) Generate the executive summary
        if "validated_report" in locals():
            self._generate_executive_summary(validated_report)

        self.logger.info("All reporting outputs have been generated successfully.")
        return context

    def _save_json_file(self, data: Dict, filename: str, context: RunContext):
        """A helper function to save a dictionary to a JSON file."""
        try:
            output_path = context.results_dir / filename
            self.logger.info(f"Saving data to '{output_path}'...")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Successfully saved file: {filename}")
        except (IOError, TypeError):
            self.logger.error(f"Failed to save JSON file '{filename}'", exc_info=True)

    def _generate_image_prompts(self, report: FashionTrendReport) -> Dict[str, Any]:
        """Generates the final, art-directed image prompts from the validated trend report."""
        self.logger.info("Generating art-directed, enriched image prompts...")
        all_prompts = {}

        model_style = (
            report.influential_models[0]
            if report.influential_models
            else "an elegant fashion model"
        )

        for piece in report.detailed_key_pieces:
            main_fabric = (
                piece.fabrics[0].material if piece.fabrics else "a high-quality fabric"
            )
            main_color = piece.colors[0].name if piece.colors else "a core color"
            silhouette = (
                piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
            )

            color_names = ", ".join([c.name for c in piece.colors])
            fabric_names = ", ".join(
                [f"{f.texture} {f.material}" for f in piece.fabrics]
            )
            details_trims_list = ", ".join(piece.details_trims)

            description_snippet = piece.description.split(".")[0]

            key_accessories_list = []
            if report.accessories.get("Footwear"):
                key_accessories_list.append(report.accessories["Footwear"][0])
            if report.accessories.get("Jewelry"):
                key_accessories_list.append(report.accessories["Jewelry"][0])
            key_accessories = ", ".join(key_accessories_list[:3])

            piece_prompts = {
                "inspiration_board": prompt_library.INSPIRATION_BOARD_PROMPT_TEMPLATE.format(
                    theme=report.overarching_theme,
                    key_piece_name=piece.key_piece_name,
                    description_snippet=description_snippet,
                    model_style=model_style,
                    color_names=color_names,
                    fabric_names=fabric_names,
                ),
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    key_piece_name=piece.key_piece_name,
                    fabric_names=fabric_names,
                    color_names=color_names,
                    details_trims=details_trims_list,
                    key_accessories=key_accessories,
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    model_style=model_style,
                    key_piece_name=piece.key_piece_name,
                    description_snippet=description_snippet,
                    main_color=main_color,
                    main_fabric=main_fabric,
                    silhouette=silhouette,
                    details_trims=details_trims_list,
                    narrative_setting=report.narrative_setting_description,
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        self.logger.info("Image prompt generation complete.")
        return all_prompts

    def _generate_executive_summary(self, report: FashionTrendReport):
        """Placeholder for generating a human-readable summary (e.g., Markdown)."""
        self.logger.info("Executive summary generation is not yet implemented.")
        pass
