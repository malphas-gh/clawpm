"""ClawPM CLI - Filesystem-first multi-project manager."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from .models import (
    ProjectStatus,
    TaskState,
    TaskComplexity,
    WorkLogAction,
    ResearchType,
    ResearchStatus,
)
from .output import (
    OutputFormat,
    output_json,
    output_error,
    output_success,
    output_projects_list,
    output_tasks_list,
    output_task_detail,
    output_worklog_entries,
    output_research_list,
    output_context,
)
from .discovery import (
    get_portfolio_path,
    load_portfolio_config,
    discover_projects,
    get_project,
    validate_portfolio,
)
from .tasks import (
    list_tasks,
    get_task,
    get_next_task,
    change_task_state,
    add_task,
)
from .worklog import (
    add_entry,
    tail_entries,
    get_last_entry,
)
from .research import (
    list_research,
    get_research,
    add_research,
    link_research_session,
)
from .context import (
    resolve_project,
    expand_task_id,
    get_context_project,
    set_context_project,
    detect_project_from_cwd,
)


# Global format option
pass_format = click.make_pass_decorator(OutputFormat, ensure=True)


@click.group()
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--project", "-p",
    "global_project",
    help="Project ID (overrides auto-detection)",
)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context, format: str, global_project: str | None) -> None:
    """ClawPM - Filesystem-first multi-project manager."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = OutputFormat(format)
    ctx.obj["global_project"] = global_project


def get_format(ctx: click.Context) -> OutputFormat:
    """Get the output format from context."""
    return ctx.obj.get("format", OutputFormat.JSON)


def require_portfolio(ctx: click.Context):
    """Load portfolio config or exit with error."""
    config = load_portfolio_config()
    if not config:
        fmt = get_format(ctx)
        output_error(
            "portfolio_not_found",
            "No portfolio found at ~/clawpm. Run setup or create portfolio.toml.",
            fmt=fmt,
        )
        sys.exit(1)
    return config


def require_project(ctx: click.Context, project_id: str | None, required: bool = True) -> tuple[str | None, str]:
    """Resolve project from explicit arg, global flag, cwd, or context.
    
    Returns (project_id, source). Exits with error if required and not found.
    Priority: explicit arg > global --project flag > cwd > context
    """
    # Check for global --project flag if no explicit arg
    if not project_id:
        project_id = ctx.obj.get("global_project")
        if project_id:
            return (project_id, "global")
    
    resolved_id, source = resolve_project(project_id)
    
    if required and not resolved_id:
        fmt = get_format(ctx)
        output_error(
            "no_project",
            "No project specified. Use --project, cd into a project, or run 'clawpm use <project>'.",
            fmt=fmt,
        )
        sys.exit(1)
    
    return resolved_id, source


# ============================================================================
# Use command (project context)
# ============================================================================


@main.command("use")
@click.argument("project_id", required=False)
@click.option("--clear", is_flag=True, help="Clear the current context")
@click.pass_context
def use_project(ctx: click.Context, project_id: str | None, clear: bool) -> None:
    """Set or show the current project context.
    
    When no project is specified, shows the current context.
    Use --clear to remove the context.
    """
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    if clear:
        set_context_project(None)
        output_success("Context cleared", fmt=fmt)
        return
    
    if project_id:
        # Verify project exists
        proj = get_project(config, project_id)
        if not proj:
            output_error("project_not_found", f"Project '{project_id}' not found", fmt=fmt)
            sys.exit(1)
        
        set_context_project(project_id)
        output_success(f"Now using project: {proj.name} ({proj.id})", fmt=fmt)
    else:
        # Show current context
        current = get_context_project()
        cwd_project = detect_project_from_cwd()
        
        result = {
            "context_project": current,
            "cwd_project": cwd_project.id if cwd_project else None,
            "effective": cwd_project.id if cwd_project else current,
        }
        
        if fmt == OutputFormat.JSON:
            output_json(result)
        else:
            if cwd_project:
                click.echo(f"Current directory: {cwd_project.name} ({cwd_project.id})")
            elif current:
                click.echo(f"Context: {current}")
            else:
                click.echo("No project context set. Use 'clawpm use <project>' or cd into a project.")


