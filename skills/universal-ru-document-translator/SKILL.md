---
name: universal-ru-document-translator
description: Автоматический перевод документов на русский язык. Поддерживает txt, md, docx, html, text-based PDF. Не изменяет исходный файл. Workspace-based pipeline с chunk-by-chunk переводом и QA.
version: 0.1.0
category: document-processing
trigger: ".txt .md .markdown .docx .html .pdf перевод translate document document translation русский"
---

# Universal RU Document Translator — SKILL.md

## 1. Когда использовать

Используй этот скилл когда пользователь просит перевести документ, статью, книгу или текст на русский язык.

**Поддерживаемые форматы (v0.1):**
- `.txt`
- `.md` / `.markdown`
- `.docx`
- `.html`
- text-based `.pdf`

**Не поддерживаются в v0.1:**
- `.epub` (stub only)
- scanned PDF (OCR не реализован)
- batch directories
- watch-folder
- URL-based input (только если файл скачан и сохранён локально)

## 2. Режимы работы

### 2.1 Direct Mode (v0.1 MVP)

По умолчанию для одиночных файлов до ~50K символов.

Агент выполняет все стадии сам:
1. intake → copy to workspace
2. extract → canonical markdown
3. normalize → structure cleanup
4. protect_spans → code/placeholder protection
5. assign_block_ids → stable IDs for QA
6. segment → chunking for LLM
7. build_glossary → build glossary/style guide via LLM
8. translate_chunks → translate via current Hermes session or delegate_task
9. deterministic_qa → completeness, structure, language checks
10. merge → assemble translated chunks
11. export → md, docx, html, txt (pdf best-effort)
12. final_report → translation_report.md

### 2.2 Kanban Mode (NOT in v0.1)

Отложено. Для больших книг и batch-обработки. Будет реализовано после отдельной команды пользователя.

## 3. Workspace

Каждый документ создаёт отдельный workspace:

```
~/translations/<project_slug>/
```

`project_slug` = `<sanitized_stem>_<YYYYMMDD>_<short_hash>`

**Правила:**
- Исходный файл пользователя никогда не изменяется на месте
- Копия всегда создаётся в workspace
- Если workspace уже существует — НЕ перезаписывать без `--force`

## 4. Обязательные результаты (гарантированные)

Для каждого успешно обработанного документа:

```
output/translated.md          ← чистый перевод (без BLOCK_ID, без guardrails)
output/translated.debug.md    ← то же с BLOCK_ID (для QA/отладки)
output/glossary.md            ← всегда создаётся (placeholder или реальный)
output/translation_report.md
state/status.json
state/stage_status.json        ← копия status.json для удобства
```

## 5. Best-effort результаты (если возможно)

```
output/translated.docx
output/translated.html
output/translated.txt
output/translated.pdf      ← только если зависимости на месте
output/qa_report.md
output/side_by_side.md     ← только при --side-by-side=full
state/qa_findings.json
```

## 6. PDF export

PDF — best-effort. Если pandoc/xelatex/шрифты недоступны:
1. Создать `translated.md` ✓
2. Создать остальные доступные форматы ✓
3. Записать warning в `translation_report.md`
4. Статус = `PARTIAL_SUCCESS` (не `FAILED_TRANSLATION`)

## 7. LLM Execution Backend (v0.1)

```
delegate_task / hermes-current orchestration
```

**NOT in v0.1:** provider-api, direct LLM API calls from Python.

## 8. Stage Execution Flow

### Mechanical stages (Python scripts):
`ingest` → `classify` → `extract` → `normalize` → `protect_spans` → `assign_block_ids` → `segment` → `qa_chunk` → `merge` → `export` → `final_report`

### LLM stages (Hermes agent):
- `build_glossary` — создание глоссария и style guide
- `translate_chunks` — перевод каждого чанка

## 9. Chunking Rules

- Target: ~1000–2000 токенов на chunk (model-agnostic)
- Respect structural boundaries (headers, paragraphs)
- Never split mid-sentence if avoidable
- Each chunk gets stable CHUNK_ID and BLOCK_ID references

## 10. QA Gates

### Deterministic QA (always):
- Completeness check (no dropped blocks) — via BLOCK_ID in `translated.debug.md`
- BLOCK_ID cleanup verification — `translated.md` should have 0 BLOCK_ID markers
- Markdown structure integrity
- Language detection (should contain Cyrillic after translation)
- Guardrail/placeholder cleanup — both in final output
- Empty file check

### QA всегда проверяет ФИНАЛЬНЫЙ output/translated.md (post-merge mode)
QA запускается дважды: до merge (проверяет чанки) и после merge (проверяет финальный файл).
qa_findings.json отражает СОСТОЯНИЕ output/translated.md, не промежуточных чанков.
Если `output/translated.md` существует — QA работает в post-merge mode.

