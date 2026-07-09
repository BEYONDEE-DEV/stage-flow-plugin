#!/usr/bin/env python3
"""Fast hook auditor for the simplified Simple Workflow."""
from __future__ import annotations

import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from typing import Any

PHASE_TO_VALIDATION = {"plan": "plan", "review": "review", "completed": "all"}
PROCEED_RE = re.compile(r"\b(approve|approved|go ahead|proceed|implement)\b|승인|진행|실행", re.I)
EXPLICIT_RE = re.compile(r"simple[- ]workflow|\.simple", re.I)
CONTINUATION_WARNING = (
    "Active Simple Workflow request exists; continue Simple Workflow rules even if the prompt did not mention the plugin."
)
NO_BLOCKING = {
    "none",
    "no blocking issues",
    "no blockers",
    "0",
    "zero",
    "없음",
    "차단 없음",
    "흐름 문제 없음",
    "계획된 변경으로 인한 흐름 문제 없음",
    "변경 흐름 문제 없음",
    "관련 흐름 문제 없음",
    "사용자에게 알려야 할 관련 흐름 문제 없음",
    "미보고 흐름 문제 없음",
}
QUESTION_DEPTH_OK = {
    "none",
    "no unresolved higher-level questions",
    "question depth checks passed",
    "no question depth issues",
    "상위 질문 없음",
    "질문 깊이 문제 없음",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check simplified Simple Workflow hook state.")
    ap.add_argument("--event", default="user_prompt_submit")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    result = check_hook(norm_event(args.event), Path(args.root).resolve(), read_payload())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def check_hook(event: str, root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    prompt = extract_prompt(payload) if event == "user_prompt_submit" else ""
    explicit = event == "user_prompt_submit" and bool(EXPLICIT_RE.search(prompt))
    proceed = event == "user_prompt_submit" and bool(PROCEED_RE.search(prompt))
    session_id = session_id_from(payload)
    current_path = root / ".simple" / "sessions" / safe(session_id) / "current.json"
    result: dict[str, Any] = {
        "schema_version":"1", "event":event, "cwd":str(root),
        "hook_scope":{"session_id":session_id, "state_dir":f".simple/hook-state/sessions/{session_id}/main"},
        "explicit_simple_workflow_invocation": explicit,
        "prompt_relevant": explicit or proceed,
        "continuation_required": False,
        "preflight_required": False,
        "request_creation_required": False,
    }
    if event not in {"user_prompt_submit", "stop"}:
        result.update(status="PREPASS", severity="info", reason="event does not require simplified workflow checks")
        return result
    if not current_path.is_file():
        if explicit:
            result.update(status="REQUEST_REQUIRED", severity="warning", reason="explicit Simple Workflow invocation must create a request", request_creation_required=True, validation={"status":"SKIPPED","reason":"no session current pointer"})
        else:
            result.update(status="PREPASS", severity="info", reason="Simple Workflow is not activated for this session")
        return result
    current = read_json(current_path)
    request_id = str(current.get("request_id") or "").strip()
    if not request_id:
        result.update(status="INVALID_CURRENT", severity="warning", reason="session current pointer is missing `request_id`", current_path=rel(root,current_path), validation={"status":"SKIPPED","reason":"invalid current pointer"})
        return result
    request_dir = root / ".simple" / "requests" / request_id
    state = read_json(request_dir / "state.json")
    phase = str(state.get("phase") or current.get("phase") or "").strip()
    result.update(current_request_id=request_id, current_source="session", current_path=rel(root,current_path), phase=phase, validation_phase=PHASE_TO_VALIDATION.get(phase,"all"), preflight_required=True)
    if not request_dir.is_dir():
        result.update(status="STALE_CURRENT", severity="warning", reason=f"request `{request_id}` does not exist")
        return result
    if phase == "completed" and explicit:
        result.update(status="COMPLETED_CURRENT", severity="warning", reason="session current points at a completed request; create a new request before continuing", request_creation_required=True)
        return result
    if phase not in PHASE_TO_VALIDATION:
        result.update(status="INVALID_CURRENT", severity="warning", reason=f"phase `{phase or 'missing'}` is not allowed")
        return result
    result["artifact_status"] = artifacts(request_dir)
    result["validation"] = run_validator(root, session_id, PHASE_TO_VALIDATION[phase])
    warnings = []
    miss = missing_for_phase(phase, result["artifact_status"])
    if miss: warnings.append(miss)
    continuation = event == "user_prompt_submit" and phase in {"plan", "review"} and not explicit and not proceed
    if continuation:
        result["prompt_relevant"] = True
        result["continuation_required"] = True
        warnings.append(CONTINUATION_WARNING)
    if proceed:
        ready = review_ready(request_dir)
        result["proceed_prompt"] = True
        result["review_status"] = ready
        if result["validation"]["status"] == "FAIL":
            warnings.append(result["validation"].get("reason","validation failed"))
        if ready["status"] != "pass":
            warnings.append(ready["reason"])
            result.update(status="BLOCKED", severity="warning", reason="review must pass before goal execution", warnings=warnings)
            return result
        if warnings:
            result.update(status="BLOCKED", severity="warning", reason="workflow validation must pass before goal execution", warnings=warnings)
            return result
        result.update(status="PROCEED_ALLOWED", severity="info", reason="review passed; create_goal may be invoked", warnings=warnings)
        return result
    if result["validation"]["status"] == "FAIL": warnings.append(result["validation"].get("reason","validation failed"))
    if warnings: result.update(status="WARN", severity="warning", reason="; ".join(warnings), warnings=warnings)
    else: result.update(status="PASS", severity="info", reason="simplified workflow preflight passed", warnings=[])
    return result


def artifacts(d: Path) -> dict[str,bool]: return {n:(d/n).is_file() for n in ("plan.md","review.md")}
def missing_for_phase(phase: str, st: dict[str,bool]) -> str:
    need={"plan":("plan.md",),"review":("plan.md","review.md"),"completed":("plan.md","review.md")}.get(phase,())
    missing=[n for n in need if not st.get(n)]
    return "missing required artifact(s): "+", ".join(missing) if missing else ""

def review_ready(d: Path) -> dict[str,str]:
    p=d/"review.md"; plan=d/"plan.md"
    if not p.is_file(): return {"status":"missing","reason":"`review.md` is required before goal execution"}
    txt=p.read_text(encoding="utf-8", errors="ignore")
    m=re.search(r"Reviewed Plan Fingerprint:\s*sha256:([0-9a-fA-F]{64})", txt)
    if not m: return {"status":"invalid","reason":"`review.md` must include reviewed plan fingerprint"}
    if m.group(1).lower()!=plan_fp(plan): return {"status":"stale","reason":"`review.md` fingerprint is stale"}
    if norm(section(txt,"## Blocking Issues")) not in NO_BLOCKING: return {"status":"blocking","reason":"`review.md` must have no blocking issues"}
    if norm(section(txt,"## Flow Check")) not in NO_BLOCKING | {"no flow issues"}:
        return {"status":"blocking","reason":"`review.md` must have no unreported relevant flow issues"}
    if norm(section(txt,"## Question Depth Check")) not in QUESTION_DEPTH_OK:
        return {"status":"blocking","reason":"`review.md` must have no unresolved higher-level questions"}
    if "pass" not in section(txt,"## Verdict").lower(): return {"status":"blocking","reason":"`review.md` verdict must be PASS"}
    return {"status":"pass","reason":"review passed"}

def run_validator(root: Path, sid: str, phase: str) -> dict[str,str]:
    v = Path(__file__).resolve().with_name("validate_simple_workflow.py")
    if not v.is_file(): return {"status":"SKIPPED","reason":"plugin-bundled validator missing"}
    r=subprocess.run([sys.executable,str(v),"--root",str(root),"--current","--session-id",sid,"--phase",phase], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    first=r.stdout.strip().splitlines()[0] if r.stdout.strip() else "validator produced no output"
    return {"status":"PASS" if r.returncode==0 else "FAIL", "reason":first}

def read_payload() -> dict[str,Any]:
    try: raw=sys.stdin.read()
    except OSError: return {}
    if not raw.strip(): return {}
    try: data=json.loads(raw)
    except json.JSONDecodeError: return {"prompt":raw}
    return data if isinstance(data,dict) else {}

def read_json(path: Path) -> dict[str,Any]:
    try: data=json.loads(path.read_text(encoding="utf-8")); return data if isinstance(data,dict) else {}
    except Exception: return {}

def extract_prompt(p: dict[str,Any]) -> str:
    for k in ("prompt","message","user_prompt","input"):
        if isinstance(p.get(k),str): return p[k]
    return ""

def session_id_from(p: dict[str,Any]) -> str:
    for k in ("session_id","sessionId"):
        if isinstance(p.get(k),str) and p[k].strip(): return safe(p[k])
    scope=p.get("hook_scope")
    if isinstance(scope,dict) and isinstance(scope.get("session_id"),str) and scope["session_id"].strip(): return safe(scope["session_id"])
    return "no-session"

def norm_event(e: str) -> str:
    v=(e or "").replace("-","_").lower()
    return "user_prompt_submit" if v=="userpromptsubmit" else (v or "unknown")
def safe(v: str) -> str: return "".join(c if c.isalnum() or c in "-_." else "_" for c in (v.strip() or "no-session"))[:120]
def rel(root: Path, path: Path) -> str:
    try: return path.relative_to(root).as_posix()
    except ValueError: return str(path)
def plan_fp(p: Path) -> str: return hashlib.sha256(p.read_bytes() if p.is_file() else b"").hexdigest()
def norm(v: str) -> str: return re.sub(r"\s+"," ",v.strip().strip(".:")).lower()
def section(text: str, heading: str) -> str:
    out=[]; cap=False; level=len(heading)-len(heading.lstrip("#"))
    for line in text.splitlines():
        s=line.strip()
        if s==heading: cap=True; continue
        if cap and s.startswith("#") and len(s)-len(s.lstrip("#"))<=level: break
        if cap: out.append(line)
    return "\n".join(out).strip()

if __name__ == "__main__": raise SystemExit(main())
