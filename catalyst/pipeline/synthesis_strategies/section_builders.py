# catalyst/pipeline/synthesis_strategies/section_builders.py

"""
This module contains the individual "Builder" strategies for each section
of the final fashion trend report. Each builder is a self-contained unit
responsible for a single, focused synthesis task.
"""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


from pydantic import ValidationError
from .synthesis_models import ColorPaletteStrategyModel, AccessoryStrategyModel
from ...clients import gemini
from ...context import RunContext
from ...models.trend_report import KeyPieceDetail
from ...prompts import prompt_library
from ...utilities.logger import get_logger
from ...utilities.json_parser import parse_json_from_llm_output

# --- START: RESILIENCE REFACTOR ---
# Import the new invoker and exception classes.
from ...resilience import invoke_with_resilience, MaxRetriesExceededError

# --- END: RESILIENCE REFACTOR ---

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
        # Now we expect dictionaries, so we can merge them directly.
        results = await asyncio.gather(
            self._build_theme(research_context, is_fallback),
            self._build_drivers(research_context, is_fallback),
            self._build_models(research_context, is_fallback),
        )

        # Merge the list of dictionaries into a single dictionary.
        final_data = {}
        for res_dict in results:
            final_data.update(res_dict)
        return final_data

    async def _build_theme(
        self, research_context: str, is_fallback: bool
    ) -> Dict[str, str]:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.THEME_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )
        try:
            model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=OverarchingThemeModel,
            )
            # Return a dictionary directly
            return {"overarching_theme": model.overarching_theme}
        except MaxRetriesExceededError:
            self.logger.warning(
                "Failed to synthesize theme after all retries. Using safe default."
            )
            return {"overarching_theme": ""}

    async def _build_drivers(
        self, research_context: str, is_fallback: bool
    ) -> Dict[str, List[str]]:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.DRIVERS_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )
        try:
            model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=CulturalDriversModel,
            )
            # Return a dictionary directly
            return {"cultural_drivers": model.cultural_drivers}
        except MaxRetriesExceededError:
            self.logger.warning(
                "Failed to synthesize drivers after all retries. Using safe default."
            )
            return {"cultural_drivers": []}

    async def _build_models(
        self, research_context: str, is_fallback: bool
    ) -> Dict[str, List[str]]:
        context_for_prompt = (
            research_context if not is_fallback else json.dumps(self.brief, indent=2)
        )
        prompt = prompt_library.MODELS_SYNTHESIS_PROMPT.format(
            research_context=context_for_prompt
        )
        try:
            model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=InfluentialModelsModel,
            )
            # Return a dictionary directly
            return {"influential_models": model.influential_models}
        except MaxRetriesExceededError:
            self.logger.warning(
                "Failed to synthesize models after all retries. Using safe default."
            )
            return {"influential_models": []}


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

        # --- START: RESILIENCE REFACTOR ---
        try:
            # Delegate the AI call to our robust invoker
            response_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=NarrativeSettingModel,
            )
            narrative_desc = response_model.narrative_setting
        except MaxRetriesExceededError:
            # If the invoker fails completely, use the safe, hardcoded fallback
            self.logger.warning(
                "Could not generate narrative setting after all retries. Using fallback."
            )
            narrative_desc = "A minimalist, contemporary architectural setting."

        return {"narrative_setting_description": narrative_desc}
        # --- END: RESILIENCE REFACTOR ---


