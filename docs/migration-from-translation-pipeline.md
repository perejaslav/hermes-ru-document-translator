# Migration from hermes-translation-pipeline

## Status

`hermes-translation-pipeline` is now a **methodology donor**, not a primary implementation.
`hermes-ru-document-translator` is the **canonical repository** for the unified pipeline.

---

## What was merged

The following concepts and patterns were brought from `hermes-translation-pipeline` into `hermes-ru-document-translator`:

### Foundation Stage
Source text analysis before translation: glossary creation, style guide, entity register.
Located at `~/translations/<project_slug>/foundation/`.

### 2-Wave Translation
- **Wave 1:** parallel chunk translation with previous-chunk context
- **Wave 2:** refinement using wave1 output + glossary + style

Implemented via `translator/orchestration/parallel_translator.py` with semaphore-based concurrency.

### 5 QA Gates
| Gate | Function |
|---|---|
| Terminology | glossary adherence |
| Integrity | content completeness |
| Style | style.md compliance |
| Fluency | natural Russian |
| Formatting | markdown structure |

Results → `qa/remediation.json` + `qa/summary.md`.

### Repair / Remediation
Chunk-level re-translation targeting specific QA failures, not full pipeline restart.

### Backend Fallback Strategy
Abstract backend layer with mock/hermes_delegate/minimax_api/sequential implementations.

---

## What was NOT transferred directly

### Parallel state system
B had its own state tracking separate from A's PipelineStatus. The unified pipeline uses A's state management as canonical.

### Alternate workspace layout
B used a different directory convention. Unified pipeline uses `~/translations/<slug>/` as the single canonical location.

### Ephemeral-only skill workflow
B's approach was skill-centric without persistent state files. The unified pipeline is state-first: every stage is resumable and crash-recoverable.

### Kanban mode
B had Kanban-oriented task structure. Not implemented in v0.2 — stub exists at `translator/kanban/`.

---

## What was preserved from A

- Python package structure (`translator/` modules)
- `scripts/run_pipeline.py` CLI
- `tests/` with 46+ passing tests
- CI/CD via GitHub Actions
- `pyproject.toml`-based install
- Multi-format export (md/txt/docx/html/pdf)
- State management via `status.json` / `stage_status.json`

---

## What B provided that A lacked

- Explicit 2-wave translation model with semantic purpose
- 5-gate quality framework with remediation
- Backend abstraction (multiple backend implementations)
- Foundation-stage concept (glossary/style/entities as separate artifacts)
- Worker-skill pattern for parallel subagent execution

---

## Future

`hermes-translation-pipeline` README will be updated to link to `hermes-ru-document-translator` as canonical. No further development on the donor repo is planned for the unified pipeline scope.