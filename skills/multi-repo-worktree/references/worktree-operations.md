# Worktree Operations

## Keyword Contract

Expose only `help`, `status`, `create`, `recycle`, `submit`, `integrate`, `merge`, and `sync`.

Normalize older wording without advertising it:

- `setup` with creation intent -> `create`
- `merge-back` -> `merge`
- `sync-derived` -> `sync`

For `create`, `recycle`, `submit`, `integrate`, `merge`, and `sync`, always:

1. Inspect all participating repositories without writing Git state.
2. Resolve repo-specific branch mappings and worktree paths.
3. Preflight the complete batch.
4. Present the exact plan, commands, order, risks, and conflict behavior.
5. Receive explicit approval after the plan.
6. Re-inspect relevant state immediately before execution.
7. Execute one repository at a time and stop on the first failure or conflict.

Do not treat an approval given before the exact plan as approval to execute it. If a material part of the approved plan changes, present the revised plan and ask again.

## Roles And Repeating Loop

The fixed-slot loop is:

```text
create once
  -> develop and validate
  -> submit regular PR at exact SHA
       -> development owner: release -> recycle -> next independent task
       -> integration session: exact-SHA validate -> approved remote merge
```

Keep three owners separate:

- **Development owner**: owns one active local slot and only its task branches, validation, regular PR submission, release, recycle, correction, and active-task `sync`.
- **Integration session**: runs outside development bundles from a user-confirmed original/root repository area; performs one-shot read-only PR preflight and the approved remote merge. It never changes the slot manifest or development worktrees.
- **GitHub**: owns PR state and source-branch updates in PR mode; auto-merge or merge queue behavior applies only when confirmed repository policy requires it.

Do not promise a daemon, scheduler, background watcher, or atomic transaction across repositories.

## Local Slot Manifest

`<workspace-root>/.stageflow-worktrees/slots.json` is the authoritative local record for slot name, absolute path, exact owner, `active`/`released` state, and repository branch/pushed-SHA/PR identity. Use:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  claim --slot "<slot>" --owner "<task-owner>" --path "<slot-path>"
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  record --slot "<slot>" --owner "<task-owner>" --repo "<repo>" \
  --branch "<task-branch>" --head-sha "<head>" --pushed-sha "<remote-head>" --pr "<pr>"
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  release --slot "<slot>" --owner "<task-owner>"
```

The helper writes atomically. Same-owner claim is idempotent; active different-owner claim, wrong-owner release, stale release, and malformed state fail closed. Use a unique request/task owner identifier rather than a reusable human label. Only the exact active development owner may release. An integration identity must always be rejected unless it truly is the recorded development owner, which role policy forbids. The helper never invokes Git and never deletes a branch or worktree.

## Read-Only Inspection

Resolve scripts relative to the loaded skill directory, not the caller's current directory:

```bash
python3 "<skill-dir>/scripts/inspect_worktrees.py" \
  --root "<workspace-root>" \
  --bundle "worktrees/<bundle-name>" \
  --json
```

Omit `--bundle` only when discovering available bundles. Use `py -3` on Windows if `python3` is unavailable.

The inspector uses local Git state only. It must not fetch, pull, create branches or worktrees, switch branches, merge, rebase, push, reset, clean, abort operations, or delete branches. If remote freshness matters, explain that limitation and approval-gate any separate fetch.

Use Git-common-directory identity to group worktrees belonging to the same repository. Record per worktree:

- absolute path and repo label
- branch and HEAD
- dirty state
- upstream, if any
- locked or prunable state
- merge, rebase, cherry-pick, revert, or bisect in progress

Git does not retain a branch's creation parent. User input is the authority for a source branch. A unique sibling-worktree branch is evidence only; mark it `(추정)` and require confirmation before a write.

## Status

When the request identifies a bundle, filter to it and do not mix the workspace or sibling bundles into the primary result. Use:

```text
대상 묶음: worktrees/<bundle-name>
원본 브랜치: <source-branch (추정)|확인 필요>
기준 폴더: <absolute-bundle-folder>

