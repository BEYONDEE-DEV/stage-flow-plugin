# Astra / Astra Light Role Handoff

Use this reference only to establish the planner/coordinator and implementation-worker boundary.

## Main Planner / Coordinator

The default main role is actual `gpt-6-astra`. A skill cannot replace the model of the running main agent: model selection belongs to the user or host. Respect any explicit user override. If the runtime does not expose the main model identity, report that limitation once when roles are established and avoid claiming that Astra is active.

The main agent owns:

- project inspection, intent and scope, critical alternatives and uncertainties, `plan.md`, and the independent plan challenge;
- user questions and decisions, approval judgment, Goal reconciliation, and every `.simple` metadata write;
- implementation dispatch, acceptance of worker evidence, final review/fix decisions, Completion Review, Goal completion, and the final response.

Keep file ownership exclusive while the worker is active. The main may inspect concurrently, but it must not edit the same worker-owned paths. After each worker turn, the main verifies the actual diff and relevant original sources rather than accepting a self-reported completion claim.

The main agent should decide from project evidence before asking questions. Ask only when an unresolved choice changes the outcome, scope, ownership, material risk, or validation standard. Plans state context, rationale, outcomes, constraints, affected areas, useful sequencing, validation, and replan triggers; they leave reversible code mechanics to the worker.

## Implementation Dispatch

Dispatch only after approval and Goal activation, and only for code-changing or other write work. Use the actual `spawn_agent` capability exposed by the host with:

- `model: "gpt-6-astra"`, unless the user explicitly chose another implementation-role model;
- `fork_turns: "none"` by default, or a small positive turn count only when those turns contain critical context that cannot be stated safely in the handoff;
- `reasoning_effort: "low"` explicitly (Astra Light), unless the user explicitly chose another implementation-role effort; do not inherit the main effort or silently increase it; and
- a unique bounded `task_name` and the self-contained message described below.

Do not use a full-history fork when setting `model` or `reasoning_effort`; the tool cannot apply these overrides to such a fork. If the host lacks model/effort-selectable subagent dispatch, the requested settings are unavailable, or dispatch fails, report the exact limitation to the user. Do not silently retry with another model/effort or label that output Astra Light work.

Give the implementation worker a lean, self-contained handoff with:

- the exact role statement: `You are the Simple Workflow implementation worker, not the coordinator`;
- the verified canonical absolute path to this loaded skill's `references/role-handoff.md`, plus an instruction to read and obey `## Implementation Worker` before any edit and to stop/report if it is unreadable;
- the canonical workflow root, request id, approved `plan.md` path, and exact fingerprint;
- the requested outcome, completion criteria, constraints, ownership boundaries, and material decisions;
- relevant project facts and raw source paths so the worker can inspect the original code directly;
- expected validation and evidence, plus known risks or replan conditions; and
- explicit authority to choose implementation mechanics, edit only the assigned files, run focused tests, and fix in-scope failures.

Do not derive the contract path from cwd, a relative path, or a guessed installed-cache version. Do not copy the full conversation, prescribe every edit, or send only a summary that omits a critical constraint. Pass raw source access in addition to the approved plan.

Keep the same implementation worker and its model/effort for ordinary in-scope fix and revalidation rounds. Send the evidence-backed finding and changed constraints with the host's actual `followup_task` capability; do not spawn a replacement or retransmit full history. After material replanning, include the new approved plan fingerprint and changed ownership or scope boundaries. That current approved fingerprint—not the immutable `goal_plan_fingerprint`—is the expected worker hash. A new worker is appropriate only when the prior worker is genuinely unavailable; apply the same implementation model/effort defaults or explicit role override, and obtain the user's decision on any unavailable setting.

## Implementation Worker

This section is an early exit from the coordinator workflow. A worker dispatched under this contract does not create or select a Simple Workflow request, run the Independent Plan Challenge, request user approval, create or update a Goal, edit `.simple`, change the approved plan, run completion metadata transitions, or claim the overall request complete. This remains true when the worker inherits an active `.simple` pointer.

At the start of each initial or resumed turn, the worker hashes the supplied approved `plan.md` and compares it with the expected dispatched fingerprint. On mismatch it stops and reports the evidence to the main agent; it does not replan or continue editing. Otherwise the worker reads the approved plan and relevant original sources, chooses implementation mechanics, makes only assigned changes, runs tests that observe the affected behavior, fixes in-scope failures, and reports:

- files changed;
- actual requirement and observable-outcome evidence;
- validation commands and results;
- method-only deviations; and
- remaining concerns.

When substantive project evidence contradicts the approved outcome, scope, ownership, or validation standard, stop that changed work and send the main agent the evidence, impact, and feasible alternatives. Do not unilaterally change the plan or Goal. Small reversible implementation discoveries remain the worker's responsibility.

## Independent Reviewers

The main agent dispatches plan and post-execution reviewers without `model` or `reasoning_effort` overrides so they inherit its model and effort, unless the user explicitly selected reviewer-specific settings. Do not copy the implementation worker's `low` setting into reviewer dispatches. Independence means a separate, non-implementing agent, not a different model.

Plan and post-execution reviewers must be able to inspect the relevant original sources, current plan, and actual result independently. Every first reviewer handoff identifies it as a Simple Workflow independent reviewer, includes the verified canonical absolute path to this loaded `references/role-handoff.md`, and directs it to read and obey this read-only contract before inspection or stop/report if unreadable. Give it the canonical root and raw paths, not only the planner's or worker's summary. Reviewer preference or style comments are non-blocking unless tied to an approved requirement, observable outcome, regression, or material risk.

This is also an early exit from the coordinator workflow. An explicitly delegated reviewer performs read-only inspection and reports evidence-backed findings to the main agent. It does not create or select a request, edit `.simple` or project files, manage approval or a Goal, dispatch other agents, run completion transitions, or certify the overall request complete, even when an active `.simple` pointer is visible.
