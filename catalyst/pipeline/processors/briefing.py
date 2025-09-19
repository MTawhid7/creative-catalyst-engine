# catalyst/pipeline/processors/briefing.py

"""
This module contains the processors for the briefing stage, now with
fully schema-driven, structured outputs for all AI calls.
"""

import json
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any, List, Union
import re

from pydantic import BaseModel, Field, ValidationError

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ...utilities.json_parser import parse_json_from_llm_output

# --- START: RESILIENCE REFACTOR ---
from ...resilience import invoke_with_resilience, MaxRetriesExceededError
# --- END: RESILIENCE REFACTOR ---


# --- Pydantic models for structured output ---
class ConceptsModel(BaseModel):
    concepts: List[str] = Field(
        ..., description="A list of 3-5 high-level creative concepts."
    )

class AntagonistSynthesisModel(BaseModel):
    """A model for the output of the creative synthesis prompt."""
    antagonist_synthesis: str = Field(
        ...,
        description="A single, innovative design synthesis that elevates the core theme.",
    )

class KeywordsModel(BaseModel):
    keywords: List[str] = Field(..., description="A list of relevant search keywords.")

# A model for the simple, single-key JSON from the ethos prompt.
class EthosModel(BaseModel):
    ethos: str


# A full Pydantic model for the complex, structured brief.
# This replaces the old, unsafe dictionary.
class StructuredBriefModel(BaseModel):
    theme_hint: str
    garment_type: Union[str, List[str]]
    brand_category: Union[str, List[str]]
    target_audience: str
    region: Union[str, List[str]]
    key_attributes: List[str]
    season: Union[str, List[str]]
    year: Union[str, int, List[Union[str, int]]]
    target_gender: str
    target_model_ethnicity: str
    target_age_group: str
    desired_mood: List[str]


class BriefDeconstructionProcessor(BaseProcessor):
    """
    Pipeline Step 1: Intelligently deconstructs the user's passage into a
    structured brief, inferring missing creative details from the core theme.
    """

    def _create_slug(self, text: Optional[str]) -> str:
        if not text:
            return "untitled"
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"[\s-]+", "-", text).strip("-")
        slug = text[:15]
        return slug.strip("-")

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Performing intelligent deconstruction of user passage...")

        prompt = prompt_library.INTELLIGENT_DECONSTRUCTION_PROMPT.format(
            user_passage=context.user_passage
        )

        try:
            # --- START: RESILIENCE REFACTOR ---
            # Now we can use our robust invoker because the prompt returns pure JSON.
            brief_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=StructuredBriefModel,
            )
            initial_brief = self._apply_operational_defaults(brief_model.model_dump())
            context.enriched_brief = initial_brief
            # --- END: RESILIENCE REFACTOR ---

            context.theme_slug = self._create_slug(initial_brief.get("theme_hint"))
            self.logger.info(f"✅ Generated theme slug: '{context.theme_slug}'")
            self.logger.info(
                "✅ Success: Deconstructed and inferred a complete initial brief."
            )
            return context

        except MaxRetriesExceededError as e:
            # This is the very first, most critical step. If we can't even get a brief,
            # the entire pipeline must stop. We raise a critical error.
            self.logger.critical(
                "❌ Deconstruction failed after all retries. Halting pipeline.",
                exc_info=e,
            )
            raise ValueError(
                "Brief deconstruction failed permanently after multiple retries."
            ) from e

    def _apply_operational_defaults(self, brief_data: Dict) -> Dict:
        """Applies essential, non-creative defaults that don't require AI."""
        if brief_data.get("season") == "auto":
            current_month = datetime.now().month
            brief_data["season"] = (
                "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
            )

        if brief_data.get("year") == "auto" or not brief_data.get("year"):
            brief_data["year"] = str(datetime.now().year)

        return brief_data


