"""Project context management for ClawPM."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .discovery import load_portfolio_config, get_project
from .models import ProjectSettings


CONTEXT_FILE = Path.home() / ".clawpm-context"


def detect_project_from_cwd() -> ProjectSettings | None:
    """Detect project from current working directory.
    
    Walks up from cwd looking for .project/settings.toml.
    Returns the project if found, None otherwise.
    """
    config = load_portfolio_config()
    if not config:
        return None
    
    cwd = Path.cwd().resolve()
    
    # Walk up looking for .project/settings.toml
    current = cwd
    while current != current.parent:
        settings_file = current / ".project" / "settings.toml"
        if settings_file.exists():
            try:
                return ProjectSettings.load(settings_file)
            except Exception:
                pass
        current = current.parent
    
    return None


def get_context_project() -> str | None:
    """Get the project ID from context file."""
    if not CONTEXT_FILE.exists():
        return None
    
    try:
        content = CONTEXT_FILE.read_text().strip()
        if content:
            return content
    except Exception:
        pass
    
    return None


def set_context_project(project_id: str | None) -> None:
    """Set the context project ID."""
    if project_id is None:
        if CONTEXT_FILE.exists():
            CONTEXT_FILE.unlink()
    else:
        CONTEXT_FILE.write_text(project_id)


def resolve_project(explicit: str | None = None) -> tuple[str | None, str]:
    """Resolve project ID from explicit arg, cwd, or context.
    
    Returns: (project_id, source) where source is one of:
        - "explicit": from command line argument
        - "cwd": detected from current directory
        - "context": from `clawpm use` context
        - "none": no project found
    """
    # 1. Explicit takes precedence
    if explicit:
        return (explicit, "explicit")
    
    # 2. Check cwd
    project = detect_project_from_cwd()
    if project:
        return (project.id, "cwd")
    
    # 3. Check context file
    context_id = get_context_project()
    if context_id:
        return (context_id, "context")
    
    return (None, "none")


def get_project_prefix(project_id: str) -> str:
    """Get the task ID prefix for a project.
    
    Converts project ID to uppercase prefix, e.g.:
        - clawpm -> CLAWP
        - my-project -> MYPRO (first 5 chars, uppercase, no hyphens)
    """
    # Remove hyphens/underscores and uppercase
    clean = re.sub(r'[-_]', '', project_id).upper()
    # Take first 5 chars
    return clean[:5]


def expand_task_id(task_ref: str, project_id: str) -> str:
    """Expand a short task reference to full ID.
    
    Examples:
        - "22" -> "CLAWP-022" (for clawpm project)
        - "CLAWP-022" -> "CLAWP-022" (already full)
        - "022" -> "CLAWP-022"
    """
    # Already has a prefix (contains hyphen and letters before it)
    if '-' in task_ref and re.match(r'^[A-Z]+-\d+$', task_ref.upper()):
        return task_ref.upper()
    
    # Pure numeric - expand with project prefix
    if task_ref.isdigit():
        prefix = get_project_prefix(project_id)
        num = int(task_ref)
        return f"{prefix}-{num:03d}"
    
    # Might be just the number part with leading zeros
    if re.match(r'^\d+$', task_ref):
        prefix = get_project_prefix(project_id)
        num = int(task_ref)
        return f"{prefix}-{num:03d}"
    
    # Return as-is if unrecognized format
    return task_ref
