# Docs Root And Config

Atomic Docs configuration lives at `<docs-root>/atomic-docs.json`. It is the only permanent Atomic Docs control file and travels with repository or submodule managed docs.

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
- `docs_root` is a portable path relative to the primary project. Its resolved directory must be the config file's parent.
- `source_root` is a portable path relative to the primary project.
- `language` is the selected prose language.
- `last_full_source_commit` is exact JSON `null` before a successful `update all`, then the full lowercase SHA-1 or SHA-256 hash of the latest reconciled source-impact commit on the primary HEAD's first-parent history.
- `auxiliary_sources` is an array. Each item has only `name`, `path`, and `revision`.

An auxiliary `name` is unique lower-kebab text. Its `path` is a portable path relative to the primary project and its pinned `revision` is the full lowercase SHA-1 or SHA-256 hash of a reachable commit in that source root.

Do not add a separate baseline file, primary-project pointer, copied config, or incremental-cursor file. The docs-root config commit is the only source-update starting point. The existing key name remains part of the version-2 key schema.

## Discovery

Run validation and updates from the primary project. Search that contained tree for the exact file name `atomic-docs.json` before parsing JSON. Exactly one regular-file candidate is required; a symbolic link is not a config. `--config <path>` selects that candidate explicitly but does not permit another candidate elsewhere. Reject zero candidates, multiple candidates, a path outside the primary project, another file name, the retired `.stageflow/atomic-docs.json` location, and a config whose parent differs from resolved `docs_root`.

Setup already knows the accepted docs root and creates the config there. Later operations may use the unique candidate or an explicit path. Do not infer a winner from valid JSON, storage mode, path proximity, or an existing `.stageflow` file.

## Storage

With `repository`, `atomic-docs.json` and managed docs are ordinary files under the configured primary-repository directory.

With `submodule`, `docs_root` is the root of one already accepted documentation submodule and `atomic-docs.json` is visible in that repository. One docs root belongs to one primary project. The config remains primary-project-relative metadata; opening the docs repository does not make standalone validation or update supported. If validation is run there, stop and rerun from the primary project root instead of creating the relative paths named by the config. Do not create, commit, or push a submodule, remote, repository, or containing gitlink merely because the mode was selected.

Reject absolute paths, backslashes, empty path components, and `.` or `..` traversal in `docs_root`. `source_root` may be `.` but otherwise follows the same portable-path rules. Auxiliary paths may contain `..` because they are explicitly rooted at the primary project, but they must still be portable relative paths.

## Source Commit Rule

Capture primary `HEAD` as the stable inspection target. Walk its first-parent history and compare each commit with its first parent; compare a root commit with the empty tree. Atomic Docs output means the repository-mode config and managed docs paths, or the documentation-submodule gitlink in submodule mode. A commit is source-impact when that comparison changes any non-output path. A merge is therefore source-impact when its tree differs from its first parent on a non-output path, including source brought in from the merged branch.

For `update all`, require a resolvable target, a clean tracked source tree outside the accepted docs/config write set, at least one source-impact first-parent commit, stable starting and ending `HEAD`, structural validation, and semantic review. Only then write the latest source-impact first-parent commit to `last_full_source_commit`. On failure retain the previous value and explain the exact recovery.

For `update changed`, preserve the configured value and capture current primary `HEAD`. The configured commit must resolve and occur on the target's first-parent history. Before any write, require the current docs-root config and managed docs worktree to be clean; in `submodule` mode also require the documentation submodule worktree and containing gitlink to be clean. Never exempt a pre-existing dirty config, document, or submodule state as though the current operation created it.

Classify every first-parent commit after the configured commit. Handle output as follows:

- A repository-mode config diff is baseline-only when `last_full_source_commit` is the only changed field. Any other config field change stops changed processing for `update all` or an explicit config update with source inspection.
- Files below `docs_root`, or the containing documentation-submodule gitlink in `submodule` mode, are managed-doc output rather than primary source impact. Report them separately, inspect the committed path diff or old-to-new submodule commit diff, and include changed documents in bounded semantic reconciliation without inferring authorship or acceptance.
- When the range contains only config/docs/gitlink output, validate current config/docs, semantically reconcile changed managed docs, report no primary source impact, and retain the previous baseline.

When source-impact commits remain, classify every changed source file under the changed flow. A reviewed conclusion that no managed-doc edit is needed is still a successful changed update. After semantic review, structural validation, and source stability checks pass, write the latest source-impact first-parent commit to `last_full_source_commit`; trailing output-only commits do not advance it. On failure restore the preserved value, validate recovery, and leave the update incomplete.

Auxiliary revisions never move automatically. Resolve every auxiliary locator against the configured revision rather than assuming the current auxiliary worktree is the evidence. When the configured source root is below the Git top level, prefix its repository-relative directory before reading `<revision>:<path>`; the locator itself remains relative to the configured source root. Updating a revision requires an explicit config write and separate source inspection.
