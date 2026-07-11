# Criteria Flow

## Contents

- [First Setup And Draft](#first-setup-and-draft)
- [Source Enrichment](#source-enrichment)
- [Criteria Structure Review Gate](#criteria-structure-review-gate)
- [User Approval Handoff](#user-approval-handoff)

## First Setup And Draft

Explain criteria bootstrap as the preparation step before real atom writing. In Korean interactions, say that atomic docs is being prepared, where docs will be stored, and that only the config and writing-criteria draft will be created or updated.

Use this user-facing shape for repository storage:

- atomic docs를 처음 준비하는 단계입니다.
- 별도 submodule 없이 현재 repository 안의 `<doc-root>` 폴더에 문서를 저장합니다.
- 이번에는 `atomic docs 설정 파일` `.stageflow/atomic-docs.json`과 `문서 작성 기준 초안` `<doc-root>/project/atomization-criteria.md`만 만들거나 갱신합니다.
- 이 초안을 확인하고 승인하면 실제 atom 문서 작성을 시작할 수 있습니다.

Do not reduce this message to raw `storage_mode`, `docs_root`, or write-path key/value lines.

When criteria are needed, make `<doc-root>/project/atomization-criteria.md` the first managed-docs write. If the current request explicitly selects storage mode and docs root and asks to start, redo, regenerate, or recreate atomic docs, treat it as accepted bootstrap scope for only config and criteria. Otherwise present that narrow change plan before writing.

The bootstrap scope must not create project goal/glossary/source convention, service logic inventory, common/domain atoms, graph edges, domain subagents, or source baseline metadata.

Write user-stated criteria, prohibitions, atomization concerns, and pending approval state before relying on chat summaries. Do not copy illustrative reference prose into the criteria document.

## Source Enrichment

After the draft exists, inspect enough source to enrich the criteria for the requested scope. For targeted work, inspect the requested feature roots and adjacent contracts needed to avoid a false boundary. Build a project-wide source feature inventory only when the user is preparing full-project docs or a global baseline. Continue beneath any inspected broad root so a broad rejection does not hide concrete business responsibility.

Keep these structures separate when they are applicable:

- durable domain/category boundary map
- full discovery candidate map
- behavior-level `Atom 후보 맵`
- accepted-scope rules for later operations

Use project-native names by default. Record capability/common promotion separately with user/source trace and promotion evidence. Put leaf workflows, policies, states, contracts, and service behaviors in `Atom 후보 맵`, not the domain map.

Under `Atom화 관점`, define these common rules once:

- `공통 Atom 후보 기준`
- `공통 소스 근거 기준`
- `공통 분리/병합 기준`
- `공통 해당 없음/미해결 처리`

Then use one result table:

```text
관점 | 적용 상태 | 프로젝트 근거/후보 | 공통 기준 예외 | 미해결 질문
```

Include rows for the perspectives evidenced by the requested scope, choosing from domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, failure/recovery, and implementation decision/verifiability. Do not add placeholder rows for perspectives that were not inspected. Use only `Atom 후보`, `소스 근거만`, `해당 없음`, or `미해결` as `적용 상태`.

Do not repeat the shared atom/evidence/split/not-applicable rules inside every row. Each row records only project-specific results, exceptions, and unresolved questions.

Keep decision completeness, proportional frontend/UI and backend/API/service/job/integration detail, conditional risk triggers, and blockers that force unstated product decisions in `서비스 로직 커버리지 요구사항` and the shared writer/reviewer standard.

## Criteria Structure Review Gate

Run an independent criteria-review subagent after drafting and source enrichment and before asking the user for approval. Criteria review is part of accepted bootstrap scope and does not require a Codex Goal or separate approval.

Apply every failure rule in `atomization-criteria-contract.md`. In particular, FAIL when:

- common atomization rules or required perspective rows are missing
- the result table has wrong columns, invalid state values, placeholder content, unsupported candidates, or unexplained not-applicable/unresolved rows
- source inspection for the requested scope is too shallow to find concrete aggregates beneath an inspected broad root
- domain, discovery, atom-candidate, and operation-scope concepts are mixed
- broad groupings are treated as valid domains or project-native language is silently replaced
- decision completeness, proportional depth, risk selection, or shared writer/reviewer quality requirements are incomplete
- runtime state, bundle queues, reviewer logs, cache paths, or stale draft notes leak into durable criteria
- reference examples, unsupported inferred intent, or destructive migration claims appear

If review FAILs, revise only the criteria document inside accepted bootstrap scope and rerun the criteria reviewer. Continue until PASS or until PASS requires a user decision. PASS means ready for user review; it does not approve the criteria.

## User Approval Handoff

After criteria-review PASS, provide the criteria path and a decision-ready Korean summary. Keep these items distinct:

- `문서 작성 기준에서 정한 핵심 원칙`
- `도메인/범위 후보`
- `실제 atom 후보 또는 분리 후보`
- `아직 불확실한 점과 승인 차단 항목`
- `지금 승인하면 허용되는 것과 아직 허용되지 않는 것`

Also summarize project-native candidates, capability/common promotion proposals, durable boundaries, compact perspective results, shared quality criteria, service-logic decision requirements, risk triggers, and judgment-label usage. Do not ask for approval with only a path and generic request.

Wait until the user approves the criteria content. Then set its approval state to user-approved and remove obsolete draft/pending/current-run notes.

Respond first with `문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다`. Ask the user to choose `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, or `기준을 더 수정`. Do not present an internal Goal gate as the user's next action.
