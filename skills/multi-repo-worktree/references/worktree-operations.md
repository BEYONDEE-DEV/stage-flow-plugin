# Worktree Operations

## Contents

- Keyword authorization and decision contract
- Roles and repeated-PR flow
- Permanent slot manifest
- Read-only inspection and status
- Complete-batch preflight
- Create
- Submit common phase
- Submit NONE and OPEN
- Submit MERGED
- Retry and partial results
- Pull
- Sync

## Keyword Authorization And Decision Contract

Expose only `help`, `status`, `create`, `submit`, `pull`, and `sync`. Do not normalize or advertise removed `recycle`, `integrate`, `merge`, `merge-back`, or `sync-derived` commands.

An explicit request to execute `create`, `submit`, `pull`, or `sync` authorizes that keyword's routine writes. A request for `status`, inspection only, or dry-run remains read-only even when it mentions a write keyword.

For every routine write operation:

1. Inspect all participating repositories and GitHub state without changing either.
2. Resolve repo-specific source branches, fixed task branches, remotes, worktree paths, manifest generations, and current PRs.
3. Preflight the complete batch and classify every changed repo.
4. Send a concise non-blocking commentary summary of exact targets, changed paths, state classification, intended effects, fetch/ref updates, risks, conflict behavior, and partial-failure behavior.
5. Re-inspect relevant local, remote, manifest, and PR state immediately before execution.
6. Execute one repository at a time and stop on the first unplanned failure or conflict.

Do not turn the summary into an approval question. Do not ask again for exact commands, clearly task-related paths, generated Korean commit/PR text, a manifest-proven state flow, or a compatible advancement of the same source branch before branch/index/manifest/remote publication.

Ask one consolidated question only when source/task/remote/path facts are missing or conflict, publish content is secret-bearing/generated/unrelated/ambiguous, scope would materially expand, or destructive/history-rewriting, stale-lock unlock, or conflict recovery is required. A semantic change in permanent identity, generation, PR classification, base, or head stops the current attempt and reports the state; the user may re-invoke the same keyword instead of approving a stale plan.

## Roles And Repeated-PR Flow

```text
create once
  -> develop and validate work A
  -> submit ready PR 1
  -> user merges PR 1 on GitHub
  -> keep the same slot, worktrees, and task branches
  -> develop and validate work B
  -> submit ready PR 2 from the same task branches
  -> repeat
```

- **Development user**: initializes one permanent bundle, develops in its fixed task branches, validates, and runs repeated `submit` or development-worktree `sync` operations.
- **Original user**: runs `pull` only in confirmed original/source worktrees.
- **GitHub user**: manually merges ready PRs outside this skill. The skill neither enables auto-merge nor runs remote merge commands.

`create` is not a task-start command after initialization. A successful submit never releases, clears, reassigns, switches, or deletes the slot. The manifest continues to point at a merged PR until a later submit successfully creates or adopts the next PR.

While PR 1 is OPEN, every commit pushed to its fixed head branch becomes part of PR 1. Git cannot determine whether an ahead commit is a PR 1 correction or work B. To keep work B out of PR 1, leave B local and do not run `submit` or a manual/CI push until PR 1 is merged.

## Permanent Slot Manifest

`<workspace-root>/.stageflow-worktrees/slots.json` owns each fixed slot path and the fixed task branch, source branch, remote, PR generation, and current PR for every repository. It has no owner or `active`/`released` lifecycle.

```json
{
  "schema_version": 3,
  "slots": {
    "slot-1": {
      "path": "/absolute/worktrees/slot-1",
      "repositories": {
        "service-a": {
          "branch": "feature-etc-docs",
          "source_branch": "feature-etc",
          "remote": "origin",
          "generation": 1,
          "pr": "https://github.com/example/service-a/pull/17"
        }
      }
    }
  }
}
```

Generation `0` requires `pr: null` and proves that no PR has been recorded yet. Every positive generation requires a non-empty current PR. Do not infer `NONE` merely from a missing field. A new schema-3 `create` requires non-empty source branch and remote for every repository.

