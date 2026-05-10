# Pipeline Stages — Canonical Definition

## Stage Order

```
ingestion → foundation → chunking → translation_wave1 → translation_wave2 → qa_gates → assembly → export → report
```

## Stage Contract

Every stage MUST define:
- **Entry criteria**: what must exist before stage starts
- **Exit criteria**: what the stage produces
- **State files written**
- **Validation rules**
- **WARN conditions**
- **FAIL conditions**
- **Resumability**: can stage be restarted without redoing completed work?

---

## 1. Ingestion

**Entry criteria:**
- Source file path provided as argument

**Exit criteria:**
- `extracted/source.md` exists and non-empty
- `extracted/metadata.json` exists
- `source/source.<ext>` copied
- `config.yaml` created with source_language, target_language, project_slug

**State files:**
- `state/stage_status.json` → ingestion status = completed

**Validation:**
- File readable, not empty
- Original copied
- Text extracted successfully
- Language detected (or marked unknown with WARN)

**WARN conditions:**
- Language already Russian (translation may not be needed)
- Language detection confidence < 0.5
- File > 10MB (large file warning)

**FAIL conditions:**
- File not readable
- Extraction produced empty text
- File type not supported

**Resumability:** Re-running ingestion overwrites previous extracted text. Use with caution.

---

## 2. Foundation

**Entry criteria:**
- `extracted/source.md` exists

**Exit criteria:**
- `foundation/glossary.md` exists
- `foundation/style.md` exists
- `foundation/entities.md` exists

**State files:**
- `state/stage_status.json` → foundation status = completed/warn

**Validation:**
- All three files exist
- Files are non-empty OR contain placeholder warning

**WARN conditions:**
- Source text < 500 words (insufficient for reliable analysis)
- NER model unavailable (proceed with heuristic fallback)
- LLM backend unavailable (heuristic glossary/style generated)

**FAIL conditions:**
- None. Foundation is enhancement layer, NOT a hard dependency.

**Resumability:** Re-running foundation regenerates all three files from source.md.

---

## 3. Chunking

**Entry criteria:**
- `extracted/source.md` exists

**Exit criteria:**
- `chunks/source/chunk_001.md` ... `chunk_NNN.md` exist
- `chunks/context/chunk_001.context.md` ... exist
- `chunks/manifest.json` exists

**State files:**
- `state/stage_status.json` → chunking status = completed, chunk_count = N

**Chunk rules:**
- Size: 500–1500 words per chunk
- Prefer paragraph/heading boundaries
- Never split mid-sentence
- Never split code blocks
- Never split tables (when possible)
- First and last chunks may be smaller
- Stable IDs: chunk_001, chunk_002, ...

**Context files:**
- `chunks/context/chunk_XXX.context.md` contains:
  - Previous context: LAST 2 sentences of previous chunk (or "None" if first)
  - Next context: FIRST 2 sentences of next chunk (or "None" if last)

**Validation:**
- All chunks exist and non-empty
- No chunk is < 100 words (except first/last)
- No chunk is > 2000 words
- manifest.json matches actual files
- Markdown code blocks not split
- Total word count within 5% of source

**WARN conditions:**
- Large paragraph split by sentence
- Chunk count > 50 (many small chunks)

**FAIL conditions:**
- Chunk count = 0
- All chunks empty

**Resumability:** Re-running chunking overwrites all chunks and manifest. State tracks which chunks are translated separately.

---

## 4. Translation Wave 1

**Entry criteria:**
- All `chunks/source/chunk_XXX.md` exist
- `foundation/glossary.md`, `foundation/style.md`, `foundation/entities.md` exist (or are placeholders)
- `chunks/context/chunk_XXX.context.md` exist

**Exit criteria:**
- All `chunks/translated/wave1/chunk_XXX.md` exist

**State files:**
- `state/stage_status.json` → translation_wave1 status = in_progress/completed
- `chunks/manifest.json` → wave1_status per chunk

**Backend:** Uses `TranslationBackend.translate_chunk()` abstraction.

**Parallelism:** Controlled by `max_workers` in config.

**Validation:**
- All wave1 files created
- No empty files
- Markdown structure preserved
- Length ratio translation/source within 0.5–2.0
- No agent conversational wrappers

**WARN conditions:**
- > 20% of chunks failed
- Length ratio anomaly in > 2 chunks

**FAIL conditions:**
- All chunks failed (backend completely unavailable)
- < 3 chunks succeeded (partial failure)

**Resumability:**
- Completed chunks skipped on restart
- Failed chunks retried once
- manifest.json tracks status per chunk

---

## 5. Translation Wave 2

