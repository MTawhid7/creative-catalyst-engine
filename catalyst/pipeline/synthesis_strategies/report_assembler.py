# catalyst/pipeline/synthesis_strategies/report_assembler.py

"""
This module defines the ReportAssembler, a strategy class that orchestrates
the multi-step, schema-driven process of constructing the final fashion trend report
by delegating tasks to specialized builder classes.
"""

from typing import Dict, Optional, Any

from pydantic import ValidationError

from ...context import RunContext
from ...models.trend_report import FashionTrendReport, PromptMetadata
from ...utilities.logger import get_logger
from .section_builders import (
    TopLevelFieldsBuilder,
    NarrativeSettingBuilder,
    StrategiesBuilder,
    AccessoriesBuilder,
    KeyPiecesBuilder,
)

logger = get_logger(__name__)


class ReportAssembler:
    """
    Orchestrates the step-by-step assembly of the final report by managing
    a sequence of specialized builder strategies.
    """

    def __init__(self, context: RunContext):
        self.context = context
        self.brief = context.enriched_brief
        self.final_report_data: Dict[str, Any] = {}

    async def assemble_report(self) -> Optional[Dict[str, Any]]:
        """
        Executes the full, multi-step report assembly process by invoking
        each builder in sequence and validating the final result.
        """
        is_fallback = not self.context.structured_research_context
        structured_research_context = self.context.structured_research_context or ""
        raw_research_context = self.context.raw_research_context or ""

        # --- Instantiate builders with no immediate data dependencies ---
        top_level_builder = TopLevelFieldsBuilder(self.context)
        strategies_builder = StrategiesBuilder(self.context)
        key_pieces_builder = KeyPiecesBuilder(self.context)

        # --- Execute builder sequence, respecting all data dependencies ---

        # Step 1: Generate the high-level themes, which are dependencies for other steps.
        top_level_data = await top_level_builder.build(
            structured_research_context, is_fallback
        )
        self.final_report_data.update(top_level_data)

        # Step 2: Now that theme and drivers exist, instantiate and call the NarrativeSettingBuilder.
        narrative_builder = NarrativeSettingBuilder(
            self.context,
            theme=self.final_report_data.get("overarching_theme", ""),
            drivers=self.final_report_data.get("cultural_drivers", []),
        )
        narrative_data = await narrative_builder.build(
            structured_research_context, is_fallback
        )
        self.final_report_data.update(narrative_data)

        # Step 3: Extract the strategic text from the research.
        strategies_data = await strategies_builder.build(
            structured_research_context, is_fallback
        )
        self.final_report_data.update(strategies_data)

        # Step 4: Now that ALL high-level context is synthesized, instantiate and call the AccessoriesBuilder.
        accessories_builder = AccessoriesBuilder(
            self.context,
            theme=self.final_report_data.get("overarching_theme", ""),
            mood=self.brief.get("desired_mood", []),
            drivers=self.final_report_data.get("cultural_drivers", []),
            models=self.final_report_data.get("influential_models", []),
            strategy=self.final_report_data.get(
                "accessory_strategy", "Accessories should complete the look."
            ),
        )
        accessories_data = await accessories_builder.build(
            raw_research_context, is_fallback
        )
        self.final_report_data.update(accessories_data)

        # Step 5: Generate the detailed product descriptions.
        key_pieces_data = await key_pieces_builder.build(
            structured_research_context, is_fallback
        )
        self.final_report_data.update(key_pieces_data)

        logger.info("✨ Assembling and validating final report...")
        return self._finalize_and_validate_report()

    def _finalize_and_validate_report(self) -> Optional[Dict[str, Any]]:
        """Adds final metadata and performs Pydantic validation."""

        self.final_report_data["prompt_metadata"] = PromptMetadata(
            run_id=self.context.run_id, user_passage=self.context.user_passage
        ).model_dump(mode="json")
        self.final_report_data["antagonist_synthesis"] = (
            self.context.antagonist_synthesis
        )

        # --- START OF DEFINITIVE FIX ---
        # Add the "Creative Compass" to the final report data before validation.
        self.final_report_data["desired_mood"] = self.brief.get("desired_mood", [])
        # --- END OF DEFINITIVE FIX ---

        demographic_keys = [
            "season",
            "year",
            "region",
            "target_gender",
            "target_age_group",
            "target_model_ethnicity",
        ]
        for key in demographic_keys:
            self.final_report_data[key] = self.brief.get(key)

        try:
            validated_report = FashionTrendReport.model_validate(self.final_report_data)
            logger.info("✅ Success: Final report assembled and validated.")
            return validated_report.model_dump(mode="json")
        except ValidationError as e:
            logger.critical(
                f"❌ The final assembled report failed validation: {e}",
                extra={"report_data": self.final_report_data},
            )
            return None