The helper reads a schema-2 permanent manifest as schema 3 with paired `source_branch: null` and `remote: null` legacy context without writing the file. `status`, inspection, and dry-run must leave manifest bytes unchanged. Before a selected legacy slot performs a routine write, prove every missing context from exact recorded-PR base plus one repository-matching remote, or ask once for only the unproven facts. Then fill the complete selected slot atomically with `bind-context`; sibling legacy slots may remain nullable. Never partially bind a slot or overwrite a non-null context. Legacy schema 1 manifests used task ownership and release semantics; fail closed with the helper's explicit legacy error.

Use the helper relative to the loaded skill directory:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" status

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  initialize --slot "<slot>" --path "<slot-path>" \
  --repository "<repo-a>" "<fixed-task-branch-a>" "<source-branch-a>" "<remote-a>" \
  --repository "<repo-b>" "<fixed-task-branch-b>" "<source-branch-b>" "<remote-b>"

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  bind-context --slot "<legacy-slot>" \
  --repository-context "<repo-a>" "<source-branch-a>" "<remote-a>" \
  --repository-context "<repo-b>" "<source-branch-b>" "<remote-b>"

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  lock --slot "<slot>" --token "<unique-submit-token>"

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  lock-status --slot "<slot>"

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  record-batch --slot "<slot>" --token "<unique-submit-token>" \
  --expected-generation "<current-generation>" \
  --repository-pr "<repo-a>" "<new-pr-a>" \
  --repository-pr "<repo-b>" "<new-pr-b>"

python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  unlock --slot "<slot>" --token "<unique-submit-token>"
```

`initialize` writes the entire repository binding atomically. An exact repeated call is idempotent and preserves generation/current PR; a different path, repository set, task/source branch, or remote fails closed. An exact retry may fill null context promoted from schema 2. `bind-context` requires every repository in the selected slot, writes them atomically, and is exact-retry idempotent. `record-batch` and operation-lock acquisition require complete context; `record-batch` requires the exact operation lock, compares every participating repository with `--expected-generation`, and updates all new PR pointers in one atomic manifest write. Repeating the exact successful update is idempotent.

The operation lock is separate from slot ownership. Acquire it after complete preflight and before the first submit mutation. A competing token fails immediately. After execution has stopped mutating state, capture the final inspection/report and unlock with the exact token even when recovery is required. A crashed process may leave a lock: show `lock-status`, verify no submit is still running, and ask one explicit recovery question before exact-token unlock; never steal or expire it automatically.

## Read-Only Inspection And Status

Resolve scripts relative to the loaded skill directory:

```bash
python3 "<skill-dir>/scripts/inspect_worktrees.py" \
  --root "<workspace-root>" \
  --bundle "worktrees/<bundle-name>" \
  --json
```

The inspector uses local Git state only. It must not fetch, pull, create/switch branches or worktrees, merge, rebase, push, reset, clean, abort, or delete.

Git does not retain a branch's creation parent. A schema-3 permanent context is authoritative after validation against the actual repository and refs. A unique sibling branch is evidence only; mark it `(추정)`. Use it to enrich a legacy slot without a question only when an exact recorded PR base and one repository-matching remote independently prove the same context; otherwise ask once before a write and persist the answer.

For an identifiable bundle, show:

```text
대상 묶음: worktrees/<bundle-name>
원본 브랜치: <source-branch (추정)|확인 필요>
기준 폴더: <absolute-bundle-folder>