**Entry criteria:**
- All `chunks/translated/wave1/chunk_XXX.md` exist
- QA remediation file `qa/remediation.json` (if exists) for targeted repair

**Exit criteria:**
- All `chunks/translated/wave2/chunk_XXX.md` exist

**State files:**
- `state/stage_status.json` → translation_wave2 status
- `chunks/manifest.json` → wave2_status per chunk

**Backend:** Same backend as Wave 1.

**Resumability:** Same as Wave 1 — completed chunks skipped.

**Validation:**
- All wave2 files created
- No empty files
- Structure preserved
- Wave2 may be identical to wave1 (this is WARN, not FAIL)

**WARN conditions:**
- > 20% identical to wave1 (possible quality issue)

**FAIL conditions:** Same as Wave 1.

---

## 6. QA Gates

**Entry criteria:**
- All `chunks/translated/wave2/chunk_XXX.md` exist

**Exit criteria:**
- `qa/gate1_terminology.md` exists
- `qa/gate2_integrity.md` exists
- `qa/gate3_style.md` exists
- `qa/gate4_fluency.md` exists
- `qa/gate5_formatting.md` exists
- `qa/summary.md` exists
- `qa/remediation.json` created/updated if issues found

**State files:**
- `state/stage_status.json` → qa_gates status

**Gate behavior:** Gates create reports, NOT hard stops.

**Flow:**
```
QA → remediation.json → repair command → re-check
```

NOT:
```
QA FAIL → terminate everything
```

**Validation:**
- All 5 gate reports exist
- summary.md exists with PASS/WARN/FAIL per gate

**WARN conditions:** Some gate checks flag issues.

**FAIL conditions:**
- Critical integrity failure (chunk missing/truncated)
- < 50% of chunks have valid translations

**Resumability:**
- Completed gates skipped on restart
- Only failed/incomplete gates re-run

---

## 7. Assembly

**Entry criteria:**
- All `chunks/translated/wave2/chunk_XXX.md` exist
- QA gates completed (or skipped)

**Exit criteria:**
- `manuscript.md` exists
- `translated.md` exists (clean, no BLOCK_ID)
- `translated.debug.md` exists (with BLOCK_ID markers)

**State files:**
- `state/stage_status.json` → assembly status = completed

**Assembly steps:**
1. Concatenate wave2 chunks in manifest order
2. Add BLOCK_ID debug markers
3. Strip guardrail markers (`<!--GUARDRAIL:...-->` and `<---->`)
4. Strip context markers
5. Write `translated.debug.md` (with markers)
6. Write `translated.md` (clean, no markers)

**Validation:**
- `translated.md` non-empty
- No guardrail markers remaining
- No context markers remaining
- Word count within 5% of sum of wave2 chunks
- BLOCK_ID present in debug version only

**WARN conditions:**
- Guardrail markers found and stripped
- Empty lines detected in unusual places

**FAIL conditions:**
- Result empty
- Chunk order wrong
- Major content loss detected

**Resumability:** Always regenerates from wave2 chunks. Safe to re-run.

---

## 8. Export

**Entry criteria:**
- `translated.md` exists

**Exit criteria:**
- `output/translated.md` — copy
- `output/translated.txt` — stripped markdown
- `output/translated.docx` — via python-docx
- `output/translated.html` — via markdown parser
- `output/translated.pdf` — via pandoc (optional, warned if unavailable)

**State files:**
- `state/stage_status.json` → export status = completed/partial

**Validation:**
- Required formats (md, txt, docx, html) exist
- PDF attempted if tools available, warned if not

**WARN conditions:**
- PDF export skipped (missing pandoc/xelatex)
- DOCX tables not supported (basic support only)

**FAIL conditions:**
- None for optional PDF
- Required format failed (md/txt/docx/html)

**Resumability:** Safe to re-run — always regenerates from translated.md.

---

## 9. Report

**Entry criteria:**
- All stages above completed
- `output/` directory exists

**Exit criteria:**
- `translation_report.md` exists

**State files:**
- `state/status.json` → overall_status updated to SUCCESS/PARTIAL_SUCCESS

**Resumability:** Safe to re-run.

---

## Stage Status Values

```python
class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WARN = "warn"
    FAILED = "failed"
```

## Overall Status Values

```python
class OverallStatus(str, Enum):
    PREPARED = "PREPARED"       # ingestion done, ready for translation
    IN_PROGRESS = "IN_PROGRESS" # pipeline running
    SUCCESS = "SUCCESS"         # all mandatory stages completed, QA passed
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # all done, some warnings
    FAILED = "FAILED"           # critical failure
```