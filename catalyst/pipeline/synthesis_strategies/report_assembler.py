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
    A utility class that handles the direct-knowledge fallback synthesis path
    when the primary research/synthesis pipeline fails.
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.brief = context.enriched_brief

    async def assemble_from_fallback_async(self) -> Optional[Dict[str, Any]]:
        """
        Handles the fallback path: generating a complete report model using the
        AI's direct knowledge.
        """
        logger.warning("⚙️ Activating direct knowledge fallback synthesis path.")
        prompt = prompt_library.FALLBACK_SYNTHESIS_PROMPT.format(
            enriched_brief=json.dumps(self.brief), brand_ethos=self.context.brand_ethos
        )
        try:
            report_model = await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt=prompt,
                response_schema=FashionTrendReport,
            )
            # The validation and metadata injection will be handled by the new
            # FinalValidationProcessor, so we just return the raw model dump.
            return report_model.model_dump(mode="json")
        except MaxRetriesExceededError:
            logger.critical(
                "❌ CRITICAL: The direct knowledge fallback synthesis also failed."
            )
            return None
