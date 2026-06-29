# Memory (Agent Persistence)

Runtime data directory for agent memory, logs, and truth artifacts.

## Subdirectories (auto-created at runtime)

| Directory | Purpose |
|---|---|
| `chat_sessions/` | PM discussion rounds (`full_summary.json`, `full_memory.json`) |
| `test_failure/` | Test failure bans (`{task_id}.json` — fingerprint + ban instruction pairs) |
| `source_failure/` | Source failure bans (`{task_id}.json`) |
| `test_logs/` | Per-task test state snapshots (`{task_id}.json`) |
| `agent_logs/` | Full agent execution logs per task per attempt |
| `truths/engineer/` | Engineer output truths (exposed files/routes/tables per task) |
| `truths/test/` | Test output truths (verified interfaces per layer) |
| `snapshots/` | Redis fallback: source code snapshots for rollback |
| `logs/` | System logs (`agent_YYYYMMDD.log`) |

## Memory Format

Ban entries follow the fingerprint + ban instruction format:
```json
[
  {"f": "layer|actor|function|subtype", "b": "DON'T: ... | fix: ... | target_file"}
]
```

> This directory is populated at runtime. All contents are auto-managed.