# ============================================================================
# Projects commands
# ============================================================================


@main.group()
def projects() -> None:
    """Manage projects."""
    pass


@projects.command("list")
@click.option(
    "--filter", "-f", "status_filter",
    type=click.Choice(["active", "paused", "archived"]),
    default=None,
    help="Filter by status",
)
@click.pass_context
def projects_list(ctx: click.Context, status_filter: str | None) -> None:
    """List all projects."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)

    status = ProjectStatus(status_filter) if status_filter else None
    projects_found = discover_projects(config, status_filter=status)

    output_projects_list(projects_found, fmt=fmt)


@projects.command("next")
@click.pass_context
def projects_next(ctx: click.Context) -> None:
    """Get the next task across all active projects."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)

    # Get all active projects
    active_projects = discover_projects(config, status_filter=ProjectStatus.ACTIVE)

    # Find next task across all projects
    best_task = None
    best_project = None

    for project in active_projects:
        task = get_next_task(config, project.id)
        if task:
            if best_task is None or (project.priority, task.priority) < (best_project.priority, best_task.priority):
                best_task = task
                best_project = project

    if best_task and best_project:
        result = {
            "project": {
                "id": best_project.id,
                "name": best_project.name,
                "priority": best_project.priority,
            },
            "task": best_task.to_dict(),
        }
        if fmt == OutputFormat.JSON:
            output_json(result)
        else:
            output_task_detail(best_task, fmt=fmt)
            click.echo(f"\nProject: {best_project.name} ({best_project.id})")
    else:
        if fmt == OutputFormat.JSON:
            output_json({"project": None, "task": None, "message": "No tasks available"})
        else:
            click.echo("No tasks available across active projects.")


# ============================================================================
# Project commands (singular)
# ============================================================================


@main.group()
def project() -> None:
    """Manage a single project."""
    pass


@project.command("context")
@click.argument("project_id", required=False)
@click.pass_context
def project_context(ctx: click.Context, project_id: str | None) -> None:
    """Get full context for a project (spec, last work, next task, blockers)."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    proj = get_project(config, project_id)
    if not proj:
        output_error("project_not_found", f"No project with id '{project_id}'", fmt=fmt)
        sys.exit(1)

    # Build context
    context: dict = {
        "project": {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status.value,
            "priority": proj.priority,
            "labels": proj.labels,
        }
    }

    # Read spec if exists
    if proj.project_dir:
        spec_file = proj.project_dir / ".project" / "SPEC.md"
        if spec_file.exists():
            context["spec"] = spec_file.read_text()

    # Get last work log entry
    last_work = get_last_entry(config, project=project_id)
    if last_work:
        context["last_work"] = last_work.to_dict()

    # Get next task
    next_task = get_next_task(config, project_id)
    if next_task:
        context["next_task"] = next_task.to_dict()

    # Get blocked tasks
    blocked = list_tasks(config, project_id, state_filter=TaskState.BLOCKED)
    if blocked:
        context["blockers"] = [t.to_dict() for t in blocked]

    output_context(context, fmt=fmt)


@project.command("init")
@click.option("--in-repo", "-r", "repo_path", type=click.Path(exists=True), default=".", help="Repository path")
@click.option("--id", "project_id", help="Project ID (defaults to directory name)")
@click.option("--name", "project_name", help="Project name")
@click.pass_context
def project_init(ctx: click.Context, repo_path: str, project_id: str | None, project_name: str | None) -> None:
    """Initialize a new project in a repository."""
    fmt = get_format(ctx)

    repo = Path(repo_path).resolve()
    project_dir = repo / ".project"

    if project_dir.exists():
        output_error("project_exists", f"Project already exists at {project_dir} (repo: {repo})", fmt=fmt)
        sys.exit(1)

    # Generate defaults
    if not project_id:
        project_id = repo.name.lower().replace(" ", "-").replace("_", "-")

    if not project_name:
        project_name = repo.name

    # Create structure
    project_dir.mkdir(parents=True)
    (project_dir / "tasks").mkdir()
    (project_dir / "tasks" / "done").mkdir()
    (project_dir / "tasks" / "blocked").mkdir()
    (project_dir / "research").mkdir()
    (project_dir / "notes").mkdir()

    # Create settings.toml
    settings_content = f'''id = "{project_id}"
name = "{project_name}"
status = "active"
priority = 5
repo_path = "{repo}"
labels = []
'''
    (project_dir / "settings.toml").write_text(settings_content)

    # Create SPEC.md template
    spec_content = f"""# {project_name}

