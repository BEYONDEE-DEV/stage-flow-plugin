# Criteria Flow

## First Setup And Draft

Explain criteria bootstrap as preparation before real atom writing. In Korean interactions, use this shape for repository storage:

- atomic docs를 처음 준비하는 단계입니다.
- 별도 submodule 없이 현재 repository 안의 `<doc-root>` 폴더에 문서를 저장합니다.
- 이번에는 `atomic docs 설정 파일` `.stageflow/atomic-docs.json`과 `문서 작성 기준 초안` `<doc-root>/project/atomization-criteria.md`만 만들거나 갱신합니다.
- 이 초안을 확인하고 승인하면 실제 atom 문서 작성을 시작할 수 있습니다.

Do not reduce this message to raw `storage_mode`, `docs_root`, or write-path key/value lines.

When criteria are needed, make `<doc-root>/project/atomization-criteria.md` the first managed-docs write. If the request explicitly selects storage mode and docs root and asks to start, redo, regenerate, or recreate atomic docs, treat it as accepted bootstrap scope for only config and criteria. Otherwise present that narrow change before writing.

Bootstrap must not create project goal/glossary/source convention, inventories, evidence indexes, domain maps, atom candidates, common/domain atoms, graph edges, domain agents, or baseline metadata.

Write only the compact durable sections from `atomization-criteria-contract.md`. Record user-stated goals, prohibitions, project exceptions, and approval blockers without copying complete skill rules or reference examples.

## Narrow Evidence Check

Do not perform project-wide source discovery, feature inventory, domain discovery, atom candidate discovery, ownership prepass, or aggregate disposition during criteria bootstrap. Those belong after criteria approval, accepted docs scope, and the Goal handoff.

Inspect source during bootstrap only when a user criterion names a specific code boundary and a narrow check is necessary to phrase that durable rule accurately. Use temporary locators only in the active reviewer context; bootstrap does not persist a separate evidence or state file. Do not promote the inspected surface into a candidate map.

## Criteria Review Gate

Run one independent criteria reviewer after drafting and before asking the user for approval. Reuse that reviewer for revision cycles. Criteria review is part of accepted bootstrap scope and does not require a Codex Goal or separate approval.

Apply the compact failure rules from `atomization-criteria-contract.md`. FAIL only for missing or contradictory durable rules, unclear user language, inaccurate approval state, unsupported inference/action, or leaked operation-local content. Do not FAIL because domain candidates, atom candidates, perspective rows, source coverage, or aggregate dispositions are absent.

If review FAILs, revise only the criteria document and rerun the same reviewer. Continue until PASS or until PASS requires a user decision. PASS means ready for user review; it does not approve the criteria.

## User Approval Handoff

After criteria-review PASS, provide the criteria path and a short decision-ready Korean summary containing:

- `문서 작성 기준의 핵심 원칙`
- `이 프로젝트에만 적용할 예외`
- `아직 결정하지 못해 승인을 막는 내용`
- `지금 승인하면 허용되는 작업과 아직 시작되지 않은 작업`

Do not claim that domains or atoms have already been discovered. State that actual domain candidates, atom candidates, and source evidence will be prepared after the user selects the docs write scope. Do not ask for approval with only a path and generic request.

Wait for criteria approval, then update the approval state and remove obsolete draft notes. Respond first with `문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다`. Ask the user to choose `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, or `기준을 더 수정`. Do not present an internal Goal gate as the user's next action.
