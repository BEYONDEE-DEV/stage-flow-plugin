# Validation Contract

## Contents

- [Responsibility](#responsibility)
- [Validator Location And CLI](#validator-location-and-cli)
- [Selection State Shape](#selection-state-shape)
- [Removal And Merge State](#removal-and-merge-state)
- [Semantic Review Closure Checks](#semantic-review-closure-checks)
- [Phase Checks](#phase-checks)
- [Validation Boundary](#validation-boundary)

## Responsibility

This reference defines the plugin-bundled structural validator. Structural validation catches deterministic format and relationship errors; semantic quality remains the responsibility of criteria, readiness, domain, and final reviewers. `shared-contract-readiness.md` owns the detailed version-4 state, retirement identity, rollback scope, and dispatch-cutoff contract consumed here.

## Validator Location And CLI

Run the validator from the installed or source plugin root:

```text
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase bootstrap
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id> --require-actions-final
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase baseline --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase metrics-preterminal --request-id <request-id>
python <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase metrics-final --request-id <request-id>
```

Never search for or invoke `scripts/validate_atomic_docs.py` relative to the target project. The target project contains atomic-docs config and output, not the plugin validator.

The validator is read-only. It exits `0` with `PASS <phase>` and exits `1` with `FAIL <phase>` plus actionable findings. Docs/baseline PASS output includes validated atom and AID totals; it does not create an active/retired AID lifecycle.

Run selection phase after candidate evidence anchors and `write|merge|drop` decisions are recorded and, for version 4, after readiness review state is recorded, but before creating the writer. `--request-id` is required for selection and optional for docs/baseline. Intermediate removal/retry checks omit `--require-actions-final`; final version-4 selection includes it. Run docs after every writer and before semantic review, repeating `--expect-atom-key` for that bundle so unrelated pre-existing defects do not block the bundle. Final request-bound docs/baseline and both metrics terminal phases rerun full current version-4 selection/routing/readiness/dispatch/retirement history while inventory/evidence still exist. `--expect-atom-key` is valid only for docs.

## Selection State Shape

New operations use version 4. It retains version-3 candidate/closure/metrics behavior and adds the routing, shared-contract, readiness, late-discovery, diagnostic, dispatch, and mandatory `selection_retirements` fields owned by `shared-contract-readiness.md`. Initialize that owner as exact `{"version":"1","retired_bundles":[],"retired_contracts":[]}`. The version-3 shape below remains a valid legacy illustration; version 3 and older operations are not migrated.

```json
{
  "accepted_scope": ["domain/path"],
  "source_commit_observed": "<40-or-64-character-git-hash>",
  "context_selection": {
    "version": "3",
    "candidates": [
      {
        "candidate_id": "domain-context",
        "domain": "domain/path",
        "candidate": "도메인 맥락",
        "disposition": "write",
        "selection_basis": "변경 전에 소유 경계를 알아야 한다.",
        "candidate_atom_keys": ["domain-context"]
      }
    ]
  },
  "bundle_queue": [
    {"domain": "domain/path", "expected_atom_keys": ["domain-context"]}
  ],
  "risk_triggers": [
    {
      "candidate_id": "domain-context",
      "atom_key": "domain-context",
      "triggers": ["shared policy contract"],
      "basis": "선택된 공유 계약이 변경 영향에 중요하다."
    }
  ],
  "semantic_review_closure": {
    "version": "1",
    "basis_revision": 1,
    "review_passes": [],
    "invalidations": [],
    "final_gate": {"required": false, "review_history": []}
  }
}
```

A `merge` candidate replaces `candidate_atom_keys` with `merge_target_atom_key`; a `drop` candidate has neither. Candidate IDs are unique within the operation. More than one candidate contract may route risk to the same Atom key.

Use this compact evidence projection beside state:

```text
source_commit_observed: `<hash>`

## <candidate_id>
- `<source locator>` why this location matters to selection
```

The source revision and every candidate section must be present. The validator checks only this shape, locator presence, and references; reviewers judge locator authority, relevance, and selection quality.

## Removal And Merge State

These fields are optional for compatibility. Their absence keeps an existing operation structurally valid but grants no automatic removal/merge authority.

`operation_created_artifacts` contains one record per output created by this operation: `candidate_id`, `atom_key`, managed-docs-relative `path`, `created_attempt_id`, lowercase 64-hex `last_operation_sha256`, and `status: present|removal_pending|removed`. The path must stay below its accepted candidate domain and be absent from the fixed managed-docs revision corresponding to `source_commit_observed` plus the current HEAD/index. For submodule storage, resolve the gitlink commit recorded at `source_commit_observed`; a path present there is pre-existing even if later HEAD removes it. `present` requires the path and hash to match. Before deletion, `removal_pending` adds artifact `rollback_path`, `state_rollback_path`, and `state_rollback_sha256`; it accepts either the unchanged managed path or its expected absence for crash-safe resume. `removed` requires managed-path absence. Both removal states retain rollback files through operation close, require candidate `drop` plus a backticked candidate ID in inventory, and forbid selected routes or incoming graph edges using the key.

`approved_existing_actions` is immutable. Each record has `action_id`, `action: delete|merge`, `source`, optional merge `target`, `reference_owners`, and `approved_action_fingerprint`. Every member has `atom_key`, managed-docs-relative `path`, and `preimage_sha256`; member paths are unique and stay below accepted domain paths. A delete omits `target`, while a merge requires it. Existing-action members and `operation_created_artifacts` must have disjoint paths and keys, so neither provenance contract can impersonate the other. Fingerprint the record without `approved_action_fingerprint`: sort `reference_owners` by path, serialize UTF-8 JSON with sorted keys and separators `,` and `:`, then SHA-256 the bytes.

`action_execution` has exactly one record per approved action: matching `action_id` and fingerprint, `status: approved|applying|rolling_back|applied`, and one runtime member for every immutable member. Each member repeats `role: source|target|reference_owner`, `atom_key`, and `path`, then records `expected_state: present|absent`; present requires `last_operation_sha256`, absent forbids it. Every non-`approved` state retains each member `rollback_path` plus `state_rollback_path` and `state_rollback_sha256`. The complete state snapshot must retain core scope/revision/selection/queue/risk fields, exactly match every unrelated top-level owner's key presence and value, keep unique candidate/artifact/action identities and unchanged artifact provenance/action manifests/execution members, provide a restorable versioned routing contract, and obey the same status-specific allowed/forbidden keys for the pre-mutation `present` artifact or `approved` execution; a forbidden key is invalid even when its JSON value is `null`, and current-created snapshots also match `created_attempt_id`. A version-4, version-3, or version-2 snapshot preserves structurally valid pre-mutation closure at the same contract version and no later basis revision; versions 4 and 3 also preserve append-only operation metrics, while version 4 preserves readiness/dispatch plus immutable `selection_retirements`. Each newly retired current row uses a basis strictly above snapshot readiness and no later than current readiness, exactly matches one snapshot-active bundle/contract excluding retirement metadata, and removes it from current active state. Every prior development/risk PASS for a newly retired bundle's stable scope, and for each still-live owner/consumer stable scope of a newly retired contract, must become stale in the snapshot. The snapshot contains an open invalidation listing every exact bundle/PASS ID, the exact `(reviewer_role, bundle scope)` pair in `required_reviews`, and `opened_revision == retired_basis_revision`. Retirement changes the affected identity/route/dependency basis, so a current pre-retirement risk PASS in that scope is not risk-neutral or reusable; reuse remains valid only outside the retirement-affected scope or for a non-retirement correction with independently unchanged risk basis. No prior PASS needs no invalidation, a contract scope retired earlier is excluded, and one correction uses one retirement basis. Independently on every current version-4 selection, every pre-retirement PASS not corrected at/after `T` or already superseded by an invalidation resolved before `T` must retain an open/resolved invalidation opened at `T` with the same exact bundle, stale ID, and required pair; status alone cannot bypass this check, and contract scopes retired before `T` are excluded. Normalization may remove only dependencies/shared routes that directly name that retired contract and must preserve participant-local or other-contract routes. For a version-4 guarded path, resolve its snapshot action/artifact `atom_key` to the exact snapshot queue `bundle_id`; current development and risk PASSes with that scope are bundle pre-mutation targets, while another same-domain shard and unrelated risk PASSes remain current. If an approved-existing source key is absent from the snapshot queue, infer no bundle and retain only the existing final-gate guard. Version 3 and version 2 retain domain lookup. When a guarded path has a current affected PASS or final-gate PASS, the snapshot must already contain the open invalidation affecting that path and the stale prior PASS. A later resolved invalidation cannot retroactively authorize the mutation. Review PASS and invalidation records from the snapshot remain in current state; open records may expand only at a newer basis or resolve, while resolved records cannot be rewritten. Ordinary correction may make current closure progress beyond a valid open snapshot. Every member rollback matches its preimage. Runtime membership never expands the approved manifest.

At `approved`, every member is present at its preimage hash. Every later present/absent expectation must match disk. At `applied`, delete requires source absence and every reference owner at its postimage; merge additionally requires the approved target identity and postimage. Both require no selected route or graph edge to the removed source. A mismatch, recreated source, unapproved incoming owner, bad rollback copy/snapshot, changed fingerprint, or accepted-scope violation is structural FAIL; the validator never repairs it. Only `--require-actions-final` requires every current-operation removal to be `removed` and every existing action to be `applied`.

## Semantic Review Closure Checks

Selection versions 4, 3, and 2 require `semantic_review_closure`; version 1 must omit it. Versions 4 and 3 additionally require metrics; version 4 also requires readiness and stable bundle IDs for development/risk scopes and `affected_bundles`. Historical closure/diagnostic/discovery references may resolve active plus retired IDs, while current routing/dependencies resolve active IDs only; older versions retain domain scopes. Validate closure shape/transitions, IDs, roles/status/triggers, revisions, artifact paths, affected scope, stale references, required review pairs, and status-specific fields. In every version-4 invalidation, each stale development/risk PASS ID requires the exact `(reviewer_role, stable bundle_id scope)` entry in `required_reviews`, including late-discovery and general-correction invalidations. A current risk PASS not listed stale adds no pair and keeps the separately confirmed risk-neutral reuse path. Versions 3 and 2 retain their legacy domain-scoped rule.

An open invalidation references `stale` prior PASSes and omits `resolved_revision`; a resolved one references `superseded` PASSes and current required PASSes at or after resolution. The same stale PASS cannot overlap invalidations. A post-readiness v4 discovery before any affected semantic PASS may use exact empty `semantic_invalidation_ids`; after such a PASS it must link invalidation. The request-bound final selection/docs/baseline check rejects open invalidations and remaining `stale` PASSes, and baseline requires the current `baseline`/`project-wide` PASS.

The closure is forward-only through selection versions 4, 3, and 2. Existing version-1 or unversioned operations remain compatible and gain no closure guarantee. The validator does not infer creation time or migrate old state.

## Phase Checks

`bootstrap` checks:

- `.stageflow/atomic-docs.json` exists, is valid JSON, and has no duplicate object keys
- required config keys exist
- `storage_mode` is `repository` or `submodule`
- `docs_root`, `source_root`, and `baseline_metadata_path` are relative paths that do not escape their configured roots
- the managed docs root and `project/atomization-criteria.md` exist

`selection` includes bootstrap checks and reads the explicit operation request under `.stageflow/atomic-docs/requests/<request-id>/`:

- `inventory.md`, `evidence.md`, and `work-state.json` exist
- selection version 1, 2, 3, or 4, a reachable `source_commit_observed`, non-empty accepted scope, and candidate/evidence structures are well formed without duplicate JSON keys
- every candidate has a unique ID, exact accepted domain path, `write|merge|drop`, non-empty selection basis, and a locator/relevance evidence section
- evidence revision, candidate headings, and locator rows use constrained plain Markdown: no tab characters, fenced or indented code (including inside blockquote or list containers), multiline inline code, or raw HTML-like syntax
- `write` owns valid planned Atom keys, `merge` resolves to a `write` key, and `drop` creates no key
- bundle expected keys equal the `write` keys and stay under each key owner's approved domain
- every risk trigger resolves its candidate and output/merge target, names at least one trigger, and has a non-empty selected-contract basis
- version 4 checks local/shared active routes, bounded contract/queue references, mandatory append-only retirement identity/history and direct-only route/dependency normalization, stable bundle review/invalidation scopes, readiness and dispatch state, post-readiness immutable RFC3339 `paused_at`, `pause_after_span_id` ordering with cutoff `finished_at <= paused_at`, timestamp-resistant pause windows, conditional late-discovery invalidation links, and unchanged shared-root resume at a strictly higher basis; every development/risk metric span, including a first-attempt `FAIL` referenced by `semantic_fail_diagnostics`, uses an active-or-retired stable bundle scope, except that only development may use `selection-readiness`; version 3 retains domain scope
- optional operation-created and approved-existing-action state satisfies the removal/merge contract, including accepted scope, exclusive source provenance, current hashes, immutable membership, runtime progress, member/state rollback copies, exact version-4 guarded-path-to-bundle mapping, source/target identity, retained drop inventory, selected-route closure, and incoming graph closure
- versions 4, 3, and 2 have mandatory forward-only semantic review closure; versions 4 and 3 also have mandatory operation metrics, while version 1 omits both

Selection validation is the request-bound structural postcondition when a valid drop/delete leaves no managed Atom. If managed Atoms remain after an applied action, run unscoped docs validation too.

Selection validation applies to versions 1 through 4; new operations use version 4, while v3 keeps metrics/closure, v2 closure, and v1 selection. For compatibility, an unversioned active request continues without selection validation, and scope expansion still follows its normal approval and Goal boundary. Final v4 selection uses `--require-actions-final`; request-bound final docs/baseline, preterminal, and final metrics each rerun current routing/readiness/ready-dispatch, metric cutoff, and retirement-history gates. Keep inventory/evidence until terminal PASS. Older versions retain their prior final checks, and baseline profile/final PASS still requires baseline phase.

`docs` includes bootstrap checks. Without `--expect-atom-key`, it checks every `*-atom.md` under the managed docs root. With expected keys, it strictly checks those atoms and their references into the global identity/AID/graph index:

- frontmatter is valid standard YAML with no duplicate mapping keys and contains one lower-kebab-case `atom_key`
- `atom_key` values are globally unique
- required atom sections exist exactly once: `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- every discovered AID has valid `[AID:<key>.<section-code>.<NNN>]` shape and is globally unique
- an AID's section code matches the required section containing it
- a preserved AID may retain a historical key prefix after its meaning moves to another atom
- every graph edge has `type`, `target_key`, `target_path`, and `reason`
- `target_key` resolves to exactly one atom and `target_path` resolves to that same atom
- every `--expect-atom-key` resolves to a real atom

`baseline` includes docs checks and requires valid baseline metadata at the configured path:

```json
{
  "version": "1",
  "source_commit": "<40-or-64-character-git-hash>",
  "coverage": "project-wide"
}
```

The baseline commit must resolve in the configured `source_root`. `coverage` values for domains, features, atoms, targeted work, or partial scope are invalid.

When docs runs without `--expect-atom-key` and with `--request-id`, or baseline runs with `--request-id`, the validator also requires final semantic review closure. Legacy unscoped validation without a request ID retains its previous structural behavior.

## Validation Boundary

The validator must not decide:

- whether a domain boundary is meaningful
- whether source exploration found the useful context candidates
- whether a candidate's `write|merge|drop` selection or stated basis is semantically correct
- whether an evidence index is concise enough or a source detail has durable value
- whether a selected candidate semantically requires a risk trigger; the development-quality reviewer checks completeness even when the trigger list is empty
- whether a risk concern is truly local/shared, every real direct consumer was found, the chosen owner/evidence is authoritative, or two FAILs share one root cause
- whether natural-language implementation context is accurate or useful
- whether an important owner, shared/external contract, or non-obvious constraint is missing
- whether an Atomic Impl/compliance requirement is complete enough for its approved implementation scope
- whether user intent or a judgment label is correct
- whether a global baseline is semantically authorized by reviewer PASS results
- whether a recorded semantic invalidation found every affected artifact, bundle, or required reviewer
- whether a correction is risk-neutral or a measured span/rerun was necessary or efficient
- whether the final integration/baseline reviewer actually reconciled glossary, context, inventory, graph, root Gap ownership, and candidate economy correctly
- whether a delete/merge action was actually approved by the user; the validator checks only the recorded immutable fingerprint and runtime state

Those decisions remain reviewer-owned. A structural PASS never replaces required subagent review.
