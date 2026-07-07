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

## Detailed Sibling References

Keep this reference under 200 lines as the structural entrypoint. Load the sibling references directly from `SKILL.md` when the operation needs their detail:

- `references/atomization-criteria-contract.md` for the first criteria document, approved criteria shape, and criteria-review contract.
- `references/source-convention-and-domain-policy.md` for source convention documents, domain discovery, hybrid naming, domain boundary review, and core business term coverage.
- `references/service-logic-coverage.md` for natural-language service logic coverage, implementation reconstruction coverage, source fact fidelity, and Goal boundary rules.
- `references/atom-format-and-judgment.md` for AID policy, required atom sections, judgment evidence, forbidden shapes, and atomicity rules.
