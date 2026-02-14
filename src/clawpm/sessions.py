"""Extract and index OpenClaw session transcripts containing clawpm tool calls."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


OPENCLAW_SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
DEFAULT_OUTPUT_LIMIT = 500  # truncate tool outputs to N chars


@dataclass
class SessionIndex:
    """Tracks which sessions have been extracted."""

    session_id: str
    extracted_at: str
    session_start: str
    entry_count: int
    clawpm_call_count: int
    total_tool_calls: int

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "extracted_at": self.extracted_at,
            "session_start": self.session_start,
            "entry_count": self.entry_count,
            "clawpm_call_count": self.clawpm_call_count,
            "total_tool_calls": self.total_tool_calls,
        }


def get_sessions_dir() -> Path | None:
    """Find the OpenClaw sessions directory."""
    if OPENCLAW_SESSIONS_DIR.is_dir():
        return OPENCLAW_SESSIONS_DIR
    return None


def load_index(index_path: Path) -> dict[str, SessionIndex]:
    """Load the extraction index. Returns {session_id: SessionIndex}."""
    if not index_path.exists():
        return {}

    result = {}
    with open(index_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                result[data["session_id"]] = SessionIndex(**data)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return result


def write_index(index_path: Path, entries: dict[str, SessionIndex]) -> None:
    """Write the full index file (overwrites)."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w") as f:
        for entry in entries.values():
            f.write(json.dumps(entry.to_dict()) + "\n")


def get_processed_ids(output_dir: Path) -> set[str]:
    """Get session IDs from the processed/ subdirectory."""
    processed_dir = output_dir / "processed"
    if not processed_dir.is_dir():
        return set()
    ids = set()
    for f in processed_dir.glob("*.jsonl"):
        ids.add(f.stem)
    return ids


def find_clawpm_sessions(sessions_dir: Path) -> list[Path]:
    """Find all session JSONL files that contain clawpm references."""
    results = []
    for f in sorted(sessions_dir.glob("*.jsonl")):
        if f.name == "sessions.json":
            continue
        try:
            text = f.read_text()
            if "clawpm" in text:
                results.append(f)
        except OSError:
            continue
    return results


