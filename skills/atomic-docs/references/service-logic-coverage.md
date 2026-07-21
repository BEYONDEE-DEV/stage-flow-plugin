# Service Logic Coverage

## Contents

- [Responsibility](#responsibility)
- [Implementation Context Selection](#implementation-context-selection)
- [Current Contract Evidence](#current-contract-evidence)
- [Accepted-Scope Exploration](#accepted-scope-exploration)
- [Proportional Depth](#proportional-depth)
- [Conditional Risk Depth](#conditional-risk-depth)
- [Source Fact Fidelity](#source-fact-fidelity)
- [Atomic Docs Goal Boundary](#atomic-docs-goal-boundary)

## Responsibility

This reference is the normative owner of implementation-context selection, proportional documentation depth, accepted-scope source exploration, semantic risk triggers, and source fact fidelity. `atom-format-and-judgment.md` owns atom shape and AIDs; `change-judgment-policy.md` owns judgment labels and finding evidence; `docs-generation-flow.md` owns Goal sequencing; `shared-contract-readiness.md` owns version-4 local/shared routing and bounded closure state.

## Implementation Context Selection

Atomic docs orient development decisions; they are not a source index, product-behavior specification, source replacement, or default security audit. Select source-established context when at least one of these signals applies:

- the purpose, owner, boundary, or source location is difficult to recover from one obvious place
- misunderstanding a business or operational rule could change a development decision
- a shared or external contract, cross-domain dependency, or source-of-truth owner affects change impact
- a non-obvious implementation constraint, ordering requirement, or side effect is important before editing
- an approved requirement or material unresolved decision needs a durable home

Do not select a behavior merely because a route, field, branch, state, exception, test, or source file exists. Exact behavior remains in source unless one of the signals above makes it useful implementation context.

After inspecting the smallest source anchors needed to judge a candidate and before writing an atom, assign one disposition with a concise basis:

- `write`: the candidate has an independent durable purpose, owner, rule, contract, constraint, approved change, or unresolved decision that meets a selection signal
- `merge`: the context is useful but has no independent ownership or change boundary, so it belongs in an existing `write` candidate
- `drop`: reopening source is sufficient and the candidate adds no durable decision context

An approved domain may need only its domain context atom and no separate behavior atom. Domain approval, source volume, risk-shaped code, or an available method does not create a minimum Atom count. Dormant or unreachable code is `drop` by default. Retain it only when it constrains a reachable consumer, preserves an active shared/external compatibility contract, is required for operational recovery, or is part of an approved activation change. A possible future use or destructive method name is not enough.

Reapply this admission decision when later source inspection reveals another fact. A reviewer must not turn an unselected fact into required managed-doc detail merely to make source coverage more complete.

Before a required final integration/baseline review, reapply admission to the operation's retained selected candidates, or only the affected candidate closure for a non-baseline operation. Confirm each still has a current durable selection basis. Existing file length, AID count, risky code, destructive names, or prior reviewer PASS cannot preserve a dormant/unreachable candidate by themselves. In version 4, 3, or 2, a late `write→merge|drop` correction follows `semantic-review-closure.md` before its prior PASS is reused; a legacy operation uses its recorded correction/review flow without adding closure state.

## Current Contract Evidence

A selected source-established context claim may describe a purpose, result, local boundary, important rule, state/effect, integration, owner, or constraint supported by a reachable production path and, when available, behavior-relevant tests, schemas, settings, or local API contracts. It may be documented without separate user approval. AI authorship alone does not make the meaning inferred or create a Gap; a method name, field annotation, or test name alone still does not establish runtime behavior.

Reachability or repetition alone does not make behavior a normal contract. An inconsistent branch, violated local invariant, accidental fallback, unsafe bypass, or source quirk without consumer/operational meaning remains implementation context or a differential finding under `atom-format-and-judgment.md`; it must not be normalized merely because the current code executes it.

Trace documented current context through `Current Implementation` source locators and the applicable revision: the project-wide source baseline for a reviewed context set, or operation-local `source_commit_observed` for targeted/partial work. This establishes the basis of the claims actually made. It does not mean every source behavior is documented, product policy is approved, or the behavior is a future required change.

`Intent` may state the smallest functional purpose supported by entry points, outcomes, ownership, and integration use, but must not present inferred product strategy or necessity as user-approved intent. Create a Gap only when competing purpose interpretations would materially change an outcome, boundary, rule, requirement, or implementation judgment. Section placement and defect routing are owned by `atom-format-and-judgment.md`.

For each selected context candidate, record only the applicable context needed to answer: why this area exists, where its important implementation lives, who or what owns it, which non-obvious rule or contract matters before changing it, and what other area may be affected. A short atom may answer only a subset when the others are obvious or immaterial.

Inputs, outputs, authorization, validation, branches, state transitions, persistence, external calls, events, failure, retry, fallback, and recovery are not a completion checklist. Include one only when it is an important rule, shared/external contract, non-obvious constraint, or accepted implementation-basis requirement. A general source-context atom does not need an observable verification target. A changed required AID used by Atomic Impl or explicit compliance keeps the verification contract from `atom-format-and-judgment.md`.

`Intent` owns only why the atom exists. `Outcomes` gives the smallest normal result needed for orientation, `Boundaries` records a meaningful ownership or handoff boundary, and `Rules` preserves only important non-obvious rules or contracts. `Current Implementation` points to key source anchors and constraints. Do not fill a section merely because the heading exists, and do not narrate every function call, framework callback, DTO copy, component split, query mapping, or branch whose meaning is clear from source.

Context atoms preserve domain-wide purpose, outcomes, vocabulary, ownership, included/excluded capabilities, and adjacent-domain boundaries. Behavior atoms reference that shared context and keep only behavior-local boundaries in their own `Boundaries`; context atoms do not absorb or enumerate concrete rules and workflow boundaries that need independent change or judgment.

## Accepted-Scope Exploration

Explore the accepted source scope enough to identify durable domain boundaries, shared/high-impact owners, and context candidates that meet the selection signals above. The operation inventory closes only the context candidates accepted into its write queue; it is not a disposition table for every source behavior.

A selected context candidate may span routes, controllers, services, repositories, UI components, settings, schemas, tests, jobs, or integrations. Cite the smallest useful source anchors and do not require a separate inventory row or AID for each surface. Tests and configuration are evidence when they clarify a documented claim, but behavior-neutral wiring is not documentation work.

For a full refresh, consider every project-native feature root and continue beneath rejected broad roots far enough to find concrete durable boundaries and high-value context. Do not enumerate or disposition every aggregate. For targeted work, inspect the requested area plus adjacent owners or contracts needed to understand impact. A partial operation must not be reported as a project-wide context refresh.

An endpoint list, class list, source path list, or one-line file summary is not useful implementation context. Source identifiers become useful when the docs explain why the location, owner, constraint, or contract matters.

## Proportional Depth

Document until the applicable questions can be answered:

1. Why does this documented area exist, and where should a developer start reading?
2. Which owner, important rule, shared/external contract, or non-obvious constraint matters before changing it?
3. Which other domain or source-of-truth could be affected or conflict?
4. Which approved change or unresolved decision, if any, needs an explicit development judgment?

Stop adding detail once the reader can navigate to source and recognize the important development context. Exact fields, payload mappings, ordinary branches, routine state mechanics, error paths, function decomposition, library choices, framework conventions, DTO copying, and component structure may remain in source. Also stop before a forensic defect inventory, attack-scenario catalog, exhaustive failure reproduction, or docs-only implementation specification. When a meaning is already complete in its owning section, another section needs a short reference, not a paraphrase.

Review must FAIL when a documented claim is false or unsupported, when the atom's stated scope hides a known shared/external contract, owner, or non-obvious constraint whose omission would mislead change impact, or when an approved implementation-basis requirement remains ambiguous. Review must not fail because ordinary fields, branches, state transitions, failure outcomes, or verification targets are absent from general source-context docs. Reopening source for exact behavior is expected.

Do not use atom count, file count, line count, or source-surface count as a quality threshold. A short atom can preserve every relevant decision, while a long source narrative can still be shallow.

Use tables or structured lists only when compact prose would obscure independently varying durable decisions. For example, a matrix may be useful when several states have different product-authorized actions or several failure types have distinct contractual recovery behavior. The matrix must itself express a product or contract decision; do not use it merely to enumerate a Cartesian test plan. Do not require field, payload, branch, state, and failure matrices as a fixed set.

For frontend/UI context, include fields, routes, screen states, access guards, persistence, payload transforms, feedback, or design constraints only when they are important to ownership, a non-obvious product rule, a shared contract, change impact, or an explicitly requested style. Display-only fields and exact CSS values are normally source-level details.

For backend/API/service/job/integration context, include payload fields, authorization, validation, domain policy, transaction/idempotency, persistence, schema, events, integrations, or recovery only when they are important before changing the documented area. Their presence in source alone does not require documentation.

## Conditional Risk Depth

Apply the independent risk/contract reviewer when a selected context candidate or approved implementation-basis change includes one of these triggers:

- authentication, authorization, security, privacy, or sensitive-data handling
- money, billing, refund, settlement, quota, or entitlement
- delete, approve, publish, irreversible mutation, or destructive operation
- external integration, webhook, event delivery, or third-party dependency
- irreversible, high-impact, or concurrency-sensitive state transition; transaction boundary; idempotency; retry; or recovery
- shared payload, storage, permission, integration, or policy contract used by another domain

For version 4, give every selected trigger the local/shared disposition from `shared-contract-readiness.md`. A risk trigger remains `local` unless changing its owner or meaning can invalidate a direct consumer bundle. Only that reference's five bounded high-fan-out kinds enter shared-contract closure; transaction order, retry details, projection fields, and dangerous-looking source do not become shared contracts merely because this list triggered risk review.

Ordinary CRUD, reversible preference persistence, or a routine state field is not a trigger by itself. Source presence alone does not start a risk audit. For a triggered context, record the high-impact owner, contract, or non-obvious constraint that matters to change impact and verify claims actually made. Require an adverse outcome and verification target only for an approved implementation-basis requirement that specifies them. Do not discover or preserve every adverse branch, actor/input/state/failure combination, or attack path. Add a matrix only when the alternatives themselves are durable contract context that prose would make misleading.

For an external contract, use authoritative local or user-approved provider evidence such as a versioned schema/specification, SDK contract, fixture, or contract test when available. Record `confirmation_needed` only when the unavailable or conflicting external guarantee prevents the accepted implementation or review judgment; do not create a Gap merely because the remote implementation is outside the repository.

Do not cross into another repository or provider to build a general defect inventory. Expand beyond accepted local evidence only when a retained claim's owner, shared/external contract, or change impact cannot otherwise be judged reliably. A field-level UX improvement, display fallback, incidental exception possibility, or source asymmetry that does not block trustworthy context remains source-level observation or a concise user report, not a managed Gap.

## Source Fact Fidelity

The context-quality reviewer compares claims actually made in managed docs with the relevant reachable source path. It does not audit every related behavior for omission. Do not infer runtime behavior from a field annotation, method name, type, endpoint name, or service class alone.

When a documented claim depends on validation, refusal, defaulting, fallback, exception, read-only behavior, or storage effects, inspect the relevant path far enough to verify that claim. Record only distinctions that are useful context; do not expand the check into a complete behavior inventory.

If source allows a fallback instead of refusing input, preserve it as a normal contract only when the reachable evidence supports that interpretation. Do not describe a path as recovered when source can throw an unhandled runtime exception. A non-blocking anomaly may remain concise `Current Implementation` context; if source conflicts with an approved requirement or a source-established current contract, route the differential finding under `change-judgment-policy.md`. Lack of product-intent proof alone does not create `confirmation_needed`.

Apply finding fields, label precedence, and AID-or-owning-section evidence from `change-judgment-policy.md`. This source-fidelity contract adds only that evidence must reach the relevant behavior path and that missing tests or possible runtime failures become gaps only when their absence prevents the accepted implementation or review judgment.

## Atomic Docs Goal Boundary

The Codex Goal after combined criteria/domain/scope approval is an execution scope for the accepted docs operation. It does not replace the approved criteria, domain boundaries, selected write scope, atom content, judgment labels, source evidence, user review, or baseline metadata.

Do not write Goal status into atom meaning. If execution is waiting or blocked, preserve that state in operation state or the change plan. A correctable review FAIL is not Goal-blocked; revise and rerun the applicable reviewer first.
