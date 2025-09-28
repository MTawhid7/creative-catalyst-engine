# catalyst/pipeline/prompt_engineering/prompt_generator.py

import json
import random
from typing import Dict, Any, List
from itertools import cycle

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
    Generates final image prompts from a structured trend report using a
    strategic pairing approach to maximize creative variation and cohesion.
    """

    def __init__(self, report: FashionTrendReport, research_dossier: Dict[str, Any]):
        self.report = report
        self.research_dossier = research_dossier
        self.logger = get_logger(self.__class__.__name__)

    def _format_visual_fabric_details(self, fabrics: List[FabricDetail]) -> str:
        """Creates a descriptive, grammatically correct list for the mood board."""
        lines = []
        for f in fabrics[:2]:
            # Prioritize the texture, as it's often the most descriptive element.
            if f.texture:
                desc = f"- A tactile swatch of fabric with a {f.texture.lower()}."
            elif f.material:
                desc = f"- A tactile swatch of {f.material}."
            else:
                desc = "- A swatch of high-quality, unique textile."
            lines.append(desc)
        return "\n  ".join(lines)

    def _format_visual_pattern_details(self, patterns: List[PatternDetail]) -> str:
        if not patterns:
            return "- A close-up on the fabric's natural weave and texture."
        lines = []
        for p in patterns[:1]:
            lines.append(f"- A print sample featuring a '{p.motif}' motif.")
        return "\n  ".join(lines)

    def _get_visual_fabric_description(self, piece: KeyPieceDetail) -> str:
        if not piece.fabrics:
            return "Crafted from a high-quality, modern textile."
        main_fabric = piece.fabrics[0]
        return f"Crafted from a luxurious {main_fabric.texture or ''} {main_fabric.material or 'textile'} with a {main_fabric.drape or 'moderate'} drape."

    def _get_visual_color_palette(self, piece: KeyPieceDetail) -> str:
        if not piece.colors:
            return "A thematically appropriate color palette."
        color_names = [c.name for c in piece.colors if c.name]
        if not color_names:
            return "A thematically appropriate color palette."
        if len(color_names) == 1:
            return f"A striking shade of {color_names[0]}."
        if len(color_names) > 2:
            return f"A palette of {', '.join(color_names[:-1])}, with an accent of {color_names[-1]}."
        return f"A palette of {color_names[0]} and {color_names[1]}."

    def _get_visual_pattern_description(self, piece: KeyPieceDetail) -> str:
        if not piece.patterns:
            return "A solid color, focusing on silhouette and texture."
        main_pattern = piece.patterns[0]
        return f"Features a '{main_pattern.motif or 'subtle'}' pattern, applied as a {main_pattern.placement or 'tonal accent'}."

    def _get_visual_details_description(self, piece: KeyPieceDetail) -> str:
        parts = []
        if piece.details_trims:
            parts.append(f"Key details include {', '.join(piece.details_trims[:3])}.")
        if piece.lining:
            parts.append(f"It is lined with {piece.lining}.")
        return " ".join(parts) or "Constructed with clean, minimalist detailing."

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

        if not self.report.detailed_key_pieces:
            self.logger.warning(
                "No detailed key pieces found. Cannot generate image prompts."
            )
            return {}

        # Create cycling iterators for our inspirational elements.
        muse_cycle = cycle(
            [model.name for model in self.report.influential_models]
            or ["a mysterious, artistic figure"]
        )
        inspiration_cycle = cycle(
            [driver.name for driver in self.report.cultural_drivers]
            or ["modern minimalist art"]
        )
        desired_mood_list = (
            ", ".join(self.report.desired_mood) or "sophisticated, elegant"
        )

        for piece in self.report.detailed_key_pieces:
            current_muse = next(muse_cycle)
            current_inspiration = next(inspiration_cycle)

            all_accessory_names = [item.name for item in self.report.accessories]
            sampled_accessories = (
                ", ".join(
                    random.sample(all_accessory_names, min(len(all_accessory_names), 2))
                )
                or "a statement handbag"
            )
            color_names = ", ".join(filter(None, [c.name for c in piece.colors]))

            piece_prompts = {
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    overarching_theme=self.report.overarching_theme,
                    desired_mood_list=desired_mood_list,
                    influential_model_name=current_muse,
                    narrative_setting=self.report.narrative_setting_description,
                    core_concept_inspiration=current_inspiration,
                    antagonist_synthesis=self.report.antagonist_synthesis
                    or "a surprising detail",
                    key_piece_name=piece.key_piece_name,
                    formatted_fabric_details=self._format_visual_fabric_details(
                        piece.fabrics
                    ),
                    color_names=color_names,
                    formatted_pattern_details=self._format_visual_pattern_details(
                        piece.patterns
                    ),
                    details_trims=", ".join(piece.details_trims[:3]),
                    key_accessories=sampled_accessories,
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
                    or "authentic styling",
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
            }
            all_prompts[piece.key_piece_name or "untitled"] = piece_prompts

        return all_prompts
