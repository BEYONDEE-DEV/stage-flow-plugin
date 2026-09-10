---
name: simple-workflow
description: "Use when the user explicitly asks to use Simple Workflow, simple-workflow, `.simple`, or the Simple Workflow plugin, or when an active `.simple` session pointer exists. Runs a plan-centered workflow with Astra planning and coordination, one independent plan challenge, explicit approval, and bounded Astra Light implementation delegation."
---

# Simple Workflow

Use this skill to keep Codex work tied to a single human-readable plan while preserving an internal review record. The default role split is `gpt-6-astra` at the main agent's existing effort for planning/coordination and a separate `gpt-6-astra` subagent with explicit `reasoning_effort: "low"` (Astra Light) for implementation. Independent reviewers inherit the main agent's model and effort, not the implementation worker's Light setting. Model names in these instructions do not change the model running an existing agent.

## Role Routing

Decide the role before resolving or activating any request:

- A main agent owns planning, the independent plan challenge, user decisions, approval, Goal and `.simple` metadata, implementation dispatch, final reviews, and completion. Read [references/role-handoff.md](references/role-handoff.md) before planning or dispatching implementation.
- An agent explicitly dispatched as the implementation worker must immediately follow the worker contract in [references/role-handoff.md](references/role-handoff.md) and stop reading this file as a coordinator procedure. An inherited active `.simple` pointer does not make that worker create or select a request, repeat planning, seek approval, manage a Goal, update workflow metadata, or certify completion.
- An agent explicitly dispatched as an independent reviewer must immediately follow the reviewer contract in [references/role-handoff.md](references/role-handoff.md) and stop reading this file as a coordinator procedure. It inspects only the supplied request, plan, sources, diff or outputs, and evidence; it never activates nested workflow state or manages the Goal.

Respect an explicit user model choice over these defaults. The skill cannot switch the already-running main agent to Astra: the user or host must start/select `gpt-6-astra`. If actual main-model identity is unavailable, say so once while establishing roles; do not claim Astra or repeatedly ask on every continuation. If exact requested role dispatch is unavailable, report the limitation and ask for a decision instead of silently substituting another model.

## Core Rule

Follow exactly this sequence:

1. Listen to the user's requirements.
2. As the main planner/coordinator (`gpt-6-astra` by default), inspect the relevant original project sources and infer intent, outcome, boundaries, assumptions, critical alternatives, and uncertainties. Ask the user only about unresolved choices that can materially change the plan; decide reversible implementation details from evidence.
3. Write `plan.md` from the resolved request. Include the observable outcome, completion criteria, evidence and rationale, change targets, execution order, validation, and conditions that require replanning. Describe outcomes and constraints without prescribing every implementation step.
4. Run one bounded `Independent Plan Challenge` with a subagent. It covers intent quality, question depth, project fit, alternatives, risks, and plan completeness in one review, then records compatible results in `review.md`.
5. For a non-material plan defect, revise and re-review. For a material requirement or scope issue, give the user the fact, impact, and decision needed; revise only after the decision and repeat the same independent review for the changed plan.
6. If the requested deliverable is the plan itself, validate the reviewed plan, set only the selected session pointer's optional `active` field to exact boolean `false`, and verify that write before presenting the plan. Approval to finalize or accept a plan-only deliverable is not authorization to create a Goal or implement it.
7. When the agent determines from conversation context that the user clearly authorizes execution of write work or a read-only analysis, first persist approval for the current reviewed fingerprint, then reconcile the Goal with `get_goal` and call `create_goal` at most once.
8. For approved code-changing or other write work, dispatch one bounded implementation worker as actual `gpt-6-astra` with explicit `reasoning_effort: "low"`; the worker chooses implementation mechanics, changes only its owned scope, tests the affected behavior, fixes in-scope failures, and returns evidence. For read-only requests, do not dispatch an implementation worker.
9. The main agent inspects the result and original sources, maps every requirement to actual evidence, runs both post-execution review perspectives, drives any fix/revalidate cycle, passes the completion pre-gate, completes the Goal, and then closes local request metadata.

