# Submit Runner

## Ordinary Submit: Prepare, Review Content, Execute

Resolve `<skill-dir>` from the loaded skill. The workspace is a container of repositories, not itself necessarily a Git repo. Require a manifest-bound slot and an explicit submit request before execution.

1. Prepare a fresh plan and inspect the bundle in one call:

```bash
python3 "<skill-dir>/scripts/submit_bundle.py" --root "<workspace-root>" \
  --bundle "worktrees/<slot>" --prepare
```

This checks every repository's local binding/state and relevant branch occupancy. Remote/PR queries and content snapshots are limited to candidates with dirty files, committed continuation, a rotation journal, or pending publication. Clean non-candidates are `LOCAL_ONLY`, not remotely classified. Use repeatable `--repository <exact-name>` when the user selects repositories explicitly. It never selects unrelated dirty work as approved content.

`--prepare` writes a uniquely named plan under `.stageflow-worktrees/submit-plans/` and returns `plan_path`; it never overwrites a prior plan or changes Git/receipts. Without `--prepare`, preflight remains read-only and returns the plan objects inline. No candidates means no plan file. Do not additionally dump workspace-wide inspection, manifests, or PR classification.

2. Review the actual staged/unstaged/untracked task changes and relevant repository conventions. In the generated plan, keep only intended repositories, confirm the literal `paths`, and fill Korean `commit_message`, `transfer_subject`, `pr_title`, and `pr_body`. The script already filled HEAD, branch, generation and worktree/identity/remote fingerprints: do not copy/reconstruct these mechanically. A new snapshot requires reviewing any intervening changes.

Also review already-committed continuation using `committed_review.boundary_sha..head_sha` and its changed paths, even when `paths` is empty. This is the immutable submission continuation boundary (or generation base), not a fresh guess from an already-corrected PR head.

`expected_generation` copies the manifest PR generation, not the branch generation. `paths` are exact repository-relative files (both old and new paths for renames), never directory selections or Git wildcard/pathspec expressions. The runner treats them literally. All selected content must have been reviewed; ask about secrets or unrelated/ambiguous content rather than widening paths. A staged unrelated file blocks the repository before commit. Unselected dirty content also blocks ordinary automated submit; do not stash or discard it to force progress.

Only include intended repositories in the plan. Execution repeats the full-bundle **local** check, then classifies and revalidates remote state only for selected repositories at their action boundaries. A blocked/missing repository is reported independently while proven siblings may proceed. Ordinary OPEN repositories can have reviewed future work committed locally, but are never pushed. Explicit PR correction does **not** use this runner: follow the isolated correction procedure in `worktree-operations.md`.

The agent owns content relevance, secrets, Korean prose and test sufficiency. `transfer_subject` describes transferred future work, not branch movement. Ordinary submit assumes development validation already completed; do not invent new test commands or rerun tests solely for PR creation. If that assumption is known to be false, say so rather than claiming validation passed.

3. Give the concise non-blocking pre-publication summary required by the skill, then execute once:

```bash
python3 "<skill-dir>/scripts/submit_bundle.py" --root "<workspace-root>" \
  --bundle "worktrees/<slot>" --plan "<absolute-plan.json>" --execute
```

Routine writes need no extra question after an explicit submit request. The runner repeats bounded machine checks, not the agent's content review. It uses one slot operation lock and continues independently eligible repositories. Do not replace failures with a blanket manual command sequence or a blind retry loop.

## Execution And Recovery

The runner performs snapshot checks → exact-path commit → source fetch/pin → existing journaled rotation when needed → validation → publication recheck → create-only push → ready PR creation → exact verification → immediate repository record.

