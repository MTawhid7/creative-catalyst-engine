# catalyst/pipeline/prompt_engineering/prompt_generator.py

"""
This module defines the PromptGenerator, a strategy class responsible for
transforming a validated FashionTrendReport into a complete set of final,
art-directed image prompts.
"""

import json
import random
from typing import Dict, Any, List, Union

from pydantic import BaseModel, Field

from ...resilience import invoke_with_resilience, MaxRetriesExceededError
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


def _normalize_to_list(value: Union[str, List[str]]) -> List[str]:
    """A helper to safely convert a 'str' or 'List[str]' into a 'List[str]'."""
    if isinstance(value, str):
        return [value] if value else []
    return value


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
        self.logger = get_logger(self.__class__.__name__)

    def _format_visual_fabric_details(self, fabrics: List[FabricDetail]) -> str:
        # ... (this method is unchanged)
        lines = []
        for f in fabrics[:3]:
            details = [f.texture, f.material, f"{f.drape or 'moderate'} drape"]
            lines.append(f"- {' / '.join(details)}")
        return "\n  ".join(lines)

    def _format_visual_pattern_details(self, patterns: List[PatternDetail]) -> str:
        # ... (this method is unchanged)
        if not patterns:
            return "- Solid color blocks with a focus on texture."
        lines = []
        for p in patterns:
            lines.append(f"- A print featuring '{p.motif}' as an {p.placement}.")
        return "\n  ".join(lines)

    def _get_visual_fabric_description(self, piece: KeyPieceDetail) -> str:
        # ... (this method is unchanged)
        if not piece.fabrics:
            return "A high-quality, modern textile."
        main_fabric = piece.fabrics[0]
        return f"Crafted from a {main_fabric.texture} {main_fabric.material} with a {main_fabric.drape or 'moderate'} drape and a {main_fabric.finish or 'matte'} finish."

    def _get_visual_color_palette(self, piece: KeyPieceDetail) -> str:
        # ... (this method is unchanged)
        if not piece.colors:
            return "A thematically appropriate color palette."
        color_names = [c.name for c in piece.colors]
        if len(color_names) > 2:
            return f"A palette of {', '.join(color_names[:-1])}, with an accent of {color_names[-1]}."
        return " and ".join(color_names)

    def _get_visual_pattern_description(self, piece: KeyPieceDetail) -> str:
        # ... (this method is unchanged)
        if not piece.patterns:
            return (
                "The garment is a solid color, focusing on its texture and silhouette."
            )
        main_pattern = piece.patterns[0]
        return f"Features a '{main_pattern.motif}' pattern, applied as a {main_pattern.placement}."

    def _get_visual_details_description(self, piece: KeyPieceDetail) -> str:
        # ... (this method is unchanged)
        parts = []
        if piece.lining:
            parts.append(piece.lining)
        if piece.details_trims:
            parts.append(f"Key details include {', '.join(piece.details_trims[:3])}.")
        return " ".join(parts) or "Constructed with clean, minimalist detailing."

    async def _generate_creative_style_guide(self) -> CreativeStyleGuideModel:
        """Calls the AI to translate report data into a concise style guide."""
        self.logger.info("✍️ Generating Creative Style Guide from report data...")

        # Normalize the potentially flexible list fields before using them.
        influential_models_list = _normalize_to_list(self.report.influential_models)

        prompt = prompt_library.CREATIVE_STYLE_GUIDE_PROMPT.format(
            brand_ethos=self.report.prompt_metadata.user_passage,
            overarching_theme=self.report.overarching_theme,
            influential_models=", ".join(
                influential_models_list
            ),  # Use the normalized list
            desired_mood=str(self.report.desired_mood or []),
        )

        try:
            style_guide_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=CreativeStyleGuideModel,
            )
            self.logger.info("✅ Success: Creative Style Guide generated.")
            return style_guide_model
        except MaxRetriesExceededError:
            self.logger.warning(
                "⚠️ AI call for style guide failed after all retries. Using fallback."
            )
            return DEFAULT_STYLE_GUIDE

    async def generate_prompts(self) -> Dict[str, Any]:
        """
        The main public method to generate all prompts using the new,
        more sophisticated and structured templates.
        """
        all_prompts = {}
        # The method now returns a Pydantic model object directly.
        style_guide_model = await self._generate_creative_style_guide()

        all_accessories = [
            item for sublist in self.report.accessories.values() for item in sublist
        ]

        cultural_drivers_list = _normalize_to_list(self.report.cultural_drivers)

        core_concept_inspiration = (
            random.choice(self.report.cultural_drivers)
            if self.report.cultural_drivers
            else "modern minimalist art"
        )

        if not self.report.detailed_key_pieces:
            self.logger.warning(
                "No detailed key pieces found in the report. Cannot generate any image prompts."
            )
            return {}

        for piece in self.report.detailed_key_pieces:
            # Normalize the list fields for each key piece before using them.
            details_trims_list = _normalize_to_list(piece.details_trims)
            suggested_pairings_list = _normalize_to_list(piece.suggested_pairings)

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
                    details_trims=", ".join(details_trims_list),
                    key_accessories=", ".join(sampled_accessories),
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                    # --- FIX 3: Use Correct Attribute Access ---
                    # Access data using attributes, not .get(), for type safety.
                    art_direction=style_guide_model.art_direction,
                    negative_style_keywords=style_guide_model.negative_style_keywords,
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
                    styling_description=" and ".join(suggested_pairings_list[:2])
                    or "the piece is styled to feel authentic",
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
            }
            all_prompts[piece.key_piece_name] = piece_prompts

        return all_prompts