Natural-language approval intent belongs to the agent applying this skill. Hooks must not classify approval with keyword or regular-expression matching. A `UserPromptSubmit` hook may report request readiness, while `PreToolUse(create_goal)` only enforces structural prerequisites after the agent has already determined that the user approved execution.

Do not add approval files, requirements files, goal files, implementation logs, completion summaries, source-requirements, analysis files, service-plan files, plan-compliance reviews, code-review files, Direct Parallel queues, Evidence Map, Inventory matrices, or subagent-only review protocols.

## Request Storage

Resolve the workflow root first, then keep request state under that root:

```text
.simple/
  index.json
  sessions/<session-id>/current.json
  requests/<request-id>/
    state.json
    plan.md
    review.md
```

`index.json`, `current.json`, `state.json`, and `review.md` are internal metadata or internal review records. The only required human workflow artifact is `plan.md`.

Use request IDs in this form: `YYYYMMDD-HHMM-short-slug`.

### Workflow Root Ownership

The workflow root owns the entire `.simple` tree for one request. Resolve it before reading or
writing `index.json`, a session pointer, or request artifacts, and keep every artifact for the
request under that one canonical root.

Use these modes and this precedence:

1. An explicit workflow root is authoritative and is not rediscovered.
2. For a user-declared bundle or a confirmed task spanning at least two independent repositories,
   use the plugin-bundled checker's read-only `--resolve-root --multi-repo --start <cwd>` mode. It
   may select a bundle automatically only from an exact `slot.path` in an ancestor
   `.stageflow-worktrees/slots.json`; if no valid exact match exists, require an explicit root.
3. For automatic hook continuation from a child repository, use the same resolver. Select the
   manifest bundle only when its `.simple/sessions/<session-id>/current.json` actively points to the
   same request. An inactive pointer remains available only for explicit request selection or Goal
   ownership checks and does not promote a new single-repository request to the bundle.
4. Otherwise preserve the nearest single-repository root. Merely being inside a manifest-backed
   slot does not promote a new or pointerless single-repo request to the bundle.

Whenever the agent creates or selects a request, record the resolved canonical absolute root as
`workflow_root` in that session's `current.json`. This optional field is a
session-bound consistency assertion, not a discovery mechanism: the pointer lives under the root it describes. Existing
pointers without the field remain valid. Hooks read but never backfill or rewrite it.

`current.json.active` is also optional and must be exact JSON boolean when present. Missing or
`true` means the pointer participates in automatic continuation. `false` preserves the selected
request for explicit reuse while preventing it from capturing unrelated prompts or Stop events.

Never infer a bundle from a path shape such as `worktrees/<name>` or from an individual
repository's `git rev-parse --show-toplevel`. In a confirmed multi-repo request, the bundle root—not
any child Git top-level—is the target project for Simple Workflow purposes.

When the canonical bundle and a child repository contain the same request id, compare
`plan.md`, `review.md`, and `state.json` without changing either copy. If all three files exist and
are byte-identical, warn with both paths and continue from the canonical bundle. If any file is
missing or different, report both paths and block only the in-scope Simple Workflow `create_goal`;
UserPrompt and Stop remain non-blocking, and unrelated Goal calls prepass. Never automatically
move, merge, align, or delete duplicate artifacts. Tell the user to remove the stale child copy or
align it manually, then allow the same canonical request and fingerprint to be retried.

Allowed phases are `plan`, `review`, and `completed`.

Use `state.json` as the local workflow source of truth. `current.json` and the selected `index.json` request entry must mirror its phase. New requests use integer `workflow_version: 2`, exact integer `intent_challenge_version: 1`, `plan_approval_status: pending|approved`, and may record `goal_status` as `pending`, `active`, `completing`, or `completed`. The intent marker means the request must use the compatible structured results from the Independent Plan Challenge. Marker-free existing v2 and legacy requests retain their previous review schema; any other marker value is invalid. After Goal creation, `goal_plan_fingerprint` permanently identifies the plan fingerprint named in the original Goal objective, while `approved_plan_fingerprint` identifies the latest plan explicitly approved for execution. Requests without `workflow_version` are legacy requests; unknown versions are invalid. Readers must accept legacy `id`/`request_id` and `phase`/`status` key variants, but the selected request id and phase values must agree.

