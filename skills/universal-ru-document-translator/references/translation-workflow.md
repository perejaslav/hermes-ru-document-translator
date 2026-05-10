# Translation Workflow Reference

## Стандартный цикл v0.1 Direct Mode

### 1. Doctor (всегда first)
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py doctor
```
Проверяет: Python packages, system tools (pandoc, xelatex, pdftotext), fonts, структуру директорий, extractors/exporters, scripts, config, skill.

### 2. Prepare
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py prepare /path/to/doc.[ext]
```
Создаёт workspace в `~/translations/<slug>/`.

### 3. Workspace verification (после prepare)
```bash
# Дерево workspace
find ~/translations/<slug>/ -type f | sort

# state/ файлы
ls ~/translations/<slug>/state/

# manifest.json
cat ~/translations/<slug>/state/manifest.json

# status.json (должен содержать overall_status: PREPARED + все stage статусы)
cat ~/translations/<slug>/state/status.json

# stage_status.json (идентичен status.json)
cat ~/translations/<slug>/state/stage_status.json

# chunk_index.json (список чанков)
cat ~/translations/<slug>/state/chunk_index.json

# Содержимое чанков
ls ~/translations/<slug>/chunks/source/
cat ~/translations/<slug>/chunks/source/chunk_001.md
```

**Обязательные state/ файлы после prepare:**
- `manifest.json` — метаданные документа
- `classification.json` — формат и язык
- `block_index.json` — BLOCK_ID mapping
- `chunk_index.json` — список чанков
- `status.json` — общий статус + stage statuses
- `stage_status.json` — копия status.json

### 4. LLM translation (manual agent step)
Агент переводит чанки через `delegate_task` или текущую сессию Hermes. Записывает результаты в `chunks/translated/<chunk_id>.md`.

### 5. QA
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py qa ~/translations/<slug>/
```
Проверяет переведённые чанки. Результат → `state/qa_findings.json`.

### 6. Merge
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py merge ~/translations/<slug>/
```
Удаляет guardrail-маркеры, собирает чанки в `output/translated.md`.

### 7. Export
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py export ~/translations/<slug>/
```
Экспортирует во все форматы: .md .txt .docx .html .pdf.

### 8. Report
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py report ~/translations/<slug>/
```
Генерирует `output/translation_report.md`.

### 9. Post-translation verification
```bash
# Проверка что guardrails удалены из translated.md
grep -c "GUARDRAIL\|<---->" ~/translations/<slug>/output/translated.md || echo "0 (clean)"

# Проверка output файлов
ls ~/translations/<slug>/output/

# Проверка QA findings (если stale — перезапустить QA после merge)
cat ~/translations/<slug>/state/qa_findings.json
```

## Дополнительные команды

### Resume
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py resume ~/translations/<slug>/
```
Показывает текущий status и следующую pending stage.

### Retry-failed
```bash
~/hermes-translator/.venv/bin/python ~/hermes-translator/scripts/run_pipeline.py retry-failed ~/translations/<slug>/
```
Показывает какие чанки помечены как failed.

## Workspace path pattern
```
~/translations/<sanitized_stem>_<YYYYMMDD>_<short_hash>/
```

Где:
- `sanitized_stem` = basename файла без расширения,safe for filesystem (без кириллицы/спецсимволов)
- `YYYYMMDD` = сегодняшняя дата
- `short_hash` = md5-хеш полного пути файла (6 символов)

Пример: `sample_python_intro_20260510_db0f24/`

## Output files после полного цикла
```
output/
  translated.md          ← чистый перевод (без BLOCK_ID, без guardrails)
  translated.debug.md    ← то же с BLOCK_ID (для QA/отладки)
  glossary.md            ← всегда создаётся (placeholder или реальный)
  translated.txt         ← best-effort
  translated.docx       ← best-effort
  translated.html       ← best-effort
  translated.pdf        ← best-effort (xelatex required)
  translation_report.md

state/
  manifest.json
  classification.json
  block_index.json
  chunk_index.json
  status.json            ← обновляется после каждой команды
  stage_status.json      ← копия status.json
  qa_findings.json       ← после qa (post-merge: отражает финальный файл)
  export_results.json    ← после export
```

## Known issues

### QA findings: pre-merge vs post-merge
Pre-merge QA проверяет `chunks/translated/` — там ещё есть guardrail-маркеры до merge.
Warning "10 guardrail markers still present" в qa_findings.json — это нормально до merge.
Post-merge QA (запускается после merge) проверяет `output/translated.md` — финальный результат.

### overall_status: когда SUCCESS, когда PARTIAL_SUCCESS
- `SUCCESS`: все стадии completed, glossary реальный (не placeholder), qa_findings.clean
- `PARTIAL_SUCCESS`: glossary placeholder ИЛИ есть warnings в qa_findings
- После `report` вызывается `set_complete()` который определяет автоматически