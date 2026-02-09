"""Tests for subtask functionality."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from clawpm.discovery import load_portfolio_config, discover_projects, get_project
from clawpm.models import PortfolioConfig, TaskState
from clawpm.tasks import list_tasks, get_task, add_task, change_task_state


@pytest.fixture
def temp_portfolio():
    """Create a temporary portfolio with a test project."""
    temp_dir = tempfile.mkdtemp(prefix="clawpm_test_")
    portfolio_root = Path(temp_dir)
    
    # Create portfolio structure
    (portfolio_root / "portfolio.toml").write_text(f'''
portfolio_root = "{portfolio_root}"
project_roots = ["{portfolio_root}/projects"]

[defaults]
status = "active"
''')
    
    # Create projects directory
    projects_dir = portfolio_root / "projects"
    projects_dir.mkdir()
    
    # Create a test project
    project_dir = projects_dir / "test-project"
    project_dir.mkdir()
    project_meta = project_dir / ".project"
    project_meta.mkdir()
    
    (project_meta / "settings.toml").write_text('''
id = "test"
name = "Test Project"
status = "active"
priority = 3
''')
    
    # Create tasks directory
    tasks_dir = project_meta / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "done").mkdir()
    (tasks_dir / "blocked").mkdir()
    
    # Set environment variable to use this portfolio
    old_env = os.environ.get("CLAWPM_PORTFOLIO")
    os.environ["CLAWPM_PORTFOLIO"] = str(portfolio_root)
    
    yield {
        "root": portfolio_root,
        "project_dir": project_dir,
        "tasks_dir": tasks_dir,
        "config": load_portfolio_config(portfolio_root),
    }
    
    # Cleanup
    if old_env:
        os.environ["CLAWPM_PORTFOLIO"] = old_env
    else:
        os.environ.pop("CLAWPM_PORTFOLIO", None)
    shutil.rmtree(temp_dir)


class TestTaskBasics:
    """Test basic task operations."""
    
    def test_add_task(self, temp_portfolio):
        """Test adding a regular task."""
        config = temp_portfolio["config"]
        
        task = add_task(config, "test", "Test task title", priority=2)
        
        assert task is not None
        assert task.id == "TEST-000"
        assert task.title == "Test task title"
        assert task.state == TaskState.OPEN
        assert task.priority == 2
        assert task.parent is None
        assert task.children == []
    
    def test_task_state_changes(self, temp_portfolio):
        """Test task state transitions."""
        config = temp_portfolio["config"]
        
        task = add_task(config, "test", "State test task")
        assert task.state == TaskState.OPEN
        
        # Move to progress
        task = change_task_state(config, "test", task.id, TaskState.PROGRESS)
        assert task.state == TaskState.PROGRESS
        
        # Move to done
        task = change_task_state(config, "test", task.id, TaskState.DONE)
        assert task.state == TaskState.DONE
        
        # Verify file is in done/
        assert "done" in task.file_path.parts


class TestSubtaskDiscovery:
    """Test subtask discovery from directory structure."""
    
    def test_discover_parent_task(self, temp_portfolio):
        """Test that _task.md in a directory is discovered as parent."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create parent task directory
        parent_dir = tasks_dir / "TEST-001"
        parent_dir.mkdir()
        (parent_dir / "_task.md").write_text('''---
id: TEST-001
priority: 2
created: '2026-02-08'
---
# Parent task

This is a parent task.
''')
        
        task = get_task(config, "test", "TEST-001")
        
        assert task is not None
        assert task.id == "TEST-001"
        assert task.is_parent  # Directory-based task
        assert task.file_path.name == "_task.md"
    
    def test_discover_subtasks(self, temp_portfolio):
        """Test that subtasks in parent directory are discovered."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create parent task directory with subtasks
        parent_dir = tasks_dir / "TEST-001"
        parent_dir.mkdir()
        (parent_dir / "_task.md").write_text('''---
id: TEST-001
priority: 2
---
# Parent task
''')
        (parent_dir / "TEST-001-001.md").write_text('''---
id: TEST-001-001
priority: 3
parent: TEST-001
---
# First subtask
''')
        (parent_dir / "TEST-001-002.md").write_text('''---
id: TEST-001-002
priority: 3
parent: TEST-001
---
# Second subtask
''')
        
        # Get parent and check children populated
        parent = get_task(config, "test", "TEST-001")
        assert parent is not None
        assert parent.is_parent
        assert "TEST-001-001" in parent.children
        assert "TEST-001-002" in parent.children
        
        # Get subtask directly
        subtask = get_task(config, "test", "TEST-001-001")
        assert subtask is not None
        assert subtask.parent == "TEST-001"
        assert not subtask.is_parent
    
    def test_list_shows_hierarchy(self, temp_portfolio):
        """Test that list_tasks populates parent-child relationships."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create parent with subtask
        parent_dir = tasks_dir / "TEST-001"
        parent_dir.mkdir()
        (parent_dir / "_task.md").write_text('''---
id: TEST-001
priority: 2
---
# Parent task
''')
        (parent_dir / "TEST-001-001.md").write_text('''---
id: TEST-001-001
parent: TEST-001
---
# Subtask
''')
        
        tasks = list_tasks(config, "test")
        task_map = {t.id: t for t in tasks}
        
        assert "TEST-001" in task_map
        assert "TEST-001-001" in task_map
        assert "TEST-001-001" in task_map["TEST-001"].children
        assert task_map["TEST-001-001"].parent == "TEST-001"
    
    def test_subtask_in_done_directory(self, temp_portfolio):
        """Test that subtasks in done/PARENT/ are discovered correctly."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create completed parent with subtasks in done/
        done_parent = tasks_dir / "done" / "TEST-001"
        done_parent.mkdir(parents=True)
        (done_parent / "_task.md").write_text('''---
id: TEST-001
priority: 2
---
# Completed parent
''')
        (done_parent / "TEST-001-001.md").write_text('''---
id: TEST-001-001
parent: TEST-001
---
# Completed subtask
''')
        
        parent = get_task(config, "test", "TEST-001")
        assert parent is not None
        assert parent.state == TaskState.DONE
        assert "TEST-001-001" in parent.children
        
        subtask = get_task(config, "test", "TEST-001-001")
        assert subtask is not None
        assert subtask.state == TaskState.DONE
        assert subtask.parent == "TEST-001"


class TestParentChildRelationships:
    """Test parent-child relationship behavior."""
    
    def test_parent_from_frontmatter(self, temp_portfolio):
        """Test that parent field is read from frontmatter."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create regular task with parent field (not in directory)
        (tasks_dir / "TEST-001.md").write_text('''---
id: TEST-001
priority: 2
---
# Parent task
''')
        (tasks_dir / "TEST-002.md").write_text('''---
id: TEST-002
parent: TEST-001
---
# Child task (flat file with parent field)
''')
        
        tasks = list_tasks(config, "test")
        task_map = {t.id: t for t in tasks}
        
        # Parent should have child in children list
        assert "TEST-002" in task_map["TEST-001"].children
        assert task_map["TEST-002"].parent == "TEST-001"