The phase transitions are:

```text
plan -> review -> completed
```

- Enter `review` only after the current `plan.md` has a passing subagent review and matching fingerprint.
- Keep phase `review` while approval is pending, while approved work is executing, and during completion preparation. The only allowed v2 state triples are `plan|pending|pending`, `review|pending|pending`, `review|approved|pending`, `review|approved|active`, `review|pending|active`, `review|approved|completing`, and `completed|approved|completed` in `phase|plan_approval_status|goal_status` order.
- Enter `completed` only after approved work, validation, and both post-execution reviews pass and `update_goal(status="complete")` succeeds.

## Artifact Rules

For `workflow_version: 2`, `plan.md` must include `# Plan`, `## Summary`, `## Outcome And Completion Criteria`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`. The outcome section must name the user-visible or system-visible final state and how it can be observed. The requirements table must use `Requirement | Plan | Completion Evidence`; every `REQ-###` needs a concrete execution plan and a concrete planned evidence source. The plan also captures evidence and rationale for material choices, useful execution order, and conditions that would require replanning. Legacy requests keep their existing plan shape.

## Shared Planning And Review Principles

Use the same principles when writing `plan.md`, independently challenging it with a subagent, and reviewing implementation or read-only results:

- Preserve the user's confirmed intent and the approved scope.
- Give every `REQ-###` a concrete, verifiable execution plan.
- Define the observable outcome first and tie every `REQ-###` to planned and actual completion evidence.
- Tell the user about relevant flow problems discovered while planning or implementing, even when they were pre-existing or outside the requested change.
- Clearly separate in-scope problems from out-of-scope issues; do not fix out-of-scope issues without user approval.
- Keep validation tied to the real affected product, feature, state, data, user, command, hook, or validator flow.
- Write human-readable artifact and review body text in Korean while preserving fixed control tokens.

`## Flow Check` in `plan.md` must state whether the affected product, feature, state, data, user, command, hook, and validation flows are coherent after considering the planned changes. It must tell the user about any relevant flow problem discovered during planning, even when the problem was pre-existing and was not caused by the requested change. Report flow breaks such as broken user journeys, inconsistent state transitions, missing failure or retry paths, contradictory behavior across entry points, data moving through the wrong owner, or a validation path that no longer proves the real flow. If a discovered problem is outside the requested scope, say so explicitly instead of hiding it.

`review.md` is internal. It must include `# Review`, `## Reviewed Plan Fingerprint` with `Reviewed Plan Fingerprint: sha256:<hex>`, `## Reviewer`, `## Verdict` whose complete trimmed body is exactly `PASS`, `## Blocking Issues` with a blocking-specific no-issue value such as `No blocking issues`, `None`, or `차단 없음`, and non-empty `## Flow Check` and `## Question Depth Check` results. Requests with `intent_challenge_version: 1` additionally require `## Intent Challenge Check`: its `Finding | User Decision Or Resolution | Verdict` table records each material finding once with a unique `IC-###`, a substantive Korean decision or resolution, and exact `PASS`; when there were no material findings it contains one `NONE` row with the review basis. `### Intent Challenge Final Verdict` must be exact `PASS`. These existing headers and markers remain validator-compatible views of one Independent Plan Challenge, not separate intent and per-depth reviews. A non-blocking flow observation does not invalidate a passing plan review. The internal review must use `Shared Planning And Review Principles` and verify that user decisions, intent, original project evidence, and `plan.md` agree; its flow result must judge whether the plan exposes all relevant flow problems to the user and keeps the affected flow coherent, not merely whether the Simple Workflow procedure was followed.

After execution reviews pass, append `## Completion Review` to the same `review.md`. It records the latest completion plan fingerprint, exactly one actual-evidence row and exact `PASS` verdict for every planned `REQ-###`, observable outcome evidence, and an exact final `PASS`. Do not create another evidence artifact.

Do not ask the user to read `review.md` as part of the normal workflow. Summarize the review result and tell the user when the plan is ready for approval.

## Language Policy

Write human-readable artifact body text in Korean. This applies to `plan.md` sections such as `## Summary`, `## Requirements Coverage`, `## Change Targets`, `## Flow Check`, `## Validation`, and `## Out Of Scope`, and to internal `review.md` body text such as blocking, flow, question-depth, Intent Challenge resolutions, and notes.

