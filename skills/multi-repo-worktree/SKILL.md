---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes `$stageflow:multi-repo-worktree`, links `[$stageflow:multi-repo-worktree](...)`, or explicitly asks to use multi-repo-worktree for a bundle of multiple independent Git repositories. Coordinate help, status, create, recycle, submit, integrate, merge, and sync workflows with read-only inspection and approval-gated Git or GitHub writes. Do not use for ordinary Git, single-repo, or single-worktree requests."
---

# Multi Repo Worktree

Coordinate one logical worktree bundle whose folders belong to multiple independent Git repositories. Treat every repository, branch, upstream, dirty state, and Git operation independently.

## Invocation

Use:

```text
$stageflow:multi-repo-worktree <keyword> [free-form intent]
```

Support only these keywords:

- `help`: explain keywords, required inputs, and safety gates.
- `status`: inspect repositories, worktrees, branches, and blockers.
- `create`: create a derived worktree bundle from confirmed source branches.
- `recycle`: reuse a released fixed slot with a new task branch.
- `submit`: push the current task branch, create/update its regular PR, and record the submitted SHA.
- `integrate`: validate exact-SHA submitted PRs and execute an approved one-shot remote merge batch.
- `merge`: merge derived branches into confirmed source branches.
- `sync`: merge confirmed source branches into derived branches by default.

If the user invokes the skill without a keyword, show help and ask which keyword to use. Normalize legacy `setup`, `merge-back`, and `sync-derived` wording as described in `references/worktree-operations.md`; do not advertise those names.

## Required Inspection

For `status`, `create`, `recycle`, `submit`, `integrate`, `merge`, and `sync`:

1. Read `references/worktree-operations.md` from this skill directory.
2. Resolve `<skill-dir>` as the directory containing this loaded `SKILL.md`; do not assume the current working directory is the plugin root.
3. Run the read-only inspector when a workspace path is available:

```bash
python3 "<skill-dir>/scripts/inspect_worktrees.py" --root "<workspace-root>" --json
```

Use `--bundle "worktrees/<bundle-name>"` when the requested bundle is known. On Windows, use `py -3` instead of `python3` when needed.

Never infer that a workspace root or bundle folder is a Git repository. Trust `git rev-parse` and the inspector's Git-common-directory grouping.

For slot-backed workflows, also read the authoritative local manifest without changing Git:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status
```

For `integrate`, inspect each PR through the read-only exact-SHA helper:

```bash
python3 "<skill-dir>/scripts/inspect_pr_submission.py" \
  --repo "<owner/repo>" --pr "<number-or-url>" --base "<source-branch>"
