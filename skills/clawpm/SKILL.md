---
name: clawpm
description: Multi-project task and research management (JSON-first CLI)
user-invocable: true
metadata: { "openclaw": { "requires": { "bins": ["clawpm"] }, "emoji": "📋" } }
---

# ClawPM Skill

Use `clawpm` for multi-project task management. All commands emit JSON by default.

## Quick Start

```bash
# If you're in a project directory, no --project needed:
cd ~/Development/my-project
clawpm status              # See project status
clawpm next                # Get next task
clawpm start 42            # Start task (short ID works)
clawpm done 42             # Mark done

# Or set a project context:
clawpm use my-project
clawpm status              # Now uses my-project
```

## Top-Level Commands (Shortcuts)

| Command | Equivalent | Description |
|---------|------------|-------------|
| `clawpm add "Title"` | `clawpm tasks add -t "Title"` | Quick add a task |
| `clawpm done 42` | `clawpm tasks state 42 done` | Mark task done |
| `clawpm start 42` | `clawpm tasks state 42 progress` | Start working |
| `clawpm block 42` | `clawpm tasks state 42 blocked` | Mark blocked |
| `clawpm next` | `clawpm projects next` | Get next task |
| `clawpm status` | - | Project overview |
| `clawpm use <id>` | - | Set project context |

## Project Auto-Detection

ClawPM automatically detects your project from (in priority order):
1. **Subcommand flag**: `clawpm tasks list --project clawpm`
2. **Global flag**: `clawpm --project clawpm status` (works from anywhere)
3. **Current directory**: Walks up looking for `.project/settings.toml`
4. **Context**: Previously set with `clawpm use <project>`

```bash
# From project directory - auto-detects:
cd ~/Development/clawpm
clawpm status              # Uses clawpm automatically
clawpm done 30             # Marks CLAWP-030 done

# From anywhere - use global flag:
clawpm -p clawpm status
clawpm --project clawpm done 30
```

## Short Task IDs

You can use just the numeric part of a task ID:
- `42` → `CLAWP-042` (prefix derived from project ID)
- `CLAWP-042` → `CLAWP-042` (full ID works too)

## Setting Up a New Project

### From an Existing Git Repo

```bash
cd /path/to/my-repo
clawpm project init                    # Auto-detects ID/name from directory
clawpm project init --id myproj        # Custom ID
clawpm project init --name "My Project" # Custom name
```

This creates `.project/` inside the repo with:
- `settings.toml` - Project config
- `SPEC.md` - Project specification template
- `tasks/` - Task storage
- `learnings.md` - Running notes
- `research/`, `notes/` - Research storage

The repo is immediately tracked by ClawPM - `clawpm status` works from that directory.

### From Outside the Repo

```bash
clawpm project init --in-repo /path/to/repo
# or
clawpm project init -r /path/to/repo
```

## Web Dashboard

```bash
clawpm serve               # Start on http://127.0.0.1:8080
clawpm serve --port 8888   # Custom port
```

Features:
- Real-time overview of blockers, active tasks, projects
- Respond to blockers directly
- Quick add tasks/issues
- Pause/resume projects

## Full Command Reference

### Projects
```bash
clawpm projects list                    # List all projects
clawpm projects next                    # Next task across all projects
clawpm project context [project]        # Full project context (spec, last work, blockers)
clawpm project init                     # Initialize project in current dir
```

### Tasks
```bash
clawpm tasks list [--state open|done|blocked|progress|all]
clawpm tasks show <id>                  # Task details
clawpm tasks add -t "Title" [--priority 3] [--complexity m]
clawpm tasks state <id> open|progress|done|blocked [--note "..."]
```

### Work Log
```bash
clawpm log add --task <id> --action progress --summary "What I did"
clawpm log tail [--limit 10]            # Recent entries
clawpm log last                         # Most recent entry
```

### Research
```bash
clawpm research list
clawpm research add --type investigation --title "Question"
clawpm research link --id <research_id> --session-key <key>
```

### Issues
```bash
clawpm issues add --type bug --severity high --actual "What happened"
clawpm issues list [--open]             # Open issues only
```

### Admin
```bash
clawpm status              # Project overview (or all projects if none selected)
clawpm doctor              # Health check
clawpm setup --check       # Verify installation
clawpm use [project]       # Set/show project context
clawpm use --clear         # Clear context
```

## Workflow Example

### Starting a Session
```bash
clawpm next                              # Find next task
clawpm start 42                          # Mark in progress
# Read the task file for full details
```

### During Work
```bash
clawpm log add --task 42 --action progress --summary "Implemented X"
```

### Completing Work
```bash
git add . && git commit -m "feat: ..."   # Commit changes
clawpm done 42 --note "Completed"        # Mark done
clawpm log add --task 42 --action done --summary "..."
```

### Hit a Blocker
```bash
clawpm block 42 --note "Need API credentials"
# Dashboard shows this; human can respond via web UI
```

## Research with Subagents

For background research:

1. Create research: `clawpm research add --type investigation --title "Question"`
2. Spawn subagent: Use `sessions_spawn` with the research task
3. Link session: `clawpm research link --id <id> --session-key <key>`
4. Check results: `sessions_history` or read the research file

## Task States & File Locations

| State | File Pattern | Meaning |
|-------|--------------|---------|
| open | `tasks/CLAWP-042.md` | Ready to work |
| progress | `tasks/CLAWP-042.progress.md` | In progress |
| done | `tasks/done/CLAWP-042.md` | Completed |
| blocked | `tasks/blocked/CLAWP-042.md` | Waiting |

## Work Log Actions

- `start` - Started working
- `progress` - Made progress
- `done` - Completed
- `blocked` - Hit a blocker
- `pause` - Switching tasks
- `research` - Research note
- `note` - General observation

## Tips

- **JSON output**: All commands emit JSON by default; use `-f text` for human-readable
- **Portfolio root**: Must be OUTSIDE OpenClaw workspace
- **Work log**: Append-only at `~/clawpm/work_log.jsonl`
- **Test changes**: When editing clawpm itself, test with `uv run clawpm ...` from the repo

## Troubleshooting

```bash
clawpm doctor              # Check for issues
clawpm setup --check       # Verify installation
clawpm log tail            # See recent activity
```
