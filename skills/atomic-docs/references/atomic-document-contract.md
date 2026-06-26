# Atomic Document Contract

## Contents

- [Responsibility](#responsibility)
- [Path Contract](#path-contract)
- [Project And Domain Context Policy](#project-and-domain-context-policy)
- [Domain Discovery Policy](#domain-discovery-policy)
- [Domain Boundary Quality Gate](#domain-boundary-quality-gate)
- [Core Business Term Coverage Gate](#core-business-term-coverage-gate)
- [Required Atom Sections](#required-atom-sections)
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

## Project And Domain Context Policy

Use generic context atoms to preserve project and domain intent without hardcoding project-specific folder names.

Default project-level atoms:

```text
<doc-root>/project/project-goal-atom.md
<doc-root>/project/project-glossary-atom.md
```

- `project-goal-atom.md` records the project-wide purpose, target users, success criteria, non-goals, current direction, planned direction, and uncertain project intent.
- `project-glossary-atom.md` records terms used across the project. Each term should include its definition, relevant domains, aliases, forbidden conflations, related source identifiers, and uncertainty when applicable.

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

Do not document a derived concept such as `resource deduction` while the parent business term such as `resource` / `제한자원` is missing or underdefined. If the parent meaning is uncertain, put the missing definition and evidence in the change plan or `Gaps` instead of writing confirmed intent.

Do not force admin, operator, or screen-centric language when the source project is not an admin UI. For non-UI services, libraries, jobs, agents, or APIs, describe the relevant caller, service, job, policy, or system flow instead of inventing an operator workflow. When a UI or command entry point exists, include that entry point as source evidence.

Each covered core business term should state:

- business meaning
- owning domain
- primary actor, user, or system action
- source of truth
- stored input fields versus API/computed output fields
- related status, hold, deduction, threshold, display, or availability rules
- aliases, related source identifiers, forbidden conflations, and uncertainty

## Required Atom Sections

Each atom file must preserve these sections:

- `Intent`
- `Rules`
- `Current Implementation`
- `Planned Changes`
- `Gaps`

`Intent` and `Rules` describe confirmed user intent only when the user or approved workflow has confirmed them. AI-written intent or rules must be marked as inferred until confirmed and must be linked to `Gaps`.

`Current Implementation` records source-observed implementation facts. `Planned Changes` records future intended work that is not yet confirmed as implemented. `Gaps` records mismatches, uncertain inference, bug candidates, missing intent, implemented-plan candidates, rename/merge candidates, and confirmation-needed boundaries.

## Forbidden Shapes

- Do not split state into type folders such as `current-state/`, `future-plan/`, or `gap/`.
- Do not put per-atomic freshness/status fields inside atom files.
- Do not store per-file commit status in the atomic document.
- Do not collapse `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps` into one undifferentiated narrative.
- Do not present AI inference as confirmed user intent.
- Do not use project-specific example domain names as skill-level rules.

## Atomicity Policy

An atom is too broad when it covers unrelated behaviors, policies, rules, states, planned changes, or gap boundaries. Split or propose a split before writing confirmed docs. If the split is ambiguous, keep candidates in the change plan or `Gaps` and ask the user.
