---
name: universal-ru-document-translator
description: Unified document translation pipeline — 2-wave translation, Foundation stage, 5 QA gates, resumable state. Translates documents to Russian via Hermes Agent or mock backend.
version: 0.2.0
category: document-processing
trigger: "перевод translate document translation русский ru document pipeline"
---

# Universal RU Document Translator — SKILL.md v0.2

## 1. When to use

Use this skill when the user asks to translate a document, article, book, or text to Russian.

**Supported formats:**
- `.txt`, `.md`, `.markdown`, `.docx`, `.html`, `.htm`, text-based `.pdf`

**NOT in v0.2:** OCR/scanned PDF, EPUB batch processing, watch-folders, URL input

---

## 2. Canonical Workspace

Every project gets its own directory:

```
~/translations/<project_slug>/
```

`project_slug` = `<sanitized_stem>_<YYYYMMDD>_<6_char_hash>`

**Directory structure:**
```
<project_slug>/
├── input/                  # copy of source file
├── chunks/
│   ├── source/             # extracted text chunks
│   ├── context/            # previous/next context per chunk
│   └── translated/
│       ├── wave1/          # first translation pass
│       └── wave2/          # refinement pass
├── foundation/             # glossary.md, style.md, entities.md
├── qa/                     # gate reports + remediation.json
├── output/                 # final translated.md + exports
└── state/
    ├── status.json         # overall + per-stage status
    └── stage_status.json   # copy of status.json
```

---

## 3. Pipeline Commands

Run in order:

```bash
# 1. Check dependencies first
python scripts/run_pipeline.py doctor

# 2. Create project from source file
python scripts/run_pipeline.py prepare /path/to/doc.md

# 3. Translate all chunks (wave1 → wave2)
python scripts/run_pipeline.py translate <project_slug> --backend mock

# 4. Run 5-gate QA
python scripts/run_pipeline.py qa <project_slug>

# 5. Repair flagged chunks (if QA had warnings)
python scripts/run_pipeline.py repair <project_slug> --backend mock

# 6. Merge wave2 chunks into final document
python scripts/run_pipeline.py merge <project_slug>

# 7. Export to all formats
python scripts/run_pipeline.py export <project_slug>

# 8. Generate final report
python scripts/run_pipeline.py report <project_slug>
```

**Utility commands:**
```bash
# List all projects
python scripts/run_pipeline.py list

# Detailed project status
python scripts/run_pipeline.py status <project_slug>
```

---

## 4. Backends

| Backend | Description |
|---|---|
| `mock` | Offline testing — deterministic pseudo-translation, always works |
| `hermes_delegate` | Hermes runtime-only / experimental — not available via `python scripts/run_pipeline.py` |
| `minimax_api` | Direct MiniMax API backend (experimental/stub, depends on build) |
| `sequential` | Single-threaded fallback — safe for testing |

**For full cycle testing:** always start with `--backend mock`

**For production CLI use:** do not use `mock`. Specify a working backend explicitly, e.g. `--backend minimax_api`, when it is configured and passes healthcheck.

`hermes_delegate` is Hermes runtime-only and will fail with `ImportError` when run via `python scripts/run_pipeline.py`.

---

## 5. Stage Flow

```
ingestion → foundation → chunking → translation_wave1 → translation_wave2 → qa_gates → assembly → export → report
```

Each stage writes its output and updates `state/status.json` immediately. The pipeline is **resumable** — if it crashes mid-wave, restart picks up from the last completed chunk.

---

## 6. Foundation Stage

Before chunking, the pipeline analyzes the source and creates:

- **glossary.md** — key terminology (capitalized terms, technical phrases)
- **style.md** — sentence length patterns, tone, calque warnings
- **entities.md** — multi-word named entities detected via heuristics

Foundation is a **non-blocking enhancement layer**. If AI backend is unavailable, heuristic fallbacks are used and chunking continues.

---

## 7. 2-Wave Translation

**Wave 1 (parallel):** Translate all source chunks with context from previous chunk.
**Wave 2 (parallel):** Refine each chunk, reading wave1 output + glossary + style guide.

Wave2 operates only on chunks where wave1 is `completed`. This ensures clean ordering.

Semaphore-based parallelism: max 3 concurrent workers by default (`--max-workers 3`).

---

## 8. 5 QA Gates

After wave2, run QA gates:

| Gate | Checks | Failure behavior |
|---|---|---|
| Gate 1: Terminology | Key terms translated correctly | WARN |
| Gate 2: Integrity | No content dropped, structure preserved | FAIL → remediation |
| Gate 3: Style | Matches style.md guidelines | WARN |
| Gate 4: Fluency | Natural Russian, no calques | WARN |
| Gate 5: Formatting | Markdown structure, code blocks | WARN |

