# ClawPM SPEC (Filesystem-First Multi-Project Manager)

**Purpose**
ClawPM is a minimal, filesystem-first portfolio manager for many projects. It keeps the Ralph loop feel, but scales across projects with a JSON-first CLI that integrates with OpenClaw via skills and hooks. Python is used for reliability and JSON output. The filesystem remains the source of truth.

**Goals**
- Preserve Ralph-loop low friction for tasks and handoffs.
- Support many projects with a consistent `.project/` layout.
- Emit JSON by default for agents and future UI integration.
- Keep dependencies minimal and installation simple (`uv` friendly).
- Avoid storing source-of-truth state in a database.
- Integrate cleanly with OpenClaw (skills, hooks, session tools).

**Non-Goals**
- No long-running service required for core use.
- No monolithic project registry database.
- No automatic prompt injection of large project context.
- No complex subtask graph scheduler.
- No MCP protocol (CLI tools with JSON output are sufficient).

**Core Principles**
- Filesystem is canonical; any index is rebuildable.
- Same commands and data model across all projects.
- Everything is human-readable and editable.
- OpenClaw hooks handle session lifecycle; CLI handles task/project state.

**Key Constraint: OpenClaw Workspace Recursion**
We previously saw OpenClaw recursively import projects placed inside the workspace repo, causing unintended imports. Therefore the portfolio root must live **outside** the OpenClaw workspace. The CLI should support scan roots so the portfolio can live anywhere.

---

## Repo Layout

```
clawpm/
  SPEC.md
  pyproject.toml               # CLI packaging (uv tool install)
  setup.sh                     # Install script (symlinks skills/hooks)

  src/
    clawpm/
      __init__.py
      cli.py                   # Main CLI entry
      discovery.py             # Project/portfolio discovery
      tasks.py                 # Task operations
      research.py              # Research operations
      worklog.py               # Work log operations
      models.py                # Data models
      output.py                # JSON/text formatting

  skills/
    clawpm/
      SKILL.md                 # OpenClaw skill: how to use clawpm

  hooks/
    clawpm-sync/
      HOOK.md                  # Hook metadata
      handler.ts               # Hook implementation

  examples/
    portfolio/                 # Example portfolio tree

  tests/
    test_cli.py
    test_discovery.py
    test_tasks.py

  .agent/
    TESTING.md                 # Agent testing protocol
    issues.jsonl               # Agent-discovered issues
    experiments.md             # Agent experiment log
```

---

## Portfolio Layout

```
~/clawpm-portfolio/
  portfolio.toml               # Global config
  work_log.jsonl               # Unified work log (all projects)

  projects/
    alpha/
      .project/
        settings.toml          # Project config
        SPEC.md                # Project specification
        PROMPT.md              # Agent instructions (optional)
        learnings.md           # Accumulated learnings
        STOP                   # Stop signal file (when present)
        tasks/
          ALPHA-001.md
          ALPHA-002.progress.md
          done/
            ALPHA-000.md
          blocked/
            ALPHA-003.md
        research/
          2026-02-05_memory-leak.md
        notes/
          journal.md

    beta/
      .project/
        settings.toml
        tasks/
        research/

    _inbox/                    # Pseudo-project for misc research
      .project/
        settings.toml
        research/
```

---

## Work Log (replaces HANDOFF.md)

Instead of per-project HANDOFF.md files, use a single `work_log.jsonl` at the portfolio root. Each line is a JSON object representing a work session.

**Location:** `~/clawpm-portfolio/work_log.jsonl`

**Entry format:**
```json
{
  "ts": "2026-02-05T14:32:00Z",
  "project": "alpha",
  "task": "ALPHA-002",
  "action": "progress",
  "agent": "main",
  "session_key": "agent:main:main",
  "summary": "Implemented CLI skeleton, added project discovery",
  "next": "Add task state transitions",
  "files_changed": ["src/clawpm/cli.py", "src/clawpm/discovery.py"],
  "blockers": null
}
```

**Entry types (action field):**
- `start` - Started working on a task
- `progress` - Made progress, continuing
- `done` - Completed task
- `blocked` - Hit a blocker
- `pause` - Paused work (switching projects/tasks)
- `research` - Research/investigation note
- `note` - General observation

