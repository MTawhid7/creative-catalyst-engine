"""
The Reporting Service: The Publisher for the Creative Catalyst Engine.
"""

import json
import os
from typing import Dict, Any

# --- START OF CHANGE ---
from pydantic import ValidationError
from ..utilities.logger import get_logger, get_run_id

# --- END OF CHANGE ---

from .. import settings
from ..models.trend_report import FashionTrendReport
from ..prompts import prompt_library

# Initialize a logger specific to this module
logger = get_logger(__name__)


def _save_json_file(data: Dict, filename: str) -> bool:
    """A resilient helper function to save a dictionary to a JSON file."""
    try:
        # Ensure the results directory exists
        settings.RESULTS_DIR.mkdir(exist_ok=True)
        file_path = os.path.join(settings.RESULTS_DIR, filename)

        logger.info(f"Saving data to '{file_path}'...")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved file: {filename}")
        return True
    except (IOError, TypeError) as e:
        logger.error(f"Failed to save JSON file '{filename}'", exc_info=True)
        return False


# --- START OF CHANGE ---
# The save_debug_json function now correctly uses the imported get_run_id
def save_debug_json(data: str, attempt: int, step: str):
    """Saves the raw, failed JSON from the model for debugging."""
    try:
        run_id = get_run_id()
        settings.RESULTS_DIR.mkdir(exist_ok=True)
        filename = f"debug_run_{run_id}_step_{step}_attempt_{attempt}.json"
        file_path = os.path.join(settings.RESULTS_DIR, filename)
        logger.info(f"Saving debug JSON to '{file_path}'...")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
    except Exception as e:
        logger.error(f"Failed to save debug JSON file '{filename}'", exc_info=True)


# --- END OF CHANGE ---


def _generate_image_prompts(report: FashionTrendReport) -> Dict[str, Any]:
    """
    Generates the final, art-directed image prompts from the validated trend report.
    """
    # ... (This function's internal logic remains the same) ...
    logger.info("Generating art-directed image prompts...")
    all_prompts = {}

    model_style = (
        report.influential_models[0] if report.influential_models else "a fashion model"
    )
    region = getattr(report, "region", "the specified region")
    model_ethnicity = getattr(report, "target_model_ethnicity", "diverse")

    for piece in report.detailed_key_pieces:
        # --- START OF CORRECTION ---
        # Correctly access elements from a simple list of strings, not a list of objects.
        main_fabric = piece.fabrics[0] if piece.fabrics else "a high-quality fabric"
        main_color = piece.colors[0] if piece.colors else "a core color"
        # --- END OF CORRECTION ---
        silhouette = (
            piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
        )

        # --- START OF CORRECTION ---
        # Correctly join strings from a simple list.
        color_names = ", ".join(piece.colors)
        fabric_names = ", ".join(piece.fabrics)
        # --- END OF CORRECTION ---
        details_trims = ", ".join(piece.details_trims)

        cultural_pattern = (
            piece.cultural_patterns[0]
            if piece.cultural_patterns
            else "a subtle geometric"
        )
        regional_context = f"traditional {cultural_pattern} patterns from {region}"

        key_accessories_list = []
        if report.accessories.get("Bags"):
            key_accessories_list.append(report.accessories["Bags"][0])
        if "Headscarves" in report.accessories.get("Other", []):
            key_accessories_list.append("a stylishly tied Headscarf")
        if report.accessories.get("Jewelry"):
            key_accessories_list.append(report.accessories["Jewelry"][0])
        key_accessories = ", ".join(key_accessories_list[:3])

        piece_prompts = {
            "inspiration_board": prompt_library.INSPIRATION_BOARD_PROMPT_TEMPLATE.format(
                theme=report.overarching_theme,
                key_piece_name=piece.key_piece_name,
                model_style=model_style,
                region=region,
                regional_context=regional_context,
                color_names=color_names,
                fabric_names=fabric_names,
            ),
            "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                key_piece_name=piece.key_piece_name,
                region=region,
                fabric_names=fabric_names,
                culturally_specific_fabric=cultural_pattern,
                color_names=color_names,
                details_trims=details_trims,
                key_accessories=key_accessories,
                regional_context=regional_context,
            ),
            "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                model_style=model_style,
                model_ethnicity=model_ethnicity,
                key_piece_name=piece.key_piece_name,
                main_color=main_color,
                main_fabric=main_fabric,
                cultural_pattern=cultural_pattern,
                silhouette=silhouette,
                region=region,
                details_trims=details_trims,
            ),
        }
        all_prompts[piece.key_piece_name] = piece_prompts

    logger.info("Image prompt generation complete.")
    return all_prompts


def _generate_executive_summary(report: FashionTrendReport):
    """
    Placeholder for generating a human-readable executive summary (e.g., Markdown or PDF).
    """
    logger.info("Executive summary generation is not yet implemented.")
    pass


def generate_outputs(final_report_data: Dict, enriched_brief: Dict):
    """
    The main public function that orchestrates the entire reporting process.
    """
    logger.info("Starting final report generation...")

    # 1. Save the main trend report JSON
    _save_json_file(final_report_data, settings.TREND_REPORT_FILENAME)

    # 2. Generate and save the image prompts JSON
    try:
        validated_report = FashionTrendReport.model_validate(final_report_data)
        prompts_data = _generate_image_prompts(validated_report)
        _save_json_file(prompts_data, settings.PROMPTS_FILENAME)
    except ValidationError as e:
        logger.error(
            "Could not generate image prompts due to a data validation error.",
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            "An unexpected error occurred during prompt generation.", exc_info=True
        )

    # 3. (Future) Generate the executive summary
    if "validated_report" in locals():
        _generate_executive_summary(validated_report)

    logger.info("All reporting outputs have been generated.")
