# catalyst/pipeline/synthesis_strategies/section_builders.py

"""
This module contains the individual "Builder" strategies for each section
of the final fashion trend report. Each builder is a self-contained unit
responsible for a single, focused synthesis task.

This version has been hardened to be defensive against failed or empty
responses from the underlying Gemini client.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from ...clients import gemini
from ...context import RunContext
from ...models.trend_report import KeyPieceDetail
from ...prompts import prompt_library
from ...utilities.logger import get_logger
from ...utilities.json_parser import parse_json_from_llm_output

from .synthesis_models import (
    OverarchingThemeModel,
    CulturalDriversModel,
    InfluentialModelsModel,
    NarrativeSettingModel,
    AccessoriesModel,
    KeyPieceNamesModel,
)


class BaseSectionBuilder(ABC):
    """Abstract base class for a report section builder."""

    def __init__(self, context: RunContext):
        self.context = context
        self.brief = context.enriched_brief
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        """Builds a specific section of the report and returns it as a dictionary."""
        pass

    def _extract_section(
        self, context_text: str, start_keyword: str, end_keywords: List[str]
    ) -> str:
        start_pattern = rf"^{re.escape(start_keyword)}"
        end_pattern = "|".join(f"^{re.escape(k)}" for k in end_keywords)
        pattern = re.compile(
            rf"{start_pattern}(.*?)(?={end_pattern}|$)",
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(context_text)
        return match.group(1).strip() if match else ""


class TopLevelFieldsBuilder(BaseSectionBuilder):
    """Builds the overarching_theme, cultural_drivers, and influential_models."""

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        self.logger.info("✨ Synthesizing top-level fields...")
        theme = await self._build_theme(research_context, is_fallback)
        drivers = await self._build_drivers(research_context, is_fallback)
        models = await self._build_models(research_context, is_fallback)

        return {
            "overarching_theme": theme,
            "cultural_drivers": drivers,
            "influential_models": models,
        }

    async def _build_theme(self, research_context: str, is_fallback: bool) -> str:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.THEME_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=OverarchingThemeModel
        )

        # --- DEFENSIVE CHECK ---
        if response and response.get("overarching_theme"):
            return response["overarching_theme"]

        self.logger.warning(
            "Failed to synthesize overarching theme. Returning empty string."
        )
        return ""

    async def _build_drivers(
        self, research_context: str, is_fallback: bool
    ) -> List[str]:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.DRIVERS_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=CulturalDriversModel
        )

        # --- DEFENSIVE CHECK ---
        if response and response.get("cultural_drivers"):
            return response["cultural_drivers"]

        self.logger.warning(
            "Failed to synthesize cultural drivers. Returning empty list."
        )
        return []

    async def _build_models(
        self, research_context: str, is_fallback: bool
    ) -> List[str]:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.MODELS_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=InfluentialModelsModel
        )

        # --- DEFENSIVE CHECK ---
        if response and response.get("influential_models"):
            return response["influential_models"]

        self.logger.warning(
            "Failed to synthesize influential models. Returning empty list."
        )
        return []


class NarrativeSettingBuilder(BaseSectionBuilder):
    """Builds the narrative_setting_description."""

    def __init__(self, context: RunContext, theme: str, drivers: List[str]):
        super().__init__(context)
        self.theme = theme
        self.drivers = drivers

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        self.logger.info("✨ Synthesizing narrative setting...")
        prompt = prompt_library.NARRATIVE_SETTING_PROMPT.format(
            overarching_theme=self.theme, cultural_drivers=", ".join(self.drivers)
        )
        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=NarrativeSettingModel
        )

        # --- DEFENSIVE CHECK ---
        if response and response.get("narrative_setting"):
            narrative_desc = response["narrative_setting"]
        else:
            self.logger.warning("Could not generate narrative setting. Using fallback.")
            narrative_desc = "A minimalist, contemporary architectural setting."

        return {"narrative_setting_description": narrative_desc}


class StrategiesBuilder(BaseSectionBuilder):
    """Extracts the color and accessory strategies from the research context."""

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        if is_fallback:
            return {
                "color_palette_strategy": "No specific color strategy was defined.",
                "accessory_strategy": "Accessories play a supportive role to complete the look.",
            }

        self.logger.info("✨ Extracting creative strategies from research context...")
        strategies_json = parse_json_from_llm_output(research_context)

        tonal_story = ""
        accessory_role = ""

        if strategies_json and isinstance(strategies_json, dict):
            tonal_story = strategies_json.get("tonal_story", "")
            accessory_role = strategies_json.get("accessory_strategy", "")
            self.logger.info("✅ Successfully extracted strategies via JSON parsing.")
        else:
            self.logger.warning(
                "⚠️ Could not find or parse the STRATEGIC_NARRATIVES_JSON object."
            )

        return {
            "color_palette_strategy": tonal_story
            or "No specific color strategy was defined.",
            "accessory_strategy": accessory_role
            or "Accessories play a supportive role to complete the look.",
        }


class AccessoriesBuilder(BaseSectionBuilder):
    """Creatively generates a categorized accessories dictionary."""

    def __init__(
        self,
        context: RunContext,
        theme: str,
        mood: List[str],
        drivers: List[str],
        models: List[str],
        strategy: str,
    ):
        super().__init__(context)
        self.theme = theme
        self.mood = mood
        self.drivers = drivers
        self.models = models
        self.strategy = strategy

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        self.logger.info("✨ Creatively generating accessories from report context...")
        context_for_prompt = {
            "overarching_theme": self.theme,
            "desired_mood": self.mood,
            "influential_models": self.models,
            "cultural_drivers": self.drivers,
            "accessory_strategy": self.strategy,
        }
        prompt = prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(
            research_context=json.dumps(context_for_prompt, indent=2)
        )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=AccessoriesModel
        )

        # --- DEFENSIVE CHECK ---
        if (
            response
            and isinstance(response, dict)
            and any(v for v in response.values())
        ):
            return {"accessories": response}

        self.logger.warning("Failed to generate accessories. Using empty default.")
        return {"accessories": {"Bags": [], "Footwear": [], "Jewelry": [], "Other": []}}


class KeyPiecesBuilder(BaseSectionBuilder):
    """Builds the detailed list of key pieces, including the full fallback logic."""

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        self.logger.info("✨ Synthesizing detailed key pieces...")
        desired_mood_text = str(self.brief.get("desired_mood", []))

        if is_fallback:
            return await self._build_fallback_pieces(desired_mood_text)
        return await self._build_primary_pieces(research_context, desired_mood_text)

    async def _build_fallback_pieces(self, desired_mood_text: str) -> Dict[str, Any]:
        self.logger.info("Building key pieces from direct knowledge (fallback)...")
        base_context = (
            f"{json.dumps(self.brief, indent=2)}\n- DESIRED_MOOD: {desired_mood_text}"
        )
        names_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
            key_piece_context=base_context
        )

        names_response = await gemini.generate_content_async(
            prompt_parts=[names_prompt], response_schema=KeyPieceNamesModel
        )

        # --- DEFENSIVE CHECK ---
        piece_names = names_response.get("names", []) if names_response else []
        if not piece_names:
            self.logger.error("❌ Fallback failed to generate key piece names.")
            return {"detailed_key_pieces": []}

        processed_pieces: List[Dict] = []
        for name in piece_names:
            detail_context = f"Generate details for a key piece named: '{name}' based on the brief: {base_context}\n- COLLECTION_COLOR_PALETTE: []"
            detail_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=detail_context
            )

            piece_response = await gemini.generate_content_async(
                prompt_parts=[detail_prompt], response_schema=KeyPieceDetail
            )

            # --- DEFENSIVE CHECK ---
            if piece_response:
                processed_pieces.append(piece_response)
            else:
                self.logger.warning(
                    f"Failed to generate details for fallback key piece: {name}"
                )

        return {"detailed_key_pieces": processed_pieces}

    async def _build_primary_pieces(
        self, research_context: str, desired_mood_text: str
    ) -> Dict[str, Any]:
        self.logger.info("Building key pieces from research context...")
        key_piece_pattern = re.compile(
            r"^(?:\*\*)?Key Piece \d+ Name:(?:\*\*)?(.*?)(?=^(?:\*\*)?Key Piece \d+ Name:|\Z)",
            re.DOTALL | re.MULTILINE,
        )
        key_piece_sections = [
            match.group(0).strip()
            for match in key_piece_pattern.finditer(research_context)
        ]

        if not key_piece_sections:
            self.logger.error("❌ No 'Key Piece' sections found in research context.")
            return {"detailed_key_pieces": []}

        color_palette_text = self._extract_section(
            research_context, "COLLECTION_COLOR_PALETTE:", ["Key Piece 1 Name:"]
        )

        processed_pieces: List[Dict] = []
        for i, section in enumerate(key_piece_sections):
            self.logger.info(
                f"🔄 Processing Key Piece {i + 1}/{len(key_piece_sections)}..."
            )
            context_for_prompt = f"{section}\n- COLLECTION_COLOR_PALETTE: {color_palette_text}\n- DESIRED_MOOD: {desired_mood_text}"
            prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=context_for_prompt
            )

            piece_response = await gemini.generate_content_async(
                prompt_parts=[prompt], response_schema=KeyPieceDetail
            )

            # --- DEFENSIVE CHECK ---
            if piece_response:
                processed_pieces.append(piece_response)
            else:
                self.logger.warning(
                    f"Failed to generate details for primary key piece section {i+1}"
                )

        return {"detailed_key_pieces": processed_pieces}
