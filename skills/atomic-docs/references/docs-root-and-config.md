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
- `last_full_source_commit` is exact JSON `null` before a successful `update all`, then the full lowercase SHA-1 or SHA-256 hash of the reachable primary-source commit last reconciled by a successful `update all` or `update changed`.
- `auxiliary_sources` is an array. Each item has only `name`, `path`, and `revision`.

An auxiliary `name` is unique lower-kebab text. Its `path` is a portable path relative to the primary project and its pinned `revision` is the full lowercase SHA-1 or SHA-256 hash of a reachable commit in that source root.

Do not add a separate baseline file or an incremental-cursor file. The config commit is the only source-update starting point. The existing key name is retained by the version-2 schema; it does not mean that every later successful commit came from another full replacement.

## Storage

With `repository`, managed docs are ordinary files in the primary repository.

With `submodule`, `docs_root` points inside an already accepted documentation submodule. Do not create a submodule, remote, or repository merely because the mode was selected. Confirm that the configured path is the intended write target.

Reject absolute paths, backslashes, empty path components, and `.` or `..` traversal in `docs_root`. `source_root` may be `.` but otherwise follows the same portable-path rules. Auxiliary paths may contain `..` because they are explicitly rooted at the primary project, but they must still be portable relative paths.

## Source Commit Rule

Before `update all`, capture the primary source `HEAD`. Require:

- `HEAD` resolves to a commit
- the tracked source tree is clean, excluding the accepted managed-doc/config write set
- ending `HEAD` equals starting `HEAD`
- the tracked source tree still satisfies the same clean rule
- structural validation and semantic review pass

Only then write the captured commit to `last_full_source_commit`. If any check fails, retain the previous value and explain the exact recovery: stabilize `HEAD`, clean or commit source changes, correct docs, or rerun `update all`.

For `update changed`, preserve the configured value and capture current primary `HEAD`. The configured commit must resolve and be an ancestor of that target. Before any write, require the current control file and managed docs worktree to be clean; in `submodule` mode also require the documentation submodule worktree and its containing gitlink to be clean. Never exempt a pre-existing dirty config, document, or submodule state as though the current operation created it.

Build the primary source-impact range between the two commits, but handle Atomic Docs-owned changes as follows:

- A `.stageflow/atomic-docs.json` diff is self-output only when `last_full_source_commit` is the only changed field. Any other config field change is meaningful configuration and stops changed processing for `update all` or an explicit config update with source inspection.
- Files below `docs_root`, or the containing documentation-submodule gitlink in `submodule` mode, are managed-doc changes rather than primary source impact. Report them separately, inspect the committed managed-doc path diff or old-to-new submodule commit diff, and include the changed documents in bounded semantic reconciliation. Do not infer authorship or prior acceptance from their path.
- When the range contains only baseline/config and managed-doc output, validate current config/docs, semantically reconcile any changed managed docs, report no primary source impact, and do not rewrite the commit value merely to follow those output commits.

When at least one primary source-impact file remains, classify every such file under the changed flow. A reviewed conclusion that none of those source changes requires a managed-doc edit is still a successful changed update. After bounded semantic review, structural validation, and source stability checks pass, set `last_full_source_commit` to the captured target and validate the final config and docs state. If any condition fails, restore the preserved value, validate the recovered state, and leave the update incomplete.

Auxiliary revisions never move automatically. Resolve every auxiliary locator against the configured revision rather than assuming the current auxiliary worktree is the evidence. When the configured source root is below the Git top level, prefix its repository-relative directory before reading `<revision>:<path>`; the locator itself remains relative to the configured source root. Updating a revision requires an explicit config write and separate source inspection.
