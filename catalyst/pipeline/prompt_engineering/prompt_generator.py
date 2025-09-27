# catalyst/pipeline/prompt_engineering/prompt_generator.py

"""
This module defines the PromptGenerator, a strategy class responsible for
transforming a validated FashionTrendReport into a complete set of final,
art-directed image prompts. This version is enhanced to create cohesive,
grammatically correct, and visually striking prompt language.
"""

import json
import random
from typing import Dict, Any, List

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


class CreativeStyleGuideModel(BaseModel):
    art_direction: str = Field(...)
    negative_style_keywords: str = Field(...)


DEFAULT_STYLE_GUIDE = CreativeStyleGuideModel(
    art_direction="A powerful, cinematic mood captured with a sharp 50mm prime lens. Lighting is soft and natural. The model has a confident, authentic presence that honors the garment's form.",
    negative_style_keywords="blurry, poor quality, generic, boring, deformed",
)


class PromptGenerator:
    """
    Generates final image prompts from a structured trend report with a focus
    on creating cohesive, visually striking language.
    """

    def __init__(self, report: FashionTrendReport, research_dossier: Dict[str, Any]):
        self.report = report
        self.research_dossier = research_dossier
        self.logger = get_logger(self.__class__.__name__)

    def _format_visual_fabric_details(self, fabrics: List[FabricDetail]) -> str:
        """Creates a descriptive, formatted list for the mood board."""
        lines = []
        for f in fabrics[:2]:  # Limit to the top 2 for clarity
            parts = [f.texture, f.material]
            desc = f"- **Fabric Swatch:** A tactile swatch of {' '.join(filter(None, parts))}, showcasing its {f.drape or 'moderate'} drape and {f.finish or 'matte'} finish."
            lines.append(desc)
        return "\n  ".join(lines)

    def _format_visual_pattern_details(self, patterns: List[PatternDetail]) -> str:
        """Creates a descriptive, formatted list for the mood board."""
        if not patterns:
            return "- **Texture Focus:** A close-up on the fabric's natural weave and texture, emphasizing its raw beauty."
        lines = []
        for p in patterns[:1]:  # Focus on the primary pattern
            lines.append(
                f"- **Pattern Detail:** A print sample featuring a '{p.motif}' motif, demonstrating its '{p.placement}' placement and scale."
            )
        return "\n  ".join(lines)

    def _get_visual_fabric_description(self, piece: KeyPieceDetail) -> str:
        """Builds a cohesive sentence describing the garment's material."""
        if not piece.fabrics:
            return "Crafted from a high-quality, modern textile with a focus on texture and form."
        main_fabric = piece.fabrics[0]
        return (
            f"Crafted from a luxurious {main_fabric.texture or ''} {main_fabric.material or 'textile'}. "
            f"The fabric has a {main_fabric.drape or 'moderate'} drape and a {main_fabric.finish or 'matte'} finish, "
            "giving it a unique hand-feel and visual depth."
        )

    def _get_visual_color_palette(self, piece: KeyPieceDetail) -> str:
        """Builds a cohesive sentence describing the color palette."""
        if not piece.colors:
            return "A thematically appropriate and sophisticated color palette."
        color_names = [c.name for c in piece.colors if c.name]
        if not color_names:
            return "A thematically appropriate and sophisticated color palette."
        if len(color_names) == 1:
            return f"The piece is rendered in a striking shade of {color_names[0]}."
        if len(color_names) > 2:
            return f"A rich color palette of {', '.join(color_names[:-1])}, with a key accent of {color_names[-1]}."
        return f"A refined color palette of {color_names[0]} and {color_names[1]}."

    def _get_visual_pattern_description(self, piece: KeyPieceDetail) -> str:
        """Builds a cohesive sentence describing the garment's pattern."""
        if not piece.patterns:
            return "The garment is a solid color, focusing on its silhouette and the natural texture of the fabric."
        main_pattern = piece.patterns[0]
        return (
            f"It features a '{main_pattern.motif or 'subtle'}' pattern, "
            f"thoughtfully applied as a {main_pattern.placement or 'tonal accent'} to enhance the garment's form."
        )

    def _get_visual_details_description(self, piece: KeyPieceDetail) -> str:
        """Builds a cohesive sentence describing key construction details."""
        parts = []
        if piece.details_trims:
            parts.append(
                f"Key construction details include {', '.join(piece.details_trims[:3])}."
            )
        if piece.lining:
            parts.append(f"It is lined with {piece.lining} for a luxurious finish.")
        return (
            " ".join(parts)
            or "Constructed with clean, minimalist detailing and an impeccable finish."
        )


    async def _generate_creative_style_guide(self) -> CreativeStyleGuideModel:
        self.logger.info("✍️ Generating Creative Style Guide from final report data...")
        influential_models_str = ", ".join(
            [item.name for item in self.report.influential_models]
        )
        prompt_args = {
            "research_dossier": json.dumps(self.research_dossier, indent=2),
            "overarching_theme": self.report.overarching_theme,
            "refined_mood": self.research_dossier.get("trend_narrative", ""),
            "influential_models": influential_models_str,
            "brand_ethos": self.report.prompt_metadata.user_passage,
            "style_guide_schema": json.dumps(
                CreativeStyleGuideModel.model_json_schema(), indent=2
            ),
        }
        try:
            style_guide_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt_library.CREATIVE_STYLE_GUIDE_PROMPT.format(**prompt_args),
                response_schema=CreativeStyleGuideModel,
            )
            self.logger.info("✅ Success: Creative Style Guide generated.")
            return style_guide_model
        except MaxRetriesExceededError:
            self.logger.warning("⚠️ AI call for style guide failed. Using fallback.")
            return DEFAULT_STYLE_GUIDE

    async def generate_prompts(self) -> Dict[str, Any]:
        all_prompts = {}
        style_guide_model = await self._generate_creative_style_guide()

        all_accessory_names = [item.name for item in self.report.accessories]
        cultural_drivers_list = [item.name for item in self.report.cultural_drivers]
        core_concept_inspiration = (
            random.choice(cultural_drivers_list)
            if cultural_drivers_list
            else "modern minimalist art"
        )

        if not self.report.detailed_key_pieces:
            self.logger.warning(
                "No detailed key pieces found. Cannot generate image prompts."
            )
            return {}

        for piece in self.report.detailed_key_pieces:
            sampled_accessory_names = (
                random.sample(all_accessory_names, min(len(all_accessory_names), 2))
                if all_accessory_names
                else []
            )
            key_accessories_str = (
                ", ".join(sampled_accessory_names)
                or "a statement handbag and elegant sunglasses"
            )
            color_names_for_prompt = [c.name for c in piece.colors if c.name]

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
                    color_names=", ".join(color_names_for_prompt),
                    formatted_pattern_details=self._format_visual_pattern_details(
                        piece.patterns
                    ),
                    details_trims=", ".join(piece.details_trims),
                    key_accessories=key_accessories_str,
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
                "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
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
                    styling_description=" and ".join(piece.suggested_pairings[:2])
                    or "the piece is styled to feel authentic and personally curated",
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
            }
            all_prompts[piece.key_piece_name or "untitled"] = piece_prompts

        return all_prompts
