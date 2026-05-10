# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык в Hermes Agent.

**Статус:** v0.1 alpha.

---

## One-shot установка через Hermes Agent

Скопируйте промпт ниже, вставьте в чат Hermes Agent и отправьте. Агент сам установит и настроит всё необходимое.

```
Установи и настрой Hermes Universal RU Document Translator из репозитория:

https://github.com/perejaslav/hermes-ru-document-translator

Требования:
- Linux/WSL Ubuntu
- Python 3.11+
- git
- internet access

Что нужно сделать пошагово:

1. Клонировать репозиторий в ~/hermes-translator

2. Создать виртуальное окружение:
   python3 -m venv .venv

3. Активировать venv (source .venv/bin/activate) и установить зависимости:
   pip install -U pip
   pip install -e ".[dev]"

4. Установить Hermes skill:
   mkdir -p ~/.hermes/skills
   cp -r skills/universal-ru-document-translator ~/.hermes/skills/

5. Проверить установку:
   python scripts/run_pipeline.py doctor
   pytest

После установки показать:
- git log --oneline -3
- tree -L 2 (или find . -maxdepth 2)
- статус doctor
- статус pytest

Если что-то не хватает:
- установить недостающие apt/python зависимости
- повторить doctor

Не запускать большие переводы автоматически.
Только подтвердить готовность pipeline к использованию.

В конце кратко объяснить:
- как запустить prepare
- где искать output
- как удалить pipeline при необходимости
```

---

## Установка вручную

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