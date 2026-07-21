# Worktree Operations

## Contents

- Keyword and approval contract
- Roles and normal flow
- Slot manifest
- Read-only inspection and status
- Complete-batch preflight
- Create
- Submit
- Pull
- Sync
- Partial results and reporting

## Keyword And Approval Contract

Expose only `help`, `status`, `create`, `submit`, `pull`, and `sync`. Do not normalize or advertise removed `recycle`, `integrate`, `merge`, `merge-back`, or `sync-derived` commands.

For every write operation:

1. Inspect all participating repositories without changing Git or GitHub state.
2. Resolve repo-specific source branches, task branches, remotes, and worktree paths.
3. Preflight the complete batch.
4. Present exact commands, order, risks, conflict behavior, and partial-failure behavior.
5. Receive explicit approval after the exact plan.
6. Re-inspect relevant state immediately before execution.
7. Execute one repository at a time and stop on the first failure or conflict.

Approval given before the exact plan does not authorize execution. Material plan changes require a revised plan and new approval.

## Roles And Normal Flow

```text
create
  -> develop and validate
  -> submit regular PR
  -> user merges the PR on GitHub
```

- **Development owner**: owns one active slot and its task branches, validation, submission, correction, and development-worktree `sync`.
- **Original owner**: runs `pull` only in the confirmed original/source worktrees.
- **GitHub user**: manually merges PRs outside this skill. The skill neither enables auto-merge nor runs remote merge commands.

After a successful submit, the development owner releases the slot and may start the next task through `create`. Before GitHub merge, a correction may explicitly recover the same PR head branch in a safe released slot and update the same PR. After merge, create a new branch and follow-up PR; never rewrite or auto-revert the merged submission.

## Slot Manifest

`<workspace-root>/.stageflow-worktrees/slots.json` owns fixed-slot name, absolute path, exact owner, `active`/`released` state, and minimal repository branch/PR identity.

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  claim --slot "<slot>" --owner "<task-owner>" --path "<slot-path>"
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  claim --slot "<slot>" --owner "<correction-owner>" --path "<slot-path>" \
  --preserve-repositories
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  record --slot "<slot>" --owner "<task-owner>" --repo "<repo>" \
  --branch "<task-branch>" --pr "<pr-number-or-url>"
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  release --slot "<slot>" --owner "<task-owner>"
```

The helper writes atomically. Same-owner claim is idempotent; different-owner active claim, wrong-owner release, stale release, fixed-path mismatch, and malformed state fail closed. A normal released-slot claim clears old repository identity. Use `--preserve-repositories` only for explicit correction recovery after confirming the released branch/PR identity; it fails when no recorded identity exists. Only the exact active owner may record or release. The helper never invokes Git or deletes anything.

Repository records deliberately omit submitted/head SHA. GitHub owns current PR head state, while the manifest exists only to recover the task branch and PR identity after slot release. Existing legacy record fields may be read, but new `record` writes replace them with only `branch` and `pr`.

## Read-Only Inspection And Status

Resolve scripts relative to the loaded skill directory:

```bash
python3 "<skill-dir>/scripts/inspect_worktrees.py" \
  --root "<workspace-root>" \
  --bundle "worktrees/<bundle-name>" \
  --json
```

The inspector uses local Git state only. It must not fetch, pull, create/switch branches or worktrees, merge, rebase, push, reset, clean, abort, or delete.

Git does not retain a branch's creation parent. User confirmation is authoritative. A unique sibling branch is evidence only; mark it `(추정)` and obtain confirmation before a write.

For an identifiable bundle, show:

```text
대상 묶음: worktrees/<bundle-name>
원본 브랜치: <source-branch (추정)|확인 필요>
기준 폴더: <absolute-bundle-folder>

<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>
```

Do not use a Markdown table. Show each participating repo on one line. List repos independently even when branch names match. Make `폴더` relative to `기준 폴더`. Keep upstream, HEAD, locks, prunable state, and operation state out of the primary line; add them only as relevant risk notes. When the user names a bundle, filter to it and do not mix the workspace or sibling bundles.

## Complete-Batch Preflight

Before any write, block the whole plan on:

- ambiguous or inferred-only branch mappings
- unexpected current branches or detached required worktrees
- an in-progress merge, rebase, cherry-pick, revert, or bisect
- operation-relevant dirty state
- unsafe locked/prunable paths or missing required paths
- branches checked out in unexpected worktrees
- missing or ambiguous remotes/upstreams required by the operation

Fetch is a Git write because it updates shared remote-tracking refs. Finish local/path/branch preflight before fetch. After fetching all repos, pin each fetched remote SHA and finish divergence/conflict preflight before changing local branches.

## Create

Create has three explicit modes:

1. **New or empty-slot path**: create new task branches and worktree paths from confirmed source branches.
2. **Existing released-slot reuse**: claim the fixed slot normally, which clears prior repository identity, then create and switch each clean existing worktree to a new task branch from its confirmed source start point.
3. **Correction recovery**: confirm the released manifest identity and remote PR head, claim with `--preserve-repositories`, and attach the recorded existing PR branch. Do not use normal reuse for a correction.

For a new branch at an empty target path:

```bash
git -C "<source-worktree>" worktree add -b "<task-branch>" "<target-path>" "<source-branch>"
```

For an existing local branch at an empty target path:

```bash
git -C "<source-worktree>" worktree add "<target-path>" "<task-branch>"
```

For an existing released slot whose repo worktrees remain on disk, require every worktree to be clean and free of in-progress operations, require the new task branch not to exist, and then plan:

```bash
git -C "<existing-slot-worktree>" switch -c "<new-task-branch>" "<confirmed-source-start-point>"
```

For correction recovery, freshly fetch the explicit PR-head ref in every repo before claiming the slot and pin its SHA:

```bash
git -C "<repository-worktree>" fetch --prune "<remote>"
git -C "<repository-worktree>" rev-parse "refs/remotes/<remote>/<recorded-pr-branch>"
```

Require the recorded local branch HEAD to equal that pinned PR-head SHA. If an existing clean slot worktree is already on the recorded branch, no branch switch is needed. If it is on another expected released branch and the correction branch is not checked out elsewhere, plan:

```bash
git -C "<existing-slot-worktree>" switch "<recorded-pr-branch>"
```

Recheck that the switched HEAD equals the pinned PR-head SHA before allowing edits. At an empty target path, attach the confirmed local branch with the existing-branch `worktree add` command above. If the local branch does not exist, create it exactly at the pinned PR-head SHA:

```bash
git -C "<source-worktree>" worktree add -b "<recorded-pr-branch>" \
  "<target-path>" "<pinned-pr-head-sha>"
