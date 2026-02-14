"""Output formatting for ClawPM."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    JSON = "json"
    TEXT = "text"


def _serialize(obj: Any) -> Any:
    """Serialize objects for JSON output."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def output_json(data: Any, pretty: bool = True) -> None:
    """Output data as JSON."""
    serialized = _serialize(data)
    if pretty:
        print(json.dumps(serialized, indent=2, default=str))
    else:
        print(json.dumps(serialized, default=str))


def output_error(error: str, message: str, details: dict[str, Any] | None = None, fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output an error."""
    if fmt == OutputFormat.JSON:
        err_data = {"error": error, "message": message}
        if details:
            err_data["details"] = details
        print(json.dumps(err_data), file=sys.stderr)
    else:
        error_console.print(f"[red]Error:[/red] {message}")
        if details:
            for k, v in details.items():
                error_console.print(f"  {k}: {v}")


def output_success(message: str, data: Any = None, fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output a success message."""
    if fmt == OutputFormat.JSON:
        result = {"status": "ok", "message": message}
        if data is not None:
            result["data"] = _serialize(data)
        print(json.dumps(result, indent=2, default=str))
    else:
        console.print(f"[green]✓[/green] {message}")
        if data is not None:
            console.print(data)


def output_projects_list(projects: list[Any], fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output a list of projects."""
    if fmt == OutputFormat.JSON:
        output_json([_serialize(p) for p in projects])
    else:
        if not projects:
            console.print("[dim]No projects found[/dim]")
            return

        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Priority", justify="right")
        table.add_column("Labels")

        for p in projects:
            status_color = {
                "active": "green",
                "paused": "yellow",
                "archived": "dim",
            }.get(p.status.value, "white")

            table.add_row(
                p.id,
                p.name,
                f"[{status_color}]{p.status.value}[/{status_color}]",
                str(p.priority),
                ", ".join(p.labels) if p.labels else "-",
            )

        console.print(table)


def output_tasks_list(tasks: list[Any], fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output a list of tasks."""
    if fmt == OutputFormat.JSON:
        output_json([t.to_dict() for t in tasks])
    else:
        if not tasks:
            console.print("[dim]No tasks found[/dim]")
            return

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("State")
        table.add_column("Pri", justify="right")
        table.add_column("Cmplx")
        table.add_column("Depends")

        for t in tasks:
            state_color = {
                "open": "white",
                "progress": "yellow",
                "done": "green",
                "blocked": "red",
            }.get(t.state.value, "white")

            table.add_row(
                t.id,
                t.title[:50] + "..." if len(t.title) > 50 else t.title,
                f"[{state_color}]{t.state.value}[/{state_color}]",
                str(t.priority),
                t.complexity.value if t.complexity else "-",
                ", ".join(t.depends) if t.depends else "-",
            )

        console.print(table)


def output_task_detail(task: Any, fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output detailed task info."""
    if fmt == OutputFormat.JSON:
        output_json(task.to_dict())
    else:
        state_color = {
            "open": "white",
            "progress": "yellow",
            "done": "green",
            "blocked": "red",
        }.get(task.state.value, "white")

        panel = Panel(
            task.content or "[dim]No content[/dim]",
            title=f"[cyan]{task.id}[/cyan] - {task.title}",
            subtitle=f"[{state_color}]{task.state.value}[/{state_color}] | Priority: {task.priority}",
        )
        console.print(panel)

        if task.depends:
            console.print(f"[dim]Depends on:[/dim] {', '.join(task.depends)}")
        if task.file_path:
            console.print(f"[dim]File:[/dim] {task.file_path}")


def output_worklog_entries(entries: list[Any], fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output work log entries."""
    if fmt == OutputFormat.JSON:
        output_json([e.to_dict() for e in entries])
    else:
        if not entries:
            console.print("[dim]No log entries found[/dim]")
            return

        for entry in entries:
            action_color = {
                "start": "cyan",
                "progress": "yellow",
                "done": "green",
                "blocked": "red",
                "pause": "dim",
                "research": "blue",
                "note": "white",
            }.get(entry.action.value, "white")

            ts = entry.ts.strftime("%Y-%m-%d %H:%M") if hasattr(entry.ts, "strftime") else str(entry.ts)

            text = Text()
            text.append(f"{ts} ", style="dim")
            text.append(f"[{entry.project}]", style="cyan")
            if entry.task:
                text.append(f" {entry.task}", style="white")
            text.append(f" {entry.action.value}", style=action_color)

            console.print(text)

            if entry.summary:
                console.print(f"  {entry.summary}")
            if entry.next:
                console.print(f"  [dim]Next:[/dim] {entry.next}")
            console.print()


def output_research_list(items: list[Any], fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output a list of research items."""
    if fmt == OutputFormat.JSON:
        output_json([r.to_dict() for r in items])
    else:
        if not items:
            console.print("[dim]No research items found[/dim]")
            return

        table = Table(title="Research")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Tags")

        for r in items:
            status_color = {
                "open": "yellow",
                "complete": "green",
                "stale": "dim",
            }.get(r.status.value, "white")

            table.add_row(
                r.id,
                r.title[:40] + "..." if len(r.title) > 40 else r.title,
                r.type.value,
                f"[{status_color}]{r.status.value}[/{status_color}]",
                ", ".join(r.tags) if r.tags else "-",
            )

        console.print(table)


def output_context(context: dict[str, Any], fmt: OutputFormat = OutputFormat.JSON) -> None:
    """Output project context."""
    if fmt == OutputFormat.JSON:
        output_json(context)
    else:
        console.print(Panel(f"[cyan bold]{context['project']['name']}[/cyan bold]", title="Project Context"))

        console.print("\n[bold]Project Info[/bold]")
        console.print(f"  ID: {context['project']['id']}")
        console.print(f"  Status: {context['project']['status']}")
        console.print(f"  Priority: {context['project']['priority']}")

        if context.get("spec"):
            console.print("\n[bold]Spec[/bold]")
            console.print(f"  {context['spec'][:200]}..." if len(context.get("spec", "")) > 200 else f"  {context.get('spec', 'N/A')}")

        if context.get("last_work"):
            console.print("\n[bold]Last Work[/bold]")
            lw = context["last_work"]
            console.print(f"  {lw.get('ts', 'N/A')} - {lw.get('action', 'N/A')}")
            if lw.get("summary"):
                console.print(f"  {lw['summary']}")

        if context.get("next_task"):
            nt = context["next_task"]
            console.print("\n[bold]Next Task[/bold]")
            console.print(f"  [{nt['id']}] {nt['title']}")

        if context.get("blockers"):
            console.print("\n[bold red]Blockers[/bold red]")
            for b in context["blockers"]:
                console.print(f"  - [{b['id']}] {b['title']}")
