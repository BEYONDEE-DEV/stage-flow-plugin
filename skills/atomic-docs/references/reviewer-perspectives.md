# Reviewer Perspective

Assign one independent semantic reviewer after the complete managed-docs diff is ready, before accepting an `update changed` source-impact no-doc result, or when reconciling a committed managed-doc range. Give the reviewer:

- the requested update scope
- the complete managed-docs diff
- the changed or selected source files
- the reason no managed-doc edit is needed when the proposed diff is empty
- the committed managed-doc path diff or old-to-new documentation-submodule commit diff when present
- exact auxiliary source content at the configured revision when used
- validator output

The reviewer answers only:

1. Are the docs useful enough to guide development without copying source mechanics?
2. Are material claims faithful to inspected source within the selected scope?
3. Are `Boundaries`, responsibilities, exclusions, handoffs, and contracts clear?
4. Do `depends_on`, source locators, and active RIDs express the selected change consistently?
5. When changed source produced no docs edit, is that disposition supported without leaving durable purpose, boundary, contract, implementation orientation, or project vocabulary stale?
6. Do committed managed-doc changes remain faithful to current source and coherent with directly affected docs without being misclassified as source seeds?

Return `FAIL` when a material project `Success` statement is filled with generic implementation
mechanics instead of project-level outcomes observable by its intended human or system consumers,
unless the technical property is itself an intended project result. Return `FAIL` when a generic
rule with a natural owning Atom is materially copied across dependent Atoms, or when
`Contracts` contains current mechanics with no reason they must survive an implementation change.

Do not require an artificial shared Atom, remove a dependent Atom's domain-specific consequence or
additional condition, or reject an item merely because it mentions a route, page size, modal, query
token, runtime setting, or another implementation-shaped name. Judge whether another consumer can
observe or rely on it and whether retaining it helps a developer decide a change.

When a glossary exists, questions 1 through 3 also cover all vocabulary exposed by the project goal and the selected Atom/source scope. Return `FAIL` when a material project term needed by a new developer is omitted, a definition is circular, vague, source-symbol-only, or inconsistent with project usage, related terms are merged in a misleading way, or artificial terms are invented only to classify lifecycle levels. A term does not need cross-Atom use to qualify. Do not require glossary ownership, source-of-truth, distinction, or source-locator columns; the glossary contains only `Term` and `Definition`, while source fidelity is checked from the review inputs.

Return `PASS` or `FAIL` with concrete findings and exact affected paths or Atom keys. Do not add another reviewer, audit, challenge, or source-wide completeness pass.

On `FAIL`, the writer corrects the findings once. Run structural validation on the corrected docs, then have the same reviewer check the original findings once against the corrected diff. New observations may be reported, but they do not open an automatic loop. If any material finding remains, stop and ask the user whether to accept, narrow, or revise the work. Run structural validation once more on the final reviewed docs before reporting completion.

The review is transient conversation evidence. Do not persist review metadata or state in the project.
