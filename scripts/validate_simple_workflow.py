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
VALIDATION_PHASES = {"plan", "review", "completion", "all"}
VALIDATION_STATE_PHASE = {"plan": "plan", "review": "review", "completion": "review", "all": "completed"}
GOAL_STATUSES = {"pending", "active", "completing", "completed"}
PLAN_APPROVAL_STATUSES = {"pending", "approved"}
BLOCKING_OK = {
    "none",
    "no blocking issues",
    "no blockers",
    "0",
    "zero",
    "없음",
    "차단 없음",
}
REVIEW_FIXED_STATUSES = {
    "none",
    "no blocking issues",
    "no flow issues",
    "no unresolved higher-level questions",
    "차단 없음",
    "흐름 문제 없음",
    "상위 질문 없음",
}
HANGUL_RE = re.compile(r"[가-힣]")
REQUEST_ID_RE = re.compile(r"^\d{8}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
OBVIOUS_PLACEHOLDER_RE = re.compile(
    r"(?:TODO|TBD|N/?A|PLACEHOLDER|미정|나중에|추후|작성\s*필요|증거\s*필요)",
    re.IGNORECASE,
)
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
INTENT_CHALLENGE_ID_RE = re.compile(r"^IC-\d{3}$")
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
ALLOWED_V2_STATES = {
    ("plan", "pending", "pending"),
    ("review", "pending", "pending"),
    ("review", "approved", "pending"),
    ("review", "approved", "active"),
    ("review", "pending", "active"),
    ("review", "approved", "completing"),
    ("completed", "approved", "completed"),
}

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
  "activated_by": "explicit_skill_invocation",
  "workflow_root": "/absolute/path/to/project"
}\n''',
    "state": '''{
  "request_id": "20260609-1120-simple-workflow-plugin",
  "workflow_version": 2,
  "intent_challenge_version": 1,
  "phase": "plan",
  "plan_approval_status": "pending",
  "goal_status": "pending",
  "last_validated_at": null
}\n''',
    "plan": '''# Plan

## Summary

요청된 변경의 목적과 접근 방식을 간단히 설명한다.

## Outcome And Completion Criteria

- 사용자가 변경된 요청 상태를 validator 명령 출력에서 확인할 수 있고 관련 테스트가 통과한다.

## Requirements Coverage

| Requirement | Plan | Completion Evidence |
| --- | --- | --- |
| REQ-001 | `REQ-001`에서 요구한 동작을 구현한다. | 관련 테스트와 실제 사용자 흐름의 상태 출력으로 완료를 확인한다. |

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

## Intent Challenge Check

### Findings

| Finding | User Decision Or Resolution | Verdict |
| --- | --- | --- |
| NONE | 요구사항 타당성과 대안을 검토했으며 사용자 결정이 필요한 material finding이 없다. | PASS |

### Intent Challenge Final Verdict

PASS

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
    index: dict[str, Any]
    index_entry: dict[str, Any]
    current: dict[str, Any]
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
    requests = index.get("requests")
    if not isinstance(requests, list):
        errors.append("`.simple/index.json` must include a `requests` list")
        requests = []
    request_id = req or ""
    cur: dict[str, Any] = {}
    if current or not request_id:
        cur_path = simple / "sessions" / safe(session_id) / "current.json"
        cur = read_json(cur_path, f"`{rel(root, cur_path)}`", errors)
        validate_current_workflow_root(cur, root, errors)
        request_id = metadata_request_id(cur)
        validate_request_id_aliases(cur, "current.json", errors)
        if not request_id:
            errors.append("session current pointer must include `request_id`")
    if not request_id:
        return None
    if not REQUEST_ID_RE.fullmatch(request_id):
        errors.append(f"request id `{request_id}` must match `YYYYMMDD-HHMM-short-slug`")
        return None
    matching_entries = [
        entry
        for entry in requests
        if isinstance(entry, dict) and metadata_request_id(entry) == request_id
    ]
    if len(matching_entries) != 1:
        errors.append(
            f"request `{request_id}` must be registered exactly once in `.simple/index.json`"
        )
    index_entry = matching_entries[0] if matching_entries else {}
    validate_request_id_aliases(index_entry, "index.json request entry", errors)
    request_dir = simple / "requests" / request_id
    requests_root = (simple / "requests").resolve()
    try:
        request_dir.resolve().relative_to(requests_root)
    except ValueError:
        errors.append(f"request `{request_id}` resolves outside `.simple/requests`")
        return None
    if not request_dir.is_dir():
        errors.append(f"missing request folder `.simple/requests/{request_id}`")
        return None
    state = read_json(request_dir / "state.json", "`state.json`", errors)
    state_request_id = metadata_request_id(state)
    if not state_request_id:
        errors.append("`state.json` must include `request_id` or legacy `id`")
    for key in ("request_id", "id"):
        value = str(state.get(key) or "").strip()
        if value and value != request_id:
            errors.append(f"`state.json` {key} must match selected request")
    validate_metadata_phases(cur, state, index_entry, errors)
    validate_goal_metadata(state, request_dir, errors)
    return Ctx(root, simple, request_id, request_dir, index, index_entry, cur, state)


