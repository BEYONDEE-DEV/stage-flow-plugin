---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes multi-repo-worktree, $multi-repo-worktree, or asks to use this skill for a multi-repo Git worktree bundle. Coordinates setup, status inspection, worktree creation planning, merge-back from derived branches to their creation/source branches, and syncing creation/source branch changes into derived branches across multiple independent repositories."
---

# Multi Repo Worktree

Use this skill only after the user explicitly names it. Do not apply it implicitly to ordinary Git, single-repo, or single-worktree questions.

This skill is for workspaces where one folder contains multiple independent Git repositories, and each repository may have its own worktrees under a shared bundle directory such as `worktrees/<task-name>/<repo-name>`.

## Core Rules

- Treat each service or package repository as an independent Git repository.
- Do not treat the workspace root or a bundle folder as a Git repository unless `git rev-parse --show-toplevel` proves it.
- Do not assume the same branch name in different repositories refers to the same branch object or commit.
- Before any write operation, summarize the repository list, source branch, derived branch, upstream, dirty state, and intended operation for user confirmation.
- Do not run destructive commands such as reset, clean, forced checkout, forced push, or branch deletion unless the user explicitly requests that exact operation.
- Prefer merge for branch update examples unless the user explicitly asks for rebase or the repository policy requires it.

## Required First Step

For setup, status, worktree creation, merge-back, or sync-derived requests:

1. Read `references/worktree-operations.md`.
2. Run the read-only inspector when a workspace path is available:

```bash
python skills/multi-repo-worktree/scripts/inspect_worktrees.py --root <workspace-root>
```

Use `--json` when structured output is easier to compare.

## Operation Model

- **Setup**: identify repository groups, main worktrees, derived worktrees, branch naming pattern, and upstream availability.
- **Current state**: report repo-by-repo branch, commit, upstream, dirty state, and worktree paths.
- **Worktree creation**: plan repo-by-repo `git worktree add` commands from a confirmed source branch to a confirmed derived branch and target folder. Ask before running write commands.
- **Merge-back**: merge a derived branch into its creation/source branch repo by repo. Confirm source branch, derived branch, clean state, and conflict strategy first.
- **Sync-derived**: bring creation/source branch changes into each derived branch repo by repo. Confirm merge vs rebase first; default to merge examples.

## Safety Boundaries

- This skill is not for single-repo-only tasks.
- The bundled inspector is read-only; it must not create branches, create worktrees, merge, rebase, pull, fetch, push, reset, or clean.
- If a repository is dirty, paused by hooks, missing upstream, detached, or ambiguous, stop and explain the blocker before proposing write commands.
- If the user asks for batch execution across repositories, present the exact repo list and operation order before executing.

## User-Facing Summary

Before any write operation, show a compact table:

| Repo | Source Branch | Derived Branch | Operation | Dirty | Upstream | Risk |
| --- | --- | --- | --- | --- | --- | --- |

Then ask for explicit approval. Keep internal Git terms only where they identify exact branches, paths, or commands.