**CLI commands:**
```bash
# Append entry
clawpm log add --project alpha --task ALPHA-002 --action progress \
  --summary "..." --next "..."

# View recent entries
clawpm log tail [--project alpha] [--limit 20]

# View last entry for project
clawpm log last --project alpha

# Stream for UI (follow mode)
clawpm log stream
```

**Benefits over HANDOFF.md:**
- Single file, easy to tail/stream for UI
- Structured JSON, easy for agents to parse
- Full history preserved (not overwritten)
- Cross-project timeline view
- Hook can auto-append on session events

---

## Project Discovery

- A project is any folder under configured roots that contains `.project/settings.toml`.
- Scan roots live in `portfolio.toml` or an explicit `--root` flag.
- Default roots must not include the OpenClaw workspace directory.

**Config: portfolio.toml**
```toml
portfolio_root = "/home/user/clawpm-portfolio"

project_roots = [
  "/home/user/clawpm-portfolio/projects",
  "/home/user/Development"
]

[defaults]
status = "active"

[openclaw]
workspace = "~/.openclaw/workspace"  # For validation (don't scan here)
```

**Project Settings: .project/settings.toml**
```toml
id = "alpha"
name = "Alpha"
status = "active"            # active | paused | archived
priority = 3                 # used when picking across projects
repo_path = "/home/user/Development/alpha"  # optional
labels = ["openclaw", "infra"]
```

---

## Task Format

**State via filename:**
- Open: `tasks/ID.md`
- In-progress: `tasks/ID.progress.md`
- Done: `tasks/done/ID.md`
- Blocked: `tasks/blocked/ID.md`

**Frontmatter (minimal and queryable):**
```yaml
---
id: ALPHA-001
priority: 2
complexity: m          # s | m | l | xl
depends: [ALPHA-000]
parent: ALPHA-000      # optional, for subtasks
created: 2026-02-05
---
# Task title

Brief description of what needs to be done.

## Acceptance Criteria

- [ ] Specific, verifiable criterion
- [ ] Another criterion

## Notes

Any additional context.
```

---

## Research Format

Location: `.project/research/`

**For standalone research:**
```yaml
---
id: alpha-research-001
type: investigation       # investigation | spike | decision | reference
status: open              # open | complete | stale
tags: [performance, urgent]
created: 2026-02-05
---
# Memory Leak Investigation

## Question
What's causing the memory growth in the worker process?

## Summary
(Filled in as research progresses)

## Findings
...

## Conclusion
...
```

**For OpenClaw subagent research:**

When spawning research via `sessions_spawn`, store the session reference:

```yaml
---
id: alpha-research-002
type: investigation
status: in-progress
tags: [api, design]
created: 2026-02-05
openclaw:
  spawned_by: "agent:main:main"
  child_session_key: "agent:main:subagent:abc123-def456"
  run_id: "run_xyz789"
  spawned_at: "2026-02-05T14:32:00Z"
---
# API Design Research

## Task Given to Subagent
Research REST vs GraphQL tradeoffs for our use case...

## Result
(Populated from subagent announce or sessions_history)
```

**CLI commands:**
```bash
clawpm research add --project alpha --type investigation \
  --title "Memory Leak" --tags performance,urgent

clawpm research list --project alpha [--status open] [--tags ...]

# Link to OpenClaw subagent session
clawpm research link --project alpha --id alpha-research-002 \
  --session-key "agent:main:subagent:abc123"
```

---

## CLI Reference (JSON-first)

All commands output JSON by default. Use `--format text` for human-readable output.

### Projects
```bash
clawpm projects list [--filter active|paused|archived]
clawpm projects next                    # Pick next task across all active projects
clawpm project context <id>             # SPEC + last work log + next task + blockers
clawpm project init [--in-repo .]       # Create .project in current dir
clawpm project doctor [--project <id>]  # Detect issues (broken paths, missing files)
```

### Tasks
```bash
clawpm tasks list --project <id> [--state open|progress|done|blocked|all]
clawpm tasks show --project <id> <task_id>
clawpm tasks state --project <id> <task_id> progress|done|blocked [--note "..."]
clawpm tasks add --project <id> --title "..." [--priority N] [--complexity s|m|l]
```