```

## Ownership And Workflow

Use `create` once, then repeat `recycle → development and validation → submit at the exact SHA`. A successful submit splits into two independent paths:

- The current development owner may release its slot and recycle it for the next independent task without waiting for integration.
- A separate integration session validates and remotely merges the submitted SHA.

The workspace-root `.stageflow-worktrees/slots.json` is authoritative for local slot owner and `active`/`released` state. Only the exact active development owner may record or release it. Integration must not release, claim, recycle, or otherwise mutate a slot manifest or development worktree. GitHub owns source-branch updates in PR mode.

Run `integrate` only from a user-confirmed integration location outside every development bundle, normally the original root repositories. It is a one-shot approved batch, never a daemon or scheduler.

## Branch And Approval Contract

- Treat the source branch as a repo-specific, user-confirmed fact. Git does not record the branch from which another branch was originally created.
- Label a source branch derived only from sibling-worktree evidence as `(추정)`. Never execute a write using an inferred or ambiguous source branch.
- Before any Git write, inspect every participating repo and present the exact repo order, worktree path, source branch, derived branch, dirty state, upstream, operation, commands, and risks.
- Accept approval only after presenting that exact plan. Approval applies only to the displayed batch; re-inspect, explain changes, and ask again if repo scope, branches, commands, strategy, or relevant state changes materially.
- Treat branch creation, worktree creation, merge, rebase, fetch, pull, push, switch, conflict resolution, abort, reset, clean, and branch deletion as Git writes.
- Never reset, clean, force checkout, force push, or delete a branch unless the user explicitly requests that exact operation.

Before a write, use this compact table:

| Repo | Source Branch | Derived Branch | Operation | Dirty | Upstream | Risk |
| --- | --- | --- | --- | --- | --- | --- |

Then show the commands in execution order and ask for explicit approval.

## Operation Rules

- **help**: Explain syntax and examples. Do not inspect unless the user requests an operation.
- **status**: Keep output read-only. When a bundle is identifiable, report only that bundle. Do not use a Markdown table. Show `대상 묶음`, `원본 브랜치`, and `기준 폴더` once, then one repo per line as `<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>`.
- **create**: Confirm every source branch, whether each derived branch is new or existing, and every target path. Never overwrite or silently reuse an existing branch or path.
- **recycle**: Require a released slot, the exact new owner, clean worktrees, no in-progress Git operation, pushed HEADs, and recorded branch/PR identity for the previous task. Re-inspect the complete repo batch before switching or creating task branches. A correction may attach the explicitly confirmed existing PR head branch when it is not checked out elsewhere; otherwise require a new task branch. Never auto-delete old branches or worktrees.
- **submit**: The development owner may push only its own committed task branches. Create or update regular non-Draft PRs, then record each pushed full head with a machine-readable `<!-- stageflow-submitted-sha: <full-head-sha> -->` comment and the branch/PR identity in the slot manifest. Release the slot only after every repo's remote handoff and manifest record succeed. A later head change invalidates the handoff until the current head is submitted again; unrelated PR comments, reviews, or status updates do not invalidate an unchanged submitted SHA.
- **integrate**: First require working `gh` authentication, confirmed GitHub repositories and source bases, and the runtime merge policy and strategy for every repo. Preflight every PR with the read-only helper; verify the PR is open and non-Draft, its current head matches the latest submitted SHA, its base is correct, it has no known merge conflict, and its dependencies are satisfied. After presenting the exact PRs, SHAs, strategy flags, order, and risks and receiving approval, re-inspect and run `gh pr merge "<pr>" --repo "<owner/repo>" --match-head-commit "<sha>" "<confirmed-strategy-flag>"` for direct merge. Do not add `--auto`, `--admin`, or `--delete-branch`. If repository protection blocks the merge, report the blocker and require a later integrate attempt; if the repository requires a merge queue, follow that confirmed policy without treating it as the default. PR mode has no post-merge local push prompt.
- **merge**: Use the worktree where the confirmed source branch is already checked out. Merge one repo at a time and stop on the first failure or conflict. After successful merges, summarize results and ask `push까지 진행할까요?`; never include push in the merge batch.
- **sync**: Bring each confirmed source branch into its derived branch. Default to merge; use rebase only when the user requests it or repository policy requires it. Process one repo at a time and stop on the first failure or conflict.

Run a complete preflight across all repos before the first write. An in-progress Git operation, detached required worktree, ambiguous branch mapping, missing path, or operation-relevant dirty state blocks the whole batch. Missing upstream blocks push or remote synchronization, but does not by itself block local create, merge, or sync.

Independent PRs may be prepared in parallel, but merge a dependent consumer only after its provider is actually merged into the source branch; a merge request or queue admission alone is insufficient. Multi-repo remote operations are not atomic. If some PRs merge or pushes succeed before another fails, report `recovery-required` with completed, failed, and untouched repos and never auto-rollback.

## Status Output

Use this shape:

```text
대상 묶음: worktrees/feature-etc-docs
원본 브랜치: feature-etc (추정)
기준 폴더: /home/kgh-wsl/projects/admin-product-3/worktrees/feature-etc-docs

majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty
majoong_events_web: 폴더 majoong_events_web / 현재 브랜치 feature-etc-docs / 변경상태 dirty
```

Keep `dirty` and `clean` unchanged. Mark inferred source branches with `(추정)`. If repositories have different or uncertain source branches, show `원본 브랜치: 확인 필요` and explain repo-specific evidence separately. Mention upstream, HEAD, locks, prunable worktrees, and in-progress operations only as risk notes when relevant to the requested next action.
