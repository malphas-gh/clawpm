#!/bin/bash
# ClawPM wrapper - runs from source with proper path handling
# Install: cp scripts/clawpm-wrapper.sh ~/.local/bin/clawpm

# Save original cwd
ORIGINAL_PWD=$(pwd)

# Resolve --in-repo paths to absolute before any directory changes
resolved_args=()
while [[ $# -gt 0 ]]; do
    case "$$1" in
        --in-repo|-r)
            resolved_args+=("$$1")
            shift
            # Convert relative path to absolute using original cwd
            if [[ "$$1" != /* ]]; then
                resolved_args+=("$$ORIGINAL_PWD/$$1")
            else
                resolved_args+=("$$1")
            fi
            shift
            ;;
        *)
            resolved_args+=("$$1")
            shift
            ;;
    esac
done

# Run from original directory, but tell uv where the project is
(cd "$$ORIGINAL_PWD" && uv run --project ~/Development/clawpm clawpm "$${resolved_args[@]}")