## 11. Error Handling

- Extraction failure → `EXTRACTION_FAILED`, partial output acceptable
- Translation failure → `TRANSLATION_FAILED`, report which chunks failed
- Export failure → `EXPORT_PARTIAL`, try other formats
- If `translated.md` exists and main translation done → `PARTIAL_SUCCESS` not `FAILED`

## 12. Side-by-side Mode

Param: `--side-by-side never|failed|sample|full`

Defaults:
- `fast` → `never` or `failed`
- `balanced` → `failed` or `sample`
- `high` → `full`

Для больших книг `full` side_by_side может быть очень тяжёлым. В `balanced`-режиме по умолчанию НЕ создавать полный side-by-side.

## 13. Kanban Mode (NOT IMPLEMENTED IN v0.1)

Stub exists at `~/hermes-translator/translator/kanban/`.

Tasks for v0.1 Kanban implementation (future):
- Translation task per chunk
- Glossary task
- QA task
- Merge task

## 14. Files that workers can write

Worker/subagent может записывать:
- `chunks/translated/<chunk_id>.md` — переведённый чанк
- `chunks/glossary_additions.md` — дополнения к глоссарию
- `state/worker_status.json` — свой статус

## 15. Files only orchestrator updates

Только главный агент/оркестратор может обновлять:
- `state/status.json` — общий статус пайплайна
- `state/chunk_index.json` — индекс чанков
- `state/block_index.json` — индекс блоков
- `output/translated.md` — финальный перевод
- `output/translation_report.md` — финальный отчёт

## 17. Final User Response

Вернуть пользователю:
1. Путь(и) к результатам (`translated.md`, `translated.docx`, etc.)
2. Краткое резюме: что сделано, сколько чанков, есть ли проблемы
3. Ссылка на `translation_report.md` если есть warnings
4. Честный статус: SUCCESS / PARTIAL_SUCCESS / FAILED

## 18. LLM-стадии: роль агента vs Python-скриптов

**Важно:** Python-скрипты выполняют только МЕХАНИЧЕСКИЕ стадии. Перевод делает агент через Hermes.

В run_pipeline.py LLM-стадии помечены как `pending_agent`:
- `glossary` — агент создаёт glossary.md через LLM
- `translation` — агент переводит чанки через delegate_task или текущую сессию

После запуска `run_pipeline.py` агент должен:
1. Прочитать сгенерированные chunks из `chunks/source/`
2. Создать glossary/style guide
3. Перевести каждый чанк, записывая результаты в `chunks/translated/<chunk_id>.md`
4. Запустить `qa_chunk.py` для проверки
5. Продолжить с merge → export → final_report

## 19. Пользовательские предпочтения коммуникации

- **Формат ответа:** plain text, НЕ markdown, renderable в терминале
- **Стиль:** кратко, тезисно, простыми словами; точные формулировки
- **Деревья:** использовать `find` + `ls` вывод, компактно
- **Не начинать перевод** без отдельной явной команды пользователя
- **Сначала doctor + tree + deps** — показать структуру до начала работ
- Перед установкой всегда сверяться с существующими скиллами

## 17. CLI Usage

```bash
# Проверка системы (всегда сначала)
python3 ~/hermes-translator/scripts/run_pipeline.py doctor

# Подготовка workspace (только механические стадии)
python3 ~/hermes-translator/scripts/run_pipeline.py prepare /path/to/doc.[ext]

# QA после перевода чанков
python3 ~/hermes-translator/scripts/run_pipeline.py qa ~/translations/<project>/
python3 ~/hermes-translator/scripts/run_pipeline.py merge ~/translations/<project>/
python3 ~/hermes-translator/scripts/run_pipeline.py export ~/translations/<project>/
python3 ~/hermes-translator/scripts/run_pipeline.py report ~/translations/<project>/
```

## 18. Pitfalls

### Python packages в venv
uv НЕ включает pip в виртуальном окружении по умолчанию. Если `python -m pip` не работает внутри venv — используй `uv pip install` с флагом `--python path/to/venv/bin/python`.

Системные пакеты (beautifulsoup4, lxml, markdown-it-py) НЕ попадают в venv автоматически при `uv venv`. После создания venv всегда переустанавливай нужные пакеты:
```bash
uv pip install beautifulsoup4 lxml markdown-it-py html2text chardet --python ~/hermes-translator/.venv/bin/python
```

### mkdir требует parents=True
В Python `pathlib.Path.mkdir(exist_ok=True)` падает с `FileNotFoundError` если родительская директория не существует. Всегда используй `mkdir(parents=True, exist_ok=True)`.

### detect_language vs extract в extractors
Extractor-функции `extract()` принимают `Path`, а `detect_language()` / `get_language()` принимают **строку** (содержимое файла). В classify_document.py нужно читать файл перед вызовом detect_language:
```python
with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
    file_content = f.read()
detected_lang = detect_language(file_content)  # не detect_language(input_file)
```
Это частая ошибка при добавлении новых extractors.

