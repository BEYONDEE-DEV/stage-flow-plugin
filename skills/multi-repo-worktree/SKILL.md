---
name: multi-repo-worktree
description: "Use only when the user explicitly invokes `$stageflow:multi-repo-worktree`, links `[$stageflow:multi-repo-worktree](...)`, or explicitly asks to use multi-repo-worktree for a bundle of multiple independent Git repositories. Coordinate help, status, one-time create, repeated same-branch submit, pull, and sync workflows with intent-authorized routine writes, persistent source/remote facts, and narrow decision gates. Do not use for ordinary Git, single-repo, or single-worktree requests."
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
- `submit` owns task-related-path Korean commits, same-branch push, Korean ready PR creation or update, merged-base incorporation, changed-files proof, and PR-generation recording.
- The user merges PRs in GitHub outside this skill. Never enable auto-merge or run a remote PR merge command.
- `pull` runs only in confirmed original/source worktrees.
- `sync` runs only in development worktrees and never updates an original worktree.

The workspace-root `.stageflow-worktrees/slots.json` is authoritative for fixed slot path and each repository's fixed task branch, source branch, remote, generation, and current PR. Use a transient exclusive operation lock during `submit`; it prevents concurrent writers but is not a slot lifecycle.

## Decision Contract

- Treat an explicit request to execute `create`, `submit`, `pull`, or `sync` as authorization for that keyword's routine writes. A request for `status`, inspection only, or dry-run is always read-only and never authorizes Git, GitHub, lock, or manifest mutation.
- Before routine writes, inspect the complete batch and send a concise non-blocking commentary summary of targets, changed paths, PR classification, intended effects, fetch/ref updates, risks, and stop behavior. Do not ask the user to approve exact commands, task-related path lists, generated Korean text, manifest-proven PR flow, or compatible source-tip refresh.
- Ask one consolidated question only when a permanent path/source/task/remote fact is missing or conflicts, publish content is secret-bearing/generated/unrelated/ambiguous, scope would materially expand, or destructive/history-rewriting, stale-lock unlock, or conflict recovery is required.
- Persist repo-specific source branches and remotes at `create`. For a legacy schema-2 slot, enrich the selected slot without a question only when exact recorded-PR base and unique repository remote prove every missing fact; otherwise ask once and persist the answer. Never write using inferred or ambiguous context.
- Revalidate stored remote names against repository identity and actual refs on every operation. A conflicting permanent fact blocks instead of being silently rebound.
- Re-inspect immediately before publication. Automatically repeat fetch/pin/preflight only for a compatible advancement of the same source branch before branch/index/manifest/remote publication. Stop and report a retryable state when permanent identity, generation, PR classification, base, or head changes.
- Never reset, clean, force checkout, force push, rewrite history, or delete a branch or worktree unless the user explicitly requests that exact operation. Never auto-resolve conflicts.

## Operation Rules

- **help**: Explain the six keywords and the one-time-create/repeated-submit flow. Do not inspect unless the user requests an operation.
- **status**: Keep output read-only. For an identifiable bundle, show `대상 묶음`, `원본 브랜치`, and `기준 폴더` once, then one repo per line as `<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>`. Add manifest generation/current PR and operation-lock blockers separately. Do not use a Markdown table.
- **create**: Resolve every source branch, remote, fixed task branch, target path, and repository set. Ask once only for missing or conflicting facts; otherwise the keyword request authorizes initialization. Initialize the complete permanent manifest binding before the first worktree write. Exact retry may complete a partial first creation; a different path, repo set, branch, remote, dirty state, or ambiguous existing path blocks before mutation. Never switch the slot to a new branch for later work.
- **submit**: Classify every changed repository independently as manifest-proven `NONE`, exact recorded `OPEN`, or exact recorded `MERGED`; supported classifications and generations may differ within one batch. Acquire the slot operation lock, re-inspect, and automatically commit only clearly task-related staged, unstaged, and non-ignored untracked paths with generated Korean messages. `NONE` creates its first ready PR, `OPEN` pushes to the same PR without rewriting its title/body unless the user explicitly requested that edit, and `MERGED` fetches and pins its base, merges it into the same task branch, proves `base...head` and the created PR contain only the next work, then creates the next ready PR. Atomically advance only repositories that created or exactly adopted a new PR, using each repository's own expected generation. A merged state with no next-work diff is a successful no-op. Always release only the operation lock after a safe terminal result; never release the slot.
- **pull**: Run only where each manifest source branch is checked out in its original worktree. Preflight all roots, fetch each stored remote, pin `refs/remotes/<remote>/<source-branch>`, reject divergence, then fast-forward each source branch to its pinned SHA. Do not use configuration-dependent plain `git pull`, create merge commits, rebase, or touch development worktrees.
- **sync**: Run only in the requested development worktree bundle. Require clean derived worktrees, fetch each stored remote, pin `refs/remotes/<remote>/<source-branch>`, then merge it into the current fixed task branch. Fetch may update shared remote-tracking refs, but never switch or update an original worktree's branch, HEAD, index, or files.

`CLOSED`, missing or inaccessible recorded PRs, head/base mismatch, unexpected remote divergence, lost manifest history, ambiguous PR adoption, and unknown API state are unsupported. Fail closed for the entire batch before mutation; do not reopen, replace, reset, force-push, guess, or bypass this skill with an untracked Git/GitHub flow. A mix of otherwise valid `NONE`, `OPEN`, and `MERGED` repositories is not a blocker.

Run complete-batch preflight before the first write. Block on ambiguous mappings, unexpected branches, detached required worktrees, in-progress Git operations, unsafe locked/prunable paths, or missing/ambiguous remotes. A `submit` may include only literal paths whose content is clearly part of the current task; suspicious or ambiguous content requires a decision before staging.

Multi-repo writes are not atomic. Report `completed`, `failed`, and `untouched` repositories with overall `recovery-required` plus exact resume state; never claim rollback or undo successful remote work automatically. A same-keyword retry may adopt only one OPEN PR whose exact base branch, head branch, and head SHA match the inspected submission.

## Status Output

Use this primary shape:

```text
대상 묶음: worktrees/feature-etc-docs
원본 브랜치: feature-etc (추정)
기준 폴더: /home/kgh-wsl/projects/admin-product-3/worktrees/feature-etc-docs

majoong_events_api: 폴더 majoong_events_api / 현재 브랜치 feature-etc-docs / 변경상태 dirty
majoong_events_web: 폴더 majoong_events_web / 현재 브랜치 feature-etc-docs / 변경상태 dirty
```

Keep `dirty` and `clean` unchanged. Prefer the permanent manifest source branch when present. Mark inspector-only or legacy inferred source branches with `(추정)`. If mappings differ or remain uncertain, show `원본 브랜치: 확인 필요` and explain repo-specific evidence separately; read-only status never enriches the manifest.