<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>
```

Rules:

- Do not use a Markdown table for status.
- Show `대상 묶음`, `원본 브랜치`, and `기준 폴더` once.
- Show each participating repo on one line.
- Make `폴더` relative to `기준 폴더`.
- Keep `dirty` and `clean` unchanged.
- Show `원본 브랜치: 확인 필요` when repo source branches differ or any mapping is unknown.
- Keep upstream, HEAD, locks, prunable state, and operation state out of the primary repo line. Add separate risk notes only when relevant.
- List repos independently even when branch names match.
- State clearly when no requested bundle matches instead of silently showing another bundle.

## Complete-Batch Preflight

Finish preflight for every repo before the first write. A blocker in any repo blocks the batch plan; do not partially start and discover an already-detectable blocker later.

Always block on:

- an ambiguous or merely inferred branch mapping
- a detached worktree required by the operation
- an in-progress merge, rebase, cherry-pick, revert, or bisect
- a locked or prunable required worktree whose safety is unclear
- a missing required worktree or invalid target path
- a branch already checked out in an unexpected worktree

Apply dirty and upstream rules by operation:

| Operation | Dirty-state rule | Upstream rule |
| --- | --- | --- |
| `create` | Source dirt does not change the source branch tip; warn that uncommitted changes are excluded. | Missing upstream does not block local creation. |
| `merge` | Require both source and derived worktrees to be clean so the merge contains only committed derived changes. | Missing upstream does not block local merge; it blocks a later push until a target is confirmed. |
| `sync` | Require the derived worktree to be clean. Warn if source dirt exists because only committed source changes are synced. | Missing upstream does not block a local branch-to-branch merge or rebase. |
| `push` or remote sync | Preserve local dirt rules for the preceding operation. | Require an explicit remote and refspec when upstream is absent or ambiguous. |

## Create

Confirm per repo:

- source branch and source worktree
- derived branch name
- target path under the bundle base
- whether to create a new branch or attach an existing branch
- that the target path does not already contain data
- that an existing derived branch is not already checked out elsewhere

For a new branch, plan:

```bash
git -C "<source-worktree>" worktree add -b "<derived-branch>" "<target-path>" "<source-branch>"
```

For an existing branch, plan only after explicit confirmation:

```bash
git -C "<source-worktree>" worktree add "<target-path>" "<derived-branch>"
```

Never overwrite a path, recreate a branch, use `--force`, or guess between new and existing branch behavior.

For a fixed slot, claim the manifest only as part of the exact approved create batch and only after all repository/path preflight passes. If Git worktree creation partially fails, report the slot and repos as `recovery-required`; do not silently release ownership or delete created worktrees.

## Recycle

Recycle reuses a fixed directory. It normally starts a new task branch, but a correction may attach an explicitly confirmed existing PR head branch. Before presenting any write plan, require:

- manifest state is `released`
- requested new owner and task branch are explicit
- every participating worktree is clean and has no merge/rebase/cherry-pick/revert/bisect in progress
- prior local HEAD equals its pushed SHA
- prior branch and PR identity are recorded
- the new branch source/base and remote are confirmed, or the correction PR, existing head branch, remote head, and source base are confirmed

Validate both manifest and current Git state; neither is sufficient alone. An existing correction branch must not be checked out in any other worktree, and the correction owner must re-submit every changed repo before release. Claim the slot for the exact new owner only in the approved batch. Plan repo commands independently and stop on first failure. Never auto-delete prior local/remote branches or remove the fixed worktree. If a different owner has already claimed it, stop rather than stealing or repairing the claim.

## Submit

Only the active development owner may submit, and only its task branches.

Preflight the complete repo batch and require the intended changes to be committed, the user-confirmed validation to have completed, and every push remote/refspec and PR base/head to be explicit. Show the push, regular non-Draft PR create/update, submitted-SHA comment, manifest record, and final release commands before approval. Do not pass `--draft` or run `gh pr ready`.

The remote handoff is a machine-readable PR comment:

```text
<!-- stageflow-submitted-sha: <full-head-sha> -->
```

For each repo, push first; create or update the regular PR; add the submitted-SHA comment; then record branch, local head, pushed SHA, and PR identity in the manifest. A record is allowed only after that repo's remote operations succeed. Release the slot only after every participating repo is recorded successfully. A partial push, PR, comment, or record failure leaves the slot active and reports completed, failed, and untouched repos as `recovery-required`.

Submission is bound to the full SHA, not the branch name. A later branch push makes the current head differ from the latest submitted marker and blocks integration until the active correction owner validates and submits the new head. Reviews, status updates, and unrelated PR comments do not invalidate an unchanged head. After complete submit succeeds, the current development owner releases the slot and may recycle it immediately for the next **independent** task. Release does not mean merged, and it does not authorize integration to mutate local slot state.

If a problem is found before integration, use a released slot or another explicitly confirmed safe worktree to attach the same PR head branch, fix it, validate it, and run submit again. If an auto-merge or queue request exists because repository policy required one, cancel or withdraw it through a separately approved remote plan before pushing a correction. If the PR is already merged, create a new correction branch and PR; never rewrite the merged submission or auto-revert it.

## Integrate

Run only in a separately confirmed integration location outside `worktrees/slot-*` and every development bundle. The normal location is the existing original/root repository set under the workspace root. Do not run from or switch a development worktree.

Before any remote write:

1. Confirm `gh auth status`, repository identity, PR number, expected source/base, and exact submitted SHA for every repo.
2. Confirm the runtime merge policy. For direct merge, confirm exactly one allowed strategy flag: `--merge`, `--squash`, or `--rebase`. When repository policy requires a merge queue, confirm that fact and omit a direct strategy flag as required by `gh`; do not assume queue mode for other repositories.
3. Run the read-only helper:

   ```bash
   python3 "<skill-dir>/scripts/inspect_pr_submission.py" \
     --repo "<owner/repo>" --pr "<number-or-url>" --base "<source-branch>"
   ```

4. Require an open non-Draft PR, current head equal to the latest submitted-SHA comment, the correct base, and no known merge conflict. Do not independently require a `merge-ready` label, generic review approval, generic status checks, PR `updatedAt` equality, or `mergeStateStatus=CLEAN`. Inspect checks or reviews only when confirmed repository policy makes them relevant to explaining why a merge is blocked.
5. Preflight every repo before merging any PR. Present exact repository, PR, base, current head SHA, dependency stage, confirmed policy and strategy, and command; receive approval for that exact batch.
6. For direct merge, execute with head protection and the confirmed strategy:

   ```bash
   gh pr merge "<pr>" --repo "<owner/repo>" \
     --match-head-commit "<submitted-sha>" "<confirmed-strategy-flag>"
   ```

Do not add `--auto`, `--admin`, or `--delete-branch`. If a confirmed merge queue is mandatory, use the queue-compatible command only after repository-required admission conditions are met; do not enable auto-merge as a workaround. If GitHub rejects a merge because of protection, checks, reviews, conflict, or policy, stop and report the exact blocker instead of bypassing it or claiming success.

Re-inspect immediately before each merge. A moved head or newer submitted marker invalidates approval; stop and require a correction submit and a new integrate plan. Integration does not release slots, edit development worktrees, locally merge source branches, or ask to push source branches afterward. GitHub owns the source update created by the explicit merge command.

## Dependencies And Partial Remote Results

Independent PRs may be prepared concurrently. For a dependent consumer, a provider merge request or queue admission is not enough: verify the provider PR is actually merged into the expected source branch before merging the consumer.

Remote multi-repo work is not atomic. If one push/PR merge succeeds and a later repo fails, report:

- `completed`: remote changes already applied
- `failed`: the repo and exact failing operation
- `untouched`: repos not started
- overall status: `recovery-required`

Never auto-revert a merged provider, auto-reset branches, or claim rollback succeeded. Build a new exact recovery plan and obtain new approval.

## Merge

Confirm that the source branch is the user-confirmed destination for each derived branch. Require committed intended changes and clean source and derived worktrees.

Use the worktree where the source branch is already checked out. Do not switch another worktree to that branch merely to standardize commands. Plan:

```bash
git -C "<source-worktree>" merge "<derived-branch>"
```

Before execution, state whether fast-forward and merge commits are allowed by user intent or repo policy. Do not invent `--ff-only`, `--no-ff`, or rebase policy.

On conflict, stop. Do not resolve, continue, skip, or abort unless that action was part of the approved conflict strategy or the user gives new approval. Report repos already merged, the failing repo, untouched repos, and current Git state.

After all requested merges succeed:

1. Report merged and skipped repos, resulting source branches and HEADs, conflicts, and validation blockers.
2. Report known upstream or push targets separately.
3. Ask `push까지 진행할까요?`.

Never include `git push` in the merge command batch. Do not ask to push a mixed or conflicted result unless the user explicitly requests a subset push plan.

## Sync

Sync committed source-branch changes into each derived branch. Default to merge unless the user requests rebase or repository policy requires it.

Use the worktree where the derived branch is already checked out. For merge, plan:

```bash
git -C "<derived-worktree>" merge "<source-branch>"
```

For rebase, explain commit rewriting and force-push implications before approval. Never select rebase solely because it makes history linear.

On conflict, stop and report completed, failing, and untouched repos. Do not continue with unaffected repos unless the user approves a revised subset plan.

## Plan And Result Reporting

Before a write, show:

| Repo | Source Branch | Derived Branch | Operation | Dirty | Upstream | Risk |
| --- | --- | --- | --- | --- | --- | --- |

Then show:

- exact worktree paths
- exact commands in execution order
- fast-forward, merge-commit, or rebase policy
- conflict stop/abort behavior
- validation to run after each repo or after the batch

After execution, distinguish completed, skipped, failed, and untouched repositories. Never describe a partially completed batch as fully successful.
