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

This reference defines the plugin-bundled structural validator. Structural validation catches deterministic format and relationship errors; semantic quality remains the responsibility of criteria, readiness, domain, and final reviewers. `shared-contract-readiness.md` owns detailed v5 routing/traces/retirement/dispatch, `semantic-review-proof.md` owns receipts/challenge/handoff, `atom-format-and-judgment.md` owns AID semantics, and `operation-metrics.md` owns the event journal consumed here.

## Validator Location And CLI

Run the validator from the installed or source plugin root:

```text
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase bootstrap
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id>
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase selection --request-id <request-id> --require-actions-final
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --expect-atom-key <key> [--expect-atom-key <key> ...]
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase docs --request-id <request-id>
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase baseline --request-id <request-id>
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase metrics-preterminal --request-id <request-id>
python3 <plugin-root>/scripts/validate_atomic_docs.py --root <target-project-root> --phase metrics-final --request-id <request-id>
```

Never search for or invoke `scripts/validate_atomic_docs.py` relative to the target project. The target project contains atomic-docs config and output, not the plugin validator.

The validator is read-only. It exits `0` with output beginning exact `PASS <phase>` and exits `1` with `FAIL <phase>` plus actionable findings. Add `[STRUCTURAL]` after the compatible PASS prefix so humans cannot confuse it with semantic review; preserve phase, exit code, and machine verdict. Do not print AID totals in an ordinary PASS; the existing atom total may remain. Keep semantic reviewers' controlled exact `PASS` token unchanged.

Run selection after candidate evidence anchors, `write|merge|drop`, binding traces, and receipt-bound readiness are recorded but before writer creation. At this pre-writer and other nonfinal intermediate gate, a trace may bind the current same-basis readiness PASS. `--request-id` is required for selection and optional for docs/baseline. Intermediate removal/retry checks omit `--require-actions-final`; final selection includes it and requires every trace to bind a current receipt-bound semantic-closure PASS. Run docs after every writer and before semantic review, repeating `--expect-atom-key` so unrelated pre-existing defects do not block the bundle. Final request-bound docs/baseline and terminal phases rerun full current v5 selection/traces/receipts/challenge/readiness/dispatch/journal/AID/retirement state while inventory/evidence/reports exist. `--expect-atom-key` is valid only for docs.

## Selection State Shape

After Goal handoff, `context_selection.version` must be exact string `"5"`. Before Goal handoff, bootstrap state may omit selection entirely. Once selection exists, a missing, non-string, v1-v4, future, or unknown marker is invalid. Fail closed with guidance to create a new v5 request under existing approval/Goal gates; never resume, mutate, migrate, backfill, or dual-read rejected state.

The required v5 routing, shared-contract, binding trace, stable bundle, readiness, late-discovery, diagnostic, dispatch, closure, receipt/challenge/handoff, journal projection, `created_aids`, and retirement owners come from their routed references. Initialize retirement as exact `{"version":"1","retired_bundles":[],"retired_contracts":[]}`, handoffs as exact `{"version":"1","history":[]}`, challenge as exact `{"version":"1","attempts":[]}`, and `created_aids: []`. Sub-schema `version: "1"` markers are not older selection contracts.

A `merge` candidate replaces `candidate_atom_keys` with `merge_target_atom_key`; a `drop` candidate has neither. Candidate IDs are unique within the operation. More than one candidate contract may route risk to the same Atom key.

Use this compact evidence projection beside state:

```text
source_commit_observed: `<hash>`

## <candidate_id>
- `<source locator>` | `<lowercase content sha256>` | why this location matters | validation question
```

The source revision and every candidate section must be present. The validator checks this shape, digest, locator/reference closure, and receipt correspondence; reviewers judge locator authority, relevance, question quality, and observed meaning.

## Removal And Merge State

These fields are conditional. Omit them when the operation has no created artifact or approved removal/merge action; their absence grants no automatic removal/merge authority.

