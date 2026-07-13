# Atomic Document Contract

## Contents

- [Responsibility](#responsibility)
- [Path Contract](#path-contract)
- [Project And Domain Context Policy](#project-and-domain-context-policy)
- [Project Document Contract](#project-document-contract)
- [Detailed Sibling References](#detailed-sibling-references)

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
<doc-root>/project/source-convention.md
```

- Project-level documents are control, context, criteria, inventory, or source-interpretation documents. They are not service logic atoms and do not use atom frontmatter, AID, graph edges, or required atom sections unless a separate accepted migration explicitly converts them into atom files.
- Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` files are legacy artifacts. Treat them as migration/update candidates; do not use those paths as defaults for new project goal or glossary work.
- A service logic inventory is operation-local by default under `.stageflow/atomic-docs/requests/<request-id>/`. Keep `<doc-root>/project/service-logic-inventory.md` only when the accepted scope explicitly asks for a final coverage index synced to real `atom_key` and AID references.

Default project-level criteria document:

```text
<doc-root>/project/atomization-criteria.md
```

- `atomization-criteria.md` records compact draft or approved rules for deciding domain ownership, atom split/merge, documentation depth, selective identity, evidence, and review. Source-derived domain/atom candidates belong in operation state, not this file.
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
<doc-root>/project/source-convention.md
```

An explicitly retained project-level coverage index may also use:

```text
<doc-root>/project/service-logic-inventory.md
```

These files must not follow the `*-atom.md` path contract, must not require frontmatter `atom_key`, must not require AID values, must not use `graph_edges`, and must not require the atom sections `Intent`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`.

Existing `<doc-root>/project/project-goal-atom.md` and `<doc-root>/project/project-glossary-atom.md` are legacy project-document artifacts. When they are present, read them as possible source material, then propose a migration or update to `project/project-goal.md` and `project/project-glossary.md` instead of continuing the atom-named defaults.

Project document writing rules:

- `project-goal.md` records the service or product purpose, target users or callers, success criteria, non-goals, confirmed business direction, and source-unverifiable items as `confirmation_needed`. It must not turn config paths, baseline metadata paths, cache paths, reset notes, deletion notes, reviewer logs, or docs-operation status into the service goal.
- `project-glossary.md` records only ambiguous, shared, ownership-sensitive, or decision-critical terms. Each entry must explain meaning and source of truth, plus ownership, actors, stored/computed distinction, related rules, aliases, forbidden conflations, or uncertainty only when applicable.
- A service logic inventory is lightweight writer/reviewer input, not a service logic atom. Keep it as operation-local state by default. If `<doc-root>/project/service-logic-inventory.md` is explicitly retained as a final coverage index, each behavior aggregate must record its decision summary, source identifiers, owner or disposition, and only the rules, state/effects, risk, related AID, or judgment fields that apply. Do not duplicate the atom body in the inventory.
- `source-convention.md` is a source interpretation helper. Runtime-impacting conventions must link to a related service logic atom_key and AID, or to a coverage gap when no atom exists yet. Non-runtime code style stays in this document and must not be mixed into service logic atoms.
- `atomization-criteria.md` records durable generation rules, project exceptions, unresolved approval decisions, and approval state. It is not a candidate map, operation ledger, or direct code suitability evidence.

Project document review rules:

- Do not fail a project document only because it omits atom required sections, frontmatter `atom_key`, AID values, or `graph_edges`.
- Fail when a project document directly claims code is implemented, missing, buggy, matching, or out of scope as if it were a service logic atom.
- Fail when `project-goal.md` treats docs configuration, baseline paths, plugin cache paths, reset/delete notes, or operation logs as service/product goals.
- Fail when a glossary entry is too shallow to resolve the ambiguity, ownership question, or conflict for which it was created.
- Fail when a retained `service-logic-inventory.md` is only a one-line summary, lacks behavior-level fields needed by writer/reviewer work, or is not synced to real atom_key/AID references; do not write or update baseline metadata while the inventory is in that state.
- Fail when `source-convention.md` records runtime-impacting behavior without a related atom_key/AID or a coverage gap.

## Detailed Sibling References

Keep this reference under 200 lines as the structural entrypoint. Load the sibling references directly from `SKILL.md` when the operation needs their detail:

- `references/atomization-criteria-contract.md` for the first criteria document, approved criteria shape, and criteria-review contract.
- `references/source-convention-and-domain-policy.md` for source convention documents, domain discovery, hybrid naming, domain boundary review, and core business term coverage.
- `references/service-logic-coverage.md` for decision-complete service logic coverage, proportional depth, source fact fidelity, and Goal boundary rules.
- `references/atom-format-and-judgment.md` for AID policy, required atom sections, judgment evidence, forbidden shapes, and atomicity rules.
