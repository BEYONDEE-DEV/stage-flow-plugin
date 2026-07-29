# Implementation Flow

The fixed sequence is:

```text
user requirements
-> Atomic Docs Changes RIDs
-> docs validation and semantic review
-> user implementation approval
-> code and tests
-> implementation review
-> user result approval
-> final Atomic Docs promotion
```

## 1. Establish The Docs Basis

Read `skills/atomic-docs/SKILL.md` before any managed-doc action. If config or the relevant managed docs are missing, use the smallest appropriate Atomic Docs update first.

Inspect the user requirement, current source behavior, and affected Atom ownership. Select one owning Atom per independent change. Add exactly one RID item for each approved but unimplemented change:

```text
- [RID:checkout-payment.reject-expired-card] 만료된 카드는 승인 요청 전에 거부하고 실패 결과를 호출자에게 반환한다.
```

The Atom key in the RID must equal the owning `atom_key`. The slug is lower-kebab. There is no RID reference token; do not repeat the RID elsewhere. Split only independently implementable or independently approvable changes; do not create IDs for observations or source mechanics.

Correct `Boundaries` before implementation only when current source proves the existing ownership statement was wrong. Keep a future boundary change in its RID item under `Changes` until implementation is complete. Use `Open Questions` when a blocking decision needs clarification. Keep existing behavior in `Implementation` only when supported by current source. Put exact evidence in `Sources`.

Run the Atomic Docs validator and one semantic review, then rerun the validator after any review correction. If a material decision remains unresolved, stop before implementation approval.

Present:

- changed docs paths
- RIDs and behavior to implement
- important boundaries, contracts, side effects, failures, and verification conditions
- remaining `Open Questions`
- selected and uninspected scope

Do not start code until the user explicitly approves this implementation basis.

## 2. Implement And Review

Implement only the approved RIDs and necessary supporting work. Follow project conventions and inspect source whenever internal mechanics are needed.

Run the relevant tests, validators, linters, or targeted commands. Then assign one implementation reviewer the approved docs basis, actual code diff, and validation output. The reviewer checks RID coverage, behavioral agreement, data/state flow, validation, side effects, failure/recovery, test evidence, and material scope drift.

Correct material findings and rerun affected validation. If an unresolved product decision appears, return to the docs basis and user approval instead of silently choosing it.

Present the implementation result, changed code paths, validation evidence, review findings, and any docs/code mismatch. Ask the user to approve the result and final docs update.

## 3. Promote Final Docs

Do not finalize Atomic Docs before explicit result approval.

For every completed RID:

1. remove the RID item from `Changes`
2. put lasting responsibility, behavior, or invariants in `Contracts` or `Boundaries`
3. update `Implementation` to describe the realized design concisely
4. add or refresh exact `Sources` locators

Use exact `- 없음` when no active change remains. Do not retain an implementation history or trace table in managed docs.

Run the Atomic Docs validator and bounded semantic review, then validate the final reviewed docs again. Compare the approved requirement, approved implementation result, final docs, actual diff, and validation output. If code and final docs differ materially, correct the responsible artifact and rerun the affected check.

Report final docs/code compliance, final paths, test and validator results, and remaining `Open Questions`.
