"""
This module contains the processors for the core synthesis stage, using a
robust, multi-step "research, structure, synthesize" pipeline.
"""

import json
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini_client
from ...prompts import prompt_library
from ...models.trend_report import FashionTrendReport, KeyPieceDetail


class WebResearchProcessor(BaseProcessor):
    """
    Pipeline Step 3: Instructs the LLM to perform a web search and return a
    single, unstructured block of text summarizing its findings.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info(
            "Starting web research using Gemini's native search capabilities..."
        )
        brief = context.enriched_brief

        prompt = prompt_library.WEB_RESEARCH_PROMPT.format(
            theme_hint=brief.get("theme_hint", ""),
            garment_type=brief.get("garment_type", "not specified"),
            target_audience=brief.get("target_audience", "a global audience"),
            region=brief.get("region", "Global"),
            creative_antagonist=brief.get("creative_antagonist", "mainstream trends"),
            search_keywords=", ".join(brief.get("search_keywords", [])),
        )

        response = await gemini_client.generate_content_async(prompt_parts=[prompt])

        if response and response.get("text"):
            self.logger.info(
                f"✅ Success: Synthesized {len(response['text'])} characters of raw text from web research."
            )
            context.raw_research_context = response["text"]
        else:
            self.logger.warning(
                "⚠️ Web research returned no content. The fallback path will now be triggered."
            )
            context.raw_research_context = ""

        return context


class ContextStructuringProcessor(BaseProcessor):
    """
    Pipeline Step 4: Organizes the raw research context into a
    clean, bulleted list to prepare for final JSON generation.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Organizing raw research into a structured outline...")

        if not context.raw_research_context:
            self.logger.warning(
                "⚠️ Raw research context is empty. Skipping structuring step."
            )
            context.structured_research_context = ""
            return context

        brief = context.enriched_brief
        if brief.get("garment_type"):
            instruction = f"Focus exclusively on the specified garment type: **{brief['garment_type']}**. Generate 2-3 distinct variations or interpretations of this single garment."
        else:
            instruction = "Identify 2-3 distinct and compelling key garment pieces from the research. They should be different types (e.g., one coat, one cape)."

        prompt = prompt_library.STRUCTURING_PREP_PROMPT.format(
            theme_hint=brief.get("theme_hint", ""),
            garment_type=brief.get("garment_type", "not specified"),
            research_context=context.raw_research_context,
            garment_generation_instruction=instruction,
        )

        response = await gemini_client.generate_content_async(prompt_parts=[prompt])
        if response and response.get("text"):
            self.logger.info(
                f"✅ Success: Created pre-structured context outline ({len(response['text'])} characters)."
            )
            context.structured_research_context = response["text"]
        else:
            self.logger.warning(
                "⚠️ Pre-structuring step failed. The final synthesis may be less reliable."
            )
            context.structured_research_context = context.raw_research_context

        return context


