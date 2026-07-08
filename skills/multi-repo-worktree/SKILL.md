---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes multi-repo-worktree, $multi-repo-worktree, or asks to use this skill for a multi-repo Git worktree bundle. Coordinates keyword-based help, status, create, merge, and sync workflows across multiple independent repositories, requiring explanation and explicit user approval before create, merge, or sync commands are executed."
---

# Multi Repo Worktree

Use this skill only after the user explicitly names it. Do not apply it implicitly to ordinary Git, single-repo, or single-worktree questions.

This skill is for workspaces where one folder contains multiple independent Git repositories, and each repository may have its own worktrees under a shared bundle directory such as `worktrees/<task-name>/<repo-name>`.

## Core Rules

- Treat each service or package repository as an independent Git repository.
- Do not treat the workspace root or a bundle folder as a Git repository unless `git rev-parse --show-toplevel` proves it.
- Do not assume the same branch name in different repositories refers to the same branch object or commit.
- Treat creation/source branches as the branches derived branches were created from.
- Before any write operation, summarize the repository list, source branch, derived branch, upstream, dirty state, and intended operation for user confirmation.
- Never execute `create`, `merge`, or `sync` commands before explaining the exact plan and receiving explicit user approval.
- Do not run destructive commands such as reset, clean, forced checkout, forced push, or branch deletion unless the user explicitly requests that exact operation.
- Prefer merge for branch update examples unless the user explicitly asks for rebase or the repository policy requires it.

## Invocation Keywords

Use this shape:

```text
$multi-repo-worktree <keyword> [free-form intent]
```

Supported keywords:

- `help`: explain available keywords, required inputs, and safety rules.
- `status`: inspect workspace, repository, worktree, branch, and dirty state.
- `create`: create or plan a derived worktree bundle from a source branch.
- `merge`: merge derived branch changes back into the creation/source branch.
- `sync`: bring creation/source branch changes into derived branches.

If the user explicitly invokes the skill without a keyword, show `help` and ask which keyword to use.

## Required First Step

For `status`, `create`, `merge`, or `sync` requests:

1. Read `references/worktree-operations.md`.
2. Run the read-only inspector when a workspace path is available:

```bash
python skills/multi-repo-worktree/scripts/inspect_worktrees.py --root <workspace-root>
```

Use `--json` when structured output is easier to compare.

## Operation Model

- **help**: explain the keyword syntax and show examples. Do not inspect or mutate repositories unless the user asks for a specific operation.
- **status**: identify repository groups, main worktrees, derived worktrees, branch naming pattern, dirty state, and worktree paths. User-facing status output must not use Markdown tables. Show the common bundle path once as `기준 폴더`, then render each repo as one line: `<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>`.
- **create**: plan repo-by-repo `git worktree add` commands from a confirmed source branch to a confirmed derived branch and target folder. Explain the plan and ask for approval before running write commands.
- **merge**: merge a derived branch into its creation/source branch repo by repo. Explain source branch, derived branch, command order, clean state, upstream, and conflict strategy; ask for approval before running write commands.
- **sync**: bring creation/source branch changes into each derived branch repo by repo. Explain merge vs rebase strategy, command order, clean state, and conflict strategy; ask for approval before running write commands.

## Safety Boundaries

- This skill is not for single-repo-only tasks.
- The bundled inspector is read-only; it must not create branches, create worktrees, merge, rebase, pull, fetch, push, reset, or clean.
- `create`, `merge`, and `sync` are approval-gated operations. Showing a plan is allowed; executing the Git writes requires explicit approval after the explanation.
- If a repository is dirty, paused by hooks, missing upstream, detached, or ambiguous, stop and explain the blocker before proposing write commands.
- If the user asks for batch execution across repositories, present the exact repo list and operation order before executing.

## User-Facing Summary

For `status`, use this shape:

```text
대상 묶음: worktrees/feature-etc-docs
원본 브랜치: feature-etc (추정)
기준 폴더: /home/kgh-wsl/projects/admin-product-3/worktrees/feature-etc-docs

majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty
majoong_events_web: 폴더 majoong_events_web / 현재 브랜치 feature-etc-docs / 변경상태 dirty
```

Do not print extra workspace or repository-count headers before this block. Keep `dirty` and `clean` unchanged. If the source branch is inferred from sibling worktrees rather than explicit user input, mark it with `(추정)`. Mention upstream only as a risk note when it affects the requested next action.

Before any write operation, show a compact table:

| Repo | Source Branch | Derived Branch | Operation | Dirty | Upstream | Risk |
| --- | --- | --- | --- | --- | --- | --- |

Then ask for explicit approval. Keep internal Git terms only where they identify exact branches, paths, or commands.
