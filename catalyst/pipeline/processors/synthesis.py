# catalyst/pipeline/processors/synthesis.py

import asyncio
from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ...utilities.config_loader import FORMATTED_SOURCES
from ..synthesis_strategies.report_assembler import ReportAssembler

# --- START: REFACTOR ---
# Import the new settings
from ... import settings

# --- END: REFACTOR ---


class WebResearchProcessor(BaseProcessor):
    """
    Pipeline Step 4: Instructs the LLM to perform a web search and return a
    single, unstructured block of text summarizing its findings. Implements a
    self-healing mechanism to ensure the output is well-structured.
    """

    async def _validate_and_repair_context(self, research_context: str) -> str:
        """Checks for a critical heading and asks the AI to repair the text if it's missing."""
        if "<key_garments>" in research_context.lower():
            self.logger.info(
                "✅ Web research context contains the required '<key_garments>' tag."
            )
            return research_context

        self.logger.warning(
            "⚠️ Research context is missing '<key_garments>' tag. Attempting self-repair..."
        )
        repair_prompt = prompt_library.CONTEXT_REPAIR_PROMPT.format(
            research_context=research_context
        )
        response = await gemini.generate_content_async(prompt_parts=[repair_prompt])
        if response and response.get("text"):
            self.logger.info("✅ Successfully repaired research context.")
            return response["text"]

        self.logger.error(
            "❌ Failed to repair research context. Proceeding with original, flawed text."
        )
        return research_context

    async def process(self, context: RunContext) -> RunContext:
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
            antagonist_synthesis=context.antagonist_synthesis
            or "No specific synthesis provided.",
            search_keywords=", ".join(brief.get("search_keywords", [])),
        )

        # --- START: REFACTOR ---
        # Use the centralized retry count from the settings file
        for attempt in range(settings.TEXT_PROCESSOR_MAX_RETRIES):
            self.logger.info(
                f"Attempt {attempt + 1}/{settings.TEXT_PROCESSOR_MAX_RETRIES} to conduct web research..."
            )
            # --- END: REFACTOR ---
            api_response = await gemini.generate_content_async(prompt_parts=[prompt])
            if api_response and api_response.get("text"):
                self.logger.info(
                    f"✅ Successfully received web research content on attempt {attempt + 1}."
                )
                repaired_context = await self._validate_and_repair_context(
                    api_response["text"]
                )
                context.raw_research_context = repaired_context
                return context

            self.logger.warning(
                f"⚠️ Web research attempt {attempt + 1} returned no content. Retrying..."
            )
            if attempt < settings.TEXT_PROCESSOR_MAX_RETRIES - 1:
                await asyncio.sleep(2)

        self.logger.error(
            "❌ Web research returned no content after all retry attempts. Fallback will be triggered."
        )
        context.raw_research_context = ""
        return context


class ContextStructuringProcessor(BaseProcessor):
    """
    Pipeline Step 5: Organizes the raw research context into a clean,
    bulleted list to prepare for final JSON generation.
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
        instruction = (
            f"Focus exclusively on the specified garment type: **{brief.get('garment_type', 'clothing')}**. Generate 2-3 distinct variations or interpretations of this single garment."
            if brief.get("garment_type")
            else "Identify 2-3 distinct and compelling key garment pieces from the research. They should be different types (e.g., one coat, one cape)."
        )

        prompt = prompt_library.STRUCTURING_PREP_PROMPT.format(
            theme_hint=brief.get("theme_hint", ""),
            garment_type=brief.get("garment_type", "not specified"),
            research_context=context.raw_research_context,
            garment_generation_instruction=instruction,
        )

        # --- START: REFACTOR ---
        # Use the centralized retry count from the settings file
        for attempt in range(settings.TEXT_PROCESSOR_MAX_RETRIES):
            # --- END: REFACTOR ---
            response = await gemini.generate_content_async(prompt_parts=[prompt])
            if response and response.get("text"):
                self.logger.info(
                    f"✅ Success: Created pre-structured context outline ({len(response['text'])} characters)."
                )
                context.structured_research_context = response["text"]
                return context
            self.logger.warning(
                f"⚠️ Pre-structuring step failed on attempt {attempt+1}. Retrying..."
            )

        self.logger.error(
            "❌ Pre-structuring failed after all retries. Using raw context as fallback."
        )
        context.structured_research_context = context.raw_research_context
        return context


class ReportSynthesisProcessor(BaseProcessor):
    """
    Pipeline Step 6 (Primary Path): Delegates the task of building the final
    report to the ReportAssembler, using the structured web research context.
    """

    # ... (This class is unchanged as its dependencies are now resilient) ...
    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Starting primary report synthesis path...")

        if not context.structured_research_context:
            self.logger.warning(
                "⚠️ Structured research context is empty. Skipping primary synthesis."
            )
            return context

        assembler = ReportAssembler(context)
        final_report_data = await assembler.assemble_report()

        if final_report_data:
            self.logger.info(
                "✅ Success: Assembled and validated the final trend report via primary path."
            )
            context.final_report = final_report_data
        else:
            self.logger.error(
                "❌ The primary synthesis process failed to produce a valid final report."
            )

        return context


class DirectKnowledgeSynthesisProcessor(BaseProcessor):
    """
    Pipeline Fallback Step: Delegates the task of building the final report
    to the ReportAssembler, using the model's internal knowledge guided by the
    enriched brief and brand ethos.
    """

    # ... (This class is unchanged as its dependencies are now resilient) ...
    async def process(self, context: RunContext) -> RunContext:
        self.logger.warning("⚙️ Activating direct knowledge fallback synthesis path.")

        assembler = ReportAssembler(context)
        final_report_data = await assembler.assemble_report()

        if final_report_data:
            self.logger.info(
                "✅ Success: Generated and validated report using direct knowledge fallback."
            )
            context.final_report = final_report_data
        else:
            self.logger.critical(
                "❌ Direct knowledge synthesis also failed. The model could not generate a report."
            )

        return context
