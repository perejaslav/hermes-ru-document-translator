# Universal RU Document Translator

Автоматический перевод документов на русский язык для Hermes Agent.

## Статус

**v0.1 Direct MVP** — реализовано. Kanban, OCR, EPUB, batch отложены.

## Быстрый старт

```bash
# Перевести документ
python3 ~/hermes-translator/scripts/run_pipeline.py /path/to/document.[ext]
```

## Поддерживаемые форматы (v0.1)

| Формат | Статус | Зависимости |
|--------|--------|-------------|
| `.txt` | ✅ полная поддержка | — |
| `.md` / `.markdown` | ✅ полная поддержка | — |
| `.docx` | ✅ полная поддержка | python-docx |
| `.html` | ✅ полная поддержка | BeautifulSoup4, lxml |
| text-based `.pdf` | ✅ полная поддержка | PyMuPDF |
| `.epub` | 🟡 заглушка | stub only (v0.2+) |
| scanned `.pdf` | ❌ не поддерживается | OCR (v0.2+) |

## Результаты

### Гарантированные
- `output/translated.md` — основной результат
- `output/glossary.md` — глоссарий терминов
- `output/translation_report.md` — отчёт о переводе
- `state/status.json` — состояние пайплайна

### Best-effort
- `output/translated.docx`, `.html`, `.txt`, `.pdf`

## Ключевые принципы

1. **Исходный файл никогда не меняется на месте**
2. **Markdown — основной гарантированный результат**
3. **Честный отчёт о проблемах** — пайплайн не притворяется успешным если что-то сломалось

## Архитектура

```
hermes-agent (orchestrator)
  └── Python pipeline (mechanical stages)
        ├── extractors/  — извлечение из разных форматов
        ├── exporters/   — экспорт в разные форматы
        ├── qa/          — проверки качества
        └── state/       — управление состоянием
  └── Hermes LLM (translation stages)
        ├── build_glossary
        └── translate_chunks
```

## v0.1 Limitations

- Нет batch-обработки
- Нет watch-folder
- Нет cron
- Нет OCR
- PDF export — best-effort
- Side-by-side — только по запросу