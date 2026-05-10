# Segmentation Rules

## Target Chunk Size

~1000-2000 tokens per chunk (model-agnostic, works with most LLM context windows).

## Structural Priority

Always try to respect these boundaries (in priority order):

1. **Chapter/Section headers** (H1, H2) — prefer as chunk boundaries
2. **Paragraph breaks** — secondary boundary
3. **Sentence boundaries** — fallback
4. **Clause/phrase** — last resort (only if paragraph is huge)

## Hard Rules

1. **Never** split mid-sentence if a paragraph boundary is nearby
2. **Never** put less than 3 sentences in a chunk unless it's a heading section
3. **Never** exceed 2500 tokens per chunk
4. **Prefer** to end chunks at natural transition points

## Chunk Metadata

Each chunk gets:
- `CHUNK_ID`: sequential, format `chunk_001`, `chunk_002`, ...
- `BLOCK_IDs`: list of source block IDs contained in this chunk
- `char_count`: character count for QA
- `token_estimate`: approximate token count

## Special Handling

### Code Blocks
- Keep code blocks as single units if possible
- If code block is very long (>500 lines), split at logical points but preserve code integrity
- Mark split with `<!--CODE_CONTINUED-->` comment

### Lists
- Prefer to keep list items together in one chunk
- If list is very long (>20 items), split at sub-list boundaries

### Tables
- Treat tables as single blocks, do not split
- If table is huge, split at row boundaries

### Block IDs in Content
- Every meaningful content block gets a BLOCK_ID
- Format: `<!--BLOCK_ID: <section>_<subsection>_<number>-->`
- Example: `<!--BLOCK_ID: ch1_intro_001-->`

## Chunk Index

`state/chunk_index.json` maps each CHUNK_ID to:
- File path in `chunks/source/` and `chunks/translated/`
- BLOCK_IDs contained
- Status (pending, translated, failed, reviewed)