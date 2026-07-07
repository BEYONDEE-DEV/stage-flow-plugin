# Atomization Criteria Contract

## Responsibility

This reference defines the first criteria document and the review contract for approving atomization criteria before domain atom writing.

## Atomization Criteria Document

The default criteria document path is:

```text
<doc-root>/project/atomization-criteria.md
```

After the docs root is confirmed and the user accepts the limited draft write action, create or update this document as the first atomic-docs write action when atomization criteria are needed. Use the draft criteria document to capture the user's conversation, prohibitions, atomization concerns, domain-boundary concerns, and review questions before relying on chat summaries or drafting domain atoms.

The criteria document is not an atom. It must not follow the `*-atom.md` path contract, the atomic graph contract, or the required atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`. Those required sections are for service-logic and context atom files only.

A draft criteria document is a review artifact. It must not be used as the required input for domain writer subagents, review subagents, or confirmed atom writing until the user approves the criteria. In Korean managed docs, record `승인 상태: 초안, 사용자 승인 대기` while it is draft. After the user approves the criteria, update it to `승인 상태: 사용자 승인 완료` and remove obsolete draft-only or pending-approval blockers.

Record user-conversation criteria in the draft before code exploration if they affect atomization. Capture only criteria that came from the user, inspected source behavior, or approved workflow evidence; do not copy illustrative wording from skill references into the criteria document.

For Korean managed docs, the criteria document must use these visible section headings:

- `목적`
- `승인 상태`
- `문서 루트와 작업 범위`
- `도메인 분할 기준`
- `후보/승인 도메인 맵`
- `Atom 후보 맵`
- `Atom화 관점`
- `서비스 로직 커버리지 요구사항`
- `작성/리뷰 공통 품질 기준`
- `서브에이전트 역할 분담`
- `판정 라벨 사용 기준`
- `미해결 질문과 승인 차단 항목`

Do not use English visible criteria headings such as `Purpose`, `Approval Status`, `Managed Docs Root And Scope`, `Domain Partitioning Criteria`, `Candidate / Approved Domain Map`, `Atom Candidate Map`, `Atomization Perspectives`, `Service Logic Coverage Requirements`, `Shared Writer/Reviewer Quality Criteria`, `Subagent Role Mapping`, `Writer Subagent Instructions`, `Reviewer Subagent Instructions`, `Judgment Policy Usage`, or `Open Questions And Approval Blockers` in Korean managed docs.

The criteria document records:

- atomization perspectives reviewed with the user, such as domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, and failure/recovery
- every entry under `Atom화 관점` with these exact visible subfields: `Atom 후보 기준`, `소스 근거로만 둘 기준`, `해당 없음 사유`, `분리/병합 기준`, `소스 근거 요구사항`, and `미해결 질문`
- which perspectives create atom candidates, which are source evidence only, and which are not applicable for the current source shape
- domain partitioning criteria for deciding domain paths, category boundaries, and durable ownership boundaries
- project-native feature/root language as the default starting point for domain candidates before any capability renaming or promotion
- each domain or category candidate with `project-native name`, `source feature root`, `optional capability alias`, `promotion reason`, and `approval state`
- a full discovery candidate map separated from the current accepted write scope, so discovered possibilities do not masquerade as accepted domain structure
- operation-local current accepted write scope recorded separately from durable domain approval status, usually under `문서 루트와 작업 범위` or the current change plan
- a candidate or approved domain map that records only durable domain or category boundaries, not behavior-level atom candidates, and records each domain name with Korean field labels for `승인 상태`, `소유 동작`, `제외 동작`, `인접 도메인 경계`, `함께 변경되는 이유`, `소스 근거`, `근거 성격`, and `미해결 질문`
- domain-boundary evidence that includes observed behavior summary, excluded behavior, adjacent boundary, why the records change together, and whether the basis is user-confirmed, source-inferred, or blocked by `needs_confirmation`
- a separate `Atom 후보 맵` or `Atom 후보/분할 제안` area for behavior-level atom candidates, so leaf workflows, policies, states, or service behaviors do not masquerade as domains
- each atom candidate with `candidate atom_key`, tentative path or slug, owning domain/category path, source evidence, split/merge reason, and unresolved question
- split and merge criteria, including how to decide when behavior belongs in one atom versus multiple atoms
- source evidence requirements for each atom candidate
- forbidden vague split gaps and the minimum evidence needed for a concrete split proposal
- one shared writer/reviewer quality standard that future docs operations must use both for drafting and reviewing atom files
- service logic coverage requirements and shared writer/reviewer quality criteria that include implementation reconstruction coverage, applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons, and blockers that prevent docs-only implementation
- shared atom identity rules, including mandatory frontmatter `atom_key` for new atoms, AID values in the form `[AID:<atom_key>.<section-code>.<NNN>]`, graph `target_key` as the target atom's `atom_key`, and graph `target_path` as a mutable locator
- subagent role mapping that explains how writer subagents produce artifacts for the shared standard and how reviewer subagents verify that same standard

These perspectives are not fixed document types. Entry surfaces discovered in the target source may be evidence, but the criteria document must not force a separate atom merely because that surface exists.

Domain approval state values are limited to `candidate`, `approved`, `rejected`, and `needs_confirmation`; keep these values unchanged, but use the Korean field label `승인 상태`.

- `candidate` means a narrow durable boundary candidate with enough observed behavior and boundary rationale to review, but not yet approved for docs writing.
- `approved` means the user approved that durable boundary as part of the criteria's durable domain map. It does not mean the domain is inside the current operation's accepted write scope.
- `needs_confirmation` means there is source evidence and boundary rationale, but a blocking user/source ownership question must be answered before approval.
- `rejected` means a broad, unsupported, excluded, or otherwise invalid grouping that must not become a docs domain unless later split or redefined.

Current accepted write scope is operation-local. Record it separately under `문서 루트와 작업 범위` or the current change plan, and never change a domain's `승인 상태` merely because the current operation includes or excludes that domain.

The `후보/승인 도메인 맵` must not contain leaf behavior entries such as a purchase preview, paid-order processing flow, refund preparation flow, one endpoint, one service method, one lifecycle transition, or one policy rule unless the entry is framed as a durable domain/category boundary with owned behavior, excluded behavior, adjacent boundary, and why its atoms change together. Otherwise, put the behavior under `Atom 후보 맵` or a concrete split proposal.

Broad domains and broad category groupings are unconditional criteria-review failures when marked `candidate`, `approved`, or `needs_confirmation`. Record a broad grouping only as `rejected` with the reason, or replace it with concrete split proposals based on observed capabilities, workflows, responsibilities, contracts, or policies.

Do not approve a domain solely from a code folder name, endpoint, controller, service class, screen, lifecycle state, temporary task grouping, category folder, or generic catch-all rationale. A domain can be approved only when evidence shows a durable boundary such as product or business capability, user-visible workflow, operational responsibility, integration contract, or shared policy/platform concern. However, the codebase's own stable feature/root language is still the default naming input; do not replace it with a new abstract capability label unless the Hybrid Domain Naming Policy allows that promotion.

Criteria source evidence does not need to describe every service logic branch at atom-level depth. However, source identifiers alone are not valid domain-boundary evidence. If a candidate has only source paths, endpoint names, class names, or method names without observed behavior summary and boundary rationale, criteria-review must fail it as identifier-only evidence.

The criteria document must not maintain separate writer-only and reviewer-only quality rules. The sections `서비스 로직 커버리지 요구사항` and `작성/리뷰 공통 품질 기준` must make implementation reconstruction coverage an explicit shared standard before user approval. The section `작성/리뷰 공통 품질 기준` is the single acceptance standard. It should cover domain-map use, atom candidate map use, atomization perspectives, service logic inventory, natural-language implementation coverage, implementation reconstruction coverage, applicable frontend/UI coverage, backend/API/service/job/integration coverage, explicit not-applicable reasons, source evidence, inferred/confirmed basis, frontmatter `atom_key`, AID assignment with `[AID:<atom_key>.<section-code>.<NNN>]`, graph `target_key`/`target_path` rules, judgment labels, Korean-first wording, no example leakage, accepted scope, and Goal Gate requirements when applicable.

The section `서브에이전트 역할 분담` may describe workflow roles only:

- writer subagents produce service logic inventories, evidence packets, and atom drafts that satisfy each item in `작성/리뷰 공통 품질 기준`
- reviewer subagents verify the same items in `작성/리뷰 공통 품질 기준` and report missing or unsupported evidence
- criteria-review subagents verify whether the criteria draft itself contains enough shared criteria before user approval

Every writer obligation must be reviewable by the same shared criterion, and every reviewer FAIL condition must map to the same shared criterion or an explicit phase gate such as criteria approval, accepted scope, or Goal Gate. Do not add hidden reviewer-only quality bars or writer-only obligations that the reviewer does not check.

Do not accept a criteria document that only lists perspective names or domain names. Do not accept one-line perspective summaries. A criteria-review subagent must fail the draft when any perspective is missing one of the required Korean subfields, when a required subfield is empty or placeholder-only, when a Korean managed criteria draft uses English visible labels for criteria sections or fields, when writer and reviewer rules appear as divergent role-specific checklists instead of one shared quality standard, or when a perspective with no current source evidence fails to record a concrete `해당 없음 사유` or `미해결 질문` entry.

Criteria-review must also fail when full discovery candidates, approved domain/category boundaries, current accepted write scope, and behavior-level atom candidates are mixed together; when durable domain approval status is used to encode operation-local write scope; when a leaf behavior candidate appears directly in the domain/category boundary map without durable boundary rationale; when a broad domain or broad category grouping is marked `candidate`, `approved`, or `needs_confirmation`; when category structure hides a broad grouping; when domain-boundary evidence is only source identifiers without observed behavior summary and boundary rationale; when the shared quality criteria omit frontmatter `atom_key`, AID, graph `target_key`, or graph `target_path` rules; or when `서비스 로직 커버리지 요구사항` or `작성/리뷰 공통 품질 기준` omits implementation reconstruction coverage, applicable or not-applicable frontend/UI coverage, backend/API/service/job/integration coverage, or blockers that prevent docs-only implementation.

Before a criteria document is marked approved, remove one-off operation logs such as plugin cache paths, reset/delete notes, reviewer agent names, and transient "currently none" or `현재 없음` status notes unless they are active approval blockers. Approved criteria should contain durable criteria, approved or unresolved boundary information, and active blockers, not the draft execution diary.

If a perspective or domain candidate has no current source evidence, mark it not applicable with a reason or keep the missing evidence as an unresolved question.