<repo>: 폴더 <relative-folder> / 현재 브랜치 <branch> / 변경상태 <dirty|clean>
```

Do not use a Markdown table. Add each repo's manifest generation/current PR and any operation lock as secondary lines. Keep upstream, HEAD, locks, prunable state, and operation state out of the primary line; add them only as relevant risk notes. When the user names a bundle, filter to it and do not mix the workspace or sibling bundles.

## Complete-Batch Preflight

Before any write, block the whole plan on:

- ambiguous or inferred-only source-branch mappings
- a slot path, repository set, or fixed task branch that disagrees with the manifest
- unexpected current branches or detached required worktrees
- an in-progress merge, rebase, cherry-pick, revert, or bisect
- operation-relevant dirty state except literal paths proven clearly task-related for a `submit` commit
- unsafe locked/prunable paths or missing required paths
- branches checked out in unexpected worktrees
- missing or ambiguous remotes/upstreams required by the operation
- an existing slot operation lock from another token
- changed repositories with different generation or `NONE`/`OPEN`/`MERGED` classifications
- `CLOSED`, missing/inaccessible recorded PR, Draft PR, head/base mismatch, unknown API state, unexpected remote divergence, or ambiguous retry candidate

Fetch is a Git write because it updates shared remote-tracking refs. Finish local/path/branch/manifest/GitHub preflight before fetch. After fetching all repos, pin every fetched SHA and finish ancestry, divergence, and conflict preflight before changing local branches.

## Create

Use `create` only for the first fixed bundle initialization or an exact retry of that initialization.

Before the first write, resolve each source worktree, source branch, remote, complete repository set, target slot path, target child path, and fixed task branch. If any permanent fact is missing or conflicting, ask one consolidated question; otherwise the explicit `create` request authorizes initialization. Require each new task branch not to exist and each target path to be absent or an exact clean partial result from the same binding.

Send a non-blocking summary, then initialize the complete manifest binding immediately before the first worktree add:

```bash
python3 "<skill-dir>/scripts/slot_manifest.py" --root "<workspace-root>" \
  initialize --slot "<slot>" --path "<slot-path>" \
  --repository "<repo-a>" "<fixed-task-branch-a>" "<source-branch-a>" "<remote-a>" \
  --repository "<repo-b>" "<fixed-task-branch-b>" "<source-branch-b>" "<remote-b>"
```

Then add each new fixed task branch:

```bash
git -C "<source-worktree>" worktree add -b "<fixed-task-branch>" \
  "<target-path>" "<confirmed-source-branch>"
```

If creation stops partway, keep the permanent binding. An exact retry may leave already-correct clean worktrees untouched and add only missing worktrees. A different branch/path/repository set, dirty partial worktree, unexpected existing branch, or ambiguous path blocks. Never switch an existing slot to a new task branch, clear prior PR identity, or use `create` to begin work B.

## Submit Common Phase

Use the manifest and read-only GitHub queries to classify each changed repository before the first branch/index/manifest/remote publication mutation. For a recorded PR:

```bash
gh pr view "<recorded-pr>" --repo "<owner/repo>" \
  --json number,state,isDraft,headRefName,headRefOid,baseRefName,mergedAt,url
```

Classify only:

- `NONE`: manifest generation is exactly `0`, current PR is `null`, and no conflicting PR exists for the fixed head branch.
- `OPEN`: the recorded PR state is `OPEN`, `isDraft` is false, and its base/head branches exactly match the manifest source/fixed task branches.
- `MERGED`: the recorded PR state is `MERGED`, `mergedAt` is non-null, and its base/head branches exactly match.

Treat a non-merged `CLOSED` PR as unsupported, not as `MERGED` or `NONE`. Require all changed repositories to have the same classification and generation. Complete this whole-batch read-only preflight, send the non-blocking execution summary, acquire the operation lock, and re-run the relevant checks before staging or fetching. The explicit `submit` request already authorizes the routine commit, fetch, merge, push, PR, and manifest writes described by the classified flow.

Inspect staged, unstaged, and non-ignored untracked paths. A dirty repo is eligible only when every changed path and patch is clearly part of the current user task and validation covers that content. Any unrelated, generated, secret-bearing, ignored-only, or ambiguous change blocks the whole batch before staging and triggers one consolidated content-scope question. Existing staged changes are not automatically trusted; inspect them under the same rule.

For each eligible dirty repo, include the exact literal path list and generated Korean commit message in the non-blocking summary. Keep identifiers or fixed template text verbatim, but write explanatory natural language in Korean. Do not ask for separate path or copy approval. Then:

```bash
git -C "<development-worktree>" add -A -- \
  "<task-path-1>" "<task-path-2>"
