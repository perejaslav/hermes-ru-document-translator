# Canonical Directory Structure

## Repository Root (canonical repo only)

```
hermes-ru-document-translator/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── pipeline-stages.md
│   ├── state-schema.md
│   ├── directory-structure.md
│   ├── architecture.md
│   ├── troubleshooting.md
│   ├── contributing.md
│   └── migration-from-translation-pipeline.md
├── examples/
│   └── sample_python_intro/
│       ├── source.md
│       ├── translated.md
│       └── ...
├── scripts/
│   └── run_pipeline.py
├── skills/
│   └── universal-ru-document-translator/
│       ├── SKILL.md
│       └── worker.md
├── tests/
│   ├── test_extractors.py
│   ├── test_chunking.py
│   ├── test_state.py
│   ├── test_manifest.py
│   ├── test_assembly.py
│   ├── test_export_md_txt_html.py
│   ├── test_backend_mock.py
│   ├── test_gate1_terminology.py
│   ├── test_gate2_integrity.py
│   ├── test_gate3_style.py
│   ├── test_gate4_fluency.py
│   ├── test_gate5_formatting.py
│   └── test_full_cycle_mock.py
├── translator/
│   ├── __init__.py
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py          # TranslationBackend interface
│   │   ├── mock.py          # offline test backend
│   │   ├── hermes_delegate.py
│   │   ├── minimax_api.py
│   │   ├── sequential.py
│   │   └── sanitizer.py     # strip conversational wrappers
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── markdown.py
│   │   ├── txt.py
│   │   ├── docx.py
│   │   ├── html.py
│   │   ├── pdf.py
│   │   └── epub.py          # stub for v1.0
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   ├── txt.py
│   │   ├── docx.py
│   │   ├── html.py
│   │   └── pdf.py           # optional, warned if unavailable
│   ├── qa/
│   │   ├── __init__.py
│   │   ├── gate1_terminology.py
│   │   ├── gate2_integrity.py
│   │   ├── gate3_style.py
│   │   ├── gate4_fluency.py
│   │   └── gate5_formatting.py
│   └── orchestration/
│       ├── __init__.py
│       └── parallel_translator.py
├── config.yaml
├── pyproject.toml
├── .gitignore
├── LICENSE
└── README.md
```

Note: `translator/state/` is NOT per-project runtime storage. It is an internal Python module only.

---

## Per-Project Runtime Workspace

Every translation project lives in:

```
~/translations/<project_slug>/
```

Example:

```
~/translations/sample_python_intro_20260510_db0f24/
```

### Canonical Project Structure

```
<project_slug>/
├── config.yaml                  # static project configuration
├── state/
│   ├── status.json              # overall pipeline status
│   └── stage_status.json        # per-stage status tracking
├── source/
│   └── source.<ext>             # original file (preserved)
├── extracted/
│   ├── source.md                 # extracted plain text
│   └── metadata.json             # extraction metadata
├── foundation/
│   ├── glossary.md              # bilingual terminology table
│   ├── style.md                  # translation style rules
│   └── entities.md              # named entity register
├── chunks/
│   ├── manifest.json            # chunk inventory (single source of truth)
│   ├── source/
│   │   ├── chunk_001.md
│   │   └── chunk_002.md
│   ├── context/
│   │   ├── chunk_001.context.md
│   │   └── chunk_002.context.md
│   ├── prompts/
│   │   ├── chunk_001.wave1.prompt.md
│   │   └── chunk_002.wave1.prompt.md
│   └── translated/
│       ├── wave1/
│       │   ├── chunk_001.md
│       │   └── chunk_002.md
│       └── wave2/
│           ├── chunk_001.md
│           └── chunk_002.md
├── qa/
│   ├── gate1_terminology.md
│   ├── gate2_integrity.md
│   ├── gate3_style.md
│   ├── gate4_fluency.md
│   ├── gate5_formatting.md
│   ├── remediation.json
│   └── summary.md
├── manuscript.md                 # assembled from wave2 chunks
├── translated.md                 # clean final translation
├── translated.debug.md            # with BLOCK_ID markers for QA
├── translation_report.md         # execution report
└── output/
    ├── translated.md
    ├── translated.txt
    ├── translated.docx
    ├── translated.html
    └── translated.pdf           # optional
```

---

## Key Rules

1. `state/` is the ONLY canonical location for runtime state within a project.
2. `manifest.json` is the ONLY canonical source of truth for chunk list and ordering.
3. Context files are stored separately from source chunks — never embedded inside chunk text.
4. `translated.md` is the clean output. `translated.debug.md` includes BLOCK_ID for QA traceability.
5. `output/` contains format-specific exports regenerated from `translated.md`.
6. `source/` preserves the original file for reference.
7. `extracted/` contains the extracted plain text used for processing.