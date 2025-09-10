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

from pydantic import BaseModel, Field

from ...clients import gemini
from ...models.trend_report import (
    FashionTrendReport,
    FabricDetail,
    PatternDetail,
    KeyPieceDetail,
)
from ...prompts import prompt_library
from ...utilities.logger import get_logger

logger = get_logger(__name__)


class CreativeStyleGuideModel(BaseModel):
    art_direction: str = Field(
        ...,
        description="A unified paragraph describing the photo style and model persona.",
    )
    negative_style_keywords: str = Field(
        ..., description="A comma-separated list of keywords to avoid."
    )


DEFAULT_STYLE_GUIDE = CreativeStyleGuideModel(
    art_direction="A powerful, cinematic mood captured with a sharp 50mm prime lens. Lighting is soft and natural. The model has a confident, authentic presence that honors the garment's form.",
    negative_style_keywords="blurry, poor quality, generic, boring, deformed",
)


class PromptGenerator:
    """
    Generates final image prompts from a structured trend report.
    """

    def __init__(self, report: FashionTrendReport):
        """
        Initializes the generator with the validated report.
        """
        self.report = report

    def _format_visual_fabric_details(self, fabrics: List[FabricDetail]) -> str:
        """Translates technical fabric data into a visual, tactile list for the mood board."""
        lines = []
        for f in fabrics[:3]:
            details = [f.texture, f.material, f"{f.drape or 'moderate'} drape"]
            lines.append(f"- {' / '.join(details)}")
        return "\n  ".join(lines)

    def _format_visual_pattern_details(self, patterns: List[PatternDetail]) -> str:
        """Translates technical pattern data into a visual list for the mood board."""
        if not patterns:
            return "- Solid color blocks with a focus on texture."
        lines = []
        for p in patterns:
            lines.append(f"- A print featuring '{p.motif}' as an {p.placement}.")
        return "\n  ".join(lines)

    def _get_visual_fabric_description(self, piece: KeyPieceDetail) -> str:
        """Creates a single, descriptive phrase for the final garment's material story."""
        if not piece.fabrics:
            return "A high-quality, modern textile."
        main_fabric = piece.fabrics[0]
        return f"Crafted from a {main_fabric.texture} {main_fabric.material} with a {main_fabric.drape or 'moderate'} drape and a {main_fabric.finish or 'matte'} finish."

    def _get_visual_color_palette(self, piece: KeyPieceDetail) -> str:
        """Creates a descriptive phrase for the garment's specific colors."""
        if not piece.colors:
            return "A thematically appropriate color palette."
        color_names = [c.name for c in piece.colors]
        if len(color_names) > 2:
            return f"A palette of {', '.join(color_names[:-1])}, with an accent of {color_names[-1]}."
        return " and ".join(color_names)

    def _get_visual_pattern_description(self, piece: KeyPieceDetail) -> str:
        """Creates a descriptive phrase for the garment's pattern."""
        if not piece.patterns:
            return (
                "The garment is a solid color, focusing on its texture and silhouette."
            )
        main_pattern = piece.patterns[0]
        return f"Features a '{main_pattern.motif}' pattern, applied as a {main_pattern.placement}."

    def _get_visual_details_description(self, piece: KeyPieceDetail) -> str:
        """Combines lining and trims into a single construction summary."""
        parts = []
        if piece.lining:
            parts.append(piece.lining)
        if piece.details_trims:
            parts.append(f"Key details include {', '.join(piece.details_trims[:3])}.")
        return " ".join(parts) or "Constructed with clean, minimalist detailing."

    async def _generate_creative_style_guide(self) -> Dict[str, str]:
        """Calls the AI to translate report data into our new, concise style guide."""
        logger.info("✍️ Generating Creative Style Guide from report data...")

        # --- START OF DEFINITIVE FIX ---
        # Correctly pass the `desired_mood` from the final report object to the prompt template.
        prompt = prompt_library.CREATIVE_STYLE_GUIDE_PROMPT.format(
            brand_ethos=self.report.prompt_metadata.user_passage,
            overarching_theme=self.report.overarching_theme,
            influential_models=", ".join(self.report.influential_models),
            desired_mood=str(self.report.desired_mood or []),  # This line is the fix
        )
        # --- END OF DEFINITIVE FIX ---

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=CreativeStyleGuideModel
        )

        if response and isinstance(response, dict):
            logger.info("✅ Success: Creative Style Guide generated.")
            return response

        logger.warning(
            "⚠️ AI call for style guide failed or returned malformed JSON. Using fallback."
        )
        return DEFAULT_STYLE_GUIDE.model_dump()

    async def generate_prompts(self) -> Dict[str, Any]:
        """
        The main public method to generate all prompts using the new,
        more sophisticated and structured templates.
        """
        all_prompts = {}
        style_guide = await self._generate_creative_style_guide()

        all_accessories = [
            item for sublist in self.report.accessories.values() for item in sublist
        ]

        core_concept_inspiration = (
            random.choice(self.report.cultural_drivers)
            if self.report.cultural_drivers
            else "modern minimalist art"
        )

        if not self.report.detailed_key_pieces:
            logger.warning(
                "No detailed key pieces found in the report. Cannot generate any image prompts."
            )
            return {}

        for piece in self.report.detailed_key_pieces:
            sampled_accessories = (
                random.sample(all_accessories, min(len(all_accessories), 3))
                if all_accessories
                else ["a statement handbag", "elegant sunglasses"]
            )

            piece_prompts = {
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    key_piece_name=piece.key_piece_name,
                    narrative_setting=self.report.narrative_setting_description,
                    core_concept_inspiration=core_concept_inspiration,
                    antagonist_synthesis=self.report.antagonist_synthesis
                    or "a surprising, innovative detail",
                    formatted_fabric_details=self._format_visual_fabric_details(
                        piece.fabrics
                    ),
                    color_names=", ".join([c.name for c in piece.colors]),
                    formatted_pattern_details=self._format_visual_pattern_details(
                        piece.patterns
                    ),
                    details_trims=", ".join(piece.details_trims),
                    key_accessories=", ".join(sampled_accessories),
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    art_direction=style_guide.get("art_direction"),
                    key_piece_name=piece.key_piece_name,
                    garment_description_with_synthesis=piece.description,
                    visual_color_palette=self._get_visual_color_palette(piece),
                    visual_fabric_description=self._get_visual_fabric_description(
                        piece
                    ),
                    visual_pattern_description=self._get_visual_pattern_description(
                        piece
                    ),
                    visual_details_description=self._get_visual_details_description(
                        piece
                    ),
                    narrative_setting=self.report.narrative_setting_description,
                    styling_description=" and ".join(piece.suggested_pairings[:2])
                    or "the piece is styled to feel authentic",
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                    negative_style_keywords=style_guide.get("negative_style_keywords"),
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        return all_prompts
