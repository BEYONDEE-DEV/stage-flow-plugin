# Reviewer Perspectives

## Responsibility

This reference defines the required domain development-quality reviewer, the conditional risk/contract reviewer, and the conditional affected-closure integration or project-wide baseline reviewer. Review effort scales with the accepted scope and risk instead of using a fixed reviewer count.

## Findings-Only Report Contract

Every PASS report contains only these fields. For Korean operation reports, use this visible order:

```text
검토 범위 | source/revision | verdict | 확인한 대표 근거 | 재실행 필요 여부
```

`source/revision` is the inspected commit and bundle attempt, `verdict` is `PASS` or `provisional`, representative evidence is the smallest sample supporting the verdict, and rerun need is normally `없음`. Use equivalent user-language labels for another selected docs language.

A FAIL report adds only blocking findings, affected `atom_key`/AID when known, required docs/evidence correction, and the reviewer roles that must rerun. Do not repeat unchanged risk triggers, principle-file lists, source indexes, atom content, or a decision matrix in every PASS report. Keep applicable triggers and agent/reviewer state in `work-state.json`.

A reviewer must not issue PASS when an applicable principle file was not read. The main agent aggregates reports but cannot replace a required independent reviewer or issue that reviewer's PASS itself.

Reviewers may inspect source. Start from the operation evidence index instead of rediscovering every entry point. Independently reopen changed or risk-bearing claims and sample unchanged high-consequence claims whose error could alter the verdict. Do not reread every cited line mechanically. Source access is required when checking fidelity, missing decisions, accepted-scope coverage, or impact. The quality test is whether the docs preserve the decisions needed for implementation, verification, and conflict analysis.

## Required Domain Development-Quality Reviewer

Reuse one independent development-quality reviewer across the operation. It reviews every domain bundle for `initial-baseline` and every new or meaning-changing bundle in other profiles. Structural-only work follows the routing policy without a complete domain review.

Always read the approved project criteria plus:

- `atom-format-and-judgment.md`
- `service-logic-coverage.md`

Read only the additional principle files implicated by the bundle: `atomic-document-contract.md` and `source-convention-and-domain-policy.md` for boundary/identity changes, `change-judgment-policy.md` for implementation judgments, and `project-documents-and-inventory.md` for ownership or inventory closure. Record the applicable principle set once in operation state; do not repeat it in every PASS report.

Check all of the following in one coherent pass:

- domain and context hygiene: no broad catch-all, context pollution, unsupported naming, vague split, or duplicated ownership
- decision completeness: intent, outcomes, boundaries, rules, observable contract, consequential branch/state/side effect, concise verification target, dependency, and unresolved decision are recorded in their owning sections when applicable
- section ownership: one meaning has one complete owner; other sections use a short AID/heading reference, behavior-local boundaries do not repeat domain context, graph reasons do not restate natural-language contracts, and `Gaps`/source evidence do not duplicate the owning narrative
- proportional depth: source mechanics are not copied into docs, repeated across sections, expanded into exhaustive test combinations, or turned into matrices/field lists unless the structure itself preserves a durable decision that prose would leave ambiguous
- source fact fidelity: judgment-bearing claims match the actual reachable source behavior and stronger intent is not inferred from identifiers alone
- accepted-scope closure: every meaningful behavior aggregate in scope has an atom/AID or explicit disposition without requiring one row per mechanical source surface
- judgment and identity integrity: inferred/confirmed basis, labels, selective AIDs, graph relationships, and operation reporting are consistent; ordinary judgments without AIDs identify the `atom_key`, exact owning section, and affected behavior
- gap economy: test absence, possible runtime exceptions, and isolated observations are not fragmented into managed gaps unless they block a stronger judgment; merged findings share one label, one unresolved decision, and compatible resolution without hiding independent high-risk concerns

FAIL when a developer still must invent product behavior, a reviewer cannot derive an observable verification result, an important contract conflict is hidden, docs contradict source, or the same condition, branch, result, state effect, failure, boundary, or evidence narrative is substantively repeated across sections or ownership artifacts. Also FAIL over-documentation that preserves a Cartesian test plan, fragments one decision into mechanical AIDs/gaps, or makes `Current Implementation` a substitute for source inspection. A short reference plus the minimum local reading context is not duplication. Do not FAIL merely because internal code structure, concrete test cases, framework mechanics, exact CSS, or behavior-neutral mappings remain in source or test code.

Do not persist an answer sheet for an ordinary development PASS. The reviewer may reason with one internally, but writes only the findings-only report. Use a decision table only when a blocking finding cannot be explained clearly without comparing several independently varying decisions.

When such a table is needed, use an equivalent of:

```text
결정 또는 관련 AID | 확인한 소스/요구사항 | 구현자가 임의로 정하면 안 되는 내용 | 검증 가능한 결과 | 영향받는 계약/도메인 | 판정
```

The answer sheet may summarize several related AIDs in one row when they form one decision. Do not create one review row per source file or per AID mechanically.

## Conditional Risk / Contract Reviewer

Run one additional independent reviewer only when `service-logic-coverage.md` identifies at least one risk trigger. Record the trigger in operation state before review and reuse the same risk reviewer across triggered bundles.

When both domain and risk reviews apply, they may run in parallel only against the same recorded review input revision and source basis. If either review causes a writer change, use the rerun routing below to decide which prior PASS remains valid.

Always read:

- `service-logic-coverage.md`
- `change-judgment-policy.md`

Read `atom-format-and-judgment.md` when the finding changes an AID or judgment-bearing atom line, and `atomic-graph.md` only for a shared/cross-domain trigger.

Review only the triggered concerns. Check adverse branches, permission or security boundaries, irreversible effects, money/entitlement changes, transaction/idempotency, retries/recovery, external contracts, sensitive data, and shared cross-domain contracts as applicable. Require the durable risky decision and concise verification target, then derive concrete test combinations during implementation/review instead of requiring their full cross-product in the atom. For an external contract, require authoritative local or user-approved provider evidence; otherwise require a supported `confirmation_needed` gap.

FAIL when the risky decision, refusal/failure path, side effect, rollback/recovery behavior, or observable verification target is missing or contradicted. Require the missing detail in its owning section and references elsewhere; do not request a second full copy in `Current Implementation` or `Gaps`. Require a structured matrix only when the alternatives themselves form a durable contract that cannot be reviewed reliably in prose, not merely to enumerate tests.

Do not repeat the complete domain review. A risk reviewer PASS is additional evidence and cannot replace the required development-quality reviewer PASS. Persist a decision comparison table only when the risky alternatives cannot be judged reliably from concise findings.

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

Use a cross-domain decision table only when ownership, contracts, or baseline carry-forward alternatives cannot be judged reliably in concise findings. The ordinary PASS report remains findings-only.

Only the project-wide form of this reviewer can approve global baseline creation or update.

## Reviewer Selection Examples

- Targeted structural-only single-domain change: scoped validator only.
- Targeted decision-bearing ordinary single-domain change: development-quality reviewer only.
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