Keep fixed validator contract tokens unchanged when needed: headings, table column names, `REQ-###`, `PASS`, `FAIL`, `sha256`, file paths, commands, code identifiers, and validator status/control values may remain in English or code form.

## Operating Flow

At the start of a main-agent Simple Workflow turn, resolve the workflow root using `Workflow Root Ownership`,
then inspect `<workflow-root>/.simple/sessions/<session-id>/current.json` when it exists. When the
skill trigger applies and the pointer is missing, invalid, inactive, or completed, the skill-applying agent
creates or selects a request under that same root, writes its canonical absolute `workflow_root` to
the selected session pointer, sets `active: true`, and then continues. Hooks do not infer activation from prompt strings.
An inactive pointer alone never triggers activation or creation. Keep it inactive for an unrelated
follow-up or plan-finalization acknowledgement; an explicit reference to executing or resuming its
stored plan may select that same request even without repeating the Simple Workflow name. An
explicit Simple Workflow request for distinct work creates or selects a different request instead.

If an active session pointer exists for a request in `plan` or `review` phase, treat follow-up user messages as Simple Workflow continuation even when the prompt does not mention the plugin again. Short answers, confirmations, corrections, and renewed requests such as `응`, `맞아`, `그렇게 해줘`, or `수정해줘` must continue from the active request and follow the same `plan.md`, internal review, validator, and approval rules. A completed request must not capture unrelated follow-up prompts; explicit Simple Workflow invocation starts or selects another request.

For a plan-only result, keep the reviewed request, `review|pending|pending` state, empty approval and
Goal fingerprints, review, and index entry intact. After `--phase review` passes, confirm the same
session, request, and canonical root; write only `current.json.active: false`; read it back as exact
`false`; and rerun `--current --phase review`. Do not claim the session was deactivated if any write,
identity check, read-back, or validation fails. `--request --phase review` may validate the preserved
plan independently, but it does not read the session pointer and cannot prove deactivation.

An inactive pointer stays inactive for unrelated follow-ups. Reuse it only when the user explicitly
selects that request or asks to execute that plan: write `active: true`, verify the current original
sources, plan, review, and reviewed fingerprint, then determine explicit execution approval and use
the existing Goal gate. Reactivation alone and ordinary approval of the plan as a deliverable are
not execution approval.

Before writing `plan.md`, inspect the relevant original project sources enough to understand the intent, expected outcome, boundaries, assumptions, affected-flow risks, and credible alternatives. Ask a question only when its answer can materially change the goal, scope, expected outcome, ownership, sequencing, irreversible risk, or validation standard. Infer reversible low-risk details from evidence and record a consequential assumption or rationale in the plan. Do not ask preference questions that only choose between behaviorally equivalent implementation details.

## Independent Plan Challenge

After drafting `plan.md`, run one bounded independent subagent review for that plan fingerprint. Give the reviewer the user's request and decisions, the candidate plan, the canonical project root, and relevant original source paths so it can verify facts directly. Do not give only the planner's conclusions. Ask it to challenge, in one pass:

- whether the plan addresses the underlying problem and observable outcome;
- false assumptions, contradictions, omissions, unclear success conditions, and project mismatches;
- affected users, systems, owners, responsibility boundaries, sequencing, and state or data flow;
- critical alternatives and whether the rationale for the chosen direction is supported;
- failure paths, edge cases, irreversible effects, material risk, and validation quality; and
- whether any unresolved user question could materially change the plan.

This is the sole pre-approval plan challenge. Do not run separate Intent Challenge, `대분류`, `중분류`, or `소분류` reviewer checkpoints. The reviewer identifies evidence-backed findings; it does not replace the user's intent, dictate code mechanics, or authorize a requirement change. A style preference or equivalent implementation choice is non-blocking.

