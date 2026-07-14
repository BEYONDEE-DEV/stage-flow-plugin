# Reviewer Perspectives

## Responsibility

This reference is the normative owner of semantic reviewer selection, report/verdict requirements, change-type routing, and rerun scope for the required domain development-quality reviewer, conditional risk/contract reviewer, and conditional affected-closure integration or project-wide baseline reviewer. `docs-generation-flow.md` owns when the selected roles are invoked and persisted.

## Findings-Only Report Contract

Every PASS report contains only these fields. For Korean operation reports, use this visible order:

```text
검토 범위 | source/revision | verdict | 확인한 대표 근거 | 재실행 필요 여부
```

`source/revision` is the inspected commit and bundle attempt, `verdict` is `PASS` or `provisional`, representative evidence is the smallest sample supporting the verdict, and rerun need is normally `없음`. Use equivalent user-language labels for another selected docs language.

A FAIL report adds only blocking findings, affected `atom_key`/AID when known, required docs/evidence correction, and the reviewer roles that must rerun. Do not repeat unchanged risk triggers, principle-file lists, source indexes, atom content, or a decision matrix in every PASS report. Keep applicable triggers and agent/reviewer state in `work-state.json`.

A reviewer must not issue PASS when an applicable principle file was not read. The main agent aggregates reports but cannot replace a required independent reviewer or issue that reviewer's PASS itself.

Reviewers may inspect source. Start from the operation evidence index instead of rediscovering every entry point. Independently reopen changed or risk-bearing claims and sample unchanged high-consequence claims whose error could alter the verdict. Do not reread every cited line mechanically or search for every undocumented behavior. Source access is required when checking fidelity, important context omissions, ownership, or impact. The quality test is whether the docs orient source inspection and expose the important constraints and contract touchpoints needed for development decisions.

## Required Domain Development-Quality Reviewer

Reuse one independent development-quality reviewer as the operation's context-quality reviewer. It reviews every selected domain bundle for `initial-baseline` and every new or meaning-changing bundle in other profiles. Structural-only work follows the routing policy without a complete domain review.

Always read the approved project criteria plus:

- `atom-format-and-judgment.md`
- `service-logic-coverage.md`

Read only the additional principle files implicated by the bundle: `atomic-document-contract.md` and `source-convention-and-domain-policy.md` for boundary/identity changes, `change-judgment-policy.md` for implementation judgments, and `project-documents-and-inventory.md` for ownership or context-candidate selection. Record the applicable principle set once in operation state; do not repeat it in every PASS report.

Check all of the following in one coherent pass:

- domain and context hygiene: no broad catch-all, context pollution, unsupported naming, vague split, or duplicated ownership
- context usefulness: the atom explains why the area exists, where to inspect it, and the important owner, rule, shared/external contract, non-obvious constraint, dependency, or unresolved decision when applicable to its stated scope
- current-context basis: source-established `Outcomes`, `Boundaries`, `Rules`, and `Current Implementation` claims are supported by reachable behavior and the applicable global baseline or operation-local `source_commit_observed` without a blanket inference Gap
- section ownership: one meaning has one complete owner; other sections use a short AID/heading reference, behavior-local boundaries do not repeat domain context, graph reasons do not restate natural-language contracts, and `Gaps`/source evidence do not duplicate the owning narrative
- proportional depth: general docs stop at useful implementation context and do not become a product-behavior specification, copy source mechanics, specify every behavior, expand exhaustive test combinations, or create matrices/field lists unless the structure itself preserves important contract context
- source fact fidelity: judgment-bearing claims match the actual reachable source behavior and stronger intent is not inferred from identifiers alone
- selected-scope trace: every context candidate accepted into the write queue has an atom or explicit unresolved/removal result, without requiring unselected source behavior to have a row or disposition
- judgment and identity integrity: source-established, confirmed, and genuinely unresolved bases, labels, selective AIDs, graph relationships, and operation reporting are consistent; ordinary judgments without AIDs identify the `atom_key`, exact owning section, and affected behavior
- gap economy: test absence, possible runtime exceptions, and isolated observations are not fragmented into managed gaps unless they block a stronger judgment; merged findings share one label, one unresolved decision, and compatible resolution without hiding independent high-risk concerns

FAIL when a documented claim contradicts source, lacks enough evidence to be trusted, hides a known shared/external contract, owner, or non-obvious constraint whose omission makes the atom's stated scope misleading, or conceals an important contract conflict. Also FAIL substantive repetition across sections, a blanket inference Gap, an observed defect promoted to a normal `Outcome` or required `Rule`, mechanical AID allocation, a forensic defect/attack inventory outside accepted scope, a Cartesian test plan, or `Current Implementation` written as a source substitute. A short reference plus the minimum local reading context is not duplication. Do not FAIL because general docs omit ordinary fields, inputs/outputs, branches, states, failures, exact verification results, concrete test cases, framework mechanics, CSS, or behavior-neutral mappings. A developer needing source to determine exact product behavior is expected; docs-only implementation is not the review target.

