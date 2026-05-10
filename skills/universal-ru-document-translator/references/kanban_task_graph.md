# Kanban Task Graph

## NOT IMPLEMENTED IN v0.1

This document describes the planned Kanban mode for large documents and batch processing. Implementation deferred.

## Planned Architecture

```
[Document Ingestion] → [Classification] → [Task Creation]
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              [Glossary]              [Translation Tasks]           [QA Tasks]
              (1 task)                (N tasks, 1 per chunk)        (M tasks)
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                    [Merge] → [Export] → [Report]
```

## Task Types (Planned)

### 1. Glossary Task
- Input: all source chunks
- Output: `glossary.md`, `style_guide.md`
- Assigned to: single worker

### 2. Translation Task (per chunk)
- Input: `chunks/source/<chunk_id>.md` + glossary + style guide
- Output: `chunks/translated/<chunk_id>.md`
- Assigned to: parallel workers (max concurrency: 3)

### 3. QA Task
- Input: translated chunk + source chunk
- Output: `chunks/reviewed/<chunk_id>.md` + QA report entry
- Assigned to: single worker (sequential)

### 4. Merge Task
- Input: all translated chunks (in order)
- Output: `output/translated.md`
- Assigned to: orchestrator

### 5. Export Task
- Input: `output/translated.md`
- Output: `output/translated.{docx,html,txt,pdf}`
- Assigned to: parallel workers (format-specific)

### 6. Report Task
- Input: all stage outputs
- Output: `output/translation_report.md`
- Assigned to: orchestrator

## Contract (Planned)

Workers write to:
- `chunks/translated/<chunk_id>.md` — translated content
- `state/worker_status.json` — current status

Orchestrator owns:
- `state/status.json`
- `state/chunk_index.json`
- `state/block_index.json`
- `output/` directory
- `state/qa_findings.json`

## Concurrency Limits (Planned)

- Max parallel translation workers: 3
- Max parallel export workers: 2
- QA runs sequentially (no parallelization)

## Error Handling (Planned)

- If chunk translation fails → mark in index, continue others
- Retry up to 2 times per chunk
- After retries exhausted → flag for manual review
- Do not block other chunks