- The reviewed HEAD/tree is pinned through publication even when tests are skipped. A new clean commit is not silently adopted. Hooks run normally; a hook changing the staged tree/history blocks publication. The runner never amends or resets that local commit.
- `NONE` rotates if source advanced. Unrotated `MERGED` transfers only continuation work using the immutable submitted boundary; squash merges are supported. Rotation delegates to the existing helpers/journal, including old **local** generation retirement. A zero diff is `NO_DIFF`, not an empty PR.
- `OPEN` returns `WAITING` with no push and unchanged PR/boundary. CLOSED, Draft, unknown/mismatched PRs and incompletely proven legacy state fail locally.
- Immediately before publication, verify manifest/lock/path, remote mapping, branch, reviewed/tested HEAD, source and remote head, and PR identity. One compatible source advance before publication intent is saved may refetch, rotate, and revalidate once. Repeated drift stops that repository.
- A new branch uses an **empty expected-ref lease**: it can only be created if absent, even if another actor races to create an ancestor ref. This never force-updates an existing branch. An already-present ref must equal the exact saved SHA; no branch rewrite, remote deletion, merge, or auto-merge occurs.
- Before push, persist an exact pending publication under `.stageflow-worktrees/submissions/`. A failed push/create response may mean the remote write succeeded. On the next invocation, recover this pending submission **before any new commit/rotation**, even when the worktree already has continuation B. Adopt only one ready PR with the exact repository/base/head/SHA/files/patch; never mix B into A.
- Persist the PR URL immediately after creation/adoption, before verification. Failures return that URL, `failed_phase`, `error_code` and `recovery_pending`; report those directly instead of searching for the PR again. If the create response itself was lost, normal exact recovery discovers the unique matching PR.
- If pending A was already merged by the user, recovery proves its exact head/identity, the unchanged saved pre-merge patch, and the merge commit's inclusion in the fetched source, then records A as `RECORDED` with `pr_state: MERGED`. It does not recreate a deleted remote branch, publish B, or test dirty B. Unmerged CLOSED/Draft or mismatched PRs still stop. A user-requested `--test` applies to new submissions, not replaying an already-published A during recovery.
- If source advanced during recovery and A was published, preserve A's head. Fetch and prove compatible source ancestry plus an unchanged exact three-dot patch before re-verifying the PR at the new base. If not yet published, replan only when the saved head is still clean and no B exists. Ambiguous heads, changed patches, incompatible source history, and stale locks require the existing narrow recovery decision; never erase a pending receipt to bypass them.
- Record each verified PR immediately with its head as both boundary and observed head. Persist verification before recording so a crash between manifest success and receipt clearing can be recognized as already recorded. Prior merged PR evidence remains in `pending_remote_cleanups`; only a later explicit `sync` deletes those remote refs.

An execution failure may leave a normal local task commit or an exact rotation journal. Preserve it. Use the next preflight to refresh a plan after reviewing any changed basis; already-published pending work resumes automatically without consuming newly selected work. A hard process kill may leave the existing slot operation lock; do not clear an unproven stale lock automatically.

## PR Verification

`scripts/verify_pr.py` checks repository/base/head/full SHAs and the complete paginated file list. It also verifies the full root-tree IDs of the merge base and submitted head against GitHub's immutable Git commit objects. A root tree binds all paths, modes, types and blob contents, including binary additions/replacements/deletions/renames. This avoids binary downloads and truncated recursive tree listings. Text bytes and structural patch metadata are still compared strictly against the PR diff; local comparison uses binary summaries, matching GitHub's display format. Missing patch output never implies a binary file. PR metadata is checked again after verification.

Only these presentation differences are accepted:

- abbreviated `index` object hashes, with matching prefixes and unchanged modes;
- the trailing function label after a hunk's unchanged numeric ranges.

Code whitespace, CRLF, EOF markers, paths, rename metadata and modes are not normalized away. Binary content equality is proven through the full Git tree IDs, not the display summary or abbreviated patch hashes. Incomplete/mismatched object or file responses and truncated text patches fail. Current API adapter supports same-repository PRs on `github.com`; Enterprise/forks need explicit adapter support.

For a standalone exception check:

```bash
python3 "<skill-dir>/scripts/verify_pr.py" --repo "<worktree>" \
  --repository "<owner/repo>" --pr "<exact-pr-url>" --base "<source-branch>" \
  --head "<head-branch>" --source-sha "<pinned-source>" --head-sha "<submitted-head>"
```

For an already-merged PR, pass `--state MERGED` and its recorded PR base SHA. This standalone command verifies only; it never updates submission records.

## Validation And Compact Results

Default `validation_mode` is `if-changed`: no test/build commands are needed for unchanged reviewed content. After source integration, compare the complete file tree with the development/reviewed tree. A different commit SHA with the same tree does not trigger tests. An actual tree change runs only the supplied `validation` argv arrays. Without commands, return `REVALIDATION_REQUIRED` before push/PR creation, preserve local work, and supply appropriate focused commands on retry. The recheck requirement is saved before rotation changes the branch, so a failed/interrupted attempt cannot erase it by refreshing the plan. `NO_DIFF` clears it because there is no remaining submission to validate.

Use `--test` or per-repository `validation_mode: always` only for an explicit request to test at submit. `validation` is optional fallback commands, not a request to run them unconditionally. Commands execute without a shell; no `cd`, pipes or chained strings. Per-command timeout defaults to 900 seconds (`validation_timeout_seconds`: 1–3600). No environment/config fingerprint cache or `--reuse-validation` is used. Tests cannot change tracked/untracked content or the pinned HEAD and then silently publish it.

The JSON result returns `SUBMITTED`, `RECORDED`, `WAITING`, `NO_DIFF`, or `FAILED`, PR links even after post-create failure, phase durations, attempts/retries, and the receipt path. Validation reports whether commands actually ran and why; do not describe assumed development validation as tests executed by submit. Preflight failures use `BLOCKED`. Exit status is nonzero for selected failures or unresolved bundle paths. Parent phase times include children; do not add them together.

Summarize submitted PRs, waits, and actionable failures. Do not dump full worktree inventories, API payloads, test logs, or patches after success. The speed gain is fewer agent decisions/tool round trips; it does not skip meaningful tests or promise a fixed production runtime.