git -C "<development-worktree>" diff --cached --check
git -C "<development-worktree>" commit -m "<generated-Korean-commit-message>"
```

Never use broad `git add .`, amend, empty commits, stash, reset, clean, force-add, or bypass hooks. Complete the local commit phase for every repo before the first remote write. Re-inspect the exact branch, clean state, commit diff, manifest, operation lock, PR state, and relevant remote ancestry.

If a commit or hook fails or changes scope, stop before remote writes. Do not undo successful local commits. Record the final state, unlock after no mutation is running, and report recovery-required.

## Submit NONE And OPEN

For `NONE`, require the fixed task branch's local history to contain the manifest source base and reject any conflicting open PR for the head branch. Generate a concise Korean title/body from the current task and inspected change, include them in the non-blocking summary, and push without force:

```bash
git -C "<development-worktree>" push "<remote>" \
  "HEAD:refs/heads/<fixed-task-branch>"
gh pr create --repo "<owner/repo>" --base "<source-branch>" \
  --head "<fixed-task-branch>" --title "<generated-Korean-title>" \
  --body "<generated-Korean-body>"
```

Do not pass `--draft`. After all repositories have created or uniquely adopted their PRs and each PR is OPEN, ready, and exact-base/head/SHA matched, advance generation `0` to `1` with one `record-batch` call.

For `OPEN`, require the PR head SHA to be an ancestor of or equal to the inspected local HEAD and reject remote-only/divergent history. A push publishes every local commit to the current PR:

```bash
git -C "<development-worktree>" push "<remote>" \
  "HEAD:refs/heads/<fixed-task-branch>"
```

Update the same PR branch only. Never run `gh pr edit` during routine `submit`; preserve title/body that a person may have edited. Edit metadata only when the user explicitly requests that specific edit, and then preserve all content outside the requested change. Verify the existing PR remains OPEN, ready, and points to the pushed HEAD. Do not advance generation or create another PR. If there is no commit, ahead SHA, or explicitly requested metadata change, report a no-op.

## Submit MERGED

Require each recorded merged PR's `headRefOid` to be an ancestor of or equal to the current local task branch. A lost or rewritten merged head blocks. For a `MERGED` batch, fetch every manifest remote and pin `refs/remotes/<remote>/<source-branch>` before the common phase's first local commit. Capture whether the fixed remote head exists and its SHA:

```bash
git -C "<development-worktree>" fetch --prune "<remote>"
git -C "<development-worktree>" rev-parse \
  "refs/remotes/<remote>/<source-branch>"
```

Fetch updates shared remote-tracking refs and must be named in the commentary summary. Before the first local commit, compare the remote source ref again. If the same source branch advanced compatibly, fetch, repin, and rerun the complete affected preflight without asking. If permanent context, generation, PR classification, base, or head changed, stop without a branch/index/manifest/remote publication mutation and report the new state.

If the remote task branch exists, require it to be an ancestor of or equal to local HEAD. If it is absent, allow later recreation only because the recorded PR is confirmed MERGED. An OPEN, CLOSED, or unknown recorded PR never permits deleted-head recreation.

After the common commit phase, merge the pinned base into every current fixed task branch. Use the generated Korean merge message when Git creates a merge commit:

```bash
git -C "<development-worktree>" merge "<pinned-base-sha>" \
  -m "기준 브랜치 <source-branch> 동기화"
```

Stop on the first conflict. Do not resolve, continue, skip, abort, or push. Report successful commits/merges in earlier repos and ask only for the conflict-recovery decision. After recovery, the user may invoke the same keyword for exact retry.

After all local merges succeed and validation passes, require the pinned base to be an ancestor of HEAD. Inspect `git diff --check`, name/status, and the patch for `<pinned-base-sha>...HEAD`. Compare them with the exact task-related next-work paths and content from preflight. Old commits from an earlier squash merge may remain in the later PR's Commits list; the required result is that `Files changed` contains only the next work.

If every changed repo has an empty `base...HEAD` diff, do not push, create a PR, or advance the manifest. Report a successful no-op; the local base merge and the current merged PR pointer remain.

Immediately before the first push, query the remote again. Require the source SHA still equal the pinned base and the task ref still equal its expected SHA or still be absent. Because local branch mutation has already begun, any drift now stops before push and reports the exact retry state; it does not start an approval loop or silently repin. Then push each same branch without force and create the next ready PR with generated Korean title/body using the NONE commands.

Verify every created PR:

```bash
gh pr view "<new-pr>" --repo "<owner/repo>" \
  --json number,state,isDraft,headRefName,headRefOid,baseRefName,url
