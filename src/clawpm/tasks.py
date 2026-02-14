"""Task operations for ClawPM."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import yaml

from .models import Task, TaskState, TaskComplexity, PortfolioConfig
from .discovery import get_project_dir


def get_tasks_dir(config: PortfolioConfig, project_id: str) -> Path | None:
    """Get the tasks directory for a project."""
    project_dir = get_project_dir(config, project_id)
    if project_dir:
        tasks_dir = project_dir / "tasks"
        if tasks_dir.exists():
            return tasks_dir
    return None


def list_tasks(
    config: PortfolioConfig,
    project_id: str,
    state_filter: TaskState | None = None,
) -> list[Task]:
    """List all tasks for a project."""
    tasks_dir = get_tasks_dir(config, project_id)
    if not tasks_dir:
        return []

    tasks: list[Task] = []

    # Collect tasks from all locations
    locations = [
        (tasks_dir, None),  # Main dir - open or progress
        (tasks_dir / "done", TaskState.DONE),
        (tasks_dir / "blocked", TaskState.BLOCKED),
    ]

    for location, forced_state in locations:
        if not location.exists():
            continue

        for file in location.glob("*.md"):
            try:
                task = Task.from_file(file)

                # Apply state filter
                if state_filter is not None and task.state != state_filter:
                    continue

                tasks.append(task)
            except Exception:
                # Skip malformed tasks
                continue

    # Sort by priority (lower is higher), then by ID
    tasks.sort(key=lambda t: (t.priority, t.id))

    return tasks


def get_task(config: PortfolioConfig, project_id: str, task_id: str) -> Task | None:
    """Get a specific task by ID."""
    tasks_dir = get_tasks_dir(config, project_id)
    if not tasks_dir:
        return None

    # Check all possible locations and filenames
    possible_paths = [
        tasks_dir / f"{task_id}.md",
        tasks_dir / f"{task_id}.progress.md",
        tasks_dir / "done" / f"{task_id}.md",
        tasks_dir / "blocked" / f"{task_id}.md",
    ]

    for path in possible_paths:
        if path.exists():
            try:
                return Task.from_file(path)
            except Exception:
                continue

    return None


def get_next_task(config: PortfolioConfig, project_id: str) -> Task | None:
    """Get the next task to work on (highest priority open task with satisfied dependencies)."""
    tasks = list_tasks(config, project_id)

    # Get IDs of completed tasks
    done_ids = {t.id for t in tasks if t.state == TaskState.DONE}

    # Find open tasks with satisfied dependencies
    for task in tasks:
        if task.state not in (TaskState.OPEN, TaskState.PROGRESS):
            continue

        # Check if all dependencies are satisfied
        if task.depends:
            if not all(dep in done_ids for dep in task.depends):
                continue

        return task

    return None


def change_task_state(
    config: PortfolioConfig,
    project_id: str,
    task_id: str,
    new_state: TaskState,
    note: str | None = None,
) -> Task | None:
    """Change a task's state by moving its file."""
    tasks_dir = get_tasks_dir(config, project_id)
    if not tasks_dir:
        return None

    # Find the current task file
    task = get_task(config, project_id, task_id)
    if not task or not task.file_path:
        return None

    current_path = task.file_path

    # Determine new path based on state
    if new_state == TaskState.OPEN:
        new_path = tasks_dir / f"{task_id}.md"
    elif new_state == TaskState.PROGRESS:
        new_path = tasks_dir / f"{task_id}.progress.md"
    elif new_state == TaskState.DONE:
        done_dir = tasks_dir / "done"
        done_dir.mkdir(exist_ok=True)
        new_path = done_dir / f"{task_id}.md"
    elif new_state == TaskState.BLOCKED:
        blocked_dir = tasks_dir / "blocked"
        blocked_dir.mkdir(exist_ok=True)
        new_path = blocked_dir / f"{task_id}.md"
    else:
        return None

    # Don't move if already in correct location
    if current_path.resolve() == new_path.resolve():
        return task

    # Move the file
    shutil.move(str(current_path), str(new_path))

    # Reload and return
    return Task.from_file(new_path)


def add_task(
    config: PortfolioConfig,
    project_id: str,
    title: str,
    task_id: str | None = None,
    priority: int = 5,
    complexity: TaskComplexity | None = None,
    depends: list[str] | None = None,
    description: str = "",
) -> Task | None:
    """Add a new task to a project."""
    tasks_dir = get_tasks_dir(config, project_id)
    if not tasks_dir:
        # Create tasks directory if project exists
        from .discovery import get_project_dir
        project_dir = get_project_dir(config, project_id)
        if not project_dir:
            return None
        tasks_dir = project_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

    # Generate task ID if not provided
    if not task_id:
        # Get project prefix from ID (uppercase)
        prefix = project_id.upper()[:5]

        # Find highest existing task number
        existing_nums = []
        for f in tasks_dir.glob(f"{prefix}-*.md"):
            try:
                num = int(f.stem.split("-")[1].replace(".progress", ""))
                existing_nums.append(num)
            except (IndexError, ValueError):
                pass

        # Also check subdirectories
        for subdir in ["done", "blocked"]:
            sub = tasks_dir / subdir
            if sub.exists():
                for f in sub.glob(f"{prefix}-*.md"):
                    try:
                        num = int(f.stem.split("-")[1])
                        existing_nums.append(num)
                    except (IndexError, ValueError):
                        pass

        next_num = max(existing_nums, default=-1) + 1
        task_id = f"{prefix}-{next_num:03d}"

    # Build frontmatter
    frontmatter = {
        "id": task_id,
        "priority": priority,
        "created": date.today().isoformat(),
    }

    if complexity:
        frontmatter["complexity"] = complexity.value

    if depends:
        frontmatter["depends"] = depends

    # Build content
    content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---
# {title}

{description}

## Acceptance Criteria

- [ ] (Add criteria here)

## Notes

"""

    # Write file
    file_path = tasks_dir / f"{task_id}.md"
    file_path.write_text(content)

    return Task.from_file(file_path)
