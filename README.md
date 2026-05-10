# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык в Hermes Agent.

**Статус:** v0.1 alpha.

## Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/perejaslav/hermes-ru-document-translator.git
cd hermes-ru-document-translator

# 2. Создать виртуальное окружение и установить зависимости
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"

# 3. Установить Hermes skill
mkdir -p ~/.hermes/skills
cp -r skills/universal-ru-document-translator ~/.hermes/skills/
```

## Проверка

```bash
python scripts/run_pipeline.py doctor
pytest
```

## Быстрый пример

```bash
python scripts/run_pipeline.py prepare examples/sample_python_intro/source.md
```

После этого в рабочей директории появится `chunks/source/` и `status.json`.

## Структура выходных файлов

Результат перевода сохраняется в `~/translations/<project_slug>/`:

- `translated.md` — чистый перевод без служебных меток
- `translated.debug.md` — перевод с BLOCK_ID для QA-проверки
- `glossary.md` — глоссарий терминов (placeholder в v0.1)
- `translation_report.md` — отчёт о выполнении
- `status.json` — текущий статус pipeline

## Поддерживаемые форматы v0.1

- `.txt`
- `.md` / `.markdown`
- `.docx`
- `.html`
- text-based `.pdf` (best-effort)

## Не поддерживается в v0.1

- EPUB
- OCR (сканированные PDF)
- batch-обработка директорий
- watch-folder
- cron
- provider-api
- pixel-perfect PDF
- Kanban-доска

## License

MIT License.