### Research
```bash
clawpm research add --project <id> --type ... --title ... [--tags a,b]
clawpm research list --project <id> [--status open] [--tags ...]
clawpm research link --project <id> --id <research_id> --session-key <key>
```

### Work Log
```bash
clawpm log add --project <id> [--task <task_id>] --action <type> --summary "..."
clawpm log tail [--project <id>] [--limit N]
clawpm log last [--project <id>]
clawpm log stream                       # Follow mode for UI
```

### Setup & Diagnostics
```bash
clawpm setup                            # Interactive setup
clawpm setup --check                    # Verify installation
clawpm doctor                           # Full health check
clawpm version
```

**Output Contract:**
- JSON is the default output.
- `--format text` enables pretty output for humans.
- Errors return non-zero exit codes with structured JSON error payloads:
  ```json
  {"error": "project_not_found", "message": "No project with id 'foo'", "details": {...}}
  ```

---

## OpenClaw Integration

### Skill

The skill teaches OpenClaw agents how to use clawpm effectively.

**Location:** `~/.openclaw/skills/clawpm/SKILL.md` (symlinked from repo)

**SKILL.md:**
```markdown
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

## Starting Work

1. Find next task: `clawpm projects next`
2. Get context: `clawpm project context <project_id>`
3. Mark in-progress: `clawpm tasks state --project <id> <task_id> progress`
4. Read the task file for details

## During Work

Log progress periodically:
```bash
clawpm log add --project <id> --task <task_id> --action progress \
  --summary "What you did" --next "What's next"
```

## Completing Work

1. Verify acceptance criteria
2. Mark done: `clawpm tasks state --project <id> <task_id> done --note "..."`
3. Log completion: `clawpm log add --project <id> --task <task_id> --action done --summary "..."`

## Research with Subagents

For background research:
1. Create research file: `clawpm research add --project <id> --type investigation --title "..."`
2. Spawn subagent: `sessions_spawn` with the research question
3. Link session: `clawpm research link --project <id> --id <research_id> --session-key <child_key>`
4. Later: check results via `sessions_history` or read the research file

## Troubleshooting

- `clawpm doctor` - Check for issues
- `clawpm log tail --project <id>` - See recent work
- Portfolio root must be OUTSIDE OpenClaw workspace
```

### Hook: clawpm-sync

Auto-log work sessions when OpenClaw session lifecycle events occur.

**Location:** `~/.openclaw/hooks/clawpm-sync/`

**HOOK.md:**
```markdown
---
name: clawpm-sync
description: Auto-log work sessions to clawpm work_log.jsonl
metadata: { "openclaw": { "emoji": "📋", "events": ["command:new", "command:stop"], "requires": { "bins": ["clawpm"] } } }
---

# ClawPM Sync Hook

Automatically appends to the clawpm work log when:
- `/new` is issued (logs pause/handoff for current work)
- `/stop` is issued (logs pause)

## What It Does

1. On `command:new`:
   - Reads last 15 messages from ending session
   - Uses LLM to extract: project, task, summary, next steps
   - Appends `pause` entry to work_log.jsonl

2. On `command:stop`:
   - Similar extraction
   - Appends `pause` entry

## Configuration

In `~/.openclaw/openclaw.json`:
```json
{
  "hooks": {
    "internal": {
      "entries": {
        "clawpm-sync": {
          "enabled": true,
          "env": {
            "CLAWPM_PORTFOLIO": "/home/user/clawpm-portfolio"
          }
        }
      }
    }
  }
}
```
```

**handler.ts:**
```typescript
import type { HookHandler } from "openclaw/hooks";
import { execSync } from "child_process";

const handler: HookHandler = async (event) => {
  if (event.type !== "command") return;
  if (event.action !== "new" && event.action !== "stop") return;

  const portfolioRoot = process.env.CLAWPM_PORTFOLIO;
  if (!portfolioRoot) {
    console.error("[clawpm-sync] CLAWPM_PORTFOLIO not set");
    return;
  }

  try {
    // Extract context from session (simplified - real impl would use LLM)
    const sessionKey = event.sessionKey;
    const timestamp = event.timestamp.toISOString();

    // For now, log a basic pause entry
    // Full implementation would extract project/task from conversation
    const entry = JSON.stringify({
      ts: timestamp,
      project: "_unknown",
      task: null,
      action: "pause",
      agent: sessionKey.split(":")[1] || "main",
      session_key: sessionKey,
      summary: `Session ${event.action} via /${event.action}`,
      next: null,
      blockers: null
    });

    execSync(`echo '${entry}' >> "${portfolioRoot}/work_log.jsonl"`);
    console.log(`[clawpm-sync] Logged ${event.action} event`);
  } catch (err) {
    console.error("[clawpm-sync] Failed:", err);
  }
};

export default handler;
```

