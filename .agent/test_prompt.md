# ClawPM Agent Smoke Test

You are validating that ClawPM works correctly by using it as a real agent would. Your **only reference** for how to use ClawPM is the skill documentation.

## Before You Start

1. **Load the skill:** Read `skills/clawpm/SKILL.md` in this repo. That is your sole reference for all ClawPM commands. Do not guess flags or syntax — if the skill doesn't document it, that's a finding.
2. **Create a test project:** Make a new directory at `~/Development/clawpm-test`, initialize it as a git repo, and work from there for the rest of the test.

## Phase 1: Project Setup

Using ClawPM from inside your test project directory:
- Quick-add a task called "Initial setup". This should auto-initialize the project.
- Verify the project was created (check for `.project/` directory)
- List all projects in the portfolio — your test project should appear
- Check the project status

## Phase 2: Task Management

- Add 3-4 tasks with different priorities and complexities (mix of small, medium, large)
- Add one task with a body/description, not just a title
- List all tasks
- Show the details of a specific task
- Edit a task — change its priority or title
- Try listing in both JSON and human-readable formats

## Phase 3: Task Lifecycle

- Start working on a task (mark it in-progress)
- Block a different task with a reason
- Unblock that task
- Complete the in-progress task with a note
- List tasks filtered by state (e.g. only done, only open, all)
- Verify the work log captured these state changes

## Phase 4: Subtasks

- Add subtasks to one of the remaining open tasks
- List tasks and check the hierarchy is visible
- Try to complete the parent while subtasks are still open
- Complete the subtasks, then the parent

## Phase 5: Work Log

- Manually log a progress entry against a task
- View the recent log — it should only show entries for your test project
- View the log across all projects
- View the single most recent entry
- Make a couple of git commits in the test repo (include a task ID in one commit message)
- Use the commit logging feature to pull git commits into the work log
- Run it again — duplicates should be skipped
- Try a dry-run first to preview

## Phase 6: Context & Navigation

- Get the full agent context for your project
- Get the next recommended task
- Try both JSON and text output for context

## Phase 7: Research & Issues

- Add a research entry (pick an appropriate type)
- List research entries
- Log a test issue against the project
- List issues

## Phase 8: Cross-Project

- Access a different project (e.g. `clawpm` itself) by name while still in your test directory
- Get the next task across all projects in the portfolio

## Phase 9: Output & Error Handling

Throughout all phases, also check:
- Pipe JSON output through a JSON parser to verify it's valid
- Try text mode for key commands — is it readable?
- Try a command with a nonexistent project or task ID — are errors helpful?
- Check that stderr hints ("Using project: ...") only appear in text mode, not JSON

## Cleanup

Remove the test project directory and note how many work log entries were created.

## Reporting

Summarize your findings:

```
## Results
- Phases completed: N/9
- Commands tested: N
- Issues found: N (list each)
- SKILL.md accurate: yes/no (note any mismatches between docs and actual behavior)
- UX observations: (anything that felt unintuitive or broken)
```

If you find bugs or SKILL.md mismatches, log them using ClawPM's issue tracking against the `clawpm` project. If a fix is straightforward, apply it in `src/clawpm/` and re-test.
