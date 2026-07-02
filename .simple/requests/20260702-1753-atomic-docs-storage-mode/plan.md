# Plan

## Summary

atomic-docs의 문서 저장 방식 계약을 submodule 전용에서 선택형으로 바꾼다. 사용자는 atomic-docs 시작 또는 docs root 설정 시 `submodule` 모드와 `repository` 모드 중 하나를 선택할 수 있어야 한다. 기존 사용 프로젝트는 없으므로 backward-compatible migration은 범위에 포함하지 않고, misleading한 submodule 전용 config/문구는 새 계약에 맞게 정리한다.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| REQ-001 | Update the atomic-docs skill contract so users can choose `submodule` or `repository` storage mode during docs root setup, while keeping writes inside the confirmed managed docs root. |
| REQ-002 | Remove migration/backward-compatibility work from scope and replace submodule-only config naming with a neutral new config contract such as `.stageflow/atomic-docs.json`. |
| REQ-003 | Update atomic-docs references, plugin prompts, and tests so storage-mode wording is consistent across discovery, config, refresh, language policy, Stageflow integration, and marketplace-facing prompts. |
| REQ-004 | Validate the Simple Workflow artifacts with the installed Simple Workflow plugin validator using `--root` for this repository, then validate implementation with focused and full unit tests. |

### REQ-001: atomic-docs는 문서 저장 방식을 선택할 수 있어야 한다.

- `skills/atomic-docs/SKILL.md`의 설명, Core Contract, Normal Operation, Boundaries에서 "configured documentation submodule" 전제를 "configured managed docs root"와 저장 모드 선택 계약으로 바꾼다.
- 저장 모드는 `submodule`과 `repository`를 명시한다.
- `submodule` 모드는 `.gitmodules` 후보를 발견하고 사용자 확인 후 선택하는 흐름을 유지한다.
- `repository` 모드는 `.gitmodules`가 없어도 사용자가 지정한 일반 repository-local 경로를 managed docs root로 선택할 수 있게 문서화한다.
- docs 출력은 선택된 managed docs root 내부에만 쓰도록 유지한다.

### REQ-002: 기존 사용 프로젝트 호환이나 마이그레이션은 고려하지 않는다.

- 기존 `.stageflow/docs-submodule.json` 명칭을 유지하기 위한 migration, fallback, dual-read 정책은 추가하지 않는다.
- 새 config 이름은 submodule 전용 의미를 제거한 neutral name으로 정한다. 기본 계획은 `.stageflow/atomic-docs.json`이다.
- 테스트도 새 계약만 검증하도록 갱신하고, 이전 config 이름을 요구하는 assertion은 제거하거나 새 이름으로 바꾼다.

### REQ-003: atomic-docs references와 plugin prompts가 새 계약을 일관되게 설명해야 한다.

- `skills/atomic-docs/references/docs-root-and-config.md`를 docs root/storage mode discovery 문서로 갱신한다.
- `skills/atomic-docs/references/refresh-flow.md`, `language-policy.md`, `atomic-document-contract.md`, `stageflow-integration.md`에서 submodule-only 문구를 managed docs root/storage mode 문구로 바꾼다.
- `skills/atomic-docs/agents/openai.yaml`과 `.codex-plugin/plugin.json`의 submodule-backed prompt/description을 storage-mode-neutral wording으로 바꾼다.
- tests에서 새 prompts와 storage mode config 필드가 검증되도록 갱신한다.

### REQ-004: 검증은 기존 테스트 중심으로 수행한다.

- `tests/test_docs_skill.py`에서 docs root config contract, write approval, refresh flow, language policy, Stageflow integration, plugin manifest expectations를 새 storage mode 계약에 맞게 수정한다.
- 가능하면 전체 Python unittest를 실행한다.
- Simple Workflow 검증은 설치된 Simple Workflow 플러그인 캐시의 `scripts/validate_simple_workflow.py`를 실행하고, `--root /home/kgh-wsl/projects/stage-flow-plugin`으로 이 target repository를 넘겨 수행한다.
- validator를 이 target repository의 `scripts/`에서 찾는 방식은 사용하지 않는다.

## Change Targets

- `.simple/requests/20260702-1753-atomic-docs-storage-mode/plan.md`
- `.simple/requests/20260702-1753-atomic-docs-storage-mode/review.md`
- `skills/atomic-docs/SKILL.md`
- `skills/atomic-docs/references/docs-root-and-config.md`
- `skills/atomic-docs/references/refresh-flow.md`
- `skills/atomic-docs/references/language-policy.md`
- `skills/atomic-docs/references/atomic-document-contract.md`
- `skills/atomic-docs/references/stageflow-integration.md`
- `skills/atomic-docs/agents/openai.yaml`
- `.codex-plugin/plugin.json`
- `tests/test_docs_skill.py`

## Flow Check

No blocking workflow-level problem is expected. The requested work changes the atomic-docs workflow contract itself, so implementation must update tests and references together. There is no migration gate because the user explicitly said existing user-project compatibility does not need to be considered. Simple Workflow validation must use the installed plugin validator with this repository passed as `--root`; this target repository is not the Simple Workflow plugin install location. The main assumption is that `repository` mode means a normal directory inside the target repository, not a separate external repository; if the user means a separate standalone repository, the plan should be corrected before implementation approval.

## Validation

- Run `python3 /home/kgh-wsl/.codex/plugins/cache/simple-workflow-local/simple-workflow-plugin/0.1.17/scripts/validate_simple_workflow.py --root /home/kgh-wsl/projects/stage-flow-plugin --current --session-id default --phase plan` before review.
- Run `python3 /home/kgh-wsl/.codex/plugins/cache/simple-workflow-local/simple-workflow-plugin/0.1.17/scripts/validate_simple_workflow.py --root /home/kgh-wsl/projects/stage-flow-plugin --current --session-id default --phase review` after review.
- Run `python -m unittest tests.test_docs_skill`.
- Run `python -m unittest` if the focused docs tests pass.
- Inspect remaining `submodule-backed`, `documentation submodule`, `docs-submodule`, and `.stageflow/docs-submodule.json` references and keep only those that explicitly describe the `submodule` storage mode.
- Do not search this target repository's `scripts/` directory for Simple Workflow plugin-owned validation scripts.

## Out Of Scope

- Migrating existing `.stageflow/docs-submodule.json` config files.
- Supporting dual config names or backward-compatible fallback reads.
- Creating a real git submodule, creating a remote repository, or generating atomic docs content.
- Changing Stageflow planning behavior outside references needed for atomic-docs integration.
