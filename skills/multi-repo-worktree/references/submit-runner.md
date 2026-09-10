# Submit Runner

## Ordinary Submit: Two Calls And Content Review

Resolve `<skill-dir>` from the loaded skill. The workspace is a container of repositories, not itself necessarily a Git repo. Require a manifest-bound slot and an explicit submit request before execution.

1. Run one read-only preflight:

```bash
python3 "<skill-dir>/scripts/submit_bundle.py" --root "<workspace-root>" \
  --bundle "worktrees/<slot>"
```

This resolves the manifest before Git discovery. It inspects every repository in that bundle, checks other registered worktrees only for relevant branch occupancy, and reports compact per-repository paths, changed file names, PR classification, exact HEAD/source SHA, generation, and snapshot fingerprints. It does not fetch, lock, write receipts, or migrate the manifest. Do not additionally run workspace-wide inspection, manifest dumps, or hand-written PR classification commands.

2. Review task content and repository commit/test conventions. Read only the actual staged/unstaged/untracked task diffs and relevant context; preflight lists names, not semantic content. Prepare a JSON plan outside the target repositories, for example `.stageflow-worktrees/submit-plans/<slot>.json`. Copy the preflight snapshot fields exactly; do not reconstruct or invent hashes. If content changed while reviewing, refresh the affected review before taking a new snapshot.

```json
{
  "repositories": {
    "events-web": {
      "expected_head": "<head_sha>",
      "expected_generation": 0,
      "expected_branch": "<branch>",
      "expected_worktree": "<worktree_fingerprint>",
      "expected_remote": "<remote_key>",
      "expected_identity": "<identity_fingerprint>",
      "paths": ["src/example.ts", "tests/example.test.ts"],
      "commit_message": "행사 검색 조건 유지",
      "transfer_subject": "행사 검색 조건 유지",
      "pr_title": "행사 검색 조건 유지",
      "pr_body": "검색 화면을 다시 열 때 이전 조건을 복원합니다. 관련 테스트를 실행했습니다.",
      "validation": [["npm", "test", "--", "--runInBand"]]
    }
  }
}
```

`expected_generation` copies the manifest PR generation, not the branch generation. `paths` are exact repository-relative files (both old and new paths for renames), never directory selections or Git wildcard/pathspec expressions. The runner treats them literally. All selected content must have been reviewed; ask about secrets or unrelated/ambiguous content rather than widening paths. A staged unrelated file blocks the repository before commit. Unselected dirty content also blocks ordinary automated submit; do not stash or discard it to force progress.

Only include intended repositories in the plan. Full-bundle preflight still runs before execution; a blocked/missing repository is reported independently while proven siblings may proceed. Ordinary OPEN repositories can have reviewed future work committed locally, but are never pushed. Explicit PR correction does **not** use this runner: follow the isolated correction procedure in `worktree-operations.md`.

The agent supplies Korean commit/title/body text and, when a nonempty rotation may occur, an outcome-focused `transfer_subject` following repository conventions. It must describe transferred future work, not branch movement. The script cannot judge relevance, secrets, natural-language quality, or test sufficiency.

3. Give the concise non-blocking pre-publication summary required by the skill, then execute once:

```bash
python3 "<skill-dir>/scripts/submit_bundle.py" --root "<workspace-root>" \
  --bundle "worktrees/<slot>" --plan "<absolute-plan.json>" --execute
```

Routine writes need no extra question after an explicit submit request. The runner repeats bounded machine checks, not the agent's content review. It uses one slot operation lock and continues independently eligible repositories. Do not replace failures with a blanket manual command sequence or a blind retry loop.

## Execution And Recovery

The runner performs snapshot checks → exact-path commit → source fetch/pin → existing journaled rotation when needed → validation → publication recheck → create-only push → ready PR creation → exact verification → immediate repository record.

