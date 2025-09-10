# catalyst/pipeline/processors/synthesis.py

"""
This module contains the processors for the core synthesis stage of the pipeline.

These processors are designed as lean controllers that manage the flow of data
into the synthesis strategies. The complex, multi-step logic of actually building
the report is encapsulated in the `ReportAssembler` strategy, ensuring this module
remains clean, readable, and focused on its role within the pipeline orchestration.
"""

import asyncio
from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ...utilities.config_loader import FORMATTED_SOURCES
from ..synthesis_strategies.report_assembler import ReportAssembler


class WebResearchProcessor(BaseProcessor):
    """
    Pipeline Step 4: Instructs the LLM to perform a web search and return a
    single, unstructured block of text summarizing its findings. Implements
    a retry mechanism for transient errors or empty responses.
    """

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

        # --- START OF DEFINITIVE FIX ---
        # Implement a retry loop to handle transient API errors or empty responses
        # before resorting to the full fallback path.
        response = None
        MAX_RETRIES = 3
        RETRY_DELAY_SECONDS = 2

        for attempt in range(MAX_RETRIES):
            self.logger.info(
                f"Attempt {attempt + 1}/{MAX_RETRIES} to conduct web research..."
            )
            api_response = await gemini.generate_content_async(prompt_parts=[prompt])
            if api_response and api_response.get("text"):
                self.logger.info(
                    f"✅ Successfully received web research content on attempt {attempt + 1}."
                )
                response = api_response
                break  # Exit the loop on success
            else:
                self.logger.warning(
                    f"⚠️ Web research attempt {attempt + 1} returned no content. Retrying in {RETRY_DELAY_SECONDS}s..."
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        # --- END OF DEFINITIVE FIX ---

        if response and response.get("text"):
            self.logger.info(
                f"✅ Success: Synthesized {len(response['text'])} characters of raw text from web research."
            )
            context.raw_research_context = response["text"]
        else:
            self.logger.error(
                "❌ Web research returned no content after all retry attempts. The fallback path will now be triggered."
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
        response = await gemini.generate_content_async(prompt_parts=[prompt])

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
    Pipeline Step 6 (Primary Path): Delegates the task of building the final
    report to the ReportAssembler, using the structured web research context.
    """

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