## Overview

(Describe the project here)

## Goals

- Goal 1
- Goal 2

## Non-Goals

- Non-goal 1

## Technical Notes

...
"""
    (project_dir / "SPEC.md").write_text(spec_content)

    # Create learnings.md
    (project_dir / "learnings.md").write_text(f"# {project_name} Learnings\n\n")

    output_success(f"Project initialized at {project_dir}", fmt=fmt)


@project.command("doctor")
@click.option("--project", "-p", "project_id", help="Check specific project")
@click.pass_context
def project_doctor(ctx: click.Context, project_id: str | None) -> None:
    """Check for issues with projects and portfolio."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)

    issues: list[dict] = []

    # Validate portfolio
    portfolio_issues = validate_portfolio(config)
    for issue in portfolio_issues:
        issues.append({"level": "error", "scope": "portfolio", "message": issue})

    # Check projects
    projects_to_check = []
    if project_id:
        proj = get_project(config, project_id)
        if proj:
            projects_to_check = [proj]
        else:
            issues.append({
                "level": "error",
                "scope": "project",
                "project": project_id,
                "message": f"Project not found: {project_id}",
            })
    else:
        projects_to_check = discover_projects(config)

    for proj in projects_to_check:
        if not proj.project_dir:
            continue

        project_path = proj.project_dir / ".project"

        # Check for required files
        if not (project_path / "settings.toml").exists():
            issues.append({
                "level": "error",
                "scope": "project",
                "project": proj.id,
                "message": "Missing settings.toml",
            })

        # Check tasks directory
        tasks_dir = project_path / "tasks"
        if not tasks_dir.exists():
            issues.append({
                "level": "warning",
                "scope": "project",
                "project": proj.id,
                "message": "Missing tasks directory",
            })

        # Check for broken repo_path
        if proj.repo_path and not proj.repo_path.exists():
            issues.append({
                "level": "warning",
                "scope": "project",
                "project": proj.id,
                "message": f"repo_path does not exist: {proj.repo_path}",
            })

    if fmt == OutputFormat.JSON:
        output_json({"issues": issues, "count": len(issues)})
    else:
        if not issues:
            click.echo("✓ No issues found")
        else:
            for issue in issues:
                level_color = {"error": "red", "warning": "yellow"}.get(issue["level"], "white")
                scope = issue.get("project", issue["scope"])
                click.echo(f"[{issue['level'].upper()}] [{scope}] {issue['message']}")


# ============================================================================
# Tasks commands
# ============================================================================


@main.group()
def tasks() -> None:
    """Manage tasks."""
    pass


