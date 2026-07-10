# Simple Workflow Hooks

The hook checker reports plan-centered workflow readiness and structurally gates `create_goal`.
It does not decide whether natural-language user text approves execution.

Codex runs hook commands with the session `cwd`, so plugin-bundled hooks must not use target-relative paths such as `python hooks/simple_workflow_hook.py ...`. The declared commands use a small inline Python bootstrap and try Python launchers in this order: `python3`, `py -3`, then `python`. The bootstrap resolves `scripts/simple_workflow_hook_check.py` from `SIMPLE_WORKFLOW_PLUGIN_ROOT`, `STAGEFLOW_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, the installed Codex plugin cache under `~/.codex/plugins/cache/**/stageflow*/**/scripts/simple_workflow_hook_check.py`, or the legacy standalone cache under `~/.codex/plugins/cache/**/simple-workflow-plugin/**/scripts/simple_workflow_hook_check.py`. If no checker is found, the hook writes a warning and exits successfully instead of blocking the user's project because of a stale path.

`simple_workflow_hook_check.py` resolves `validate_simple_workflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `hooks/simple_workflow_hook.py` or `scripts/validate_simple_workflow.py`.

It keeps the session pointer model:

```text
.simple/sessions/<session-id>/current.json
```

`UserPromptSubmit` emits valid hook wire output with `additionalContext` when the agent needs
Simple Workflow readiness or continuation context. It never emits `PROCEED_ALLOWED` and does not
search prompts for approval keywords. The skill-applying agent owns semantic approval judgment.

It reports when:

- an explicit Simple Workflow prompt has no active request
- an active `plan` or `review` request receives a follow-up prompt that does not mention Simple Workflow again; this is a non-blocking continuation warning that reminds Codex to keep applying Simple Workflow rules
- the active request points to a missing or completed request
- `plan.md` is missing for the plan phase
- internal `review.md` is missing for the review or completed phase
- internal `review.md` has a stale plan fingerprint

A completed request does not capture unrelated prompts. Explicit Simple Workflow invocation with a
completed pointer asks the agent to create or select a new request.

`PreToolUse` ignores tools other than `create_goal`. It also prepasses unrelated `create_goal`
calls unless their objective contains an exact `.simple/requests/<request-id>/plan.md` path;
mentioning Simple Workflow or `.simple` as a topic is not enough. This keeps Stageflow and other
Goal flows independent. For an in-scope Simple Workflow `create_goal`, it emits
`hookSpecificOutput.permissionDecision: deny` unless all structural requirements hold:

- the selected request metadata is coherent and phase is exactly `review`
- plugin-bundled `--phase review` validation passes
- the objective request id and fingerprint exactly match the selected request and current plan
- `review.md` has the current plan fingerprint and an exact uppercase `PASS` verdict
- local `goal_status` is not already `active`, `completing`, or `completed`

The pre-tool hook does not prove user approval; the agent has already made that conversational
decision before attempting the tool call. `Stop` emits a blocking wire response only when the
current phase's required artifacts or validation are invalid.

Run manually with the plugin-bundled checker against a target project root:

```powershell
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event user_prompt_submit
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event pre_tool_use
python <plugin-root>/scripts/simple_workflow_hook_check.py --root <target-project-root> --event stop
```

These commands produce hook wire output. Add `--diagnostic` when manually inspecting the internal
audit result in tests or local debugging.
