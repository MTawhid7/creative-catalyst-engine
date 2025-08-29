"""
This module contains the processor for the final reporting stage, with
an advanced "Creative Direction" step to generate highly specific and
art-directed image prompts using a professional-grade data model.
"""

import json
import random
from typing import Dict, Any, List
from pathlib import Path

from pydantic import ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ... import settings
from ...models.trend_report import FashionTrendReport, FabricDetail, PatternDetail
from ...prompts import prompt_library
from ...clients import gemini_client


class FinalOutputGeneratorProcessor(BaseProcessor):
    """
    Generates all final output files, including the main JSON report and the
    AI-driven "Creative Style Guide" that produces the final image prompts.
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
            final_dir = Path(context.results_dir)
            final_dir.mkdir(parents=True, exist_ok=True)
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
            self.logger.info("🎨 Performing AI Creative Direction step...")

            prompts_data = await self._generate_image_prompts(
                report=validated_report,
                brand_ethos=context.brand_ethos,
                enriched_brief=context.enriched_brief,
            )

            # --- START OF FIX: SAVE PROMPTS TO CONTEXT ARTIFACTS ---
            # This makes the prompts available to downstream processors like DalleImageGenerationProcessor
            # without needing to re-read the file from disk.
            if "FinalOutputGeneratorProcessor" not in context.artifacts:
                context.artifacts["FinalOutputGeneratorProcessor"] = {}
            context.artifacts["FinalOutputGeneratorProcessor"]["prompts"] = prompts_data
            # --- END OF FIX ---

            self._save_json_file(
                data=prompts_data, filename=settings.PROMPTS_FILENAME, context=context
            )
            self.logger.info("✅ Success: Image prompt generation complete.")
        except ValidationError as e:
            self.logger.error(
                "❌ Could not generate prompts due to a validation error in the final report.",
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
            output_path = Path(context.results_dir) / filename
            self.logger.info(f"💾 Saving data to '{output_path}'...")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"✅ Successfully saved file: {filename}")
        except (IOError, TypeError):
            self.logger.error(
                f"❌ Failed to save JSON file '{filename}'", exc_info=True
            )

    async def _generate_creative_style_guide(
        self, report: FashionTrendReport, brand_ethos: str, enriched_brief: Dict
    ) -> Dict:
        """Calls the AI to translate the report data into a concrete style guide."""
        self.logger.info("✍️ Generating Creative Style Guide from report data...")

        prompt = prompt_library.CREATIVE_STYLE_GUIDE_PROMPT.format(
            brand_ethos=brand_ethos
            or "A focus on creating a beautiful and compelling image.",
            overarching_theme=report.overarching_theme,
            influential_models=", ".join(report.influential_models),
            creative_antagonist=enriched_brief.get(
                "creative_antagonist", "mainstream trends"
            ),
        )

        response = await gemini_client.generate_content_async(prompt_parts=[prompt])

        if response and response.get("text"):
            try:
                json_text = (
                    response["text"]
                    .strip()
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                style_guide = json.loads(json_text)
                self.logger.info("✅ Success: Creative Style Guide generated.")
                return style_guide
            except (json.JSONDecodeError, KeyError):
                self.logger.warning(
                    "⚠️ Could not parse style guide JSON. Using fallback."
                )
        else:
            self.logger.warning("⚠️ AI call for style guide failed. Using fallback.")

        return {
            "photographic_style": "The lighting should be soft and natural, creating a timeless and elegant mood.",
            "model_persona": "The model embodies the core theme with a confident and authentic presence.",
            "negative_style_keywords": "generic, boring, poorly lit, blurry",
        }

    def _format_fabric_details(self, fabrics: List[FabricDetail]) -> str:
        """Formats fabric details into a descriptive list for the mood board."""
        lines = []
        for f in fabrics:
            details = [f.texture, f.material]
            if f.weight_gsm:
                details.append(f"{f.weight_gsm} gsm")
            if f.drape:
                details.append(f"{f.drape} drape")
            if f.finish:
                details.append(f"{f.finish} finish")
            lines.append(f"- {' / '.join(details)}")
        return "\n      ".join(lines)

    def _format_pattern_details(self, patterns: List[PatternDetail]) -> str:
        """Formats pattern details into a descriptive list for the mood board."""
        if not patterns:
            return "- No specific patterns defined."
        lines = []
        for p in patterns:
            details = [p.motif, p.placement]
            if p.scale_cm:
                details.append(f"{p.scale_cm}cm scale")
            lines.append(f"- {' / '.join(details)}")
        return "\n      ".join(lines)

    async def _generate_image_prompts(
        self, report: FashionTrendReport, brand_ethos: str, enriched_brief: Dict
    ) -> Dict[str, Any]:
        """
        Generates prompts by first creating an AI-driven style guide, then applying
        it to each key piece using the new, highly detailed data model.
        """
        all_prompts = {}

        style_guide = await self._generate_creative_style_guide(
            report, brand_ethos, enriched_brief
        )

        all_accessories = [
            item for sublist in report.accessories.values() for item in sublist
        ]

        for piece in report.detailed_key_pieces:

            # --- START OF FIX: PROVIDE ALL DEFAULT ARGUMENTS FOR FALLBACK ---
            main_fabric = piece.fabrics[0] if piece.fabrics else FabricDetail(
                material="high-quality fabric",
                texture="woven",
                sustainable=None,
                weight_gsm=None,
                drape=None,
                finish=None
            )
            # --- END OF FIX ---

            main_color = piece.colors[0].name if piece.colors else "a core color"
            silhouette = piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"

            description_snippet = piece.description.split(".")[0]

            styling_elements = piece.suggested_pairings[:2]
            if len(styling_elements) >= 2:
                styling_description = f"{styling_elements[0]} and {styling_elements[1]}"
            elif len(styling_elements) == 1:
                styling_description = f"{styling_elements[0]}"
            else:
                styling_description = "the piece is styled to feel authentic and personally curated"

            if all_accessories:
                num_accessories = min(len(all_accessories), 3)
                sampled_accessories = random.sample(all_accessories, num_accessories)
            else:
                sampled_accessories = ["a statement handbag", "elegant sunglasses"]

            fabric_details_list = self._format_fabric_details(piece.fabrics)
            pattern_details_list = self._format_pattern_details(piece.patterns)

            main_pattern = piece.patterns[0] if piece.patterns else None
            pattern_description = "The garment is a solid color without a prominent pattern."
            if main_pattern:
                pattern_description = f"The garment features a '{main_pattern.motif}' pattern, applied as an {main_pattern.placement}."

            color_names = ", ".join([c.name for c in piece.colors])
            details_trims_list = ", ".join(piece.details_trims)

            piece_prompts = {
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    key_piece_name=piece.key_piece_name,
                    fabric_details_list=fabric_details_list,
                    pattern_details_list=pattern_details_list,
                    color_names=color_names,
                    details_trims=details_trims_list,
                    key_accessories=", ".join(sampled_accessories),
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    photographic_style_guide=style_guide.get("photographic_style"),
                    model_persona=style_guide.get("model_persona"),
                    negative_style_keywords=style_guide.get("negative_style_keywords"),
                    key_piece_name=piece.key_piece_name,
                    silhouette=silhouette,
                    main_fabric=main_fabric.material,
                    main_fabric_texture=main_fabric.texture,
                    main_fabric_weight_gsm=main_fabric.weight_gsm or 200,
                    main_fabric_drape=main_fabric.drape or "moderate",
                    main_fabric_finish=main_fabric.finish or "matte",
                    main_color=main_color,
                    pattern_description=pattern_description,
                    lining_description=piece.lining or "The garment's lining is not specified.",
                    styling_description=styling_description,
                    narrative_setting=report.narrative_setting_description,
                    details_trims=details_trims_list,
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        return all_prompts