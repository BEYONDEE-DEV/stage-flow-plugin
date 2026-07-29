# Docs Root And Config

Atomic Docs configuration lives at `.stageflow/atomic-docs.json` in the primary project. It is the only permanent Atomic Docs control file.

## Exact Schema

```json
{
  "version": 2,
  "storage_mode": "repository",
  "docs_root": "docs/atomic",
  "source_root": ".",
  "language": "ko",
  "last_full_source_commit": null,
  "auxiliary_sources": [
    {
      "name": "shared-contracts",
      "path": "../shared-contracts",
      "revision": "0123456789abcdef0123456789abcdef01234567"
    }
  ]
}
```

All seven top-level keys are required and no extra key is allowed.

- `version` is integer `2`.
- `storage_mode` is `repository` or `submodule`.
- `docs_root` is a portable path relative to the primary project.
- `source_root` is a portable path relative to the primary project.
- `language` is the selected prose language.
- `last_full_source_commit` is exact JSON `null` before a successful `update all`, then the full lowercase SHA-1 or SHA-256 hash of a reachable primary-source commit.
- `auxiliary_sources` is an array. Each item has only `name`, `path`, and `revision`.

An auxiliary `name` is unique lower-kebab text. Its `path` is a portable path relative to the primary project and its pinned `revision` is the full lowercase SHA-1 or SHA-256 hash of a reachable commit in that source root.

Do not add a separate baseline file. The config commit is the only full-update starting point.

## Storage

With `repository`, managed docs are ordinary files in the primary repository.

With `submodule`, `docs_root` points inside an already accepted documentation submodule. Do not create a submodule, remote, or repository merely because the mode was selected. Confirm that the configured path is the intended write target.

Reject absolute paths, backslashes, empty path components, and `.` or `..` traversal in `docs_root`. `source_root` may be `.` but otherwise follows the same portable-path rules. Auxiliary paths may contain `..` because they are explicitly rooted at the primary project, but they must still be portable relative paths.

## Full-Update Commit Rule

Before `update all`, capture the primary source `HEAD`. Require:

- `HEAD` resolves to a commit
- the tracked source tree is clean, excluding the accepted managed-doc/config write set
- ending `HEAD` equals starting `HEAD`
- the tracked source tree still satisfies the same clean rule
- structural validation and semantic review pass

Only then write the captured commit to `last_full_source_commit`. If any check fails, retain the previous value and explain the exact recovery: stabilize `HEAD`, clean or commit source changes, correct docs, or rerun `update all`.

For `update changed`, the configured commit must resolve and be an ancestor of current primary `HEAD`. Otherwise stop rather than silently choosing another baseline.

Auxiliary revisions never move automatically. Resolve every auxiliary locator against the configured revision rather than assuming the current auxiliary worktree is the evidence. When the configured source root is below the Git top level, prefix its repository-relative directory before reading `<revision>:<path>`; the locator itself remains relative to the configured source root. Updating a revision requires an explicit config write and separate source inspection.