class ReportSynthesisProcessor(BaseProcessor):
    """
    Pipeline Step 5: Uses the reliable "divide and conquer" method to
    generate the final, validated JSON trend report from the structured context.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Starting final 'divide and conquer' report synthesis...")

        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Structured research context is empty. Skipping this processor."
            )
            return context

        final_report_data = await self._structure_report_divide_and_conquer(
            context.enriched_brief, context.structured_research_context
        )

        if not final_report_data:
            self.logger.error(
                "❌ The 'divide and conquer' synthesis process failed to produce a valid final report."
            )
        else:
            self.logger.info(
                "✅ Success: Assembled and validated the final trend report."
            )
            context.final_report = final_report_data

        return context

    def _extract_section(
        self, context_text: str, start_keyword: str, end_keywords: List[str]
    ) -> str:
        """A robust helper to extract a specific section from the pre-structured text."""
        end_pattern = "|".join(re.escape(k) for k in end_keywords)
        pattern = re.compile(
            rf"{re.escape(start_keyword)}(.*?)(?={end_pattern}|$)",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(context_text)
        return match.group(1).strip() if match else ""

    async def _structure_report_divide_and_conquer(
        self, brief: Dict, research_context: str
    ) -> Optional[Dict]:
        """Breaks the synthesis task into smaller, reliable, schema-driven API calls."""
        final_report = {}

        # STEP 1: Generate Top-Level Fields
        self.logger.info("Step 1/5: Generating top-level fields...")
        top_level_context = self._extract_section(
            research_context,
            "Overarching Theme:",
            ["Accessories:", "Key Piece 1 Name:"],
        )

        class TopLevelModel(BaseModel):
            overarching_theme: str
            cultural_drivers: List[str]
            influential_models: List[str]

        top_level_response = await gemini_client.generate_content_async(
            prompt_parts=[
                prompt_library.TOP_LEVEL_SYNTHESIS_PROMPT.format(
                    research_context=top_level_context
                )
            ],
            response_schema=TopLevelModel,
        )
        if top_level_response:
            final_report.update(top_level_response)
        else:
            self.logger.error("Failed to generate top-level fields.")
            return None

        # STEP 2: Generate Narrative Setting
        self.logger.info("Step 2/5: Generating narrative setting...")
        setting_prompt = prompt_library.NARRATIVE_SETTING_PROMPT.format(
            overarching_theme=final_report.get("overarching_theme", ""),
            cultural_drivers=", ".join(final_report.get("cultural_drivers", [])),
        )
        setting_response = await gemini_client.generate_content_async(
            prompt_parts=[setting_prompt]
        )
        final_report["narrative_setting_description"] = (
            setting_response.get(
                "text", "A minimalist, contemporary architectural setting."
            )
            if setting_response
            else ""
        )

        # STEP 3: Generate Accessories
        self.logger.info("Step 3/5: Generating accessories...")
        accessories_context = self._extract_section(
            research_context, "Accessories:", ["Key Piece 1 Name:"]
        )

        class AccessoriesModel(BaseModel):
            accessories: Dict[str, List[str]]

        accessories_response = await gemini_client.generate_content_async(
            prompt_parts=[
                prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(
                    research_context=accessories_context
                )
            ],
            response_schema=AccessoriesModel,
        )
        final_report.update(accessories_response or {"accessories": {}})

        # STEP 4: Generate Key Pieces
        self.logger.info("Step 4/5: Generating detailed key pieces...")
        key_piece_sections = research_context.split("Key Piece ")[1:]
        processed_pieces = []
        for i, section in enumerate(key_piece_sections):
            self.logger.info(
                f"Processing Key Piece {i + 1}/{len(key_piece_sections)}..."
            )
            key_piece_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=section
            )
            piece_response = await gemini_client.generate_content_async(
                prompt_parts=[key_piece_prompt], response_schema=KeyPieceDetail
            )
            if piece_response:
                try:
                    validated_piece = KeyPieceDetail.model_validate(piece_response)
                    processed_pieces.append(validated_piece.model_dump(mode="json"))
                except ValidationError as e:
                    self.logger.warning(f"Validation failed for Key Piece {i + 1}: {e}")
            else:
                self.logger.error(f"Failed to get a response for Key Piece {i + 1}.")
        final_report["detailed_key_pieces"] = processed_pieces

        # STEP 5: Assemble and Validate
        self.logger.info("Step 5/5: Assembling and validating final report...")
        final_report["season"] = brief.get("season", "")
        final_report["year"] = brief.get("year", 0)
        final_report["region"] = brief.get("region")
        final_report["target_model_ethnicity"] = "Diverse"

        # --- START OF FIX ---
        # The line `final_report["visual_analysis"] = []` has been removed.
        # --- END OF FIX ---

        if "accessories" in final_report and isinstance(
            final_report.get("accessories"), str
        ):
            try:
                self.logger.warning(
                    "Accessories field was a string. Attempting to parse JSON."
                )
                final_report["accessories"] = json.loads(final_report["accessories"])
            except json.JSONDecodeError:
                self.logger.error(
                    "Failed to parse accessories string. Defaulting to empty dict."
                )
                final_report["accessories"] = {}

        try:
            validated_report = FashionTrendReport.model_validate(final_report)
            return validated_report.model_dump(mode="json")
        except ValidationError as e:
            self.logger.critical(
                f"The final assembled report from divide-and-conquer failed validation: {e}"
            )
            return None


class DirectKnowledgeSynthesisProcessor(BaseProcessor):
    """
    Pipeline Fallback Step: Generates the entire trend report in a single call,
    relying solely on the model's pre-trained knowledge.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.warning("⚙️ Activating direct knowledge fallback pipeline.")
        self.logger.info(
            "Generating report directly from Gemini's internal knowledge base..."
        )
        brief = context.enriched_brief
        prompt = prompt_library.DIRECT_KNOWLEDGE_SYNTHESIS_PROMPT.format(
            theme_hint=brief.get("theme_hint", ""),
            garment_type=brief.get("garment_type", "not specified"),
            target_audience=brief.get("target_audience", ""),
            season=brief.get("season", ""),
            year=brief.get("year", ""),
            creative_antagonist=brief.get("creative_antagonist", ""),
        )
        response = await gemini_client.generate_content_async(
            prompt_parts=[prompt], response_schema=FashionTrendReport
        )
        if not response:
            self.logger.critical(
                "❌ Direct knowledge synthesis also failed. The model could not generate a report."
            )
            raise RuntimeError("The fallback knowledge synthesis process failed.")
        self.logger.info("✅ Success: Generated report using direct knowledge.")
        context.final_report = response
        return context
