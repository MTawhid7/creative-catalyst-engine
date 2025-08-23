"""
This module contains the processors for the briefing stage.
The deconstruction processor is an "intelligent" step that infers
contextually relevant defaults for any missing creative information.
"""

import json
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini_client
from ...prompts import prompt_library


class BriefDeconstructionProcessor(BaseProcessor):
    """
    Pipeline Step 1: Intelligently deconstructs the user's passage into a
    structured brief, inferring missing creative details from the core theme.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("⚙️ Performing intelligent deconstruction of user passage...")

        extracted_data = await self._deconstruct_and_infer_async(context.user_passage)
        initial_brief = self._validate_and_apply_operational_defaults(extracted_data)

        if not initial_brief:
            self.logger.critical(
                "❌ Intelligent deconstruction failed to produce a valid initial brief. Halting pipeline."
            )
            raise ValueError("Brief deconstruction failed. Check logs for details.")

        context.enriched_brief = initial_brief
        self.logger.info(
            "✅ Success: Deconstructed and inferred a complete initial brief."
        )
        return context

    async def _deconstruct_and_infer_async(self, user_passage: str) -> Optional[Dict]:
        """Uses the intelligent prompt to extract and infer a complete brief."""
        prompt = prompt_library.INTELLIGENT_DECONSTRUCTION_PROMPT.format(
            user_passage=user_passage
        )

        response_data = await gemini_client.generate_content_async(
            prompt_parts=[prompt]
        )

        if not response_data or "text" not in response_data:
            self.logger.error(
                "❌ AI failed to deconstruct/infer the brief.",
                extra={"response": response_data},
            )
            return None

        try:
            json_text = response_data["text"].strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            return json.loads(json_text)
        except (json.JSONDecodeError, KeyError):
            self.logger.error(
                "🛑 Failed to parse JSON from deconstruction response.",
                exc_info=True,
                extra={"raw_text": response_data.get("text")},
            )
            return None

    def _validate_and_apply_operational_defaults(
        self, extracted_data: Optional[Dict]
    ) -> Optional[Dict]:
        """Applies essential, non-creative defaults (like date/time) and validates the structure."""
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


class BriefEnrichmentProcessor(BaseProcessor):
    """
    Pipeline Step 2: Expands the initial brief with AI-driven creative
    concepts, a strategic antagonist, and searchable keywords for research.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info(
            "⚙️ Enriching brief with AI-driven creative concepts and keywords..."
        )
        enriched_brief = await self._enrich_brief_async(context.enriched_brief)
        context.enriched_brief = enriched_brief
        self.logger.info(
            f"✅ Success: Brief enriched. Found {len(enriched_brief.get('search_keywords', []))} keywords."
        )
        self.logger.debug(f"💡   - Concepts: {enriched_brief.get('expanded_concepts')}")
        self.logger.debug(
            f"🎭   - Antagonist: {enriched_brief.get('creative_antagonist')}"
        )
        return context

    async def _get_enrichment_data_async(
        self,
        initial_prompt: str,
        correction_prompt_template: str,
        prompt_args: Dict,
        task_name: str,
    ) -> Optional[str]:
        """A resilient helper function that attempts to get enrichment data, with a self-correction retry."""
        self.logger.debug(f"⏳ Attempting to generate {task_name} (Attempt 1)...")
        initial_response = await gemini_client.generate_content_async(
            prompt_parts=[initial_prompt]
        )
        if (
            initial_response
            and initial_response.get("text")
            and initial_response["text"].strip()
        ):
            self.logger.debug(
                f"✅ Successfully generated {task_name} on the first attempt."
            )
            return initial_response["text"].strip()

        self.logger.warning(
            f"⚠️ First attempt to generate {task_name} failed or returned empty. Triggering self-correction."
        )
        failed_output = (
            initial_response.get("text", "None") if initial_response else "None"
        )
        correction_prompt = correction_prompt_template.format(
            failed_output=failed_output, **prompt_args
        )

        self.logger.debug(
            f"⏳ Attempting to generate {task_name} (Attempt 2 - Correction)..."
        )
        correction_response = await gemini_client.generate_content_async(
            prompt_parts=[correction_prompt]
        )
        if (
            correction_response
            and correction_response.get("text")
            and correction_response["text"].strip()
        ):
            self.logger.info(
                f"✅ Successfully generated {task_name} on the second (correction) attempt."
            )
            return correction_response["text"].strip()

        self.logger.critical(
            f"❌ Self-correction also failed for {task_name}. The model could not produce a valid output."
        )
        return None

    def _parse_llm_creative_output(self, text: Optional[str], expected_key: str) -> Any:
        """Robustly parses raw LLM text output, handling plain text, lists, and JSON."""
        if not text:
            return None
        cleaned_text = text.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            data = json.loads(cleaned_text)
            return data.get(expected_key)
        except (json.JSONDecodeError, AttributeError):
            return cleaned_text

    async def _enrich_brief_async(self, brief: Dict) -> Dict:
        """The main enrichment logic, calling out to the LLM for creative expansion."""
        concept_prompt_args = {
            "theme_hint": brief.get("theme_hint", "general fashion"),
            "garment_type": brief.get("garment_type", "clothing"),
            "key_attributes": ", ".join(brief.get("key_attributes", [])),
        }
        antagonist_prompt_args = {
            "theme_hint": brief.get("theme_hint", "general fashion")
        }

        expansion_task = self._get_enrichment_data_async(
            prompt_library.THEME_EXPANSION_PROMPT.format(**concept_prompt_args),
            prompt_library.CONCEPTS_CORRECTION_PROMPT,
            concept_prompt_args,
            "concepts",
        )
        antagonist_task = self._get_enrichment_data_async(
            prompt_library.CREATIVE_ANTAGONIST_PROMPT.format(**antagonist_prompt_args),
            prompt_library.ANTAGONIST_CORRECTION_PROMPT,
            antagonist_prompt_args,
            "antagonist",
        )

        concepts_output, antagonist_output = await asyncio.gather(
            expansion_task, antagonist_task
        )

        parsed_concepts = self._parse_llm_creative_output(concepts_output, "concepts")
        if isinstance(parsed_concepts, list):
            brief["expanded_concepts"] = parsed_concepts
        elif isinstance(parsed_concepts, str):
            brief["expanded_concepts"] = [
                c.strip() for c in parsed_concepts.split(",") if c.strip()
            ]
        else:
            brief["expanded_concepts"] = []

        parsed_antagonist = self._parse_llm_creative_output(
            antagonist_output, "antagonist"
        )
        brief["creative_antagonist"] = (
            parsed_antagonist if isinstance(parsed_antagonist, str) else None
        )

        search_keywords = set()
        if brief.get("theme_hint"):
            search_keywords.add(brief["theme_hint"])
        if brief.get("expanded_concepts"):
            extraction_prompt = prompt_library.KEYWORD_EXTRACTION_PROMPT.format(
                concepts_list=json.dumps(brief["expanded_concepts"])
            )
            keyword_response = await gemini_client.generate_content_async(
                prompt_parts=[extraction_prompt]
            )
            if keyword_response and keyword_response.get("text"):
                keyword_data = self._parse_llm_creative_output(
                    keyword_response["text"], "keywords"
                )
                if isinstance(keyword_data, list):
                    search_keywords.update(keyword_data)

        brief["search_keywords"] = list(search_keywords)
        return brief