gh pr diff "<new-pr>" --repo "<owner/repo>" --name-only
gh pr diff "<new-pr>" --repo "<owner/repo>" --patch
```

Require OPEN, non-Draft, exact base/head, the pushed HEAD SHA, and a changed-files patch matching the inspected local `pinned-base...HEAD` result. Only after every repo passes may one `record-batch` atomically advance the participating repositories to the next generation and replace current PR pointers.

## Retry And Partial Results

Multi-repo commit, merge, push, and GitHub API operations are not one transaction. On failure, report:

- `completed`: exact local commits/merges, pushed SHAs, created PRs, and recorded pointers
- `failed`: repository and exact operation/local/remote/PR state
- `untouched`: repositories not started
- overall `recovery-required`

Never auto-rollback a commit, base merge, pushed branch, or created PR.

If a PR may have been created before manifest recording failed, list OPEN PRs for the exact base/head:

```bash
gh pr list --repo "<owner/repo>" --state open \
  --base "<source-branch>" --head "<fixed-task-branch>" \
  --json number,state,isDraft,headRefName,headRefOid,baseRefName,url
```

Adopt only one ready OPEN result whose base, head, and `headRefOid` exactly match the inspected pushed SHA. Zero matches means create the missing PR only after rechecking remote SHA. Multiple matches or any identity mismatch blocks without changing the manifest. This rule applies to both initial generation and the next generation after a merged PR.

Keep old current PR pointers until all next PRs are created or adopted and verified. Then retry the idempotent atomic `record-batch`. After execution has stopped and the final state is captured, release the operation lock with the same token. A stale lock from a crashed process requires read-only reconciliation and one explicit unlock-recovery decision; it is never automatic slot release.

## Pull

`pull` runs only from the manifest-bound original/root repository set, with each stored source branch already checked out in its original worktree. It never touches development worktrees. The explicit `pull` request authorizes routine fetch and fast-forward after the non-blocking summary.

Before fetch, require every root to be clean, on the stored source branch, free of in-progress operations, and configured with the stored remote/source ref. Validate that the remote still identifies the expected repository. Then fetch every repo and pin its SHA:

```bash
git -C "<original-worktree>" fetch --prune "<remote>"
git -C "<original-worktree>" merge --ff-only "<pinned-source-sha>"
```

Require the current source HEAD to be an ancestor of the pinned SHA before the fast-forward phase. Do not use plain `git pull`, create merge commits, rebase, reset, switch branches, or update a development worktree. A no-op already at the pinned SHA is successful and retry-safe.

## Sync

`sync` runs only in the requested development bundle. It never runs from an original/root worktree and never updates a root worktree's checked-out state. The explicit `sync` request authorizes routine fetch and merge after the non-blocking summary.

Before fetch, require every derived worktree to be clean, on its manifest-fixed task branch, and free of in-progress operations. Validate each manifest source branch, remote, and repository identity, then:

```bash
git -C "<development-worktree>" fetch --prune "<remote>"
git -C "<development-worktree>" merge "<pinned-source-sha>"
```

Fetching from a linked worktree updates repository-shared objects and remote-tracking refs, but must not switch or update the original worktree's branch, HEAD, index, or files. The original worktree may remain intentionally stale. `sync` does not invoke `pull`, and the two commands have no required ordering.

On conflict, stop in the failing development worktree. Report its Git state and untouched repos, then ask one conflict-recovery question. Do not resolve, continue, skip, abort, update the original worktree, release the permanent slot, or switch its fixed task branch without that decision.
