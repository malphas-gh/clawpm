---
name: clawpm-sync
description: Auto-log work sessions to clawpm work_log.jsonl
metadata: { "openclaw": { "emoji": "📋", "events": ["command:new", "command:stop"], "requires": { "bins": ["clawpm"] } } }
---

# ClawPM Sync Hook

Automatically appends to the clawpm work log when OpenClaw session lifecycle events occur.

## Events

- `command:new` - Logs a `pause` entry when starting a new session (captures handoff from previous work)
- `command:stop` - Logs a `pause` entry when stopping the agent

## What It Does

1. On `command:new`:
   - Captures session metadata (session key, timestamp)
   - Appends a `pause` entry to work_log.jsonl
   - Future: Extract project/task context from conversation history

2. On `command:stop`:
   - Similar capture and logging
   - Marks work as paused

## Requirements

- `clawpm` CLI must be installed and on PATH
- Portfolio at `~/clawpm` with a `work_log.jsonl` file

## Log Entry Format

```json
{
  "ts": "2026-02-05T14:32:00Z",
  "project": "_unknown",
  "task": null,
  "action": "pause",
  "agent": "main",
  "session_key": "agent:main:main",
  "summary": "Session new via /new",
  "next": null,
  "blockers": null
}
```

## Future Enhancements

- Extract project/task from conversation context using LLM
- Parse last few messages to determine what was being worked on
- Link to specific task IDs when detectable
