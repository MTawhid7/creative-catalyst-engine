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

    def __init__(self, user_passage: str, results_dir: Path):
        # The run_id is a unique identifier for logging and the initial temp folder.
        self.run_id: str = str(uuid.uuid4()).split("-")[0]
        self.user_passage: str = user_passage

        # This will be populated with the human-readable theme slug later.
        self.theme_slug: str = ""

        # The initial folder is temporary and will be renamed at the end of the run.
        self.results_dir: Path = results_dir / self.run_id

        self.artifacts: Dict[str, Any] = {"inputs": {"user_passage": user_passage}}

        # --- Pipeline Data Fields ---
        self.enriched_brief: Dict = {}
        # --- START OF FIX ---
        # Add a new field to hold the deeper understanding of the user's philosophy.
        self.brand_ethos: str = ""
        # --- END OF FIX ---
        self.discovered_urls: List[str] = []
        self.raw_research_context: str = ""
        self.structured_research_context: str = ""
        self.final_report: Dict = {}

    def record_artifact(self, step_name: str, data: Any):
        """Records the output of a processor for debugging purposes."""
        self.artifacts[step_name] = data

    def save_artifacts(self):
        """
        Saves all recorded artifacts to a JSON file.
        This method is designed to not fail silently and will raise exceptions
        on file errors, to be caught by the calling orchestrator.
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.results_dir / "debug_run_artifacts.json"

        with open(artifact_path, "w", encoding="utf-8") as f:
            # The default=str is a safeguard for objects that are not JSON serializable
            json.dump(self.artifacts, f, indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the primary data fields of the context to a dictionary for logging."""
        return {
            "run_id": self.run_id,
            "user_passage": self.user_passage,
            "enriched_brief": self.enriched_brief,
            "brand_ethos": self.brand_ethos,  # Add to logging
            "discovered_urls_count": len(self.discovered_urls),
            "raw_research_context_length": len(self.raw_research_context),
            "structured_research_context_length": len(self.structured_research_context),
            "final_report_keys": (
                list(self.final_report.keys()) if self.final_report else []
            ),
        }