For a material finding, the main agent tells the user the supporting fact, likely impact, critical alternatives, and decision needed. Never silently apply the reviewer's preferred alternative. After the user's correction or explicit tradeoff acceptance changes the candidate plan, repeat the same independent challenge for the new fingerprint. For a non-material plan defect, the main agent may repair and re-review it without another user round. A repeated finding with unchanged code, plan, or evidence requires the main agent to resolve the cited evidence or explain concretely why it is non-blocking; never force `PASS`, waive it arbitrarily, or stop only because an iteration quota was reached.

Do not create a challenge artifact. Preserve the result in the existing `review.md`: `## Intent Challenge Check` records material intent findings and their user decisions (or one substantive `NONE` row), while `## Question Depth Check` records whether any plan-changing question remains. These are compatibility fields populated by the same Independent Plan Challenge, not separate reviews. Keep every material finding as one unique `IC-###` row with a substantive Korean resolution and exact `PASS`; `### Intent Challenge Final Verdict` must be exact `PASS` only when none remains unresolved.

Before moving to the next step, run the plugin-bundled validator against the target project root. The validator lives under the Simple Workflow plugin root, not under the target project's `scripts/` directory:

```powershell
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase plan
python <plugin-root>/scripts/validate_simple_workflow.py --root <target-project-root> --current --session-id <session-id> --phase review
```

Treat validator failures as the next action. Fix the artifact or ask the user for the missing decision.

## Goal Gate And Recovery

After review passes, finish the plan-only deactivation sequence above and stop before this gate when the requested outcome is plan-only. Otherwise the agent—not the hook—decides whether the user's latest message clearly approves execution. Words such as `approve`, `proceed`, `승인`, `진행`, or `실행` are examples, not a regular-expression contract; negations, status questions, quoted text, and unrelated uses are not approval.

Immediately after recognizing approval and before `get_goal` or `create_goal`, durably set `plan_approval_status: approved` and `approved_plan_fingerprint` to the current reviewed plan fingerprint. If that write fails, do not call `create_goal`. This `approved + pending` state is the retry-safe proof that the exact plan was authorized.

Before calling `create_goal`, call `get_goal` and reconcile it with the selected request id and reviewed plan fingerprint:

- If no Goal exists, call `create_goal` with an objective naming the request id, exact `.simple/requests/<request-id>/plan.md` path, and reviewed plan fingerprint.
- If a matching Goal is already active, do not call `create_goal` again; repair local `goal_status: active` and continue the same work.
- If a matching Goal is already complete, do not call `create_goal` again; repair the local completed metadata.
- If another unfinished Goal exists, stop and report the conflict instead of replacing it.

The plugin `PreToolUse(create_goal)` hook is a structural gate only. Scope the gate only to Goal objectives containing an exact `.simple/requests/<request-id>/plan.md` path; mentioning Simple Workflow or `.simple` as a topic is not enough. Unrelated Stageflow or other `create_goal` calls must prepass. For an in-scope call, deny the tool unless the path's request id exactly equals the selected request, the selected request is in `review`, metadata is coherent, plugin-bundled review validation passes, the review, current plan, and objective fingerprints match, the review verdict is exactly uppercase `PASS`, and local Goal status is `pending`. V2 additionally requires `approved`, with the approved plan fingerprint matching the same plan; legacy requests retain their existing single-fingerprint gate. Do not write `goal.md`.

For every new Simple Workflow Goal, the objective must contain the canonical host-native absolute
`<workflow-root>/.simple/requests/<request-id>/plan.md` and its `sha256:<64-hex>` fingerprint,
each exactly once. Quote or backtick an absolute path that contains whitespace. The absolute plan
path bootstraps `create_goal` discovery when the hook process cwd differs from the workflow root;
it does not override canonical single-repo or bundle ownership. The hook binds the derived root to
the same session/request, checks optional `current.json.workflow_root`, applies the existing
resolver and duplicate policy, and only then runs the existing review/approval/fingerprint gate.

If an absolute Simple Workflow-like candidate is malformed, repeated, missing, stale, unreadable,
drive-relative, foreign to the execution host, non-canonical, symlinked, or conflicts with another
root/owner/source, fail closed and do not retry discovery from cwd. Only a Goal with no Simple
Workflow plan candidate prepasses as unrelated. Exact legacy relative
`.simple/requests/<request-id>/plan.md` objectives remain compatible only when the existing cwd and
session resolver already finds their root. This bootstrap applies only to `create_goal`;
UserPromptSubmit and Stop keep their existing non-blocking cwd behavior.