def validate_current_workflow_root(current: dict[str, Any], root: Path, errors: list[str]) -> None:
    if "workflow_root" not in current:
        return
    value = current.get("workflow_root")
    if not isinstance(value, str) or not value.strip():
        errors.append("`current.json` workflow_root must be a non-empty canonical absolute path")
        return
    raw = value.strip()
    path = Path(raw)
    if not path.is_absolute():
        errors.append("`current.json` workflow_root must be absolute")
        return
    if raw != str(path) or path.resolve() != path:
        errors.append("`current.json` workflow_root must use canonical path text without symlink aliases")
        return
    if path != root.resolve():
        errors.append("`current.json` workflow_root must match the validator root")


def validate(ctx: Ctx, phase: str, errors: list[str]) -> None:
    validate_meta(ctx, errors)
    state_phase = metadata_phase(ctx.state)
    expected_phase = VALIDATION_STATE_PHASE[phase]
    if state_phase and state_phase != expected_phase:
        errors.append(
            f"validation phase `{phase}` requires `state.json` phase `{expected_phase}`, got `{state_phase}`"
        )
    if phase in {"plan", "review", "completion", "all"}:
        validate_plan(ctx, errors)
    if phase in {"review", "completion", "all"}:
        validate_review(ctx, errors)
    if phase in {"completion", "all"}:
        validate_completion(ctx, phase, errors)
        validate_completion_review(ctx, required=phase == "completion", errors=errors)


def validate_meta(ctx: Ctx, errors: list[str]) -> None:
    phase = metadata_phase(ctx.state)
    if not phase:
        errors.append("`state.json` must include `phase`")
    elif phase not in PHASES:
        errors.append(f"`state.json` phase `{phase}` is not allowed")
    version = ctx.state.get("workflow_version")
    if version is not None and (type(version) is not int or version != 2):
        errors.append("`state.json` workflow_version must be integer `2` when present")
    if "intent_challenge_version" in ctx.state:
        challenge_version = ctx.state["intent_challenge_version"]
        if type(challenge_version) is not int or challenge_version != 1:
            errors.append("`state.json` intent_challenge_version must be exact integer `1` when present")
        elif not is_v2(ctx.state):
            errors.append("`state.json` intent_challenge_version requires workflow_version `2`")


