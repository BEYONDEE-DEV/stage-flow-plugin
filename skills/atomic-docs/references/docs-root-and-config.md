# Docs Root And Config

## Responsibility

This reference defines how the `atomic-docs` skill discovers, confirms, and persists the documentation submodule root for a target project.

## Discovery Policy

- Do not assume a hardcoded `docs/` root. A project may already have a normal `docs/` folder that is not the managed documentation submodule.
- If `.stageflow/docs-submodule.json` exists, read it as the configured docs root contract.
- If no configured root exists, inspect `.gitmodules` for submodule candidates.
- If `.gitmodules` has exactly one candidate, still ask the user to confirm before persisting it.
- If `.gitmodules` has multiple candidates, present the candidates and ask the user to choose.
- If `.gitmodules` has no suitable candidate, report that the docs submodule root is missing and ask for the minimum recovery action.

## Configuration File

Persist the confirmed root in target-project config at `.stageflow/docs-submodule.json` only after the user has accepted the docs-root setup scope and config write. This file is project/plugin configuration, not a Stageflow request artifact and not docs refresh evidence.

If the current user request explicitly selects a managed docs root and asks to start, redo, or recreate atomic docs, treat that request as accepting the docs-root setup scope and config write for `.stageflow/docs-submodule.json`. That bootstrap acceptance does not authorize any other docs writes except the paired draft criteria atom allowed by `refresh-flow.md`.

Required fields:

```json
{
  "docs_root": "path/to/documentation-submodule",
  "source_root": ".",
  "baseline_metadata_path": "path/inside/docs-root/source-baseline.json"
}
```

- `docs_root` is the selected documentation submodule root.
- `source_root` is the source repository root used for diffs. It defaults to the parent repository root and may be overridden by configuration.
- `baseline_metadata_path` points to the metadata file inside the docs submodule root that stores the last refreshed source-code commit hash.

## Recovery Policy

- If the configured docs root is missing, dirty, inaccessible, detached, or not initialized, report the state before writing docs.
- Do not silently create a real submodule, remote repository, or migration. Those are separate user requests.
- Do not write managed docs outside the confirmed docs submodule root.
- If the stored source commit hash is not reachable from `source_root`, report uncertainty and ask whether to rebaseline or inspect from the current source state.
