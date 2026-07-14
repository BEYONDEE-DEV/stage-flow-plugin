# Criteria Flow

## Responsibility

This reference owns bootstrap sequencing, requested discovery scope, reviewer invocation and revision cycles, and the combined user approval handoff. `atomization-criteria-contract.md` owns criteria content; `source-convention-and-domain-policy.md` owns domain-candidate validity and boundary failures; `docs-generation-flow.md` owns operation-state fields and Goal transition.

## First Setup And Draft

Explain criteria bootstrap as preparation before real atom writing. In Korean interactions, use this shape for repository storage:

- atomic docs를 처음 준비하는 단계입니다.
- 별도 submodule 없이 현재 repository 안의 `<doc-root>` 폴더에 문서를 저장합니다.
- `atomic docs 설정 파일` `.stageflow/atomic-docs.json`과 `문서 작성 기준 초안` `<doc-root>/project/atomization-criteria.md`을 준비하고, 소스를 도메인 경계 수준으로 살펴 도메인 구성을 함께 제안합니다.
- 작성 기준, 도메인 경계, 실제 작성할 도메인을 함께 확인하고 승인하면 그 범위의 atom 문서 작성을 시작합니다.

Do not reduce this message to raw `storage_mode`, `docs_root`, or write-path key/value lines.

When criteria are needed, make `<doc-root>/project/atomization-criteria.md` the first managed-docs write. If the request selects storage mode, docs root, and project-wide or targeted discovery and asks to start, redo, regenerate, or recreate atomic docs, treat it as accepted bootstrap scope. Otherwise explain and confirm that narrow scope first.

Accepted bootstrap scope may create or update config, criteria, Atomic Docs request state, `work-state.json`, one domain-only `inventory.md`, and the compact bootstrap review result. It does not authorize `evidence.md`, Atom candidates, project/context docs, graph edges, domain writer bundles, or baseline metadata.

## Domain Proposal Discovery

Confirm the requested discovery scope before source inspection. For project-wide setup, inspect every project-native feature area only far enough to propose durable domains. For targeted setup, inspect the requested feature and adjacent ownership or shared-contract surfaces. Create operation state under `.stageflow/atomic-docs/requests/<request-id>/` and record `source_commit_observed`, requested discovery scope, and empty accepted scope under `docs-generation-flow.md`.

Write domain candidates only to operation-local `inventory.md`. Each proposal includes project-native name, tentative path, durable responsibility, important exclusion, adjacent boundary, the smallest representative source locator plus one concise observed-boundary summary, and a status display mirrored from authoritative `work-state.json`. Follow the detailed candidate and broad-boundary contract in `source-convention-and-domain-policy.md`.

Do not create `evidence.md`, candidate `atom_key` values, split proposals, behavior-level rows, field/payload/branch/state/failure/test inventories, or queues before combined approval. Reading adjacent source to judge a boundary is allowed; persisting those details as a proposal artifact is not. Never copy the candidate map into criteria.

## Bootstrap Review Gate

Run one independent bootstrap reviewer and reuse it for revision cycles. First review criteria structure against `atomization-criteria-contract.md` without requiring project discovery in the criteria file. Then review the domain proposal and its representative source against the boundary rules in `source-convention-and-domain-policy.md`.

If either review FAILs, revise only the affected criteria or proposal content and rerun that perspective. Continue until both PASS or until a boundary cannot PASS without a user ownership decision. In the latter case, update that domain to `needs_confirmation` in `work-state.json`, then synchronize the inventory projection; it is not eligible for approval or writing. Any status mismatch is a bootstrap review FAIL. Review is part of accepted bootstrap scope and does not require a Codex Goal or separate approval.

Both PASS results mean the criteria and proposal are ready for user judgment; they do not approve either one.

## User Approval Handoff

After both bootstrap reviews PASS, provide the criteria path and a decision-ready Korean summary containing:

- `문서 작성 기준의 핵심 원칙`
- `이 프로젝트에만 적용할 예외`
- `도메인 후보별 책임, 제외 범위, 인접 경계와 대표 소스 근거`
- `승인 가능한 도메인과 소유권 결정이 필요한 도메인`
- `실제로 작성할 도메인 선택`
- `지금 승인하면 시작되는 작업과 아직 만들지 않은 Atom 문서`
- project-wide initial docs이면 `전체 승인 시 source baseline 생성까지 포함하는지`

For Korean handoff, use a compact table shaped as `도메인 후보 | 책임 | 제외 범위 | 인접 경계 | 대표 소스 근거 | 상태/미해결 질문`. Do not ask for approval with only a path, generic criteria summary, or raw internal status.

Treat the user's response as one combined decision over criteria, source-supported domain boundaries, and selected domain write scope. Partial approval is valid: set selected candidates to `approved` and put only their approved tentative domain paths in accepted scope; keep unselected candidates outside scope and keep `needs_confirmation` domains blocked without stopping approved domains.

After combined approval, mark criteria user-approved, remove obsolete draft notes, and continue the same Atomic Docs request. Project-wide bootstrap discovery with only some domains approved becomes a `targeted` execution and cannot create a global baseline. Full approval selects `initial-baseline` only when the handoff explicitly included baseline creation and the user approved that action. Say first that `문서 작성 기준과 선택한 도메인 경계는 승인됐고, 아직 실제 Atom 문서는 작성하지 않았다`. Do not ask for the same write scope again or present the Goal as a user action; create the Goal internally, then begin Atom-candidate and detailed-evidence work.

If later discovery adds a domain or materially changes an approved responsibility, exclusion, or adjacent boundary, rerun the affected boundary review and obtain approval for that changed domain before adding it to accepted scope. Unchanged approved domains keep their approval.
