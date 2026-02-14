# ClawPM Handoff

**Date:** 2026-02-05
**Status:** CLI complete and tested on OpenClaw server

## Current State

ClawPM is installed and working:
- **CLI**: `~/.local/bin/clawpm` (installed via `uv tool install`)
- **Portfolio**: `~/clawpm/` (hardcoded default, no env var needed)
- **Source**: `~/Development/clawpm/`
- **Skill**: `~/.openclaw/skills/clawpm` → symlink
- **Hook**: `~/.openclaw/hooks/clawpm-sync` → symlink

## What Works

| Feature | Status |
|---------|--------|
| `clawpm projects list/next` | ✅ |
| `clawpm project context/init/doctor` | ✅ |
| `clawpm tasks list/show/add/state` | ✅ |
| `clawpm log add/tail/last` | ✅ |
| `clawpm research add/list/link` | ✅ |
| JSON + text output formats | ✅ |
| Hardcoded ~/clawpm default | ✅ |
| Skill symlinked | ✅ |
| Hook symlinked | ✅ |
| Hook integration test | ⏸️ Needs gateway |

## Key Files

```
~/Development/clawpm/
├── src/clawpm/
│   ├── cli.py          # Main CLI (~550 lines)
│   ├── models.py       # Data models
│   ├── discovery.py    # Project discovery (hardcodes ~/clawpm)
│   ├── tasks.py        # Task operations
│   ├── worklog.py      # Work log operations
│   ├── research.py     # Research operations
│   └── output.py       # JSON/text formatting
├── skills/clawpm/SKILL.md
├── hooks/clawpm-sync/
│   ├── HOOK.md
│   └── handler.ts
├── .project/           # ClawPM manages itself
└── .agent/TESTING.md   # Testing protocol
```

## Portfolio Layout

```
~/clawpm/
├── portfolio.toml      # Points to ~/clawpm/projects + ~/Development
├── work_log.jsonl      # Unified work log
└── projects/           # Can add standalone projects here
```

## Usage

```bash
# No env var needed - defaults to ~/clawpm
clawpm projects next
clawpm project context clawpm
clawpm tasks list --project clawpm
clawpm --format text tasks list --project clawpm  # Human readable
```

## Remaining Work

1. **Hook testing** - Enable with `openclaw hooks enable clawpm-sync`, test with `/new`
2. **Agent testing** - Use `.agent/TESTING.md` protocol for thorough testing
3. **Bug fixes** - Log to `.agent/issues.jsonl`

## Recent Changes

- Moved source to `~/Development/clawpm`
- Moved portfolio to `~/clawpm`
- Hardcoded `~/clawpm` as default (no CLAWPM_PORTFOLIO env needed)
- Fixed comma-separated tags bug in `research add`
- Fixed skill/hook symlinks to new location
