# Implementation Plan Writing And Review Rules

## Contents

- [Stage Artifact](#stage-artifact)
- [Stage Responsibility](#stage-responsibility)
- [Request Type Profiles](#request-type-profiles)
- [Technical Design Depth](#technical-design-depth)
- [Definition Fidelity](#definition-fidelity)
- [Flow Completeness Contract](#flow-completeness-contract)
- [Selective Rework After Definition Changes](#selective-rework-after-definition-changes)
- [Language Policy](#language-policy)
- [Stage Artifact Format](#stage-artifact-format)
- [Required Artifact Sections](#required-artifact-sections)
- [Writing And Review Rule Table](#writing-and-review-rule-table)
- [Verification Meaning](#verification-meaning)

## Stage Artifact

Target: `02-implementation-plan/implementation-plan.md`

## Stage Responsibility

The implementation-plan stage maps the approved definition behavior model to a decision-complete technical implementation design. It is the first stage that should name implementation surfaces as work to perform, and it must explain how the work will be built: architecture choice, module responsibilities, control/data flow, edge cases, failure modes, and validation strategy.

Decision-complete means every approved user/system/policy flow that is in scope is closed from trigger to observable completion. A work-item list can be detailed but still fail this stage when the approved flow has an unresolved handoff, missing state/data transition, missing failure or empty-state behavior, or validation evidence that does not prove the flow outcome.

The implementation plan must not create new requirements, new UX policy, new service meaning, new endpoint semantics, or a narrower UX interpretation of ambiguous definition wording. When technical decisions reveal a missing product decision, return to the earlier Stageflow stage instead of silently deciding it here.

Implementation-plan owns the technical decisions that definition must defer: files, modules, components, functions, hooks, scripts, architecture, libraries, packages, schema/type/interface shape, storage/query implementation, control/data-flow implementation, test commands, validation strategy, work item split, and implementation order. Resolve those as implementation-plan assumptions, work items, risks, or validation steps without asking the user unless the answer would change approved service meaning, user-visible behavior, policy, boundary, acceptance outcome, failure/recovery semantics, or service-level data responsibility.

## Request Type Profiles

Use the approved request profile only to shape implementation evidence:

- Feature-heavy work maps service policies to technical architecture, implementation units, and validation scenarios.
- Bugfix-heavy work records the confirmed or likely cause, correction surface, control/data flow change, and regression tests.
- Mixed work maps both desired outcomes and problem resolutions without changing the approved definition model.

## Technical Design Depth

A passing implementation plan must let another agent implement without inventing architecture or flow handoffs. Avoid generic entries such as "code and tests", "implement behavior", or "run tests" as the only implementation guidance. Name the relevant modules, scripts, hooks, validators, schemas, commands, or artifact contracts when they are known from inspection, and connect them to complete implementation flows.

## Definition Fidelity

Read `references/intent-fidelity.md` before planning technical UX, route, screen, state, data, API, or persistence interpretations. The implementation plan must include `## Definition Fidelity Matrix` to prove each work item preserves the approved definition meaning and returns to definition when ambiguous.

When a work item narrows the approved definition to a smaller API/UI/data subset, treats behavior as read-only/manual/future work, or excludes an adjacent capability, the `## Definition Fidelity Matrix` must cite the definition source that approved the narrowing in its `Definition Source` column. The source should be a `DEC-*`, `REQ-*`, `SP-*`, or `INTENT-*` reference from the approved definition. If no such source exists, return to definition instead of turning the narrowing into an implementation-plan assumption.

## Flow Completeness Contract

This contract is the single source of truth for writing and reviewing implementation-plan flow completeness. The implementation-plan review agent must evaluate every `IP-FLOW-*` rule using the same meanings recorded here.

| Rule ID | Flow Rule | Plan Must Record | Reviewer Must Confirm | Blocking Condition |
| --- | --- | --- | --- | --- |
| IP-FLOW-001 | Extract approved definition flows. | `## Implementation Flow Model` records definition source, trigger, target outcome, primary work items, and flow status for each approved user/system/policy flow. | The approved definition's major user, system, policy, and integration flows are not omitted. | An approved major flow is absent from the plan. |
| IP-FLOW-002 | A complete flow must run end to end. | `## Flow Completeness Matrix` records an ordered path for every `complete` flow. | The flow connects trigger -> processing/handoff -> state or data transition -> result exposure without gaps. | The plan leaves a missing handoff, continuation, or completion point. |
| IP-FLOW-003 | State and data transitions belong inside the flow. | The matrix records creation, update, save, query, cache refresh, transaction, no-op, or other meaningful transition for each complete flow. | The implementer does not need to invent state/data behavior while coding. | Work items exist, but state/data transition behavior is unclear. |
| IP-FLOW-004 | Failure and empty states are part of the flow. | The matrix records validation failure, API failure, empty state, permission failure, external consumer responsibility, or equivalent flow-specific failure behavior. | Failure behavior is attached to the affected flow, not hidden as a generic risk. | Failure handling is missing or only says "handle errors". |
| IP-FLOW-005 | Completion must be observable. | The matrix records what a user, admin, system consumer, or test observes to know the flow completed. | Completion can be checked without relying on internal implementation claims. | Completion is only described as "implemented" or "done". |
| IP-FLOW-006 | Validation must prove flow completion. | Validation evidence states which flow outcome it proves. | Commands, tests, manual checks, or review checks connect to the flow outcome. | Validation evidence is generic and not tied to a flow outcome. |
| IP-FLOW-007 | Unresolved gaps must stay visible. | Non-complete flows use `return-to-definition` or `out-of-scope-by-definition` and cite the definition basis. | Unresolved decisions, deferred work, non-applicability, and consumer responsibility match approved definition sources. | A gap is hidden as complete, or a flow is marked non-applicable without source support. |

Do not enforce this contract by banning words. A complete flow may record that a transition is intentionally absent, such as "No state change: read-only lookup flow; observable completion is the returned list." A single placeholder value such as `N/A`, `TBD`, or `미정` is not enough because it does not explain why the gap is valid or how completion is observed.

## Selective Rework After Definition Changes

When the definition is revised after an implementation plan already exists, do not rewrite the whole plan by default. Compare the revised requirements, policy rules, acceptance criteria, and data responsibilities with the current `## Work Items` and `## Coverage Matrix`.

Keep unaffected work items, partially update work items whose technical design still fits but needs adjusted scope or validation, and rewrite only the work items whose service rule coverage is no longer correct. Record the reason in `## Cause Or Design Notes`, update affected `## Work Items`, `## Coverage Matrix`, `## Validation Strategy`, and `## Risks`, then rerun the implementation-plan review and approval gate.


## Language Policy

Read `references/language-policy.md` before writing or revising the implementation-plan artifact. Keep required headings, table columns, rule IDs, paths, commands, and code identifiers unchanged, but write natural-language technical approach, work-item explanations, risk notes, validation explanations, and review evidence in the selected user/artifact language.

For a Korean workflow, new implementation-plan prose should default to Korean. English starter filler such as `Describe...`, `One concrete implementation unit.`, or generic English row prose is not review-ready content unless the selected artifact language is English.

## Stage Artifact Format

```md
# Implementation Plan

## Technical Approach

승인된 definition에 맞는 기술 접근, 검토한 대안, 선택 이유를 설명한다.

## Implementation Architecture

모듈/스크립트/컴포넌트 책임, 호출 흐름, 데이터 흐름, artifact/schema 변경, 호환성 경계를 설명한다.

## Change Areas

구현 단위에서 변경될 코드, 문서, 테스트, 자산을 설명한다.

## Cause Or Design Notes

승인된 definition에 근거한 구현 관련 원인 분석, 설계 제약, 가정만 기록한다.

## Implementation Flow Model

| Flow ID | Definition Source | Trigger Or Entry | Target Outcome | Primary Work Items | Flow Status |
| --- | --- | --- | --- | --- | --- |
| FLOW-001 | REQ-001, SP-001 | 승인된 flow를 시작하는 사용자 또는 시스템 진입점. | 사용자가 보거나 시스템 consumer가 확인하는 완료 결과. | WORK-001 | complete |

## Flow Completeness Matrix

| Flow ID | Ordered Implementation Path | State/Data Transitions | Failure Or Empty States | Observable Completion | Validation Evidence |
| --- | --- | --- | --- | --- | --- |
| FLOW-001 | 진입점 -> 처리/조합 -> 저장 또는 상태 갱신 -> 결과 노출. | 생성, 수정, 조회, 캐시 갱신, no-op 등 flow 안의 의미 있는 변화. | 검증 실패, 빈 상태, 권한 실패, 외부 consumer 책임 등 flow별 실패 동작. | 사용자, 관리자, consumer, 테스트가 확인할 완료 결과. | FLOW-001 완료를 증명하는 테스트, 명령, 수동 확인, 리뷰 증거. |

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | 구체적인 구현 단위 하나. | 정확한 기술 접근, 영향 표면, 변경할 동작, 관련 Flow ID. | 변경된 artifact와 FLOW-001을 증명하는 테스트/리뷰 증거. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | 대상 모듈, 스크립트, 문서, 테스트, 자산. | service rule을 입증하는 구체적인 자동 또는 수동 확인. | 관련 구현 위험 또는 제약. |

## Definition Fidelity Matrix

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | REQ-001, SP-001, INTENT-001 | definition에서 승인된 요구사항 의미. | 승인된 의미를 보존하는 기술 구현. | 승인되지 않은 더 좁은 UX, route, screen, state, data, API 해석. | return-to-definition |

## Edge Cases And Failure Modes

구현에 영향을 주는 검증 실패, 누락 상태, 잘못된 artifact, 하위 호환성, 권한, 사용할 수 없는 dependency, rollback/recovery, no-op 동작을 설명한다.

## Validation Strategy

구체적인 명령, 테스트 케이스, fixture 시나리오, 리뷰 확인을 나열한다. 각 확인이 어떤 기술 결정이나 service rule을 입증하는지 설명한다.

## Risks

중요한 기술 위험과 완화 방법을 기록한다.

## Constraints

구현을 승인된 definition과 기록된 기술 architecture 범위 안에 유지한다.
```

## Required Artifact Sections

- `## Technical Approach`
- `## Implementation Architecture`
- `## Change Areas`
- `## Cause Or Design Notes`
- `## Implementation Flow Model`
- `## Flow Completeness Matrix`
- `## Work Items`
- `## Coverage Matrix`
- `## Definition Fidelity Matrix`
- `## Edge Cases And Failure Modes`
- `## Validation Strategy`
- `## Risks`
- `## Constraints`

## Writing And Review Rule Table

| Rule ID | Writing Rule | Required Artifact Evidence | Review Check | Blocking Condition |
| --- | --- | --- | --- | --- |
| IP-RULE-001 | Define the selected technical approach and architecture. | `## Technical Approach`, `## Implementation Architecture`, `## Implementation Flow Model`, and `## Flow Completeness Matrix` explain architecture choice, alternatives, responsibilities, call/data flow, flow handoffs, and compatibility boundaries. | Confirm another implementer would not need to choose the architecture or invent flow handoffs. | Technical approach, architecture, or complete-flow path is absent, generic, or leaves major design choices open. |
| IP-RULE-002 | Record implementation-relevant cause, design notes, or assumptions without changing service behavior. | `## Cause Or Design Notes` ties cause analysis or design constraints to approved service rules. | Confirm bugfix/root-cause notes and design assumptions are useful for implementation but do not invent product behavior. | Cause/design notes are absent when needed, or they create new service meaning. |
| IP-RULE-003 | Define concrete work items with technical design and evidence. | `## Work Items` table has `ID`, `Implementation Unit`, `Technical Design`, and `Completion Evidence` columns; each work item references its related Flow ID. | Confirm each work item is small enough to verify independently, detailed enough to implement directly, and connected to a complete flow. | Work items are vague, bundled, file-list-only, lack technical design/evidence, or are not tied to a flow. |
| IP-RULE-004 | Trace approved service policy rules from the definition to technical work and flows. | `## Coverage Matrix` table has `Service Rule ID`, `Work Item ID`, `Change Area`, `Validation Evidence`, and `Risk/Constraint` columns; `## Implementation Flow Model`, `## Flow Completeness Matrix`, and `## Definition Fidelity Matrix` link work items back to definition sources. | Confirm every service policy rule is covered by implementation work, validation evidence, flow evidence, and fidelity evidence. | A service policy rule is not mapped to technical work, flow completion, validation, or definition fidelity evidence. |
| IP-RULE-005 | Specify validation strategy, commands, and scenarios. | `## Validation Strategy` lists concrete commands, test cases, fixture scenarios, and what each proves; `## Flow Completeness Matrix` ties validation evidence to flow outcomes. | Confirm validation evidence is sufficient for the planned technical changes and proves the relevant flow outcomes. | Validation is missing, generic, impossible to run, or disconnected from service rules or flow outcomes. |
| IP-RULE-006 | Record edge cases, failure modes, risks, and constraints. | `## Edge Cases And Failure Modes`, `## Risks`, `## Constraints`, and `## Flow Completeness Matrix` state material limits, assumptions, failure behavior, and guardrails. | Confirm the implementer has enough constraints to avoid scope drift and predictable flow failure gaps. | Failure modes, risks, constraints, or flow-specific failure/empty states that affect implementation are omitted. |
| IP-RULE-007 | Do not implement code during this stage. | The artifact contains planning only and no implementation results. | Confirm no implementation work is claimed before user approval. | Code changes are made or recorded before implementation approval. |
| IP-RULE-008 | Do not create new requirements, UX policy, service behavior, endpoint semantics, scope narrowing, or unapproved UX interpretations. | Work items, coverage, and `## Definition Fidelity Matrix` map only to approved service policy rules, Intent Fidelity rows, and source-traced boundaries from the definition. | Confirm implementation planning applies `references/intent-fidelity.md`, maps service decisions to code work, cites definition sources for read-only/manual/future/out-of-scope narrowing, and returns to definition when approved meaning is ambiguous. | The plan introduces new product behavior, UX structure, API meaning, scope narrowing, or technical interpretation that was not approved in definition, or chooses an interpretation for ambiguous wording instead of returning to definition. |

## Verification Meaning

An implementation plan is ready for implementation only when another agent can execute every complete flow without deciding architecture, interfaces, module responsibilities, handoffs, state/data transitions, edge-case behavior, completion evidence, or validation strategy.
