# Kanban create_tasks — STUB (NOT IMPLEMENTED IN v0.1)
# Full implementation deferred to v0.2+

def create_tasks(workspace: Path, chunks: list) -> dict:
    """Create Kanban tasks for chunk translation."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def create_glossary_task(workspace: Path) -> dict:
    """Create glossary generation task."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def create_translation_task(chunk_id: str, workspace: Path) -> dict:
    """Create translation task for a single chunk."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def create_qa_task(chunk_id: str, workspace: Path) -> dict:
    """Create QA task for a translated chunk."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def create_merge_task(workspace: Path) -> dict:
    """Create merge task."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")


def create_export_tasks(workspace: Path, formats: list) -> list:
    """Create export tasks for each format."""
    raise NotImplementedError("Kanban mode not implemented in v0.1")