@tasks.command("list")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option(
    "--state", "-s",
    type=click.Choice(["open", "progress", "done", "blocked", "all"]),
    default="all",
    help="Filter by state",
)
@click.pass_context
def tasks_list(ctx: click.Context, project_id: str | None, state: str) -> None:
    """List tasks for a project."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    state_filter = None if state == "all" else TaskState(state)
    found_tasks = list_tasks(config, project_id, state_filter=state_filter)

    output_tasks_list(found_tasks, fmt=fmt)


@tasks.command("show")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("task_id")
@click.pass_context
def tasks_show(ctx: click.Context, project_id: str | None, task_id: str) -> None:
    """Show details for a specific task."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)
    task_id = expand_task_id(task_id, project_id)

    task = get_task(config, project_id, task_id)
    if not task:
        output_error("task_not_found", f"No task with id '{task_id}' in project '{project_id}'", fmt=fmt)
        sys.exit(1)

    output_task_detail(task, fmt=fmt)


@tasks.command("state")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("task_id")
@click.argument("new_state", type=click.Choice(["open", "progress", "done", "blocked"]))
@click.option("--note", "-n", help="Note about the state change")
@click.pass_context
def tasks_state(ctx: click.Context, project_id: str | None, task_id: str, new_state: str, note: str | None) -> None:
    """Change task state."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)
    task_id = expand_task_id(task_id, project_id)

    state = TaskState(new_state)
    task = change_task_state(config, project_id, task_id, state, note=note)

    if not task:
        output_error("task_not_found", f"No task with id '{task_id}' in project '{project_id}'", fmt=fmt)
        sys.exit(1)

    output_success(f"Task {task_id} moved to {new_state}", data=task.to_dict(), fmt=fmt)


@tasks.command("add")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--id", "task_id", help="Task ID (auto-generated if not provided)")
@click.option("--priority", type=int, default=5, help="Priority (1-10, lower is higher)")
@click.option("--complexity", "-c", type=click.Choice(["s", "m", "l", "xl"]), help="Complexity")
@click.option("--depends", "-d", multiple=True, help="Dependencies (can specify multiple)")
@click.option("--description", help="Task description (deprecated, use --body)")
@click.option("--body", "-b", help="Task body content")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--stdin", "read_stdin", is_flag=True, help="Read body from stdin")
@click.pass_context
def tasks_add(
    ctx: click.Context,
    project_id: str | None,
    title: str,
    task_id: str | None,
    priority: int,
    complexity: str | None,
    depends: tuple[str, ...],
    description: str | None,
    body: str | None,
    body_file: str | None,
    read_stdin: bool,
) -> None:
    """Add a new task."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    # Determine body content
    task_body = ""
    if body:
        task_body = body
    elif body_file:
        task_body = Path(body_file).read_text()
    elif read_stdin:
        import sys
        task_body = sys.stdin.read()
    elif description:
        task_body = description

    cmplx = TaskComplexity(complexity) if complexity else None
    deps = list(depends) if depends else None

    task = add_task(
        config,
        project_id,
        title,
        task_id=task_id,
        priority=priority,
        complexity=cmplx,
        depends=deps,
        description=task_body,
    )

    if not task:
        output_error("add_failed", f"Failed to add task to project '{project_id}'", fmt=fmt)
        sys.exit(1)

    output_success(f"Task {task.id} created", data=task.to_dict(), fmt=fmt)


# ============================================================================
# Top-level task shortcuts
# ============================================================================


@main.command("add")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("title")
@click.option("--priority", type=int, default=5, help="Priority (1-10)")
@click.option("--complexity", "-c", type=click.Choice(["s", "m", "l", "xl"]), default="m", help="Complexity")
@click.pass_context
def quick_add(ctx: click.Context, project_id: str | None, title: str, priority: int, complexity: str) -> None:
    """Quick add a task (alias for 'tasks add')."""
    ctx.invoke(tasks_add, project_id=project_id, title=title, priority=priority, complexity=complexity)


@main.command("done")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("task_id")
@click.option("--note", "-n", help="Completion note")
@click.pass_context
def quick_done(ctx: click.Context, project_id: str | None, task_id: str, note: str | None) -> None:
    """Mark a task as done (alias for 'tasks state <id> done')."""
    ctx.invoke(tasks_state, project_id=project_id, task_id=task_id, new_state="done", note=note)


