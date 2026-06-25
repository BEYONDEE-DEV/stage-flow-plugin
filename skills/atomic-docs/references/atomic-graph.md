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

## Target Keys And Paths

- `target_key` is derived from the atom file slug by removing the `-atom.md` suffix and must be globally unique across the docs set.
- Duplicate `target_key` values are invalid conflicts. Do not silently auto-prefix with a domain or generated suffix.
- If a likely atom slug would conflict, choose a clearer file slug before writing or ask the user when the boundary is ambiguous.
- `target_path` points to the existing target `*-atom.md` file relative to the docs root.
- If `target_path` is stale but `target_key` resolves to an existing atom file, correct the path during refresh and show the path correction in the change plan.
- Graph edges may only target existing atom files. Future, missing, rename, or merge candidates belong in a change plan or `Gaps` until the target file exists.

## Edge Types And Direction

Start with a small controlled vocabulary such as:

- `related_to`
- `depends_on`
- `replaces`
- `conflicts_with`

All graph edges are directional. Add explicit inverse edges only when the inverse relationship is needed and meaningful.

## Traversal Policy

Source-to-atom discovery is a separate seed step. Atomic graph traversal starts from seed atom files and expands to related atom files. Continue traversal while related atoms create plausible modification candidates. Stop when no further modification candidates appear.

Relevance should be inferred from edge type and traversal distance, not strength or priority fields.

## Root Graph Policy

Do not create a root graph output by default. If a root graph is needed later, generate it as a programmatic derived artifact from atom frontmatter, not as a manually maintained source of truth.
