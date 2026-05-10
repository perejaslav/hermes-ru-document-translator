# Kanban collect_results — STUB (NOT IMPLEMENTED IN v0.1)
# Full implementation deferred to v0.2+

from pathlib import Path


def collect_results(workspace: Path) -> dict:
    """Collect results from all Kanban workers."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def collect_translated_chunk(chunk_id: str, workspace: Path) -> str | None:
    """Collect a single translated chunk."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def collect_glossary(workspace: Path) -> str | None:
    """Collect generated glossary."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def check_task_status(task_id: str, workspace: Path) -> dict:
    """Check status of a specific task."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def wait_for_completion(workspace: Path, timeout: int = 600) -> dict:
    """Wait for all tasks to complete."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")