### Guardrail markers: два типа закрытия
protect_spans.py ставит **два** вида маркеров:
- Открывающий: `<!--GUARDRAIL:name-->...content...`
- Закрывающий: `<---->` (фрагмент, не полный тег)

merge.py должен удалять **оба**:
```python
GUARDRAIL_OPEN_PATTERN = re.compile(r'<!--GUARDRAIL:[^>]+-->')
GUARDRAIL_CLOSE_FRAGMENT = '<---->'

content = GUARDRAIL_OPEN_PATTERN.sub('', content)
content = content.replace(GUARDRAIL_CLOSE_FRAGMENT, '')
```
Если `<---->` не удалён — в `translated.md` останутся артефакты.

### status.json/stage_status.json обновляются после каждой стадии
cmd_qa, cmd_merge, cmd_export, cmd_report — все используют `PipelineStatus.load()` → `set_stage()` → `save()`.
После cmd_report вызывается `set_complete()` который определяет overall_status (SUCCESS/PARTIAL_SUCCESS).
Оба файла (`status.json` и `stage_status.json`) обновляются после каждой команды.

### QA dual-mode: pre-merge и post-merge
qa_chunk.py автоматически определяет режим:
- Если `output/translated.md` существует → **post-merge mode** (проверяет финальный файл)
- Иначе → **pre-merge mode** (проверяет чанки в `chunks/translated/`)

**Правильная последовательность:**
1. `prepare` → создаёт workspace, glossary placeholder, status.json
2. Агент переводит чанки → записывает в `chunks/translated/<chunk_id>.md`
3. `qa` (первый запуск) → pre-merge, проверяет чанки
4. `merge` → создаёт `output/translated.md` + `output/translated.debug.md`
5. `qa` (второй запуск) → post-merge, проверяет финальный файл; qa_findings.json обновляется
6. `export`
7. `report` → overall_status = SUCCESS/PARTIAL_SUCCESS

### BLOCK_ID: два файла на выходе из merge
merge.py создаёт **два** файла:
- `output/translated.md` — чистый пользовательский output (BLOCK_ID стёрты)
- `output/translated.debug.md` — то же с BLOCK_ID (для QA и отладки)

BLOCK_ID стёрт из пользовательского файла. Всегда.

### stage_status.json — копия status.json
После `prepare` сохраняются два файла: `status.json` и `stage_status.json`. Они идентичны. `stage_status.json` — отдельный файл для удобства (можно открыть не загружая Python-модуль PipelineStatus).

### glossary.md всегда создаётся
`output/glossary.md` создаётся в `cmd_prepare` через `_create_glossary_placeholder()`.
Это гарантирует что файл существует всегда — placeholder или реальный glossary.
Stage `glossary` в status = `completed` (placeholder) с warning.
Реальный glossary content = pending_agent LLM step (обновить позже).

### Doctor перед prepare
Всегда запускай `doctor` перед первым `prepare` в новой сессии. Это подтвердит что все зависимости на месте.

### Статус пайплайна
`status.json` (PipelineStatus) не создаётся stage-скриптами напрямую. stage-скрипты работают автономно и сохраняют только свои state-файлы. Для полного status tracking нужен orchestrator.

## 19. Key Learnings (v0.1)

- v0.1 реализует ТОЛЬКО механические стадии; LLM-стадии требуют ручного вызова агента
- epub, OCR, kanban, batch, watch-folder, provider-api — ЗАГЛУШКИ или отложены
- prepare создаёт 1 chunk для документа <2K токенов; для больших — несколько
- BLOCK_ID внедряется в каждый paragraph для QA; guardrail-маркеры ставятся на code/URL/email
- merge stage создаёт **два** файла: translated.md (чистый) и translated.debug.md (с BLOCK_ID)
- QA post-merge проверяет финальный файл; qa_findings.json = авторитетный результат
- status.json/stage_status.json обновляются после каждой команды (qa/merge/export/report)
- output/glossary.md создаётся всегда (placeholder или real)
- overall_status после report: SUCCESS (всё чисто) или PARTIAL_SUCCESS (есть warnings)
- build_glossary_inputs.py: баг — `.exists` вместо `.exists()` → patch при обнаружении

## 20. References

- `references/spec-comparison-pattern.md` — compare spec vs installed implementation (user asks "check, don't install")
- `references/qa_checklist.md` — QA gates и severity levels
- `references/segmentation_rules.md` — chunking rules и BLOCK_ID format
- `references/format_support.md` — supported formats matrix
- `references/kanban_task_graph.md` — Kanban architecture (stub)
- `references/limitations.md` — v0.1 limitations
- `references/execution_backends.md` — execution backends