"""
This module contains the processors for the core synthesis stage, using a
robust, multi-step "research, structure, synthesize" pipeline with graceful
handling for incomplete creative briefs.
"""

import json
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini_client
from ...prompts import prompt_library

# --- START OF CHANGE: IMPORT NEW MODELS ---
from ...models.trend_report import (
    FashionTrendReport,
    KeyPieceDetail,
    PromptMetadata,
)

# --- END OF CHANGE ---
from ...utilities.config_loader import FORMATTED_SOURCES


class WebResearchProcessor(BaseProcessor):
    """
    Pipeline Step 4: Instructs the LLM to perform a web search and return a
    single, unstructured block of text summarizing its findings, guided by the brand ethos
    and a curated list of sources.
    """

    async def process(self, context: RunContext) -> RunContext:
        # This processor is unchanged, but its output will be used by the updated processors below.
        self.logger.info(
            "🌐 Starting web research using Gemini's native search capabilities..."
        )
        brief = context.enriched_brief
        prompt = prompt_library.WEB_RESEARCH_PROMPT.format(
            brand_ethos=context.brand_ethos or "No specific ethos provided.",
            curated_sources=FORMATTED_SOURCES,
            theme_hint=brief.get("theme_hint", "fashion"),
            garment_type=brief.get("garment_type") or "not specified",
            target_audience=brief.get("target_audience") or "a general audience",
            region=brief.get("region") or "Global",
            key_attributes=", ".join(brief.get("key_attributes") or ["general"]),
            creative_antagonist=brief.get("creative_antagonist") or "mainstream trends",
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
    Pipeline Step 5: Organizes the raw research context into a
    clean, bulleted list to prepare for final JSON generation.
    """

    async def process(self, context: RunContext) -> RunContext:
        # This processor is also unchanged.
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
    Pipeline Step 6: Uses the reliable "divide and conquer" method to
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
            context, context.structured_research_context
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
        self, context: RunContext, research_context: str
    ) -> Optional[Dict]:
        """Breaks the synthesis task into smaller, reliable, schema-driven API calls."""
        final_report = {}
        brief = context.enriched_brief

        # STEP 1: Generate Top-Level Fields
        self.logger.info("✨ Step 1/5: Generating top-level fields...")
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
            self.logger.error("❌ Failed to generate top-level fields.")
            return None

        # STEP 2: Generate Narrative Setting
        self.logger.info("✨ Step 2/5: Generating narrative setting...")
        setting_prompt = prompt_library.NARRATIVE_SETTING_PROMPT.format(
            overarching_theme=final_report.get("overarching_theme", ""),
            cultural_drivers=", ".join(final_report.get("cultural_drivers", [])),
        )
        setting_response = await gemini_client.generate_content_async(
            prompt_parts=[setting_prompt]
        )

        narrative_desc = "A minimalist, contemporary architectural setting."
        if setting_response and setting_response.get("text"):
            try:
                json_text = (
                    setting_response["text"]
                    .strip()
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                setting_data = json.loads(json_text)
                base_narrative = setting_data.get("narrative_setting", narrative_desc)
                time_of_day = setting_data.get("time_of_day")
                weather = setting_data.get("weather_condition")
                full_narrative = base_narrative
                if time_of_day:
                    full_narrative += f" The scene is set during the {time_of_day}."
                if weather:
                    full_narrative += f" The weather is {weather}."
                narrative_desc = full_narrative
            except (json.JSONDecodeError, KeyError):
                self.logger.warning(
                    "⚠️ Could not parse narrative setting JSON. Using fallback."
                )
        final_report["narrative_setting_description"] = narrative_desc

        # STEP 3: Generate Accessories
        self.logger.info("✨ Step 3/5: Generating accessories...")
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
        self.logger.info("✨ Step 4/5: Generating detailed key pieces...")
        key_piece_sections = research_context.split("Key Piece ")[1:]
        processed_pieces = []
        for i, section in enumerate(key_piece_sections):
            self.logger.info(
                f"🔄 Processing Key Piece {i + 1}/{len(key_piece_sections)}..."
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
                    self.logger.warning(
                        f"⚠️ Validation failed for Key Piece {i + 1}: {e}"
                    )
            else:
                self.logger.error(f"❌ Failed to get a response for Key Piece {i + 1}.")
        final_report["detailed_key_pieces"] = processed_pieces

        # STEP 5: Assemble and Validate
        self.logger.info("✨ Step 5/5: Assembling and validating final report...")
        final_report["prompt_metadata"] = PromptMetadata(
            run_id=context.run_id, user_passage=context.user_passage
        ).model_dump(mode="json")
        final_report["season"] = brief.get("season", "")
        final_report["year"] = brief.get("year", 0)
        final_report["region"] = brief.get("region")
        final_report["target_model_ethnicity"] = "Diverse"

        # --- START OF FIX: REINTRODUCE DEFENSIVE PARSING BLOCK ---
        # This handles cases where the AI returns the accessories as a JSON string
        # instead of a proper dictionary object.
        accessories_data = final_report.get("accessories")
        if isinstance(accessories_data, str):
            try:
                self.logger.warning(
                    "⚠️ Accessories field was a string. Attempting to parse JSON."
                )
                final_report["accessories"] = json.loads(accessories_data)
            except json.JSONDecodeError:
                self.logger.error(
                    "❌ Failed to parse accessories string. Defaulting to empty dict."
                )
                final_report["accessories"] = {}
        # --- END OF FIX ---

        try:
            validated_report = FashionTrendReport.model_validate(final_report)
            return validated_report.model_dump(mode="json")
        except ValidationError as e:
            self.logger.critical(
                f"❌ The final assembled report from divide-and-conquer failed validation: {e}"
            )
            return None


class DirectKnowledgeSynthesisProcessor(BaseProcessor):
    """
    Pipeline Fallback Step: Generates the entire trend report using a robust,
    multi-step process guided by the brand ethos and the model's internal knowledge,
    now fully compatible with the enhanced, professional-grade data model.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.warning("⚙️ Activating direct knowledge fallback pipeline.")
        self.logger.info(
            "✨ Generating report directly from Gemini's internal knowledge base..."
        )

        final_report_data = await self._generate_report_with_internal_knowledge(context)

        if not final_report_data:
            self.logger.critical(
                "❌ Direct knowledge synthesis also failed. The model could not generate a report."
            )
            raise RuntimeError("The fallback knowledge synthesis process failed.")

        self.logger.info("✅ Success: Generated report using direct knowledge.")
        context.final_report = final_report_data
        return context

    async def _generate_report_with_internal_knowledge(
        self, context: RunContext
    ) -> Optional[Dict]:
        """
        Breaks the synthesis task into smaller, reliable, schema-driven API calls
        using the model's internal knowledge, now generating the enhanced data model.
        """
        final_report = {}
        brief = context.enriched_brief
        brand_ethos = context.brand_ethos
        ethos = brand_ethos or "A focus on creating a beautiful and compelling design."
        brief_context_str = json.dumps(brief, indent=2)

        # STEP 1: Generate Top-Level Fields
        self.logger.info("✨ Fallback Step 1/4: Generating top-level fields...")

        class TopLevelModel(BaseModel):
            overarching_theme: str
            cultural_drivers: List[str]
            influential_models: List[str]

        top_level_prompt = f"""
        Based on your internal knowledge, the creative brief, and the guiding philosophy below, generate the top-level fashion concepts.

        GUIDING PHILOSOPHY (ETHOS):
        {ethos}

        CREATIVE BRIEF:
        {brief_context_str}
        """
        top_level_response = await gemini_client.generate_content_async(
            prompt_parts=[top_level_prompt],
            response_schema=TopLevelModel,
        )
        if top_level_response:
            final_report.update(top_level_response)
        else:
            self.logger.error("❌ Fallback failed to generate top-level fields.")
            return None

        # STEP 2: Generate Narrative Setting (Updated for new JSON structure)
        self.logger.info("✨ Fallback Step 2/4: Generating narrative setting...")
        setting_prompt = prompt_library.NARRATIVE_SETTING_PROMPT.format(
            overarching_theme=final_report.get("overarching_theme", ""),
            cultural_drivers=", ".join(final_report.get("cultural_drivers", [])),
        )
        setting_response = await gemini_client.generate_content_async(
            prompt_parts=[setting_prompt]
        )

        narrative_desc = "A minimalist, contemporary architectural setting."  # Fallback
        if setting_response and setting_response.get("text"):
            try:
                json_text = (
                    setting_response["text"]
                    .strip()
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                setting_data = json.loads(json_text)
                base_narrative = setting_data.get("narrative_setting", narrative_desc)
                time_of_day = setting_data.get("time_of_day")
                weather = setting_data.get("weather_condition")

                full_narrative = base_narrative
                if time_of_day:
                    full_narrative += f" The scene is set during the {time_of_day}."
                if weather:
                    full_narrative += f" The weather is {weather}."
                narrative_desc = full_narrative

            except (json.JSONDecodeError, KeyError):
                self.logger.warning(
                    "⚠️ Fallback could not parse narrative setting JSON. Using basic text."
                )

        final_report["narrative_setting_description"] = narrative_desc

        # STEP 3: Generate Accessories
        self.logger.info("✨ Fallback Step 3/4: Generating accessories...")

        class AccessoriesModel(BaseModel):
            accessories: Dict[str, List[str]]

        accessories_prompt = f"""
        Based on your internal knowledge, the creative brief, and the guiding philosophy below, generate a list of relevant accessories.

        GUIDING PHILOSOPHY (ETHOS):
        {ethos}

        CREATIVE BRIEF:
        {brief_context_str}
        """
        accessories_response = await gemini_client.generate_content_async(
            prompt_parts=[accessories_prompt],
            response_schema=AccessoriesModel,
        )
        final_report.update(accessories_response or {"accessories": {}})

        # STEP 4: Generate Key Pieces (Updated to use the new, richer model)
        self.logger.info("✨ Fallback Step 4/4: Generating detailed key pieces...")

        class KeyPieceNames(BaseModel):
            names: List[str]

        key_pieces_names_prompt = f"""
        Based on the creative brief and ethos below, generate a list of 2-3 creative and descriptive names for key fashion pieces that fit the theme.

        GUIDING PHILOSOPHY (ETHOS):
        {ethos}

        CREATIVE BRIEF:
        {brief_context_str}
        """
        names_response = await gemini_client.generate_content_async(
            prompt_parts=[key_pieces_names_prompt],
            response_schema=KeyPieceNames,
        )

        processed_pieces = []
        if names_response and names_response.get("names"):
            for i, piece_name in enumerate(names_response["names"]):
                self.logger.info(
                    f"🔄 Processing Key Piece '{piece_name}' ({i + 1}/{len(names_response['names'])})..."
                )

                # The prompt now implicitly asks for the new, richer model via response_schema
                key_piece_prompt = f"""
                You are a fashion expert and technical designer. Based on the creative brief and guiding philosophy below, generate the detailed JSON data for a single key piece named '{piece_name}'.
                You MUST include technical details like fabric weight (GSM), drape, finish, detailed pattern information, and lining.

                GUIDING PHILOSOPHY (ETHOS):
                {ethos}

                CREATIVE BRIEF:
                {brief_context_str}
                """
                piece_response = await gemini_client.generate_content_async(
                    prompt_parts=[key_piece_prompt], response_schema=KeyPieceDetail
                )
                if piece_response:
                    try:
                        validated_piece = KeyPieceDetail.model_validate(piece_response)
                        processed_pieces.append(validated_piece.model_dump(mode="json"))
                    except ValidationError as e:
                        self.logger.warning(
                            f"⚠️ Validation failed for Key Piece '{piece_name}': {e}"
                        )
                else:
                    self.logger.error(
                        f"❌ Failed to get a response for Key Piece '{piece_name}'."
                    )
        final_report["detailed_key_pieces"] = processed_pieces

        # STEP 5: Assemble and Validate (Updated with metadata)
        self.logger.info(
            "✨ Fallback Step 5/5: Assembling and validating final report..."
        )
        final_report["prompt_metadata"] = PromptMetadata(
            run_id=context.run_id, user_passage=context.user_passage
        ).model_dump(mode="json")
        final_report["season"] = brief.get("season", "")
        final_report["year"] = brief.get("year", 0)
        final_report["region"] = brief.get("region")
        final_report["target_model_ethnicity"] = "Diverse"

        try:
            validated_report = FashionTrendReport.model_validate(final_report)
            return validated_report.model_dump(mode="json")
        except ValidationError as e:
            self.logger.critical(
                f"❌ The final assembled report from the fallback process failed validation: {e}"
            )
            return None
