# Spec vs Implementation Comparison Pattern

## Когда использовать

Пользователь даёт файл спецификации (TZ, README, SKILL.md, план) и просит:
- "сравни", "сверь", "проверь что установлено"
- "пока не устанавливай", "только сверка"
- "есть ли уже", "что уже есть"

Ничего не устанавливать. Только чтение + сравнение + отчёт.

## Шаблон

```
1. Прочитать файл спецификации
2. Определить что именно проверять:
   - CLI tools → which / which -a
   - Python packages → pip list / uv pip list
   - System packages → apt list --installed
   - Skill files → ~/.hermes/skills/<name>/
   - Конфиги → ~/.config/ или проектные
3. Проверить каждую позицию
4. Сравнить: что уже есть vs чего нет vs что отличается
5. Доложить компактно: matched / missing / version mismatch
```

## Пример проверки CLI tools

```bash
which pandoc tesseract python3 2>/dev/null
pip3 list 2>/dev/null | grep -iE "pattern1|pattern2"
apt list --installed 2>/dev/null | grep -iE "pkg1|pkg2"
```

## Пример проверки skills

```bash
ls ~/.hermes/skills/
cat ~/.hermes/skills/<name>/SKILL.md | head -50
```

## Output format

Таблица или компактный список:
```
✓ pandoc 3.x — есть
✗ tesseract  — нет (нужен для OCR PDF)
⚠ python-docx — старая версия (ожидалась 1.1+, найдена 0.8)
✓ skill universal-ru-document-translator — есть (v0.1)
```

Никаких рекомендаций по установке пока пользователь не попросит.

## Контекст из сессий

- 2026-05-10: User дал TZ для universal-ru-document-translator. Проверены: pandoc, tesseract, python3, pip packages. Оказалось — translator уже установлен в ~/hermes-translator/ (создан в предыдущих сессиях). TZ оказался финальным требованием к v0.1 который уже реализован.