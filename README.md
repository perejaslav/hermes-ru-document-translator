# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык в Hermes Agent.

**Статус:** v0.1 Direct MVP.

## Быстрый старт

```bash
source ~/hermes-translator/.venv/bin/activate
python3 ~/hermes-translator/scripts/run_pipeline.py doctor
```

## Поддерживаемые форматы v0.1

- `.txt`
- `.md`
- `.markdown`
- `.docx`
- `.html`
- text-based `.pdf`

## Не поддерживается в v0.1

- EPUB
- OCR
- batch directories
- watch-folder
- cron
- provider-api
- pixel-perfect PDF

## Структура

```text
hermes-translator/
├── config.yaml
├── scripts/
├── skills/universal-ru-document-translator/
├── translator/
└── tests/
```

## Гарантированные результаты

- `output/translated.md`
- `output/glossary.md`
- `output/translation_report.md`
- `state/status.json`

## Best-effort export

- DOCX
- HTML
- TXT
- PDF

## License

Not specified yet.