---

## Installation

### Quick Install (setup.sh)

```bash
# From clawpm repo root
./setup.sh
```

**setup.sh:**
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_DIR="${OPENCLAW_DIR:-$HOME/.openclaw}"

echo "ClawPM Setup"
echo "============"
echo ""

# 1. Check/install clawpm CLI
if ! command -v clawpm &> /dev/null; then
    echo "Installing clawpm CLI..."
    if command -v uv &> /dev/null; then
        uv tool install "$SCRIPT_DIR"
    else
        echo "Error: uv not found. Install uv first: https://docs.astral.sh/uv/"
        exit 1
    fi
else
    echo "✓ clawpm CLI already installed"
fi

# 2. Symlink skill
SKILL_SRC="$SCRIPT_DIR/skills/clawpm"
SKILL_DST="$OPENCLAW_DIR/skills/clawpm"

mkdir -p "$OPENCLAW_DIR/skills"
if [ -L "$SKILL_DST" ] || [ -d "$SKILL_DST" ]; then
    echo "✓ Skill already exists at $SKILL_DST"
else
    ln -s "$SKILL_SRC" "$SKILL_DST"
    echo "✓ Symlinked skill to $SKILL_DST"
fi

# 3. Symlink hook
HOOK_SRC="$SCRIPT_DIR/hooks/clawpm-sync"
HOOK_DST="$OPENCLAW_DIR/hooks/clawpm-sync"

mkdir -p "$OPENCLAW_DIR/hooks"
if [ -L "$HOOK_DST" ] || [ -d "$HOOK_DST" ]; then
    echo "✓ Hook already exists at $HOOK_DST"
else
    ln -s "$HOOK_SRC" "$HOOK_DST"
    echo "✓ Symlinked hook to $HOOK_DST"
fi

# 4. Initialize portfolio (interactive)
echo ""
read -p "Initialize a new portfolio? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DEFAULT_PORTFOLIO="$HOME/clawpm-portfolio"
    read -p "Portfolio path [$DEFAULT_PORTFOLIO]: " PORTFOLIO_PATH
    PORTFOLIO_PATH="${PORTFOLIO_PATH:-$DEFAULT_PORTFOLIO}"

    mkdir -p "$PORTFOLIO_PATH/projects"

    if [ ! -f "$PORTFOLIO_PATH/portfolio.toml" ]; then
        cat > "$PORTFOLIO_PATH/portfolio.toml" << EOF
portfolio_root = "$PORTFOLIO_PATH"

project_roots = [
    "$PORTFOLIO_PATH/projects"
]

[defaults]
status = "active"

[openclaw]
workspace = "$OPENCLAW_DIR/workspace"
EOF
        echo "✓ Created portfolio.toml"
    fi

    touch "$PORTFOLIO_PATH/work_log.jsonl"
    echo "✓ Portfolio initialized at $PORTFOLIO_PATH"

    echo ""
    echo "Add to your shell profile:"
    echo "  export CLAWPM_PORTFOLIO=\"$PORTFOLIO_PATH\""
fi

# 5. Verify
echo ""
echo "Verification"
echo "------------"
clawpm setup --check 2>/dev/null || echo "(clawpm setup --check not yet implemented)"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Enable the hook: openclaw hooks enable clawpm-sync"
echo "  2. Create a project: clawpm project init --in-repo /path/to/repo"
echo "  3. Start working: clawpm projects next"
```

### Manual Install

```bash
# 1. Install CLI
uv tool install /path/to/clawpm
# or
uv tool install git+https://github.com/youruser/clawpm

