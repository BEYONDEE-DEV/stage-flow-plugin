#!/usr/bin/env python3
"""Validate the simplified `.simple` plan-review workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PHASES = {"plan", "review", "completed"}
VALIDATION_PHASES = {"plan", "review", "all"}
NO_BLOCKING = {
    "none",
    "no blocking issues",
    "no blockers",
    "no flow issues",
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
HANGUL_RE = re.compile(r"[가-힣]")

VALIDATOR_TEMPLATES = {
    "index": '''{
  "version": "1",
  "requests": [
    {"id": "20260609-1120-simple-workflow-plugin", "title": "Simple workflow request", "status": "plan", "created_at": "2026-06-09T02:20:00Z", "updated_at": "2026-06-09T02:30:00Z"}
  ]
}\n''',
    "current": '''{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "phase": "plan",
  "activated_by": "explicit_skill_invocation"
}\n''',
    "state": '''{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "phase": "plan",
  "last_validated_at": null
}\n''',
    "plan": '''# Plan

## Summary

요청된 변경의 목적과 접근 방식을 간단히 설명한다.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| REQ-001 | `REQ-001`에서 요구한 동작을 구현한다. |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `path/or/module` | `REQ-001`을 만족하는 가장 작은 변경을 적용한다. |

## Flow Check

- 계획된 변경과 관련된 사용자 동선, 상태 전이, 데이터 흐름, 실패/재시도 경로, 검증 흐름을 확인한다.
- 이번 변경이 만든 문제가 아니더라도 관련 흐름 문제를 발견하면 사용자에게 알리고, 범위 밖이면 범위 밖이라고 명시한다.

## Validation

- `REQ-001`이 만족되는지 증명하는 대상 검사를 실행한다.

## Out Of Scope

- `## Requirements Coverage`에 포함되지 않은 작업은 범위에서 제외한다.
''',
    "review": '''# Review

## Reviewed Plan Fingerprint

Reviewed Plan Fingerprint: sha256:<hex>

## Reviewer

subagent

## Verdict

PASS

## Blocking Issues

차단 없음

## Flow Check

사용자에게 알려야 할 관련 흐름 문제 없음

## Question Depth Check

상위 질문 없음

## Notes

현재 `plan.md` fingerprint에 대한 내부 리뷰가 통과했다.
''',
}


@dataclass
class Ctx:
    root: Path
    simple: Path
    request_id: str
    request_dir: Path
    state: dict[str, Any]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate simplified Simple Workflow `.simple` artifacts.")
    ap.add_argument("--print-template", choices=sorted(VALIDATOR_TEMPLATES))
    ap.add_argument("--root", default=".")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--current", action="store_true")
    g.add_argument("--request")
    ap.add_argument("--session-id", default="no-session")
    ap.add_argument("--phase", choices=sorted(VALIDATION_PHASES), default="all")
    args = ap.parse_args(argv)
    if args.print_template:
        print(VALIDATOR_TEMPLATES[args.print_template].rstrip())
        return 0
    errors: list[str] = []
    ctx = resolve(Path(args.root).resolve(), args.current, args.request, args.session_id, errors)
    if ctx:
        validate(ctx, args.phase, errors)
    if errors:
        print(f"FAIL {args.phase}:")
        for e in errors:
            print(f"- {e}")
        print(f"Next action: repair `{next_artifact(errors)}` and re-run validation.")
        return 1
    print(f"PASS {args.phase}: {ctx.request_id if ctx else Path(args.root).resolve()}")
    return 0


def resolve(root: Path, current: bool, req: str | None, session_id: str, errors: list[str]) -> Ctx | None:
    simple = root / ".simple"
    if not simple.is_dir():
        errors.append("missing `.simple` directory")
        return None
    index = read_json(simple / "index.json", "`.simple/index.json`", errors)
    request_id = req or ""
    if current or not request_id:
        cur_path = simple / "sessions" / safe(session_id) / "current.json"
        cur = read_json(cur_path, f"`{rel(root, cur_path)}`", errors)
        request_id = str(cur.get("request_id") or "").strip()
        if not request_id:
            errors.append("session current pointer must include `request_id`")
    if not request_id:
        return None
    if isinstance(index.get("requests"), list) and not any(isinstance(x, dict) and x.get("id") == request_id for x in index["requests"]):
        errors.append(f"request `{request_id}` is not registered in `.simple/index.json`")
    request_dir = simple / "requests" / request_id
    if not request_dir.is_dir():
        errors.append(f"missing request folder `.simple/requests/{request_id}`")
        return None
    state = read_json(request_dir / "state.json", "`state.json`", errors)
    if state.get("request_id") and state.get("request_id") != request_id:
        errors.append("`state.json` request_id must match selected request")
    phase = str(state.get("phase") or "").strip()
    if phase and phase not in PHASES:
        errors.append(f"`state.json` phase `{phase}` is not allowed")
    return Ctx(root, simple, request_id, request_dir, state)


def validate(ctx: Ctx, phase: str, errors: list[str]) -> None:
    validate_meta(ctx, errors)
    if phase in {"plan", "review", "all"}:
        validate_plan(ctx, errors)
    if phase in {"review", "all"}:
        validate_review(ctx, errors)


def validate_meta(ctx: Ctx, errors: list[str]) -> None:
    phase = str(ctx.state.get("phase") or "").strip()
    if not phase:
        errors.append("`state.json` must include `phase`")
    elif phase not in PHASES:
        errors.append(f"`state.json` phase `{phase}` is not allowed")


def validate_plan(ctx: Ctx, errors: list[str]) -> None:
    text = read_md(ctx.request_dir / "plan.md", "`plan.md`", errors)
    if not text:
        return
    need_heads(text, "plan.md", ["# Plan", "## Summary", "## Requirements Coverage", "## Change Targets", "## Flow Check", "## Validation", "## Out Of Scope"], errors)
    ids = req_ids(text)
    if not ids:
        errors.append("`plan.md` must include at least one `REQ-###` requirement id")
        return
    if not section(text, "## Flow Check"):
        errors.append("`plan.md` Flow Check must describe relevant affected product or system flow problems, including pre-existing issues discovered during planning")
    require_korean_sections(
        text,
        "plan.md",
        ["## Summary", "## Requirements Coverage", "## Change Targets", "## Flow Check", "## Validation", "## Out Of Scope"],
        errors,
    )
    coverage = section(text, "## Requirements Coverage")
    for rid in ids:
        row = coverage_row(coverage, rid)
        if not row:
            errors.append(f"`plan.md` Requirements Coverage must include a table row for `{rid}`")
        elif not meaningful_plan_cell(row):
            errors.append(f"`plan.md` Requirements Coverage must include a concrete plan for `{rid}`")


def validate_review(ctx: Ctx, errors: list[str]) -> None:
    text = read_md(ctx.request_dir / "review.md", "`review.md`", errors)
    if not text:
        return
    need_heads(text, "review.md", ["# Review", "## Reviewed Plan Fingerprint", "## Reviewer", "## Verdict", "## Blocking Issues", "## Flow Check", "## Question Depth Check"], errors)
    fp = reviewed_fp(text)
    if not fp:
        errors.append("`review.md` must include `Reviewed Plan Fingerprint: sha256:<hex>`")
    elif fp != plan_fp(ctx.request_dir):
        errors.append("`review.md` reviewed plan fingerprint is stale")
    if "pass" not in section(text, "## Verdict").lower():
        errors.append("`review.md` verdict must be `PASS` before goal execution")
    if norm(section(text, "## Blocking Issues")) not in NO_BLOCKING:
        errors.append("`review.md` Blocking Issues must say `No blocking issues` or `None`")
    if norm(section(text, "## Flow Check")) not in NO_BLOCKING:
        errors.append("`review.md` Flow Check must say there are no unreported relevant flow issues")
    if norm(section(text, "## Question Depth Check")) not in QUESTION_DEPTH_OK:
        errors.append("`review.md` Question Depth Check must say `No unresolved higher-level questions` or `None`")
    validate_review_language(text, errors)


def read_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing {label}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        errors.append(f"invalid {label}: {exc}")
        return {}


def read_md(path: Path, label: str, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing {label}")
        return ""
    return read_file(path)


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def need_heads(text: str, artifact: str, heads: list[str], errors: list[str]) -> None:
    lines = {x.strip() for x in text.splitlines()}
    for h in heads:
        if h not in lines:
            errors.append(f"`{artifact}` must include `{h}`")


def require_korean_sections(text: str, artifact: str, heads: list[str], errors: list[str]) -> None:
    for heading in heads:
        body = section(text, heading)
        if body and not HANGUL_RE.search(body):
            errors.append(f"`{artifact}` section `{heading}` must include Korean body text")


def validate_review_language(text: str, errors: list[str]) -> None:
    for heading, allowed in (
        ("## Blocking Issues", NO_BLOCKING),
        ("## Flow Check", NO_BLOCKING),
        ("## Question Depth Check", QUESTION_DEPTH_OK),
    ):
        body = section(text, heading)
        if body and norm(body) not in allowed and not HANGUL_RE.search(body):
            errors.append(f"`review.md` section `{heading}` must use Korean body text or an allowed fixed status")
    notes = section(text, "## Notes")
    if notes and not HANGUL_RE.search(notes):
        errors.append("`review.md` section `## Notes` must include Korean body text")


def req_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\bREQ-\d{3}\b", text)))


def coverage_row(coverage: str, rid: str) -> list[str]:
    for line in coverage.splitlines():
        if rid not in line or "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == rid:
            return cells
    return []


def meaningful_plan_cell(row: list[str]) -> bool:
    if len(row) < 2:
        return False
    plan = row[1].strip()
    return bool(plan) and plan not in {"-", "TBD", "TODO", "N/A"}


def plan_fp(request_dir: Path) -> str:
    return hashlib.sha256((request_dir / "plan.md").read_bytes() if (request_dir / "plan.md").is_file() else b"").hexdigest()


def reviewed_fp(text: str) -> str:
    return match_fp(r"Reviewed Plan Fingerprint:\s*sha256:([0-9a-fA-F]{64})", text)


def match_fp(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).lower() if m else ""


def norm(v: str) -> str:
    return re.sub(r"\s+", " ", v.strip().strip(".:")).lower()


def safe(v: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in (v.strip() or "no-session"))[:120]


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def section(text: str, heading: str) -> str:
    out = []
    cap = False
    level = len(heading) - len(heading.lstrip("#"))
    for line in text.splitlines():
        s = line.strip()
        if s == heading:
            cap = True
            continue
        if cap and s.startswith("#") and len(s) - len(s.lstrip("#")) <= level:
            break
        if cap:
            out.append(line)
    return "\n".join(out).strip()


def next_artifact(errors: list[str]) -> str:
    j = "\n".join(errors)
    for name in ("plan.md", "review.md", "state.json", "current.json", "index.json"):
        if name in j:
            return name
    return "workflow artifacts"


if __name__ == "__main__":
    raise SystemExit(main())
