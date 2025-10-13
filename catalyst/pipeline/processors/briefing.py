# catalyst/pipeline/processors/briefing.py

"""
This module contains the processors for the briefing stage, refactored for
efficiency by consolidating multiple AI calls into a single, powerful step.
"""

import json
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any, List, Union
import re

from pydantic import BaseModel, Field

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ...resilience import invoke_with_resilience, MaxRetriesExceededError


# --- Pydantic Models for Structured Output ---


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

    # --- START: NEW FIELDS FOR DYNAMIC GENERATION ---
    generation_strategy: str = Field(
        description="The strategy to use: 'collection', 'variations', or 'specified_items'."
    )
    explicit_garments: Optional[List[str]] = Field(
        None, description="A list of specific garments the user requested, if any."
    )
    # --- END: NEW FIELDS ---


class ConsolidatedBriefingModel(BaseModel):
    """The new, efficient model for the consolidated briefing step."""

    ethos: str = Field(..., description="The distilled, single-paragraph brand ethos.")
    expanded_concepts: List[str] = Field(
        ..., description="A list of 3-5 high-level, tangential creative concepts."
    )
    search_keywords: List[str] = Field(
        ...,
        description="A list of 10-15 actionable search keywords derived from the concepts.",
    )


class AntagonistSynthesisModel(BaseModel):
    antagonist_synthesis: str = Field(
        ...,
        description="A single, innovative design synthesis that elevates the core theme.",
    )


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
            brief_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=StructuredBriefModel,
            )
            initial_brief = self._apply_operational_defaults(brief_model.model_dump())
            context.enriched_brief = initial_brief
            context.theme_slug = self._create_slug(initial_brief.get("theme_hint"))
            self.logger.info(f"✅ Generated theme slug: '{context.theme_slug}'")
            self.logger.info(
                "✅ Success: Deconstructed and inferred a complete initial brief."
            )
            return context
        except MaxRetriesExceededError as e:
            self.logger.critical(
                "❌ Deconstruction failed after all retries. Halting pipeline.",
                exc_info=e,
            )
            raise ValueError(
                "Brief deconstruction failed permanently after multiple retries."
            ) from e

    def _apply_operational_defaults(self, brief_data: Dict) -> Dict:
        if brief_data.get("season") == "auto":
            current_month = datetime.now().month
            brief_data["season"] = (
                "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
            )
        if brief_data.get("year") == "auto" or not brief_data.get("year"):
            brief_data["year"] = str(datetime.now().year)
        return brief_data


class ConsolidatedBriefingProcessor(BaseProcessor):
    async def process(self, context: RunContext) -> RunContext:
        self.logger.info(
            "🔬 Performing consolidated briefing (ethos, concepts, keywords)..."
        )
        try:
            prompt = prompt_library.CONSOLIDATED_BRIEFING_PROMPT.format(
                user_passage=context.user_passage,
                theme_hint=context.enriched_brief.get("theme_hint", ""),
                briefing_schema=json.dumps(
                    ConsolidatedBriefingModel.model_json_schema()
                ),
            )
            briefing_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=ConsolidatedBriefingModel,
            )
            context.brand_ethos = briefing_model.ethos
            context.enriched_brief["expanded_concepts"] = (
                briefing_model.expanded_concepts
            )
            search_keywords = set(context.enriched_brief.get("search_keywords", []))
            if context.enriched_brief.get("theme_hint"):
                search_keywords.add(context.enriched_brief["theme_hint"])
            search_keywords.update(briefing_model.search_keywords)
            context.enriched_brief["search_keywords"] = sorted(list(search_keywords))
            self.logger.info("✅ Success: Consolidated briefing complete.")
        except MaxRetriesExceededError:
            self.logger.warning(
                "⚠️ Consolidated briefing failed. Proceeding with minimal data."
            )
            context.brand_ethos = ""
            context.enriched_brief["expanded_concepts"] = []
        return context


class CreativeAntagonistProcessor(BaseProcessor):
    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("🎨 Generating creative antagonist synthesis...")
        try:
            prompt = prompt_library.CREATIVE_ANTAGONIST_PROMPT.format(
                theme_hint=context.enriched_brief.get("theme_hint", "general fashion"),
                brand_ethos=context.brand_ethos or "No specific ethos provided.",
            )
            model = await invoke_with_resilience(
                gemini.generate_content_async, prompt, AntagonistSynthesisModel
            )
            context.antagonist_synthesis = model.antagonist_synthesis
            self.logger.info("✅ Success: Creative antagonist generated.")
        except MaxRetriesExceededError:
            self.logger.warning(
                "⚠️ Creative antagonist generation failed. Proceeding without it."
            )
            context.antagonist_synthesis = ""
        return context
