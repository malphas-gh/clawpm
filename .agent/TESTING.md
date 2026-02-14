# ClawPM Agent Testing Protocol

You are testing ClawPM by using it for real work. This creates a feedback loop where real usage surfaces issues and drives improvements.

## Current State

- **CLI**: `clawpm` installed via `uv tool install` at `~/.local/bin/clawpm`
- **Portfolio**: `~/clawpm` (default, override via `CLAWPM_PORTFOLIO` env var)
- **Skill**: `~/.openclaw/skills/clawpm` (symlink)
- **Hook**: Disabled - use explicit `clawpm log add` instead

## Quick Test

```bash
# Should return JSON with status ok
clawpm setup --check

# Should list projects
clawpm projects list

# Should show next task
clawpm projects next
```

## Your Goals

1. Use clawpm commands as documented in the skill
2. Log any issues to `.agent/issues.jsonl`
3. Fix issues when you can, document when you can't

## Testing Checklist

### Setup & Discovery

- [ ] `clawpm setup --check` returns status ok
- [ ] `clawpm projects list` shows projects
- [ ] `clawpm version` works

### Task Lifecycle

Create a test task and work through the lifecycle:

```bash
# 1. Find next task
clawpm projects next

# 2. Get context
clawpm project context <project_id>

# 3. Start work (mark in-progress)
clawpm tasks state --project <id> <task_id> progress

# 4. Log progress
clawpm log add --project <id> --task <task_id> --action start --summary "Starting work"

# 5. Do work... then log more
clawpm log add --project <id> --task <task_id> --action progress --summary "Made progress" --next "Next steps"

# 6. Complete
clawpm tasks state --project <id> <task_id> done --note "Done"
clawpm log add --project <id> --task <task_id> --action done --summary "Completed"
```

Verify:
- [ ] Task file moves from `tasks/ID.md` → `tasks/ID.progress.md` → `tasks/done/ID.md`
- [ ] `work_log.jsonl` has entries
- [ ] `clawpm log tail` shows the entries

### Task Creation

```bash
clawpm tasks add --project <id> --title "Test task" --priority 2 --complexity m
```

- [ ] Creates `tasks/PROJ-NNN.md` file
- [ ] File has correct frontmatter

### Research

```bash
# Create
clawpm research add --project <id> --type investigation --title "Test research" --tags foo,bar

# List
clawpm research list --project <id>
```

- [ ] Creates research file
- [ ] Tags are split correctly (not "foo,bar" as single tag)

### Error Handling

Test these error cases:
- [ ] `clawpm tasks list --project nonexistent` - helpful error?
- [ ] `clawpm tasks state --project <id> BADID done` - helpful error?
- [ ] Running without portfolio - helpful error?

### Output Formats

- [ ] Default JSON is valid and parseable
- [ ] `clawpm --format text projects list` is human-readable

## Logging Issues

Use the CLI to log issues:

```bash
clawpm issues add --project <id> \
  --type bug \
  --severity high \
  --command "clawpm tasks state ..." \
  --expected "Task should move" \
  --actual "Error occurred" \
  --context "Additional details"
```

List issues:
```bash
clawpm issues list --project <id>
clawpm issues list --project <id> --open  # unfixed only
```

**Types:** `bug`, `ux`, `docs`, `feature`
**Severity:** `high` (blocks work), `medium` (workaroundable), `low` (minor)

## Fixing Issues

1. Fix the code in `src/clawpm/`
2. Test with `uv run clawpm <command>` or reinstall with `uv tool install --force`
3. Update issue with `"fixed": true`
4. Note fix in commit or experiments.md

## Self-Management

ClawPM manages its own development. Use it:

```bash
# See clawpm's own tasks
clawpm tasks list --project clawpm

# Log your testing work
clawpm log add --project clawpm --action progress --summary "Testing task lifecycle"
```
