# State Schema

## Overview

The pipeline uses three main state files:

- `state/status.json` — overall project status
- `state/stage_status.json` — per-stage tracking
- `chunks/manifest.json` — chunk inventory

These files live in the per-project workspace at `~/translations/<project_slug>/`.

---

## state/status.json

```json
{
  "project_slug": "example_project",
  "overall_status": "PREPARED",
  "current_stage": "chunking",
  "source_language": "en",
  "target_language": "ru",
  "warnings": [
    "source appears to be Russian; translation may not be needed"
  ],
  "created_at": "2026-05-10T12:00:00Z",
  "updated_at": "2026-05-10T12:30:00Z"
}
```

### Fields

| Field | Type | Description |
|---|---|---|
| project_slug | string | Unique project identifier |
| overall_status | enum | PREPARED / IN_PROGRESS / SUCCESS / PARTIAL_SUCCESS / FAILED |
| current_stage | string | Name of currently executing stage |
| source_language | string | ISO language code or "unknown" |
| target_language | string | ISO language code, default "ru" |
| warnings | array[string] | Non-critical issues encountered |
| created_at | ISO timestamp | Project creation time |
| updated_at | ISO timestamp | Last modification time |

---

## state/stage_status.json

```json
{
  "stages": {
    "ingestion": {
      "status": "completed",
      "started_at": "2026-05-10T12:00:00Z",
      "finished_at": "2026-05-10T12:01:00Z",
      "warnings": []
    },
    "foundation": {
      "status": "completed",
      "started_at": "2026-05-10T12:01:00Z",
      "finished_at": "2026-05-10T12:05:00Z",
      "warnings": ["heuristic mode: LLM unavailable"]
    },
    "chunking": {
      "status": "completed",
      "chunk_count": 12,
      "warnings": []
    },
    "translation_wave1": {
      "status": "completed",
      "translated": 12,
      "total": 12,
      "failed": 0,
      "backend": "mock"
    },
    "translation_wave2": {
      "status": "completed",
      "translated": 12,
      "total": 12,
      "failed": 0,
      "backend": "mock"
    },
    "qa_gates": {
      "status": "completed",
      "warnings": 2,
      "failed_gates": 0
    },
    "assembly": {
      "status": "completed",
      "warnings": ["guardrail markers stripped: 3"]
    },
    "export": {
      "status": "completed",
      "formats": ["md", "txt", "docx", "html"],
      "pdf_skipped": true,
      "pdf_reason": "xelatex not available"
    },
    "report": {
      "status": "completed"
    }
  }
}
```

### Stage Status Values

Each stage object supports:

| Field | Type | Description |
|---|---|---|
| status | enum | pending / in_progress / completed / warn / failed |
| started_at | ISO timestamp | When stage began |
| finished_at | ISO timestamp | When stage completed |
| warnings | array | Non-critical issues |
| *(stage-specific fields) | varies | e.g., chunk_count, translated, failed |

---

## chunks/manifest.json

```json
{
  "project_slug": "example_project",
  "source_hash": "a1b2c3d4...",
  "total_chunks": 2,
  "chunks": [
    {
      "id": "chunk_001",
      "word_count": 847,
      "char_start": 0,
      "char_end": 4500,
      "source_hash": "...",
      "has_previous_context": false,
      "has_next_context": true,
      "wave1_status": "completed",
      "wave2_status": "completed",
      "qa_status": "passed"
    },
    {
      "id": "chunk_002",
      "word_count": 623,
      "char_start": 4501,
      "char_end": 7800,
      "source_hash": "...",
      "has_previous_context": true,
      "has_next_context": false,
      "wave1_status": "completed",
      "wave2_status": "completed",
      "qa_status": "passed"
    }
  ]
}
```

### Per-Chunk Fields

| Field | Type | Description |
|---|---|---|
| id | string | Stable chunk ID (chunk_001, etc.) |
| word_count | int | Word count of source chunk |
| char_start | int | Character offset in source |
| char_end | int | Character end offset in source |
| source_hash | string | SHA256 of original source text |
| has_previous_context | bool | Whether previous chunk exists |
| has_next_context | bool | Whether next chunk exists |
| wave1_status | enum | pending / in_progress / completed / failed |
| wave2_status | enum | pending / in_progress / completed / failed |
| qa_status | enum | pending / passed / warn / failed |

---

## qa/remediation.json

Created when QA gates find issues:

```json
{
  "chunks": {
    "chunk_004": ["style", "fluency"],
    "chunk_009": ["terminology"]
  },
  "gates": {
    "terminology": {"status": "PASS", "terms_checked": 42},
    "integrity": {"status": "PASS"},
    "style": {"status": "WARN", "violations": 2},
    "fluency": {"status": "WARN", "issues": 3},
    "formatting": {"status": "PASS"}
  }
}
```

---

## State Update Rules

1. **Immediately persist** — Every stage writes state immediately, not at end.
2. **Never delete state** — Only update status values. Deleted chunks are marked, not erased.
3. **Crash recovery** — On restart, read state/stage_status.json to find incomplete stages.
4. **Resumability** — Incomplete chunks have status != completed and get processed.
5. **No race conditions** — Single-threaded state updates; no locking needed.

---

## Backwards Compatibility

Old `workspace/<project_slug>/status.json` is LEGACY FORMAT.

New projects use `~/translations/<project_slug>/state/status.json`.

Migration tooling is out of scope for v1.0.