`operation_created_artifacts` contains one record per output created by this operation: `candidate_id`, `atom_key`, managed-docs-relative `path`, `created_attempt_id`, lowercase 64-hex `last_operation_sha256`, and `status: present|removal_pending|removed`. The path must stay below its accepted candidate domain and be absent from the fixed managed-docs revision corresponding to `source_commit_observed` plus the current HEAD/index. For submodule storage, resolve the gitlink commit recorded at `source_commit_observed`; a path present there is pre-existing even if later HEAD removes it. `present` requires the path and hash to match. Before deletion, `removal_pending` adds artifact `rollback_path`, `state_rollback_path`, and `state_rollback_sha256`; it accepts either the unchanged managed path or its expected absence for crash-safe resume. `removed` requires managed-path absence. Both removal states retain rollback files through operation close, require candidate `drop` plus a backticked candidate ID in inventory, and forbid selected routes or incoming graph edges using the key.

`approved_existing_actions` is immutable. Each record has `action_id`, `action: delete|merge`, `source`, optional merge `target`, `reference_owners`, and `approved_action_fingerprint`. Every member has `atom_key`, managed-docs-relative `path`, and `preimage_sha256`; member paths are unique and stay below accepted domain paths. A delete omits `target`, while a merge requires it. Existing-action members and `operation_created_artifacts` must have disjoint paths and keys, so neither provenance contract can impersonate the other. Fingerprint the record without `approved_action_fingerprint`: sort `reference_owners` by path, serialize UTF-8 JSON with sorted keys and separators `,` and `:`, then SHA-256 the bytes.

`action_execution` has exactly one record per approved action: matching `action_id` and fingerprint, `status: approved|applying|rolling_back|applied`, and one runtime member for every immutable member. Each member repeats `role: source|target|reference_owner`, `atom_key`, and `path`, then records `expected_state: present|absent`; present requires `last_operation_sha256`, absent forbids it. Every non-`approved` state retains each member `rollback_path` plus `state_rollback_path` and `state_rollback_sha256`. The complete state snapshot retains core scope/revision/v5 selection/queue/risk/trace/proof/AID fields, exactly matches every unrelated top-level owner, keeps unique candidate/artifact/action identities, and provides a restorable exact v5 routing contract. Current state and snapshot must exactly match every unrelated top-level owner. Every snapshot preserves structurally valid pre-mutation closure, its exact `operation_metrics` projection, readiness/dispatch, and retirement state; compare only snapshot projected-span progression while validating the current journal chain and exact projection equality. A newly retired current row uses a basis strictly above snapshot readiness and exactly matches one snapshot-active bundle/contract after excluding retirement metadata. Review PASS and invalidation records from the snapshot remain in current state. Apply the existing guarded-path, stale-PASS, required-review, retirement-basis, direct-route normalization, exact-bundle mapping, unrelated-scope preservation, and runtime membership rules without weakening them; another same-domain shard and unrelated risk PASSes remain current. A later resolved invalidation cannot retroactively authorize the mutation. Enforce status-specific allowed/forbidden keys and reject a forbidden key even when its JSON value is `null`, along with partial state extracts or a missing projection.

At `approved`, every member is present at its preimage hash. Every later present/absent expectation must match disk. At `applied`, delete requires source absence and every reference owner at its postimage; merge additionally requires the approved target identity and postimage. Both require no selected route or graph edge to the removed source. A mismatch, recreated source, unapproved incoming owner, bad rollback copy/snapshot, changed fingerprint, or accepted-scope violation is structural FAIL; the validator never repairs it. Only `--require-actions-final` requires every current-operation removal to be `removed` and every existing action to be `applied`.

## Semantic Review Closure Checks