QA is **diagnostic, not blocking**. Results go to:
- `qa/remediation.json` — chunk-level issue mapping
- `qa/summary.md` — human-readable summary

If `qa/remediation.json` exists, run `repair` before merge.

---

## 9. Repair

`repair` re-runs wave2 only for chunks flagged in `remediation.json`. It does NOT restart the full pipeline.

```bash
python scripts/run_pipeline.py repair <project_slug> --backend mock
```

Then re-run QA to verify fixes.

**Safety:** `repair` refuses implicit mock backend. Without `--backend`, it reads the backend from manifest.json (chunk-level `wave2_backend` or project-level `translation.wave2_backend`). If the backend is unknown, the command exits with an error to prevent silent overwrite of real translations. Pass `--backend mock` explicitly for testing.

---

## 10. Overall Status Values

| Status | Meaning |
|---|---|
| `SUCCESS` | All stages completed, no warnings |
| `PARTIAL_SUCCESS` | Completed with QA warnings or missing optional outputs |
| `FAILED_TRANSLATION` | Translation stage failed |
| `EXTRACTION_FAILED` | Could not extract text from source |

`PARTIAL_SUCCESS` is normal when PDF export is unavailable or QA has fluency warnings.

---

## 11. PDF Export

PDF is **optional**. If pandoc/xelatex/noto fonts are missing:
- PDF step reports a warning
- All other formats (md, txt, docx, html) still succeed
- overall_status = `PARTIAL_SUCCESS`, not failure

---

## 12. Output Files

After full pipeline:
```
output/translated.md          ← main output
output/translated.debug.md    ← with block IDs for debugging
output/translated.txt
output/translated.docx
output/translated.html
output/translated.pdf        ← optional
output/translation_report.md  ← final report
output/glossary.md            ← terminology reference
qa/remediation.json           ← chunks needing repair
qa/summary.md                 ← QA summary per gate
state/status.json             ← full pipeline status
chunks/manifest.json          ← chunk inventory with wave/qa status
```

---

## 13. Resumability

The pipeline persists state after every stage. If interrupted:

- Completed chunks are skipped on restart
- wave1 can resume from last completed chunk
- wave2 can resume from last completed wave1 chunk
- QA checks are re-run only on updated chunks
- `state/status.json` always reflects current state

---

## 14. For the Agent

When the user asks "translate this document":

1. Run `doctor` first to confirm environment
2. Run `prepare <source_file>` to create workspace
3. Run `translate <slug> --backend mock` for full 2-wave mock translation
4. Run `qa <slug>` — read `qa/remediation.json`
5. If issues: `repair <slug> --backend mock` then `qa <slug>` again
6. `merge <slug>` → `export <slug>` → `report <slug>`
7. Report results to user with file paths

Do NOT start large translations without explicit user confirmation.

---

## 15. Legacy Note

Old projects using `workspace/<project_slug>/` format are **legacy**. New projects always use `~/translations/<project_slug>/`.

If user has old `workspace/` projects, do not migrate automatically — new format is canonical.

---

## 16. Pitfalls

### Manifest-based chunk tracking
Chunk status is stored in `chunks/manifest.json`, NOT in filenames. Always read manifest to determine which chunks need translation.

### Wave2 requires wave1 completion
Wave2 only processes chunks where `wave1_status == "completed"`. If wave1 is still in progress, wave2 waits.

### Context files are separate
Context (previous/next chunk text) is stored in `chunks/context/<chunk_id>.context.md`, NOT embedded in source chunk.

### Sanitizer layer
Hermes subagent output passes through a sanitizer that strips conversational wrappers ("Here's the translation:", "Вот перевод:", etc.). Do not trust raw subagent output directly.

### Mock backend is deterministic
Mock backend adds `[RU]` to headings and `<!-- refined -->` to wave2 output. This is intentional for test repeatability.

---

## 17. Quick Reference

```bash
# Full mock cycle (for testing)
python scripts/run_pipeline.py doctor
python scripts/run_pipeline.py prepare /path/to/doc.md
SLUG=$(python -c "from translator.state.manifest import create_project_slug; from pathlib import Path; print(create_project_slug(Path('/path/to/doc.md')))")
echo "Project slug: $SLUG"
python scripts/run_pipeline.py translate $SLUG --backend mock
python scripts/run_pipeline.py qa $SLUG
python scripts/run_pipeline.py repair $SLUG --backend mock  # if needed
python scripts/run_pipeline.py merge $SLUG
python scripts/run_pipeline.py export $SLUG
python scripts/run_pipeline.py report $SLUG
python scripts/run_pipeline.py status $SLUG
```

---

## 18. References

- `references/pipeline-stages.md` — detailed stage definitions
- `references/directory-structure.md` — canonical layout
- `references/state-schema.md` — status.json schema
- `references/qa-gates.md` — gate implementation details