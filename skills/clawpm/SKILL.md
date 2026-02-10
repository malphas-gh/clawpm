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

## Agent Context (Full Onboarding)

Get everything needed to resume work in one command:

```bash
clawpm context             # Full context for current project
clawpm context -p myproj   # Specific project
```

Returns JSON with:
- Project info + spec (truncated)
- In-progress tasks or next task
- Blockers needing attention
- Recent work log (last 5 entries)
- Git status (branch, uncommitted, recent commits)
- Open issues

## Top-Level Commands (Shortcuts)

| Command | Equivalent | Description |
|---------|------------|-------------|
| `clawpm add "Title"` | `clawpm tasks add -t "Title"` | Quick add a task |
| `clawpm add "Title" --parent 25` | - | Add subtask |
| `clawpm done 42` | `clawpm tasks state 42 done` | Mark task done |
| `clawpm start 42` | `clawpm tasks state 42 progress` | Start working |
| `clawpm block 42` | `clawpm tasks state 42 blocked` | Mark blocked |
| `clawpm next` | `clawpm projects next` | Get next task |
| `clawpm status` | - | Project overview |
| `clawpm context` | - | Full agent context |
| `clawpm use <id>` | - | Set project context |

## Project Auto-Detection

ClawPM automatically detects your project from (in priority order):
1. **Subcommand flag**: `clawpm tasks list --project clawpm`
2. **Global flag**: `clawpm --project clawpm status`
3. **Current directory**: Walks up looking for `.project/settings.toml`
4. **Auto-init**: If in untracked git repo under project_roots, auto-initializes
5. **Context**: Previously set with `clawpm use <project>`

```bash
# From project directory - auto-detects:
cd ~/Development/clawpm
clawpm status              # Uses clawpm automatically

# Auto-init from new git clone:
cd ~/Development/new-repo  # Untracked git repo
clawpm add "First task"    # Auto-initializes .project/, then adds task
```

## Short Task IDs

You can use just the numeric part of a task ID:
- `42` → `CLAWP-042` (prefix derived from project ID)
- `CLAWP-042` → `CLAWP-042` (full ID works too)

## Subtasks

Tasks can have subtasks via directory structure:

```bash
# Convert task to parent (for adding subtasks)
clawpm tasks split 25      # CLAWP-025.md → CLAWP-025/_task.md

# Add subtask directly (auto-splits parent if needed)
clawpm add "Subtask" --parent 25   # Creates CLAWP-025/CLAWP-025-001.md

# List shows hierarchy
clawpm -f text tasks list
# CLAWP-025 [open] P2 Parent task
#   └─ CLAWP-025-001 ↳ [done] P3 Subtask
#   └─ CLAWP-025-002 ↳ [progress] P3 Another subtask

# Parent completion blocked if subtasks incomplete
clawpm done 25             # Fails if subtasks not done
clawpm done 25 --force     # Override and complete anyway
```

Subtasks move with parent on state change (done/blocked moves entire directory).

## Setting Up a New Project

### Auto-Init from Git Repo

```bash
git clone git@github.com:user/repo.git ~/Development/repo
cd ~/Development/repo
clawpm add "First task"    # Auto-initializes project
```

### Manual Init

```bash
cd /path/to/my-repo
clawpm project init                    # Auto-detects ID/name from directory
clawpm project init --id myproj        # Custom ID
```

### Discover Untracked Repos

```bash
clawpm projects list --all   # Shows tracked + untracked git repos
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
clawpm projects list [--all]            # List projects (--all includes untracked repos)
clawpm projects next                    # Next task across all projects
clawpm project context [project]        # Full project context
clawpm project init                     # Initialize project in current dir
```

### Tasks
```bash
clawpm tasks list [-s open|done|blocked|progress|all] [--flat]
clawpm tasks show <id>                  # Task details
clawpm tasks add -t "Title" [--priority 3] [--complexity m] [--parent <id>]
clawpm tasks state <id> open|progress|done|blocked [--note "..."] [--force]
clawpm tasks split <id>                 # Convert to parent directory for subtasks
```

### Work Log
```bash
clawpm log add --task <id> --action progress --summary "What I did"
clawpm log tail [--limit 10]            # Recent entries
clawpm log tail --follow                # Live tail (like tail -f)
clawpm log last                         # Most recent entry
```

Note: State changes (start/done/block) auto-log to work_log with git files_changed.

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
clawpm status              # Project overview
clawpm context             # Full agent context (project, tasks, git, issues)
clawpm doctor              # Health check
clawpm setup --check       # Verify installation
clawpm use [project]       # Set/show project context
clawpm use --clear         # Clear context
```

## Workflow Example

### Starting a Session
```bash
clawpm context             # Get full context
clawpm start 42            # Mark in progress (auto-logs)
```

### During Work
```bash
# Work on the task...
# State changes auto-log with git files_changed
```

### Completing Work
```bash
git add . && git commit -m "feat: ..."
clawpm done 42 --note "Completed"       # Auto-logs with files_changed
```

### Hit a Blocker
```bash
clawpm block 42 --note "Need API credentials"
# Dashboard shows this; human can respond via web UI
```

## Task States & File Locations

| State | File Pattern | Meaning |
|-------|--------------|---------|
| open | `tasks/CLAWP-042.md` | Ready to work |
| progress | `tasks/CLAWP-042.progress.md` | In progress |
| done | `tasks/done/CLAWP-042.md` | Completed |
| blocked | `tasks/blocked/CLAWP-042.md` | Waiting |

### Subtask Directory Structure
```
tasks/
  CLAWP-024.md              # Regular task
  CLAWP-025/                # Parent task directory
    _task.md                # Parent task content
    CLAWP-025-001.md        # Subtask 1
    CLAWP-025-002.md        # Subtask 2
  done/
    CLAWP-023/              # Completed parent + subtasks
```

## Work Log Actions

- `start` - Started working (auto-logged on `clawpm start`)
- `progress` - Made progress
- `done` - Completed (auto-logged on `clawpm done`)
- `blocked` - Hit a blocker (auto-logged on `clawpm block`)
- `pause` - Switching tasks
- `research` - Research note
- `note` - General observation

Auto-logged entries include `"auto": true` and `files_changed` from git.

## Tips

- **JSON output**: All commands emit JSON by default; use `-f text` for human-readable
- **Portfolio root**: Must be OUTSIDE OpenClaw workspace
- **Work log**: Append-only at `~/clawpm/work_log.jsonl`
- **Live monitoring**: `clawpm log tail -f` for real-time log watching
- **Test changes**: When editing clawpm itself, test with `uv run clawpm ...` from the repo

## Troubleshooting

```bash
clawpm doctor              # Check for issues
clawpm setup --check       # Verify installation
clawpm log tail            # See recent activity
clawpm context             # Full project state
```