# 2. Symlink skill
ln -s /path/to/clawpm/skills/clawpm ~/.openclaw/skills/clawpm

# 3. Symlink hook
ln -s /path/to/clawpm/hooks/clawpm-sync ~/.openclaw/hooks/clawpm-sync

# 4. Enable hook
openclaw hooks enable clawpm-sync

# 5. Set portfolio path
export CLAWPM_PORTFOLIO="$HOME/clawpm-portfolio"
```

---

## Agent-Driven Testing Protocol

ClawPM should be tested and improved by an agent using it. This creates a feedback loop where real usage surfaces issues.

### Testing Protocol

**Location:** `.agent/TESTING.md`

```markdown
# ClawPM Agent Testing Protocol

You are testing ClawPM by using it for real work. Your goal is to:
1. Use clawpm commands as documented
2. Log any issues, confusions, or failures to `.agent/issues.jsonl`
3. Note experiments and improvements in `.agent/experiments.md`
4. Suggest spec changes when patterns don't work

## Testing Workflow

1. **Bootstrap**: Run `clawpm setup --check` and note any issues
2. **Create Test Project**: `clawpm project init --in-repo .`
3. **Add Tasks**: Create 3-5 realistic tasks
4. **Work Loop**:
   - `clawpm projects next` to get next task
   - `clawpm project context <id>` to get context
   - Work on the task
   - `clawpm log add ...` to log progress
   - `clawpm tasks state ... done` when complete
5. **Research Flow**: Test `clawpm research add` and linking with sessions_spawn
6. **Edge Cases**: Test error handling, missing files, invalid states

## Issue Logging

When you hit a problem, append to `.agent/issues.jsonl`:
```json
{
  "ts": "2026-02-05T14:32:00Z",
  "type": "bug|ux|docs|feature",
  "command": "clawpm tasks state ...",
  "expected": "Task should move to done/",
  "actual": "Error: file not found",
  "context": "Task file had .progress.md suffix",
  "severity": "high|medium|low",
  "suggestion": "Handle .progress.md files in state transition"
}
```

## Experiment Log

Track experiments in `.agent/experiments.md`:
- What you tried
- What worked / didn't work
- Proposed changes

## Success Criteria

ClawPM is ready when:
- [ ] Full task lifecycle works (create → progress → done)
- [ ] Work log captures meaningful context
- [ ] Research + subagent flow works
- [ ] Error messages are helpful
- [ ] JSON output is parseable and complete
- [ ] Agent can use it without reading source code
```

### Issue Format

**Location:** `.agent/issues.jsonl`

```json
{"ts":"2026-02-05T10:00:00Z","type":"bug","command":"clawpm tasks state","expected":"...","actual":"...","severity":"high","suggestion":"..."}
{"ts":"2026-02-05T10:15:00Z","type":"ux","command":"clawpm log add","expected":"...","actual":"...","severity":"medium","suggestion":"..."}
```

### Experiment Log

**Location:** `.agent/experiments.md`

```markdown
# ClawPM Experiments

## 2026-02-05: Task State Transitions

**Tried:** Moving task from open to progress
**Command:** `clawpm tasks state --project alpha ALPHA-001 progress`
**Result:** Worked, but no confirmation message
**Suggestion:** Add `--verbose` flag or always show result summary

## 2026-02-05: Work Log Context Extraction

**Tried:** Hook extracting project from conversation
**Problem:** No reliable way to know which project agent was working on
**Idea:** Agent should explicitly set project context at start of session
**Proposed:** `clawpm context set --project alpha` that writes to a temp file
```

---

## Guardrails

- Never write inside the OpenClaw workspace repo by default.
- All paths are explicit and scan-root based.
- Keep all file formats hand-editable.
- Work log is append-only (no overwrites).
- Portfolio root validated against OpenClaw workspace on startup.

---

## Future Considerations

**Phase 2 (if needed):**
- `clawpm serve` - HTTP API for UI
- SQLite cache for large portfolios (rebuildable, not source of truth)
- Real-time work log streaming via websocket

**Not Planned:**
- MCP protocol support (JSON CLI is sufficient)
- Complex dependency graphs (keep it simple)
- Automatic context injection (agent reads files explicitly)
