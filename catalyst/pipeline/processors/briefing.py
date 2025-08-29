"""
This module contains the processors for the briefing stage.
The deconstruction processor is an "intelligent" step that infers
contextually relevant defaults for any missing creative information.
"""

import json
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any
import re

from catalyst.pipeline.base_processor import BaseProcessor
from catalyst.context import RunContext
from ...clients import gemini_client
from ...prompts import prompt_library


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
        # Remove special characters, allowing only letters, numbers, spaces, and hyphens
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        # Replace spaces and consecutive hyphens with a single hyphen
        text = re.sub(r"[\s-]+", "-", text).strip("-")
        # Truncate to a reasonable length
        slug = text[:15]
        return slug.strip("-")

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

        # Generate and store the theme slug in the context object
        theme_hint = initial_brief.get("theme_hint")
        context.theme_slug = self._create_slug(theme_hint)
        self.logger.info(f"✅ Generated theme slug: '{context.theme_slug}'")

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


class EthosClarificationProcessor(BaseProcessor):
    """
    Pipeline Step 2: Analyzes the user's passage for an underlying
    design philosophy or brand ethos.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info("🔬 Analyzing user passage for deeper brand ethos...")

        prompt = prompt_library.ETHOS_ANALYSIS_PROMPT.format(
            user_passage=context.user_passage
        )

        # --- START OF FIX ---
        # The client will now receive a JSON string, which needs to be parsed.
        response_text = await gemini_client.generate_content_async(
            prompt_parts=[prompt]
        )

        if response_text and response_text.get("text"):
            try:
                # Clean up potential markdown and parse the JSON
                json_text = response_text["text"].strip()
                if json_text.startswith("```json"):
                    json_text = json_text[7:-3].strip()

                data = json.loads(json_text)
                ethos = data.get("ethos")  # Safely get the 'ethos' value

                if ethos:
                    context.brand_ethos = ethos
                    self.logger.info("✅ Success: Distilled brand ethos.")
                    self.logger.debug(f"Found Ethos: {ethos}")
                else:
                    self.logger.info(
                        "💨 No specific ethos found. Proceeding with standard brief."
                    )
            except (json.JSONDecodeError, KeyError):
                self.logger.warning(
                    "⚠️ Ethos analysis returned malformed JSON. Skipping."
                )
        else:
            self.logger.warning("⚠️ Ethos analysis returned no content. Skipping.")
        # --- END OF FIX ---

        return context


class BriefEnrichmentProcessor(BaseProcessor):
    """
    Pipeline Step 3: Expands the initial brief with AI-driven creative
    concepts, a strategic antagonist, and searchable keywords for research.
    """

    async def process(self, context: RunContext) -> RunContext:
        self.logger.info(
            "⚙️ Enriching brief with AI-driven creative concepts and keywords..."
        )
        # Pass the newly found brand_ethos to the enrichment process
        enriched_brief = await self._enrich_brief_async(
            context.enriched_brief, context.brand_ethos
        )
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
    ) -> Dict | None:
        """
        A resilient helper function that attempts to get enrichment data, with a
        self-correction retry. Now returns a parsed JSON dictionary.
        """
        self.logger.debug(f"⏳ Attempting to generate {task_name} (Attempt 1)...")

        # --- START OF CHANGE: EXPECT JSON RESPONSE ---
        # The AI is now expected to return a dictionary (as a JSON string).
        initial_response = await gemini_client.generate_content_async(
            prompt_parts=[initial_prompt]
        )

        if initial_response and isinstance(initial_response, dict):
            self.logger.debug(
                f"✅ Successfully generated and parsed {task_name} on the first attempt."
            )
            return initial_response

        self.logger.warning(
            f"⚠️ First attempt to generate {task_name} failed or returned invalid format. Triggering self-correction."
        )

        failed_output = str(
            initial_response
        )  # Convert potential error to string for the prompt
        correction_prompt = correction_prompt_template.format(
            failed_output=failed_output, **prompt_args
        )

        self.logger.debug(
            f"⏳ Attempting to generate {task_name} (Attempt 2 - Correction)..."
        )
        correction_response = await gemini_client.generate_content_async(
            prompt_parts=[correction_prompt]
        )

        if correction_response and isinstance(correction_response, dict):
            self.logger.info(
                f"✅ Successfully generated and parsed {task_name} on the second (correction) attempt."
            )
            return correction_response

        self.logger.critical(
            f"❌ Self-correction also failed for {task_name}. The model could not produce a valid JSON output."
        )
        return None
        # --- END OF CHANGE ---

    # --- START OF CHANGE: REWRITTEN PARSING LOGIC AND MAIN METHOD ---
    async def _enrich_brief_async(self, brief: Dict, brand_ethos: str) -> Dict:
        """The main enrichment logic, now updated to handle structured JSON responses."""

        concept_prompt_args = {
            "theme_hint": brief.get("theme_hint", "general fashion"),
            "garment_type": brief.get("garment_type", "clothing"),
            "key_attributes": ", ".join(brief.get("key_attributes", [])),
            "brand_ethos": brand_ethos or "No specific ethos provided.",
        }

        antagonist_prompt_args = {
            "theme_hint": brief.get("theme_hint", "general fashion")
        }

        # The helper function now returns a dictionary, so we expect that.
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

        concepts_result, antagonist_result = await asyncio.gather(
            expansion_task, antagonist_task
        )

        # Safely extract the data from the dictionaries.
        brief["expanded_concepts"] = (
            concepts_result.get("concepts", []) if concepts_result else []
        )
        brief["creative_antagonist"] = (
            antagonist_result.get("antagonist") if antagonist_result else None
        )

        # The keyword extraction part remains the same as it already expected a JSON response.
        search_keywords = set()
        if brief.get("theme_hint"):
            search_keywords.add(brief["theme_hint"])

        if brief.get("expanded_concepts"):
            # This prompt already expected a JSON list, so no changes needed here.
            extraction_prompt = prompt_library.KEYWORD_EXTRACTION_PROMPT.format(
                concepts_list=json.dumps(brief["expanded_concepts"])
            )
            keyword_response = await gemini_client.generate_content_async(
                prompt_parts=[extraction_prompt]
            )
            if keyword_response and keyword_response.get("keywords"):
                search_keywords.update(keyword_response["keywords"])

        brief["search_keywords"] = sorted(list(search_keywords))
        return brief

    # --- END OF CHANGE ---
