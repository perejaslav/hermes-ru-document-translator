# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык в Hermes Agent.

**Статус:** v0.1 alpha.

---

## One-shot установка через Hermes Agent

Скопируйте промпт ниже, вставьте в чат Hermes Agent и отправьте. Агент сам установит и настроит всё необходимое.

```
Установи и настрой pipeline Hermes Universal RU Document Translator из репозитория:

https://github.com/perejaslav/hermes-ru-document-translator

Цель: установить pipeline для использования в Hermes Agent и проверить, что он готов к работе.

Среда:
- Linux или WSL Ubuntu
- Python 3.11+
- git
- доступ в интернет

Важно:
- Не запускай большие переводы автоматически.
- Не удаляй существующую папку ~/hermes-translator без моего отдельного разрешения.
- Если папка уже существует, сначала покажи git status, git remote -v и спроси, обновлять ли её.
- Все команды выполняй пошагово и показывай ошибки, если они возникнут.

Что нужно сделать:

1. Проверить системные зависимости:

python3 --version
git --version

Если не хватает базовых пакетов, установить:

sudo apt update
sudo apt install -y git python3 python3-venv python3-pip pandoc poppler-utils

2. Клонировать репозиторий:

git clone https://github.com/perejaslav/hermes-ru-document-translator.git ~/hermes-translator
cd ~/hermes-translator

3. Создать виртуальное окружение и установить зависимости:

python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"

4. Установить Hermes skill:

mkdir -p ~/.hermes/skills
rm -rf ~/.hermes/skills/universal-ru-document-translator
cp -r skills/universal-ru-document-translator ~/.hermes/skills/
test -f ~/.hermes/skills/universal-ru-document-translator/SKILL.md

5. Проверить установку:

.venv/bin/python scripts/run_pipeline.py doctor
.venv/bin/python -m pytest

6. Показать итоговую проверку:

git log --oneline -3
tree -L 2
ls ~/.hermes/skills/universal-ru-document-translator

7. В конце кратко сообщить:
- установлен ли pipeline успешно;
- прошёл ли doctor;
- прошёл ли pytest;
- где находится проект;
- где находится Hermes skill;
- как запустить тестовый prepare;
- как удалить pipeline при необходимости.

Пример команды для проверки prepare:

cd ~/hermes-translator
.venv/bin/python scripts/run_pipeline.py prepare examples/sample_python_intro/source.md

Где искать результаты:

~/translations/<project_slug>/
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