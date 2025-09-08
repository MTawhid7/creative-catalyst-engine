# catalyst/pipeline/prompt_engineering/prompt_generator.py

"""
This module defines the PromptGenerator, a strategy class responsible for
transforming a validated FashionTrendReport into a complete set of final,
art-directed image prompts.

It encapsulates all creative direction, data formatting, and prompt assembly
logic, acting as a pure, testable component with no external side effects.
"""

import json
import random
from typing import Dict, Any, List

from ...clients import gemini
from ...models.trend_report import FashionTrendReport, FabricDetail, PatternDetail
from ...prompts import prompt_library
from ...utilities.logger import get_logger

logger = get_logger(__name__)

# --- Constants ---
DEFAULT_STYLE_GUIDE = {
    "photographic_style": "The lighting should be soft and natural, creating a timeless and elegant mood.",
    "model_persona": "The model embodies the core theme with a confident and authentic presence.",
    "negative_style_keywords": "generic, boring, poorly lit, blurry",
}


class PromptGenerator:
    """
    Generates final image prompts from a structured trend report.
    """

    def __init__(
        self,
        report: FashionTrendReport,
        brand_ethos: str,
        enriched_brief: Dict[str, Any],
    ):
        """
        Initializes the generator with all necessary data.

        Args:
            report: The validated Pydantic model of the final report.
            brand_ethos: The distilled brand philosophy.
            enriched_brief: The enriched brief containing the creative antagonist.
        """
        self.report = report
        self.brand_ethos = brand_ethos
        self.enriched_brief = enriched_brief

    async def _generate_creative_style_guide(self) -> Dict[str, str]:
        """Calls the AI to translate report data into a concrete style guide."""
        logger.info("✍️ Generating Creative Style Guide from report data...")
        prompt = prompt_library.CREATIVE_STYLE_GUIDE_PROMPT.format(
            brand_ethos=self.brand_ethos
            or "A focus on creating a beautiful and compelling image.",
            overarching_theme=self.report.overarching_theme,
            influential_models=", ".join(self.report.influential_models),
            creative_antagonist=self.enriched_brief.get(
                "creative_antagonist", "mainstream trends"
            ),
        )

        response = await gemini.generate_content_async(prompt_parts=[prompt])

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
                if all(k in style_guide for k in DEFAULT_STYLE_GUIDE.keys()):
                    logger.info("✅ Success: Creative Style Guide generated.")
                    return style_guide
            except (json.JSONDecodeError, KeyError):
                logger.warning("⚠️ Could not parse style guide JSON. Using fallback.")

        logger.warning("⚠️ AI call for style guide failed. Using fallback.")
        return DEFAULT_STYLE_GUIDE

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

    async def generate_prompts(self) -> Dict[str, Any]:
        """
        The main public method to generate all prompts.

        It first creates an AI-driven style guide, then applies it to each key
        piece from the report to generate a mood board and a final garment prompt.

        Returns:
            A dictionary containing all generated prompts, keyed by garment name.
        """
        all_prompts = {}
        style_guide = await self._generate_creative_style_guide()

        all_accessories = [
            item for sublist in self.report.accessories.values() for item in sublist
        ]

        for piece in self.report.detailed_key_pieces:
            # --- START OF FIX ---
            # Correctly instantiate the fallback FabricDetail by providing
            # explicit None values for all optional fields.
            if piece.fabrics:
                main_fabric = piece.fabrics[0]
            else:
                main_fabric = FabricDetail(
                    material="high-quality fabric",
                    texture="woven",
                    sustainable=None,
                    weight_gsm=None,
                    drape=None,
                    finish=None,
                )
            # --- END OF FIX ---

            main_color = piece.colors[0].name if piece.colors else "a core color"
            silhouette = (
                piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
            )

            styling_elements = piece.suggested_pairings[:2]
            styling_description = (
                " and ".join(styling_elements)
                if len(styling_elements) > 1
                else (
                    styling_elements[0]
                    if styling_elements
                    else "the piece is styled to feel authentic"
                )
            )

            sampled_accessories = (
                random.sample(all_accessories, min(len(all_accessories), 3))
                if all_accessories
                else ["a statement handbag", "elegant sunglasses"]
            )

            main_pattern = piece.patterns[0] if piece.patterns else None
            pattern_description = (
                f"The garment features a '{main_pattern.motif}' pattern, applied as a {main_pattern.placement}."
                if main_pattern
                else "The garment is a solid color."
            )

            piece_prompts = {
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    key_piece_name=piece.key_piece_name,
                    fabric_details_list=self._format_fabric_details(piece.fabrics),
                    pattern_details_list=self._format_pattern_details(piece.patterns),
                    color_names=", ".join([c.name for c in piece.colors]),
                    details_trims=", ".join(piece.details_trims),
                    key_accessories=", ".join(sampled_accessories),
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    photographic_style_guide=style_guide.get("photographic_style"),
                    model_persona=style_guide.get("model_persona"),
                    negative_style_keywords=style_guide.get("negative_style_keywords"),
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                    key_piece_name=piece.key_piece_name,
                    silhouette=silhouette,
                    main_fabric=main_fabric.material,
                    main_fabric_texture=main_fabric.texture,
                    main_fabric_weight_gsm=main_fabric.weight_gsm or 200,
                    main_fabric_drape=main_fabric.drape or "moderate",
                    main_fabric_finish=main_fabric.finish or "matte",
                    main_color=main_color,
                    pattern_description=pattern_description,
                    lining_description=piece.lining
                    or "The garment's lining is not specified.",
                    styling_description=styling_description,
                    narrative_setting=self.report.narrative_setting_description,
                    details_trims=", ".join(piece.details_trims),
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        return all_prompts