def validate_plan(ctx: Ctx, errors: list[str]) -> None:
    text = read_md(ctx.request_dir / "plan.md", "`plan.md`", errors)
    if not text:
        return
    heads = ["# Plan", "## Summary", "## Requirements Coverage", "## Change Targets", "## Flow Check", "## Validation", "## Out Of Scope"]
    korean_heads = ["## Summary", "## Requirements Coverage", "## Change Targets", "## Flow Check", "## Validation", "## Out Of Scope"]
    if is_v2(ctx.state):
        heads.insert(2, "## Outcome And Completion Criteria")
        korean_heads.insert(1, "## Outcome And Completion Criteria")
    need_heads(text, "plan.md", heads, errors)
    ids = req_ids(text)
    if not ids:
        errors.append("`plan.md` must include at least one `REQ-###` requirement id")
        return
    if not section(text, "## Flow Check"):
        errors.append("`plan.md` Flow Check must describe relevant affected product or system flow problems, including pre-existing issues discovered during planning")
    require_korean_sections(
        text,
        "plan.md",
        korean_heads,
        errors,
    )
    if is_v2(ctx.state):
        outcome = section(text, "## Outcome And Completion Criteria")
        if is_blank_or_placeholder(outcome):
            errors.append("`plan.md` Outcome And Completion Criteria must not be empty or an obvious placeholder")
    coverage = section(text, "## Requirements Coverage")
    if is_v2(ctx.state):
        header = coverage_header(coverage)
        if [norm(cell) for cell in header] != ["requirement", "plan", "completion evidence"]:
            errors.append("`plan.md` v2 Requirements Coverage header must be exactly `Requirement | Plan | Completion Evidence`")
    for rid in ids:
        rows = coverage_rows(coverage, rid)
        if not rows:
            errors.append(f"`plan.md` Requirements Coverage must include a table row for `{rid}`")
            continue
        if len(rows) != 1:
            errors.append(f"`plan.md` Requirements Coverage must include exactly one table row for `{rid}`")
            continue
        row = rows[0]
        if len(row) < 2 or is_blank_or_placeholder(row[1]):
            errors.append(f"`plan.md` Requirements Coverage plan cell for `{rid}` must not be empty or an obvious placeholder")
        if is_v2(ctx.state) and (len(row) < 3 or is_blank_or_placeholder(row[2])):
            errors.append(f"`plan.md` Requirements Coverage evidence cell for `{rid}` must not be empty or an obvious placeholder")


def validate_review(ctx: Ctx, errors: list[str]) -> None:
    text = read_md(ctx.request_dir / "review.md", "`review.md`", errors)
    if not text:
        return
    heads = ["# Review", "## Reviewed Plan Fingerprint", "## Reviewer", "## Verdict", "## Blocking Issues", "## Flow Check", "## Question Depth Check"]
    if has_intent_challenge_contract(ctx.state):
        heads.append("## Intent Challenge Check")
    need_heads(text, "review.md", heads, errors)
    fp = reviewed_fp(text)
    if not fp:
        errors.append("`review.md` must include `Reviewed Plan Fingerprint: sha256:<hex>`")
    elif fp != plan_fp(ctx.request_dir):
        errors.append("`review.md` reviewed plan fingerprint is stale")
    if not exact_pass(section(text, "## Verdict")):
        errors.append("`review.md` verdict must be `PASS` before goal execution")
    if norm(section(text, "## Blocking Issues")) not in BLOCKING_OK:
        errors.append("`review.md` Blocking Issues must say `No blocking issues` or `None`")
    if is_blank_or_placeholder(section(text, "## Flow Check")):
        errors.append("`review.md` Flow Check must include a non-empty review result")
    if is_blank_or_placeholder(section(text, "## Question Depth Check")):
        errors.append("`review.md` Question Depth Check must include a non-empty review result")
    if has_intent_challenge_contract(ctx.state):
        validate_intent_challenge(section(text, "## Intent Challenge Check"), errors)
    validate_review_language(text, errors)


def validate_intent_challenge(value: str, errors: list[str]) -> None:
    if not value:
        return
    need_heads(
        value,
        "review.md Intent Challenge Check",
        ["### Findings", "### Intent Challenge Final Verdict"],
        errors,
    )
    findings = section(value, "### Findings")
    header, rows = intent_challenge_table(findings)
    if header != ["Finding", "User Decision Or Resolution", "Verdict"]:
        errors.append(
            "`review.md` Intent Challenge Findings header must be exactly "
            "`Finding | User Decision Or Resolution | Verdict`"
        )
    if not rows:
        errors.append("`review.md` Intent Challenge Findings must include at least one data row")
    ids: list[str] = []
    for row in rows:
        if len(row) != 3:
            errors.append("`review.md` each Intent Challenge Findings row must contain exactly three cells")
            continue
        finding_id, resolution, verdict = row
        if finding_id != "NONE" and not INTENT_CHALLENGE_ID_RE.fullmatch(finding_id):
            errors.append("`review.md` Intent Challenge finding id must be `IC-###` or `NONE`")
        ids.append(finding_id)
        if is_blank_or_placeholder(resolution):
            errors.append(
                f"`review.md` Intent Challenge resolution for `{finding_id}` must not be empty or an obvious placeholder"
            )
        elif not HANGUL_RE.search(resolution):
            errors.append(
                f"`review.md` Intent Challenge resolution for `{finding_id}` must include Korean body text"
            )
        if verdict != "PASS":
            errors.append(
                f"`review.md` Intent Challenge verdict for `{finding_id}` must be exactly `PASS`"
            )
    finding_ids = [finding_id for finding_id in ids if finding_id != "NONE"]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("`review.md` Intent Challenge finding ids must be unique")
    if "NONE" in ids and (len(ids) != 1 or ids.count("NONE") != 1):
        errors.append("`review.md` Intent Challenge `NONE` must be the only finding row")
    if not exact_pass(section(value, "### Intent Challenge Final Verdict")):
        errors.append("`review.md` Intent Challenge Final Verdict must be exactly `PASS`")


