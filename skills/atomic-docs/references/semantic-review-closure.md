# Semantic Review Closure

## Contents

- [Responsibility](#responsibility)
- [Forward-Only State](#forward-only-state)
- [Opening An Invalidation](#opening-an-invalidation)
- [Correction And Resolution](#correction-and-resolution)
- [Final Gate](#final-gate)

## Responsibility

This reference is the normative owner of forward-only semantic review invalidation state, its transition order, and the request-bound final closure gate. `reviewer-perspectives.md` decides which semantic reviews are required and whether their findings PASS. `docs-generation-flow.md` invokes the transition around writes, removals, merges, and owner changes. `validation-contract.md` defines only deterministic validation of the recorded state.

## Forward-Only State

New Atomic Docs operations use `context_selection.version: "4"`; existing version-3 and version-2 operations keep this same closure contract. All three add `semantic_review_closure` to `work-state.json` after Goal handoff and before candidate writing. Versions 4 and 3 use the sibling metrics contract from `operation-metrics.md`; version 4 additionally uses `shared-contract-readiness.md`. Existing version-1 or unversioned operations continue without migration and cannot claim this closure guarantee.

Use this version-1 shape:

```json
{
  "semantic_review_closure": {
    "version": "1",
    "basis_revision": 2,
    "review_passes": [
      {
        "review_id": "fulfillment-development-1",
        "reviewer_role": "development",
        "scope": "fulfillment",
        "basis_revision": 1,
        "verdict": "PASS",
        "status": "superseded"
      },
      {
        "review_id": "fulfillment-development-2",
        "reviewer_role": "development",
        "scope": "fulfillment",
        "basis_revision": 2,
        "verdict": "PASS",
        "status": "current"
      },
      {
        "review_id": "affected-integration-2",
        "reviewer_role": "integration",
        "scope": "affected-closure",
        "basis_revision": 2,
        "verdict": "PASS",
        "status": "current"
      }
    ],
    "invalidations": [
      {
        "invalidation_id": "fulfillment-drop-1",
        "trigger": "candidate-disposition",
        "cause": "후보가 write에서 drop으로 바뀌어 기존 소유권 설명이 오래됐다.",
        "opened_revision": 2,
        "affected_artifacts": [
          {"location": "managed-docs", "path": "project/project-glossary.md"},
          {"location": "request", "path": "inventory.md"}
        ],
        "affected_bundles": ["fulfillment"],
        "stale_review_ids": ["fulfillment-development-1"],
        "required_reviews": [
          {"reviewer_role": "development", "scope": "fulfillment"},
          {"reviewer_role": "integration", "scope": "affected-closure"}
        ],
        "status": "resolved",
        "resolved_revision": 2
      }
    ],
    "final_gate": {
      "required": true,
      "review_history": ["affected-integration-2"],
      "review_id": "affected-integration-2"
    }
  }
}
```

`basis_revision` is a positive operation-local integer, not a source commit or global document version. Increment it only when a post-PASS meaning or review basis changes. Review roles are `development`, `risk`, `integration`, or `baseline`. Review status is `current`, `stale`, or `superseded`; verdict is exact `PASS` because FAIL findings remain in the ordinary review result until corrected.

For version 4, bundle-scoped development/risk review PASSes and `required_reviews.scope` use stable `bundle_id`, and invalidation `affected_bundles` records those same IDs. Historical scopes and affected IDs resolve through active bundles plus immutable `selection_retirements.retired_bundles`; active routing still resolves active bundles only. Integration/baseline scopes keep their controlled values. Version 3 and version 2 retain domain-scoped development/risk reviews and affected bundles.

For every version-4 invalidation, including late-discovery and general-correction invalidations, each `stale_review_ids` entry that names a development or risk PASS requires its exact `(reviewer_role, stable bundle_id scope)` pair in `required_reviews`. This rule follows the PASS that actually became stale, not merely an affected bundle: a current risk PASS left out of `stale_review_ids` adds no risk pair and remains reusable only under the independently confirmed risk-neutral flow below. Version 3 and version 2 keep their recorded domain-scoped invalidation behavior.

Review PASS and invalidation records are append-only history. Keep each ID and its opening identity; a PASS status moves `current → stale → superseded`, and an open invalidation may only expand or become resolved. A later rollback comparison may observe `current → superseded` only when the retained resolved invalidation proves the stale-and-resolution sequence. Never delete or replace an older record to make current state appear closed. Once an invalidation is resolved, leave it unchanged; a later affected correction opens a new invalidation and preserves the resolved one.

Artifact locations are `managed-docs` for paths below the configured docs root and `request` for paths below the active Atomic Docs request. Do not include `work-state.json` itself. `final_gate.required` follows `reviewer-perspectives.md`. `review_history` is append-only and records every review assigned to the final gate; `review_id` points to its latest current entry. When invalidating that result, clear only `review_id`, retain history, and stale the latest history PASS. A local operation with no integration/final reviewer records `{"required": false, "review_history": []}`. A project-wide baseline always records `required: true` and points to the current `baseline`/`project-wide` PASS at the latest basis revision.

## Opening An Invalidation

Open an invalidation before changing a meaning that already contributed to a PASS. A version-4 late discovery after readiness but before any affected bundle semantic PASS has nothing to invalidate and records `semantic_invalidation_ids: []`; once an affected PASS exists, invalidation is mandatory before correction. Triggers are `candidate-disposition`, `atom-merge`, `ownership`, `glossary-source`, `shared-decision-owner`, `graph-relationship`, or `documented-meaning`.

1. Increment `basis_revision` once for the correction set.
2. Record the cause, every known affected managed/request artifact, active-or-retired stable bundle ID for version 4 or domain for older versions, and every required review pair; for version 4, derive the exact development/risk pair from each PASS made stale.
3. Change only affected `current` review passes to `stale` and list their IDs in `stale_review_ids`. Do not stale unrelated bundle PASSes.
4. If an affected final PASS exists, stale it, list it in `stale_review_ids`, clear `final_gate.review_id`, and retain `review_history`; keep whether the gate is required.
5. Then edit, remove, merge, or reroute the affected artifacts.

If another cause is found while an open invalidation already owns any PASS that must become stale, expand that open invalidation before editing: append the cause, affected artifacts/bundles, stale review IDs, and required review pairs, and advance the basis once for the enlarged correction set. Do not create overlapping invalidations that name the same stale PASS. Keep the original `trigger` as the opening trigger; disjoint corrections that share no stale PASS may use separate invalidations. For version-4 rollback guards, derive affected bundle IDs from the pre-mutation path→artifact/action `atom_key`→queue `bundle_id` mapping, never from domain; stale current development and risk PASSes for that ID, while same-domain shards with different IDs stay current. An approved-existing source key absent from the queue gets no inferred bundle invalidation and retains only existing final-gate protection.

A current-operation Atom drop remains automatic, and an exact approved existing-Atom action keeps its prior authorization. If a version-4 drop retires its bundle or shared contract, append the prior identity to `selection_retirements` before removing active state so this closure remains resolvable. Before the mutation snapshot, every prior development/risk PASS for the newly retired stable bundle scope must appear `stale`; an open invalidation lists the exact bundle and PASS IDs, includes each stale PASS's exact reviewer-role/bundle-scope pair in `required_reviews`, and has `opened_revision` equal to `retired_basis_revision`. Resolution therefore requires the matching rerun. Retirement necessarily changes that stable scope's identity, route, or dependency basis, so every pre-retirement risk PASS in the scope is stale; risk-neutral reuse remains available only outside the retirement-affected scope or for a non-retirement correction whose risk basis is independently unchanged. Apply the same rule separately to every still-live contract owner/consumer stable bundle when its contract retires. No prior semantic PASS means no retirement invalidation, a scope retired earlier is excluded, and a bundle plus related contract retired in one correction use the same basis. On every later version-4 selection, recheck all retirement revisions: every pre-retirement PASS not already superseded by an earlier-resolved invalidation retains its retirement-revision invalidation and exact required pair, regardless of current status; corrected-basis PASSes and contract scopes retired earlier are excluded. Remove only a route/dependency that directly references the retired contract; participant-local and other-contract risk routes remain unchanged. The invalidation is review bookkeeping, not another approval request. If correction discovers a new domain, unapproved protected action, hash/provenance conflict, migration, external action, or user-only decision, follow the separate authorization boundary instead of using this state to expand scope.

## Correction And Resolution

Run selection and structural preflight after the correction. Derive `required_reviews` from the meaning and evidence impact table in `reviewer-perspectives.md`, not from the correction label alone. Reuse a risk PASS only after development review confirms every recorded risk trigger, risky contract meaning, owner/route, adverse behavior, and evidence basis stayed unchanged; uncertainty requires risk review. Record each required PASS with a unique `review_id`, exact role/scope, and current `basis_revision`.

When risk impact cannot be known before inspecting the corrected result, open the invalidation before editing with development review required and leave the prior risk PASS `current`. The open invalidation prevents that risk PASS from authorizing resolution or final completion by itself. If development review confirms every risk dimension stayed unchanged, record its PASS and reuse the risk PASS. If it finds a change or uncertainty, do not record a corrected-basis development PASS: advance the basis, expand the still-open invalidation to stale the risk PASS and require risk review, then rerun development and risk at that basis. This is the only post-edit expansion path; it is valid because the invalidation never closed and no corrected-basis PASS was recorded before expansion.

Resolve an invalidation only when every required pair has a `current` PASS at its `resolved_revision`, the affected inventory/owner/graph routes agree with the managed docs, and no correction finding remains. Set `resolved_revision` to the current `basis_revision`, change its listed old PASSes from `stale` to `superseded`, and set status to `resolved`. A later current PASS for the same pair may have a newer basis. An open invalidation has no `resolved_revision` and its listed prior PASSes remain `stale`.

When one correction affects an earlier shared owner, include that owner bundle ID and only consumer bundle IDs whose recorded basis changed. For version-4 late discovery, `shared-contract-readiness.md` owns the discovery/pause record and this closure owns only post-PASS staleness: use no invalidation before an affected semantic PASS, otherwise use the applicable ownership/shared-decision trigger and leave unrelated bundle PASSes current. Retired bundle/contract IDs keep historical reviews, invalidations, diagnostics, and discoveries interpretable but never become active routes. When a later unrelated correction increments the operation revision, an already resolved invalidation remains valid. If a later change affects its artifacts, owner/consumer basis, or required review result, open a new invalidation rather than rewriting the resolved record.

## Final Gate

Before request-bound unscoped docs validation or baseline validation:

- rerun final candidate admission for the operation's selected or affected candidates; do not retain dormant/unreachable behavior merely because it is risky or implemented
- ensure every invalidation is `resolved`, no review PASS remains `stale`, and each required review has a current PASS at or after the recorded resolved revision
- when `final_gate.required` is true, record a current integration/baseline PASS at the latest `basis_revision`
- retain request inventory/evidence, then run the validator with the request ID for final selection plus request-bound docs/baseline and terminal checks so version-4 routing, immutable retirement history, current readiness, ready dispatch, and this closure are checked together

The final reviewer independently compares the current managed docs and operation inventory under `reviewer-perspectives.md`. This state proves only that the required current-basis reviews were recorded and no known invalidation was left open; it does not prove that owner, Gap, candidate, or natural-language judgments are semantically correct.
