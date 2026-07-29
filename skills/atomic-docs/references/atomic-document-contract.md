# Atomic Document Contract

## Managed Paths

```text
<docs-root>/
  project/
    project-goal.md
    project-glossary.md       # conditional
  <domain>/
    <topic>-atom.md
```

Domain directories and Atom filenames use lower-kebab names. Do not create permanent indexes, graphs, criteria, request records, or review artifacts.

## Project Goal

`project/project-goal.md` has exactly these level-two headings in this order:

1. `Purpose`
2. `Users`
3. `Success`
4. `Non-goals`
5. `Sources`

Every section is meaningful. `Sources` contains at least one valid source locator.

## Project Glossary

Create `project/project-glossary.md` when the project has at least one term that a new developer needs defined to understand its requirements, docs, UI, API, or business behavior. This is a general project glossary, not a cross-Atom relationship table or evidence ledger. It contains `## Terms` and this exact table:

```text
| Term | Definition |
```

Derive candidates from the project goal, the selected Atom docs, user-facing language, API concepts, and inspected source. Include a term when omitting its definition could make a new developer misunderstand the project. Cross-Atom reuse, ambiguity, or sensitive ownership strengthens the need for an entry but is never a prerequisite. Terms owned by one Atom still qualify.

Cover the applicable vocabulary categories:

- user roles and actors
- core domain entities, important sub-entities, and their relationships
- business actions, workflows, states, and results
- project-specific identifiers, acronyms, aliases, and externally visible names
- ordinary words that have a narrower or unusual meaning in this project

Write one row per unique canonical term:

- `Term`: the name used by the project.
- `Definition`: a concise, non-circular explanation of what the term means and what role it has in this project. Make the definition understandable without requiring the reader to open the source.

Explain a material distinction from a related term inside `Definition` when needed. If the project uses one term for a definition, issued instance, current state, or history, explain that usage clearly. Create separate rows only when the project itself has separate stable terms; do not invent artificial names solely to split lifecycle or abstraction levels.

Do not add an isolated type, function, field, route parameter, or implementation symbol merely because it exists. Include it only when it is also meaningful project vocabulary. Do not put source locators, ownership metadata, source-of-truth claims, or review evidence in the glossary. Verify definitions against inspected source while writing and reviewing; keep persistent source evidence in the applicable Atom `Sources` sections.

Delete the glossary only when no project term needs definition.

## Atom

Every `*-atom.md` begins with exact-purpose YAML frontmatter:

```yaml
---
atom_key: checkout-payment
depends_on:
  - customer-credit
---
```

`atom_key` is globally unique lower-kebab text and remains stable across file moves. `depends_on` is required; use `[]` when empty. Entries are unique existing Atom keys, exclude self, and represent only direct dependencies.

After one level-one title, every Atom has exactly these level-two headings in this order:

1. `Purpose`
2. `Boundaries`
3. `Contracts`
4. `Implementation`
5. `Sources`
6. `Changes`
7. `Open Questions`

All sections are required. `Purpose`, `Boundaries`, `Contracts`, `Implementation`, and `Sources` contain meaningful content. An empty `Changes` or `Open Questions` contains exact `- 없음` and nothing else.

- `Purpose`: why this area exists and the outcome it owns.
- `Boundaries`: included responsibility, explicit exclusions, and handoffs.
- `Contracts`: durable rules, externally observable behavior, invariants, and shared obligations.
- `Implementation`: concise current orientation: entry points, important flow, persistence, integrations, or constraints.
- `Sources`: exact source evidence.
- `Changes`: active approved Atomic Impl deltas only.
- `Open Questions`: unresolved decisions that materially affect development.

## Source Locators

Use an inline-code locator with exact shape:

```text
`<source-name>:<source-root-relative-path>#<symbol>`
```

Examples of source names are `primary` and a configured auxiliary `name`. The path:

- uses normalized POSIX separators
- is relative to that source root
- stays inside that source root
- names an existing file
- has no line number or line range

The symbol is non-empty and identifies the relevant declaration, route, configuration key, document heading, or stable source anchor. Use at least one locator per `Sources` section; two to five is a writing guide, not a validation quota.

## Requirement IDs

Atomic Docs has no general-purpose semantic identifier. Only an active Atomic Impl change uses:

```text
[RID:<atom_key>.<lower-kebab-slug>]
```

The RID appears exactly once, only in the owning Atom's `Changes` section, and its prefix matches that Atom's `atom_key`. There is no RID reference token. A change item includes the required outcome or invariant needed to implement and review it.

After implementation and user result approval, remove the RID. Promote durable responsibility or behavior into `Contracts` or `Boundaries`, and update `Implementation` and `Sources` to describe the realized code.
