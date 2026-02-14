"""Project and portfolio discovery for ClawPM."""

from __future__ import annotations

import os
from pathlib import Path

from .models import PortfolioConfig, ProjectSettings, ProjectStatus


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
