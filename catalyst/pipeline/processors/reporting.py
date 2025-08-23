"""
This module contains the processor for the final reporting stage, with
enhanced logic for generating highly specific and creative image prompts.
"""

import json
import random
from typing import Dict, Any

from pydantic import ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ... import settings
from ...models.trend_report import FashionTrendReport
from ...prompts import prompt_library


class FinalOutputGeneratorProcessor(BaseProcessor):
    """
    Generates all final output files, including the main JSON report and the
    art-directed image prompts.
    """

    async def process(self, context: RunContext) -> RunContext:
        """Orchestrates the creation and saving of all final report files."""
        self.logger.info("⚙️ Starting final report generation...")

        if not context.final_report:
            self.logger.critical(
                "❌ Final report data is missing. Halting report generation."
            )
            raise ValueError("Cannot generate outputs without a final report.")

        try:
            context.results_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.critical(
                f"❌ Could not create output directory {context.results_dir}: {e}",
                exc_info=True,
            )
            raise

        self._save_json_file(
            data=context.final_report,
            filename=settings.TREND_REPORT_FILENAME,
            context=context,
        )

        try:
            validated_report = FashionTrendReport.model_validate(context.final_report)
            self.logger.info("⚙️ Generating art-directed, enriched image prompts...")
            prompts_data = self._generate_image_prompts(validated_report)
            self._save_json_file(
                data=prompts_data, filename=settings.PROMPTS_FILENAME, context=context
            )
            self.logger.info("✅ Success: Image prompt generation complete.")
        except ValidationError as e:
            self.logger.error(
                "❌ Could not generate prompts due to a validation error.",
                exc_info=True,
            )
        except Exception:
            self.logger.error(
                "❌ An unexpected error occurred during prompt generation.",
                exc_info=True,
            )

        self.logger.info("✅ Success: All reporting outputs have been generated.")
        return context

    def _save_json_file(self, data: Dict, filename: str, context: RunContext):
        """A helper function to save a dictionary to a JSON file."""
        try:
            output_path = context.results_dir / filename
            self.logger.info(f"💾 Saving data to '{output_path}'...")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"✅ Successfully saved file: {filename}")
        except (IOError, TypeError):
            self.logger.error(
                f"❌ Failed to save JSON file '{filename}'", exc_info=True
            )

    def _generate_image_prompts(self, report: FashionTrendReport) -> Dict[str, Any]:
        """
        Generates highly specific and creative image prompts by intelligently
        selecting a relevant muse and a diverse set of accessories for each key piece.
        """
        all_prompts = {}

        all_accessories = [
            item for sublist in report.accessories.values() for item in sublist
        ]

        for piece in report.detailed_key_pieces:
            # --- START OF FIX ---

            # 1. Correctly select the FIRST item from the list before accessing attributes.
            main_fabric = (
                piece.fabrics[0].material if piece.fabrics else "a high-quality fabric"
            )
            main_color = piece.colors[0].name if piece.colors else "a core color"
            silhouette = (
                piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
            )

            # 2. Refine Muse Selection Logic to ensure it's always a string.
            best_muse = (
                report.influential_models[0]
                if report.influential_models
                else "an elegant fashion model"
            )
            for model in report.influential_models:
                if any(
                    keyword.lower() in model.lower()
                    for keyword in piece.inspired_by_designers
                ):
                    best_muse = model
                    break

            # 3. Correct Description Snippet to get only the first sentence.
            description_snippet = piece.description.split(".")[0]

            # 4. Correct Styling Description for more natural language.
            styling_elements = piece.suggested_pairings[:2]
            if len(styling_elements) >= 2:
                styling_description = f"The garment is styled with {styling_elements[0]} and {styling_elements[1]} to create a complete, authentic look."
            elif len(styling_elements) == 1:
                styling_description = f"The garment is styled with {styling_elements[0]} to create a complete, authentic look."
            else:
                styling_description = (
                    "The garment is styled to feel authentic and personally curated."
                )

            # --- END OF FIX ---

            # Diverse Accessory Sampling remains correct.
            num_accessories = min(len(all_accessories), 3)
            sampled_accessories = (
                random.sample(all_accessories, num_accessories)
                if num_accessories > 0
                else ["a statement handbag", "chunky boots"]
            )

            color_names = ", ".join([c.name for c in piece.colors])
            fabric_names = ", ".join(
                [f"{f.texture} {f.material}" for f in piece.fabrics]
            )
            details_trims_list = ", ".join(piece.details_trims)

            piece_prompts = {
                "inspiration_board": prompt_library.INSPIRATION_BOARD_PROMPT_TEMPLATE.format(
                    theme=report.overarching_theme,
                    key_piece_name=piece.key_piece_name,
                    description_snippet=description_snippet,
                    model_style=best_muse,
                    color_names=color_names,
                    fabric_names=fabric_names,
                ),
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    key_piece_name=piece.key_piece_name,
                    fabric_names=fabric_names,
                    color_names=color_names,
                    details_trims=details_trims_list,
                    key_accessories=", ".join(sampled_accessories),
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    model_style=best_muse,
                    key_piece_name=piece.key_piece_name,
                    description_snippet=description_snippet,
                    main_color=main_color,
                    main_fabric=main_fabric,
                    silhouette=silhouette,
                    details_trims=details_trims_list,
                    narrative_setting=report.narrative_setting_description,
                    styling_description=styling_description,
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        return all_prompts
