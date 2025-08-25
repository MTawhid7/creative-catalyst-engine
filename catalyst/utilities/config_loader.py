# catalyst/utilities/config_loader.py

import yaml
from pathlib import Path
from typing import Dict, Any

from .. import settings
from .logger import get_logger

logger = get_logger(__name__)


def load_sources_config() -> Dict[str, Any]:
    """Loads the sources.yaml file from the project root."""
    try:
        sources_path = settings.BASE_DIR / "catalyst" / "config" / "sources.yaml"
        if sources_path.exists():
            with open(sources_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            logger.warning(
                "⚠️ sources.yaml not found. Proceeding without curated sources."
            )
            return {}
    except yaml.YAMLError as e:
        logger.error(f"❌ Error parsing sources.yaml: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to load sources.yaml: {e}")
        return {}


def format_sources_for_prompt(config: Dict[str, Any]) -> str:
    """Formats the loaded sources config into a clean, readable string for an LLM prompt."""
    if not config:
        return "No specific sources provided."

    output_lines = []
    for vector, sources in config.items():
        output_lines.append(f"\n--- {vector.replace('_', ' ').title()} ---")
        for category, items in sources.items():
            if isinstance(items, list):
                formatted_items = ", ".join(items)
                output_lines.append(
                    f"- {category.replace('_', ' ').title()}: {formatted_items}"
                )
            elif isinstance(items, dict):
                output_lines.append(f"- {category.replace('_', ' ').title()}:")
                for sub_cat, sub_items in items.items():
                    formatted_sub_items = ", ".join(sub_items)
                    output_lines.append(f"  - {sub_cat}: {formatted_sub_items}")

    return "\n".join(output_lines)


# Load and format the sources once on startup
CURATED_SOURCES_CONFIG = load_sources_config()
FORMATTED_SOURCES = format_sources_for_prompt(CURATED_SOURCES_CONFIG)
