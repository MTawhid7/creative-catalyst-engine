# catalyst/pipeline/synthesis_strategies/report_assembler.py

import json
from typing import Dict, Optional, Any

from pydantic import ValidationError

from ...context import RunContext
from ...models.trend_report import FashionTrendReport, PromptMetadata
from ...utilities.logger import get_logger
from ...clients import gemini
from ...prompts import prompt_library
from ...resilience import invoke_with_resilience, MaxRetriesExceededError

logger = get_logger(__name__)


class ReportAssembler:
    """
    A utility class that handles the finalization and validation of the report,
    as well as the direct-knowledge fallback synthesis path.
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.brief = context.enriched_brief

    async def _assemble_from_fallback_async(self) -> Optional[Dict[str, Any]]:
        """
        Handles the fallback path: generating a complete report model using the
        AI's direct knowledge when the primary research/synthesis path fails.
        """
        logger.warning("⚙️ Activating direct knowledge fallback synthesis path.")
        prompt = prompt_library.FALLBACK_SYNTHESIS_PROMPT.format(
            enriched_brief=json.dumps(self.brief), brand_ethos=self.context.brand_ethos
        )
        try:
            # Note: The fallback could also be upgraded to use the "pro" model for quality.
            report_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=FashionTrendReport,
            )
            report_data = report_model.model_dump(mode="json")
            return self._finalize_and_validate_report(
                report_data, needs_validation=False
            )
        except MaxRetriesExceededError:
            logger.critical(
                "❌ CRITICAL: The direct knowledge fallback synthesis also failed."
            )
            return None

    def _finalize_and_validate_report(
        self, report_data: Dict[str, Any], needs_validation: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Adds final metadata and performs Pydantic validation. This is the single,
        unified exit point for all report creation paths.
        """
        report_data["prompt_metadata"] = PromptMetadata(
            run_id=self.context.run_id, user_passage=self.context.user_passage
        ).model_dump(mode="json")
        report_data["antagonist_synthesis"] = self.context.antagonist_synthesis

        brief_keys_to_copy = [
            "season",
            "year",
            "region",
            "target_gender",
            "target_age_group",
            "target_model_ethnicity",
            "antagonist_synthesis",
        ]
        for key in brief_keys_to_copy:
            if key not in report_data or not report_data[key]:
                report_data[key] = self.brief.get(key)

        # --- START: THE DEFINITIVE FIX ---
        # Explicitly normalize the fields that might be single values before validation.
        # This is more robust and clearer than a Pydantic validator for this specific task.
        for key in ["season", "year", "region"]:
            if key in report_data and not isinstance(report_data[key], list):
                report_data[key] = [report_data[key]]
        # --- END: THE DEFINITIVE FIX ---

        if needs_validation:
            logger.info("Validating the final assembled report from builders...")
            try:
                validated_report = FashionTrendReport.model_validate(report_data)
                logger.info("✅ Success: Final report assembled and validated.")
                return validated_report.model_dump(mode="json")
            except ValidationError as e:
                logger.critical(f"❌ The final assembled report failed validation: {e}")
                return None
        else:
            logger.info(
                "✅ Success: Final report assembled (pre-validated from fallback)."
            )
            return report_data
