# Reviewer Perspectives

## Responsibility

This reference defines the required domain development-quality reviewer, the conditional risk/contract reviewer, and the conditional project-wide integration/baseline reviewer. Review effort scales with the accepted scope and risk instead of using a fixed reviewer count.

## Shared Report Contract

Every reviewer report must include:

- `review scope`
- `review role`
- `principle files reviewed`
- `source basis`: the inspected commit or explicitly recorded source revision
- `risk triggers` that apply or `none`
- `verdict`: `PASS`, `FAIL`, or `provisional`
- blocking findings with docs, source, operation-state, or validation evidence appropriate to the role
- affected `atom_key`/AID when known
- evidence changed since the previous run
- rerun requirement and affected reviewers

A reviewer must not issue PASS when a required principle file was not read. The main agent aggregates reports but cannot replace a required independent reviewer or issue that reviewer's PASS itself.

Reviewers may inspect source. Source access is required when checking fidelity, missing decisions, accepted-scope coverage, or impact. The quality test is not whether a reviewer can reproduce code without source; it is whether the docs preserve the decisions needed for implementation, verification, and conflict analysis.

## Required Domain Development-Quality Reviewer

Every active domain bundle uses one writer followed by one independent development-quality reviewer.

Read:

- `atomic-document-contract.md`
- `atom-format-and-judgment.md`
- `atomization-criteria-contract.md`
- `source-convention-and-domain-policy.md`
- `service-logic-coverage.md`
- `change-judgment-policy.md`
- `project-documents-and-inventory.md`

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

Read:

- `service-logic-coverage.md`
- `change-judgment-policy.md`
- `atom-format-and-judgment.md`
- `atomic-graph.md`

Review only the triggered concerns. Check adverse branches, permission or security boundaries, irreversible effects, money/entitlement changes, transaction/idempotency, retries/recovery, external contracts, sensitive data, and shared cross-domain contracts as applicable. For an external contract, require authoritative local or user-approved provider evidence; otherwise require a supported `confirmation_needed` gap.

FAIL when the risky decision, refusal/failure path, side effect, rollback/recovery behavior, or observable verification evidence is missing or contradicted. Require a structured matrix only when the alternatives cannot be reviewed reliably in prose.

Do not repeat the complete domain review. A risk reviewer PASS is additional evidence and cannot replace the required development-quality reviewer PASS.

## Conditional Project-Wide Integration / Baseline Reviewer

Run one project-wide reviewer only when at least one condition applies:

- the accepted scope is project-wide
- more than one domain bundle changed
- a shared cross-domain contract or graph relationship changed
- the operation seeks to create or update the global source baseline

Read:

- `atomic-graph.md`
- `source-baseline-and-change-plan.md`
- `docs-generation-flow.md`
- `service-logic-coverage.md`
- `project-documents-and-inventory.md`

Check cross-domain ownership, duplicate responsibility, glossary source of truth, graph consistency, shared payload/state/storage/permission/integration contracts, changed evidence after domain PASS, accepted-scope reporting, and baseline eligibility. Require every participating domain review to use the operation's recorded `source_commit_observed`; if source changed, reopen affected bundles before PASS.

For a global baseline, also verify that every project behavior aggregate has a disposition, all required domain and risk reviews PASSed at the same source commit, structural baseline validation PASSed, and no blocker prevents project-wide development judgment.

Do not repeat unchanged domain detail. If the project-wide view exposes a local defect, reopen the affected bundle, rerun its writer and affected reviewers, then rerun this reviewer.

This reviewer is the only semantic reviewer that can approve global baseline creation or update.

## Reviewer Selection Examples

- Targeted, ordinary single-domain change: development-quality reviewer only.
- Targeted high-risk single-domain change: development-quality reviewer plus risk/contract reviewer.
- Multi-domain or shared-contract change: applicable domain reviews plus project-wide integration reviewer.
- Full project baseline: every domain's applicable reviews plus project-wide integration/baseline reviewer.

## Rerun Policy

- After a FAIL, revise the affected bundle and rerun the failed reviewer plus any reviewer whose evidence changed.
- Do not rerun unaffected PASS results.
- Do not start the next sequential bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.
- Reviewer FAIL is not completion and is not a Goal blocker when it can be corrected inside accepted scope.
- Ask the user only when PASS requires a user decision or a separately authorized destructive or external action.