@main.command("start")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("task_id")
@click.pass_context
def quick_start(ctx: click.Context, project_id: str | None, task_id: str) -> None:
    """Start working on a task (alias for 'tasks state <id> progress')."""
    ctx.invoke(tasks_state, project_id=project_id, task_id=task_id, new_state="progress", note=None)


@main.command("block")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.argument("task_id")
@click.option("--note", "-n", help="Blocker description")
@click.pass_context
def quick_block(ctx: click.Context, project_id: str | None, task_id: str, note: str | None) -> None:
    """Mark a task as blocked (alias for 'tasks state <id> blocked')."""
    ctx.invoke(tasks_state, project_id=project_id, task_id=task_id, new_state="blocked", note=note)


@main.command("next")
@click.option("--project", "-p", "project_id", help="Project ID (if not specified, searches all)")
@click.pass_context
def quick_next(ctx: click.Context, project_id: str | None) -> None:
    """Get the next task to work on."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    if project_id:
        # Get next task for specific project
        task = get_next_task(config, project_id)
        if task:
            output_task_detail(task, fmt=fmt)
        else:
            if fmt == OutputFormat.JSON:
                output_json({"task": None, "message": "No tasks available"})
            else:
                click.echo("No tasks available.")
    else:
        # Delegate to projects next
        ctx.invoke(projects_next)


@main.command("status")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.pass_context
def quick_status(ctx: click.Context, project_id: str | None) -> None:
    """Show current project status (tasks in progress, blockers, next up)."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    resolved_id, source = require_project(ctx, project_id, required=False)
    
    if not resolved_id:
        # Show overview of all projects
        projects_found = discover_projects(config, status_filter=ProjectStatus.ACTIVE)
        
        result = {
            "projects": [],
            "total_active": 0,
            "total_blocked": 0,
        }
        
        for proj in projects_found:
            in_progress = list_tasks(config, proj.id, state_filter=TaskState.PROGRESS)
            blocked = list_tasks(config, proj.id, state_filter=TaskState.BLOCKED)
            
            proj_info = {
                "id": proj.id,
                "name": proj.name,
                "in_progress": len(in_progress),
                "blocked": len(blocked),
            }
            result["projects"].append(proj_info)
            result["total_active"] += len(in_progress)
            result["total_blocked"] += len(blocked)
        
        if fmt == OutputFormat.JSON:
            output_json(result)
        else:
            click.echo(f"Active: {result['total_active']} tasks in progress, {result['total_blocked']} blocked\n")
            for proj in result["projects"]:
                status_str = []
                if proj["in_progress"]:
                    status_str.append(f"{proj['in_progress']} active")
                if proj["blocked"]:
                    status_str.append(f"{proj['blocked']} blocked")
                click.echo(f"  {proj['name']}: {', '.join(status_str) if status_str else 'idle'}")
    else:
        # Show specific project status
        proj = get_project(config, resolved_id)
        if not proj:
            output_error("project_not_found", f"Project '{resolved_id}' not found", fmt=fmt)
            sys.exit(1)
        
        in_progress = list_tasks(config, resolved_id, state_filter=TaskState.PROGRESS)
        blocked = list_tasks(config, resolved_id, state_filter=TaskState.BLOCKED)
        open_tasks = list_tasks(config, resolved_id, state_filter=TaskState.OPEN)
        next_task = get_next_task(config, resolved_id)
        
        result = {
            "project": proj.id,
            "name": proj.name,
            "source": source,
            "in_progress": [t.to_dict() for t in in_progress],
            "blocked": [t.to_dict() for t in blocked],
            "open_count": len(open_tasks),
            "next": next_task.to_dict() if next_task else None,
        }
        
        if fmt == OutputFormat.JSON:
            output_json(result)
        else:
            click.echo(f"Project: {proj.name} ({source})")
            click.echo(f"Open: {len(open_tasks)} | In Progress: {len(in_progress)} | Blocked: {len(blocked)}")
            
            if in_progress:
                click.echo("\nIn Progress:")
                for t in in_progress:
                    click.echo(f"  → {t.id}: {t.title}")
            
            if blocked:
                click.echo("\nBlocked:")
                for t in blocked:
                    click.echo(f"  ✗ {t.id}: {t.title}")
            
            if next_task and next_task not in in_progress:
                click.echo(f"\nNext up: {next_task.id}: {next_task.title}")