class StrategiesBuilder(BaseSectionBuilder):
    """Extracts the color and accessory strategies from the research context using Pydantic validation."""

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:

        # --- START: REFACTOR ---
        # The fallback path is now simpler and uses the default Pydantic models.
        if is_fallback:
            return {
                "color_palette_strategy": ColorPaletteStrategyModel(
                    tonal_story="No specific color strategy was defined."
                ).tonal_story,
                "accessory_strategy": AccessoryStrategyModel(
                    accessory_strategy="Accessories play a supportive role to complete the look."
                ).accessory_strategy,
            }

        self.logger.info("✨ Extracting creative strategies from research context...")
        # Use a regex to find the content inside our new XML tag.
        strategies_json = None
        match = re.search(
            r"<strategic_narratives_json>(.*?)</strategic_narratives_json>",
            research_context,
            re.DOTALL,
        )
        if match:
            try:
                # The content is in the first capturing group.
                strategies_json = json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                self.logger.warning(
                    "⚠️ Found strategy tags, but the content was not valid JSON."
                )

        tonal_story = "No specific color strategy was defined."
        accessory_role = "Accessories play a supportive role to complete the look."

        if strategies_json and isinstance(strategies_json, dict):
            try:
                # Use Pydantic to validate the color strategy part of the JSON
                color_model = ColorPaletteStrategyModel.model_validate(strategies_json)
                tonal_story = color_model.tonal_story
                self.logger.info(
                    "✅ Successfully extracted and validated 'tonal_story'."
                )
            except ValidationError:
                self.logger.warning(
                    "⚠️ Could not validate 'tonal_story' from research. Using default."
                )

            try:
                # Use Pydantic to validate the accessory strategy part of the JSON
                accessory_model = AccessoryStrategyModel.model_validate(strategies_json)
                accessory_role = accessory_model.accessory_strategy
                self.logger.info(
                    "✅ Successfully extracted and validated 'accessory_strategy'."
                )
            except ValidationError:
                self.logger.warning(
                    "⚠️ Could not validate 'accessory_strategy' from research. Using default."
                )
        else:
            self.logger.warning(
                "⚠️ Could not find or parse a valid JSON object for strategies. Using defaults."
            )

        return {
            "color_palette_strategy": tonal_story,
            "accessory_strategy": accessory_role,
        }
        # --- END: REFACTOR ---


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

        # --- START: RESILIENCE REFACTOR ---
        try:
            # Delegate the AI call and validation to the invoker
            response_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=AccessoriesModel,
            )
            # The .model_dump() method converts the Pydantic model back into a dictionary
            accessories_dict = response_model.model_dump()
        except MaxRetriesExceededError:
            # If all retries fail, create an empty (but valid) default model
            self.logger.warning(
                "Failed to generate accessories after all retries. Using empty default."
            )
            accessories_dict = AccessoriesModel().model_dump()

        return {"accessories": accessories_dict}
        # --- END: RESILIENCE REFACTOR ---


class KeyPiecesBuilder(BaseSectionBuilder):
    """Builds the detailed list of key pieces, with robust, resilient AI calls."""

    async def build(self, research_context: str, is_fallback: bool) -> Dict[str, Any]:
        self.logger.info("✨ Synthesizing detailed key pieces...")
        desired_mood_text = str(self.brief.get("desired_mood", []))

        if is_fallback:
            processed_pieces = await self._build_fallback_pieces(desired_mood_text)
        else:
            processed_pieces = await self._build_primary_pieces(
                research_context, desired_mood_text
            )

        return {"detailed_key_pieces": processed_pieces}

    async def _build_fallback_pieces(
        self, desired_mood_text: str
    ) -> List[Dict[str, Any]]:
        self.logger.info("Building key pieces from direct knowledge (fallback)...")
        base_context = (
            f"{json.dumps(self.brief, indent=2)}\n- DESIRED_MOOD: {desired_mood_text}"
        )
        names_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
            key_piece_context=base_context
        )

        # --- START: RESILIENCE REFACTOR (Step 1: Get Names) ---
        try:
            # First, resiliently get the list of names. This is a critical step.
            names_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=names_prompt,
                response_schema=KeyPieceNamesModel,
            )
            piece_names = names_model.names
        except MaxRetriesExceededError:
            # If we can't even get the names, we cannot proceed.
            self.logger.error(
                "❌ Fallback failed to generate key piece names after all retries."
            )
            return []
        # --- END: RESILIENCE REFACTOR (Step 1) ---

        processed_pieces: List[Dict] = []
        for name in piece_names:
            detail_context = f"Generate details for a key piece named: '{name}' based on the brief: {base_context}\n- COLLECTION_COLOR_PALETTE: []"
            detail_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=detail_context
            )

            # --- START: RESILIENCE REFACTOR (Step 2: Get Details) ---
            try:
                # Resiliently get the details for each individual name.
                piece_model = await invoke_with_resilience(
                    ai_function=gemini.generate_content_async,
                    prompt=detail_prompt,
                    response_schema=KeyPieceDetail,
                )
                processed_pieces.append(piece_model.model_dump())
            except MaxRetriesExceededError:
                # If one piece fails, we log it and continue to the next.
                self.logger.warning(
                    f"Failed to generate details for fallback key piece: {name}. Skipping."
                )
                continue
            # --- END: RESILIENCE REFACTOR (Step 2) ---

        return processed_pieces

    async def _build_primary_pieces(
        self, research_context: str, desired_mood_text: str
    ) -> List[Dict[str, Any]]:
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
            return []

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

            # --- START: RESILIENCE REFACTOR ---
            try:
                # Wrap the AI call inside the loop with our robust invoker.
                piece_model = await invoke_with_resilience(
                    ai_function=gemini.generate_content_async,
                    prompt=prompt,
                    response_schema=KeyPieceDetail,
                )
                processed_pieces.append(piece_model.model_dump())
            except MaxRetriesExceededError:
                # If one piece fails, we can log it and still process the others.
                self.logger.warning(
                    f"Failed to generate details for primary key piece section {i+1}. Skipping."
                )
                continue
            # --- END: RESILIENCE REFACTOR ---

        return processed_pieces
