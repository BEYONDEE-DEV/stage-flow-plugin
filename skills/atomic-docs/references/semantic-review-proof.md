# Semantic Review Proof

## Contents

- [Responsibility](#responsibility)
- [Embedded Receipt](#embedded-receipt)
- [Receipt Binding](#receipt-binding)
- [Persistent Primary](#persistent-primary)
- [Blind Terminal Challenge](#blind-terminal-challenge)
- [Conditional Handoff](#conditional-handoff)
- [Retention And Boundary](#retention-and-boundary)

## Responsibility

This reference is the normative owner of v5 embedded review receipts, persistent-primary reviewer identity, the blind terminal challenge, and append-only primary handoff history. `reviewer-perspectives.md` owns reviewer selection and semantic verdict quality, `semantic-review-closure.md` owns PASS invalidation and resolution, `shared-contract-readiness.md` owns readiness and dispatch state, and `validation-contract.md` owns deterministic validation.

## Embedded Receipt

Embed one `receipt` in every `selection_readiness.reviews` PASS and every `semantic_review_closure.review_passes` PASS. Do not create a separate receipt or proof file. Use this exact shape:

```json
{
  "receipt": {
    "reviewer_agent_id": "agent-7",
    "review_run_id": "orders-development-run-2",
    "reviewer_role": "development",
    "scope": "orders-bundle",
    "basis_manifest": {
      "basis_revision": 2,
      "docs": [{"path": "docs/domains/orders/order-atom.md", "sha256": "<64-hex>"}],
      "source_revision": "<40-or-64-hex>",
      "source_locators": [{"locator": "src/orders.py:40", "content_sha256": "<64-hex>"}]
    },
    "basis_manifest_sha256": "<64-hex>",
    "validation_question": "검토할 계약과 실패 조건",
    "observed_result": "검토에서 직접 확인한 결과",
    "verdict": "PASS",
    "report_path": ".stageflow/atomic-docs/requests/<request-id>/reviews/orders-development-run-2.md",
    "report_sha256": "<64-hex>"
  }
}
```

Require every string to be non-empty and single-line. Keep `docs` and `source_locators` non-empty, unique by path/locator, and sorted before hashing: order `docs` by `path` and `source_locators` by `locator`, and reject duplicates. Resolve each docs path to the exact managed or request-local input reviewed. Resolve each source locator at `source_revision` and hash the cited content bytes, not the locator text. Use lowercase SHA-256.

Hash `basis_manifest` as UTF-8 JSON with sorted object keys, compact separators `,` and `:`, and direct non-ASCII code points (`ensure_ascii=false`). Do not include `basis_manifest_sha256` in its own digest. This digest binds the declared inputs; it does not replace path/hash validation.

## Receipt Binding

Make the containing record and receipt agree exactly on reviewer agent when present, reviewer role, scope, basis revision, and verdict. For the latest current readiness PASS, require role `development`, scope `selection-readiness`, and the current `persistent_agent_ids.reviewer`. A historical `stale|superseded` readiness review instead matches the persistent reviewer that was active at its basis according to ordered `reviewer_handoffs`; never compare it with today's current reviewer. For semantic PASS, require exact `PASS`; keep FAIL in the findings-only report and operation diagnostics until correction produces a new PASS.

Write each `review_run_id` once. Keep `report_path` project-root-relative, symlink-free at every lexical component, and normalized below `.stageflow/atomic-docs/requests/<active-request-id>/reviews/`; reject an absolute, escaping, or symlinked path. Point it to one immutable findings-only report owned by `reviewer-perspectives.md`, hash the complete report bytes, and retain that file. Never use a mutable aggregate report whose later append would invalidate an older receipt.

Record the actual validation question and observed result, not a generic checklist label. Every current receipt includes and hashes the configured docs root's project-root-relative `project/atomization-criteria.md` plus the managed/request inputs required by its scope. Require `source_revision` to match the operation's HEAD-reachable ancestor `source_commit_observed`. Resolve every source locator lexically from the repository tree at that revision; never follow a current-worktree symlink target. A trace-bound final receipt includes both owner and consumer Atoms, and its source locator set contains the trace authority and implementation locators with identical digests and source revision. For a current receipt, rehash declared docs from current bytes. For a historical `stale|superseded` receipt, validate the stored docs digest through its retained canonical manifest, immutable report, and source locators at `source_revision`; do not compare that historical docs digest with mutable current managed-doc bytes. A hash-only, source-free, unknown-report, stale-basis, or reviewer-ID-mismatched receipt cannot support current PASS.

## Persistent Primary

Keep `persistent_agent_ids.reviewer` as the current primary development reviewer and `persistent_agent_ids.writer` as a different agent once writing starts. Every readiness/development PASS uses the primary active at its own basis, including stale or superseded history. Reuse one separate risk agent across all risk PASS history; it differs from writer and every primary agent anywhere in handoff history. Integration/baseline reviewers differ from writer, their basis-active primary, and risk reviewer. Do not rotate the primary after a fixed bundle count.

After the fourth completed bundle, check whether the primary can still retain the selected owners, contract meanings, active basis, and unresolved findings before dispatching the next bundle. Continue with the same primary when it can. Handoff only under the conditions below.

## Blind Terminal Challenge

Create top-level `semantic_challenge` with exact `version: "1"` and append-only `attempts`. Each attempt has:

```text
challenge_id, basis_revision, mode, review_id, reviewer_agent_id,
primary_agent_id, excluded_inputs, verdict, receipt
```

Use `mode: reuse-final-review|dedicated`. Set `excluded_inputs` to exactly `primary-report`, `primary-verdict`, and `primary-evidence-summary`. Give the challenger current managed atoms, criteria, raw `inventory.md`, raw `evidence.md`, source revision, and relevant source locators; do not give it a prior primary report, verdict, answer sheet, diagnostic summary, or evidence summary. Require the receipt manifest to include project-root-relative inventory/evidence paths, every current managed Atom required by the terminal scope, and the relevant source locators. Do not hash `work-state.json` or invent a receipt-excluded state projection; structural validation separately proves the current closure state.

Use an agent different from writer, `primary_agent_id`, risk reviewer, all prior semantic reviewers, and every earlier challenge agent, with a fresh `review_run_id` and report. `primary_agent_id` equals the primary active at that attempt's basis. Exclude `work-state.json` as well as primary reports/verdict/summary from the manifest; structural validation owns state. A qualifying current integration/baseline review may use `reuse-final-review` when its agent, current-basis scope, input blindness, and receipt satisfy this contract; set `review_id` to that current semantic PASS and embed the same receipt. Otherwise run one `dedicated` challenge with receipt role `challenger` and scope `terminal-current-basis`. Record that dedicated run as a journal-projected `integration-review` span whose scope is `terminal-current-basis`, whose `span_id` equals the challenge `review_id`, and whose outcome equals the challenge verdict.

Run at most one challenge attempt for a basis revision and only after that basis is terminal-ready: every required development/risk review follows its successful bundle/writer attempt, all required reviews are current, invalidations are resolved, dispatch is ready, and final candidate admission is complete. In journal order, the challenge follows every current bundle review and the last bundle/writer correction. Final closure requires exactly one attempt at the current closure basis and exact `PASS`.

For the current attempt, compare receipt documents and required bundle reviews with the exact current queue, risk closure, and managed Atom set. For a retained historical attempt, validate its raw-input/Atom path shape, readiness, recorded review role/scope history, invalidation resolution, and journal chronology without applying later-added bundles or later managed-Atom paths backward. Workflow requires exact completeness while an attempt is current, but the mutable state does not retain a trusted complete past queue/risk snapshot or commit challenge state into the journal. Later structural validation therefore cannot reconstruct or prove a wholly omitted historical prerequisite; do not claim that stronger property.

Treat a material challenge FAIL as new semantic evidence. Preserve the attempt, increment the basis exactly once, open the affected invalidation, and hand off the primary with reason `challenger-material-fail`. The handoff and invalidation use the same affected bundles; every primary PASS named stale by the handoff appears in that invalidation, which resolves only after its required reruns. Then challenge the new terminal-ready basis once with another fresh agent. Never rerun a blind challenge on the same failed basis.

## Conditional Handoff

Create top-level `reviewer_handoffs` as exact `{"version":"1","history":[]}` before review work. Append this shape only when a handoff occurs:

```text
handoff_id, from_agent_id, to_agent_id, reason, basis_revision,
affected_bundle_ids, stale_review_ids[, context_check_review_id]
```

Use one reason: `context-saturation`, `agent-unavailable`, `basis-reset`, or `challenger-material-fail`. Require different non-empty agent IDs, a positive basis revision, and unique affected bundle/PASS IDs. At a handoff basis, `to_agent_id` becomes the basis-active primary until the next handoff; older reviews keep the reviewer active at their own basis. Set only the latest `to_agent_id` as the current `persistent_agent_ids.reviewer`.

Use `context-saturation` only after the post-fourth-bundle check shows the primary cannot retain the current basis. For this reason alone, require `context_check_review_id` naming a finished development PASS by `from_agent_id` on the fourth distinct completed queue item; four reviews of one item do not qualify. The replacement's first readiness/development action must start later in journal sequence than that anchor. Omit this field for every other reason. Use `basis-reset` only for a late or systemic change that invalidates the primary's cross-bundle context. Do not hand off for elapsed time, raw bundle count, routine bundle advance, or a local correctable finding.

Before handoff, stale only prior PASSes whose basis the replacement cannot safely inherit and open their required invalidations. Give the replacement accepted scope, current operation state, raw docs/source inputs, active findings, and affected history without presenting an old verdict as the answer. Rerun only affected readiness or bundle reviews.

## Retention And Boundary

Retain receipt-bearing records, their findings-only reports, `semantic_challenge`, and `reviewer_handoffs` below the request after terminal PASS. Keep append-only attempt and handoff identities through rollback comparison; never delete an old FAIL or handoff to make the final basis look clean.

Treat the receipt and hashes as input-binding and reviewer self-attestation. They can expose missing, changed, or mismatched declared inputs; they do not cryptographically prove semantic truth, reviewer independence, source access, or honest observation. Require semantic reviewers and the blind challenge to make those judgments.