After `create_goal` succeeds for a v2 request, record the objective fingerprint as `goal_plan_fingerprint` and set `goal_status: active`; approval was already recorded and must not be rewritten. If `create_goal` fails, preserve `approved + pending` and retry with the same approval. If the post-success state write fails, use the matching active Goal request id and objective fingerprint returned by `get_goal` as authoritative on the next turn, repair `goal_plan_fingerprint` and Goal status, and never call `create_goal` again for recovery. Legacy requests keep the existing single-fingerprint behavior.

## Implementation Handoff

For an approved read-only request, the main agent performs the work and later applies the same evidence and completion gates without an implementation worker dispatch.

For approved write work, follow [references/role-handoff.md](references/role-handoff.md) and call the host's actual `spawn_agent` tool with `model: "gpt-6-astra"`, `reasoning_effort: "low"`, and `fork_turns: "none"` or a small positive turn count. Full-history forks cannot override model or effort. Pass `low` explicitly so the implementation worker does not inherit a higher main effort. An explicit user override for the implementation role takes precedence; changing the main effort alone does not change the worker's Light default. If the requested model/effort dispatch is unavailable, report that fact and wait for the user's choice; do not silently substitute or increase effort on retries.

Every first worker or reviewer handoff must include its explicit non-coordinator role and the canonical absolute path to `references/role-handoff.md` from the skill version the main agent actually loaded, with instructions to read the applicable contract before work. Resolve and verify that path directly; do not infer it from cwd, a relative path, or a guessed cache version. If it cannot be read, the delegated agent must stop and report the failure.

Give the worker the approved plan and fingerprint, canonical root, bounded ownership, raw source paths, outcomes, constraints, validation evidence, and replanning triggers. The worker owns implementation mechanics within those boundaries. The main agent may inspect while it runs but must not write concurrently to worker-owned paths. After the worker returns, verify the actual diff and original sources. Use the same worker through `followup_task` for evidence-backed, in-scope fixes and revalidation instead of starting another worker or retransmitting full history. After a material replan, the resumed handoff names the new approved plan fingerprint and changed boundaries explicitly; do not present the immutable Goal fingerprint as the worker's expected plan hash.

## Adaptive Execution And Material Replan

Keep execution flexible without silently changing the approved goal:

- A method-only adaptation changes implementation mechanics but preserves every approved requirement, scope boundary, expected outcome, owner, and validation standard. Do not rewrite `plan.md` or ask for another approval. Explain the deviation and prove equivalent or better completion evidence in both post-execution reviews.
- A material change modifies a requirement, scope boundary, expected outcome, ownership, irreversible risk, or validation standard. Stop before executing the changed work and tell the user what new fact was discovered plus the retry, goal-preserving fallback, or rescope choices.
- Before revising a material plan while the implementation worker is active, call the host's actual `interrupt_agent` capability and confirm the worker has stopped writing. Do not edit or redispatch against a new fingerprint while the worker may still be changing files under the superseded plan.
- Before editing a material plan, obtain the user's decision about the change. Then durably set `plan_approval_status: pending`, revise `plan.md`, repeat the internal review and `--phase review` validation, summarize the revision, and ask for explicit execution approval again.
- After a material replan decision, run the same single Independent Plan Challenge for the revised fingerprint; do not add separate intent or question-depth checkpoints.
- While a v2 plan is pending approval, `UserPromptSubmit` readiness must say that execution is on hold. `Stop` must still allow Codex to send the reapproval request; hooks must not decide the user's answer.
- After explicit reapproval, update only `approved_plan_fingerprint` to the current reviewed plan fingerprint, set `plan_approval_status: approved`, rerun `--phase review`, and continue the same active Goal. Never call `create_goal` again and never change the immutable `goal_plan_fingerprint`.

If the pending marker write succeeds but a later plan edit or review fails, remain pending and repair that sequence. If the user declines the material change, do not reduce scope silently; either continue the previously approved work when still valid or present a plan-preserving fallback. A rescope becomes executable only after revised plan review and explicit approval.

## Post-Implementation Review

