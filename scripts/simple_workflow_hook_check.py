#!/usr/bin/env python3
"""Hook auditor and structural goal gate for Simple Workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PHASE_TO_VALIDATION = {"plan": "plan", "review": "review", "completed": "all"}
SIMPLE_PLAN_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])\.simple[/\\]requests[/\\](?P<request_id>\d{8}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*)[/\\]plan\.md"
    r"(?=$|[\s`'\"<>()\[\]{},;:]|\.(?:$|\s))",
    re.I,
)
OBJECTIVE_FINGERPRINT_RE = re.compile(r"sha256:([0-9a-fA-F]{64})")
CONTINUATION_WARNING = (
    "Active Simple Workflow request exists; continue Simple Workflow rules even if the prompt did not mention the plugin."
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check simplified Simple Workflow hook state.")
    ap.add_argument("--event", default="user_prompt_submit")
    ap.add_argument("--root", default=".")
    ap.add_argument(
        "--diagnostic",
        action="store_true",
        help="Print the internal audit result instead of hook wire output.",
    )
    args = ap.parse_args(argv)
    event = norm_event(args.event)
    result = check_hook(event, Path(args.root).resolve(), read_payload())
    if args.diagnostic:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    wire_output = to_wire_output(event, result)
    if wire_output is not None:
        print(json.dumps(wire_output, ensure_ascii=False, sort_keys=True))
    elif event == "stop" and result.get("severity") == "warning":
        print(f"Simple Workflow WARN: {result.get('reason', 'state check failed')}", file=sys.stderr)
    return 0


def check_hook(event: str, root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    create_goal_tool = event == "pre_tool_use" and is_create_goal_tool(payload)
    goal_objective = extract_goal_objective(payload) if create_goal_tool else ""
    objective_request_id = simple_goal_request_id(goal_objective) if create_goal_tool else ""
    objective_fingerprint = goal_objective_fingerprint(goal_objective) if create_goal_tool else ""
    simple_goal_candidate = create_goal_tool and bool(objective_request_id)
    session_id = session_id_from(payload)
    current_path = root / ".simple" / "sessions" / safe(session_id) / "current.json"
    result: dict[str, Any] = {
        "schema_version": "2",
        "event": event,
        "cwd": str(root),
        "hook_scope": {
            "session_id": session_id,
            "state_dir": f".simple/hook-state/sessions/{session_id}/main",
        },
        "prompt_relevant": False,
        "continuation_required": False,
        "preflight_required": simple_goal_candidate,
        "request_creation_required": False,
        "create_goal_tool": create_goal_tool,
        "simple_workflow_goal_candidate": simple_goal_candidate,
        "goal_objective_request_id": objective_request_id,
    }
    if event not in {"user_prompt_submit", "pre_tool_use", "stop"}:
        result.update(status="PREPASS", severity="info", reason="event does not require Simple Workflow checks")
        return result
    if event == "pre_tool_use" and not create_goal_tool:
        result.update(status="PREPASS", severity="info", reason="tool is outside the Simple Workflow goal gate")
        return result
    if not current_path.is_file():
        if simple_goal_candidate:
            return block(result, "create_goal requires an active Simple Workflow review request")
        if create_goal_tool:
            result.update(status="PREPASS", severity="info", reason="create_goal is outside Simple Workflow scope")
            return result
        result.update(status="PREPASS", severity="info", reason="Simple Workflow is not activated for this session")
        return result

    current = read_json(current_path)
    request_id = metadata_request_id(current)
    if not request_id:
        if create_goal_tool and not simple_goal_candidate:
            result.update(status="PREPASS", severity="info", reason="create_goal is outside Simple Workflow scope")
            return result
        return invalid_current(
            event,
            result,
            "session current pointer is missing `request_id`",
            current_path=rel(root, current_path),
        )

    if create_goal_tool and not simple_goal_candidate:
        result.update(status="PREPASS", severity="info", reason="create_goal objective is outside Simple Workflow scope")
        return result
    if simple_goal_candidate and objective_request_id != request_id:
        return block(result, "Simple Workflow create_goal objective must name the selected request id")

    request_dir = root / ".simple" / "requests" / request_id
    if not request_dir.is_dir():
        return invalid_current(event, result, f"request `{request_id}` does not exist")
    state = read_json(request_dir / "state.json")
    phase = metadata_phase(state) or metadata_phase(current)
    goal_status = str(state.get("goal_status") or "pending").strip()
    workflow_version = state.get("workflow_version")
    plan_approval_status = str(state.get("plan_approval_status") or "").strip()
    approved_plan_fingerprint = str(state.get("approved_plan_fingerprint") or "").strip().lower()
    result.update(
        current_request_id=request_id,
        current_source="session",
        current_path=rel(root, current_path),
        phase=phase,
        goal_status=goal_status,
        workflow_version=workflow_version,
        plan_approval_status=plan_approval_status,
        approved_plan_fingerprint=approved_plan_fingerprint,
        validation_phase=PHASE_TO_VALIDATION.get(phase, "all"),
        preflight_required=True,
    )
    if phase not in PHASE_TO_VALIDATION:
        return invalid_current(event, result, f"phase `{phase or 'missing'}` is not allowed")

    if event == "pre_tool_use":
        return check_create_goal_gate(root, session_id, request_dir, objective_fingerprint, result)
    if event == "stop":
        return check_stop(result)
    return check_user_prompt(result)


def check_user_prompt(result: dict[str, Any]) -> dict[str, Any]:
    phase = str(result["phase"])
    if phase == "completed":
        result.update(
            status="PREPASS",
            severity="info",
            reason="completed Simple Workflow request does not capture follow-up prompts",
            preflight_required=False,
        )
        return result

    warnings = [CONTINUATION_WARNING]
    result["prompt_relevant"] = True
    result["continuation_required"] = True
    if result.get("workflow_version") == 2 and result.get("plan_approval_status") == "pending":
        warnings.append(
            "Current v2 plan awaits explicit user approval; do not execute the pending plan or revised scope."
        )
    if result.get("goal_status") == "pending" and result.get("plan_approval_status") == "approved":
        warnings.append("The reviewed plan is approved and ready for Goal reconciliation.")
    result.update(
        status="WARN",
        severity="warning",
        reason="; ".join(warnings),
        warnings=warnings,
        validation={"status": "SKIPPED", "reason": "UserPromptSubmit uses lightweight state checks"},
    )
    return result


def check_create_goal_gate(
    root: Path,
    session_id: str,
    request_dir: Path,
    objective_fingerprint: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    if result["phase"] != "review":
        return block(result, "create_goal is allowed only while the Simple Workflow request is in review phase")
    if result["goal_status"] != "pending":
        return block(result, "create_goal has already started or completed for this Simple Workflow request")
    current_fingerprint = plan_fp(request_dir / "plan.md")
    if result.get("workflow_version") == 2:
        if result.get("plan_approval_status") != "approved":
            return block(result, "create_goal requires recorded user approval for the current plan")
        if result.get("approved_plan_fingerprint") != f"sha256:{current_fingerprint}":
            return block(result, "create_goal requires approved_plan_fingerprint to match the current plan")
    if objective_fingerprint != current_fingerprint:
        return block(result, "Simple Workflow create_goal objective must name the current plan fingerprint")

    result["artifact_status"] = artifacts(request_dir)
    result["validation"] = run_validator(root, session_id, "review")
    result["review_status"] = review_ready(request_dir)
    if result["validation"]["status"] != "PASS":
        return block(result, result["validation"].get("reason", "review validation failed"))
    if result["review_status"]["status"] != "pass":
        return block(result, result["review_status"]["reason"])
    result.update(
        status="CREATE_GOAL_ALLOWED",
        severity="info",
        reason="review structure passed; create_goal may run after the agent confirms user approval intent",
        decision="allow",
    )
    return result


def check_stop(result: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    if result.get("workflow_version") == 2 and result.get("plan_approval_status") == "pending":
        warnings.append("Simple Workflow execution is waiting for user approval.")
    if warnings:
        result.update(
            status="WARN",
            severity="warning",
            reason="; ".join(warnings),
            warnings=warnings,
            validation={"status": "SKIPPED", "reason": "Stop uses lightweight state checks"},
        )
    else:
        result.update(
            status="PASS",
            severity="info",
            reason="Simple Workflow stop check passed",
            warnings=[],
            validation={"status": "SKIPPED", "reason": "Stop uses lightweight state checks"},
        )
    return result


def invalid_current(event: str, result: dict[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
    result.update(status="INVALID_CURRENT", severity="warning", reason=reason, **extra)
    if event == "pre_tool_use":
        result["decision"] = "block"
    return result


def block(result: dict[str, Any], reason: str) -> dict[str, Any]:
    result.update(status="BLOCKED", severity="warning", reason=reason, decision="block")
    return result


def to_wire_output(event: str, result: dict[str, Any]) -> dict[str, Any] | None:
    if event == "user_prompt_submit":
        if result.get("status") == "PREPASS":
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": json.dumps(result, ensure_ascii=False, sort_keys=True),
            }
        }
    if event == "pre_tool_use":
        if result.get("decision") != "block":
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": str(result.get("reason") or "Simple Workflow create_goal gate denied this call"),
            }
        }
    return None


def artifacts(directory: Path) -> dict[str, bool]:
    return {name: (directory / name).is_file() for name in ("plan.md", "review.md")}


def review_ready(directory: Path) -> dict[str, str]:
    review = directory / "review.md"
    plan = directory / "plan.md"
    if not review.is_file():
        return {"status": "missing", "reason": "`review.md` is required before goal execution"}
    text = review.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Reviewed Plan Fingerprint:\s*sha256:([0-9a-fA-F]{64})", text)
    if not match:
        return {"status": "invalid", "reason": "`review.md` must include reviewed plan fingerprint"}
    if match.group(1).lower() != plan_fp(plan):
        return {"status": "stale", "reason": "`review.md` fingerprint is stale"}
    if section(text, "## Verdict").strip() != "PASS":
        return {"status": "blocking", "reason": "`review.md` verdict must be exactly PASS"}
    return {"status": "pass", "reason": "review structure passed"}


def run_validator(root: Path, session_id: str, phase: str) -> dict[str, str]:
    validator = Path(__file__).resolve().with_name("validate_simple_workflow.py")
    if not validator.is_file():
        return {"status": "SKIPPED", "reason": "plugin-bundled validator missing"}
    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--root",
            str(root),
            "--current",
            "--session-id",
            session_id,
            "--phase",
            phase,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "reason": summarize_validator_output(result.stdout),
    }


def summarize_validator_output(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "validator produced no output"
    if not lines[0].startswith("FAIL "):
        return lines[0]
    detail = next((line.removeprefix("- ") for line in lines[1:] if line.startswith("- ")), "")
    next_action = next((line for line in lines[1:] if line.startswith("Next action:")), "")
    reason = lines[0]
    if detail:
        reason = f"{reason} {detail}"
    if next_action:
        reason = f"{reason}; {next_action}"
    return reason


def read_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"prompt": raw}
    return data if isinstance(data, dict) else {}


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_tool_name(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool", "name"):
        if isinstance(payload.get(key), str):
            return payload[key].strip()
    return ""


def extract_tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input") or payload.get("toolInput") or payload.get("arguments")
    return value if isinstance(value, dict) else {}


def extract_goal_objective(payload: dict[str, Any]) -> str:
    objective = extract_tool_input(payload).get("objective")
    return objective if isinstance(objective, str) else ""


def simple_goal_request_id(objective: str) -> str:
    match = SIMPLE_PLAN_PATH_RE.search(objective)
    return match.group("request_id") if match else ""


def goal_objective_fingerprint(objective: str) -> str:
    match = OBJECTIVE_FINGERPRINT_RE.search(objective)
    return match.group(1).lower() if match else ""


def is_create_goal_tool(payload: dict[str, Any]) -> bool:
    name = extract_tool_name(payload).casefold()
    parts = [part for part in re.split(r"(?:__|[.:/])", name) if part]
    return bool(parts) and parts[-1] == "create_goal"


def session_id_from(payload: dict[str, Any]) -> str:
    for key in ("session_id", "sessionId"):
        if isinstance(payload.get(key), str) and payload[key].strip():
            return safe(payload[key])
    scope = payload.get("hook_scope")
    if isinstance(scope, dict) and isinstance(scope.get("session_id"), str) and scope["session_id"].strip():
        return safe(scope["session_id"])
    return "no-session"


def metadata_phase(value: dict[str, Any]) -> str:
    return str(value.get("phase") or value.get("status") or "").strip()


def metadata_request_id(value: dict[str, Any]) -> str:
    return str(value.get("request_id") or value.get("id") or "").strip()


def norm_event(event: str) -> str:
    value = (event or "").replace("-", "_").lower()
    return {
        "userpromptsubmit": "user_prompt_submit",
        "pretooluse": "pre_tool_use",
    }.get(value, value or "unknown")


def safe(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in (value.strip() or "no-session"))[:120]


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def plan_fp(path: Path) -> str:
    return hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()


def section(text: str, heading: str) -> str:
    output: list[str] = []
    capture = False
    level = len(heading) - len(heading.lstrip("#"))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= level:
            break
        if capture:
            output.append(line)
    return "\n".join(output).strip()


if __name__ == "__main__":
    raise SystemExit(main())
