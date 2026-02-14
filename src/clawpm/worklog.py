"""Work log operations for ClawPM."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import PortfolioConfig, WorkLogEntry, WorkLogAction


def get_worklog_path(config: PortfolioConfig) -> Path:
    """Get the work log file path."""
    return config.portfolio_root / "work_log.jsonl"


def add_entry(
    config: PortfolioConfig,
    project: str,
    action: WorkLogAction,
    task: str | None = None,
    summary: str | None = None,
    next_steps: str | None = None,
    files_changed: list[str] | None = None,
    blockers: str | None = None,
    agent: str = "main",
    session_key: str | None = None,
) -> WorkLogEntry:
    """Add an entry to the work log."""
    entry = WorkLogEntry(
        ts=datetime.now(timezone.utc),
        project=project,
        action=action,
        task=task,
        summary=summary,
        next=next_steps,
        files_changed=files_changed,
        blockers=blockers,
        agent=agent,
        session_key=session_key,
    )

    worklog_path = get_worklog_path(config)

    # Ensure parent directory exists
    worklog_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to file
    with open(worklog_path, "a") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")

    return entry


def read_entries(
    config: PortfolioConfig,
    project: str | None = None,
    limit: int | None = None,
) -> list[WorkLogEntry]:
    """Read entries from the work log."""
    worklog_path = get_worklog_path(config)

    if not worklog_path.exists():
        return []

    entries: list[WorkLogEntry] = []

    with open(worklog_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                entry = WorkLogEntry.from_dict(data)

                # Apply project filter
                if project is not None and entry.project != project:
                    continue

                entries.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip malformed entries
                continue

    # Sort by timestamp descending (most recent first)
    entries.sort(key=lambda e: e.ts, reverse=True)

    # Apply limit
    if limit is not None:
        entries = entries[:limit]

    return entries


def get_last_entry(
    config: PortfolioConfig,
    project: str | None = None,
) -> WorkLogEntry | None:
    """Get the most recent work log entry."""
    entries = read_entries(config, project=project, limit=1)
    return entries[0] if entries else None


def tail_entries(
    config: PortfolioConfig,
    project: str | None = None,
    limit: int = 20,
) -> list[WorkLogEntry]:
    """Get the most recent entries (tail)."""
    entries = read_entries(config, project=project, limit=limit)
    # Reverse to show oldest first (like tail)
    return list(reversed(entries))
