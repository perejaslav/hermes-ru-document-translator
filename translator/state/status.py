"""Pipeline status tracking."""
import json
from pathlib import Path
from datetime import datetime
from enum import Enum


class StageStatus(str, Enum):
    """Stage completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    STUB = "stub"  # Not implemented yet
    PENDING_AGENT = "pending_agent"  # Requires Hermes agent action


class OverallStatus(str, Enum):
    """Overall pipeline status."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED_TRANSLATION = "FAILED_TRANSLATION"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    PREPARED = "PREPARED"  # Workspace prepared, ready for LLM translation


STAGE_ORDER = [
    "ingest",
    "classify",
    "extract",
    "normalize",
    "protect_spans",
    "block_ids",
    "segment",
    "glossary",
    "translation",
    "qa",
    "merge",
    "export",
    "report"
]


class PipelineStatus:
    """Tracks pipeline stage status and overall progress."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.data = {
            "stages": {stage: {"status": "pending", "started_at": None, "completed_at": None}
                      for stage in STAGE_ORDER},
            "overall_status": "IN_PROGRESS",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "errors": [],
            "warnings": []
        }

    def set_stage(self, stage: str, status: str, error: str = None):
        """Set status for a specific stage."""
        if stage not in self.data["stages"]:
            # Allow unknown stages (for extensibility)
            self.data["stages"][stage] = {"status": "pending", "started_at": None, "completed_at": None}

        stage_data = self.data["stages"][stage]
        old_status = stage_data["status"]

        if status == "in_progress" and old_status == "pending":
            stage_data["started_at"] = datetime.now().isoformat()

        stage_data["status"] = status

        if status in ("completed", "failed", "skipped", "stub"):
            stage_data["completed_at"] = datetime.now().isoformat()

        if error:
            self.data["errors"].append({"stage": stage, "error": error})

    def set_complete(self):
        """Mark pipeline as complete with final status."""
        self.data["completed_at"] = datetime.now().isoformat()

        # Determine overall status based on stages
        stages = self.data["stages"]

        if stages.get("extract", {}).get("status") == "failed":
            self.data["overall_status"] = "EXTRACTION_FAILED"
        elif stages.get("translation", {}).get("status") == "failed":
            self.data["overall_status"] = "FAILED_TRANSLATION"
        elif stages.get("export", {}).get("status") == "failed":
            # Export failure is non-critical if md exists
            if (self.workspace / "output" / "translated.md").exists():
                self.data["overall_status"] = "PARTIAL_SUCCESS"
            else:
                self.data["overall_status"] = "FAILED_TRANSLATION"
        elif all(stages.get(s, {}).get("status") in ("completed", "skipped", "stub")
                 for s in STAGE_ORDER):
            # All done
            self.data["overall_status"] = "SUCCESS"
        else:
            self.data["overall_status"] = "PARTIAL_SUCCESS"

    def add_warning(self, warning: str):
        """Add a non-critical warning."""
        self.data["warnings"].append({
            "warning": warning,
            "at": datetime.now().isoformat()
        })

    def save(self):
        path = self.workspace / "state" / "status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, workspace: Path) -> "PipelineStatus":
        path = workspace / "state" / "status.json"
        if not path.exists():
            return cls(workspace)

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        instance = cls(workspace)
        instance.data = data
        return instance

    def summary(self) -> str:
        """Get human-readable status summary."""
        lines = [f"Overall: {self.data['overall_status']}"]
        for stage, data in self.data["stages"].items():
            status = data["status"]
            if status != "pending":
                lines.append(f"  {stage}: {status}")
        return "\n".join(lines)