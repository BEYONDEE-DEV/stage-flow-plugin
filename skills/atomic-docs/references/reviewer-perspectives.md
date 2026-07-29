# Reviewer Perspective

Assign one independent semantic reviewer after the complete managed-docs diff is ready. Give the reviewer:

- the requested update scope
- the complete managed-docs diff
- the changed or selected source files
- exact auxiliary source content at the configured revision when used
- validator output

The reviewer answers only:

1. Are the docs useful enough to guide development without copying source mechanics?
2. Are material claims faithful to inspected source within the selected scope?
3. Are `Boundaries`, responsibilities, exclusions, handoffs, and contracts clear?
4. Do `depends_on`, source locators, and active RIDs express the selected change consistently?

Return `PASS` or `FAIL` with concrete findings and exact affected paths or Atom keys. Do not add another reviewer, audit, challenge, or source-wide completeness pass.

On `FAIL`, the writer corrects the findings once. Run structural validation on the corrected docs, then have the same reviewer check the original findings once against the corrected diff. New observations may be reported, but they do not open an automatic loop. If any material finding remains, stop and ask the user whether to accept, narrow, or revise the work. Run structural validation once more on the final reviewed docs before reporting completion.

The review is transient conversation evidence. Do not persist review metadata or state in the project.
