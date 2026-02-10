"""Project and portfolio discovery for ClawPM."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import PortfolioConfig, ProjectSettings, ProjectStatus


@dataclass
class UntrackedRepo:
    """A git repo without .project/ tracking."""
    
    path: Path
    name: str
    remote: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "name": self.name,
            "remote": self.remote,
            "tracked": False,
        }


def get_portfolio_path() -> Path | None:
    """Get the portfolio path from default location or environment override."""
    # Default location: ~/clawpm
    default = Path.home() / "clawpm"
    if (default / "portfolio.toml").exists():
        return default

    # Allow environment override (useful for testing)
    if env_path := os.environ.get("CLAWPM_PORTFOLIO"):
        path = Path(env_path).expanduser()
        if (path / "portfolio.toml").exists():
            return path

    return None


def load_portfolio_config(portfolio_path: Path | None = None) -> PortfolioConfig | None:
    """Load portfolio configuration."""
    if portfolio_path is None:
        portfolio_path = get_portfolio_path()

    if portfolio_path is None:
        return None

    config_file = portfolio_path / "portfolio.toml"
    if not config_file.exists():
        return None

    return PortfolioConfig.load(config_file)


def discover_projects(
    config: PortfolioConfig,
    status_filter: ProjectStatus | None = None,
) -> list[ProjectSettings]:
    """Discover all projects in configured roots."""
    projects: list[ProjectSettings] = []

    for root in config.project_roots:
        if not root.exists():
            continue

        # Skip OpenClaw workspace if configured
        if config.openclaw_workspace and root == config.openclaw_workspace:
            continue

        # Look for .project/settings.toml in immediate subdirectories
        for item in root.iterdir():
            if not item.is_dir():
                continue

            settings_file = item / ".project" / "settings.toml"
            if settings_file.exists():
                try:
                    project = ProjectSettings.load(settings_file)

                    # Apply status filter
                    if status_filter is not None and project.status != status_filter:
                        continue

                    projects.append(project)
                except Exception:
                    # Skip malformed projects
                    continue

    # Sort by priority (lower is higher priority), then by name
    projects.sort(key=lambda p: (p.priority, p.name))

    return projects


def get_project(config: PortfolioConfig, project_id: str) -> ProjectSettings | None:
    """Get a specific project by ID."""
    for root in config.project_roots:
        if not root.exists():
            continue

        # Check direct match first
        direct = root / project_id / ".project" / "settings.toml"
        if direct.exists():
            try:
                return ProjectSettings.load(direct)
            except Exception:
                pass

        # Search all projects
        for item in root.iterdir():
            if not item.is_dir():
                continue

            settings_file = item / ".project" / "settings.toml"
            if settings_file.exists():
                try:
                    project = ProjectSettings.load(settings_file)
                    if project.id == project_id:
                        return project
                except Exception:
                    continue

    return None


def get_project_dir(config: PortfolioConfig, project_id: str) -> Path | None:
    """Get the .project directory for a project."""
    project = get_project(config, project_id)
    if project and project.project_dir:
        return project.project_dir / ".project"
    return None


def discover_untracked_repos(config: PortfolioConfig) -> list[UntrackedRepo]:
    """Discover git repos in project_roots that don't have .project/ tracking."""
    untracked: list[UntrackedRepo] = []
    
    # Get IDs of tracked projects to exclude
    tracked_paths = set()
    for root in config.project_roots:
        if not root.exists():
            continue
        for item in root.iterdir():
            if not item.is_dir():
                continue
            if (item / ".project" / "settings.toml").exists():
                tracked_paths.add(item.resolve())
    
    # Find git repos without .project/
    for root in config.project_roots:
        if not root.exists():
            continue
        
        # Skip OpenClaw workspace
        if config.openclaw_workspace and root == config.openclaw_workspace:
            continue
        
        for item in root.iterdir():
            if not item.is_dir():
                continue
            
            # Skip if already tracked
            if item.resolve() in tracked_paths:
                continue
            
            # Check if it's a git repo
            if not (item / ".git").exists():
                continue
            
            # Get remote URL if available
            remote = None
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=item,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    remote = result.stdout.strip()
            except Exception:
                pass
            
            untracked.append(UntrackedRepo(
                path=item,
                name=item.name,
                remote=remote,
            ))
    
    # Sort by name
    untracked.sort(key=lambda r: r.name)
    
    return untracked


def is_git_repo(path: Path) -> bool:
    """Check if a path is a git repository."""
    return (path / ".git").exists()


def init_project_from_repo(repo_path: Path, project_id: str | None = None) -> ProjectSettings | None:
    """Initialize a .project/ structure in a git repo.
    
    Auto-detects project name from directory and remote.
    Returns the created ProjectSettings.
    """
    if not repo_path.is_dir():
        return None
    
    # Generate project ID from directory name if not provided
    if not project_id:
        project_id = repo_path.name.lower().replace(" ", "-").replace("_", "-")
    
    # Generate project name from directory or remote
    project_name = repo_path.name
    
    # Try to get a better name from git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote = result.stdout.strip()
            # Extract repo name from remote URL
            # e.g., git@github.com:user/repo.git -> repo
            # or https://github.com/user/repo.git -> repo
            if "/" in remote:
                name = remote.split("/")[-1]
                if name.endswith(".git"):
                    name = name[:-4]
                project_name = name
    except Exception:
        pass
    
    # Create .project directory structure
    project_dir = repo_path / ".project"
    project_dir.mkdir(exist_ok=True)
    
    tasks_dir = project_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "done").mkdir(exist_ok=True)
    (tasks_dir / "blocked").mkdir(exist_ok=True)
    
    (project_dir / "research").mkdir(exist_ok=True)
    (project_dir / "notes").mkdir(exist_ok=True)
    
    # Write settings.toml
    settings_content = f'''id = "{project_id}"
name = "{project_name}"
status = "active"
priority = 5
repo_path = "{repo_path}"
'''
    (project_dir / "settings.toml").write_text(settings_content)
    
    # Create minimal SPEC.md
    spec_content = f'''# {project_name}

## Purpose

(Describe the purpose of this project)

## Goals

- (Add goals)

## Notes

Auto-initialized by clawpm from git repo.
'''
    (project_dir / "SPEC.md").write_text(spec_content)
    
    # Create learnings.md
    (project_dir / "learnings.md").write_text(f"# Learnings - {project_name}\n\n")
    
    # Load and return the project
    return ProjectSettings.load(project_dir / "settings.toml")


def validate_portfolio(config: PortfolioConfig) -> list[str]:
    """Validate portfolio configuration and return issues."""
    issues: list[str] = []

    # Check portfolio root exists
    if not config.portfolio_root.exists():
        issues.append(f"Portfolio root does not exist: {config.portfolio_root}")

    # Check project roots exist
    for root in config.project_roots:
        if not root.exists():
            issues.append(f"Project root does not exist: {root}")

    # Check for OpenClaw workspace collision
    if config.openclaw_workspace:
        for root in config.project_roots:
            try:
                if root.resolve() == config.openclaw_workspace.resolve():
                    issues.append(
                        f"Project root overlaps with OpenClaw workspace: {root}"
                    )
                elif config.openclaw_workspace.resolve() in root.resolve().parents:
                    issues.append(
                        f"Project root is inside OpenClaw workspace: {root}"
                    )
            except Exception:
                pass

    # Check work log exists
    work_log = config.portfolio_root / "work_log.jsonl"
    if not work_log.exists():
        issues.append(f"Work log does not exist: {work_log}")

    return issues
