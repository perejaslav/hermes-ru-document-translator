# Agent-Orchestrated Mode

Hermes-native translation pipeline — the only production-suitable mode for
Hermes Agent runtime.

## Architecture

┌──────────────────────────────────────────────────────┐
│  Hermes Agent (orchestration runtime)                │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  AgentOrchestratedTranslator                  │   │
│  │  ────────────────────────────                 │   │
│  │  • translate_project()                        │   │
│  │  • translate_wave()          ── delegate ──►  │   │
│  │  • translate_chunk()            task()        │   │
│  │  • repair_project()             (subagent)    │   │
│  └──────────┬───────────────────────────────────┘   │
│             │ reads/writes                           │
│             ▼                                        │
│  ┌──────────────────────────────────────────────┐   │
│  │  Pipeline (deterministic infrastructure)      │   │
│  │  ────────────────────────────                 │   │
│  │  state/ →  status tracking                    │   │
│  │  chunks/ → source, translated                 │   │
│  │  manifest.json → metadata                     │   │
│  │  qa/ → quality gates                          │   │
│  │  foundation/ → glossary, style, entities      │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘

## Execution Models

There are three distinct execution modes — understand the differences:

### 1. Agent-Orchestrated (PRODUCTION — this mode)

**How:** Hermes Agent instantiates ``AgentOrchestratedTranslator`` via
``execute_code()`` or embedded Hermes workflow, then calls
``translate_project()`` which invokes ``delegate_task()`` for each chunk.

**Where:** ONLY inside Hermes Agent runtime.

**Capabilities:**
- ``delegate_task`` — spawn subagent workers
- Full Hermes toolset (read_file, write_file, etc.)
- Sanitizer for output cleaning

### 2. Mock CLI Mode (DEVELOPMENT / TESTING)

**How:** ``hermes-translator translate <slug> --backend mock``

**Where:** Any terminal, any Python process.

**Capabilities:**
- Deterministic output for smoke tests
- No AI dependencies
- Verifies pipeline integrity (state, chunks, manifest)

### 3. Standalone CLI Infrastructure Mode

**How:** ``hermes-translator prepare/qa/merge/export/report <slug>``

**Where:** Any terminal, any Python process.

**Capabilities:**
- Prepare, QA, merge, export, report
- No translation — infrastructure only

### What Does NOT Work

``hermes-translator translate --backend hermes_delegate`` from a terminal
**will fail** with a healthcheck error. This is by design — ``delegate_task``
is not a Python-importable library function, it is a Hermes Agent runtime
capability.

## Why delegate_task Is Not a Python Library

``delegate_task`` is a tool provided by the Hermes Agent framework at the
**agent level**, not a function in ``hermes_tools`` that can be imported
from any Python script.

- ``terminal()`` subprocesses → ``hermes_tools`` unavailable → ImportError
- ``execute_code()`` sandbox → ``hermes_tools`` exists but limited subset
- **Agent tool call** → ``delegate_task`` available directly

This is not a bug — it is a fundamental architectural property of the
Hermes Agent system. Subagent delegation is a **runtime capability**, not
a library function.

## How to Use Agent-Orchestrated Mode

### Prerequisites

1. A prepared project (``hermes-translator prepare <file>``)
2. Running inside Hermes Agent

### Usage

```python
from translator.orchestration.agent_orchestrated import (
    AgentOrchestratedTranslator,
    require_delegate_task,
)

# Verify runtime (raises clear error if not in Hermes)
require_delegate_task()

# Create orchestrator
orchestrator = AgentOrchestratedTranslator("~/translations/<project_slug>")

# Run translation (waves 1 and 2)
result = orchestrator.translate_project()

# Or step by step:
result_w1 = orchestrator.translate_wave(1)
result_w2 = orchestrator.translate_wave(2)

# Repair chunks after QA
repair_result = orchestrator.repair_project()
```

After translation, switch back to CLI for deterministic steps:

```bash
hermes-translator qa <slug>
hermes-translator merge <slug>
hermes-translator export <slug>
hermes-translator report <slug>
```

### From Hermes Agent execute_code()

When running inside Hermes Agent, use ``execute_code()`` as the entrypoint:

```python
# Inside Hermes Agent — this code runs via execute_code()
from translator.orchestration.agent_orchestrated import AgentOrchestratedTranslator

orchestrator = AgentOrchestratedTranslator("~/translations/my_project")
orchestrator.translate_project()
print("Translation complete")
```

## Migration from hermes_delegate backend

The ``HermesDelegateBackend`` in ``translator/backends/hermes_delegate.py``
is preserved for reference but **deprecated for standalone CLI use**.

**Old (does not work from CLI):**
```
hermes-translator translate <slug> --backend hermes_delegate
```

**New (works from Hermes runtime):**
```python
orchestrator = AgentOrchestratedTranslator("<slug>")
orchestrator.translate_project()
```

## Verification Checklist

After running agent-orchestrated translation:

- [ ] ``chunks/translated/wave1/<chunk_id>.md`` exists
- [ ] ``chunks/translated/wave2/<chunk_id>.md`` exists
- [ ] Manifest shows ``"wave1_backend": "agent_orchestrated"``
- [ ] Manifest shows ``"wave2_backend": "agent_orchestrated"``
- [ ] ``hermes-translator qa <slug>`` passes all gates
- [ ] No ``<think>`` blocks in output
- [ ] No CJK contamination in output
