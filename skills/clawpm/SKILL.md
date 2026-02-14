---
name: clawpm
description: Multi-project task and research management (JSON-first CLI)
user-invocable: true
metadata: { "openclaw": { "requires": { "bins": ["clawpm"] }, "emoji": "📋" } }
---

# ClawPM Skill

Use `clawpm` for multi-project task management. All commands emit JSON by default.

## When to Use ClawPM vs OpenClaw Session Tools

| Task | Tool |
|------|------|
| Query tasks across projects | `clawpm projects next`, `clawpm tasks list` |
| Change task state | `clawpm tasks state` |
| Log work progress | `clawpm log add` |
| Get project context | `clawpm project context` |
| Spawn background research | `sessions_spawn` (then `clawpm research link`) |
| Review past conversations | `sessions_history` |

## Quick Reference

```bash
# See what's next
clawpm projects next

# Get full context for a project
clawpm project context <project_id>

# List tasks
clawpm tasks list --project <id> --state open

# Change task state
clawpm tasks state --project <id> <task_id> progress|done|blocked

# Log work
clawpm log add --project <id> --task <task_id> --action progress --summary "..."

# See recent work
clawpm log tail --project <id> --limit 10
```

## Starting Work

1. Find next task: `clawpm projects next`
2. Get context: `clawpm project context <project_id>`
3. Mark in-progress: `clawpm tasks state --project <id> <task_id> progress`
4. Read the task file for full details

## During Work

Log progress periodically:
```bash
clawpm log add --project <id> --task <task_id> --action progress \
  --summary "What you did" --next "What's next"
```

## Completing Work

1. Verify acceptance criteria are met
2. Mark done: `clawpm tasks state --project <id> <task_id> done --note "..."`
3. Log completion: `clawpm log add --project <id> --task <task_id> --action done --summary "..."`

## Research with Subagents

For background research that shouldn't block main work:

1. Create research file:
   ```bash
   clawpm research add --project <id> --type investigation --title "Research question"
   ```

2. Spawn subagent via OpenClaw:
   ```
   sessions_spawn with task: "Research question..."
   ```

3. Link the session to research:
   ```bash
   clawpm research link --project <id> --id <research_id> --session-key <child_session_key>
   ```

4. Later, check results via `sessions_history` or read the research file

## Task States

- **open** - `tasks/ID.md` - Ready to work on
- **progress** - `tasks/ID.progress.md` - Currently being worked on
- **done** - `tasks/done/ID.md` - Completed
- **blocked** - `tasks/blocked/ID.md` - Waiting on something

## Work Log Actions

- `start` - Started working on a task
- `progress` - Made progress, continuing
- `done` - Completed task
- `blocked` - Hit a blocker
- `pause` - Paused work (switching tasks/projects)
- `research` - Research note
- `note` - General observation

## Troubleshooting

- `clawpm doctor` - Check for issues
- `clawpm log tail --project <id>` - See recent work history
- `clawpm setup --check` - Verify installation

## Important Notes

- Portfolio root must be OUTSIDE OpenClaw workspace (avoids recursion issues)
- All output is JSON by default; use `--format text` for human-readable
- Work log is append-only at `~/clawpm/work_log.jsonl`
