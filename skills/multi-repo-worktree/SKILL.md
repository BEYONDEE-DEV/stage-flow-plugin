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
- `submit`: push the current task branch and create/update its Draft or Ready PR.
- `integrate`: validate exact-SHA Ready PRs and enqueue an approved one-shot integration batch.
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
python3 "<skill-dir>/scripts/inspect_pr_readiness.py" \
  --repo "<owner/repo>" --pr "<number-or-url>" --base "<source-branch>"
```

## Ownership And Workflow

Use `create` once, then repeat `recycle → development → submit Draft → development/test → submit Ready`. Ready splits into two independent paths:

- The current development owner may release its slot and recycle it for the next independent task without waiting for integration.
- A separate integration session validates and queues the immutable Ready SHA.

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
- **recycle**: Require a released slot, the exact new owner, clean worktrees, no in-progress Git operation, pushed HEADs, and recorded branch/PR identity for the previous task. Re-inspect the complete repo batch before switching or creating task branches. Never auto-delete old branches or worktrees.
- **submit**: The development owner may push only its own task branch. Draft submission records branch and PR identity. Ready submission requires final validation, a non-Draft PR, `merge-ready`, and a machine-readable `<!-- stageflow-ready-sha: <full-head-sha> -->` comment for the pushed current head. Make that comment the final PR update. Freeze the branch after Ready; any later PR update, push, or force-push invalidates readiness until the current head SHA is declared Ready again.
- **integrate**: First require working `gh` authentication, confirmed GitHub repositories and source bases, and confirmed merge-queue policy. Preflight every PR with the read-only helper; verify CI, review, current head, Ready SHA, base, mergeability, and dependencies. If any post-Ready push or force-push is known or suspected, audit the PR timeline and require a fresh Ready declaration even when the head later returns to the old SHA. After presenting exact PRs and SHAs and receiving approval, enqueue with `gh pr merge "<pr>" --repo "<owner/repo>" --match-head-commit "<sha>"`. If queue policy cannot be confirmed, do not run this command because it could merge directly; offer the existing local flow instead. PR mode has no post-merge local push prompt.
- **merge**: Use the worktree where the confirmed source branch is already checked out. Merge one repo at a time and stop on the first failure or conflict. After successful merges, summarize results and ask `push까지 진행할까요?`; never include push in the merge batch.
- **sync**: Bring each confirmed source branch into its derived branch. Default to merge; use rebase only when the user requests it or repository policy requires it. Process one repo at a time and stop on the first failure or conflict.

Run a complete preflight across all repos before the first write. An in-progress Git operation, detached required worktree, ambiguous branch mapping, missing path, or operation-relevant dirty state blocks the whole batch. Missing upstream blocks push or remote synchronization, but does not by itself block local create, merge, or sync.

Independent PRs may be prepared in parallel, but enqueue a dependent consumer only after its provider is actually merged into the source branch; queue registration alone is insufficient. Multi-repo remote operations are not atomic. If some PRs merge or pushes succeed before another fails, report `recovery-required` with completed, failed, and untouched repos and never auto-rollback.

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