def _linearize_entry(entry: dict, output_limit: int) -> list[dict]:
    """Convert a raw JSONL entry into linearized transcript entries."""
    results = []

    if entry.get("type") == "session":
        results.append({
            "type": "session",
            "id": entry.get("id"),
            "timestamp": entry.get("timestamp"),
            "cwd": entry.get("cwd"),
        })

    elif entry.get("type") == "message":
        msg = entry.get("message", {})
        role = msg.get("role", "")
        ts = msg.get("timestamp", 0)

        if role == "user":
            texts = [
                c.get("text", "")
                for c in msg.get("content", [])
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            if texts:
                results.append({
                    "type": "user",
                    "seq": ts,
                    "text": "\n".join(texts),
                })

        elif role == "assistant":
            for block in msg.get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    results.append({
                        "type": "assistant",
                        "seq": ts,
                        "text": block.get("text", ""),
                    })
                elif block.get("type") == "toolCall":
                    results.append({
                        "type": "tool_call",
                        "seq": ts,
                        "tool": block.get("name", ""),
                        "id": block.get("id", ""),
                        "args": block.get("arguments", {}),
                    })

        elif role == "toolResult":
            content = msg.get("content", [])
            output_text = ""
            if content and isinstance(content, list) and len(content) > 0:
                first = content[0]
                if isinstance(first, dict):
                    output_text = first.get("text", "")

            results.append({
                "type": "tool_result",
                "seq": ts,
                "tool": msg.get("toolName", ""),
                "id": msg.get("toolCallId", ""),
                "is_error": msg.get("isError", False),
                "output": output_text[:output_limit] if output_text else "",
            })

    return results


def extract_session(
    session_path: Path,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
) -> tuple[list[dict], dict]:
    """Extract and linearize a session transcript.

    Returns (entries, stats) where stats has counts.
    """
    entries = []
    clawpm_call_count = 0
    total_tool_calls = 0
    session_start = ""

    with open(session_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            linearized = _linearize_entry(raw, output_limit)
            for entry in linearized:
                entries.append(entry)

                if entry.get("type") == "session":
                    session_start = entry.get("timestamp", "")

                if entry.get("type") == "tool_call":
                    total_tool_calls += 1
                    if entry.get("tool") == "exec":
                        cmd = entry.get("args", {}).get("command", "")
                        if "clawpm" in str(cmd):
                            clawpm_call_count += 1

    stats = {
        "entry_count": len(entries),
        "clawpm_call_count": clawpm_call_count,
        "total_tool_calls": total_tool_calls,
        "session_start": session_start,
    }
    return entries, stats


def entries_to_markdown(entries: list[dict]) -> str:
    """Convert linearized entries to readable markdown."""
    lines = []

    for entry in entries:
        etype = entry.get("type", "")

        if etype == "session":
            lines.append(f"# Session {entry.get('id', '?')}")
            lines.append(f"**Started**: {entry.get('timestamp', '?')}")
            if entry.get("cwd"):
                lines.append(f"**CWD**: {entry['cwd']}")
            lines.append("")
            lines.append("---")
            lines.append("")

        elif etype == "user":
            lines.append("## User")
            lines.append("")
            lines.append(entry.get("text", ""))
            lines.append("")

        elif etype == "assistant":
            lines.append("## Assistant")
            lines.append("")
            lines.append(entry.get("text", ""))
            lines.append("")

        elif etype == "tool_call":
            tool = entry.get("tool", "?")
            args = entry.get("args", {})

            if tool == "exec":
                cmd = args.get("command", "")
                lines.append(f"### exec")
                lines.append("")
                lines.append("```bash")
                lines.append(cmd)
                lines.append("```")
                lines.append("")
            elif tool == "read":
                lines.append(f"### read `{args.get('path', '?')}`")
                lines.append("")
            elif tool == "write":
                lines.append(f"### write `{args.get('path', '?')}`")
                lines.append("")
            else:
                args_str = json.dumps(args)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."
                lines.append(f"### {tool}")
                lines.append("")
                lines.append("```json")
                lines.append(args_str)
                lines.append("```")
                lines.append("")

        elif etype == "tool_result":
            output = entry.get("output", "")
            is_error = entry.get("is_error", False)
            tool = entry.get("tool", "?")

            if is_error:
                lines.append(f"**ERROR** ({tool}):")
                lines.append("")
                lines.append("```")
                lines.append(output)
                lines.append("```")
                lines.append("")
            elif output:
                lines.append(f"<details><summary>{tool} result</summary>")
                lines.append("")
                lines.append("```")
                lines.append(output)
                lines.append("```")
                lines.append("")
                lines.append("</details>")
                lines.append("")

    return "\n".join(lines)


def extract_all(
    output_dir: Path,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
    force: bool = False,
) -> list[dict]:
    """Extract all clawpm sessions to output_dir.

    Returns list of extraction results (one per session).
    """
    sessions_dir = get_sessions_dir()
    if not sessions_dir:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.jsonl"

    # Load existing index to skip already-extracted sessions
    existing = load_index(index_path)

    # Also skip sessions already in processed/
    processed_ids = get_processed_ids(output_dir)

    # Find sessions with clawpm references
    session_files = find_clawpm_sessions(sessions_dir)

    results = []
    dirty = False  # track whether index needs rewriting

    for session_path in session_files:
        session_id = session_path.stem

        # Skip if already processed (moved to processed/ dir)
        if session_id in processed_ids and not force:
            results.append({
                "session_id": session_id,
                "status": "skipped",
                "reason": "already_processed",
            })
            continue

        # Skip if already extracted (unless force)
        if session_id in existing and not force:
            results.append({
                "session_id": session_id,
                "status": "skipped",
                "reason": "already_extracted",
            })
            continue

        # Extract
        entries, stats = extract_session(session_path, output_limit)

        # Skip sessions with no actual clawpm exec calls
        if stats["clawpm_call_count"] == 0:
            continue

        # Write JSONL
        jsonl_path = output_dir / f"{session_id}.jsonl"
        with open(jsonl_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Write markdown
        md_path = output_dir / f"{session_id}.md"
        md_content = entries_to_markdown(entries)
        md_path.write_text(md_content)

        # Update index in memory
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        idx = SessionIndex(
            session_id=session_id,
            extracted_at=now,
            session_start=stats["session_start"],
            entry_count=stats["entry_count"],
            clawpm_call_count=stats["clawpm_call_count"],
            total_tool_calls=stats["total_tool_calls"],
        )
        existing[session_id] = idx
        dirty = True

        results.append({
            "session_id": session_id,
            "status": "extracted",
            "session_start": stats["session_start"],
            "entry_count": stats["entry_count"],
            "clawpm_calls": stats["clawpm_call_count"],
            "total_tool_calls": stats["total_tool_calls"],
            "files": [str(jsonl_path), str(md_path)],
        })

    # Write index once at the end (deduped)
    if dirty:
        write_index(index_path, existing)

    return results
