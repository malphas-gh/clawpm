# ClawPM

Filesystem-first multi-project manager for AI agents.

## Installation

```bash
# Create wrapper script
cat > ~/.local/bin/clawpm << 'EOF'
#!/bin/bash
uv run --directory ~/Development/clawpm clawpm "$@"
EOF
chmod +x ~/.local/bin/clawpm
```

## Quick Start

```bash
# Create portfolio at ~/clawpm (default location)
mkdir -p ~/clawpm/projects
echo 'name = "My Portfolio"' > ~/clawpm/portfolio.toml
touch ~/clawpm/work_log.jsonl

# Create a project
clawpm project init --in-repo /path/to/repo

# See what's next
clawpm projects next

# List tasks
clawpm tasks list --project myproject

# Change task state
clawpm tasks state --project myproject TASK-001 progress

# Log work
clawpm log add --project myproject --task TASK-001 --action progress --summary "Did stuff"
```

## Features

- **Filesystem-first**: All state lives in markdown files and TOML configs
- **JSON output**: All commands emit JSON by default for agent consumption
- **Multi-project**: Manage tasks across multiple projects from one portfolio
- **OpenClaw integration**: Skills and hooks for seamless agent workflows

## Documentation

See [SPEC.md](./SPEC.md) for full documentation.
