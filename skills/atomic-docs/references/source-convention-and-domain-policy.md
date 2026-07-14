# Source Convention And Domain Policy

## Responsibility

This reference is the normative owner of source-convention content and semantic review failures, domain discovery, hybrid domain naming, domain boundary review, and core business term coverage. `atomic-document-contract.md` owns structural paths and non-atom classification; `project-documents-and-inventory.md` owns creation and retention timing.

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

- Non-runtime code style belongs only in `project/source-convention.md`; do not put it in service logic atom `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, or `Gaps` unless the user explicitly asks for a style atom outside normal service-logic docs.
- Runtime-impacting conventions may be summarized in `project/source-convention.md`. Repeat or link one in a service logic atom only when it is important context for that atom's stated scope or supports an implementation/compliance judgment. Link to its `atom_key` and include its AID when one exists; do not create an atom, AID, or gap solely because a runtime convention exists.
- The source convention document alone cannot support `bug_or_regression`, `missing_required_behavior`, `matches_confirmed_intent`, `unapproved_implemented_behavior`, or `out_of_scope_behavior` for service logic. Use it as interpretation context, then connect the judgment to service logic atoms, source evidence, baseline metadata, and judgment labels.
- If a service logic atom contains simple code convention, source folder taxonomy, import order, formatting, naming, or layer-placement notes as if they were runtime behavior, reviewer must fail or request moving that material to `project/source-convention.md`.
- If a source convention is used as the basis of a service-logic judgment, connect that judgment to an existing relevant atom and reachable source evidence. If no atom was selected because the convention is ordinary navigation context, no coverage gap is required.

## Domain Discovery Policy

Choose domain paths from project evidence, not from a fixed project-specific list. For targeted work, inspect the requested behavior and adjacent ownership or shared-contract surfaces. Do not require project-wide domain discovery unless the accepted operation is full-project or seeks a global baseline.

Use this priority order:

1. User-confirmed product, business, or bounded-context language.
2. Existing managed-docs-root domain language and existing context atoms.
3. Source-observed user-visible capabilities, workflows, policies, or domain models.
4. Cross-cutting boundaries such as shared platform, integration contract, infrastructure, or policy only when the content coherently affects multiple domains.

Do not confirm a domain solely from a code folder name.

Category and subdomain folders are allowed only as organization inside an approved durable boundary. They must not hide a broad domain, generic bucket, lifecycle status group, or code-layer grouping. If a category label is broad, record it as `rejected` or split it into concrete durable boundary proposals before atom writing.

When a broad source root or category/root surface is rejected, inspect below it far enough to find concrete durable responsibilities that would be useful implementation context. Repeated project-native business language, ownership, shared contracts, or change impact can justify a concrete domain candidate or split proposal. Do not stop at the broad rejection when an obvious high-value responsibility is present, but do not enumerate every sub-aggregate merely to prove coverage.

Record concrete candidates found beneath a rejected broad root in the operation inventory with their selection reason and source evidence. A broad root rejection with no follow-up is insufficient only when source evidence shows an obvious durable owner, shared/external contract, or non-obvious responsibility whose omission would make the proposed docs misleading.

Treat management/operational responsibility as a domain candidate signal when project-native verbs such as manage, register, approve, issue, settle, recover, disable, restore, or delete repeatedly appear with durable ownership, policy, shared contracts, or change impact. A verb plus an endpoint or persistence call alone does not require a candidate. The candidate name should preserve project/user business language unless user-approved or source-observed evidence supports promotion.

## Hybrid Domain Naming Policy

Use a hybrid domain naming model for operation inventories, change plans, and domain context atoms:

1. Start with project-native feature/root language observed in source roots, existing docs, API surfaces, package roots, or user vocabulary.
2. Keep those project-native names visible as the default domain/category candidates unless they are broad or unsupported.
3. Promote a cross-feature capability/common boundary only when operation evidence or a user decision records explicit promotion evidence.

Treat project-native feature/root language as the default starting point before inventing a capability alias or common boundary.

Even when a source root is broad and must be split, the codebase's own stable feature/root language is still the default naming input for concrete candidates below it.

Each operation-local domain candidate must distinguish:

- `project-native name`: the name already used by the project or user
- `source feature root`: the package/root/surface where the source-observed behavior appears
- `optional capability alias`: a proposed business capability label, if any
- `promotion reason`: why the alias should replace or sit above project-native feature language
- `approval state`: `candidate`, `approved`, `rejected`, or `needs_confirmation`

AI-renamed domain labels are not valid default domain names. If the source uses a feature root such as `auth`, `commerce`, `refund`, `resource`, `ticketgroup`, `web`, or `admin`, an operation inventory must not silently rename that root into a new abstract capability label such as `sales-fulfillment` unless one of these bases is recorded:

- user approval or user vocabulary for the new capability label
- existing managed-docs-root terminology that already uses that capability label
- durable ownership evidence showing the capability crosses multiple source feature roots

Capability or common promotion requires at least one of these evidence types: cross-feature ownership, shared persistence or state, shared policy, or shared recovery question. Without that evidence, keep the project-native feature/root name and put the cross-feature idea in `optional capability alias` or `needs_confirmation`.

Broad source feature roots such as an `admin` root are not automatically valid domains. Treat them as category/root surfaces or split proposals until operation evidence supports narrower durable boundaries. This preserves the broad-domain FAIL rule while avoiding arbitrary AI renaming.

Prefer project/user business language for the promoted aggregate. If the source behavior is about managing, registering, approving, issuing, settling, or recovering a product-visible thing, do not default to technical labels such as `configuration` only because the methods or DTOs sit in a setup/admin area. Keep technical names as source evidence or optional aliases unless the project or user actually uses them as the domain language.

Atom candidates must point their owning domain/category path at an approved or candidate hybrid boundary. Do not point atom candidates at an AI-renamed label that lacks user/source trace or promotion evidence.

## Domain Boundary Quality Gate

A first-level domain is valid only when it describes a durable ownership boundary. The boundary must be explainable as at least one of:

- a product or business capability
- a user-visible workflow
- an operational responsibility
- an integration contract
- a shared policy or platform concern

Before creating or moving a domain, the domain context or change plan must state the applicable navigation context:

- the durable responsibility the domain owns
- an important excluded capability when needed to prevent confusion
- the adjacent-domain boundary
- why the atom files in the domain tend to change together

Do not confirm a first-level domain when its main rationale is a documentation section type, lifecycle state, task status, freshness state, review state, temporary work grouping, code-layer grouping, screen grouping, category grouping, or generic catch-all bucket. If a candidate boundary is broad or unclear, the development reviewer must FAIL it unless the operation inventory records it as a rejected broad grouping or a concrete split proposal based on observed capabilities, workflows, responsibilities, contracts, or policies.

The development reviewer must also FAIL a bundle that rejects a broad source root while hiding an obvious high-value lower-level owner or shared contract needed to understand the proposed docs. It must not require a candidate, split, or disposition for every route/controller/service/policy/persistence/workflow surface underneath that root.

## Core Business Term Coverage Gate

Before writing or refreshing selected atom files, identify business terms whose meaning is ambiguous, shared across domains, ownership-sensitive, or necessary to understand those atoms. Define those terms in `project/project-glossary.md` or an appropriate domain atom. Do not inventory project-wide terminology or create glossary entries for every repeated type, collection key, UI title, or payload noun.

When a selected derived concept depends on an ambiguous parent business term, define or flag only the parent meaning needed to understand that concept. Do not turn unrelated missing vocabulary into a project-wide gap.

Do not force admin, operator, or screen-centric language when the source project is not an admin UI. For non-UI services, libraries, jobs, agents, or APIs, describe the relevant caller, service, job, policy, or system flow instead of inventing an operator workflow. When a UI or command entry point exists, include that entry point as source evidence.

Each covered core business term should state the applicable fields only:

- business meaning
- owning domain
- primary actor, user, or system action
- source of truth
- stored input versus computed output only when the distinction changes behavior
- related status, threshold, display, or availability rule only when needed for the documented decision
- aliases, forbidden conflations, source identifiers, and uncertainty when they prevent confusion or conflict