def validate_completion(ctx: Ctx, phase: str, errors: list[str]) -> None:
    goal_status = str(ctx.state.get("goal_status") or "").strip()
    if phase == "completion" and goal_status and goal_status not in {"active", "completing"}:
        errors.append("completion validation requires goal_status `active` or `completing`")
    if not is_v2(ctx.state):
        return
    approval_status = str(ctx.state.get("plan_approval_status") or "").strip()
    if approval_status != "approved":
        errors.append("completion requires `plan_approval_status: approved`")
    approved = str(ctx.state.get("approved_plan_fingerprint") or "").strip().lower()
    if not FINGERPRINT_RE.fullmatch(approved):
        errors.append("completion requires `approved_plan_fingerprint: sha256:<hex>`")
    elif approved.removeprefix("sha256:") != plan_fp(ctx.request_dir):
        errors.append("completion requires approved_plan_fingerprint to match the current `plan.md`")


def validate_completion_review(ctx: Ctx, required: bool, errors: list[str]) -> None:
    text = read_md(ctx.request_dir / "review.md", "`review.md`", errors)
    if not text:
        return
    completion_count = sum(line.strip() == "## Completion Review" for line in text.splitlines())
    if completion_count == 0:
        if required:
            errors.append("`review.md` must include `## Completion Review` before Goal completion")
        return
    if completion_count != 1:
        errors.append("`review.md` must include exactly one `## Completion Review` section")

    need_heads(
        text,
        "review.md",
        [
            "## Completion Review",
            "### Completion Plan Fingerprint",
            "### Requirements Evidence",
            "### Observable Outcome Evidence",
            "### Completion Verdict",
        ],
        errors,
    )
    completion_fp = match_fp(
        r"Completion Plan Fingerprint:\s*sha256:([0-9a-fA-F]{64})",
        section(text, "### Completion Plan Fingerprint"),
    )
    current_fp = plan_fp(ctx.request_dir)
    if not completion_fp:
        errors.append("`review.md` Completion Review must include `Completion Plan Fingerprint: sha256:<hex>`")
    elif completion_fp != current_fp:
        errors.append("`review.md` Completion Plan Fingerprint is stale")

    evidence = section(text, "### Requirements Evidence")
    header = table_header(evidence)
    if [norm(cell) for cell in header] != ["requirement", "actual evidence", "verdict"]:
        errors.append("`review.md` Requirements Evidence header must be exactly `Requirement | Actual Evidence | Verdict`")
    planned_ids = req_ids(section(read_file(ctx.request_dir / "plan.md"), "## Requirements Coverage"))
    evidence_rows = table_rows(evidence)
    evidence_ids = [row[0] for row in evidence_rows if row and re.fullmatch(r"REQ-\d{3}", row[0])]
    for rid in planned_ids:
        rows = [row for row in evidence_rows if row and row[0] == rid]
        if len(rows) != 1:
            errors.append(f"`review.md` Requirements Evidence must include exactly one row for `{rid}`")
            continue
        row = rows[0]
        if len(row) < 2 or is_blank_or_placeholder(row[1]):
            errors.append(f"`review.md` Actual Evidence for `{rid}` must not be empty or an obvious placeholder")
        if len(row) < 3 or row[2].strip() != "PASS":
            errors.append(f"`review.md` Requirements Evidence verdict for `{rid}` must be exactly `PASS`")
    for rid in sorted(set(evidence_ids) - set(planned_ids)):
        errors.append(f"`review.md` Requirements Evidence contains unknown requirement `{rid}`")

    outcome = section(text, "### Observable Outcome Evidence")
    if is_blank_or_placeholder(outcome):
        errors.append("`review.md` Observable Outcome Evidence must not be empty or an obvious placeholder")
    elif not HANGUL_RE.search(outcome):
        errors.append("`review.md` Observable Outcome Evidence must include Korean body text")
    if not exact_pass(section(text, "### Completion Verdict")):
        errors.append("`review.md` Completion Verdict must be exactly `PASS`")


