# catalyst/pipeline/synthesis_strategies/report_assembler.py

"""
This module defines the ReportAssembler, a strategy class responsible for
the multi-step, schema-driven process of constructing the final fashion trend report.

It encapsulates the "divide and conquer" logic, making it a reusable component
for both the primary (web-researched) and fallback (direct knowledge) synthesis paths.
"""

import json
import re
from typing import Dict, List, Optional, Any

from pydantic import ValidationError

from ...clients import gemini
from ...context import RunContext
from ...models.trend_report import FashionTrendReport, KeyPieceDetail, PromptMetadata
from ...prompts import prompt_library
from ...utilities.logger import get_logger
from .synthesis_models import AccessoriesModel, KeyPieceNamesModel, TopLevelModel

# --- Constants ---
DEFAULT_NARRATIVE_SETTING = "A minimalist, contemporary architectural setting."
logger = get_logger(__name__)


class ReportAssembler:
    """
    Orchestrates the step-by-step assembly of the final report, using
    focused LLM calls for each section to ensure reliability and structure.
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.brief = context.enriched_brief
        self.final_report_data: Dict[str, Any] = {}

    def _extract_section(
        self, context_text: str, start_keyword: str, end_keywords: List[str]
    ) -> str:
        """A robust helper to extract a specific section from pre-structured text."""
        end_pattern = "|".join(re.escape(k) for k in end_keywords)
        pattern = re.compile(
            rf"{re.escape(start_keyword)}(.*?)(?={end_pattern}|$)",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(context_text)
        return match.group(1).strip() if match else ""

    async def _build_top_level_fields(
        self, research_context: str, is_fallback: bool
    ) -> bool:
        """Generates the 'overarching_theme', 'cultural_drivers', and 'influential_models'."""
        logger.info("✨ Step 1/5: Generating top-level fields...")
        if is_fallback:
            prompt = prompt_library.TOP_LEVEL_SYNTHESIS_PROMPT.format(
                research_context=json.dumps(self.brief, indent=2)
            )
        else:
            context_for_prompt = self._extract_section(
                research_context,
                "Overarching Theme:",
                ["Accessories:", "Key Piece 1 Name:"],
            )
            prompt = prompt_library.TOP_LEVEL_SYNTHESIS_PROMPT.format(
                research_context=context_for_prompt
            )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=TopLevelModel
        )

        if response:
            self.final_report_data.update(response)
            return True
        logger.error("❌ Failed to generate top-level fields.")
        return False

    async def _build_narrative_setting(self) -> bool:
        """Generates the cinematic 'narrative_setting_description'."""
        logger.info("✨ Step 2/5: Generating narrative setting...")
        theme = self.final_report_data.get(
            "overarching_theme", self.brief.get("theme_hint", "")
        )
        drivers = self.final_report_data.get("cultural_drivers", [])

        prompt = prompt_library.NARRATIVE_SETTING_PROMPT.format(
            overarching_theme=theme, cultural_drivers=", ".join(drivers)
        )
        response = await gemini.generate_content_async(prompt_parts=[prompt])

        narrative_desc = DEFAULT_NARRATIVE_SETTING
        if response and response.get("text"):
            try:
                # This prompt returns a more complex JSON, so we parse it manually
                json_text = (
                    response["text"]
                    .strip()
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                data = json.loads(json_text)
                narrative_desc = data.get(
                    "narrative_setting", DEFAULT_NARRATIVE_SETTING
                )
            except (json.JSONDecodeError, KeyError):
                logger.warning(
                    "⚠️ Could not parse narrative setting JSON. Using fallback."
                )

        self.final_report_data["narrative_setting_description"] = narrative_desc
        return True

    async def _build_accessories(
        self, research_context: str, is_fallback: bool
    ) -> bool:
        """Generates the categorized 'accessories' dictionary."""
        logger.info("✨ Step 3/5: Generating accessories...")
        if is_fallback:
            prompt = prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(
                research_context=json.dumps(self.brief, indent=2)
            )
        else:
            context_for_prompt = self._extract_section(
                research_context, "Accessories:", ["Key Piece 1 Name:"]
            )
            prompt = prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(
                research_context=context_for_prompt
            )

        response = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=AccessoriesModel
        )

        # --- START OF FIX: Use explicit assignment instead of update() ---
        # This is more robust and avoids the ValueError. We expect the response
        # to be the dictionary itself (e.g., {"Bags": [...], "Footwear": [...]}).
        if response and isinstance(response, dict):
            self.final_report_data["accessories"] = response
        else:
            # If the call fails or returns an invalid type, assign a safe default.
            self.final_report_data["accessories"] = {
                "Bags": [],
                "Footwear": [],
                "Jewelry": [],
                "Other": [],
            }
        return True

    async def _build_key_pieces(self, research_context: str, is_fallback: bool) -> bool:
        """Generates the detailed list of 'detailed_key_pieces'."""
        logger.info("✨ Step 4/5: Generating detailed key pieces...")
        processed_pieces = []

        if is_fallback:
            # Fallback path: First generate names, then generate details for each name.
            names_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=json.dumps(self.brief, indent=2)
            )
            names_response = await gemini.generate_content_async(
                prompt_parts=[names_prompt], response_schema=KeyPieceNamesModel
            )
            piece_names = names_response.get("names", []) if names_response else []

            for name in piece_names:
                detail_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                    key_piece_context=f"Generate details for a key piece named: '{name}' based on the brief: {json.dumps(self.brief, indent=2)}"
                )
                piece_response = await gemini.generate_content_async(
                    prompt_parts=[detail_prompt], response_schema=KeyPieceDetail
                )
                if piece_response:
                    processed_pieces.append(piece_response)

        else:
            # Primary path: Split the research context and process each section.
            key_piece_sections = research_context.split("Key Piece ")[1:]
            for i, section in enumerate(key_piece_sections):
                logger.info(
                    f"🔄 Processing Key Piece {i + 1}/{len(key_piece_sections)}..."
                )
                prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                    key_piece_context=section
                )
                piece_response = await gemini.generate_content_async(
                    prompt_parts=[prompt], response_schema=KeyPieceDetail
                )
                if piece_response:
                    processed_pieces.append(piece_response)

        self.final_report_data["detailed_key_pieces"] = processed_pieces
        return True

    async def assemble_report(self) -> Optional[Dict[str, Any]]:
        """
        Executes the full, multi-step report assembly process and returns a
        validated report dictionary on success, or None on failure.
        """
        is_fallback = not self.context.structured_research_context
        research_context = self.context.structured_research_context or ""

        # Execute each build step sequentially, checking for failure.
        if not await self._build_top_level_fields(research_context, is_fallback):
            return None
        if not await self._build_narrative_setting():
            return None
        if not await self._build_accessories(research_context, is_fallback):
            return None
        if not await self._build_key_pieces(research_context, is_fallback):
            return None

        # --- Final Assembly and Validation ---
        logger.info("✨ Step 5/5: Assembling and validating final report...")

        # Add metadata and demographic info from the context and brief
        self.final_report_data["prompt_metadata"] = PromptMetadata(
            run_id=self.context.run_id, user_passage=self.context.user_passage
        ).model_dump(mode="json")

        demographic_keys = [
            "season",
            "year",
            "region",
            "target_gender",
            "target_age_group",
            "target_model_ethnicity",
        ]
        for key in demographic_keys:
            self.final_report_data[key] = self.brief.get(key)

        try:
            # The final, critical validation step.
            validated_report = FashionTrendReport.model_validate(self.final_report_data)
            logger.info("✅ Success: Final report assembled and validated.")
            return validated_report.model_dump(mode="json")
        except ValidationError as e:
            logger.critical(
                f"❌ The final assembled report failed validation: {e}",
                extra={"report_data": self.final_report_data},
            )
            return None