class EthosClarificationProcessor(BaseProcessor):
    """
    Pipeline Step 2: Analyzes the user's passage for an underlying brand ethos.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("🔬 Analyzing user passage for deeper brand ethos...")
        prompt = prompt_library.ETHOS_ANALYSIS_PROMPT.format(
            user_passage=context.user_passage
        )

        # --- START: RESILIENCE REFACTOR ---
        try:
            # Use the invoker for a robust call
            ethos_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=EthosModel
            )
            context.brand_ethos = ethos_model.ethos
            self.logger.info("✅ Success: Distilled brand ethos.")
        except MaxRetriesExceededError:
            self.logger.warning("⚠️ Ethos analysis failed after all retries. Proceeding without it.")
            context.brand_ethos = "" # Provide a safe default

        return context
        # --- END: RESILIENCE REFACTOR ---


class BriefEnrichmentProcessor(BaseProcessor):
    """
    Pipeline Step 3: Expands the initial brief with AI-driven creative concepts.
    """

    async def _get_concepts(self, prompt_args: Dict) -> List[str]:
        prompt = prompt_library.THEME_EXPANSION_PROMPT.format(**prompt_args)
        try:
            model = await invoke_with_resilience(gemini.generate_content_async, prompt, ConceptsModel)
            return model.concepts
        except MaxRetriesExceededError:
            self.logger.warning("Failed to generate concepts. Returning empty list.")
            return []

    async def _get_synthesis(self, prompt_args: Dict) -> str:
        prompt = prompt_library.CREATIVE_ANTAGONIST_PROMPT.format(**prompt_args)
        try:
            model = await invoke_with_resilience(gemini.generate_content_async, prompt, AntagonistSynthesisModel)
            return model.antagonist_synthesis
        except MaxRetriesExceededError:
            self.logger.warning("Failed to generate antagonist synthesis. Proceeding without it.")
            return ""

    async def _get_keywords(self, concepts: List[str]) -> List[str]:
        if not concepts:
            return []
        prompt = prompt_library.KEYWORD_EXTRACTION_PROMPT.format(concepts_list=json.dumps(concepts))
        try:
            model = await invoke_with_resilience(gemini.generate_content_async, prompt, KeywordsModel)
            return model.keywords
        except MaxRetriesExceededError:
            self.logger.warning("Failed to extract keywords. Returning empty list.")
            return []

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Enriching brief with AI-driven creative concepts and keywords...")

        garment_type_raw = context.enriched_brief.get("garment_type", "clothing")
        garment_type_str = (
            ", ".join(garment_type_raw)
            if isinstance(garment_type_raw, list)
            else garment_type_raw
        )

        concept_prompt_args = {
            "theme_hint": context.enriched_brief.get("theme_hint", "general fashion"),
            "garment_type": garment_type_str,
            "key_attributes": ", ".join(
                context.enriched_brief.get("key_attributes", [])
            ),
            "brand_ethos": context.brand_ethos or "No specific ethos provided.",
        }
        antagonist_prompt_args = {"theme_hint": context.enriched_brief.get("theme_hint", "general fashion")}

        # --- START: RESILIENCE REFACTOR ---
        # Run concept and synthesis generation concurrently
        concepts_list, synthesis_text = await asyncio.gather(
            self._get_concepts(concept_prompt_args),
            self._get_synthesis(antagonist_prompt_args)
        )

        # Get keywords based on the results of the first batch
        keywords_list = await self._get_keywords(concepts_list)

        # Update the context and brief
        context.antagonist_synthesis = synthesis_text
        context.enriched_brief["expanded_concepts"] = concepts_list

        search_keywords = set(context.enriched_brief.get("search_keywords", []))
        if context.enriched_brief.get("theme_hint"):
            search_keywords.add(context.enriched_brief["theme_hint"])
        search_keywords.update(keywords_list)
        context.enriched_brief["search_keywords"] = sorted(list(search_keywords))
        # --- END: RESILIENCE REFACTOR ---

        self.logger.info(f"✅ Success: Brief enriched. Found {len(context.enriched_brief.get('search_keywords', []))} keywords.")
        return context
