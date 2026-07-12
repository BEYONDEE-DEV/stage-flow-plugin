# Reviewer Perspectives

## Responsibility

This reference defines the required domain development-quality reviewer, the conditional risk/contract reviewer, and the conditional affected-closure integration or project-wide baseline reviewer. Review effort scales with the accepted scope and risk instead of using a fixed reviewer count.

## Shared Report Contract

Every reviewer report must include:

- `review scope`
- `review role`
- `principle files reviewed`
- `source basis`: the inspected commit or explicitly recorded source revision
- `review input revision`: the bundle attempt reviewed
- `risk triggers` that apply or `none`
- `verdict`: `PASS`, `FAIL`, or `provisional`
- blocking findings with docs, source, operation-state, or validation evidence appropriate to the role
- affected `atom_key`/AID when known
- evidence changed since the previous run
- rerun requirement and affected reviewers

A reviewer must not issue PASS when a required principle file was not read. The main agent aggregates reports but cannot replace a required independent reviewer or issue that reviewer's PASS itself.

Reviewers may inspect source. Start from the operation evidence index instead of rediscovering every entry point. Independently reopen changed or risk-bearing claims and sample unchanged high-consequence claims whose error could alter the verdict. Do not reread every cited line mechanically. Source access is required when checking fidelity, missing decisions, accepted-scope coverage, or impact. The quality test is whether the docs preserve the decisions needed for implementation, verification, and conflict analysis.

## Required Domain Development-Quality Reviewer

Every active domain bundle uses one writer followed by one independent development-quality reviewer.

Always read the approved project criteria plus:

- `atom-format-and-judgment.md`
- `service-logic-coverage.md`

Read only the additional principle files implicated by the bundle: `atomic-document-contract.md` and `source-convention-and-domain-policy.md` for boundary/identity changes, `change-judgment-policy.md` for implementation judgments, and `project-documents-and-inventory.md` for ownership or inventory closure. The report lists which conditional files applied.

Check all of the following in one coherent pass:

- domain and context hygiene: no broad catch-all, context pollution, unsupported naming, vague split, or duplicated ownership
- decision completeness: intent, rules, observable contract, consequential branch/state/side effect, verification condition, dependency, and unresolved decision are recorded when applicable
- proportional depth: source mechanics are not copied into docs, and matrices or field lists exist only where prose would leave a decision ambiguous
- source fact fidelity: judgment-bearing claims match the actual reachable source behavior and stronger intent is not inferred from identifiers alone
- accepted-scope closure: every meaningful behavior aggregate in scope has an atom/AID or explicit disposition without requiring one row per mechanical source surface
- judgment and identity integrity: inferred/confirmed basis, labels, selective AIDs, graph relationships, and operation reporting are consistent

FAIL when a developer still must invent product behavior, a reviewer cannot derive an observable verification result, an important contract conflict is hidden, or docs contradict source. Do not FAIL merely because internal code structure, framework mechanics, exact CSS, or behavior-neutral mappings remain in source.

Use an answer sheet equivalent to:

```text
결정 또는 관련 AID | 확인한 소스/요구사항 | 구현자가 임의로 정하면 안 되는 내용 | 검증 가능한 결과 | 영향받는 계약/도메인 | 판정
```

The answer sheet may summarize several related AIDs in one row when they form one decision. Do not create one review row per source file or per AID mechanically.

## Conditional Risk / Contract Reviewer

Run one additional independent reviewer only when `service-logic-coverage.md` identifies at least one risk trigger. Record the trigger in operation state before review.

When both domain and risk reviews apply, they may run in parallel only against the same recorded review input revision and source basis. If either review causes a writer change, use the rerun routing below to decide which prior PASS remains valid.

Always read:

- `service-logic-coverage.md`
- `change-judgment-policy.md`

Read `atom-format-and-judgment.md` when the finding changes an AID or judgment-bearing atom line, and `atomic-graph.md` only for a shared/cross-domain trigger.

