# Format Support Matrix

## v0.1 MVP — Full Support

| Format | Extension | Extractor | Notes |
|--------|-----------|-----------|-------|
| Plain text | `.txt` | `txt.py` | Direct read, charset auto-detect |
| Markdown | `.md`, `.markdown` | `markdown.py` | Preserve structure |
| Word document | `.docx` | `docx.py` | via python-docx |
| HTML | `.html`, `.htm` | `html.py` | BeautifulSoup4 + lxml |
| Text-based PDF | `.pdf` | `pdf.py` | via PyMuPDF, text layer only |

## v0.2 — Planned

| Format | Extension | Extractor | Notes |
|--------|-----------|-----------|-------|
| EPUB | `.epub` | `epub.py` | epub2/epub3 support |
| Scanned PDF | `.pdf` | `pdf.py` + OCR | tesseract-ocr integration |
| Mixed PDF | `.pdf` | `pdf.py` + layout analysis | text + images |

## Not Planned (v0.x)

| Format | Notes |
|--------|-------|
| `.odt` | OpenDocument Text |
| `.rtf` | Rich Text Format |
| `.pptx` | PowerPoint |
| `.xlsx` | Excel |
| Batch directories | Multiple files |
| Watch-folder | File system events |

## URL Input

v0.1: URL input accepted only if Hermes/orchestrator downloads the content and saves as local `input/original.ext`.

Full web scraping, bypass blocks, readability extraction — NOT in v0.1.