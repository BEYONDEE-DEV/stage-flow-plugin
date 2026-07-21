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
    ap.add_argument("--root", help="Use this authoritative workflow root without rediscovery.")
    ap.add_argument("--start", help="Start root discovery here instead of the process cwd.")
    ap.add_argument(
        "--multi-repo",
        action="store_true",
        help="Require an exact slot-manifest bundle root; otherwise require an explicit --root.",
    )
    ap.add_argument(
        "--resolve-root",
        action="store_true",
        help="Print the read-only root-resolution result and exit.",
    )
    ap.add_argument("--session-id", help="Session id used for continuation root discovery.")
    ap.add_argument("--request-id", help="Request id used for continuation and duplicate checks.")
    ap.add_argument(
        "--diagnostic",
        action="store_true",
        help="Print the internal audit result instead of hook wire output.",
    )
    args = ap.parse_args(argv)
    event = norm_event(args.event)
    payload = {} if args.resolve_root else read_payload()
    session_id = safe(args.session_id) if args.session_id else session_id_from(payload)
    objective_request_id = ""
    if event == "pre_tool_use" and is_create_goal_tool(payload):
        objective_request_id = simple_goal_request_id(extract_goal_objective(payload))
    request_id = safe(args.request_id) if args.request_id else objective_request_id
    start = Path(args.start).resolve() if args.start else Path.cwd().resolve()
    explicit_root = Path(args.root).resolve() if args.root else None
    resolution = resolve_workflow_root(
        start,
        explicit_root=explicit_root,
        multi_repo=args.multi_repo,
        session_id=session_id,
        request_id=request_id,
    )
    if args.resolve_root:
        if resolution.get("status") == "RESOLVED" and request_id and resolution.get("is_bundle"):
            resolution["duplicate"] = inspect_duplicate_requests(
                Path(str(resolution["workflow_root"])), request_id
            )
        print(json.dumps(resolution, ensure_ascii=False, sort_keys=True))
        return 0 if resolution.get("status") == "RESOLVED" else 2
    if resolution.get("status") != "RESOLVED":
        result = {
            "schema_version": "2",
            "event": event,
            "status": "UNRESOLVED_ROOT",
            "severity": "warning",
            "reason": resolution.get("reason", "workflow root could not be resolved"),
            "decision": "block" if event == "pre_tool_use" and objective_request_id else None,
            "root_resolution": resolution,
        }
    else:
        result = check_hook(
            event,
            Path(str(resolution["workflow_root"])),
            payload,
            resolution=resolution,
        )
    if args.diagnostic:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    wire_output = to_wire_output(event, result)
    if wire_output is not None:
        print(json.dumps(wire_output, ensure_ascii=False, sort_keys=True))
    elif event == "stop" and result.get("severity") == "warning":
        print(f"Simple Workflow WARN: {result.get('reason', 'state check failed')}", file=sys.stderr)
    return 0


def resolve_workflow_root(
    start: Path,
    *,
    explicit_root: Path | None = None,
    multi_repo: bool = False,
    session_id: str = "no-session",
    request_id: str = "",
) -> dict[str, Any]:
    """Resolve a workflow root without creating, moving, or editing project files."""
    start = (start.parent if start.is_file() else start).resolve()
    session_id = safe(session_id)
    request_id = safe(request_id) if request_id else ""
    if explicit_root is not None:
        root = explicit_root.resolve()
        bundle, manifest, _ = find_slot_bundle(root)
        is_bundle = multi_repo or bundle == root
        return resolved_root(
            start,
            root,
            "bundle" if is_bundle else "explicit",
            "explicit_root",
            manifest,
            is_bundle,
        )

    bundle, manifest, manifest_error = find_slot_bundle(start)
    if multi_repo:
        if bundle is None:
            detail = manifest_error or "no exact slot.path contains the discovery start"
            return {
                "status": "UNRESOLVED",
                "start": str(start),
                "root_kind": "bundle",
                "source": "slot_manifest",
                "manifest": str(manifest) if manifest else None,
                "reason": f"multi-repo workflow root is unresolved ({detail}); pass an explicit --root",
            }
        return resolved_root(start, bundle, "bundle", "slot_manifest_multi_repo", manifest, True)

    session_root = nearest_session_root(start, session_id, request_id)
    continuation_request_id = request_id
    if not continuation_request_id and session_root is not None:
        continuation_request_id = session_pointer_request_id(session_root, session_id)

    if bundle is not None and bundle_pointer_matches(bundle, session_id, continuation_request_id):
        return resolved_root(start, bundle, "bundle", "slot_manifest_continuation", manifest, True)

    if session_root is not None:
        return resolved_root(start, session_root, "single_repo", "session_continuation", manifest, False)

    repo_root = nearest_repo_root(start)
    return resolved_root(start, repo_root, "single_repo", "single_repo", manifest, False, manifest_error)


def resolved_root(
    start: Path,
    root: Path,
    root_kind: str,
    source: str,
    manifest: Path | None,
    is_bundle: bool,
    note: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "RESOLVED",
        "start": str(start),
        "workflow_root": str(root.resolve()),
        "root_kind": root_kind,
        "source": source,
        "is_bundle": is_bundle,
        "manifest": str(manifest) if manifest else None,
    }
    if note:
        result["note"] = note
    return result