# ============================================================================
# Log commands
# ============================================================================


@main.group()
def log() -> None:
    """Manage work log."""
    pass


@log.command("add")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--task", "-t", "task_id", help="Task ID")
@click.option(
    "--action", "-a",
    type=click.Choice(["start", "progress", "done", "blocked", "pause", "research", "note"]),
    required=True,
    help="Action type",
)
@click.option("--summary", "-s", required=True, help="Summary of work")
@click.option("--next", "next_steps", help="Next steps")
@click.option("--files", "-f", multiple=True, help="Files changed")
@click.option("--blocker", "-b", help="Blocker description")
@click.option("--agent", default="main", help="Agent ID")
@click.option("--session-key", help="OpenClaw session key")
@click.pass_context
def log_add(
    ctx: click.Context,
    project_id: str | None,
    task_id: str | None,
    action: str,
    summary: str,
    next_steps: str | None,
    files: tuple[str, ...],
    blocker: str | None,
    agent: str,
    session_key: str | None,
) -> None:
    """Add a work log entry."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)
    
    # Expand task ID if provided
    if task_id:
        task_id = expand_task_id(task_id, project_id)

    # Auto-detect changed files from git if not manually specified
    if not files and project_id:
        project = get_project(config, project_id)
        if project and project.repo_path and project.repo_path.exists():
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=project.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    files = tuple(f for f in result.stdout.strip().split('\n') if f)
            except Exception:
                pass  # No git or error - continue without files_changed

    entry = add_entry(
        config,
        project=project_id,
        action=WorkLogAction(action),
        task=task_id,
        summary=summary,
        next_steps=next_steps,
        files_changed=list(files) if files else None,
        blockers=blocker,
        agent=agent,
        session_key=session_key,
    )

    output_success("Entry added", data=entry.to_dict(), fmt=fmt)


@log.command("tail")
@click.option("--project", "-p", "project_id", help="Filter by project")
@click.option("--limit", "-n", type=int, default=20, help="Number of entries")
@click.pass_context
def log_tail(ctx: click.Context, project_id: str | None, limit: int) -> None:
    """Show recent work log entries."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)

    entries = tail_entries(config, project=project_id, limit=limit)
    output_worklog_entries(entries, fmt=fmt)


@log.command("last")
@click.option("--project", "-p", "project_id", help="Filter by project")
@click.pass_context
def log_last(ctx: click.Context, project_id: str | None) -> None:
    """Show the most recent work log entry."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)

    entry = get_last_entry(config, project=project_id)

    if entry:
        output_worklog_entries([entry], fmt=fmt)
    else:
        if fmt == OutputFormat.JSON:
            output_json(None)
        else:
            click.echo("No entries found")


# ============================================================================
# Research commands
# ============================================================================


@main.group()
def research() -> None:
    """Manage research items."""
    pass


@research.command("list")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--status", "-s", type=click.Choice(["open", "complete", "stale"]), help="Filter by status")
@click.option("--tags", "-t", multiple=True, help="Filter by tags (must have all)")
@click.pass_context
def research_list(ctx: click.Context, project_id: str | None, status: str | None, tags: tuple[str, ...]) -> None:
    """List research items."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    status_filter = ResearchStatus(status) if status else None
    tags_filter = list(tags) if tags else None

    items = list_research(config, project_id, status_filter=status_filter, tags_filter=tags_filter)
    output_research_list(items, fmt=fmt)