Exact selection version 5 requires closure, receipt-bound readiness/semantic PASSes, stable bundle scopes, challenge/handoff state, and journal projection. Validate closure transitions, IDs, roles/status/triggers, revisions, artifacts, affected scope, stale references, exact required review pairs, immutable receipts/reports, current-basis challenge, and status-specific fields. The latest current readiness identity matches the current persistent reviewer; a historical stale/superseded readiness identity matches the persistent reviewer active at its own basis. Rehash current receipt docs from current bytes, but validate a historical receipt through its retained canonical manifest, immutable report, and source-revision locators without comparing its docs hash to mutable current docs. In every invalidation, including late-discovery and general-correction invalidations, each stale development/risk PASS ID requires its exact `(reviewer_role, stable bundle_id scope)` pair. A current risk PASS not listed stale adds no pair and keeps only the separately confirmed risk-neutral reuse path.

An open invalidation references `stale` prior PASSes and omits `resolved_revision`; a resolved one references `superseded` PASSes and current required PASSes at or after resolution. Across retained history, an open invalidation may only expand or become resolved. The same stale PASS cannot overlap invalidations. A post-readiness v5 discovery before any affected semantic PASS may use exact empty `semantic_invalidation_ids`; after such a PASS it must link invalidation. Final request-bound checks reject open invalidations, stale PASSes, a missing/non-blind/non-current challenge, and baseline without the current `baseline`/`project-wide` PASS.

The closure, receipts, challenge attempts, and handoff history are forward-only inside exact selection version 5. The validator rejects every other post-Goal marker and never migrates it.

## Phase Checks

`bootstrap` checks:

- `.stageflow/atomic-docs.json` exists, is valid JSON, and has no duplicate object keys
- required config keys exist
- `storage_mode` is `repository` or `submodule`
- `docs_root`, `source_root`, and `baseline_metadata_path` are relative paths that do not escape their configured roots
- the managed docs root and `project/atomization-criteria.md` exist

`selection` includes bootstrap checks and reads the explicit operation request under `.stageflow/atomic-docs/requests/<request-id>/`:

- `inventory.md`, `evidence.md`, and `work-state.json` exist
- exact selection version 5, a `source_commit_observed` that is a HEAD-reachable ancestor of the configured source repository, non-empty accepted scope, and candidate/evidence structures are well formed without duplicate JSON keys
- every candidate has a unique ID, exact accepted domain path, `write|merge|drop`, non-empty selection basis, and locator/digest/relevance/question evidence
- evidence revision, candidate headings, and locator rows use constrained plain Markdown: no tab characters, fenced or indented code (including inside blockquote or list containers), multiline inline code, or raw HTML-like syntax
- `write` owns valid planned Atom keys, `merge` resolves to a `write` key, and `drop` creates no key
- bundle expected keys equal the `write` keys and stay under each key owner's approved domain
- every risk trigger has unique `risk_id`, resolves candidate/output, and has one trace with owner/authority/applicability/consumer/resource/implementation/review binding; trace locators/digests and final owner/consumer Atoms occur in the referenced receipt manifest, pre-writer/intermediate traces may bind current same-basis readiness, final traces bind current receipt-bound semantic closure, and permission/privacy traces include the four-link chain
- local/shared routes, contract/queue references, retirement history, stable review scopes, criteria-bound receipts, writer/primary/risk/final identity separation, challenge/handoff recovery, dispatch cutoffs, late-discovery links, journal-projected review order, and strictly higher-basis resume are structurally closed
- optional artifact/action state satisfies removal/merge, exact v5 guarded-path-to-bundle mapping, snapshot projected-span progression, source/target identity, retained drop inventory, selected-route/trace closure, and incoming graph closure
- mandatory closure, proof, `created_aids`, journal/projection, readiness, dispatch, and retirement owners are present

Selection validation is the request-bound structural postcondition when a valid drop/delete leaves no managed Atom. If managed Atoms remain after an applied action, run unscoped docs validation too.

Selection validation applies only to exact version 5 after Goal handoff. Final selection uses `--require-actions-final`; every request-bound docs/baseline and terminal call rejects non-v5 state. Final phases rerun current routing/traces/receipts/challenge/AID consumers/readiness/dispatch/journal/retirement gates. Keep inventory/evidence/reports until terminal PASS and require baseline for a baseline profile/final PASS.

