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

Create `project/project-glossary.md` only when multiple areas share an ambiguous, ownership-sensitive, or easily confused term. It contains `## Terms` and this exact table:

```text
| Term | Meaning | Scope Or Owner | Source Of Truth | Do Not Confuse With | Sources |
```

Every row describes a real term and includes at least one valid source locator. Delete the glossary if no qualifying term remains.

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
