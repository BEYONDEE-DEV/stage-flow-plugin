# Reviewer Perspectives

## Contents

- [Responsibility](#responsibility)
- [Findings-Only Report Contract](#findings-only-report-contract)
- [Sanitized Semantic Regression Guard](#sanitized-semantic-regression-guard)
- [Required Domain Development-Quality Reviewer](#required-domain-development-quality-reviewer)
- [Conditional Risk / Contract Reviewer](#conditional-risk--contract-reviewer)
- [Conditional Integration / Baseline Reviewer](#conditional-integration--baseline-reviewer)
- [Reviewer Selection Examples](#reviewer-selection-examples)
- [Rerun Policy](#rerun-policy)

## Responsibility

This reference is the normative owner of semantic reviewer selection, findings-only report/verdict requirements, change-type routing, and rerun scope for the required domain development-quality reviewer, conditional risk/contract reviewer, and conditional affected-closure integration or project-wide baseline reviewer. `docs-generation-flow.md` owns when selected roles run; `shared-contract-readiness.md` owns v5 readiness and binding traces; `semantic-review-proof.md` owns receipt, primary/challenger identity, and handoff; `semantic-review-closure.md` owns invalidating and resolving PASS basis.

## Findings-Only Report Contract

Every PASS report contains only these fields. For Korean operation reports, use this visible order:

```text
검토 범위 | source/revision | verdict | 확인한 대표 근거 | 재실행 필요 여부
```

`source/revision` is the inspected commit and bundle attempt, `verdict` is `PASS` or `provisional`, representative evidence is the smallest sample supporting the verdict, and rerun need is normally `없음`. Use equivalent user-language labels for another selected docs language.

A FAIL report adds only blocking findings. Each blocking finding records the affected `atom_key`/AID when known, one `correction_mode`, required docs/evidence correction, and the reviewer roles that must rerun. Different findings in one report may use different modes; use the first applicable mode for each finding:

- `remove`: the claim, paragraph, or Atom lacks a durable selection basis
- `generalize`: the underlying context is useful but source mechanics should become concise owner, contract, rule, or constraint context
- `correct_selected_claim`: a retained important claim is false, unsupported, or materially incomplete

Do not choose `correct_selected_claim` for a finding until removal and generalization have been considered for that finding. Do not repeat unchanged risk triggers, principle-file lists, source indexes, atom content, or a decision matrix in every PASS report. Keep applicable triggers and agent/reviewer state in `work-state.json`. Persist each report as one immutable request-local file and let `semantic-review-proof.md` bind its path/hash; do not add receipt fields to the findings-only body.

For a whole-Atom `remove`, name the candidate and whether correction is a current-operation-created drop, an exact already approved existing-Atom action, or a new protected action. The first two continue automatically through `docs-generation-flow.md`; only the third needs a user decision. Do not turn a correctable current-operation drop into Goal `blocked` or request the same approved delete/merge twice.

A reviewer must not issue PASS when an applicable principle file was not read. The main agent aggregates reports but cannot replace a required independent reviewer or issue that reviewer's PASS itself.

Reviewers may inspect source. Start from the operation evidence index instead of rediscovering every entry point. Independently reopen changed or risk-bearing claims and sample unchanged high-consequence claims whose error could alter the verdict. Do not reread every cited line mechanically or search for every undocumented behavior. Source access is required when checking fidelity, important context omissions, ownership, or impact. The quality test is whether the docs orient source inspection and expose the important constraints and contract touchpoints needed for development decisions.

## Sanitized Semantic Regression Guard

Use a sanitized immutable golden corpus to regression-test reviewer policy without carrying project data. Require the expected semantic outcome to reject a cross-resource PII load/projection as a healthy Rule, classify a verified authoritative/applicable canonical-identifier consumer conflict as `bug_or_regression` rather than `confirmation_needed`, reject mechanical AID allocation, and keep independently resolvable Gaps/claims separate. Require the expected binding trace, receipt, AID definition/reference, and observed result for each applicable case.

For the forward check, give a fresh reviewer only the raw sanitized request, managed docs, criteria, source, and source locators. Exclude expected answers, prior verdicts, diagnostic summaries, and primary reports. Treat PASS as policy/fixture regression evidence only; never claim it remediates or revalidates the source repository from which a failure family was learned.

## Required Domain Development-Quality Reviewer

Reuse one independent development-quality reviewer as the operation's context-quality reviewer. The same persistent reviewer first performs the selection-readiness review from `shared-contract-readiness.md`; this does not add a reviewer role. It then reviews every selected domain bundle for `initial-baseline` and every new or meaning-changing bundle in other profiles. Structural-only work follows the routing policy without a complete domain review.

Always read the approved project criteria plus:

- `atom-format-and-judgment.md`
- `service-logic-coverage.md`

Read only the additional principle files implicated by the bundle: `atomic-document-contract.md` and `source-convention-and-domain-policy.md` for boundary/identity changes, `change-judgment-policy.md` for implementation judgments, and `project-documents-and-inventory.md` for ownership or context-candidate selection. Record the applicable principle set once in operation state; do not repeat it in every PASS report.

Check all of the following in one coherent pass:

- domain and context hygiene: no broad catch-all, context pollution, unsupported naming, vague split, or duplicated ownership
- candidate admission: every written Atom traces to a `write` candidate or merge target with a durable selection basis, while `drop` and ordinary unselected source behavior remain outside managed docs
- risk classification completeness: apply the trigger contract to every selected `write` or `merge` candidate and verify candidate-linked routes before deciding whether a risk reviewer exists; an empty trigger list is not self-validating
- binding integrity: require one `shared-contract-readiness.md` trace for every selected risk ID and verify its authority, applicability, consumer, resource/identifier, observed implementation, explicit `observed_conflict` finding when applicable, receipt-bound review, and permission/privacy chain when applicable
- context usefulness: the atom explains why the area exists, where to inspect it, and the important owner, rule, shared/external contract, non-obvious constraint, dependency, or unresolved decision when applicable to its stated scope
- current-context basis: source-established `Outcomes`, `Boundaries`, `Rules`, and `Current Implementation` claims are supported by reachable behavior and the applicable global baseline or operation-local `source_commit_observed` without a blanket inference Gap
- section ownership: one meaning has one complete owner; other sections use a short `[AID-REF:...]` or heading reference, behavior-local boundaries do not repeat domain context, graph reasons do not restate natural-language contracts, and `Gaps`/source evidence do not duplicate the owning narrative
- proportional depth: general docs stop at useful implementation context and do not become a product-behavior specification, copy source mechanics, specify every behavior, expand exhaustive test combinations, or create matrices/field lists unless the structure itself preserves important contract context
- source fact fidelity: judgment-bearing claims match the actual reachable source behavior and stronger intent is not inferred from identifiers alone
- selected-scope trace: every `write` candidate and merge target has its planned Atom result, every `drop` candidate has none, and unselected source behavior needs no row or disposition
- judgment and identity integrity: source-established, confirmed, and genuinely unresolved bases, labels, selective AIDs, graph relationships, and operation reporting are consistent; ordinary judgments without AIDs identify the `atom_key`, exact owning section, and affected behavior
- gap economy: test absence, possible runtime exceptions, and isolated observations are not fragmented into managed gaps unless they block a stronger judgment; merged findings share one label, one unresolved decision, and compatible resolution without hiding independent high-risk concerns
- canonical unresolved-decision ownership: one root decision or Gap has one owning context/Atom; consumers cite that owner and add only a distinct local consequence, not a second independently resolvable copy

Before failing for an omitted source fact, apply candidate admission to that fact. If it would be `drop`, omission is correct. If it belongs in an existing meaning without an independent boundary, use `generalize` or merge it instead of demanding branch-level detail. Only a fact that changes a retained claim, important owner, durable contract, or accepted implementation basis may require `correct_selected_claim`. Stop completeness discovery once selected claims can be judged. Escalate only a directly evidenced omitted bounded high-fan-out contract to `shared-contract-readiness.md`; ordinary API, branch, transaction, projection, failure, or attack-path detail cannot expand the review scope.

FAIL when a documented claim contradicts source, lacks enough evidence to be trusted, hides a known shared/external contract, owner, or non-obvious constraint whose omission makes the atom's stated scope misleading, or conceals an important contract conflict. Also FAIL substantive repetition across sections, a blanket inference Gap, an observed defect promoted to a normal `Outcome` or required `Rule`, mechanical AID allocation, a dangling `[AID-REF:...]`, independently resolvable Gap/claim meanings merged together, a forensic defect/attack inventory outside accepted scope, a Cartesian test plan, or `Current Implementation` written as a source substitute. A short reference plus the minimum local reading context is not duplication. Do not FAIL because general docs omit ordinary fields, inputs/outputs, branches, states, failures, exact verification results, concrete test cases, framework mechanics, CSS, or behavior-neutral mappings. A developer needing source to determine exact product behavior is expected; docs-only implementation is not the review target.

Do not persist an answer sheet for an ordinary development PASS. The reviewer may reason with one internally, but writes only the findings-only report. Use a decision table only when a blocking finding cannot be explained clearly without comparing several independently varying decisions.

When such a table is needed, use an equivalent of:

```text
맥락 또는 관련 AID | 확인한 소스/요구사항 | 변경 전에 알아야 하는 이유 | 영향받는 계약/도메인 | 판정
```

The answer sheet may summarize several related AIDs in one row when they form one decision. Do not create one review row per source file or per AID mechanically.

## Conditional Risk / Contract Reviewer

Run one additional independent reviewer when operation state records at least one `service-logic-coverage.md` risk trigger tied to a selected candidate/Atom contract or an approved implementation-basis change. The development-quality reviewer independently checks trigger completeness, its local/shared route, and one-to-one binding trace. If it FAILs on a missing candidate-linked trigger or trace, correct state, rerun version-5 selection preflight, and rerun both development and applicable risk reviews against the same corrected revision; never reuse the old FAIL as PASS. Code containing a possible risk surface and a domain-level risk category are not by themselves requests for a retained risk audit. Record the risk ID, candidate ID, planned `atom_key`, trigger, selected contract basis, route, and trace before review and reuse the same risk reviewer across triggered bundles. Several candidate contracts may reference the same Atom key and remain separate trigger entries/traces.

When both domain and risk reviews apply, they may run in parallel only against the same recorded review input revision and source basis. If either review causes a writer change, use the rerun routing below to decide which prior PASS remains valid.

Always read:

- `service-logic-coverage.md`
- `change-judgment-policy.md`

Read `atom-format-and-judgment.md` when the finding changes an AID or judgment-bearing atom line, and `atomic-graph.md` only for a shared/cross-domain trigger.

Review claims and owner/contract context for the selected triggered concern. Reopen the trace's authoritative owner revision, applicability basis, consumer, resource/canonical identifier, and observed implementation instead of trusting its labels. For permission/privacy, follow principal → authorized object/data → loaded object → projection/use and reject cross-resource sensitive-data exposure as a normal Rule. Check whether permission or security boundaries, irreversible effects, money/entitlement ownership, transaction/idempotency constraints, retry/recovery guarantees, external contracts, sensitive data, or shared cross-domain contracts are accurate and not overstated. Do not discover every adverse branch or require a verification target for general context docs. An approved implementation-basis change must still state its required adverse outcome or verification condition when applicable. For an external contract, require authoritative local or user-approved provider evidence only when the docs or approved change relies on that guarantee.

FAIL when a documented high-risk contract is contradicted or overclaimed, its binding trace is missing/stale, its owner or non-obvious constraint is missing in a way that misleads change impact, or an approved implementation-basis requirement omits a required adverse outcome or verification condition. When the trace records `observed_conflict: true` and authoritative revision and target applicability are both verified, apply the owner conflict precedence from `change-judgment-policy.md`; do not downgrade it merely because the consumer has no local restatement. Verified status without an observed conflict does not itself choose the verdict. Keep `confirmation_needed` when applicability is unresolved. Do not FAIL a general context atom merely because an unmentioned refusal, failure, side effect, rollback, recovery path, or test case exists in source. Require a structured matrix only when the alternatives themselves are important durable contract context that prose cannot explain reliably.

Do not repeat the complete domain review. A risk reviewer PASS is additional evidence and cannot replace the required development-quality reviewer PASS. Persist a decision comparison table only when the risky alternatives cannot be judged reliably from concise findings.

Do not turn incidental risk discovery into a retained audit backlog. Reapply candidate admission before asking the writer to retain a newly discovered adverse path; the risk reviewer cannot expand managed-doc scope merely because a source surface is dangerous. A routine FAIL report keeps only concise blocking findings under the findings-only contract; detailed attack paths, fixture combinations, and non-blocking defect inventories are not persisted in managed docs or routine review artifacts. A materially serious incidental issue may be summarized to the user, but a complete security or defect audit and retained report require separately accepted scope.

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

Independently inspect the current managed docs and operation inventory. Compare glossary source-of-truth terms with domain context and Atom ownership, inventory disposition/owner with retained Atom and graph projections, canonical root decisions/Gaps with consumer references, and final candidate admission with retained Atom/AID content. Upstream PASS reports and evidence indexes may guide navigation but cannot establish this verdict.

Also check cross-domain ownership, duplicate responsibility, graph consistency, shared payload/state/storage/permission/integration contracts, changed evidence after domain PASS, accepted-scope reporting, and baseline eligibility when applicable. Every newly run domain review uses the operation's `source_commit_observed`; if relevant source or a reviewed semantic basis changed after review, open or consume the affected closure and reopen affected bundles before PASS.

For `initial-baseline`, verify the latest selection preflight matches the final queue, binding traces, and candidate-linked risk references; unscoped docs structure is valid; every project-native feature area was considered; obvious high-impact owners were documented or excluded with a reason; and every selected domain/risk review PASSed at the same source commit. Reapply candidate admission to every retained selected candidate; dormant/unreachable source, risk-shaped code, or an existing AID is not by itself a retention basis. Do not require every product behavior or aggregate to have a disposition. After this reviewer PASS is recorded as the final baseline gate, run request-bound baseline validation. Let this review also satisfy `semantic-review-proof.md`'s challenge only when its agent, raw inputs, blindness, current basis, and receipt qualify.

For `baseline-diff-refresh`, verify the complete old-to-new diff and ownership/graph/criteria impact expansion, impacted bundle reviews at the new commit, and the recorded rationale for carrying each unaffected bundle class from the trusted prior baseline. Do not claim carried reviews ran at the new commit.

Do not mechanically repeat every unchanged domain checklist or rediscover its source. If the current-corpus comparison exposes a local admission, depth, fidelity, or risk-routing defect, reopen that affected bundle; final review remains a safety net rather than ignoring a real defect because it is local. Apply the rerun table below, rerun the writer only when selected output or documented meaning changes, run only impact-selected reviewers, resolve closure, and then rerun this reviewer against the corrected current corpus.

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
| Source locator/evidence index correction with unchanged documented claim | version-5 selection preflight, then narrowed source-evidence check by the development reviewer |
| Intent, important context, rule/contract, ownership, approved verification condition, or judgment label | development-quality reviewer for affected bundle(s) |
| Risk-trigger, binding-trace, or candidate/Atom route change | version-5 selection preflight, then development-quality and applicable risk/contract reviewers on the corrected revision |
| Adverse branch, permission, destructive effect, transaction/idempotency, recovery, sensitive data, or external contract | risk/contract reviewer; also development reviewer when the documented decision changed |
| Atom boundary, owner, edge type/target, shared contract meaning, or glossary source of truth | development reviewer for affected bundles plus affected-closure integration reviewer when its prior basis changed |

Graph `reason` wording or inventory count alone does not trigger semantic review when relationship meaning and ownership are unchanged. If either changes meaning, route it as a shared-contract/ownership change.

A reference stabilization, queue-time wording removal, or `generalize` correction is not automatically risk-neutral. Reuse an existing risk PASS only when the development reviewer independently confirms that every candidate-linked trigger, risky contract meaning, owner/route, adverse behavior, and evidence basis is unchanged. Record that concise finding basis with the correction. If any dimension changed or remains uncertain, include the risk reviewer. The correction mode alone never decides rerun scope.

When that impact is knowable only from the corrected result, use the provisional development-gate transition in `semantic-review-closure.md`. A development FAIL or uncertainty expands the still-open invalidation before any corrected-basis PASS is recorded; it does not retroactively treat the old risk PASS as sufficient.

- After a FAIL, revise the affected bundle and run only the checks selected above.
- A post-PASS meaning change first opens `semantic-review-closure.md`; record only affected PASSes as stale and do not reuse them until their required rerun succeeds at the corrected basis.
- When `remove` or `merge` changes candidate disposition, expected Atom keys, risk references, or traces, rerun version-5 selection preflight before the writer or semantic rerun.
- Do not rerun unaffected PASS results or a complete domain review for evidence-only correction.
- Do not start the next sequential bundle until every reviewer applicable to the active bundle PASSes or a user decision is required.
- Reviewer FAIL is not completion and is not a Goal blocker when it can be corrected inside accepted scope, including removal of unchanged output created by the current operation.
- Ask the user only when PASS requires a user decision, an existing-Atom action absent from the approved manifest, an artifact ownership/hash conflict, or a separately authorized migration, push, or external action. Execute an exact approved delete/merge without repeated approval.