`docs` includes bootstrap checks. Without `--expect-atom-key`, it checks every `*-atom.md` under the managed docs root. With expected keys, it strictly checks those atoms and their references into the global identity/AID/graph index:

- frontmatter is valid standard YAML with no duplicate mapping keys and contains one lower-kebab-case `atom_key`
- `atom_key` values are globally unique
- required atom sections exist exactly once: `Intent`, `Outcomes`, `Boundaries`, `Rules`, `Current Implementation`, `Planned Changes`, and `Gaps`
- every discovered definition has valid `[AID:<key>.<section-code>.<NNN>]` shape and is globally unique
- an AID's section code matches the required section containing it
- a preserved AID may retain a historical key prefix after its meaning moves to another atom
- every `[AID-REF:<value>]` resolves one definition; a definition token never counts as a consumer
- final request-bound validation requires every v5 active `created_aids` value to resolve one definition and at least one external managed or recognized request-local consumer block; arbitrary request Markdown and same-definition-block references do not count, while intermediate and existing unlisted AIDs are exempt only from orphan checks
- every graph edge has `type`, `target_key`, `target_path`, and `reason`
- `target_key` resolves to exactly one atom and `target_path` resolves to that same atom
- every `--expect-atom-key` resolves to a real atom

Semantic AID indexing uses the plugin-vendored `markdown-it-py`/`mdurl` runtime, and standard YAML parsing uses the plugin-vendored pure-Python `PyYAML` runtime; third-party notices are retained under `scripts/_vendor/`. Validation fails closed if either bundled runtime is missing or corrupt. The AID index uses the CommonMark block/inline AST with GFM table parsing and indexes only rendered prose under `atom-format-and-judgment.md`; it does not recover with a second handwritten Markdown scanner or depend on host site-packages.

`baseline` includes docs checks and requires valid baseline metadata at the configured path:

```json
{
  "version": "1",
  "source_commit": "<40-or-64-character-git-hash>",
  "coverage": "project-wide"
}
```

The baseline commit must resolve in the configured `source_root`. `coverage` values for domains, features, atoms, targeted work, or partial scope are invalid.

When docs runs without `--expect-atom-key` and with `--request-id`, or baseline runs with `--request-id`, the validator also requires final semantic review closure. Docs validation without a request ID remains structural-only and does not validate operation state.

## Validation Boundary

The validator must not decide:

- whether a domain boundary is meaningful
- whether source exploration found the useful context candidates
- whether a candidate's `write|merge|drop` selection or stated basis is semantically correct
- whether an evidence index is concise enough or a source detail has durable value
- whether a selected candidate semantically requires a risk trigger; the development-quality reviewer checks completeness even when the trigger list is empty
- whether a risk concern is truly local/shared, every real direct consumer was found, the chosen owner/evidence is authoritative, or two FAILs share one root cause
- whether authority/applicability is truly verified, a consumer resource/identifier is correct, or a permission/privacy chain is safe
- whether natural-language implementation context is accurate or useful
- whether an important owner, shared/external contract, or non-obvious constraint is missing
- whether an Atomic Impl/compliance requirement is complete enough for its approved implementation scope
- whether user intent or a judgment label is correct
- whether a global baseline is semantically authorized by reviewer PASS results
- whether a recorded semantic invalidation found every affected artifact, bundle, or required reviewer
- whether a correction is risk-neutral or a measured span/rerun was necessary or efficient
- whether the final integration/baseline reviewer actually reconciled glossary, context, inventory, graph, root Gap ownership, and candidate economy correctly
- whether a receipt proves honest observation, a challenger was cognitively independent, or the event journal has an external trusted anchor
- whether a delete/merge action was actually approved by the user; the validator checks only the recorded immutable fingerprint and runtime state

Those decisions remain reviewer-owned. A structural PASS never replaces required subagent review.
