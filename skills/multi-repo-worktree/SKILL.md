---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes `$stageflow:multi-repo-worktree`, links `[$stageflow:multi-repo-worktree](...)`, or explicitly asks to use multi-repo-worktree for a bundle of multiple independent Git repositories. Coordinate help, status, one-time create, repeated same-branch submit, pull, and sync workflows with read-only inspection and approval-gated Git or GitHub writes. Do not use for ordinary Git, single-repo, or single-worktree requests."
---

# Multi Repo Worktree

Coordinate one fixed development bundle whose folders belong to multiple independent Git repositories. Treat every repository, source branch, fixed task branch, upstream, dirty state, PR, and Git operation independently.

## Invocation

Use:

```text
$stageflow:multi-repo-worktree <keyword> [free-form intent]
```

Support only these keywords:

- `help`: explain the workflow, inputs, and safety gates.
- `status`: inspect repositories, permanent slot bindings, branches, PR generations, and blockers.
- `create`: initialize a fixed slot, worktrees, and per-repo task branches once.
- `submit`: conditionally commit, update an open PR, or create the next same-branch PR.
- `pull`: fast-forward confirmed original branches from their remotes.
- `sync`: merge confirmed remote source branches into development worktrees.

If the user invokes the skill without a keyword, show help and ask which keyword to use. Do not accept or advertise `recycle`, `integrate`, the former PR-less local `merge`, or their legacy aliases.

## Required Inspection

For `status`, `create`, `submit`, `pull`, and `sync`:

1. Read `references/worktree-operations.md` from this skill directory.
2. Resolve `<skill-dir>` as the directory containing this loaded `SKILL.md`; do not assume the current working directory is the plugin root.
3. Run the read-only inspector when a workspace path is available:

```bash
python3 "<skill-dir>/scripts/inspect_worktrees.py" --root "<workspace-root>" --json
```

Use `--bundle "worktrees/<bundle-name>"` when the requested bundle is known. On Windows, use `py -3` when needed. Never infer that a workspace root or bundle folder is a Git repository; trust Git and the inspector.

For slot-backed `status`, `create`, and `submit`, read the permanent manifest without changing Git:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status
```

## Workflow And Ownership

Use this normal flow:

```text
create once -> develop -> submit -> user merges on GitHub
                         ^                         |
                         |---- develop next ------|
```

- `create` owns only first initialization and exact idempotent retry of the same fixed binding. Never use it to start later work.
- The slot path, worktrees, local task branches, and manifest binding persist. There is no `active`/`released` state, owner reassignment, submit-time release, or automatic cleanup.
- `submit` owns approved-path Korean commits, same-branch push, Korean ready PR creation or update, merged-base incorporation, changed-files proof, and PR-generation recording.
- The user merges PRs in GitHub outside this skill. Never enable auto-merge or run a remote PR merge command.
- `pull` runs only in confirmed original/source worktrees.
- `sync` runs only in development worktrees and never updates an original worktree.

The workspace-root `.stageflow-worktrees/slots.json` is authoritative for fixed slot path and each repository's branch, generation, and current PR. Use a transient exclusive operation lock during `submit`; it prevents concurrent writers but is not a slot lifecycle.

## Approval Contract

- Treat every source branch as a repo-specific, user-confirmed fact. Git does not record the branch from which another branch was originally created.
- Label source branches derived only from sibling-worktree evidence as `(추정)`. Never execute a write using an inferred or ambiguous source branch.
- Before any Git or GitHub write, inspect every participating repo and present the exact repo order, paths, source and task branches, manifest generation/current PR, dirty paths, PR-state classification, remote/refspec, operation, commands, and risks.
- Accept approval only after presenting that exact plan; require explicit approval. Approval applies only to the displayed batch. Re-inspect before execution and ask again if scope, branches, commands, strategy, PR state, or relevant SHA changes materially.
- Never reset, clean, force checkout, force push, rewrite history, or delete a branch or worktree unless the user explicitly requests that exact operation. Never auto-resolve conflicts.

## Operation Rules

- **help**: Explain the six keywords and the one-time-create/repeated-submit flow. Do not inspect unless the user requests an operation.
- **status**: Keep output read-only. For an identifiable bundle, show `대상 묶음`, `원본 브랜치`, and `기준 폴더` once, then one repo per line as `<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>`. Add manifest generation/current PR and operation-lock blockers separately. Do not use a Markdown table.
- **create**: Confirm every source branch, fixed task branch, target path, and repository set. Initialize the permanent manifest binding before the first approved worktree write. Exact retry may complete a partial first creation; a different path, repo set, branch, dirty state, or ambiguous existing path blocks before mutation. Never switch the slot to a new branch for later work.
- **submit**: Classify every changed repository as manifest-proven `NONE`, exact recorded `OPEN`, or exact recorded `MERGED`. All must have the same supported state; otherwise block the whole batch before mutation. Acquire the slot operation lock, re-inspect, conditionally commit only approved paths with Korean messages, and follow the state flow in the reference. `OPEN` updates the same PR. `MERGED` fetches and pins the base, merges it into the same task branch, proves `base...head` and the created PR contain only the next work, then creates the next ready PR and atomically advances generation. A merged state with no next-work diff is a successful no-op. Always release only the operation lock after a safe terminal result; never release the slot.
- **pull**: Run only where each confirmed original/source branch is checked out. Preflight all roots, fetch each confirmed remote, pin each `origin/<source>` SHA, reject divergence, then fast-forward each source branch to its pinned SHA. Do not use configuration-dependent plain `git pull`, create merge commits, rebase, or touch development worktrees.
- **sync**: Run only in the requested development worktree bundle. Require clean derived worktrees, fetch each confirmed remote, pin each `origin/<source>` SHA, then merge it into the current fixed task branch. Fetch may update shared remote-tracking refs, but never switch or update an original worktree's branch, HEAD, index, or files.

`CLOSED`, missing or inaccessible recorded PRs, head/base mismatch, unexpected remote divergence, lost manifest history, ambiguous PR adoption, unknown API state, and mixed multi-repo states are unsupported. Fail closed for the entire batch before mutation; do not reopen, replace, reset, force-push, or guess.

Run complete-batch preflight before the first write. Block on ambiguous mappings, unexpected branches, detached required worktrees, in-progress Git operations, unsafe locked/prunable paths, or missing/ambiguous remotes. A `submit` may allow only the exact dirty paths included in its approved commit plan.

Multi-repo writes are not atomic. Report `completed`, `failed`, and `untouched` repositories with overall `recovery-required`; never claim rollback or undo successful remote work automatically. A retry may adopt only one OPEN PR whose exact base branch, head branch, and head SHA match the approved submission.

## Status Output

Use this primary shape:

```text
대상 묶음: worktrees/feature-etc-docs
원본 브랜치: feature-etc (추정)
기준 폴더: /home/kgh-wsl/projects/admin-product-3/worktrees/feature-etc-docs

majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty
majoong_events_web: 폴더 majoong_events_web / 현재 브랜치 feature-etc-docs / 변경상태 dirty
```

Keep `dirty` and `clean` unchanged. Mark inferred source branches with `(추정)`. If mappings differ or remain uncertain, show `원본 브랜치: 확인 필요` and explain repo-specific evidence separately.
