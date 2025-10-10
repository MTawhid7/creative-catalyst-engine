# catalyst/pipeline/prompt_engineering/prompt_generator.py

import json
import random
from typing import Dict, Any, List, Tuple
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
from ..synthesis_strategies.synthesis_models import ArtDirectionModel
from ...prompts import prompt_library
from ...utilities.logger import get_logger

logger = get_logger(__name__)


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

    # --- START: REFINED HELPER FUNCTION 1 ---
    def _get_visual_fabric_description(self, piece: KeyPieceDetail) -> str:
        """
        Generates a grammatically correct, natural-language description of
        the garment's primary fabric and texture.
        """
        if not piece.fabrics:
            return "Crafted from a high-quality, modern textile."
        main_fabric = piece.fabrics[0]

        base = f"Crafted from {main_fabric.material or 'a high-quality textile'}"
        texture_desc = main_fabric.texture or ""

        if texture_desc:
            # Make sure the texture description flows grammatically.
            if texture_desc[0].isupper():
                texture_desc = texture_desc[0].lower() + texture_desc[1:]
            return f"{base}, which has a {texture_desc}."
        else:
            return f"{base}."

    # --- END: REFINED HELPER FUNCTION 1 ---

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

    # --- START: REFINED HELPER FUNCTION 2 ---
    def _get_visual_details_description(self, piece: KeyPieceDetail) -> str:
        """
        Generates a natural-language summary of the key construction details and lining.
        """
        parts = []
        if piece.details_trims:
            trims_list = piece.details_trims[:3]
            if len(trims_list) > 1:
                trims_str = ", ".join(trims_list[:-1]) + f", and {trims_list[-1]}"
            else:
                trims_str = trims_list[0]
            parts.append(f"Key details include {trims_str}")

        if piece.lining:
            lining_desc = piece.lining
            # Append the lining description, ensuring it flows as a new sentence.
            if not lining_desc.endswith("."):
                parts.append(f"it is lined with {lining_desc.lower()}")
            else:
                parts.append(lining_desc)

        if not parts:
            return "Constructed with clean, minimalist detailing."

        # Join the parts into a single, grammatically correct paragraph.
        description = ". ".join(parts).capitalize().replace("..", ".")
        if not description.endswith("."):
            description += "."
        return description

    # --- END: REFINED HELPER FUNCTION 2 ---

    async def _generate_art_direction(self) -> ArtDirectionModel:
        """Generates the unified art direction using the new, optimized prompt."""
        self.logger.info("✍️ Generating Unified Art Direction from final report data...")
        prompt_args = {
            "enriched_brief": json.dumps(
                self.report.model_dump(
                    include={"overarching_theme", "desired_mood", "prompt_metadata"}
                ),
                indent=2,
            ),
            "research_dossier": json.dumps(self.research_dossier, indent=2),
            "art_direction_schema": json.dumps(
                ArtDirectionModel.model_json_schema(), indent=2
            ),
        }
        try:
            art_direction_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt_library.ART_DIRECTION_PROMPT.format(**prompt_args),
                response_schema=ArtDirectionModel,
            )
            self.logger.info("✅ Success: Unified Art Direction generated.")
            return art_direction_model
        except MaxRetriesExceededError:
            self.logger.warning(
                "⚠️ AI call for art direction failed. Using fallback defaults."
            )
            return ArtDirectionModel()

    async def generate_prompts(self) -> Tuple[Dict[str, Any], ArtDirectionModel]:
        all_prompts = {}
        art_direction_model = await self._generate_art_direction()

        if not self.report.detailed_key_pieces:
            self.logger.warning(
                "No detailed key pieces found. Cannot generate image prompts."
            )
            return {}, art_direction_model

        # --- START: CLEANUP STEP FOR ARTIFACTS ---
        cleaned_narrative_setting = (
            art_direction_model.narrative_setting_description.replace(
                "Context-is-King.", ""
            ).strip()
            if art_direction_model.narrative_setting_description
            else ""
        )
        # --- END: CLEANUP STEP FOR ARTIFACTS ---

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

            if piece.patterns:
                main_pattern = piece.patterns[0]
                pattern_motif = main_pattern.motif or "Not specified"
                pattern_artistic_style = (
                    main_pattern.artistic_style or "As described in the garment concept"
                )
                technique = main_pattern.print_technique or "Applied"
                placement = main_pattern.placement or "as a key accent"
                pattern_technique_and_placement = f"{technique}, {placement}."
            else:
                pattern_motif = "Solid color"
                pattern_artistic_style = "Focus on fabric texture and silhouette"
                pattern_technique_and_placement = "No print or pattern applied."

            piece_prompts = {
                "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                    overarching_theme=self.report.overarching_theme,
                    desired_mood_list=desired_mood_list,
                    influential_model_name=current_muse,
                    narrative_setting=cleaned_narrative_setting,  # Use cleaned variable
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
                    photographic_style=art_direction_model.photographic_style,
                    lighting_style=art_direction_model.lighting_style,
                    film_aesthetic=art_direction_model.film_aesthetic,
                    negative_style_keywords=art_direction_model.negative_style_keywords,
                    narrative_setting_description=cleaned_narrative_setting,  # Use cleaned variable
                    key_piece_name=piece.key_piece_name,
                    garment_description_with_synthesis=piece.description,
                    visual_color_palette=self._get_visual_color_palette(piece),
                    visual_fabric_description=self._get_visual_fabric_description(
                        piece
                    ),
                    pattern_motif=pattern_motif,
                    pattern_artistic_style=pattern_artistic_style,
                    pattern_technique_and_placement=pattern_technique_and_placement,
                    visual_details_description=self._get_visual_details_description(
                        piece
                    ),
                    styling_description=" and ".join(piece.suggested_pairings[:2])
                    or "authentic styling",
                    target_gender=self.report.target_gender,
                    target_model_ethnicity=self.report.target_model_ethnicity,
                ),
            }
            all_prompts[piece.key_piece_name or "untitled"] = piece_prompts

        return all_prompts, art_direction_model