@research.command("add")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--type", "-t", "research_type", type=click.Choice(["investigation", "spike", "decision", "reference"]), required=True)
@click.option("--title", required=True, help="Research title")
@click.option("--id", "research_id", help="Research ID (auto-generated if not provided)")
@click.option("--tags", multiple=True, help="Tags")
@click.option("--question", "-q", help="Research question")
@click.pass_context
def research_add(
    ctx: click.Context,
    project_id: str | None,
    research_type: str,
    title: str,
    research_id: str | None,
    tags: tuple[str, ...],
    question: str | None,
) -> None:
    """Add a new research item."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    # Support both -t tag1 -t tag2 and --tags tag1,tag2
    parsed_tags = []
    for tag in tags:
        parsed_tags.extend(t.strip() for t in tag.split(",") if t.strip())

    item = add_research(
        config,
        project_id,
        title,
        ResearchType(research_type),
        research_id=research_id,
        tags=parsed_tags if parsed_tags else None,
        question=question or "",
    )

    if not item:
        output_error("add_failed", f"Failed to add research to project '{project_id}'", fmt=fmt)
        sys.exit(1)

    output_success(f"Research {item.id} created", data=item.to_dict(), fmt=fmt)


@research.command("link")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--id", "research_id", required=True, help="Research ID")
@click.option("--session-key", "-s", required=True, help="OpenClaw session key")
@click.option("--run-id", "-r", help="OpenClaw run ID")
@click.option("--spawned-by", help="Spawning session key")
@click.pass_context
def research_link(
    ctx: click.Context,
    project_id: str | None,
    research_id: str,
    session_key: str,
    run_id: str | None,
    spawned_by: str | None,
) -> None:
    """Link a research item to an OpenClaw session."""
    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)

    item = link_research_session(
        config,
        project_id,
        research_id,
        session_key,
        run_id=run_id,
        spawned_by=spawned_by,
    )

    if not item:
        output_error("link_failed", f"Failed to link research '{research_id}'", fmt=fmt)
        sys.exit(1)

    output_success(f"Research {research_id} linked to session", data=item.to_dict(), fmt=fmt)


# ============================================================================
# Setup commands
# ============================================================================


@main.command("setup")
@click.option("--check", is_flag=True, help="Check installation status")
@click.pass_context
def setup(ctx: click.Context, check: bool) -> None:
    """Setup or verify ClawPM installation."""
    fmt = get_format(ctx)

    if check:
        issues: list[str] = []

        # Check portfolio path (defaults to ~/clawpm)
        portfolio_path = get_portfolio_path()
        if not portfolio_path:
            issues.append("No portfolio found at ~/clawpm (portfolio.toml missing)")
        else:
            if not (portfolio_path / "work_log.jsonl").exists():
                issues.append(f"work_log.jsonl not found in {portfolio_path}")

        # Check portfolio config
        config = load_portfolio_config()
        if config:
            portfolio_issues = validate_portfolio(config)
            issues.extend(portfolio_issues)

        if fmt == OutputFormat.JSON:
            output_json({
                "status": "ok" if not issues else "issues",
                "portfolio_path": str(portfolio_path) if portfolio_path else None,
                "issues": issues,
            })
        else:
            if issues:
                click.echo("Issues found:")
                for issue in issues:
                    click.echo(f"  - {issue}")
            else:
                click.echo("✓ ClawPM is properly configured")
                if portfolio_path:
                    click.echo(f"  Portfolio: {portfolio_path}")
    else:
        # Interactive setup - just show instructions for now
        if fmt == OutputFormat.JSON:
            output_json({"message": "Create ~/clawpm/portfolio.toml to get started"})
        else:
            click.echo("Manual setup:")
            click.echo("  1. Create ~/clawpm directory")
            click.echo("  2. Create portfolio.toml in that directory")
            click.echo("  3. Create projects/ subdirectory")
            click.echo("  4. Create work_log.jsonl (empty file)")


@main.command("version")
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version."""
    fmt = get_format(ctx)
    if fmt == OutputFormat.JSON:
        output_json({"version": __version__})
    else:
        click.echo(f"clawpm {__version__}")


