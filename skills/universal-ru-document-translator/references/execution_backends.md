# Execution Backends

## v0.1 Supported

### hermes-current (default)
- Orchestrator uses current Hermes session for LLM calls
- Pros: simple, no additional setup
- Cons: limited to current context window

### delegate_task
- Spawn subagents for chunk translation
- Each subagent gets context: chunk content + glossary + style guide
- Pros: parallelization, larger total document
- Cons: coordination overhead, subagent context limits

## v0.2 Planned (NOT YET IMPLEMENTED)

### kanban
- Full Kanban board with task contracts
- Multiple workers, status tracking
- Resume/retry support

### hermes-cli
- Direct CLI invocation of Hermes for LLM calls
- Bypasses current context limits

### provider-api
- Direct API calls to translation provider
- Requires API key configuration
- Not using Hermes Agent as intermediary

## Backend Selection

```python
# In config.yaml or CLI arg:
backend: "hermes-current"  # default for v0.1
# backend: "delegate_task"
# backend: "kanban"         # NOT IMPLEMENTED
# backend: "hermes-cli"     # NOT IMPLEMENTED
# backend: "provider-api"   # NOT IMPLEMENTED
```

## Changing Backend

Backend is set in:
1. `~/hermes-translator/config.yaml` — default for all runs
2. CLI argument `--backend delegate_task` — per-run override

## Implementation Note

v0.1 Python scripts do NOT call LLM APIs directly. They prepare data and invoke backends through Hermes agent orchestration.