After approved work and validation commands are complete, the main agent first inspects the actual diff or read-only outputs and the relevant original sources. Then dispatch bounded, read-only independent review covering the two perspectives below before the final user response. Both perspectives must use `Shared Planning And Review Principles`; one or more independent reviewers may cover them, but the implementation worker cannot self-certify completion. Reviewer handoffs include the canonical root, user decisions, approved plan, raw source paths, actual diff or outputs, and validation results. This gate applies to code-changing and read-only work.

1. `Intent Compliance Review`: compare the confirmed user intent, latest approved `plan.md`, actual diff when code changed, or actual outputs and commands when work was read-only, plus validation results. Its response must list every `REQ-###` with the actual evidence that proves it and identify any method-only adaptation. A missing requirement, scope violation, in-scope regression, or expected validation failure is blocking.
2. `Flow / Unexpected Issue Review`: inspect the affected user, state, data, failure or recovery, command, hook, and validator flows and independently challenge whether the evidence proves the observable outcome. Its response must cover every `REQ-###`; a test command alone is insufficient when it does not observe the real affected result. An in-scope or implementation-caused issue is blocking. If an issue is outside the user's intent, pre-existing, or requires expanded scope, the main agent tells the user before changing it.

For a blocking in-scope finding on write work, the main agent sends the evidence to the same implementation worker with `followup_task`, preserving its model and effort, waits for its fix, verifies the changed diff, reruns affected validation, and repeats both perspectives. For read-only work, the main agent corrects the output and follows the same revalidation cycle. Do not rerun already-passing checks when neither relevant code nor evidence changed. A repeated identical finding is resolved against concrete requirement and source evidence; reviewer disagreement is not settled by an arbitrary waiver, forced `PASS`, or iteration quota.

Keep requirement-to-evidence coverage in the bounded reviewer responses while reviewing. After both pass, the main agent consolidates their actual evidence into the existing `review.md` Completion Review; do not create a new artifact. A critical outcome that cannot be observed is a verification gap, not a pass. Obtain the smallest missing user-supplied evidence or present retry/fallback/rescope choices instead of claiming completion. Summarize the two review results in the final response. If an out-of-scope or pre-existing issue blocks safe completion, explain the blocker and wait for the user's decision.

## Completion And Partial-Failure Recovery

Complete only when every approved requirement has actual evidence, the observable outcome is proven, validation passes, and both post-execution reviews pass. Use this order:

1. While phase and mirrored metadata remain `review`, write the Completion Review into `review.md`, then run plugin-bundled validation with `--phase completion`. For v2 this requires the latest passing review, current completion fingerprint, exactly one non-empty actual-evidence row with exact `PASS` for every REQ, non-empty observable outcome evidence, exact final `PASS`, `plan_approval_status: approved`, and `approved_plan_fingerprint` equal to the current plan. Do not continue on failure.
2. While phase remains `review`, durably set `state.json` `goal_status: completing`. If this write fails, do not call `update_goal`.
3. Call `update_goal(status="complete")`; this is the first completed transition.
4. After Goal completion succeeds, set the selected `state.json`, session `current.json`, and matching `index.json` entry to phase `completed`; set `state.json` `goal_status` to `completed` while preserving both fingerprints and approval status.
5. Run plugin-bundled validation with `--phase all` and then give the final response. For backward compatibility, `--phase all` accepts an existing completed v2 request without Completion Review; if the section exists, it must be valid. Every new completion must pass step 1 first.

If `update_goal` fails, keep local phase `review` and `goal_status: completing`; use `get_goal` to determine whether the Goal remains active before retrying Goal completion. If Goal completion succeeds but local completion metadata fails, the durable `completing` marker records the recovery path: a matching complete Goal, or no unfinished Goal after completion was requested, means repair only local completed metadata and validation on the next turn. Never create a replacement Goal from `completing`. For read-only work, the same completion order applies after the two reviews compare the approved plan with actual outputs, commands, and validation results.

If any REQ remains unmet, do not label partial work complete. Retry in scope when safe, offer a fallback only when it preserves the approved outcome, or ask the user to approve a material rescope through the replan flow. Completion convenience never overrides the approved goal.