```

Do not guess or silently fast-forward a mismatched local correction branch.

Claim the manifest inside the approved batch after all repos and paths pass preflight but before the first worktree add or switch. A partial add/switch keeps ownership active and reports `recovery-required`; do not auto-delete created worktrees, restore old branches, or silently release ownership. Never overwrite a path, steal an active slot, reuse a dirty slot, recreate an existing branch, use `--force`, or guess between new/reuse/recovery.

## Submit

Only the exact active development owner may submit its committed task branches.

Preflight the complete batch. Require user-confirmed validation, explicit push remote/refspec, and explicit PR base/head. Compose the exact title and body before the write plan. Write the PR title and explanatory prose in Korean while preserving literal identifiers, paths, commands, URLs, quoted text, and repository-required fixed template text. For an existing PR, show any title/body rewrite instead of silently replacing user-authored content.

For each repo:

1. Push the committed task branch.
2. Create or update a regular non-Draft PR with the approved Korean title/body.
3. Record only branch and PR identity in the manifest.

After every repo succeeds, release the slot as the exact owner. A partial push, PR, or record failure keeps the slot active and reports completed/failed/untouched repos as `recovery-required`.

Do not pass `--draft`, run `gh pr ready`, create submitted-SHA comments, enable auto-merge, or run a remote PR merge command. The user merges on GitHub outside this skill.

## Pull

`pull` runs only from the confirmed original/root repository set, with each source branch already checked out in its original worktree. It never touches development worktrees.

Before fetch, require every root to be clean, on the confirmed source branch, free of in-progress operations, and configured with an explicit remote/source ref. Then fetch every repo:

```bash
git -C "<original-worktree>" fetch --prune "<remote>"
```

After all fetches succeed, resolve and display the full fetched `refs/remotes/<remote>/<source>` SHA for every repo. Require the current source HEAD to be an ancestor of that pinned SHA. Divergence blocks the entire fast-forward phase.

Fast-forward one repo at a time to the pinned SHA:

```bash
git -C "<original-worktree>" merge --ff-only "<pinned-source-sha>"
```

Do not use plain `git pull`, create a merge commit, rebase, reset, switch branches, or update a development worktree. A no-op already at the pinned SHA is successful and retry-safe.

## Sync

`sync` runs only in the requested development worktree bundle. It never runs from an original/root worktree and never updates a root worktree's checked-out state.

Before fetch, require every derived worktree to be clean, on the expected task branch, and free of in-progress operations. Confirm the repo-specific source branch and remote. Fetch every repo:

```bash
git -C "<derived-worktree>" fetch --prune "<remote>"
```

After all fetches succeed, resolve and display the full fetched `refs/remotes/<remote>/<source>` SHA. Merge the pinned SHA into each current derived branch:

```bash
git -C "<derived-worktree>" merge "<pinned-source-sha>"
```

Fetching from a linked worktree updates repository-shared objects and remote-tracking refs, but must not switch or update the original worktree's branch, HEAD, index, or files. The original worktree may remain intentionally stale. `sync` does not invoke `pull`, and the two commands have no required ordering.

On conflict, stop in the failing derived worktree. Report its Git state and untouched repos. Do not resolve, continue, skip, abort, or update the root unless separately approved.

## Partial Results And Reporting

Multi-repo operations are not atomic. Complete-batch preflight reduces predictable partial work but cannot eliminate network, hook, or filesystem failures.

After execution, report:

- `completed`: exact repos and resulting branches/HEADs or remote PR writes
- `failed`: repo and exact failing operation/state
- `untouched`: repos not started
- overall `recovery-required` when any requested repo remains incomplete

Never auto-rollback a pushed branch, created PR, fast-forwarded source, created worktree, or successful derived merge. Build a fresh exact recovery plan and obtain new approval.
