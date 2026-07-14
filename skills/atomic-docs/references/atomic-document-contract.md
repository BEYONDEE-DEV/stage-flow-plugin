# Atomic Document Contract

## Contents

- [Responsibility](#responsibility)
- [Path Contract](#path-contract)
- [Project And Domain Context Policy](#project-and-domain-context-policy)
- [Project Document Contract](#project-document-contract)
- [Detailed Sibling References](#detailed-sibling-references)

## Responsibility

This reference is the structural owner of paths, stable atom identity, project-document kinds, and project/domain context-atom placement inside the configured docs root. Sibling references own project-document lifecycle, source/domain meaning, atom section content, and semantic review failures.

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

A domain context atom owns domain-wide purpose, important capabilities, durable ownership, and adjacent-domain boundaries needed for navigation and change impact. A behavior atom's `Boundaries` section owns only a local distinction that prevents ownership or handoff confusion. The behavior atom references the context atom for a shared domain boundary instead of repeating it, and the context atom does not enumerate every behavior or local boundary.

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

- A domain context atom combines the domain goal and important ownership boundary.
- It records the domain purpose, durable responsibilities, important included/excluded capabilities, adjacent-domain boundaries, and conditions for promoting shared concepts to `common`; it is not a complete behavior catalog.
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

These files must not follow the `*-atom.md` path contract, must not require frontmatter `atom_key`, must not require AID values, must not use `graph_edges`, and must not require the atom sections `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`.

Existing atom-named project documents are legacy structural shapes. Their lifecycle and migration decisions belong to `project-documents-and-inventory.md`; criteria meaning belongs to `atomization-criteria-contract.md`; source-convention meaning belongs to `source-convention-and-domain-policy.md`. This structural contract does not redefine their writing or semantic review rules.

Existing `<doc-root>/project/atomization-criteria-atom.md` is a legacy path. Treat it as migration source material and an explicit migration/update candidate; do not use it as the default path for new criteria work.

## Detailed Sibling References

Keep this reference under 200 lines as the structural entrypoint. Load the sibling references directly from `SKILL.md` when the operation needs their detail:

- `references/atomization-criteria-contract.md` for the first criteria document, approved criteria shape, and criteria-review contract.
- `references/project-documents-and-inventory.md` for project-document lifecycle, inventory retention, and operation inventory/evidence flow.
- `references/source-convention-and-domain-policy.md` for source convention documents, domain discovery, hybrid naming, domain boundary review, and core business term coverage.
- `references/service-logic-coverage.md` for implementation-context selection, proportional depth, source exploration, source fact fidelity, and Goal boundary rules.
- `references/atom-format-and-judgment.md` for AID policy, required atom sections, atom-local judgment placement, forbidden shapes, and atomicity rules.
- `references/change-judgment-policy.md` for controlled labels, judgment precedence, and finding evidence.
