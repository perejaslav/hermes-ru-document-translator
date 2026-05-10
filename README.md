# Hermes Universal Document Translator

Python-пакет для автоматического перевода документов на русский язык в Hermes Agent.

**Статус:** v0.2 — unified pipeline (2-wave translation, Foundation, 5 QA gates).

---

## Что нового в v0.2

Объединены два репозитория — `hermes-ru-document-translator` (A) и `hermes-translation-pipeline` (B).
Из B перенесены: Foundation stage, 2-wave translation, 5 QA gates, repair/remediation, backend fallback.
Из A перенесены: Python package, CI, state management, multi-format export, resumable pipeline.

Canonical workspace: `~/translations/<project_slug>/` (не `workspace/`).

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
df -h ~
command -v hermes || echo "Hermes Agent not found"

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
```

---

## Установка вручную

```bash
# 1. Клонировать репозиторий
git clone https://github.com/perejaslav/hermes-ru-document-translator.git ~/hermes-translator
cd ~/hermes-translator

# 2. Установить системные зависимости
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip pandoc poppler-utils

# 3. Создать виртуальное окружение и установить зависимости
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"

# 4. Установить Hermes skill
mkdir -p ~/.hermes/skills
cp -r skills/universal-ru-document-translator ~/.hermes/skills/
```

## Проверка

```bash
python scripts/run_pipeline.py doctor
.venv/bin/python -m pytest
```

---

## Быстрый старт (полный цикл на mock backend)

```bash
# 1. Проверка окружения
python scripts/run_pipeline.py doctor

# 2. Создать проект из файла
python scripts/run_pipeline.py prepare examples/sample.md

# 3. Перевести всё (wave1 + wave2, mock backend)
python scripts/run_pipeline.py translate <project_slug> --backend mock

# 4. QA — 5 гейтов
python scripts/run_pipeline.py qa <project_slug>

# 5. Починить проблемные чанки (если QA выдал warnings)
python scripts/run_pipeline.py repair <project_slug> --backend mock

# 6. Собрать финальный документ
python scripts/run_pipeline.py merge <project_slug>

# 7. Экспорт во все форматы
python scripts/run_pipeline.py export <project_slug>

# 8. Сгенерировать отчёт
python scripts/run_pipeline.py report <project_slug>

# Статус проекта
python scripts/run_pipeline.py status <project_slug>

# Список всех проектов
python scripts/run_pipeline.py list
```

---

## Где искать результаты

```
~/translations/<project_slug>/
├── chunks/
│   ├── source/             # извлечённые чанки
│   ├── context/            # контекст (пред/след чанк)
│   └── translated/
│       ├── wave1/          # первый проход перевода
│       └── wave2/          # дошлифовка
├── foundation/             # glossary.md, style.md, entities.md
├── qa/                     # отчёты 5 гейтов + remediation.json
├── output/                 # финальные файлы
│   ├── translated.md       # основной результат
│   ├── translated.docx
│   ├── translated.html
│   ├── translated.txt
│   ├── translated.pdf      # optional
│   ├── translation_report.md
│   └── glossary.md
└── state/
    ├── status.json         # общий статус pipeline
    └── stage_status.json
```

---

## Ключевые концепции

### Foundation
Анализ исходного текста до начала перевода. Создаёт glossary.md (термины), style.md (стиль), entities.md (именованные сущности). Не блокирует pipeline — при недоступности LLM используется эвристический fallback.

### 2-wave translation
**Wave 1:** параллельный перевод всех чанков с контекстом из предыдущего чанка.
**Wave 2:** дошлифовка каждого чанка с учётом wave1 + glossary + style.
Semaphore: max 3 concurrent workers.

### 5 QA Gates
После wave2 работают 5 гейтов:

| Гейт | Проверяет | При неудаче |
|---|---|---|
| Gate 1: Terminology | Корректность перевода терминов | WARN |
| Gate 2: Integrity | Сохранность контента, структуры | FAIL → remediation |
| Gate 3: Style | Соответствие style.md | WARN |
| Gate 4: Fluency | Естественность русского языка | WARN |
| Gate 5: Formatting | Markdown, code blocks | WARN |

QA не блокирует pipeline — результаты идут в `qa/remediation.json`.

### Remediation и Repair
`qa/remediation.json` содержит mapping `chunk_id → [проблемные гейты]`.
`repair` перезапускает wave2 только для указанных чанков. НЕ перезапускает весь pipeline.

### Status: SUCCESS vs PARTIAL_SUCCESS
- `SUCCESS` — все стадии завершены, warnings нет
- `PARTIAL_SUCCESS` — завершено с QA warnings или отсутствующим PDF

---

## Backends

| Backend | Назначение |
|---|---|
| `mock` | Оффлайн-тестирование, deterministic, всегда работает |
| `hermes_delegate` | Hermes runtime-only / experimental (не запускается через `python scripts/run_pipeline.py`) |
| `minimax_api` | Direct MiniMax API backend (experimental/stub, зависит от сборки) |
| `sequential` | Однопоточный fallback для безопасного тестирования |

### Sanitizer

Очистка вывода перевода:

- **Reasoning blocks:** `<think>`, `<thinking>`, `<reasoning>` удаляются автоматически (DOTALL, non-greedy, case-insensitive).
- **Конверсационные обёртки:** `"Вот перевод:"`, `"Here's the translation:"` и др.
- **CJK-контаминация:** детектируется (threshold 2%). При превышении в выходной файл добавляется `<!-- WARNING -->` комментарий. Текст не удаляется, чтобы не ломать легитимный мультиязычный контент.
- **Whitespace normalization:** после удаления блоков множественные пустые строки схлопываются.

Для тестирования: `--backend mock`.

Для production CLI-запуска не используйте `mock`. Указывайте рабочий прямой backend явно, например `--backend minimax_api`, когда он настроен и проходит healthcheck.

`hermes_delegate` является Hermes runtime-only / experimental backend: он не предназначен для обычного запуска через `python scripts/run_pipeline.py`, потому что зависит от Hermes Agent runtime.

В текущей версии `minimax_api` может быть experimental/stub в зависимости от установленной сборки. Перед использованием обязательно проверяйте `doctor` и backend healthcheck.

### Repair safety

`repair` без `--backend` берёт backend из manifest.json (chunk-level `wave2_backend` или project-level `translation.wave2_backend`). Если backend неизвестен, команда откажется работать, чтобы не перезаписать реальный перевод mock-результатом. Для тестов можно явно указать `repair <slug> --backend mock`.

---

## Current status

- Pipeline функционален с mock backend
- Real backend зависит от доступности delegate_task в Hermes
- PDF export optional — WARN если pandoc/xelatex отсутствуют

---

## Legacy note

Старые проекты в формате `workspace/<project_slug>/` — **legacy**. Новые проекты всегда создаются в `~/translations/<project_slug>/`. Миграция старых проектов не требуется.

---

## Поддерживаемые форматы

- `.txt`, `.md`, `.markdown`
- `.docx`
- `.html`, `.htm`
- text-based `.pdf` (best-effort)

**Не поддерживается:** EPUB, OCR/scanned PDF, batch directories, watch-folders.

---

## Uninstall

```bash
rm -rf ~/hermes-translator
rm -rf ~/.hermes/skills/universal-ru-document-translator
```

---

## License

MIT License.