@main.command("doctor")
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Run full health check."""
    # Delegate to project doctor with no specific project
    ctx.invoke(project_doctor, project_id=None)


# ============================================================================
# Issues commands
# ============================================================================

@main.group("issues")
def issues_group() -> None:
    """Log and track issues found during work."""
    pass


@issues_group.command("add")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--type", "-t", "issue_type", type=click.Choice(["bug", "ux", "docs", "feature"]), default="bug", help="Issue type")
@click.option("--severity", "-s", type=click.Choice(["high", "medium", "low"]), default="medium", help="Severity")
@click.option("--command", "-c", "cmd", help="Command that triggered the issue")
@click.option("--expected", "-e", help="What was expected")
@click.option("--actual", "-a", help="What actually happened")
@click.option("--context", help="Additional context")
@click.pass_context
def issues_add(
    ctx: click.Context,
    project_id: str | None,
    issue_type: str,
    severity: str,
    cmd: str | None,
    expected: str | None,
    actual: str | None,
    context: str | None,
) -> None:
    """Log an issue for a project."""
    import json
    from datetime import datetime, timezone

    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)
    proj = get_project(config, project_id)

    if not proj:
        output_error("project_not_found", f"Project '{project_id}' not found", fmt=fmt)
        sys.exit(1)

    # Create .agent directory if needed
    agent_dir = proj.project_dir / ".agent"
    agent_dir.mkdir(exist_ok=True)
    issues_file = agent_dir / "issues.jsonl"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "type": issue_type,
        "severity": severity,
        "command": cmd,
        "expected": expected,
        "actual": actual,
        "context": context,
        "fixed": False,
    }

    # Remove None values
    entry = {k: v for k, v in entry.items() if v is not None}

    with open(issues_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if fmt == OutputFormat.JSON:
        output_json({"status": "logged", "file": str(issues_file), "entry": entry})
    else:
        click.echo(f"Logged {issue_type} issue ({severity}) to {issues_file}")


@issues_group.command("list")
@click.option("--project", "-p", "project_id", help="Project ID (auto-detected if not specified)")
@click.option("--open", "open_only", is_flag=True, help="Show only unfixed issues")
@click.pass_context
def issues_list(ctx: click.Context, project_id: str | None, open_only: bool) -> None:
    """List issues for a project."""
    import json

    fmt = get_format(ctx)
    config = require_portfolio(ctx)
    
    project_id, _ = require_project(ctx, project_id)
    proj = get_project(config, project_id)

    if not proj:
        output_error("project_not_found", f"Project '{project_id}' not found", fmt=fmt)
        sys.exit(1)

    issues_file = proj.project_dir / ".agent" / "issues.jsonl"
    if not issues_file.exists():
        if fmt == OutputFormat.JSON:
            output_json({"issues": [], "count": 0})
        else:
            click.echo("No issues logged yet.")
        return

    issues = []
    with open(issues_file) as f:
        for line in f:
            line = line.strip()
            if line:
                issue = json.loads(line)
                if open_only and issue.get("fixed"):
                    continue
                issues.append(issue)

    if fmt == OutputFormat.JSON:
        output_json({"issues": issues, "count": len(issues)})
    else:
        if not issues:
            click.echo("No issues found.")
            return
        for i, issue in enumerate(issues, 1):
            status = "✓" if issue.get("fixed") else "○"
            sev = issue.get("severity", "?")[0].upper()
            typ = issue.get("type", "?")
            click.echo(f"{status} [{sev}] {typ}: {issue.get('actual', issue.get('context', 'No description'))}")


# ============================================================================
# Serve command
# ============================================================================

@main.command("serve")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
def serve(host: str, port: int) -> None:
    """Start the web UI server."""
    import uvicorn
    from .serve import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
