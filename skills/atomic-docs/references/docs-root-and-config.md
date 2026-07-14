# Docs Root And Config

## Responsibility

This reference defines how the `atomic-docs` skill discovers, confirms, and persists the managed documentation root and storage mode for a target project.

## Discovery Policy

- Do not assume a hardcoded `docs/` root. A project may already have a normal `docs/` folder that is not the managed documentation root.
- If `.stageflow/atomic-docs.json` exists, read it as the configured docs root and storage-mode contract.
- If no configured root exists, ask the user to choose a storage mode before persisting config.
- Supported storage modes are `submodule` and `repository`.
- For `submodule` mode, inspect `.gitmodules` for documentation submodule candidates. If `.gitmodules` has exactly one candidate, still ask the user to confirm it before persisting config. If `.gitmodules` has multiple candidates, present the candidates and ask the user to choose. If `.gitmodules` has no suitable candidate, report that the documentation submodule root is missing and ask for the minimum recovery action.
- For `repository` mode, ask the user to select or confirm a repository-local managed docs root. This root does not need to appear in `.gitmodules`.
- Do not infer `submodule` mode merely because `.gitmodules` exists.
- Do not infer `repository` mode merely because a `docs/` directory exists.

## User-Facing Storage Terms

When explaining docs-root setup to a user, describe what will happen before naming internal config values:

- `repository` means `현재 프로젝트 안의 폴더에 문서를 저장`.
- `submodule` means `별도 문서 저장소/submodule에 문서를 저장`.
- `docs_root` and managed docs root mean `문서 저장 위치`.
- `.stageflow/atomic-docs.json` is the `atomic docs 설정 파일`.

For a first setup where the user chose repository storage and `docs`, explain the scope as: atomic docs를 처음 설정하는 단계이며, 실제 atom 문서를 쓰기 전에 문서 저장 위치와 문서 작성 기준 초안을 준비하고 소스를 도메인 경계 수준으로 살펴 도메인 구성을 제안한다. Then identify the concrete config and criteria paths; explain the operation-local domain proposal in user language before any internal state path.

## Configuration File

Persist the confirmed root and storage mode in target-project config at `.stageflow/atomic-docs.json` only after the user has accepted the docs-root setup scope and config write. This file is project/plugin configuration, not a Stageflow request artifact and not docs refresh evidence.

If the current user request explicitly selects a storage mode, selects a managed docs root, and asks to start, redo, regenerate, or recreate atomic docs, treat that request as accepting the docs-root setup scope and config write for `.stageflow/atomic-docs.json`. That bootstrap acceptance authorizes the paired criteria draft and operation-local domain proposal allowed by `criteria-flow.md`, but no other managed docs.

Required fields:

```json
{
  "storage_mode": "submodule",
  "docs_root": "path/to/managed-docs-root",
  "source_root": ".",
  "baseline_metadata_path": "source-baseline.json"
}
```

- `storage_mode` is either `submodule` or `repository`.
- `docs_root` is the selected managed docs root.
- `source_root` is the source repository root used for diffs. It defaults to the parent repository root and may be overridden by configuration.
- `baseline_metadata_path` is a docs-root-relative path to the metadata file that stores the reviewed project-wide context baseline. The default is `source-baseline.json`; with `docs_root` set to `docs`, this resolves to `docs/source-baseline.json`, not `docs/docs/source-baseline.json`. Partial or targeted operations must not create or update this file.

For `repository` mode, the config shape is the same except `storage_mode` is `repository`:

```json
{
  "storage_mode": "repository",
  "docs_root": "docs",
  "source_root": ".",
  "baseline_metadata_path": "source-baseline.json"
}
```

## Recovery Policy

- If the configured managed docs root is missing or inaccessible, report the state before writing docs.
- In `submodule` mode, also report when the configured docs root is dirty, detached, or not initialized as a submodule.
- In `repository` mode, do not require `.gitmodules` membership or submodule initialization.
- Do not silently create a real submodule, remote repository, repository-local docs directory, or migration. Those are separate user requests.
- Do not write managed docs outside the confirmed managed docs root.
- If the stored source commit hash is not reachable from `source_root`, report uncertainty and ask whether to rebaseline or inspect from the current source state.
- Run the plugin-bundled validator from `<plugin-root>/scripts/validate_atomic_docs.py`; do not look for a validator under the target project's `scripts/` directory.
