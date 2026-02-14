# ClawPM Development Guide

## Overview

ClawPM is a filesystem-first multi-project manager for AI agents. It provides a JSON-first CLI for managing tasks, work logs, and research across multiple projects.

## Quick Reference

```bash
# List projects
clawpm projects list

# Get next task across all projects
clawpm projects next

# Get project context (spec + last work + next task + blockers)
clawpm project context <project_id>

# Task operations
clawpm tasks list --project <id> [--state open|progress|done|blocked|all]
clawpm tasks state --project <id> <task_id> progress|done|blocked
clawpm tasks add --project <id> --title "..." --priority N --complexity s|m|l

# Work log
clawpm log add --project <id> --task <task_id> --action start|progress|done --summary "..."
clawpm log tail [--project <id>] [--limit N]

# Research
clawpm research add --project <id> --type investigation|spike|decision|reference --title "..."
clawpm research list --project <id>

# Human-readable output
clawpm --format text <command>
```

## Directory Structure

```
~/clawpm/                      # Portfolio (hardcoded default)
├── portfolio.toml
├── work_log.jsonl
└── projects/
    └── clawpm/                # Source code
        ├── src/clawpm/
        │   ├── cli.py                 # Click CLI commands
        │   ├── models.py              # Pydantic-style dataclasses
        │   ├── discovery.py           # Portfolio/project discovery
        │   ├── tasks.py               # Task CRUD + state transitions
        │   ├── worklog.py             # Work log operations
        │   ├── research.py            # Research operations
        │   └── output.py              # JSON/text formatting with rich
        ├── skills/clawpm/SKILL.md     # OpenClaw skill
        ├── hooks/clawpm-sync/         # OpenClaw hook
        ├── .project/                  # ClawPM manages itself
        └── .agent/                    # Agent testing protocol

```

OpenClaw installed via npm at `~/.npm-global/lib/node_modules/openclaw/`
Docs: `~/.npm-global/lib/node_modules/openclaw/docs/`

## Searching Documentation
```bash
# Search specific file types only
rg -t md 'pattern' .                    # Markdown files
rg -t py 'pattern' .                    # Python files
rg -t ts 'pattern' .                    # TypeScript files
rg -t js 'pattern' .                    # JavaScript files

# Search specific directory
rg 'pattern' openclaw/docs/
rg 'pattern' openclaw/src/

# Exclude directories
rg --glob '!node_modules' --glob '!vendor' 'pattern' .
rg -g '!*.min.js' 'pattern' .           # Exclude minified JS
```

## Development Workflow

### Running clawpm

Wrapper script at `~/.local/bin/clawpm`:
```bash
#!/bin/bash
uv run --directory ~/clawpm/projects/clawpm clawpm "$@"
```

This runs from source - no install needed, changes are picked up immediately.

### Making Changes

1. Edit source in `~/clawpm/projects/clawpm/src/clawpm/`
2. Test immediately with `uv run` - no reinstall needed
3. **Commit when done** - don't leave fixes uncommitted:
   ```bash
   git add <files>
   git commit -m "fix/feat: description"
   ```

### Testing Protocol

See `.agent/TESTING.md` for the full testing protocol. Key points:
- Log issues to `.agent/issues.jsonl`
- Track experiments in `.agent/experiments.md`
- Use clawpm to manage clawpm development tasks

### Task State Convention

- Open: `tasks/ID.md`
- In-progress: `tasks/ID.progress.md`
- Done: `tasks/done/ID.md`
- Blocked: `tasks/blocked/ID.md`

## Key Design Decisions

1. **Filesystem is source of truth** - No database, everything in markdown/TOML/JSONL
2. **JSON output by default** - All commands emit JSON for agent consumption
3. **Portfolio at ~/clawpm** - Hardcoded default, no env var needed
4. **work_log.jsonl** - Single append-only log for all projects (replaces per-project HANDOFF.md)
5. **Project discovery** - Scans `project_roots` for directories with `.project/settings.toml`

## OpenClaw Integration

### Skill
Located at `skills/clawpm/SKILL.md`, symlinked to `~/.openclaw/skills/clawpm`

### Hook (disabled)
Located at `hooks/clawpm-sync/`, installed to `~/.openclaw/hooks/clawpm-sync`
- **Currently disabled** - relying on agent following skill instructions to call `clawpm log add` instead
- **Setup**: Real directory with symlinked files (not a directory symlink - OpenClaw won't discover those)
  ```bash
  mkdir -p ~/.openclaw/hooks/clawpm-sync
  ln -s ~/clawpm/projects/clawpm/hooks/clawpm-sync/HOOK.md ~/.openclaw/hooks/clawpm-sync/HOOK.md
  ln -s ~/clawpm/projects/clawpm/hooks/clawpm-sync/handler.ts ~/.openclaw/hooks/clawpm-sync/handler.ts
  ```
- Triggers on `command:new` and `command:stop`
- Auto-logs session events to work_log.jsonl
- Enable with: `openclaw hooks enable clawpm-sync`

## Common Tasks

### Add a new CLI command
1. Add function in `src/clawpm/cli.py`
2. Use `@click.command()` and `@click.option()` decorators
3. Call `require_portfolio(ctx)` to get config
4. Use `output_json()` or `output_success()` for output

### Add a new model
1. Add dataclass in `src/clawpm/models.py`
2. Include `to_dict()` method for JSON serialization
3. Include `from_file()` classmethod if loading from markdown

### Debug issues
```bash
clawpm doctor                    # Check for config issues
clawpm --format text <command>   # Human-readable output
```
