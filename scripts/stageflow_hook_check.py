#!/usr/bin/env python3
"""Fast hook auditor for the three-stage Stageflow model."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PHASE_TO_VALIDATION = {
    "definition": "definition",
    "implementation-plan": "implementation-plan",
    "implementation": "implementation",
    "completed": "all",
}
EXPLICIT_WORKFLOW_RE = re.compile(
    r"\b(?:use|run|start|resume|continue|check|create)\s+(?:the\s+)?(?:stage\s*-?\s*flow|stageflow|workflow)\b|"
    r"\b(?:stage\s*-?\s*flow|stageflow|workflow)\s+(?:status|request|current|resume|start|create|continue|plan|run|preflight)\b|"
    r"\.stageflow\s+(?:status|request|current|workflow|preflight)\b|"
    r"\uc6cc\ud06c\ud50c\ub85c\uc6b0\s*(?:\uc0c1\ud0dc|\uc2dc\uc791|\uc9c4\ud589|\uc7ac\uac1c|\uc694\uccad)",
    re.IGNORECASE,
)
IMPLEMENTATION_TOKENS = (
    "implement",
    "implementation",
    "fix",
    "edit",
    "write",
    "change",
    "patch",
    "\uad6c\ud604",
    "\ubc18\uc601",
    "\uc218\uc815",
    "\ubcc0\uacbd",
    "\uace0\uccd0",
    "\uc801\uc6a9",
    "\ucd94\uac00",
    "\uc0ad\uc81c",
    "\uc800\uc7a5",
    "\ud328\uce58",
)
COMPLETION_TOKENS = ("complete", "completed", "done", "\uc644\ub8cc")
STOP_BLOCK_WIRE_REASON = "Stageflow cannot advance yet because the current workflow gate is not complete."
AWAITING_USER_COMPLETION_CLAIM_RE = re.compile(
    r"\b(completed|done)\b|완료\s*확인|목표(?:를)?\s*(?:완료|달성)|"
    r"\bdefinition\s+(?:approved|approval|is approved)\b|정의(?:\s*단계)?(?:가|를|은|는)?\s*(?:승인|approved)|"
    r"다음\s*단계(?:로)?\s*(?:진행|이동)|서비스\s*계획(?:을)?\s*(?:작성|진행|시작)|"
    r"구현\s*계획(?:을)?\s*(?:작성|진행|시작)",
    re.IGNORECASE,
)
PREFLIGHT_MARKER_PREFIX = "Stageflow preflight:"
WRITE_TOOL_TOKENS = (
    "edit",
    "write",
    "notebookedit",
    "apply_patch",
    "apply-patch",
)
SHELL_TOOL_TOKENS = ("bash", "shell", "shell_command", "powershell", "cmd")
WRITE_COMMAND_RE = re.compile(
    r"(\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b|\bremove-item\b|"
    r"\bmove-item\b|\bcopy-item\b|\bmkdir\b|\btouch\b|\btee\b|>>|"
    r"(?<![<>=])>(?![>=])|\bpython\b.*\b(open|write_text|Path\().*['\"]w)",
    re.IGNORECASE | re.DOTALL,
)
READ_TOOL_TOKENS = ("read", "grep", "glob", "search")
READ_COMMAND_RE = re.compile(
    r"(\bcat\b|\bsed\b|\brg\b|\bgrep\b|\bhead\b|\btail\b|\bless\b|\bmore\b|"
    r"\btype\b|\bget-content\b|\bpython\b.*\b(read_text|open\().*['\"]r)",
    re.IGNORECASE | re.DOTALL,
)
STORE_PENDING_GATES = {"pending-answer", "store-only", "store-only-next-question"}
STORE_SYNC_GATES = {"targeted-sync-required", "full-consistency-required", "snapshot-current"}
STORE_DEFINITION_BLOCK_GATES = STORE_PENDING_GATES
STORE_GATES = STORE_PENDING_GATES | STORE_SYNC_GATES
QUESTION_SCOPES = {"큰방향", "주요결정", "세부확인"}
TARGETED_SYNC_GATE = "targeted-sync-required"
FULL_CONSISTENCY_GATE = "full-consistency-required"
SNAPSHOT_CURRENT_GATE = "snapshot-current"
DEFINITION_STORE_FAST_PATH_STATUSES = {"AWAITING_USER", "TARGETED_SYNC_REQUIRED", "FULL_CONSISTENCY_REQUIRED", "SNAPSHOT_CURRENT_REQUIRED"}


def safe_segment(value: str) -> str:
    value = value.strip()
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)[:120]


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("hook payload must be a JSON object")
    return value


def extract_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content")
                if isinstance(content, str):
                    return content
    return ""


def extract_last_assistant(payload: dict[str, Any]) -> str:
    value = payload.get("last_assistant_message")
    if isinstance(value, str):
        return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if isinstance(item, dict) and item.get("role") == "assistant":
                content = item.get("content")
                if isinstance(content, str):
                    return content
    return ""


def is_explicit_workflow(prompt: str) -> bool:
    return bool(EXPLICIT_WORKFLOW_RE.search(prompt))


def looks_like_implementation(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(token in lowered for token in IMPLEMENTATION_TOKENS)


def looks_like_completion(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in COMPLETION_TOKENS)


def subagent_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("agent_type", "role", "prompt", "task", "description", "instructions"):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def is_question_generation_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return (
        ("question" in text or "clarification" in text or "질문" in text)
        and ("backlog" in text or "candidate" in text or "후보" in text)
    )


def is_question_scope_transition_review_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return (
        ("question" in text or "clarification" in text or "scope" in text or "질문" in text)
        and ("transition" in text or "depth" in text or "전환" in text)
        and ("review" in text or "audit" in text or "검토" in text)
    )


def is_definition_store_helper_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return (
        ("definition-store" in text or "impact" in text or "targeted sync" in text or "trace-index" in text)
        and ("candidate" in text or "plan" in text or "helper" in text or "후보" in text or "계획" in text)
    )


def is_targeted_sync_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return "targeted-sync" in text or "targeted sync" in text or "영향 범위" in text or "부분 동기화" in text


def is_full_consistency_subagent(payload: dict[str, Any]) -> bool:
    text = subagent_text(payload)
    return (
        "full-consistency" in text
        or "full consistency" in text
        or "definition consistency" in text
        or "전체 일관성" in text
    )


def resolve_root(args: argparse.Namespace, payload: dict[str, Any]) -> Path:
    start = Path(str(args.root or payload.get("cwd") or ".")).resolve()
    candidates = (start, *start.parents)
    session_id = safe_segment(str(payload.get("session_id") or "")) or "no-session"
    for candidate in candidates:
        if (candidate / ".stageflow" / "sessions" / session_id / "current.json").is_file():
            return candidate
    for candidate in candidates:
        stageflow_dir = candidate / ".stageflow"
        if (stageflow_dir / "index.json").is_file() or (stageflow_dir / "requests").is_dir():
            return candidate
    return start


def current_path(root: Path, payload: dict[str, Any]) -> Path:
    session_id = safe_segment(str(payload.get("session_id") or "")) or "no-session"
    return root / ".stageflow" / "sessions" / session_id / "current.json"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def session_id_for(payload: dict[str, Any]) -> str:
    return safe_segment(str(payload.get("session_id") or "")) or "no-session"


def agent_id_for(payload: dict[str, Any]) -> str:
    return safe_segment(str(payload.get("agent_id") or ""))


def hook_session_dir(root: Path, payload: dict[str, Any]) -> Path:
    return root / ".stageflow" / "hook-state" / "sessions" / session_id_for(payload)


def agent_role_path(root: Path, payload: dict[str, Any], agent_id: str | None = None) -> Path | None:
    safe_agent_id = safe_segment(agent_id or str(payload.get("agent_id") or ""))
    if not safe_agent_id:
        return None
    return hook_session_dir(root, payload) / "agents" / safe_agent_id / "role.json"


def write_agent_role(
    root: Path,
    payload: dict[str, Any],
    *,
    role: str,
    allowed_gate: str,
    request_id: str,
) -> None:
    path = agent_role_path(root, payload)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "agent_id": agent_id_for(payload),
                "role": role,
                "allowed_gate": allowed_gate,
                "request_id": request_id,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_agent_role(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = agent_role_path(root, payload)
    return (load_json(path) if path is not None else None) or {}


def write_turn_state(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> None:
    session_id = session_id_for(payload)
    agent_id = agent_id_for(payload)
    if agent_id:
        state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "agents" / agent_id / "current-turn.json"
    else:
        state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "main" / "current-turn.json"
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mirror = root / ".stageflow" / "hook-state" / "current-turn.json"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["hook_state_written"] = True
    except OSError as exc:
        result.setdefault("warnings", []).append(f"could not write Stageflow hook state: {exc}")
        result["hook_state_written"] = False

def read_turn_state(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = session_id_for(payload)
    state_path = root / ".stageflow" / "hook-state" / "sessions" / session_id / "main" / "current-turn.json"
    return load_json(state_path) or load_json(root / ".stageflow" / "hook-state" / "current-turn.json") or {}


def run_validator(root: Path, phase: str, payload: dict[str, Any]) -> dict[str, Any]:
    validator = Path(__file__).resolve().with_name("validate_stageflow.py")
    command = [sys.executable, str(validator), "--root", str(root), "--current", "--phase", phase]
    session_id = str(payload.get("session_id") or "").strip()
    if session_id:
        command.extend(["--session-id", session_id])
    proc = subprocess.run(command, text=True, capture_output=True)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        status = "PASS"
    elif proc.returncode == 3 or output.startswith("AWAITING_USER"):
        status = "AWAITING_USER"
    else:
        status = "FAIL"
    return {
        "phase": phase,
        "status": status,
        "returncode": proc.returncode,
        "output": output,
    }


def base_result(event: str, root: Path) -> dict[str, Any]:
    return {
        "event": event,
        "root": str(root),
        "status": "PREPASS",
        "severity": "info",
        "preflight_required": False,
        "turn_start_action": "none",
        "state_handling_required": False,
        "warnings": [],
    }


def marker_for(request_id: str, phase: str, validation_status: str) -> str:
    return f"{PREFLIGHT_MARKER_PREFIX} current={request_id}, phase={phase}, validation={validation_status}"


def block_result(result: dict[str, Any], reason: str) -> None:
    result.update(
        {
            "status": "BLOCKED",
            "severity": "error",
            "decision": "block",
            "reason": reason,
        }
    )
    warnings = result.setdefault("warnings", [])
    if reason not in warnings:
        warnings.append(reason)


def set_turn_start_action(
    result: dict[str, Any],
    action: str,
    instruction: str,
    *,
    required: bool = True,
) -> None:
    result["turn_start_action"] = action
    result["turn_start_instruction"] = instruction
    result["state_handling_required"] = required


def pending_clarification_section(text: str) -> str:
    marker = "## Pending Clarifications"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    next_heading = re.search(r"\n##\s+", tail)
    return tail[: next_heading.start()] if next_heading else tail


def has_active_pending_clarification(definition_path: Path) -> bool:
    if not definition_path.is_file():
        return False
    section = pending_clarification_section(definition_path.read_text(encoding="utf-8-sig"))
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 8 and cells[-1].lower() in {"pending", "awaiting"}:
            return True
    return False


def definition_store_required(request_dir: Path) -> bool:
    stage_dir = request_dir / "01-definition"
    return (
        has_active_pending_clarification(stage_dir / "definition.md")
        and not (stage_dir / "definition-store").is_dir()
    )


def definition_store_dir(request_dir: Path) -> Path:
    return request_dir / "01-definition" / "definition-store"


def json_string(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def json_list(data: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def store_question_options_text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_store_question(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    question_id = json_string(raw, "id", "pending_id", "pendingId", "ID").upper()
    status = json_string(raw, "status", "Status") or "pending"
    if status.lower() not in {"pending", "awaiting", "awaiting_user", "대기", "답변 대기"}:
        return None
    options = store_question_options_text(raw.get("options", raw.get("Options", "")))
    return {
        "ID": question_id,
        "Question Scope": json_string(raw, "scope", "question_scope", "questionScope", "Question Scope"),
        "Question": json_string(raw, "question", "Question"),
        "Options": options,
        "Recommended Option": json_string(raw, "recommended_option", "recommendedOption", "recommended", "Recommended Option"),
        "Transition Option": json_string(raw, "transition_option", "transitionOption", "Transition Option") or "N/A",
        "Why This Matters": json_string(raw, "why_this_matters", "whyThisMatters", "why", "Why This Matters"),
        "Status": status,
    }


def store_active_questions(working_set: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in json_list(working_set, "active_pending_questions", "activePendingQuestions"):
        row = normalize_store_question(raw)
        if row is not None:
            rows.append(row)
    return rows


def fast_path_question_is_valid(row: dict[str, str]) -> bool:
    options = row.get("Options", "").lower()
    return (
        bool(re.fullmatch(r"PENDING-\d+", row.get("ID", ""), re.IGNORECASE))
        and row.get("Question Scope", "") in QUESTION_SCOPES
        and bool(row.get("Question", "").strip())
        and "option 1:" in options
        and "option 2:" in options
        and bool(row.get("Recommended Option", "").strip())
        and row.get("Transition Option", "").strip().lower() == "n/a"
        and bool(row.get("Why This Matters", "").strip())
    )


def store_active_ids(working_set: dict[str, Any]) -> set[str]:
    question_ids = {row["ID"] for row in store_active_questions(working_set) if row.get("ID")}
    explicit_ids = {
        str(item).strip().upper()
        for item in json_list(working_set, "active_pending_ids", "activePendingIds")
        if re.fullmatch(r"PENDING-\d+", str(item).strip(), re.IGNORECASE)
    }
    return question_ids or explicit_ids


def read_definition_store(request_dir: Path) -> tuple[dict[str, Any], dict[str, Any], Path] | None:
    store_dir = definition_store_dir(request_dir)
    working_set = load_json(store_dir / "working-set.json")
    sync_state = load_json(store_dir / "sync-state.json")
    if working_set is None or sync_state is None:
        return None
    return working_set, sync_state, store_dir


def definition_store_gate(request_dir: Path) -> str:
    store = read_definition_store(request_dir)
    if store is None:
        return ""
    working_set, sync_state, _ = store
    gate = json_string(sync_state, "current_gate", "currentGate", "gate") or json_string(
        working_set, "current_gate", "currentGate", "gate"
    )
    if gate:
        return gate
    if store_active_ids(working_set):
        return "pending-answer"
    return ""


def active_request_dir(root: Path, current: dict[str, Any]) -> Path:
    request_id = str(current.get("request_id") or "").strip()
    return root / ".stageflow" / "requests" / request_id


def current_definition_store_gate(root: Path, payload: dict[str, Any]) -> str:
    current, state = active_request(root, payload)
    if current is None or state is None:
        return ""
    phase = str(state.get("phase") or current.get("phase") or "").strip()
    if phase != "definition":
        return ""
    return definition_store_gate(active_request_dir(root, current))


def format_store_pending_output(request_dir: Path, questions: list[dict[str, str]]) -> str:
    request_id = request_dir.name
    path = f".stageflow/requests/{request_id}/01-definition/definition-store/working-set.json"
    lines = ["AWAITING_USER definition:"]
    for row in questions:
        scope = row.get("Question Scope", "").strip()
        lines.append(
            f"- `{path}` pending clarification `{row.get('ID', '<unknown>')}`: "
            f"질문 범위: {scope} [{scope}] "
            f"Question: {row.get('Question', '')} "
            f"Options: {row.get('Options', '')} "
            f"Recommended: {row.get('Recommended Option', '')} "
            f"Transition option: {row.get('Transition Option', 'N/A')} "
            f"Why this matters: {row.get('Why This Matters', '')}"
        )
    return "\n".join(lines)


def store_fast_path_result(
    root: Path,
    payload: dict[str, Any],
    result: dict[str, Any],
    *,
    request_id: str,
    request_dir: Path,
    phase: str,
    validation_phase: str,
) -> dict[str, Any] | None:
    store = read_definition_store(request_dir)
    if store is None:
        return None
    working_set, sync_state, _ = store
    questions = store_active_questions(working_set)
    if not questions:
        return None

    gate = definition_store_gate(request_dir) or "pending-answer"
    if gate not in STORE_GATES or not all(fast_path_question_is_valid(question) for question in questions):
        return None
    if gate == TARGETED_SYNC_GATE:
        status = "TARGETED_SYNC_REQUIRED"
        action = "run_targeted_sync_subagent"
        instruction = (
            "The definition store recorded medium-risk answer impact. Register and run a targeted-sync subagent, "
            "write `01-definition/definition-store/targeted-sync-plan.json`, then let the main agent promote the result."
        )
    elif gate == FULL_CONSISTENCY_GATE:
        status = "FULL_CONSISTENCY_REQUIRED"
        action = "run_full_consistency_subagent"
        instruction = (
            "The definition store recorded high-risk or transition impact. Register and run a full-consistency subagent, "
            "write a PASS `01-definition/definition-store/full-consistency-report.json`, and do not snapshot or advance before it passes."
        )
    elif gate == SNAPSHOT_CURRENT_GATE:
        status = "SNAPSHOT_CURRENT_REQUIRED"
        action = "sync_definition_snapshot"
        instruction = (
            "The definition store is ready to snapshot. Sync `definition.md` from the store, update the current definition fingerprint, "
            "and keep review/approval blocked until validator passes."
        )
    else:
        status = "AWAITING_USER"
        action = "handle_awaiting_user_clarification"
        instruction = (
            "The current definition has active store-backed pending questions. Interpret the latest user message semantically, "
            "record the answer in `definition-store/`, set `sync-state.current_gate` by risk, and do not read or write `definition.md` on the store-only path."
        )

    result.update(
        {
            "status": status,
            "severity": "info",
            "current_request_id": request_id,
            "phase": phase,
            "validation_phase": validation_phase,
            "definition_store_gate": gate,
            "validation": {
                "phase": validation_phase,
                "status": "AWAITING_USER",
                "returncode": 3,
                "output": "definition-store fast path",
                "source": "definition-store-fast-path",
            },
            "pending_clarification_output": format_store_pending_output(request_dir, questions),
            "preflight_required": True,
            "preflight_marker": marker_for(request_id, phase, "AWAITING_USER"),
        }
    )
    set_turn_start_action(result, action, instruction)
    write_turn_state(root, payload, result)
    return result


def user_prompt_additional_context(result: dict[str, Any]) -> str:
    lines = [
        "Stageflow hook state is available in `.stageflow/hook-state/`.",
        f"Stageflow status: {result.get('status')}",
        f"turn_start_action: {result.get('turn_start_action')}",
    ]
    for key, label in (
        ("turn_start_instruction", "instruction"),
        ("reason", "reason"),
    ):
        value = result.get(key)
        if value:
            lines.append(f"{label}: {value}")
    if result.get("current_request_id"):
        lines.append(f"current_request_id: {result.get('current_request_id')}")
    if result.get("phase"):
        lines.append(f"phase: {result.get('phase')}")
    pending = str(result.get("pending_clarification_output") or "").strip()
    if pending:
        lines.append("pending_clarifications:")
        lines.append(pending)
    return "\n".join(lines)


def wire_reason(result: dict[str, Any], fallback: str) -> str:
    warnings = [str(item).strip() for item in result.get("warnings", []) if str(item).strip()]
    if warnings:
        return "\n".join(warnings)
    reason = str(result.get("reason") or "").strip()
    return reason or fallback


def to_wire_output(event: str, result: dict[str, Any]) -> dict[str, Any] | None:
    is_blocked = result.get("decision") == "block"

    if event == "user_prompt_submit":
        if is_blocked:
            return {"decision": "block", "reason": wire_reason(result, "Stageflow user prompt blocked")}
        if result.get("status") == "PREPASS":
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": user_prompt_additional_context(result),
            }
        }

    if event == "pre_tool_use":
        if not is_blocked:
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": wire_reason(result, "Stageflow pre-tool-use gate denied this tool call"),
            }
        }

    if event == "stop":
        if not is_blocked:
            return None
        return {"decision": "block", "reason": STOP_BLOCK_WIRE_REASON}

    if event == "subagent_start":
        if not is_blocked:
            return None
        return {
            "continue": False,
            "stopReason": wire_reason(result, "Stageflow subagent-start gate blocked this subagent"),
        }

    if event == "subagent_stop":
        if not is_blocked:
            return None
        return {"decision": "block", "reason": wire_reason(result, "Stageflow subagent-stop gate blocked this subagent")}

    return None

def handle_user_prompt_submit(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    prompt = extract_prompt(payload)
    explicit = is_explicit_workflow(prompt)
    stageflow_dir = root / ".stageflow"
    current = load_json(current_path(root, payload))

    if current is None:
        if not explicit:
            write_turn_state(root, payload, result)
            return result
        if explicit:
            result.update(
                {
                    "status": "REQUEST_REQUIRED",
                    "severity": "warning",
                    "preflight_required": True,
                    "preflight_marker": marker_for("none", "request-required", "REQUEST_REQUIRED"),
                    "request_creation_required": True,
                    "reason": "explicit Stageflow prompt has no session current pointer",
                }
            )
            set_turn_start_action(
                result,
                "create_request",
                "Inspect the project, create `.stageflow` request scaffolding including `01-definition/definition-store/`, and write the session current pointer before any substantive workflow answer.",
            )
            write_turn_state(root, payload, result)
        return result

    request_id = str(current.get("request_id") or "").strip()
    request_dir = stageflow_dir / "requests" / request_id
    state = load_json(request_dir / "state.json") if request_id else None
    if not request_id or state is None:
        result.update(
            {
                "status": "INVALID_CURRENT",
                "severity": "warning",
                "preflight_required": True,
                "preflight_marker": marker_for(request_id or "none", "invalid-current", "FAIL"),
                "reason": "session current pointer does not reference a valid request",
            }
        )
        set_turn_start_action(
            result,
            "repair_current_pointer",
            "Repair or replace the session current pointer so it references an existing `.stageflow/requests/<request-id>` with matching `state.json` before continuing.",
        )
        write_turn_state(root, payload, result)
        return result

    phase = str(state.get("phase") or current.get("phase") or "").strip()
    validation_phase = PHASE_TO_VALIDATION.get(phase)
    if validation_phase is None:
        result.update(
            {
                "status": "INVALID_CURRENT",
                "severity": "warning",
                "preflight_required": True,
                "preflight_marker": marker_for(request_id, phase or "invalid-current", "FAIL"),
                "current_request_id": request_id,
                "phase": phase,
                "reason": "current request phase is not allowed",
            }
        )
        set_turn_start_action(
            result,
            "repair_current_state",
            "Repair `state.json` and the session current pointer so the phase is one of the allowed Stageflow phases before continuing.",
        )
        write_turn_state(root, payload, result)
        return result

    if phase == "completed" and not explicit:
        result.update(
            {
                "status": "PREPASS",
                "severity": "info",
                "current_request_id": request_id,
                "phase": phase,
                "completed_current_prepass": True,
                "preflight_required": False,
            }
        )
        write_turn_state(root, payload, result)
        return result

    if phase == "definition":
        fast_path = store_fast_path_result(
            root,
            payload,
            result,
            request_id=request_id,
            request_dir=request_dir,
            phase=phase,
            validation_phase=validation_phase,
        )
        if fast_path is not None:
            return fast_path

    validation = run_validator(root, validation_phase, payload)
    marker = marker_for(request_id, phase, validation["status"])
    store_required = phase == "definition" and definition_store_required(request_dir)
    gate = definition_store_gate(request_dir) if phase == "definition" else ""
    if store_required:
        status = "DEFINITION_STORE_REQUIRED"
        severity = "warning"
        action = "create_definition_store"
        instruction = (
            "The current definition has active Pending Clarifications but no `01-definition/definition-store/`. "
            "Before processing the user answer, create `working-set.json`, `decision-ledger.jsonl`, "
            "`trace-index.json`, and `sync-state.json` with the current active pending IDs, scope, "
            "definition fingerprint, and empty decision sync state."
        )
    elif validation["status"] == "PASS":
        status = "OK"
        severity = "info"
        action = "continue_current_stage"
        instruction = "Continue from the validated current Stageflow stage and do not advance until its required artifact, subagent review, and approval gates pass. Goal gates apply only after definition."
    elif validation["status"] == "AWAITING_USER":
        status = "AWAITING_USER"
        severity = "info"
        action = "handle_awaiting_user_clarification"
        instruction = (
            "The current Stageflow stage has an active pending clarification batch with a valid definition-store. Interpret the latest user message semantically against the pending questions: record answers in definition-store, create the next pending batch after the required risk check, answer follow-ups and restate pending options, or handle an explicit clarification stop signal by running the transition-risk audit. Do not review, approve, advance, or implement while AWAITING_USER remains active."
        )
    else:
        status = "WARNING"
        severity = "warning"
        action = "repair_current_stage"
        instruction = "Repair the current Stageflow stage artifacts until the current-stage validator passes before advancing or answering as if the stage is ready."
    if phase == "completed":
        status = "COMPLETED_CURRENT" if validation["status"] == "PASS" else "WARNING"
        severity = "warning"
        action = "start_new_request"
        instruction = (
            "The session current pointer references a completed Stageflow request; create or select a non-completed request before doing new workflow work."
        )
    result.update(
        {
            "status": status,
            "severity": severity,
            "current_request_id": request_id,
            "phase": phase,
            "validation_phase": validation_phase,
            "validation": validation,
            "definition_store_gate": gate,
            "preflight_required": True,
            "preflight_marker": marker,
        }
    )
    set_turn_start_action(result, action, instruction, required=action != "continue_current_stage")
    if validation["status"] == "FAIL":
        result["warnings"].append("current Stageflow stage validation failed")
        if store_required:
            result["warnings"].append("definition-store is required before handling active Pending Clarifications")
    elif validation["status"] == "AWAITING_USER":
        result["pending_clarification_output"] = validation.get("output", "")

    if looks_like_implementation(prompt) and validation["status"] != "AWAITING_USER":
        entry_gate = run_validator(root, "implementation-plan", payload)
        result["implementation_entry_gate"] = entry_gate
        if entry_gate["status"] != "PASS":
            result["warnings"].append("implementation requested before implementation-plan stage passed")
            result["implementation_block_required"] = True
            result["status"] = "IMPLEMENTATION_BLOCKED"
            result["severity"] = "warning"
            set_turn_start_action(
                result,
                "repair_implementation_plan_gate",
                "Do not implement. Return to the implementation-plan stage and repair its goal, artifact, subagent review, and approval gates until `--phase implementation-plan` passes.",
            )

    write_turn_state(root, payload, result)
    return result


def handle_stop(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    turn = read_turn_state(root, payload)
    if turn.get("preflight_required"):
        last_message = extract_last_assistant(payload)

        if turn.get("request_creation_required") and load_json(current_path(root, payload)) is None:
            block_result(result, "explicit Stageflow prompt ended without creating a session current pointer")
        elif turn.get("request_creation_required"):
            current = load_json(current_path(root, payload)) or {}
            request_id = str(current.get("request_id") or "").strip()
            if request_id:
                request_dir = root / ".stageflow" / "requests" / request_id
                if not (request_dir / "01-definition" / "definition-store").is_dir():
                    block_result(result, "Stageflow request creation must include `01-definition/definition-store/`")
                else:
                    validation = run_validator(root, "definition", payload)
                    result["definition_store_validation"] = validation
                    if validation["status"] == "FAIL":
                        block_result(result, "Stageflow request creation must include a valid `01-definition/definition-store/`")

        if turn.get("status") == "INVALID_CURRENT":
            current = load_json(current_path(root, payload))
            request_id = str((current or {}).get("request_id") or "").strip()
            state = load_json(root / ".stageflow" / "requests" / request_id / "state.json") if request_id else None
            if not request_id or state is None:
                block_result(result, "Stageflow session current pointer is still invalid")

        if turn.get("status") == "AWAITING_USER":
            if AWAITING_USER_COMPLETION_CLAIM_RE.search(last_message):
                block_result(result, "AWAITING_USER response must not claim completion or next-stage progress before the user answers")
            return result

        if turn.get("status") == "DEFINITION_STORE_REQUIRED":
            current = load_json(current_path(root, payload)) or {}
            request_id = str(current.get("request_id") or "").strip()
            request_dir = root / ".stageflow" / "requests" / request_id if request_id else None
            if not request_dir or definition_store_required(request_dir):
                block_result(result, "definition-store is still missing for active Pending Clarifications")
                return result
            validation = run_validator(root, "definition", payload)
            result["definition_store_validation"] = validation
            if validation["status"] == "FAIL":
                block_result(result, "definition-store is invalid for the current definition stage")
                return result

        if turn.get("status") in {"TARGETED_SYNC_REQUIRED", "FULL_CONSISTENCY_REQUIRED", "SNAPSHOT_CURRENT_REQUIRED"}:
            validation = run_validator(root, "definition", payload)
            result["definition_store_gate_validation"] = validation
            if validation["status"] == "FAIL":
                block_result(result, "definition-store gate artifacts are incomplete or invalid")
                return result

        if looks_like_completion(last_message):
            validation = run_validator(root, "all", payload)
            result["completion_validation"] = validation
            if validation["status"] != "PASS":
                block_result(result, "completion-like response but three-stage validation failed")

    return result


def extract_tool_name(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input")
    if isinstance(value, dict):
        return value
    value = payload.get("input")
    if isinstance(value, dict):
        return value
    return {}


def normalize_tool_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def is_stageflow_path(value: str) -> bool:
    normalized = normalize_tool_path(value).lower()
    return (
        normalized == ".stageflow"
        or normalized.startswith(".stageflow/")
        or "/.stageflow/" in normalized
        or normalized.endswith("/.stageflow")
    )


def patch_paths(text: str) -> list[str]:
    paths: list[str] = []
    for line in text.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: "):
            if line.startswith(prefix):
                paths.append(line[len(prefix) :].strip())
    return paths


def payload_paths(tool_input: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    value = tool_input.get("paths")
    if isinstance(value, list):
        paths.extend(str(item).strip() for item in value if str(item).strip())
    for key in ("patch", "content", "input", "command"):
        value = tool_input.get(key)
        if isinstance(value, str):
            paths.extend(patch_paths(value))
    return paths


def is_write_like_tool(payload: dict[str, Any]) -> bool:
    tool_name = extract_tool_name(payload).lower()
    tool_input = extract_tool_input(payload)
    if any(token in tool_name for token in WRITE_TOOL_TOKENS):
        return True
    if any(token in tool_name for token in SHELL_TOOL_TOKENS):
        command = str(tool_input.get("command") or "")
        return bool(WRITE_COMMAND_RE.search(command))
    return False


def is_read_like_tool(payload: dict[str, Any]) -> bool:
    tool_name = extract_tool_name(payload).lower()
    tool_input = extract_tool_input(payload)
    if any(token in tool_name for token in READ_TOOL_TOKENS):
        return True
    if any(token in tool_name for token in SHELL_TOOL_TOKENS):
        command = str(tool_input.get("command") or "")
        return bool(READ_COMMAND_RE.search(command))
    return False


def is_stageflow_artifact_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return all(is_stageflow_path(path) for path in paths)

    command = str(tool_input.get("command") or "")
    if command and WRITE_COMMAND_RE.search(command):
        normalized = normalize_tool_path(command).lower()
        return ".stageflow/" in normalized or "\\.stageflow\\" in command.lower()

    return False


def is_definition_md_access(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return any(normalize_tool_path(path).lower().endswith("/01-definition/definition.md") for path in paths)
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    content = normalize_tool_path(str(tool_input.get("content") or "")).lower()
    return "01-definition/definition.md" in command or "01-definition/definition.md" in content


def is_question_backlog_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return all(normalize_tool_path(path).lower().endswith("/01-definition/question-backlog.md") for path in paths)
    command = str(tool_input.get("command") or "")
    return "question-backlog.md" in normalize_tool_path(command).lower()


def is_question_scope_transition_review_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        return all(
            normalize_tool_path(path).lower().endswith("/01-definition/question-scope-transition-review.md")
            for path in paths
        )
    command = str(tool_input.get("command") or "")
    return "question-scope-transition-review.md" in normalize_tool_path(command).lower()


def is_definition_store_json_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all("/01-definition/definition-store/" in path and path.endswith(".json") for path in normalized_paths)
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    return "/01-definition/definition-store/" in command and ".json" in command


def is_definition_store_data_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all(
            "/01-definition/definition-store/" in path and (path.endswith(".json") or path.endswith(".jsonl"))
            for path in normalized_paths
        )
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    return "/01-definition/definition-store/" in command and (".json" in command or ".jsonl" in command)


def is_targeted_sync_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    allowed = ("targeted-sync-plan.json", "targeted-sync-report.json", "impact-candidates.json")
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all("/01-definition/definition-store/" in path and path.rsplit("/", 1)[-1] in allowed for path in normalized_paths)
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    return "/01-definition/definition-store/" in command and any(name in command for name in allowed)


def is_full_consistency_write(payload: dict[str, Any]) -> bool:
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    allowed = ("full-consistency-report.json",)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all("/01-definition/definition-store/" in path and path.rsplit("/", 1)[-1] in allowed for path in normalized_paths)
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    return "/01-definition/definition-store/" in command and any(name in command for name in allowed)


def is_required_definition_store_write(payload: dict[str, Any]) -> bool:
    required_names = {
        "working-set.json",
        "decision-ledger.jsonl",
        "trace-index.json",
        "sync-state.json",
    }
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all(
            "/01-definition/definition-store/" in path
            and path.rsplit("/", 1)[-1] in required_names
            for path in normalized_paths
        )
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    if not command:
        return False
    if "mkdir" in command and "/01-definition/definition-store" in command:
        return True
    return "/01-definition/definition-store/" in command and any(name in command for name in required_names)


def is_awaiting_user_definition_write(payload: dict[str, Any]) -> bool:
    allowed_suffixes = (
        "/01-definition/definition.md",
        "/01-definition/question-backlog.md",
        "/01-definition/question-scope-transition-review.md",
        "/01-definition/transition-risk-goal.md",
        "/01-definition/transition-risk.md",
    )
    tool_input = extract_tool_input(payload)
    paths = payload_paths(tool_input)
    if paths:
        normalized_paths = [normalize_tool_path(path).lower() for path in paths]
        return all(
            any(path.endswith(suffix) for suffix in allowed_suffixes)
            or ("/01-definition/definition-store/" in path and (path.endswith(".json") or path.endswith(".jsonl")))
            for path in normalized_paths
        )
    command = normalize_tool_path(str(tool_input.get("command") or "")).lower()
    if not command:
        return False
    return (
        (
            "01-definition/definition.md" in command
            or "01-definition/question-backlog.md" in command
            or "01-definition/question-scope-transition-review.md" in command
            or "01-definition/definition-store/" in command
            or "01-definition/transition-risk-goal.md" in command
            or "01-definition/transition-risk.md" in command
        )
        and "01-definition/review/" not in command
        and "01-definition/approval.md" not in command
        and "02-implementation-plan" not in command
        and "03-implementation" not in command
    )


def active_request(root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    current = load_json(current_path(root, payload))
    if current is None:
        return None, None
    request_id = str(current.get("request_id") or "").strip()
    state = load_json(root / ".stageflow" / "requests" / request_id / "state.json") if request_id else None
    return current, state


def handle_pre_tool_use(root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    result["event"] = "pre_tool_use"
    turn = read_turn_state(root, payload)
    gate = str(turn.get("definition_store_gate") or current_definition_store_gate(root, payload) or "")
    if gate:
        result["definition_store_gate"] = gate

    if is_read_like_tool(payload):
        result["read_like_tool"] = True
        if (
            turn.get("status") in DEFINITION_STORE_FAST_PATH_STATUSES
            and gate in STORE_DEFINITION_BLOCK_GATES
            and is_definition_md_access(payload)
        ):
            block_result(
                result,
                "definition-store store-only turns may not read `01-definition/definition.md`; use `definition-store/working-set.json` instead",
            )
            return result

    if not is_write_like_tool(payload):
        return result

    result["write_like_tool"] = True
    if turn.get("status") == "DEFINITION_STORE_REQUIRED":
        if is_required_definition_store_write(payload):
            result["definition_store_required_write"] = True
            return result
        block_result(
            result,
            "DEFINITION_STORE_REQUIRED turns may only create required `01-definition/definition-store/` files "
            "before handling active Pending Clarifications",
        )
        return result

    if payload.get("agent_id") and turn.get("status") in DEFINITION_STORE_FAST_PATH_STATUSES:
        role_state = read_agent_role(root, payload)
        role = str(role_state.get("role") or "")
        allowed_gate = str(role_state.get("allowed_gate") or "")
        result["registered_subagent_role"] = role
        if not role:
            block_result(
                result,
                "definition clarification subagent writes require a role registered by SubagentStart for this agent_id",
            )
            return result
        if role == "question-backlog" and is_question_backlog_write(payload):
            result["question_backlog_write"] = True
            return result
        if role == "question-scope-transition-review" and is_question_scope_transition_review_write(payload):
            result["question_scope_transition_review_write"] = True
            return result
        if role == "definition-store-helper" and is_definition_store_json_write(payload):
            result["definition_store_helper_write"] = True
            return result
        if role == "targeted-sync" and gate == allowed_gate == TARGETED_SYNC_GATE and is_targeted_sync_write(payload):
            result["targeted_sync_write"] = True
            return result
        if role == "full-consistency" and gate == allowed_gate == FULL_CONSISTENCY_GATE and is_full_consistency_write(payload):
            result["full_consistency_write"] = True
            return result
        block_result(
            result,
            "definition clarification subagents may only write files allowed by their registered role and current definition-store gate",
        )
        return result

    if turn.get("status") in DEFINITION_STORE_FAST_PATH_STATUSES and is_stageflow_artifact_write(payload):
        if gate in STORE_DEFINITION_BLOCK_GATES:
            if is_definition_md_access(payload):
                block_result(
                    result,
                    "definition-store store-only turns may not write `01-definition/definition.md`; record the answer and next gate in `definition-store/` first",
                )
                return result
            if (
                is_definition_store_data_write(payload)
                or is_question_backlog_write(payload)
                or is_question_scope_transition_review_write(payload)
                or is_awaiting_user_definition_write(payload)
            ):
                result["store_only_definition_write"] = True
                return result
        elif gate == TARGETED_SYNC_GATE:
            if is_targeted_sync_write(payload) or is_definition_store_data_write(payload):
                result["targeted_sync_write"] = True
                return result
        elif gate == FULL_CONSISTENCY_GATE:
            if is_full_consistency_write(payload) or is_definition_store_data_write(payload):
                result["full_consistency_write"] = True
                return result
        elif gate == SNAPSHOT_CURRENT_GATE:
            if is_awaiting_user_definition_write(payload):
                result["snapshot_current_definition_write"] = True
                return result
        elif is_awaiting_user_definition_write(payload):
            result["awaiting_user_definition_write"] = True
            return result
        block_result(
            result,
            "definition clarification turns may only write files allowed by the current `definition-store` gate",
        )
        return result

    if is_stageflow_artifact_write(payload):
        result["stageflow_artifact_write"] = True
        return result

    current, state = active_request(root, payload)
    if current is None:
        if turn.get("request_creation_required") or turn.get("preflight_required"):
            block_result(
                result,
                "Stageflow is active but no session current pointer exists; create `.stageflow` request artifacts before non-Stageflow edits",
            )
        return result

    request_id = str(current.get("request_id") or "").strip()
    if state is None:
        block_result(result, "Stageflow session current pointer does not reference a valid request")
        return result

    phase = str(state.get("phase") or current.get("phase") or "").strip()
    result.update({"current_request_id": request_id, "phase": phase})
    if phase == "completed":
        result["completed_current_prepass"] = True
        return result

    entry_gate = run_validator(root, "implementation-plan", payload)
    result["implementation_entry_gate"] = entry_gate
    if entry_gate["status"] != "PASS":
        block_result(result, "non-Stageflow file edit blocked until implementation-plan stage passes")

    return result

def handle_subagent(event: str, root: Path, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    turn = read_turn_state(root, payload)
    current, state = active_request(root, payload)
    request_id = str((current or {}).get("request_id") or turn.get("current_request_id") or "").strip()
    gate = str(turn.get("definition_store_gate") or current_definition_store_gate(root, payload) or "")
    result.update(
        {
            "status": "SUBAGENT_OBSERVED",
            "severity": "info",
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "role": payload.get("role"),
            "current_request_id": request_id,
            "definition_store_gate": gate,
        }
    )
    if event == "subagent_start" and turn.get("status") in DEFINITION_STORE_FAST_PATH_STATUSES:
        if is_question_generation_subagent(payload):
            result["status"] = "QUESTION_BACKLOG_SUBAGENT_ALLOWED"
            result["question_backlog_allowed"] = True
            write_agent_role(root, payload, role="question-backlog", allowed_gate=gate or "pending-answer", request_id=request_id)
        elif is_question_scope_transition_review_subagent(payload):
            result["status"] = "QUESTION_SCOPE_TRANSITION_REVIEW_SUBAGENT_ALLOWED"
            result["question_scope_transition_review_allowed"] = True
            write_agent_role(
                root,
                payload,
                role="question-scope-transition-review",
                allowed_gate=gate or "pending-answer",
                request_id=request_id,
            )
        elif is_definition_store_helper_subagent(payload):
            result["status"] = "DEFINITION_STORE_HELPER_SUBAGENT_ALLOWED"
            result["definition_store_helper_allowed"] = True
            write_agent_role(root, payload, role="definition-store-helper", allowed_gate=gate or "pending-answer", request_id=request_id)
        elif gate == TARGETED_SYNC_GATE and is_targeted_sync_subagent(payload):
            result["status"] = "TARGETED_SYNC_SUBAGENT_ALLOWED"
            result["targeted_sync_allowed"] = True
            write_agent_role(root, payload, role="targeted-sync", allowed_gate=TARGETED_SYNC_GATE, request_id=request_id)
        elif gate == FULL_CONSISTENCY_GATE and is_full_consistency_subagent(payload):
            result["status"] = "FULL_CONSISTENCY_SUBAGENT_ALLOWED"
            result["full_consistency_allowed"] = True
            write_agent_role(root, payload, role="full-consistency", allowed_gate=FULL_CONSISTENCY_GATE, request_id=request_id)
        else:
            block_result(
                result,
                "definition clarification allows only registered question backlog, question scope transition, definition-store helper, targeted-sync, or full-consistency subagents at the matching gate",
            )
    write_turn_state(root, payload, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--event",
        choices=("user_prompt_submit", "pre_tool_use", "stop", "subagent_start", "subagent_stop"),
        default="user_prompt_submit",
    )
    parser.add_argument("--root")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        payload = read_payload()
    except Exception as exc:
        sys.stderr.write(json.dumps({"status": "ERROR", "severity": "error", "reason": str(exc)}) + "\n")
        raise SystemExit(1)

    root = resolve_root(args, payload)
    result = base_result(args.event, root)
    if args.event == "user_prompt_submit":
        result = handle_user_prompt_submit(root, payload, result)
    elif args.event == "pre_tool_use":
        result = handle_pre_tool_use(root, payload, result)
    elif args.event == "stop":
        result = handle_stop(root, payload, result)
    else:
        result = handle_subagent(args.event, root, payload, result)
    wire_output = to_wire_output(args.event, result)
    if wire_output is not None:
        print(json.dumps(wire_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
