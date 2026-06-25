# Refresh Flow

## Responsibility

This reference defines full refresh and targeted docs operations against source code and existing atomic docs.

## Source Baseline

Freshness is tracked with one source-code commit hash stored in metadata at the documentation submodule root. The baseline metadata is outside individual `atomic.md` files.

The baseline records the last source-code commit hash used for a confirmed docs refresh. The docs skill should compare `git diff <stored-source-hash>..HEAD` or the equivalent source-root diff to prioritize changed source behavior files.

## Full Refresh

A full refresh is a first-class operation when the user explicitly asks for it.

1. Read the configured docs root and source root.
2. Read the docs-root source commit baseline metadata.
3. Inspect changed source behavior files since the stored source commit hash.
4. Ignore tests, settings, schema, build, and auxiliary files by default unless the user requested auxiliary-file reflection.
5. Use source-to-atomic seed discovery to find likely domain and atomic candidates.
6. Expand affected scope through atomic graph traversal.
7. Stop graph expansion when related atomic docs no longer create modification candidates.
8. Present a domain-grouped change plan before writing docs.
9. Write confirmed updates only after the change plan is accepted.
10. Update the docs-root source commit baseline metadata after confirmed writes.

## Targeted Docs Operation

Targeted domain or atomic work is also a first-class flow. When targeted work overlaps with full-refresh scope, prioritize the current user-requested target. Put adjacent affected scope in follow-up proposals or `Gaps`.

## Change Plan Requirements

A change plan should group by domain and list:

- source behavior files inspected
- affected atomic targets
- affected `atomic.md` sections
- inferred `Intent` or `Rules` that require confirmation
- `Current Implementation` changes
- `Planned Changes` reconciliation candidates
- `Gaps`, bug candidates, uncertain mappings, rename/merge proposals, and implemented-plan candidates
- graph path corrections or target-key conflicts

## Inference And Gaps

The skill may draft `Current Implementation`, `Gaps`, and inferred `Intent` or `Rules` from code. Inferred `Intent` and `Rules` remain inferred until confirmed by the user. If observed code conflicts with confirmed intent or rules, do not resolve the conflict silently; preserve it as a gap or bug candidate.