class TestTaskSplit:
    """Test tasks split command."""
    
    def test_split_regular_task(self, temp_portfolio):
        """Test splitting a regular task into directory structure."""
        config = temp_portfolio["config"]
        
        # Create a regular task
        task = add_task(config, "test", "Task to split", priority=2)
        assert task.file_path.name == "TEST-000.md"
        assert not task.is_parent
        
        # Import and use split
        from clawpm.tasks import split_task
        split = split_task(config, "test", task.id)
        
        assert split is not None
        assert split.file_path.name == "_task.md"
        assert split.file_path.parent.name == "TEST-000"
        assert split.is_parent
        assert split.title == "Task to split"
    
    def test_split_already_directory(self, temp_portfolio):
        """Test that splitting an already-split task is a no-op."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create directory-based task
        parent_dir = tasks_dir / "TEST-001"
        parent_dir.mkdir()
        (parent_dir / "_task.md").write_text('''---
id: TEST-001
---
# Already split
''')
        
        from clawpm.tasks import split_task
        task = split_task(config, "test", "TEST-001")
        
        assert task is not None
        assert task.file_path.name == "_task.md"
    
    def test_split_in_done_directory(self, temp_portfolio):
        """Test splitting a task that's in done/ directory."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create done task
        (tasks_dir / "done" / "TEST-001.md").write_text('''---
id: TEST-001
---
# Completed task
''')
        
        from clawpm.tasks import split_task
        task = split_task(config, "test", "TEST-001")
        
        assert task is not None
        assert task.file_path.name == "_task.md"
        assert "done" in task.file_path.parts
        assert task.state == TaskState.DONE


class TestAddSubtask:
    """Test adding subtasks with --parent."""
    
    def test_add_subtask_auto_splits_parent(self, temp_portfolio):
        """Test that adding subtask auto-splits parent if needed."""
        config = temp_portfolio["config"]
        
        # Create regular parent task
        parent = add_task(config, "test", "Parent task")
        assert parent.file_path.name == "TEST-000.md"
        
        # Add subtask
        from clawpm.tasks import add_subtask
        subtask = add_subtask(config, "test", parent.id, "First subtask")
        
        assert subtask is not None
        assert subtask.id == "TEST-000-001"
        assert subtask.parent == "TEST-000"
        assert "TEST-000" in subtask.file_path.parts
        
        # Verify parent was split
        parent = get_task(config, "test", "TEST-000")
        assert parent.file_path.name == "_task.md"
        assert subtask.id in parent.children
    
    def test_add_multiple_subtasks(self, temp_portfolio):
        """Test adding multiple subtasks gets sequential IDs."""
        config = temp_portfolio["config"]
        
        parent = add_task(config, "test", "Parent task")
        
        from clawpm.tasks import add_subtask
        sub1 = add_subtask(config, "test", parent.id, "Subtask 1")
        sub2 = add_subtask(config, "test", parent.id, "Subtask 2")
        sub3 = add_subtask(config, "test", parent.id, "Subtask 3")
        
        assert sub1.id == "TEST-000-001"
        assert sub2.id == "TEST-000-002"
        assert sub3.id == "TEST-000-003"
        
        parent = get_task(config, "test", "TEST-000")
        assert len(parent.children) == 3
    
    def test_add_subtask_to_existing_directory(self, temp_portfolio):
        """Test adding subtask to already-split parent."""
        tasks_dir = temp_portfolio["tasks_dir"]
        config = temp_portfolio["config"]
        
        # Create directory-based parent
        parent_dir = tasks_dir / "TEST-001"
        parent_dir.mkdir()
        (parent_dir / "_task.md").write_text('''---
id: TEST-001
---
# Existing parent
''')
        (parent_dir / "TEST-001-001.md").write_text('''---
id: TEST-001-001
parent: TEST-001
---
# Existing subtask
''')
        
        from clawpm.tasks import add_subtask
        new_sub = add_subtask(config, "test", "TEST-001", "New subtask")
        
        # Should get next sequential ID
        assert new_sub.id == "TEST-001-002"
        assert new_sub.parent == "TEST-001"


# TODO: Add tests for Phase 3 features
# class TestSubtaskStateMovement:
#     """Test that subtasks move with parent."""
#     pass

# class TestParentCompletionBlocking:
#     """Test that parent can't complete with incomplete subtasks."""
#     pass
