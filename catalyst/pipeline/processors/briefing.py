# catalyst/pipeline/processors/briefing.py

"""
This module contains the processors for the briefing stage, now with
fully schema-driven, structured outputs for all AI calls.
"""

import json
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any, List
import re

# --- START OF FIX: Add all required imports and class definitions ---
from pydantic import BaseModel, Field

# --- END OF FIX ---

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini
from ...prompts import prompt_library
from ...utilities.json_parser import parse_json_from_llm_output


# --- START OF FIX: Define Pydantic models for structured output ---
class ConceptsModel(BaseModel):
    concepts: List[str] = Field(
        ..., description="A list of 3-5 high-level creative concepts."
    )


class AntagonistModel(BaseModel):
    antagonist: str = Field(
        ..., description="A short, powerful phrase for the creative antagonist."
    )


class KeywordsModel(BaseModel):
    keywords: List[str] = Field(..., description="A list of relevant search keywords.")


# --- END OF FIX ---


class BriefDeconstructionProcessor(BaseProcessor):
    """
    Pipeline Step 1: Intelligently deconstructs the user's passage into a
    structured brief, inferring missing creative details from the core theme.
    """

    def _create_slug(self, text: Optional[str]) -> str:
        """Generates a clean, URL-friendly slug from a string."""
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
        response_data = await gemini.generate_content_async(prompt_parts=[prompt])

        if not response_data or "text" not in response_data:
            self.logger.error(
                "❌ AI failed to deconstruct/infer the brief.",
                extra={"response": response_data},
            )
            raise ValueError("Brief deconstruction AI call failed.")

        extracted_data = parse_json_from_llm_output(response_data["text"])

        initial_brief = self._validate_and_apply_operational_defaults(extracted_data)

        if not initial_brief:
            self.logger.critical(
                "❌ Intelligent deconstruction failed. Halting pipeline."
            )
            raise ValueError(
                "Brief deconstruction failed after parsing. Check logs for details."
            )

        context.enriched_brief = initial_brief
        context.theme_slug = self._create_slug(initial_brief.get("theme_hint"))
        self.logger.info(f"✅ Generated theme slug: '{context.theme_slug}'")
        self.logger.info(
            "✅ Success: Deconstructed and inferred a complete initial brief."
        )
        return context

    def _validate_and_apply_operational_defaults(
        self, extracted_data: Optional[Dict]
    ) -> Optional[Dict]:
        """Applies essential, non-creative defaults and validates the structure."""
        if not isinstance(extracted_data, dict):
            self.logger.error("❌ Deconstruction did not return a dictionary.")
            return None

        if extracted_data.get("season") == "auto":
            current_month = datetime.now().month
            extracted_data["season"] = (
                "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
            )

        year_value = extracted_data.get("year")
        if year_value == "auto" or not year_value:
            extracted_data["year"] = datetime.now().year
        else:
            try:
                extracted_data["year"] = int(year_value)
            except (ValueError, TypeError):
                self.logger.warning(
                    f"⚠️ Could not parse '{year_value}' as a year. Defaulting to current year."
                )
                extracted_data["year"] = datetime.now().year

        if not extracted_data.get("theme_hint"):
            self.logger.critical(
                "❌ Missing required variable 'theme_hint' after deconstruction."
            )
            return None

        return extracted_data


class EthosClarificationProcessor(BaseProcessor):
    """
    Pipeline Step 2: Analyzes the user's passage for an underlying brand ethos.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("🔬 Analyzing user passage for deeper brand ethos...")
        prompt = prompt_library.ETHOS_ANALYSIS_PROMPT.format(
            user_passage=context.user_passage
        )
        response_data = await gemini.generate_content_async(prompt_parts=[prompt])

        if response_data and response_data.get("text"):
            data = parse_json_from_llm_output(response_data["text"])
            if data and isinstance(data, dict) and "ethos" in data:
                context.brand_ethos = data["ethos"]
                self.logger.info("✅ Success: Distilled brand ethos.")
                self.logger.debug(f"Found Ethos: {data['ethos']}")
            else:
                self.logger.warning(
                    "⚠️ Ethos analysis returned malformed or incomplete JSON. Skipping."
                )
        else:
            self.logger.warning("⚠️ Ethos analysis returned no content. Skipping.")
        return context


class BriefEnrichmentProcessor(BaseProcessor):
    """
    Pipeline Step 3: Expands the initial brief with AI-driven creative concepts.
    """

    async def _get_enrichment_data_async(
        self,
        prompt: str,
        response_schema: Optional[type[BaseModel]],
        task_name: str,
    ) -> Optional[Dict]:
        """A resilient helper that attempts to get structured enrichment data."""
        self.logger.debug(f"⏳ Attempting to generate {task_name}...")

        response_data = await gemini.generate_content_async(
            prompt_parts=[prompt], response_schema=response_schema
        )

        if response_data and isinstance(response_data, dict):
            self.logger.debug(
                f"✅ Successfully received structured data for {task_name}."
            )
            return response_data

        self.logger.error(
            f"❌ Failed to get structured data for {task_name} after retries."
        )
        return None

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info(
            "⚙️ Enriching brief with AI-driven creative concepts and keywords..."
        )

        concept_prompt_args = {
            "theme_hint": context.enriched_brief.get("theme_hint", "general fashion"),
            "garment_type": context.enriched_brief.get("garment_type", "clothing"),
            "key_attributes": ", ".join(
                context.enriched_brief.get("key_attributes", [])
            ),
            "brand_ethos": context.brand_ethos or "No specific ethos provided.",
        }
        antagonist_prompt_args = {
            "theme_hint": context.enriched_brief.get("theme_hint", "general fashion")
        }

        expansion_task = self._get_enrichment_data_async(
            prompt=prompt_library.THEME_EXPANSION_PROMPT.format(**concept_prompt_args),
            response_schema=ConceptsModel,
            task_name="concepts",
        )
        antagonist_task = self._get_enrichment_data_async(
            prompt=prompt_library.CREATIVE_ANTAGONIST_PROMPT.format(
                **antagonist_prompt_args
            ),
            response_schema=AntagonistModel,
            task_name="antagonist",
        )

        concepts_result, antagonist_result = await asyncio.gather(
            expansion_task, antagonist_task
        )

        context.enriched_brief["expanded_concepts"] = (
            concepts_result.get("concepts", []) if concepts_result else []
        )
        context.enriched_brief["creative_antagonist"] = (
            antagonist_result.get("antagonist") if antagonist_result else None
        )

        search_keywords = set(context.enriched_brief.get("search_keywords", []))
        if context.enriched_brief.get("theme_hint"):
            search_keywords.add(context.enriched_brief["theme_hint"])

        if context.enriched_brief.get("expanded_concepts"):
            extraction_prompt = prompt_library.KEYWORD_EXTRACTION_PROMPT.format(
                concepts_list=json.dumps(context.enriched_brief["expanded_concepts"])
            )
            keyword_response = await self._get_enrichment_data_async(
                prompt=extraction_prompt,
                response_schema=KeywordsModel,
                task_name="keywords",
            )
            if keyword_response and keyword_response.get("keywords"):
                search_keywords.update(keyword_response["keywords"])

        context.enriched_brief["search_keywords"] = sorted(list(search_keywords))

        self.logger.info(
            f"✅ Success: Brief enriched. Found {len(context.enriched_brief.get('search_keywords', []))} keywords."
        )
        return context
