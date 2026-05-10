# QA Checklist

## QA Modes

QA работает в **dual mode**:
- **pre-merge** (до merge): проверяет `chunks/translated/*.md` — видит guardrail-маркеры, BLOCK_ID присутствуют
- **post-merge** (после merge, если `output/translated.md` существует): проверяет финальный файл

Post-merge результаты записываются в `qa_findings.json` поверх pre-merge.

## Deterministic QA Gates (always run)

### Post-merge checks (on `output/translated.md`)

| Check | What | Severity |
|-------|------|----------|
| `block_id_cleanup` | 0 BLOCK_ID markers in translated.md | CRITICAL if found |
| `guardrails` | 0 guardrail artifacts in final output | CRITICAL if found |
| `file_empty` | translated.md not empty | CRITICAL if empty |
| `language` | Cyrillic characters present | WARNING if <10 |
| `markdown_structure` | possibly unclosed code fences | WARNING if found |

### Pre-merge checks (on `chunks/translated/*.md`)

| Check | What | Severity |
|-------|------|----------|
| `file_exists` | translated chunk file exists | CRITICAL if missing |
| `block_completeness` | all BLOCK_IDs from source present | WARNING if missing |
| `language` | Cyrillic characters present | WARNING if <10 |
| `guardrails` | guardrail markers in chunk | WARNING if >0 |

## Error Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| `CRITICAL` | Translation incomplete or corrupted | Block merge, require retry |
| `WARNING` | Minor issues, translation usable | Log, proceed with caution |
| `INFO` | Informational, no action needed | Log only |

## QA Flow

```
1. prepare → workspace created
2. translate chunks → chunks/translated/*.md
3. qa (first) → pre-merge mode → qa_findings.json (may show guardrail warnings)
4. merge → output/translated.md + translated.debug.md (BLOCK_ID stripped from translated.md)
5. qa (second) → post-merge mode → qa_findings.json updated with final state
6. export
7. report
```

## How to read qa_findings.json

```json
{
  "findings": [...],
  "mode": "post-merge",
  "passed_checks": 5,
  "summary": { "critical": 0, "warnings": 1 }
}
```

`mode: post-merge` = QA проверяла финальный файл. Это единственный авторитетный результат.