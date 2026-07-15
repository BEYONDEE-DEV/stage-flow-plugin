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

Every Atomic Docs operation created under this contract uses `context_selection.version: "2"` and adds `semantic_review_closure` to `work-state.json` after Goal handoff and before candidate writing. Existing version-1 or unversioned operations continue their recorded flow without migration and cannot claim this contract's structural guarantee. Version 1 must not be retrofitted with the field merely to claim the new guarantee.

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

Review PASS and invalidation records are append-only history. Keep each ID and its opening identity; a PASS status moves `current → stale → superseded`, and an open invalidation may only expand or become resolved. A later rollback comparison may observe `current → superseded` only when the retained resolved invalidation proves the stale-and-resolution sequence. Never delete or replace an older record to make current state appear closed. Once an invalidation is resolved, leave it unchanged; a later affected correction opens a new invalidation and preserves the resolved one.

Artifact locations are `managed-docs` for paths below the configured docs root and `request` for paths below the active Atomic Docs request. Do not include `work-state.json` itself. `final_gate.required` follows `reviewer-perspectives.md`. `review_history` is append-only and records every review assigned to the final gate; `review_id` points to its latest current entry. When invalidating that result, clear only `review_id`, retain history, and stale the latest history PASS. A local operation with no integration/final reviewer records `{"required": false, "review_history": []}`. A project-wide baseline always records `required: true` and points to the current `baseline`/`project-wide` PASS at the latest basis revision.

## Opening An Invalidation

Open an invalidation before changing a meaning that already contributed to a PASS. Triggers are `candidate-disposition`, `atom-merge`, `ownership`, `glossary-source`, `shared-decision-owner`, `graph-relationship`, or `documented-meaning`.

1. Increment `basis_revision` once for the correction set.
2. Record the cause, every known affected managed/request artifact, affected bundle, and required review pair.
3. Change only affected `current` review passes to `stale` and list their IDs in `stale_review_ids`. Do not stale unrelated bundle PASSes.
4. If an affected final PASS exists, stale it, list it in `stale_review_ids`, clear `final_gate.review_id`, and retain `review_history`; keep whether the gate is required.
5. Then edit, remove, merge, or reroute the affected artifacts.

If another cause is found while an open invalidation already owns any PASS that must become stale, expand that open invalidation before editing: append the cause, affected artifacts/bundles, stale review IDs, and required review pairs, and advance the basis once for the enlarged correction set. Do not create overlapping invalidations that name the same stale PASS. Keep the original `trigger` as the opening trigger; disjoint corrections that share no stale PASS may use separate invalidations.

A current-operation Atom drop remains automatic, and an exact approved existing-Atom action keeps its prior authorization. The invalidation is review bookkeeping, not another approval request. If correction discovers a new domain, unapproved protected action, hash/provenance conflict, migration, external action, or user-only decision, follow the separate authorization boundary instead of using this state to expand scope.

## Correction And Resolution

Run selection and structural preflight after the correction. Then run only the review pairs in `required_reviews` plus any newly triggered risk or integration review. Record each PASS with a unique `review_id`, the exact reviewer role and scope, and the current `basis_revision`.

Resolve an invalidation only when every required pair has a `current` PASS at its `resolved_revision`, the affected inventory/owner/graph routes agree with the managed docs, and no correction finding remains. Set `resolved_revision` to the current `basis_revision`, change its listed old PASSes from `stale` to `superseded`, and set status to `resolved`. A later current PASS for the same pair may have a newer basis. An open invalidation has no `resolved_revision` and its listed prior PASSes remain `stale`.

When one correction affects an earlier shared owner, include that owner bundle and only consumers whose recorded basis changed. When a later unrelated correction increments the operation revision, an already resolved invalidation remains valid. If a later change affects its artifacts, owner/consumer basis, or required review result, open a new invalidation rather than rewriting the resolved record.

## Final Gate

Before request-bound unscoped docs validation or baseline validation:

- rerun final candidate admission for the operation's selected or affected candidates; do not retain dormant/unreachable behavior merely because it is risky or implemented
- ensure every invalidation is `resolved`, no review PASS remains `stale`, and each required review has a current PASS at or after the recorded resolved revision
- when `final_gate.required` is true, record a current integration/baseline PASS at the latest `basis_revision`
- run the validator with the request ID so it can check this state

The final reviewer independently compares the current managed docs and operation inventory under `reviewer-perspectives.md`. This state proves only that the required current-basis reviews were recorded and no known invalidation was left open; it does not prove that owner, Gap, candidate, or natural-language judgments are semantically correct.
