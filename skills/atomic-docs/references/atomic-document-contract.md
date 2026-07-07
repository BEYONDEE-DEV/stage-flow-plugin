# Atomic Document Contract

## Contents

- [Responsibility](#responsibility)
- [Path Contract](#path-contract)
- [Project And Domain Context Policy](#project-and-domain-context-policy)
- [Project Document Contract](#project-document-contract)
- [Atomization Criteria Document](#atomization-criteria-document)
- [Source Convention Document](#source-convention-document)
- [Domain Discovery Policy](#domain-discovery-policy)
- [Hybrid Domain Naming Policy](#hybrid-domain-naming-policy)
- [Domain Boundary Quality Gate](#domain-boundary-quality-gate)
- [Core Business Term Coverage Gate](#core-business-term-coverage-gate)
- [Service Logic Natural-Language Coverage](#service-logic-natural-language-coverage)
- [Implementation Reconstruction Coverage](#implementation-reconstruction-coverage)
- [Source Fact Fidelity Gate](#source-fact-fidelity-gate)
- [Atomic Docs Goal Boundary](#atomic-docs-goal-boundary)
- [Atom Line ID Policy](#atom-line-id-policy)
- [Required Atom Sections](#required-atom-sections)
- [Judgment Evidence Policy](#judgment-evidence-policy)
- [Forbidden Shapes](#forbidden-shapes)
- [Atomicity Policy](#atomicity-policy)

## Responsibility

This reference defines the managed documentation shape inside the configured managed docs root.

## Path Contract

Every atom uses this exact organization:

```text
<doc-root>/<domain-path>/<file-slug>-atom.md
```

- `<doc-root>` is the confirmed managed docs root.
- `<domain-path>` is one or more folder segments below the docs root. It may include category or subdomain segments, but it is a mutable placement path, not atom identity.
- `<file-slug>` is a readable file slug for one user-visible behavior, policy, rule, state, plan, context, or gap boundary. It is a mutable locator, not atom identity.
- Every atom file must end with `-atom.md`.
- Every new atom file must include frontmatter `atom_key`.
- `atom_key` is the stable atom identity. It must be globally unique across the docs set, lower-kebab-case, and unchanged by category moves, domain-path moves, file-slug changes, or file renames.
- Existing atoms without `atom_key` use slug-derived identity only as a legacy fallback for discovery. Treat them as explicit `atom_key` migration candidates in refresh or change plans before relying on them for new graph/AID work.
- Do not create new `<file-slug>/atomic.md` folder-shaped atoms. If an existing docs set uses that older shape, propose a migration before changing paths.
- The project documents listed in the Project Document Contract, including the atomization criteria document and source convention document, are not atoms and are exempt from this path contract.

## Project And Domain Context Policy

Use generic context atoms to preserve project and domain intent without hardcoding project-specific folder names.

Default project-level documents:

```text
<doc-root>/project/atomization-criteria.md
<doc-root>/project/project-goal.md
<doc-root>/project/project-glossary.md
<doc-root>/project/service-logic-inventory.md
<doc-root>/project/source-convention.md
```

- Project-level documents are control, context, criteria, inventory, or source-interpretation documents. They are not service logic atoms and do not use atom frontmatter, AID, graph edges, or required atom sections unless a separate accepted migration explicitly converts them into atom files.
- Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` files are legacy artifacts. Treat them as migration/update candidates; do not use those paths as defaults for new project goal or glossary work.

Default project-level criteria document:

```text
<doc-root>/project/atomization-criteria.md
```

- `atomization-criteria.md` records draft or approved criteria used to decide domain boundaries, split/merge atom files, draft docs, review docs, and apply judgment policy.
- This criteria document is not a service-logic atom, not a graph target, and not direct code suitability evidence. Code suitability judgments come from generated natural-language service logic atoms, source evidence, graph relationships, baseline metadata, and judgment labels.
- Existing `<doc-root>/project/atomization-criteria-atom.md` files are legacy artifacts. Treat them as migration/update candidates; do not use that path as the default for new criteria work.

Default project-level source convention document:

```text
<doc-root>/project/source-convention.md
```

- `source-convention.md` records source interpretation conventions needed for writing and reviewing docs, such as project-specific source structure, validation or wiring conventions, behavior-impact boundaries, and formatter/linter/static-check evidence.
- This source convention document is not a service-logic atom, not a graph target, not direct code suitability evidence, and not a substitute for source-observed behavior in the relevant service logic atoms.
- Use it to keep code convention and source structure notes out of service logic atoms, especially when the convention is non-runtime formatting, naming, package placement, layer placement, import ordering, or similar code style.

Default shared-domain atom:

```text
<doc-root>/common/common-context-atom.md
```

- `common` is the default domain for concepts, policies, code structures, or rules shared by multiple domains.
- `common` must not become a miscellaneous bucket. Each common atom must describe one shared concept, shared policy, or shared code structure.
- Single-domain behavior belongs in that domain, not in `common`.

Default domain-level atom:

```text
<doc-root>/<domain>/<domain>-context-atom.md
```

- A domain context atom combines the domain goal and domain boundary.
- It records the domain purpose, responsibilities, included behavior, excluded behavior, adjacent-domain boundaries, and conditions for promoting shared concepts to `common`.
- When creating a new domain, create or update its context atom in the same accepted change plan. If the domain goal or boundary is unclear, present candidate boundaries and ask instead of writing confirmed intent.
- Do not create a domain-specific glossary by default. Add domain-only terms to `project/project-glossary.md` with their domain scope unless the user explicitly wants separate glossary documents or glossary atoms.

## Project Document Contract

Project documents are non-atom documents under `<doc-root>/project/`. They define criteria, project context, terminology, source interpretation, or writer/reviewer input. They do not directly judge whether code matches service behavior; that judgment must come from service logic atoms, source evidence, graph relationships, baseline metadata, and judgment labels.

Default project documents are:

```text
<doc-root>/project/atomization-criteria.md
<doc-root>/project/project-goal.md
<doc-root>/project/project-glossary.md
<doc-root>/project/service-logic-inventory.md
<doc-root>/project/source-convention.md
```

These files must not follow the `*-atom.md` path contract, must not require frontmatter `atom_key`, must not require AID values, must not use `graph_edges`, and must not require the atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`.

Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` are legacy project-document artifacts. When they are present, read them as possible source material, then propose a migration or update to `project/project-goal.md` and `project/project-glossary.md` instead of continuing the atom-named defaults.

Project document writing rules:

- `project-goal.md` records the service or product purpose, target users or callers, success criteria, non-goals, confirmed business direction, and source-unverifiable items as `confirmation_needed`. It must not turn config paths, baseline metadata paths, cache paths, reset notes, deletion notes, reviewer logs, or docs-operation status into the service goal.
- `project-glossary.md` records each core term with structured fields for meaning, owning domain, actor/system action, source of truth, stored vs computed, related rules/status, aliases, forbidden conflations, and uncertainty. A glossary that only contains one-line term definitions is not enough to support core term coverage.
- `service-logic-inventory.md` is a writer/reviewer input document, not a service logic atom. Each behavior item must include source identifiers, conditions/branches, validation/guard, state transition, persistence side effect, external call, error/recovery, basis, owning atom_key, related AID, and judgment label when applicable. One-line behavior summaries are not enough for baseline readiness.
- `source-convention.md` is a source interpretation helper. Runtime-impacting conventions must link to a related service logic atom_key and AID, or to a coverage gap when no atom exists yet. Non-runtime code style stays in this document and must not be mixed into service logic atoms.
- `atomization-criteria.md` records generation criteria, domain/category boundary semantics, accepted scope semantics, and approval state. It is not direct code suitability evidence.

Project document review rules:

- Do not fail a project document only because it omits atom required sections, frontmatter `atom_key`, AID values, or `graph_edges`.
- Fail when a project document directly claims code is implemented, missing, buggy, matching, or out of scope as if it were a service logic atom.
- Fail when `project-goal.md` treats docs configuration, baseline paths, plugin cache paths, reset/delete notes, or operation logs as service/product goals.
- Fail when `project-glossary.md` is only a list of one-line term definitions without the structured fields required above.
- Fail when `service-logic-inventory.md` is only a one-line summary or lacks behavior-level fields needed by writer/reviewer work; do not write or update baseline metadata while the inventory is in that state.
- Fail when `source-convention.md` records runtime-impacting behavior without a related atom_key/AID or a coverage gap.

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

## Source Convention Document

The default source convention document path is:

```text
<doc-root>/project/source-convention.md
```

Create or update this document only when the user asks for a source convention format, or when a docs operation repeatedly needs project-specific source interpretation conventions that would otherwise leak into service logic atoms. This document is a non-atom document like the criteria document. It must not follow the `*-atom.md` path contract, required atom sections, atomic graph contract, frontmatter `atom_key`, or AID policy.

For Korean managed docs, the source convention document must use these visible section headings:

- `목적`
- `승인 상태`
- `적용 범위`
- `소스 구조 관례`
- `동작 영향 관례`
- `비동작 코드 스타일`
- `Formatter / Linter / Static Check 근거`
- `서비스 로직 Atom과의 경계`
- `리뷰 기준`
- `미해결 질문`

The source convention document is not a general style guide for its own sake. It records only conventions that help docs writers and reviewers interpret source behavior consistently:

- source structure conventions, such as package roots, layer placement, module ownership, generated-source boundaries, or wiring locations used as source navigation evidence
- runtime-impacting conventions, such as transaction activation, validation activation, authorization wiring, error response mapping, lock ordering, persistence ordering, event publication, or framework wiring that changes behavior
- non-runtime code style, such as formatting, naming, package placement, layer placement, import ordering, comments, or file organization when it does not change product, operation, or integration behavior
- formatter, linter, or static-check evidence that proves whether a convention is enforced by tooling or is only inferred from source shape

Keep source convention and service logic judgment separate:

- Non-runtime code style belongs only in `project/source-convention.md`; do not put it in service logic atom `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, or `Gaps` unless the user explicitly asks for a style atom outside normal service-logic docs.
- Runtime-impacting conventions may be summarized in `project/source-convention.md`, but the actual code judgment basis must also appear as natural-language behavior in the relevant service logic atom with source evidence.
- The source convention document alone cannot support `bug_or_regression`, `missing_required_behavior`, `matches_confirmed_intent`, `unapproved_implemented_behavior`, or `out_of_scope_behavior` for service logic. Use it as interpretation context, then connect the judgment to service logic atoms, source evidence, baseline metadata, and judgment labels.
- If a service logic atom contains simple code convention, source folder taxonomy, import order, formatting, naming, or layer-placement notes as if they were runtime behavior, reviewer must fail or request moving that material to `project/source-convention.md`.
- If a source convention has runtime impact but no related service logic atom records the behavior, leave a coverage gap or `confirmation_needed` item instead of treating the source convention as sufficient code judgment evidence.

## Domain Discovery Policy

Choose domain paths from project evidence, not from a fixed project-specific list.

Use this priority order:

1. User-confirmed product, business, or bounded-context language.
2. Existing managed-docs-root domain language and existing context atoms.
3. Source-observed user-visible capabilities, workflows, policies, or domain models.
4. Cross-cutting boundaries such as shared platform, integration contract, infrastructure, or policy only when the content coherently affects multiple domains.

Do not confirm a domain solely from a code folder name.

Category and subdomain folders are allowed only as organization inside an approved durable boundary. They must not hide a broad domain, generic bucket, lifecycle status group, or code-layer grouping. If a category label is broad, record it as `rejected` or split it into concrete durable boundary proposals before atom writing.

When a broad source root or category/root surface is rejected, still inspect below it for concrete business aggregates. A concrete aggregate is a source-observed responsibility where routes, controllers, service methods, policy rules, persistence side effects, or user-visible workflow steps repeatedly describe the same capability, operation, lifecycle, or management task and tend to change together. Promote that aggregate to a concrete domain candidate or concrete split proposal with owned behavior, excluded behavior, adjacent boundary, and unresolved questions instead of stopping at the broad rejection.

## Hybrid Domain Naming Policy

Use a hybrid domain naming model for criteria drafts and domain maps:

1. Start with project-native feature/root language observed in source roots, existing docs, API surfaces, package roots, or user vocabulary.
2. Keep those project-native names visible as the default domain/category candidates unless they are broad or unsupported.
3. Promote a cross-feature capability/common boundary only when the criteria records explicit promotion evidence.

The criteria document must distinguish:

- `project-native name`: the name already used by the project or user
- `source feature root`: the package/root/surface where the source-observed behavior appears
- `optional capability alias`: a proposed business capability label, if any
- `promotion reason`: why the alias should replace or sit above project-native feature language
- `approval state`: `candidate`, `approved`, `rejected`, or `needs_confirmation`

AI-renamed domain labels are not valid default domain names. If the source uses a feature root such as `auth`, `commerce`, `refund`, `resource`, `ticketgroup`, `web`, or `admin`, a criteria draft must not silently rename that root into a new abstract capability label such as `sales-fulfillment` unless one of these bases is recorded:

- user approval or user vocabulary for the new capability label
- existing managed-docs-root terminology that already uses that capability label
- durable ownership evidence showing the capability crosses multiple source feature roots

Capability or common promotion requires at least one of these evidence types: cross-feature ownership, shared persistence or state, shared policy, or shared recovery question. Without that evidence, keep the project-native feature/root name and put the cross-feature idea in `optional capability alias` or `needs_confirmation`.

Broad source feature roots such as an `admin` root are not automatically approved domains. Treat them as category/root surfaces or split proposals until the criteria records narrower durable boundaries. This preserves the broad-domain FAIL rule while avoiding arbitrary AI renaming.

Prefer project/user business language for the promoted aggregate. If the source behavior is about managing, registering, approving, issuing, settling, or recovering a product-visible thing, do not default to technical labels such as `configuration` only because the methods or DTOs sit in a setup/admin area. Keep technical names as source evidence or optional aliases unless the project or user actually uses them as the domain language.

Atom candidates must point their owning domain/category path at an approved or candidate hybrid boundary. Do not point atom candidates at an AI-renamed label that lacks user/source trace or promotion evidence.

## Domain Boundary Quality Gate

A first-level domain is valid only when it describes a durable ownership boundary. The boundary must be explainable as at least one of:

- a product or business capability
- a user-visible workflow
- an operational responsibility
- an integration contract
- a shared policy or platform concern

Before creating or moving a domain, the domain context or change plan must state:

- the behavior the domain owns
- the behavior the domain excludes
- the adjacent-domain boundary
- why the atom files in the domain tend to change together

Do not confirm a first-level domain when its main rationale is a documentation section type, lifecycle state, task status, freshness state, review state, temporary work grouping, code-layer grouping, screen grouping, category grouping, or generic catch-all bucket. If a candidate boundary is broad or unclear, criteria-review must fail it unless it is recorded as `rejected` broad grouping or as a concrete split proposal based on observed capabilities, workflows, responsibilities, contracts, or policies before writing confirmed docs.

Criteria-review must also fail a criteria draft that rejects a broad source root but does not account for obvious concrete aggregates underneath it. A rejected broad root needs either concrete aggregate candidates, concrete split proposals, or a recorded explanation that no route/controller/service/policy/persistence/workflow evidence supports a durable lower-level boundary.

## Core Business Term Coverage Gate

Before writing or refreshing atom files, identify source-repeated business nouns from type/interface names, collection keys, UI titles, API payloads, and existing domain atoms. Each core business term must be defined in `project/project-glossary.md` or in an appropriate domain atom before derived behavior is treated as covered.

Do not document a derived concept while its parent business term is missing or underdefined. If the parent meaning is uncertain, put the missing definition and source evidence in the change plan or `Gaps` instead of writing confirmed intent.

Do not force admin, operator, or screen-centric language when the source project is not an admin UI. For non-UI services, libraries, jobs, agents, or APIs, describe the relevant caller, service, job, policy, or system flow instead of inventing an operator workflow. When a UI or command entry point exists, include that entry point as source evidence.

Each covered core business term should state:

- business meaning
- owning domain
- primary actor, user, or system action
- source of truth
- stored input fields versus API/computed output fields
- related status, hold, deduction, threshold, display, or availability rules
- aliases, related source identifiers, forbidden conflations, and uncertainty

## Service Logic Natural-Language Coverage

Atomic docs are a natural-language service logic standard, not a source index. Generated docs should let a reviewer understand the meaningful runtime behavior without rereading every source file first.

Document all meaningful application, service, and domain logic that affects product behavior, operational behavior, or integration behavior. This includes conditions, branches, state transitions, validation, permission checks, policy rules, transaction or idempotency behavior, persistence side effects, external calls, emitted events, error handling, and recovery behavior.

Do not treat endpoint lists, controller lists, service class names, method names, file paths, or terse class-role summaries as service logic coverage. These identifiers are source evidence only until the atom explains in natural language what the source behavior does, when it does it, what it refuses, what it stores or changes, what it calls, and what result or failure it produces.

For each meaningful service logic item, the docs must record:

- source identifiers that were inspected
- owning atom or a coverage gap when ownership is unresolved
- natural-language behavior description
- input conditions, guards, branches, and failure conditions that affect the behavior
- state, persistence, integration, emitted-event, or external side effects
- confirmed or inferred basis for intent, rule, requirement, exclusion, or boundary
- judgment readiness: whether the item can be judged from the docs or must remain `confirmation_needed` or a coverage gap

Complex logic should be split into multiple atoms when separate behaviors, policies, states, or side effects need independent judgment. Splitting does not allow omission: each split atom must still describe the concrete conditions, outcomes, and side effects it owns.

Trivial getters, mechanical DTO copying, framework boilerplate, and generated wiring do not require standalone atoms when they carry no service meaning. If such code changes validation, permission, persistence, transaction, state, integration, error, idempotency, or recovery behavior, document that behavior in natural language.

## Implementation Reconstruction Coverage

Atomic docs must satisfy a source-to-docs-to-code implementation reconstruction standard for the accepted scope. A competent implementer should be able to implement the same functional behavior from the docs without rereading source. This does not require pixel-perfect visual design, exact CSS values, component internal structure, or library choice unless source or user requirements make them behavior-relevant. It does require basic design/state presentation, screen structure, and visual feedback guidance when they affect product behavior or the style the user asked to preserve.

For frontend/UI source, document app shell behavior, routing, route/hash/query handling, selected entity and persistence, permission/access/no-data guards, preload/fallback behavior, form field matrix, collection editor behavior, validation/refusal/defaulting, payload transforms, save/delete scopes, confirmation modals, readiness blocker order, detail routes, empty/loading/error states, and basic design/state presentation enough to implement the required style.

For backend/API/service/job/integration source, document API contract, request/response payload, authorization/authentication, validation/guard behavior, domain policy, transaction or idempotency behavior, persistence mutation/read model, DB schema/DTO fields that affect behavior, async job/event behavior, external integration behavior, and error/retry/recovery semantics.

A docs set is not implementation-reconstruction-ready when these behaviors are only endpoint identifiers, screen identifiers, source identifiers, method-call sequences, source convention notes, one-line inventory, or unresolved `confirmation_needed` without next action.

## Source Fact Fidelity Gate

Atom `Rules`, `Current Implementation`, `Gaps`, evidence packets, and review findings must preserve the source-observed behavior actually reachable through the inspected entry path. Do not simplify a branch into the behavior that a field annotation, method name, service class name, or DTO type seems to imply.

When documenting validation, refusal, defaulting, fallback, exception, read-only, or storage-effect behavior, compare the relevant source branches instead of relying on one identifier. Inspect the endpoint or caller binding, validator activation, service guard, null handling, blank handling, optional dependency fallback, default value fallback, explicit exception branches, runtime exception possibility, transaction mode, and persistence calls when those details affect product, operation, or integration behavior.

If source allows a null, blank, optional dependency, fallback value, or runtime path instead of refusing it, the docs must preserve that branch as observed behavior or record it as `confirmation_needed`. Do not rewrite an allowed fallback path as a guaranteed validation failure. Conversely, do not describe a behavior as safe or recovered when the source can throw an unhandled runtime exception.

If an observed behavior depends on both declarative metadata and runtime wiring, describe both sides. For example, a request field annotation is not enough to claim that the endpoint rejects the request unless the controller or caller path actually activates validation. Use a generic coverage gap or `confirmation_needed` when the inspected source does not prove the stronger claim.

Judgment-bearing `Gaps` and review findings are not sufficient when they only contain a label. Each such item must include source evidence, confirmed or inferred basis, affected behavior, next action, and related stable `atom_key` and AID values when the affected atom lines are known.

## Atomic Docs Goal Boundary

The Codex Goal used after criteria approval is an execution scope for performing the accepted docs operation. It does not replace criteria approval, accepted docs write scope, atom content, judgment labels, source evidence, user review, or source-baseline metadata.

Do not write Goal status or Goal completion as atom-level status, per-atom freshness, or judgment evidence. Code suitability judgments still come from approved criteria, generated atoms, source evidence, graph relationships, baseline metadata, and controlled judgment labels.

If the Goal is incomplete, blocked, waiting for user input, or blocked by review FAIL, preserve that state in the operation summary or change plan rather than in atom judgment labels. Atom files should continue to describe intent, rules, current implementation, planned changes, and gaps.

## Atom Line ID Policy

Every `*-atom.md` file must assign a stable unique ID to each judgment-relevant meaning line. A meaning line is a bullet, paragraph, table row, source evidence row, planned-change item, gap item, or reviewable behavior statement that can be referenced by a change plan, review finding, judgment label, or source evidence mapping.

Use this format:

```text
[AID:<atom_key>.<section-code>.<NNN>]
```

For example:

```text
- [AID:paid-order-processing.impl.003] paid line마다 ticket group 하나를 만들고 저장한다.
```

Section codes are:

- `intent` for `Intent`
- `rules` for `Rules`
- `impl` for `Current Implementation`
- `plan` for `Planned Changes`
- `gap` for `Gaps`
- `source` for source evidence rows

Use `- [AID:...] 내용` for bullets, `[AID:...] 내용` for standalone paragraphs, and an `AID` column for tables. New AID values use the target atom's stable `atom_key` as the prefix and must be globally unique across the docs set, not just unique within one atom.

Do not require AID values on frontmatter, `graph_edges`, blank lines, section headings, code fence markers, or purely structural Markdown. Project documents such as `project/atomization-criteria.md`, `project/project-goal.md`, `project/project-glossary.md`, `project/service-logic-inventory.md`, and `project/source-convention.md` are not atoms and are not required to use AID values.

Preserve AID stability. If the same meaning line is edited, moved, split into another atom, merged into another atom, retained after an atom rename, or retained after a category/domain-path move, keep its existing AID when the meaning is still traceable. Category moves, file renames, path drift, and atom slug changes are not AID change reasons. Assign new AID values only to newly introduced meaning lines. Do not renumber existing AID values for cosmetic ordering. If an AID migration is unavoidable, record the migration explicitly in the change plan and review findings. Do not infer the current owning atom only from an older preserved AID prefix; use frontmatter `atom_key` for current identity.

## Required Atom Sections

Each atom file must preserve these sections:

- `Intent`
- `Rules`
- `Current Implementation`
- `Planned Changes`
- `Gaps`

`Intent` and `Rules` describe confirmed user intent only when the user or approved workflow has confirmed them. AI-written intent or rules must be marked as inferred until confirmed and must be linked to `Gaps`. When intent or rules are confirmed, include the confirmation basis and whether the behavior is required, optional, excluded, or boundary-defining. Include acceptance criteria when the behavior can be judged by observable source behavior.

`Current Implementation` records source-observed implementation facts with source evidence such as files, classes, functions, states, payload fields, storage effects, or integration points, and expresses those facts as natural-language service logic. A bare list of source identifiers, endpoints, controllers, service classes, or methods is not sufficient.

For Korean managed docs, write the prose under `Current Implementation` with Korean-first structure when that structure helps the atom explain behavior. Recommended subheadings are:

- `### 동작 흐름`
- `### 관찰된 판단 규칙`
- `### 상태와 저장 효과`
- `### 외부 연동과 이벤트`
- `### 실패와 복구 동작`
- `### Source Evidence`

Do not force every atom to include every subheading. Use only the applicable subsections, but make the implementation readable as behavior criteria: input conditions, branches or refusals, state changes, stored or external effects, and failure results. Do not write `Current Implementation` as a translated English skeleton or as a method-call sequence such as "class A calls method B and then saves C" unless the atom also states the service behavior, decision rule, state effect, and failure outcome that the call implements.

`Planned Changes` records future intended work that is not yet confirmed as implemented and must classify each planned item as `approved_required_change`, `approved_optional_change`, `tentative_future_change`, or `implemented_pending_confirmation`. `Gaps` records judgment-labeled mismatches, uncertain inference, bug candidates, missing required behavior, missing intent, unapproved implementation, out-of-scope behavior, docs-stale findings, implemented-plan candidates, rename/merge candidates, service logic coverage gaps, and confirmation-needed boundaries.

## Judgment Evidence Policy

Atomic docs should let a reviewer determine what is implemented, what should be implemented, what is missing, what is buggy, what is unapproved or out of scope, and what still needs confirmation for the documented source baseline.

Do not add top-level per-atom status fields for these judgments. Instead, attach controlled judgment labels from `change-judgment-policy.md` to specific `Gaps`, change plan items, review findings, or domain evidence packet items.

Each judgment-bearing item must include:

- one judgment label from `change-judgment-policy.md`
- source evidence for the observed behavior or missing behavior
- confirmed or inferred basis from the relevant atom section, boundary, baseline metadata, or user approval
- next action for resolving the finding

For Korean managed docs, write judgment-bearing `Gaps`, `Planned Changes`, change plan items, and review findings with Korean-visible field labels or Korean sentence wording. Keep the controlled judgment label itself unchanged, but render the surrounding structure as `판정 라벨`, `소스 근거`, `근거`, `영향받는 동작`, `다음 조치`, and `관련 AID` when structured fields are useful. Do not use English scaffold labels such as `affected behavior`, `next action`, `basis`, `source evidence`, or `judgment label` inside Korean atom prose.

`matches_confirmed_intent` is allowed only as an explicit review finding after the reviewer inspects source evidence and confirms that no higher-priority judgment label applies. Do not treat the lack of a `Gaps` item as proof that code matches confirmed intent.

Approved project documents may provide context such as non-goals or terminology boundaries, and domain context atoms must preserve excluded behavior and adjacent-domain boundaries clearly enough for `out_of_scope_behavior` review. A service judgment still needs service logic atom content, source evidence, baseline metadata, and a controlled judgment label.

## Forbidden Shapes

- Do not split state into type folders such as `current-state/`, `future-plan/`, or `gap/`.
- Do not put per-atomic freshness/status fields inside atom files.
- Do not store per-file commit status in the atomic document.
- Do not collapse `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` into one undifferentiated narrative.
- Do not present AI inference as confirmed user intent.
- Do not use project-specific example domain names as skill-level rules.
- Do not leave an evasive split or coverage gap in place of documenting inspected service logic. A note that logic should be split later is invalid unless it also records the concrete source evidence, proposed owners, unresolved question, and the behavior already observed.
- Do not use source identifiers without natural-language behavior as proof that service logic is covered.

## Atomicity Policy

An atom is too broad when it covers unrelated behaviors, policies, rules, states, planned changes, or gap boundaries. Split or propose a split before writing confirmed docs. If the split is ambiguous, keep candidates in the change plan or `Gaps` and ask the user.

Do not write a vague split gap that says more precision is needed without concrete evidence. A split proposal must name candidate atom keys, tentative paths or slugs, owning domain path, source files/classes/functions or other source identifiers, the split criterion, each candidate atom's behavior/state/rule responsibility, and unresolved questions. If that evidence is missing, record the missing evidence as a `Gaps` item instead of pretending the split is already specified.
