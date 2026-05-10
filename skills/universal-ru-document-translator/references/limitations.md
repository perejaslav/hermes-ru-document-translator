# Limitations

## v0.1 Direct MVP

### Supported
- Single file processing only
- Languages: any supported by source extractor and target LLM
- Text-based documents (no scanned images)
- Documents up to ~100K characters (soft limit, depends on LLM context)

### Not Supported
- Batch processing (multiple files in one run)
- Watch-folder automation
- Cron-triggered runs
- OCR for scanned PDFs
- EPUB format
- provider-api (direct LLM API from Python)
- Full translation cache
- Pixel-perfect PDF export (best-effort only)

### Format-Specific

| Format | Limitation |
|--------|-------------|
| PDF | Only text layer (no OCR). Vector graphics may be lost. |
| DOCX | Track changes, comments, revision history not preserved. |
| HTML | Complex JavaScript-rendered content not supported. |
| Markdown | Some flavor-specific syntax may not round-trip perfectly. |

### Quality Boundaries

- Translation quality depends on source document clarity
- Complex technical documents may need manual post-editing
- Literary texts may need literary editor review
- Documents with mixed scripts (e.g., Chinese + English) may have inconsistent handling

### Edge Cases

- Very short documents (<100 chars): may have poor chunking
- Very long documents (>100K chars): may hit LLM context limits
- Documents with unusual encodings: may need manual charset detection
- Password-protected files: not supported
- Corrupted files: partial extraction with warning

## Known Issues

1. Side-by-side mode for large books can produce very large files
2. PDF export may fail if xelatex/font dependencies missing
3. BLOCK_ID injection changes document structure slightly (acceptable for QA)
4. Protected spans rely on placeholder markers that are stripped at end