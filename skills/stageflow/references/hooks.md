# Stageflow Codex Hooks

Stageflow ships plugin-provided hooks that audit the four-stage workflow model. The hooks do not create or repair request artifacts. They only report current state and write runtime records under `.stageflow/hook-state/`.

## Events

`hooks/hooks.json` declares:

- `UserPromptSubmit`: `python hooks/stageflow_hook.py user_prompt_submit`
- `Stop`: `python hooks/stageflow_hook.py stop`
- `SubagentStart`: `python hooks/stageflow_hook.py subagent_start`
- `SubagentStop`: `python hooks/stageflow_hook.py subagent_stop`

The wrapper resolves the plugin root from its own location, or from `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or `CLAUDE_PLUGIN_ROOT`.

## UserPromptSubmit

The hook reads `.stageflow/sessions/<session-id>/current.json`, then validates the current request stage with `scripts/validate_stageflow.py`.

Behavior:

- Explicit Stageflow prompts without a session current pointer return `REQUEST_REQUIRED`.
- Non-workflow prompts without a session current pointer return `PREPASS`.
- Active requests return a preflight marker:

```text
Stageflow preflight: current=<request-id>, phase=<phase>, validation=<PASS|FAIL>
```

- Implementation-like prompts also validate `--phase implementation-plan`. If that gate fails, implementation must not proceed.

## Stop

The stop hook reads the previous turn state from `.stageflow/hook-state/`.

Behavior:

- If a preflight marker was required, the assistant response must include it.
- Completion-like responses validate `--phase all`.
- Validation failure produces a warning instead of mutating workflow artifacts.

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

Run a prompt check:

```powershell
'{"hook_event_name":"UserPromptSubmit","session_id":"session-1","prompt":"[$stageflow:stageflow] 상태 확인"}' | python scripts/stageflow_hook_check.py --event user_prompt_submit
```

Run a stop check:

```powershell
'{"hook_event_name":"Stop","session_id":"session-1","last_assistant_message":"구현 완료했습니다."}' | python scripts/stageflow_hook_check.py --event stop
```
