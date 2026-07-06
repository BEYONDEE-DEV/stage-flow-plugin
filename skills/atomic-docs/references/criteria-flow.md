# Criteria Flow

## Contents

- [Atomization Criteria File-First Flow](#atomization-criteria-file-first-flow)
- [Criteria Structure Review Gate](#criteria-structure-review-gate)

## Atomization Criteria File-First Flow

Explain this flow to users as a first setup step before real atom document writing. In Korean interactions, call it `첫 설정 단계` or `처음 준비 단계`. The first step prepares the document storage location and the draft writing criteria; it does not create the full atom set, service logic inventory, graph edges, or source baseline. Show create/update targets as natural-language descriptions first and file paths second, such as `atomic docs 설정 파일` followed by `.stageflow/atomic-docs.json` and `문서 작성 기준 초안` followed by `<doc-root>/project/atomization-criteria.md`.

Do not summarize this first step only as raw key-value lines such as `storage mode`, `docs root`, or `작성/갱신`. After this first step passes criteria-review, tell the user that they should inspect the 작성 기준 초안 and approve or request changes before actual atom document writing begins.

For Korean first-setup responses, use this shape instead of a raw config summary:

- atomic docs를 처음 준비하는 단계입니다.
- 별도 submodule 없이 현재 repository 안의 `<doc-root>` 폴더에 문서를 저장합니다. (`storage_mode: repository`, `docs_root: <doc-root>`)
- 이번에는 `atomic docs 설정 파일` `.stageflow/atomic-docs.json`과 `문서 작성 기준 초안` `<doc-root>/project/atomization-criteria.md`만 만들거나 갱신합니다.
- 이 초안을 확인하고 승인하면 실제 atom 문서 작성을 시작할 수 있습니다.

When atomization criteria are needed, do not keep reviewed atomization perspectives only in chat or only in the change plan. For Korean managed docs, record this as `검토된 Atom화 관점`. After the docs root is confirmed, make the first atomic-docs write action a limited draft creation or update of `<doc-root>/project/atomization-criteria.md` as the criteria proposal.

If the current user request explicitly asks to start, redo, regenerate, or recreate atomic docs and confirms both the storage mode and managed docs root, treat the request itself as accepting the bootstrap write scope. In that case, do not stop at an approval request: create or update only `.stageflow/atomic-docs.json` when needed and `<doc-root>/project/atomization-criteria.md` as a draft criteria proposal in the same turn, then run the Criteria Structure Review Gate and stop for user review only after criteria-review PASS.

Before that first draft write, present a narrow change plan that names only the docs root config write when needed, `project/atomization-criteria.md`, and the draft criteria write action unless the current request already accepted that bootstrap scope. If `.stageflow/atomic-docs.json` is missing, the same first approved or bootstrap-accepted write scope may create that config and the criteria draft; it must not also create project goal, project glossary, common context, common policy atoms, domain atoms, graph edges, domain writer/reviewer subagent work, service logic inventory, or source baseline metadata.

The draft should first record criteria already stated in the user conversation and pending user approval state. It must not record reference example prose as criteria.

After the draft exists, use code exploration to enrich the criteria document itself, not just the change plan. Source exploration should first create a source feature inventory from project-native feature/root language such as package roots, existing docs terms, API surfaces, and user vocabulary. The inventory must also scan for route/controller/service/policy/persistence/workflow aggregates beneath broad source roots, so rejecting a broad root does not hide a concrete business responsibility that should become a domain candidate or split proposal. Then add or revise `도메인 분할 기준`, `후보/승인 도메인 맵`, `Atom 후보 맵`, `검토된 Atom화 관점`, `서비스 로직 커버리지 요구사항`, and `작성/리뷰 공통 품질 기준` entries for domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, failure/recovery, and implementation reconstruction coverage. The criteria document must keep durable domain/category boundaries, behavior-level atom candidates, the full discovery candidate map, and the current accepted write scope separate so broad or unapproved findings do not look like accepted domain structure. The current accepted write scope is operation-local and must not be encoded in durable domain approval status. Use project-native feature/root names as the default domain candidate language; record capability/common promotion proposals separately with user/source trace or promotion evidence. Leaf workflows, policies, states, or service behaviors belong in `Atom 후보 맵` or concrete split proposals, not directly in `후보/승인 도메인 맵`. For each perspective in Korean managed docs, record `Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, and `미해결 질문` in the criteria document. The `서비스 로직 커버리지 요구사항` and `작성/리뷰 공통 품질 기준` sections must carry the implementation reconstruction standard, including applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons, and blockers that prevent docs-only implementation. Use `서브에이전트 역할 분담` only to explain how writer subagents produce artifacts for the shared criteria and reviewer subagents verify the same criteria.

Before asking the user to approve the criteria document, satisfy the Criteria Structure Review Gate below. After criteria-review PASS, tell the user the criteria document path, summarize the actual written content, and ask the user to inspect the file and approve it or request changes. Do not ask for criteria approval with only the criteria document path and a generic approval request.

The approval-request summary must be decision-ready and cover these items as separate, concise bullets:

- `문서 작성 기준에서 정한 핵심 원칙`
- `도메인/범위 후보`
- `실제 atom 후보 또는 분리 후보`
- `아직 불확실한 점과 승인 차단 항목`
- `지금 승인하면 허용되는 것과 아직 허용되지 않는 것`

The summary should also cover the docs root and scope, domain partitioning criteria, project-native feature candidates, capability/common promotion proposals, candidate or approved domain/category boundary map, atom candidate map, atomization perspectives, shared writer/reviewer quality criteria, service logic coverage requirements, judgment policy usage, and open blockers as separate items. Do not treat the summary as a substitute for the file. The user reviews, adds, removes, revises, and approves the criteria through the criteria document only after that gate passes. Until the criteria document is approved, it is a draft review artifact and must not be used as the required input for domain writer subagents, review subagents, or confirmed atom writing. After approval, update the criteria document from draft/pending state to approved state and remove transient draft-operation logs before starting domain atom work.

Expected project domains found during exploration are candidates only when they are narrow durable boundary candidates with observed behavior and boundary rationale. Do not treat candidate names as confirmed domain structure before criteria approval. Broad discoveries are not candidates; they must be recorded as `rejected` broad groupings or converted into concrete split proposals.

When a broad discovery is rejected, the criteria draft must still show what happened to the concrete aggregates below it: promoted concrete domain candidates, concrete split proposals, or an explicit evidence-based reason that no durable lower-level aggregate was found. Do not let `configuration` or another technical bucket name replace user-visible management, registration, approval, issuance, settlement, recovery, or policy language when the source evidence shows a concrete business workflow.

If a legacy `<doc-root>/project/atomization-criteria-atom.md` exists, treat it as a migration/update candidate. Do not write new criteria to the legacy path unless the accepted change plan explicitly covers migration from that legacy artifact.

## Criteria Structure Review Gate

Run this gate after the criteria draft is created or enriched, and before asking the user for criteria approval.

Use an independent criteria-review subagent to review only the criteria draft, source exploration evidence, and accepted draft scope. This review subagent is allowed before criteria approval and does not require a Codex Goal because it is part of criteria-draft quality control, not docs generation.

The criteria-review subagent must fail the draft when:

- any `Atom화 관점` entry is missing one of the required Korean subfields: `Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, or `미해결 질문`
- a required perspective subfield is empty, placeholder-only, or a one-line summary that does not explain the criterion
- Korean managed criteria docs use English visible labels for criteria sections or fields, such as `Purpose`, `Approval Status`, `Atomization Perspectives`, `Atom candidate criteria`, `Source evidence only criteria`, or `Unresolved questions`
- source evidence is absent and the perspective does not record a concrete `해당 없음 사유` or `미해결 질문`
- the criteria draft lacks a source feature inventory before proposing domain names
- the source feature inventory lists only package roots, API surfaces, or screens and omits the route/controller/service/policy/persistence/workflow aggregate scan needed to find lower-level concrete domain candidates
- the domain map is missing, source-unsupported, or treats candidate domains as approved before user approval
- a broad source root or category/root surface is rejected but obvious concrete aggregates beneath it are missing from the domain map, concrete split proposals, or unresolved boundary questions
- the domain map uses an AI-renamed domain label that replaces project-native feature/root language without user approval, existing docs terminology, or durable promotion evidence
- a feature-root flow is renamed into an abstract capability label without recording `project-native name`, `source feature root`, `optional capability alias`, `promotion reason`, and `approval state`
- full discovery candidates, approved domain/category boundaries, current accepted write scope, and atom candidate map entries are mixed together so the reader cannot tell what is merely discovered, what is a durable boundary, what is a behavior-level atom candidate, and what is accepted for the current operation
- durable domain approval status is used to encode operation-local write scope
- leaf behavior, workflow, policy, state-transition, endpoint, or service-method candidates are listed directly in the domain/category boundary map instead of `Atom 후보 맵` or a concrete split proposal
- a broad domain or broad category grouping is marked `candidate`, `approved`, or `needs_confirmation` instead of `rejected` or a concrete split proposal
- a broad source feature root is marked as an approved domain instead of a category/root surface or split proposal
- a capability/common promotion lacks cross-feature ownership, shared persistence/state, shared policy, or shared recovery question evidence
- a category or subdomain structure hides a broad domain, generic bucket, lifecycle status group, code-layer grouping, or screen grouping
- domain-boundary evidence is only source identifiers without observed behavior summary, excluded behavior, adjacent boundary, why the records change together, and confirmed/inferred/needs_confirmation basis
- `작성/리뷰 공통 품질 기준` omits any of the required atom identity rules: frontmatter `atom_key`, AID format `[AID:<atom_key>.<section-code>.<NNN>]`, graph `target_key` as the target atom's `atom_key`, or graph `target_path` as a mutable locator
- `서비스 로직 커버리지 요구사항` or `작성/리뷰 공통 품질 기준` omits implementation reconstruction coverage, including applicable or not-applicable frontend/UI and backend/API/service/job/integration coverage, or treats shallow source-observed inventory as enough for docs-only implementation
- criteria state semantics for `candidate`, `approved`, `rejected`, or `needs_confirmation` are ambiguous or used inconsistently
- writer and reviewer rules are written as divergent role-specific checklists instead of one `작성/리뷰 공통 품질 기준`
- any reviewer FAIL condition lacks a matching shared criterion or explicit phase gate, or any writer obligation is not reviewable by the same shared criterion
- the draft makes unapproved destructive claims about legacy artifacts, including deleting `atomization-criteria-atom.md` without an accepted migration/delete action
- an approved criteria document still contains one-off draft operation logs such as cache paths, reset/delete notes, reviewer agent names, stale "currently none" status, or transient `현재 없음` status, unless the note is an active approval blocker
- reference example prose leaks into the criteria document without target-project user or source trace
- source-derived intent, rules, domain ownership, or boundaries are not marked as inferred or `needs_confirmation` while still unapproved

If criteria-review fails, revise only `project/atomization-criteria.md` within the accepted criteria draft scope, then rerun the criteria-review subagent. Repeat this cycle until the criteria-review subagent reports no blocking issues. A PASS means the criteria draft is ready for user review and possible approval; it does not approve the criteria automatically.

When criteria-review PASS is reached, respond to the user with:

- the criteria document file path, normally `<doc-root>/project/atomization-criteria.md`
- a concise Korean summary of what was written, including docs root/scope, domain partitioning criteria, project-native feature candidates, capability/common promotion proposals, candidate or approved domain/category boundary map, atom candidate map, atomization perspectives, shared writer/reviewer quality criteria, service logic coverage requirements, judgment policy usage, and open blockers as separate items
- a clear request for the user to inspect the file content and either approve it, say there is no issue, or request corrections

Do not proceed to criteria approval state update, Codex Goal creation, service logic inventory, domain writer/reviewer subagents, project/common/domain atom writing, graph writing, or source-baseline update until the user confirms the criteria content has no issue or explicitly approves it.

When the user approves the criteria, respond in user-action terms:

- First say `문서 작성 기준 승인은 완료됐고, 아직 실제 서비스 로직 문서는 작성하지 않았다`.
- Explain that the next choice is the docs writing scope, not an internal gate.
- Offer user-enterable next actions: `전체 문서 작성 시작`, `특정 도메인만 작성`, `특정 기능/흐름만 작성`, and `기준을 더 수정`.
- Do not present `Goal Gate` as the primary next action. Mention the Codex Goal only as an internal requirement or brief note after the user chooses a write scope.