Do not persist an answer sheet for an ordinary development PASS. The reviewer may reason with one internally, but writes only the findings-only report. Use a decision table only when a blocking finding cannot be explained clearly without comparing several independently varying decisions.

When such a table is needed, use an equivalent of:

```text
맥락 또는 관련 AID | 확인한 소스/요구사항 | 변경 전에 알아야 하는 이유 | 영향받는 계약/도메인 | 판정
```

The answer sheet may summarize several related AIDs in one row when they form one decision. Do not create one review row per source file or per AID mechanically.

## Conditional Risk / Contract Reviewer

Run one additional independent reviewer only when `service-logic-coverage.md` identifies at least one risk trigger in selected context or an approved implementation-basis change. Code containing a possible risk surface is not by itself a request for a retained risk audit. Record the trigger in operation state before review and reuse the same risk reviewer across triggered bundles.

When both domain and risk reviews apply, they may run in parallel only against the same recorded review input revision and source basis. If either review causes a writer change, use the rerun routing below to decide which prior PASS remains valid.

Always read:

- `service-logic-coverage.md`
- `change-judgment-policy.md`

Read `atom-format-and-judgment.md` when the finding changes an AID or judgment-bearing atom line, and `atomic-graph.md` only for a shared/cross-domain trigger.

Review claims and owner/contract context for the selected triggered concern. Check whether documented permission or security boundaries, irreversible effects, money/entitlement ownership, transaction/idempotency constraints, retry/recovery guarantees, external contracts, sensitive data, or shared cross-domain contracts are accurate and not overstated. Do not discover every adverse branch or require a verification target for general context docs. An approved implementation-basis change must still state its required adverse outcome or verification condition when applicable. For an external contract, require authoritative local or user-approved provider evidence only when the docs or approved change relies on that guarantee.

FAIL when a documented high-risk contract is contradicted or overclaimed, when its owner or a non-obvious constraint is missing in a way that misleads change impact, or when an approved implementation-basis requirement omits a required adverse outcome or verification condition. Do not FAIL a general context atom merely because an unmentioned refusal, failure, side effect, rollback, recovery path, or test case exists in source. Require a structured matrix only when the alternatives themselves are important durable contract context that prose cannot explain reliably.

Do not repeat the complete domain review. A risk reviewer PASS is additional evidence and cannot replace the required development-quality reviewer PASS. Persist a decision comparison table only when the risky alternatives cannot be judged reliably from concise findings.

Do not turn incidental risk discovery into a retained audit backlog. A routine FAIL report keeps only concise blocking findings under the findings-only contract; detailed attack paths, fixture combinations, and non-blocking defect inventories are not persisted in managed docs or routine review artifacts. A materially serious incidental issue may be summarized to the user, but a complete security or defect audit and retained report require separately accepted scope.

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

For `initial-baseline`, verify every project-native feature area was considered for context selection, obvious high-impact shared/external owners were documented or excluded with a reason, every selected domain and risk review PASSed at the same source commit, and structural baseline validation PASSed. Do not require every product behavior or aggregate to have a disposition.

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
- Full project baseline: every selected domain bundle's applicable reviews plus project-wide integration/baseline reviewer.

## Rerun Policy

- Route reruns by what changed after the reviewed input revision:

| Change after review | Required rerun |
| --- | --- |
| Markdown formatting, graph path repair, expected-key correction, or inventory count with unchanged selection/owner | structural preflight only |
| Source locator/evidence index correction with unchanged documented claim | narrowed source-evidence check by the development reviewer |
| Intent, important context, rule/contract, ownership, approved verification condition, or judgment label | development-quality reviewer for affected bundle(s) |
| Risk trigger, adverse branch, permission, destructive effect, transaction/idempotency, recovery, sensitive data, or external contract | risk/contract reviewer; also development reviewer when the documented decision changed |
| Atom boundary, owner, edge type/target, shared contract meaning, or glossary source of truth | development reviewer for affected bundles plus affected-closure integration reviewer when its prior basis changed |

Graph `reason` wording or inventory count alone does not trigger semantic review when relationship meaning and ownership are unchanged. If either changes meaning, route it as a shared-contract/ownership change.

- After a FAIL, revise the affected bundle and run only the checks selected above.
- Do not rerun unaffected PASS results or a complete domain review for evidence-only correction.
- Do not start the next sequential bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.
- Reviewer FAIL is not completion and is not a Goal blocker when it can be corrected inside accepted scope.
- Ask the user only when PASS requires a user decision or a separately authorized destructive or external action.
