# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык.

**Статус: v0.1 Direct MVP**

## Быстрый старт

```bash
source ~/hermes-translator/.venv/bin/activate
python3 ~/hermes-translator/scripts/run_pipeline.py /path/to/document.[ext]
```

## Структура

```
hermes-translator/
├── config.yaml           — конфигурация пайплайна
├── scripts/              — выполняемые скрипты
│   ├── run_pipeline.py   — главный раннер
│   ├── ingest.py         — копирование в workspace
│   ├── extract.py        — извлечение из формата
│   ├── normalize.py      — нормализация Markdown
│   ├── protect_spans.py  — защита непереводимого
│   ├── assign_block_ids.py
│   ├── build_glossary_inputs.py
│   ├── segment.py        — чанкинг
│   ├── qa_chunk.py       — QA-проверки
│   ├── merge.py          — сборка результата
│   ├── export.py         — экспорт в форматы
│   └── final_report.py
├── translator/
│   ├── extractors/       — модули извлечения
│   ├── exporters/        — модули экспорта
│   ├── qa/               — QA-проверки
│   ├── state/            — управление состоянием
│   └── kanban/          — ЗАГЛУШКА (v0.2+)
└── tests/
```

## Зависимости

- Python >= 3.11
- PyMuPDF, python-docx, BeautifulSoup4, lxml, markdown-it-py

## Поддерживаемые форматы (v0.1)

`.txt` `.md` `.markdown` `.docx` `.html` text-based `.pdf`

## Не поддерживаются в v0.1

EPUB, OCR, batch, watch-folder, cron, provider-api — заглушки или отложено.

## v0.2+ планируется

EPUB, OCR (tesseract), batch directories, watch-folder, kanban, provider-api.