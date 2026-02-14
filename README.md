# ClawPM

Filesystem-first multi-project manager for AI agents.

## Installation

```bash
# Install globally with uv
uv tool install clawpm

# Or from git
uv tool install git+https://github.com/yourusername/clawpm.git

# Or for development
git clone https://github.com/yourusername/clawpm.git
cd clawpm
uv tool install -e .
```

## Quick Start

```bash
# Initialize portfolio structure (optional - clawpm uses sensible defaults)
mkdir -p ~/clawpm/projects
touch ~/clawpm/work_log.jsonl

# Initialize a project from any git repo
cd /path/to/your/repo
clawpm project init

# Or specify a repo
clawpm project init --in-repo /path/to/repo

# See what's next across all projects
clawpm next

# Add a task
clawpm add "Implement feature X"

# Start working
clawpm start 1

# Complete it
clawpm done 1
```

## Configuration

ClawPM works out of the box with these defaults:
- Portfolio root: `~/clawpm`
- Project roots: `~/clawpm/projects`
- OpenClaw workspace: `~/.openclaw/workspace` (auto-detected)

Override via environment variables:
- `CLAWPM_PORTFOLIO`: Portfolio root directory
- `CLAWPM_PROJECT_ROOTS`: Colon-separated list of additional project directories
- `CLAWPM_WORKSPACE`: OpenClaw workspace path

Or create `~/clawpm/portfolio.toml`:
```toml
portfolio_root = "~/clawpm"
project_roots = [
    "~/clawpm/projects",
    "~/Development"
]

[openclaw]
workspace = "~/.openclaw/workspace"
```

## OpenClaw Integration

Install the skill for OpenClaw agents:
```bash
# Copy skill to OpenClaw skills directory
cp -r skills/clawpm ~/.openclaw/skills/

# Or symlink for development
ln -s $(pwd)/skills/clawpm ~/.openclaw/skills/clawpm
```

## Features

- **Filesystem-first**: All state lives in markdown files and TOML configs
- **JSON output**: All commands emit JSON by default for agent consumption
- **Multi-project**: Manage tasks across multiple projects from one portfolio
- **Auto-detection**: Run commands from any project directory
- **Sensible defaults**: Works without configuration

## Documentation

See the skill documentation at `skills/clawpm/SKILL.md` for full command reference.
