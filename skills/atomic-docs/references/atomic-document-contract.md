# Atomic Document Contract

## Contents

- [Responsibility](#responsibility)
- [Path Contract](#path-contract)
- [Project And Domain Context Policy](#project-and-domain-context-policy)
- [Atomization Criteria Document](#atomization-criteria-document)
- [Domain Discovery Policy](#domain-discovery-policy)
- [Domain Boundary Quality Gate](#domain-boundary-quality-gate)
- [Core Business Term Coverage Gate](#core-business-term-coverage-gate)
- [Service Logic Natural-Language Coverage](#service-logic-natural-language-coverage)
- [Atomic Docs Goal Boundary](#atomic-docs-goal-boundary)
- [Atom Line ID Policy](#atom-line-id-policy)
- [Required Atom Sections](#required-atom-sections)
- [Judgment Evidence Policy](#judgment-evidence-policy)
- [Forbidden Shapes](#forbidden-shapes)
- [Atomicity Policy](#atomicity-policy)

## Responsibility

This reference defines the managed documentation shape inside the configured documentation submodule.

## Path Contract

Every atom uses this exact organization:

```text
<doc-root>/<domain>/<atomic-target>-atom.md
```

- `<doc-root>` is the confirmed documentation submodule root.
- `<domain>` is the first-level domain folder below the docs root.
- `<atomic-target>` is a file slug for one user-visible behavior, policy, rule, state, plan, context, or gap boundary.
- Every atom file must end with `-atom.md`.
- The atom file slug without `-atom.md` creates the default `target_key` and must be globally unique across the docs set.
- Do not create new `<atomic-target>/atomic.md` folder-shaped atoms. If an existing docs set uses that older shape, propose a migration before changing paths.
- The atomization criteria document is not an atom and is exempt from this path contract.

## Project And Domain Context Policy

Use generic context atoms to preserve project and domain intent without hardcoding project-specific folder names.

Default project-level atoms:

```text
<doc-root>/project/project-goal-atom.md
<doc-root>/project/project-glossary-atom.md
```

- `project-goal-atom.md` records the project-wide purpose, target users, success criteria, non-goals, current direction, planned direction, and uncertain project intent.
- `project-glossary-atom.md` records terms used across the project. Each term should include its definition, relevant domains, aliases, forbidden conflations, related source identifiers, and uncertainty when applicable.

Default project-level criteria document:

```text
<doc-root>/project/atomization-criteria.md
```

- `atomization-criteria.md` records draft or approved criteria used to decide domain boundaries, split/merge atom files, draft docs, review docs, and apply judgment policy.
- This criteria document is not a service-logic atom, not a graph target, and not direct code suitability evidence. Code suitability judgments come from generated natural-language service logic atoms, source evidence, graph relationships, baseline metadata, and judgment labels.
- Existing `<doc-root>/project/atomization-criteria-atom.md` files are legacy artifacts. Treat them as migration/update candidates; do not use that path as the default for new criteria work.

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
- Do not create a domain-specific glossary by default. Add domain-only terms to `project/project-glossary-atom.md` with their domain scope unless the user explicitly wants separate glossary atoms.

## Atomization Criteria Document

The default criteria document path is:

```text
<doc-root>/project/atomization-criteria.md
```

After the docs root is confirmed and the user accepts the limited draft write action, create or update this document as the first atomic-docs write action when atomization criteria are needed. Use the draft criteria document to capture the user's conversation, prohibitions, atomization concerns, domain-boundary concerns, and review questions before relying on chat summaries or drafting domain atoms.

The criteria document is not an atom. It must not follow the `*-atom.md` path contract, the atomic graph contract, or the required atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`. Those required sections are for service-logic and context atom files only.

A draft criteria document is a review artifact. It must not be used as the required input for domain writer subagents, review subagents, or confirmed atom writing until the user approves the criteria. In draft state, record `Approval Status: draft, pending user approval`. After the user approves the criteria, update it to `Approval Status: approved by user` and remove obsolete draft-only or pending-approval blockers.

Record user-conversation criteria in the draft before code exploration if they affect atomization. Capture only criteria that came from the user, inspected source behavior, or approved workflow evidence; do not copy illustrative wording from skill references into the criteria document.

The criteria document must include these sections:

- `Purpose`
- `Approval Status`
- `Managed Docs Root And Scope`
- `Domain Partitioning Criteria`
- `Candidate / Approved Domain Map`
- `Atomization Perspectives`
- `Service Logic Coverage Requirements`
- `Writer Subagent Instructions`
- `Reviewer Subagent Instructions`
- `Judgment Policy Usage`
- `Open Questions And Approval Blockers`

The criteria document records:

- atomization perspectives reviewed with the user, such as domain capability, entry surface, service/application flow, state transition, policy/rule, integration contract, persistence/side effect, core business term, and failure/recovery
- every entry under `Atomization Perspectives` with these exact subfields: `Atom candidate criteria`, `Source evidence only criteria`, `Not applicable reason`, `Split/merge criteria`, `Source evidence requirement`, and `Unresolved questions`
- which perspectives create atom candidates, which are source evidence only, and which are not applicable for the current source shape
- domain partitioning criteria for deciding first-level domain folders
- a candidate or approved domain map that records each domain name, owned behavior, excluded behavior, adjacent domain boundary, why the atoms in that domain change together, source evidence, unresolved questions, and approval state
- split and merge criteria, including how to decide when behavior belongs in one atom versus multiple atoms
- source evidence requirements for each atom candidate
- forbidden vague split gaps and the minimum evidence needed for a concrete split proposal
- writer subagent and review subagent checklists that future docs operations must read before drafting or reviewing atom files

These perspectives are not fixed document types. Entry surfaces discovered in the target source may be evidence, but the criteria document must not force a separate atom merely because that surface exists.

Domain approval states are limited to `candidate`, `approved`, `rejected`, and `needs_confirmation`. Do not approve a domain solely from a code folder name, endpoint, controller, service class, screen, lifecycle state, temporary task grouping, or generic catch-all rationale. A domain can be approved only when evidence shows a durable boundary such as product or business capability, user-visible workflow, operational responsibility, integration contract, or shared policy/platform concern.

Do not accept a criteria document that only lists perspective names or domain names. Do not accept one-line perspective summaries. A criteria-review subagent must fail the draft when any perspective is missing one of the required subfields, when a required subfield is empty or placeholder-only, or when a perspective with no current source evidence fails to record a concrete `Not applicable reason` or `Unresolved questions` entry.

If a perspective or domain candidate has no current source evidence, mark it not applicable with a reason or keep the missing evidence as an unresolved question.

## Domain Discovery Policy

Choose domain folders from project evidence, not from a fixed project-specific list.

Use this priority order:

1. User-confirmed product, business, or bounded-context language.
2. Existing docs-submodule domain language and existing context atoms.
3. Source-observed user-visible capabilities, workflows, policies, or domain models.
4. Cross-cutting boundaries such as shared platform, integration contract, infrastructure, or policy only when the content coherently affects multiple domains.

Do not confirm a domain solely from a code folder name.

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

Do not confirm a first-level domain when its main rationale is a documentation section type, lifecycle state, task status, freshness state, review state, temporary work grouping, code-layer grouping, screen grouping, or generic catch-all bucket. If a candidate boundary is broad or unclear, present a split proposal based on observed capabilities, workflows, responsibilities, contracts, or policies before writing confirmed docs.

## Core Business Term Coverage Gate

Before writing or refreshing atom files, identify source-repeated business nouns from type/interface names, collection keys, UI titles, API payloads, and existing domain atoms. Each core business term must be defined in `project/project-glossary-atom.md` or in an appropriate domain atom before derived behavior is treated as covered.

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

## Atomic Docs Goal Boundary

The Codex Goal used after criteria approval is an execution scope for performing the accepted docs operation. It does not replace criteria approval, accepted docs write scope, atom content, judgment labels, source evidence, user review, or source-baseline metadata.

Do not write Goal status or Goal completion as atom-level status, per-atom freshness, or judgment evidence. Code suitability judgments still come from approved criteria, generated atoms, source evidence, graph relationships, baseline metadata, and controlled judgment labels.

If the Goal is incomplete, blocked, waiting for user input, or blocked by review FAIL, preserve that state in the operation summary or change plan rather than in atom judgment labels. Atom files should continue to describe intent, rules, current implementation, planned changes, and gaps.

## Atom Line ID Policy

Every `*-atom.md` file must assign a stable unique ID to each judgment-relevant meaning line. A meaning line is a bullet, paragraph, table row, source evidence row, planned-change item, gap item, or reviewable behavior statement that can be referenced by a change plan, review finding, judgment label, or source evidence mapping.

Use this format:

```text
[AID:<atom-target-key>.<section-code>.<NNN>]
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

Use `- [AID:...] 내용` for bullets, `[AID:...] 내용` for standalone paragraphs, and an `AID` column for tables. AID values must be globally unique across the docs set, not just unique within one atom.

Do not require AID values on frontmatter, `graph_edges`, blank lines, section headings, code fence markers, or purely structural Markdown. The criteria document at `project/atomization-criteria.md` is not an atom and is not required to use AID values.

Preserve AID stability. If the same meaning line is edited, moved, split into another atom, merged into another atom, or retained after an atom rename, keep its existing AID when the meaning is still traceable. Assign new AID values only to newly introduced meaning lines. Do not renumber existing AID values for cosmetic ordering. If an AID migration is unavoidable, record the migration explicitly in the change plan and review findings.

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

`matches_confirmed_intent` is allowed only as an explicit review finding after the reviewer inspects source evidence and confirms that no higher-priority judgment label applies. Do not treat the lack of a `Gaps` item as proof that code matches confirmed intent.

Project and domain context atoms must preserve non-goals, excluded behavior, and adjacent-domain boundaries clearly enough for `out_of_scope_behavior` judgments.

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

Do not write a vague split gap that says more precision is needed without concrete evidence. A split proposal must name candidate atom slugs, owning domain, source files/classes/functions, the split criterion, each candidate atom's behavior/state/rule responsibility, and unresolved questions. If that evidence is missing, record the missing evidence as a `Gaps` item instead of pretending the split is already specified.