Review only the triggered concerns. Check adverse branches, permission or security boundaries, irreversible effects, money/entitlement changes, transaction/idempotency, retries/recovery, external contracts, sensitive data, and shared cross-domain contracts as applicable. For an external contract, require authoritative local or user-approved provider evidence; otherwise require a supported `confirmation_needed` gap.

FAIL when the risky decision, refusal/failure path, side effect, rollback/recovery behavior, or observable verification evidence is missing or contradicted. Require a structured matrix only when the alternatives cannot be reviewed reliably in prose.

Do not repeat the complete domain review. A risk reviewer PASS is additional evidence and cannot replace the required development-quality reviewer PASS.

## Conditional Integration / Baseline Reviewer

Run one integration/baseline reviewer only when at least one condition applies:

- a shared cross-domain contract, ownership, glossary source of truth, or graph relationship changed
- the operation profile is `initial-baseline` or `baseline-diff-refresh`

For a non-baseline operation, review only the affected closure. Do not add this reviewer merely because several independent bundles changed. For a baseline profile, expand the review to the whole project.

Always read:

- `atomic-graph.md`
- `docs-generation-flow.md`
- `project-documents-and-inventory.md`

Read `source-baseline-and-change-plan.md` for a baseline profile and `service-logic-coverage.md` only when shared risk/contract triggers are in scope.

Check cross-domain ownership, duplicate responsibility, glossary source of truth, graph consistency, shared payload/state/storage/permission/integration contracts, changed evidence after domain PASS, accepted-scope reporting, and baseline eligibility when applicable. Every newly run domain review uses the operation's `source_commit_observed`; if relevant source changed after review, reopen affected bundles before PASS.

For `initial-baseline`, verify every project behavior aggregate has a disposition, all required domain and risk reviews PASSed at the same source commit, structural baseline validation PASSed, and no blocker prevents project-wide development judgment.

For `baseline-diff-refresh`, verify the complete old-to-new diff and ownership/graph/criteria impact expansion, impacted bundle reviews at the new commit, and the recorded rationale for carrying each unaffected bundle class from the trusted prior baseline. Do not claim carried reviews ran at the new commit.

Do not repeat unchanged domain detail. If the project-wide view exposes a local defect, reopen the affected bundle, rerun its writer and affected reviewers, then rerun this reviewer.

Only the project-wide form of this reviewer can approve global baseline creation or update.

## Reviewer Selection Examples

- Targeted, ordinary single-domain change: development-quality reviewer only.
- Targeted high-risk single-domain change: development-quality reviewer plus risk/contract reviewer.
- Independent multi-domain changes: applicable domain reviews only.
- Shared-contract change: applicable domain reviews plus affected-closure integration reviewer.
- Full project baseline: every domain's applicable reviews plus project-wide integration/baseline reviewer.

## Rerun Policy

- Route reruns by what changed after the reviewed input revision:

| Change after review | Required rerun |
| --- | --- |
| Markdown formatting, graph path repair, expected-key correction, or inventory count with unchanged owner/disposition | structural preflight only |
| Source locator/evidence index correction with unchanged documented claim | narrowed source-evidence check by the development reviewer |
| Intent, rule, observable contract, verification condition, behavior ownership, or judgment label | development-quality reviewer for affected bundle(s) |
| Risk trigger, adverse branch, permission, destructive effect, transaction/idempotency, recovery, sensitive data, or external contract | risk/contract reviewer; also development reviewer when the documented decision changed |
| Atom boundary, owner, edge type/target, shared contract meaning, or glossary source of truth | development reviewer for affected bundles plus affected-closure integration reviewer when its prior basis changed |

Graph `reason` wording or inventory count alone does not trigger semantic review when relationship meaning and ownership are unchanged. If either changes meaning, route it as a shared-contract/ownership change.

- After a FAIL, revise the affected bundle and run only the checks selected above.
- Do not rerun unaffected PASS results or a complete domain review for evidence-only correction.
- Do not start the next sequential bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.
- Reviewer FAIL is not completion and is not a Goal blocker when it can be corrected inside accepted scope.
- Ask the user only when PASS requires a user decision or a separately authorized destructive or external action.
