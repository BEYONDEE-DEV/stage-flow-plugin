# Atomic Graph

## Responsibility

This reference defines graph relationships between atom files. The graph helps preserve context and find likely related atoms without scanning every document for every source behavior change.

## Storage

Store graph edges in each atom file frontmatter under `graph_edges`. Do not store the same edge set in both frontmatter and body sections.

Minimum edge fields:

- `type`
- `target_key`
- `target_path`
- `reason`

The `reason` is one human-readable sentence. Do not add relationship strength, priority, ranking score, source anchor, or numeric relevance fields.

Graph frontmatter is structural metadata. Do not assign atom line IDs to `graph_edges`; AID values belong to judgment-relevant meaning lines in atom body content.

## Target Keys And Paths

- `target_key` is the target atom's stable frontmatter `atom_key`, not the atom file slug, category path, domain path, or filename.
- Duplicate `atom_key` values and duplicate graph `target_key` references that resolve to different atom files are invalid conflicts. Do not silently auto-prefix with a domain, category, or generated suffix.
- If a likely `atom_key` would conflict, choose a clearer stable key before writing or ask the user when the boundary is ambiguous.
- Existing atoms without frontmatter `atom_key` may use slug-derived identity only as a legacy fallback for discovery. Treat that fallback as an explicit `atom_key` migration candidate before adding new graph relationships.
- `target_path` is a mutable locator that points to the current existing target `*-atom.md` file relative to the docs root.
- If `target_path` is stale but `target_key` resolves to an existing atom with the same `atom_key`, correct the path during refresh and show the path correction in the change plan.
- Graph edges may only target existing atom files. Future, missing, rename, or merge candidates belong in a change plan or `Gaps` until the target file exists.
- The criteria document at `project/atomization-criteria.md` is not an atom file and must not be used as a `graph_edges` source or target.

## Edge Types And Direction

Start with a small controlled vocabulary such as:

- `related_to`
- `depends_on`
- `replaces`
- `conflicts_with`

All graph edges are directional. Add explicit inverse edges only when the inverse relationship is needed and meaningful.

## Traversal Policy

Existing graph edges are not proof that every relationship has been discovered. Before graph traversal for a changed or planned behavior, inspect the relevant domain/common context, glossary meaning and source-of-truth rules, shared payload/state/storage/permission/integration contracts, and operation-inventory ownership. Use these surfaces to seed missing relationship candidates without running an exhaustive project-wide search for every AID.

When that check finds a durable relationship, update the existing atom body or graph edge through the accepted change plan. Put unresolved candidates or conflicts in the existing change plan, `Gaps`, or reviewer report. Do not create a separate impact-trace artifact. For partial work, report inspected adjacent impact and uninspected boundaries instead of claiming project-wide conflict closure.

Source-to-atom discovery is a separate seed step. Atomic graph traversal starts from seed atom files and expands to related atom files. Continue traversal while related atoms create plausible modification candidates. Stop when no further modification candidates appear.

Relevance should be inferred from edge type and traversal distance, not strength or priority fields.

## Root Graph Policy

Do not create a root graph output by default. If a root graph is needed later, generate it as a programmatic derived artifact from atom frontmatter, not as a manually maintained source of truth.
