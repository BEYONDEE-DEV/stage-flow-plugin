---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes `$stageflow:multi-repo-worktree`, links `[$stageflow:multi-repo-worktree](...)`, or explicitly asks to use multi-repo-worktree for a bundle of multiple independent Git repositories. Coordinate help, status, create, submit, pull, and sync workflows with read-only inspection and approval-gated Git or GitHub writes. Do not use for ordinary Git, single-repo, or single-worktree requests."
---

# Multi Repo Worktree

Coordinate one logical worktree bundle whose folders belong to multiple independent Git repositories. Treat every repository, branch, upstream, dirty state, and Git operation independently.

## Invocation

Use:

```text
$stageflow:multi-repo-worktree <keyword> [free-form intent]
```

Support only these keywords:

- `help`: explain the workflow, inputs, and safety gates.
- `status`: inspect repositories, worktrees, branches, slots, and blockers.
- `create`: create a bundle or safely reuse a released fixed slot.
- `submit`: commit approved intended changes when needed, push task branches, create or update regular PRs, and release the slot.
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

For slot-backed `status`, `create`, and `submit`, read the manifest without changing Git:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status
```

## Workflow And Ownership

Use this normal flow:

```text
create -> develop and validate -> submit -> user merges on GitHub
```

- `create` owns new bundle creation, safe released-slot reuse, and explicit recovery of an existing PR branch.
- `submit` owns conditional commit, push, Korean PR title/body, minimal branch/PR manifest identity, and release after complete success.
- GitHub PR merge is manual and outside this skill. Never enable auto-merge or run a PR merge command.
- `pull` runs only in confirmed original/source worktrees.
- `sync` runs only in development worktrees and never updates an original worktree.

The workspace-root `.stageflow-worktrees/slots.json` is authoritative for fixed-slot path, exact owner, `active`/`released` state, and repository branch/PR identity. Only the exact active owner may record or release a slot.

## Approval Contract

- Treat every source branch as a repo-specific, user-confirmed fact. Git does not record the branch from which another branch was originally created.
- Label source branches derived only from sibling-worktree evidence as `(추정)`. Never execute a write using an inferred or ambiguous source branch.
- Before any Git write or GitHub write, inspect every participating repo and present the exact repo order, paths, source and task branches, dirty state, upstream/remote, operation, commands, and risks.
- Accept approval only after presenting that exact plan; require explicit approval. Approval applies only to the displayed batch. Re-inspect before execution and ask again if scope, branches, commands, strategy, or relevant state changes materially.
- Never reset, clean, force checkout, force push, or delete a branch or worktree unless the user explicitly requests that exact operation. Never auto-resolve conflicts.

## Operation Rules

- **help**: Explain the six keywords and the normal flow. Do not inspect unless the user requests an operation.
- **status**: Keep output read-only. For an identifiable bundle, show `대상 묶음`, `원본 브랜치`, and `기준 폴더` once, then one repo per line as `<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>`. Do not use a Markdown table.
- **create**: Confirm every source branch, task branch, target path, and whether the operation creates an empty-path worktree, switches an existing released clean slot to a new branch, or explicitly recovers a manifest-recorded PR branch. A normal reuse clears prior repository identity; explicit correction recovery preserves confirmed branch/PR identity while claiming the slot. Claim before the first approved add/switch, keep partial failures active for recovery, and never overwrite or steal an active, dirty, ambiguous, or differently owned slot.
- **submit**: Inspect staged, unstaged, and untracked changes. If a repo is dirty, require every changed path to be an intended submission change, show the exact paths and commit message, then stage only those approved paths and commit before any push. Skip the commit for clean repos. Complete the local commit phase for every repo, re-inspect for clean worktrees and unchanged scope, then show and execute exact pushes and Korean PR titles/bodies. If a commit or hook fails or leaves new dirt, keep the slot active and do not start remote writes. Create or update regular non-Draft PRs, record only repository branch/PR identity, and release only after every repo succeeds. Never amend, create an empty commit, enable auto-merge, or merge a PR.
- **pull**: Run only where each confirmed original/source branch is checked out. Preflight all roots, fetch each confirmed remote, pin each `origin/<source>` SHA, reject divergence, then fast-forward each source branch to its pinned SHA. Do not use configuration-dependent plain `git pull`, create merge commits, rebase, or touch development worktrees.
- **sync**: Run only in the requested development worktree bundle. Require clean derived worktrees, fetch each confirmed remote, pin each `origin/<source>` SHA, then merge it into the current derived branch. Fetch may update shared remote-tracking refs, but never switch or update an original worktree's branch, HEAD, index, or files.

Run complete-batch preflight before the first write. Block on ambiguous mappings, unexpected branches, dirty operation-relevant worktrees except an approved `submit` commit candidate, detached required worktrees, in-progress Git operations, unsafe locked/prunable paths, or missing or ambiguous remotes. Process one repository at a time and stop on the first failure or conflict.

Multi-repo writes are not atomic. Report `completed`, `failed`, and `untouched` repositories with overall `recovery-required`; never claim rollback or undo successful remote work automatically.

## Status Output

Use this shape:

```text
대상 묶음: worktrees/feature-etc-docs
원본 브랜치: feature-etc (추정)
기준 폴더: /home/kgh-wsl/projects/admin-product-3/worktrees/feature-etc-docs

majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty
majoong_events_web: 폴더 majoong_events_web / 현재 브랜치 feature-etc-docs / 변경상태 dirty
```

Keep `dirty` and `clean` unchanged. Mark inferred source branches with `(추정)`. If mappings differ or remain uncertain, show `원본 브랜치: 확인 필요` and explain repo-specific evidence separately.
