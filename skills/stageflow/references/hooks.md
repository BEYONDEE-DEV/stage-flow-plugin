# Stageflow Codex Hooks

Stageflow ships plugin-provided hooks that audit the four-stage workflow model and block premature file edits. The hooks do not create or repair request artifacts. They report current state, write runtime records under `.stageflow/hook-state/`, and block non-Stageflow file edits until the implementation-plan gate passes.

## Events

`hooks/hooks.json` declares:

- `PreToolUse`: `python hooks/stageflow_hook.py pre_tool_use`
- `UserPromptSubmit`: `python hooks/stageflow_hook.py user_prompt_submit`
- `Stop`: `python hooks/stageflow_hook.py stop`
- `SubagentStart`: `python hooks/stageflow_hook.py subagent_start`
- `SubagentStop`: `python hooks/stageflow_hook.py subagent_stop`

The wrapper resolves the plugin root from its own location, or from `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or `CLAUDE_PLUGIN_ROOT`. `stageflow_hook_check.py` then resolves `validate_stageflow.py` from its own plugin `scripts` directory with `__file__`, so hook validation does not depend on the target project containing `scripts/validate_stageflow.py`.

## PreToolUse

The hook inspects write-like tools before they run.

Behavior:

- Writes to `.stageflow/**` artifacts are allowed so the workflow can be created or repaired.
- Non-write tools and read-only shell commands return `PREPASS`.
- Non-Stageflow file edits are blocked while an active Stageflow request lacks a valid session current pointer or while the plugin-bundled validator fails `--phase implementation-plan` for the target project root.
- Completed Stageflow requests do not authorize new file edits; start a new request first.

## UserPromptSubmit

The hook reads `.stageflow/sessions/<session-id>/current.json`, then validates the current request stage with the plugin-bundled `scripts/validate_stageflow.py` against the target project root.

Behavior:

- Explicit Stageflow prompts without a session current pointer return `REQUEST_REQUIRED`, `turn_start_action: create_request`, require a preflight marker, and record turn state for the Stop hook.
- Non-workflow prompts without a session current pointer return `PREPASS` and `turn_start_action: none`.
- Invalid or stale current pointers return `INVALID_CURRENT` with `turn_start_action: repair_current_pointer` or `repair_current_state`.
- Completed current requests return `COMPLETED_CURRENT` with `turn_start_action: start_new_request` so new workflow work does not continue on terminal state.
- Active requests return a preflight marker:

```text
Stageflow preflight: current=<request-id>, phase=<phase>, validation=<PASS|FAIL>
```

- Active requests also return `turn_start_action`: `continue_current_stage` when validation passes, or `repair_current_stage` when the current stage fails validation.
- Implementation-like prompts also validate `--phase implementation-plan`. If that gate fails, the hook returns `IMPLEMENTATION_BLOCKED`, `implementation_block_required: true`, and `turn_start_action: repair_implementation_plan_gate`; implementation must not proceed.
- `turn_start_instruction` is mandatory next-action guidance for the main agent.

## Stop

The stop hook reads the previous turn state from `.stageflow/hook-state/`.

Behavior:

- If a preflight marker was required, the assistant response must include it.
- Completion-like responses validate `--phase all`.
- Missing preflight markers, missing current pointers after explicit Stageflow prompts, invalid current pointers, and completion validation failures return a block decision instead of silently warning.

## Subagent Hooks

`SubagentStart` and `SubagentStop` record lightweight lifecycle observations. They do not count as stage review evidence by themselves. A stage review only passes when the stage's `review.md` records `Subagent review.`, a matching artifact fingerprint, `PASS`, and no blocking issues.

## Runtime State

Hook runtime state may appear at:

```text
.stageflow/hook-state/current-turn.json
.stageflow/hook-state/sessions/<session-id>/main/current-turn.json
.stageflow/hook-state/sessions/<session-id>/agents/<agent-id>/current-turn.json
```

Do not treat hook-state files as durable workflow artifacts. Durable request state belongs under `.stageflow/requests/<request-id>/`.

## Manual Checks

Run a pre-tool edit gate check:

```powershell
'{"hook_event_name":"PreToolUse","session_id":"session-1","tool_name":"Write","tool_input":{"file_path":"src/app.ts"}}' | python <plugin-root>/scripts/stageflow_hook_check.py --event pre_tool_use --root <target-project-root>
```

Run a prompt check:

```powershell
'{"hook_event_name":"UserPromptSubmit","session_id":"session-1","prompt":"[$stageflow:stageflow] 상태 확인"}' | python <plugin-root>/scripts/stageflow_hook_check.py --event user_prompt_submit --root <target-project-root>
```

Run a stop check:

```powershell
'{"hook_event_name":"Stop","session_id":"session-1","last_assistant_message":"구현 완료했습니다."}' | python <plugin-root>/scripts/stageflow_hook_check.py --event stop --root <target-project-root>
```