def read_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing {label}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            errors.append(f"{label} must contain a JSON object")
            return {}
        return data
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
    for heading in ("## Blocking Issues", "## Flow Check", "## Question Depth Check"):
        body = section(text, heading)
        if body and norm(body) not in REVIEW_FIXED_STATUSES and not HANGUL_RE.search(body):
            errors.append(f"`review.md` section `{heading}` must use Korean body text or an allowed fixed status")
    notes = section(text, "## Notes")
    if notes and not HANGUL_RE.search(notes):
        errors.append("`review.md` section `## Notes` must include Korean body text")


def req_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"\bREQ-\d{3}\b", text)))


def coverage_rows(coverage: str, rid: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in coverage.splitlines():
        if rid not in line or "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == rid:
            rows.append(cells)
    return rows


def coverage_header(coverage: str) -> list[str]:
    return table_header(coverage)


def table_header(value: str) -> list[str]:
    for line in value.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and norm(cells[0]) == "requirement":
            return cells
    return []


def table_rows(value: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in value.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or norm(cells[0]) == "requirement" or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def intent_challenge_table(value: str) -> tuple[list[str], list[list[str]]]:
    header: list[str] = []
    rows: list[list[str]] = []
    for line in value.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and norm(cells[0]) == "finding":
            header = cells
            continue
        if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return header, rows


def is_blank_or_placeholder(value: str) -> bool:
    stripped = value.strip()
    if not stripped or stripped == "-":
        return True
    plain = INLINE_CODE_RE.sub(lambda match: match.group(1), stripped).strip()
    plain = re.sub(r"^[-*]\s*", "", plain).strip().strip(".:。")
    return bool(OBVIOUS_PLACEHOLDER_RE.fullmatch(plain))


def exact_pass(value: str) -> bool:
    return value.strip() == "PASS"


def metadata_request_id(value: dict[str, Any]) -> str:
    return str(value.get("request_id") or value.get("id") or "").strip()


def validate_request_id_aliases(value: dict[str, Any], label: str, errors: list[str]) -> None:
    request_id = str(value.get("request_id") or "").strip()
    legacy_id = str(value.get("id") or "").strip()
    if request_id and legacy_id and request_id != legacy_id:
        errors.append(f"`{label}` request_id and legacy id values must match")


def metadata_phase(value: dict[str, Any]) -> str:
    return str(value.get("phase") or value.get("status") or "").strip()


def validate_metadata_phases(
    current: dict[str, Any],
    state: dict[str, Any],
    index_entry: dict[str, Any],
    errors: list[str],
) -> None:
    values = {
        "state.json": state,
        "index.json request entry": index_entry,
    }
    if current:
        values["current.json"] = current
    phases = {label: metadata_phase(value) for label, value in values.items()}
    for label, value in values.items():
        phase_value = str(value.get("phase") or "").strip()
        status_value = str(value.get("status") or "").strip()
        if phase_value and status_value and phase_value != status_value:
            errors.append(f"`{label}` phase and legacy status values must match")
    for label, phase in phases.items():
        if not phase:
            errors.append(f"`{label}` must include `phase` or legacy `status`")
        elif phase not in PHASES:
            errors.append(f"`{label}` phase `{phase}` is not allowed")
    present = {phase for phase in phases.values() if phase in PHASES}
    if len(present) > 1:
        errors.append("current, state, and index phases must match for the selected request")


def validate_goal_metadata(state: dict[str, Any], request_dir: Path, errors: list[str]) -> None:
    goal_status = str(state.get("goal_status") or "").strip()
    v2 = is_v2(state)
    if not goal_status:
        if v2:
            errors.append("`state.json` v2 requests require `goal_status`")
            validate_v2_approval_metadata(state, "", request_dir, errors)
        return
    if goal_status not in GOAL_STATUSES:
        errors.append(f"`state.json` goal_status `{goal_status}` is not allowed")
        return
    if v2:
        validate_v2_approval_metadata(state, goal_status, request_dir, errors)
        return
    phase = metadata_phase(state)
    incompatible = (
        (phase == "plan" and goal_status != "pending")
        or (phase == "review" and goal_status == "completed")
        or (phase == "completed" and goal_status != "completed")
    )
    if incompatible:
        errors.append(f"`state.json` phase `{phase}` is incompatible with goal_status `{goal_status}`")
    fingerprint = str(state.get("goal_plan_fingerprint") or "").strip().lower()
    if goal_status == "pending" and fingerprint and not FINGERPRINT_RE.fullmatch(fingerprint):
        errors.append("`state.json` goal_plan_fingerprint must use `sha256:<hex>`")
    if goal_status in {"active", "completing", "completed"} and not FINGERPRINT_RE.fullmatch(fingerprint):
        errors.append(
            "`state.json` active/completing/completed goal_status requires `goal_plan_fingerprint: sha256:<hex>`"
        )
    elif not v2 and goal_status in {"active", "completing", "completed"} and fingerprint.removeprefix("sha256:") != plan_fp(request_dir):
        errors.append("`state.json` goal_plan_fingerprint must match the current `plan.md`")


def validate_v2_approval_metadata(
    state: dict[str, Any],
    goal_status: str,
    request_dir: Path,
    errors: list[str],
) -> None:
    phase = metadata_phase(state)
    approval_status = str(state.get("plan_approval_status") or "").strip()
    if approval_status not in PLAN_APPROVAL_STATUSES:
        errors.append("`state.json` v2 requests require plan_approval_status `pending` or `approved`")
    elif (phase, approval_status, goal_status) not in ALLOWED_V2_STATES:
        errors.append(
            "`state.json` v2 phase, plan_approval_status, and goal_status combination is not allowed"
        )

    goal_fingerprint = str(state.get("goal_plan_fingerprint") or "").strip().lower()
    approved = str(state.get("approved_plan_fingerprint") or "").strip().lower()
    if goal_status == "pending" and goal_fingerprint:
        errors.append("`state.json` pending goal_status must not set `goal_plan_fingerprint`")
    elif goal_status in {"active", "completing", "completed"} and not FINGERPRINT_RE.fullmatch(goal_fingerprint):
        errors.append(
            "`state.json` active/completing/completed goal_status requires `goal_plan_fingerprint: sha256:<hex>`"
        )
    if approved and not FINGERPRINT_RE.fullmatch(approved):
        errors.append("`state.json` approved_plan_fingerprint must use `sha256:<hex>`")
    if approval_status == "pending" and goal_status == "pending" and approved:
        errors.append("`state.json` initial pending approval must not set `approved_plan_fingerprint`")
    if approval_status == "pending" and goal_status == "active" and not FINGERPRINT_RE.fullmatch(approved):
        errors.append("`state.json` material replan must preserve `approved_plan_fingerprint: sha256:<hex>`")
    if approval_status == "approved" and not FINGERPRINT_RE.fullmatch(approved):
        errors.append(
            "`state.json` approved plan requires `approved_plan_fingerprint: sha256:<hex>`"
        )
    elif approval_status == "approved" and approved.removeprefix("sha256:") != plan_fp(request_dir):
        errors.append("`state.json` approved_plan_fingerprint must match the current `plan.md` when approved")


def is_v2(state: dict[str, Any]) -> bool:
    return type(state.get("workflow_version")) is int and state.get("workflow_version") == 2


def has_intent_challenge_contract(state: dict[str, Any]) -> bool:
    return type(state.get("intent_challenge_version")) is int and state.get("intent_challenge_version") == 1


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