- Validation's HEAD is pinned through publication. A new clean commit after testing is not silently adopted. Hooks run normally; a hook changing the staged tree/history blocks publication. The runner never amends or resets that local commit.
- `NONE` rotates if source advanced. Unrotated `MERGED` transfers only continuation work using the immutable submitted boundary; squash merges are supported. Rotation delegates to the existing helpers/journal, including old **local** generation retirement. A zero diff is `NO_DIFF`, not an empty PR.
- `OPEN` returns `WAITING` with no push and unchanged PR/boundary. CLOSED, Draft, unknown/mismatched PRs and incompletely proven legacy state fail locally.
- Immediately before publication, verify manifest/lock/path, remote mapping, branch, reviewed/tested HEAD, source and remote head, and PR identity. One compatible source advance before publication intent is saved may refetch, rotate, and revalidate once. Repeated drift stops that repository.
- A new branch uses an **empty expected-ref lease**: it can only be created if absent, even if another actor races to create an ancestor ref. This never force-updates an existing branch. An already-present ref must equal the exact saved SHA; no branch rewrite, remote deletion, merge, or auto-merge occurs.
- Before push, persist an exact pending publication under `.stageflow-worktrees/submissions/`. A failed push/create response may mean the remote write succeeded. On the next invocation, recover this pending submission **before any new commit/rotation**, even when the worktree already has continuation B. Adopt only one ready PR with the exact repository/base/head/SHA/files/patch; never mix B into A.
- If source advanced during recovery and A was published, preserve A's head. Fetch and prove compatible source ancestry plus an unchanged exact three-dot patch before re-verifying the PR at the new base. If not yet published, replan only when the saved head is still clean and no B exists. Ambiguous heads, changed patches, incompatible source history, and stale locks require the existing narrow recovery decision; never erase a pending receipt to bypass them.
- Record each verified PR immediately with its head as both boundary and observed head. Persist verification before recording so a crash between manifest success and receipt clearing can be recognized as already recorded. Prior merged PR evidence remains in `pending_remote_cleanups`; only a later explicit `sync` deletes those remote refs.

An execution failure may leave a normal local task commit or an exact rotation journal. Preserve it. Use the next preflight to refresh a plan after reviewing any changed basis; already-published pending work resumes automatically without consuming newly selected work. A hard process kill may leave the existing slot operation lock; do not clear an unproven stale lock automatically.

## PR Verification

`scripts/verify_pr.py` is the shared read-only verifier. It checks exact GitHub repository/base/head/head SHA and pinned base SHA, the complete paginated file list, and a deterministic local three-dot patch against the PR's raw diff. It rechecks metadata after reading files/patch to detect a moving PR.

Only these presentation differences are accepted:

- abbreviated `index` object hashes, with matching prefixes and unchanged modes;
- the trailing function label after a hunk's unchanged numeric ranges.

Code whitespace, CRLF, EOF markers, file names, additions/deletions, rename metadata, modes, and binary data are not normalized away. No whitespace-insensitive patch-id, `strip()`, loose changed-line count, or visual-only approval. Truncated API output or an unavailable/non-comparable binary patch fails closed; report the exact exception rather than repeatedly reading full diffs or weakening the comparison. Current API adapter supports same-repository PRs on `github.com`; Enterprise/forks need explicit adapter support, not guessed identity.

For a standalone exception check:

```bash
python3 "<skill-dir>/scripts/verify_pr.py" --repo "<worktree>" \
  --repository "<owner/repo>" --pr "<exact-pr-url>" --base "<source-branch>" \
  --head "<head-branch>" --source-sha "<pinned-source>" --head-sha "<submitted-head>"
```

## Validation And Compact Results

`validation` is a list of argv arrays, executed without a shell in the repository. Do not put `cd`, pipes, chained commands, or shell substitutions in a string. The default per-command timeout is 900 seconds; `validation_timeout_seconds` may set 1–3600. An empty list requires a meaningful `validation_not_applicable` reason, never a speed shortcut.

Validation runs by default. Optional `--reuse-validation` additionally requires a `validation_context` supplied by the caller to identify external test inputs (toolchain/dependency installation/environment/services). Reuse requires identical HEAD (all tracked code/tests/config), pinned source SHA, command arguments, Git configuration, process environment hash, and context. Changed, failed, or dirty/generated tracked/untracked input does not reuse success. Ignored files/external services are not automatically content-hashed: omit reuse when their equivalence cannot be proven; never guess a context string. No environment values are stored, only the combined hash.

The JSON result returns `SUBMITTED`, `RECORDED`, `WAITING`, `NO_DIFF`, or `FAILED` per repository, exact PR links, a bounded error, phase durations, attempt/retry counts, and the local receipt path. Preflight failures use `BLOCKED`. Exit status is nonzero if any repository or bundle target is unresolved, without undoing successful siblings. Phase times include nested work; use the repository total for wall-clock reporting rather than adding parent and child times.

Summarize submitted PRs, waits, and actionable failures. Do not dump full worktree inventories, API payloads, test logs, or patches after success. The speed gain is fewer agent decisions/tool round trips; it does not skip meaningful tests or promise a fixed production runtime.
