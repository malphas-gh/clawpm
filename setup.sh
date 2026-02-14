#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_DIR="${OPENCLAW_DIR:-$HOME/.openclaw}"
DEFAULT_PORTFOLIO="$HOME/clawpm"

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
    echo "✓ clawpm CLI already installed ($(which clawpm))"
fi

# 2. Symlink skill
SKILL_SRC="$SCRIPT_DIR/skills/clawpm"
SKILL_DST="$OPENCLAW_DIR/skills/clawpm"

mkdir -p "$OPENCLAW_DIR/skills"
if [ -L "$SKILL_DST" ]; then
    echo "✓ Skill symlink already exists at $SKILL_DST"
elif [ -d "$SKILL_DST" ]; then
    echo "⚠ Skill directory exists (not a symlink) at $SKILL_DST"
else
    ln -s "$SKILL_SRC" "$SKILL_DST"
    echo "✓ Symlinked skill to $SKILL_DST"
fi

# 3. Setup hook (real directory with symlinked files)
HOOK_SRC="$SCRIPT_DIR/hooks/clawpm-sync"
HOOK_DST="$OPENCLAW_DIR/hooks/clawpm-sync"

mkdir -p "$OPENCLAW_DIR/hooks"
if [ -d "$HOOK_DST" ] && [ ! -L "$HOOK_DST" ]; then
    # Real directory exists, check if files are symlinked
    if [ -L "$HOOK_DST/HOOK.md" ] && [ -L "$HOOK_DST/handler.ts" ]; then
        echo "✓ Hook already setup at $HOOK_DST"
    else
        echo "⚠ Hook directory exists but files aren't symlinked at $HOOK_DST"
    fi
elif [ -L "$HOOK_DST" ]; then
    # Directory symlink - convert to real dir with symlinked files
    echo "Converting hook from directory symlink to real dir with symlinked files..."
    rm "$HOOK_DST"
    mkdir -p "$HOOK_DST"
    ln -s "$HOOK_SRC/HOOK.md" "$HOOK_DST/HOOK.md"
    ln -s "$HOOK_SRC/handler.ts" "$HOOK_DST/handler.ts"
    echo "✓ Converted hook setup at $HOOK_DST"
else
    mkdir -p "$HOOK_DST"
    ln -s "$HOOK_SRC/HOOK.md" "$HOOK_DST/HOOK.md"
    ln -s "$HOOK_SRC/handler.ts" "$HOOK_DST/handler.ts"
    echo "✓ Setup hook at $HOOK_DST"
fi

# 4. Initialize portfolio (interactive)
echo ""
if [ -d "$DEFAULT_PORTFOLIO" ] && [ -f "$DEFAULT_PORTFOLIO/portfolio.toml" ]; then
    echo "✓ Portfolio already exists at $DEFAULT_PORTFOLIO"
else
    read -p "Initialize portfolio at $DEFAULT_PORTFOLIO? [Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        mkdir -p "$DEFAULT_PORTFOLIO/projects"
        mkdir -p "$DEFAULT_PORTFOLIO/projects/_inbox/.project/research"

        # Create portfolio.toml if it doesn't exist
        if [ ! -f "$DEFAULT_PORTFOLIO/portfolio.toml" ]; then
            cat > "$DEFAULT_PORTFOLIO/portfolio.toml" << EOF
portfolio_root = "$DEFAULT_PORTFOLIO"

project_roots = [
    "$DEFAULT_PORTFOLIO/projects"
]

[defaults]
status = "active"

[openclaw]
workspace = "$OPENCLAW_DIR/workspace"
EOF
            echo "✓ Created portfolio.toml"
        fi

        # Create _inbox project settings
        if [ ! -f "$DEFAULT_PORTFOLIO/projects/_inbox/.project/settings.toml" ]; then
            cat > "$DEFAULT_PORTFOLIO/projects/_inbox/.project/settings.toml" << EOF
id = "_inbox"
name = "Inbox"
status = "active"
priority = 99
labels = ["misc", "inbox"]
EOF
            echo "✓ Created _inbox project"
        fi

        # Create work_log.jsonl if it doesn't exist
        touch "$DEFAULT_PORTFOLIO/work_log.jsonl"
        echo "✓ Portfolio initialized at $DEFAULT_PORTFOLIO"
    fi
fi

# 5. Verify installation
echo ""
echo "Verification"
echo "------------"

# Check clawpm
if command -v clawpm &> /dev/null; then
    echo "✓ clawpm CLI: $(clawpm version 2>/dev/null || echo 'installed')"
else
    echo "✗ clawpm CLI not found"
fi

# Check skill
if [ -L "$SKILL_DST" ] || [ -d "$SKILL_DST" ]; then
    echo "✓ Skill installed at $SKILL_DST"
else
    echo "✗ Skill not found"
fi

# Check hook
if [ -d "$HOOK_DST" ]; then
    echo "✓ Hook installed at $HOOK_DST"
else
    echo "✗ Hook not found"
fi

# Check portfolio
if [ -f "$DEFAULT_PORTFOLIO/portfolio.toml" ]; then
    echo "✓ Portfolio at $DEFAULT_PORTFOLIO"
else
    echo "⚠ No portfolio at $DEFAULT_PORTFOLIO"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Create a project: clawpm project init --in-repo /path/to/repo"
echo "  2. Start working: clawpm projects next"
