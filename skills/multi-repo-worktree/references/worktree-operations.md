# Worktree Operations

## Setup

Use setup when the user needs Codex to understand a workspace before acting.

1. Find repository roots under the workspace.
2. Group worktrees by Git common directory.
3. Identify source branches and derived branches from user wording, branch names, or `git worktree list`.
4. Record which repositories participate in the bundle.
5. Report repositories that are dirty, detached, missing upstream, or outside the requested bundle.

Never infer that a workspace root is the repo root just because it contains many repo folders.

## Current State

State inspection is read-only. Use:

- `git rev-parse --show-toplevel`
- `git rev-parse --git-common-dir`
- `git branch --show-current`
- `git rev-parse --short HEAD`
- `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
- `git status --porcelain`
- `git worktree list --porcelain`

Summarize each repo independently. If the same branch name appears in several repositories, list each repo and commit separately.

## Worktree Creation

Create worktrees only after user approval.

Required confirmation:

- workspace root
- participating repositories
- source branch per repository
- derived branch per repository
- target bundle folder
- whether the branch should be created from the source branch or use an existing branch
- dirty state and upstream status for each repo

Example shape:

```bash
git -C <repo-main-worktree> worktree add -b <derived-branch> <target-path> <source-branch>
```

If a derived branch already exists, do not overwrite it. Ask whether to attach the existing branch, choose another name, or stop.

## Merge Back To Source

Merge-back means applying a derived branch's completed changes into the creation/source branch for the same repository.

Required confirmation:

- source branch is the branch the derived branch was created from
- derived branch contains the intended changes
- source branch worktree is clean
- derived branch worktree is clean or its changes are intentionally committed
- upstream/push target is understood

Example shape:

```bash
git -C <source-worktree> switch <source-branch>
git -C <source-worktree> merge <derived-branch>
```

If the source branch is checked out in another worktree, use that worktree instead of trying to check it out elsewhere.

## Sync Source Changes Into Derived Branches

Sync-derived means applying source branch updates into a derived branch.

Default to merge unless the user or repo policy chooses rebase.

Example merge shape:

```bash
git -C <derived-worktree> switch <derived-branch>
git -C <derived-worktree> merge <source-branch>
```

For multi-repo bundles, run one repo at a time and stop on conflicts. Do not continue other repositories after a conflict unless the user asks to continue with unaffected repos.

## Approval And Failure Rules

- Ask before any command that writes Git state.
- Stop when a repo has uncommitted changes unless the user approves how to handle them.
- Stop when source and derived branch relationship is unclear.
- Stop when upstream is missing and the requested operation includes push or remote synchronization.
- Report conflicts, skipped repositories, and out-of-scope repositories separately.
