# catalyst/context.py

"""
This module defines the RunContext, a central data object to hold the state
and artifacts of a single execution pipeline.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List


class RunContext:
    """
    A data object that is created at the start of a run and passed through
    each step of the pipeline, accumulating data and artifacts. It does not
    contain any operational logic or logging.
    """

    # --- CHANGE: Add 'variation_seed' to the constructor ---
    def __init__(self, user_passage: str, results_dir: Path, variation_seed: int = 0):
        # The run_id is a unique identifier for logging and the initial temp folder.
        self.run_id: str = str(uuid.uuid4()).split("-")[0]
        self.user_passage: str = user_passage

        # --- ADD: Store the variation_seed ---
        self.variation_seed: int = variation_seed

        # This will be populated with the human-readable theme slug later.
        self.theme_slug: str = ""

        # The initial folder is temporary and will be renamed at the end of the run.
        self.results_dir: Path = results_dir / self.run_id

        # --- CHANGE: Include the seed in the initial artifacts ---
        self.artifacts: Dict[str, Any] = {
            "inputs": {"user_passage": user_passage, "variation_seed": variation_seed}
        }

        # --- Pipeline Data Fields ---
        self.enriched_brief: Dict = {}
        self.brand_ethos: str = ""
        self.antagonist_synthesis: str = ""
        self.structured_research_context: Dict[str, Any] = {}
        self.final_report: Dict = {}

        # --- Granular Status Tracking Fields ---
        self.current_status: str = "Initializing..."
        self.is_complete: bool = False

    def record_artifact(self, step_name: str, data: Any):
        """Records the output of a processor for debugging purposes."""
        self.artifacts[step_name] = data

    def save_artifacts(self):
        """
        Saves all recorded artifacts to a JSON file.
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.results_dir / "debug_run_artifacts.json"

        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(self.artifacts, f, indent=2, default=str)

    def save_dossier_artifact(self):
        """
        Saves the structured research dossier to its own dedicated JSON file.
        """
        if not self.structured_research_context or not isinstance(
            self.structured_research_context, dict
        ):
            return

        self.results_dir.mkdir(parents=True, exist_ok=True)
        dossier_path = self.results_dir / "research_dossier.json"
        try:
            with open(dossier_path, "w", encoding="utf-8") as f:
                json.dump(self.structured_research_context, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save research dossier artifact: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Converts the primary data fields of the context to a dictionary for logging."""
        return {
            "run_id": self.run_id,
            "user_passage": self.user_passage,
            # --- ADD: Include the seed in the log dictionary ---
            "variation_seed": self.variation_seed,
            "enriched_brief": self.enriched_brief,
            "brand_ethos": self.brand_ethos,
            "antagonist_synthesis": self.antagonist_synthesis,
            "structured_research_context_length": len(self.structured_research_context),
            "final_report_keys": (
                list(self.final_report.keys()) if self.final_report else []
            ),
            "current_status": self.current_status,
        }
