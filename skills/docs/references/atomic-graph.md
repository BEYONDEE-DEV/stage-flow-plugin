# Atomic Graph

## Responsibility

This reference defines graph relationships between atomic docs. The graph helps preserve context and find likely related atomic docs without scanning every document for every source behavior change.

## Storage

Store graph edges in each `atomic.md` frontmatter under `graph_edges`. Do not store the same edge set in both frontmatter and body sections.

Minimum edge fields:

- `type`
- `target_key`
- `target_path`
- `reason`

The `reason` is one human-readable sentence. Do not add relationship strength, priority, ranking score, source anchor, or numeric relevance fields.

## Target Keys And Paths

- `target_key` is derived from the atomic target folder slug and must be globally unique across the docs set.
- Duplicate `target_key` values are invalid conflicts. Do not silently auto-prefix with a domain or generated suffix.
- `target_path` points to the existing target `atomic.md` path.
- If `target_path` is stale but `target_key` resolves to an existing atomic target, correct the path during refresh and show the path correction in the change plan.
- Graph edges may only target existing `atomic.md` files. Future, missing, rename, or merge candidates belong in a change plan or `Gaps` until the target document exists.

## Edge Types And Direction

Start with a small controlled vocabulary such as:

- `related_to`
- `depends_on`
- `replaces`
- `conflicts_with`

All graph edges are directional. Add explicit inverse edges only when the inverse relationship is needed and meaningful.

## Traversal Policy

Source-to-atomic discovery is a separate seed step. Atomic graph traversal starts from seed atomic docs and expands to related atomic docs. Continue traversal while related atomic docs create plausible modification candidates. Stop when no further modification candidates appear.

Relevance should be inferred from edge type and traversal distance, not strength or priority fields.

## Root Graph Policy

Do not create a root graph output by default. If a root graph is needed later, generate it as a programmatic derived artifact from atomic frontmatter, not as a manually maintained source of truth.