def find_slot_bundle(start: Path) -> tuple[Path | None, Path | None, str | None]:
    """Return only a bundle path named exactly by an ancestor slot manifest."""
    start = start.resolve()
    for ancestor in (start, *start.parents):
        manifest = ancestor / ".stageflow-worktrees" / "slots.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            return None, manifest, f"slot manifest is malformed: {exc}"
        slots = data.get("slots") if isinstance(data, dict) else None
        if not isinstance(slots, dict):
            return None, manifest, "slot manifest is missing an object `slots`"
        matches: list[Path] = []
        for slot in slots.values():
            if not isinstance(slot, dict) or not isinstance(slot.get("path"), str):
                continue
            raw_path = Path(slot["path"]).expanduser()
            slot_path = (raw_path if raw_path.is_absolute() else ancestor / raw_path).resolve()
            if path_contains(slot_path, start):
                matches.append(slot_path)
        if not matches:
            return None, manifest, "slot manifest has no exact slot.path containing the discovery start"
        return max(matches, key=lambda value: len(value.parts)), manifest, None
    return None, None, "no ancestor slot manifest was found"


def path_contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def bundle_pointer_matches(bundle: Path, session_id: str, request_id: str) -> bool:
    selected = session_pointer_request_id(bundle, session_id)
    if not selected:
        return False
    return not request_id or selected == request_id


def session_pointer_request_id(root: Path, session_id: str) -> str:
    current = read_json(root / ".simple" / "sessions" / safe(session_id) / "current.json")
    return metadata_request_id(current)


def nearest_session_root(start: Path, session_id: str, request_id: str) -> Path | None:
    repo_root = nearest_repo_root(start)
    for candidate in (start, *start.parents):
        if not path_contains(repo_root, candidate):
            break
        current_path = candidate / ".simple" / "sessions" / safe(session_id) / "current.json"
        if not current_path.is_file():
            continue
        selected = session_pointer_request_id(candidate, session_id)
        if selected and (not request_id or selected == request_id):
            return candidate
    return None


def nearest_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def inspect_duplicate_requests(bundle_root: Path, request_id: str) -> dict[str, Any]:
    canonical = bundle_root / ".simple" / "requests" / request_id
    duplicates: list[Path] = []
    if bundle_root.is_dir():
        try:
            children = tuple(bundle_root.iterdir())
        except OSError:
            children = ()
        duplicates = sorted(
            child / ".simple" / "requests" / request_id
            for child in children
            if child.is_dir()
            and (child / ".git").exists()
            and (child / ".simple" / "requests" / request_id).is_dir()
        )
    if not duplicates:
        return {
            "status": "none",
            "canonical_path": str(canonical),
            "duplicate_paths": [],
        }

    artifact_names = ("plan.md", "review.md", "state.json")
    comparisons: dict[str, dict[str, bool]] = {}
    identical = canonical.is_dir()
    for duplicate in duplicates:
        artifact_matches: dict[str, bool] = {}
        for name in artifact_names:
            canonical_file = canonical / name
            duplicate_file = duplicate / name
            matches = (
                canonical_file.is_file()
                and duplicate_file.is_file()
                and canonical_file.read_bytes() == duplicate_file.read_bytes()
            )
            artifact_matches[name] = matches
            identical = identical and matches
        comparisons[str(duplicate)] = artifact_matches

    status = "identical" if identical else "divergent"
    duplicate_text = ", ".join(str(path) for path in duplicates)
    if identical:
        warning = (
            f"Identical Simple Workflow duplicate detected; canonical bundle request is {canonical}; "
            f"duplicate request(s): {duplicate_text}. Continue with the canonical bundle. "
            "After confirming the child copies are no longer needed, manually remove or align them; no files were changed."
        )
    else:
        warning = (
            f"Divergent Simple Workflow duplicate detected; canonical bundle request is {canonical}; "
            f"conflicting request(s): {duplicate_text}. Manually remove the stale child copy or align its "
            "plan.md, review.md, and state.json with the canonical request, then retry the same operation; no files were changed."
        )
    return {
        "status": status,
        "canonical_path": str(canonical),
        "duplicate_paths": [str(path) for path in duplicates],
        "artifact_matches": comparisons,
        "warning": warning,
    }


def check_hook(
    event: str,
    root: Path,
    payload: dict[str, Any],
    *,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "invocation_cwd": str((resolution or {}).get("start") or root),
        "workflow_root": str(root),
        "root_kind": str((resolution or {}).get("root_kind") or "explicit"),
        "root_source": str((resolution or {}).get("source") or "caller"),
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

    duplicate = inspect_duplicate_requests(root, request_id) if (resolution or {}).get("is_bundle") else None
    if duplicate and duplicate["status"] != "none":
        result["duplicate"] = duplicate
        result["warnings"] = [duplicate["warning"]]
        if duplicate["status"] == "divergent" and event == "pre_tool_use":
            return block(result, duplicate["warning"])

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
        duplicate_warnings = list(result.get("warnings") or [])
        if duplicate_warnings:
            result.update(
                status="WARN",
                severity="warning",
                reason="; ".join(duplicate_warnings),
                warnings=duplicate_warnings,
                prompt_relevant=False,
                continuation_required=False,
                preflight_required=False,
                validation={"status": "SKIPPED", "reason": "UserPromptSubmit reports duplicate state only"},
            )
            return result
        result.update(
            status="PREPASS",
            severity="info",
            reason="completed Simple Workflow request does not capture follow-up prompts",
            preflight_required=False,
        )
        return result

    warnings = list(result.get("warnings") or [])
    warnings.append(CONTINUATION_WARNING)
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
    warnings: list[str] = list(result.get("warnings") or [])
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
