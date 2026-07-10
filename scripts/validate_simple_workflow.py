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
FLOW_OK = {
    "none",
    "no flow issues",
    "0",
    "zero",
    "없음",
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
REQUEST_ID_RE = re.compile(r"^\d{8}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
PLAN_PLACEHOLDER_RE = re.compile(
    r"(?:(?<![A-Za-z0-9_])(?:TODO|TBD|N/?A)(?![A-Za-z0-9_])|미정|나중에|추후)",
    re.IGNORECASE,
)
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
INLINE_CODE_RE = re.compile(r"`([^`]*)`")
PLACEHOLDER_CODE_RE = re.compile(
    r"(?:(?<![A-Za-z0-9_])(?:TODO|TBD|N/?A|PLACEHOLDER)(?![A-Za-z0-9_])|미정|나중에|추후)",
    re.IGNORECASE,
)
PLACEHOLDER_TARGET_LABEL_RE = re.compile(
    r"^\s*(?:marker|token|literal|identifier|placeholder|마커|표식|토큰|리터럴|식별자|문자열)"
    r"(?=$|\s|[가-힣])",
    re.IGNORECASE,
)
PLACEHOLDER_WORD_RE = re.compile(
    r"(?<![A-Za-z0-9_])placeholder(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PLACEHOLDER_PLAIN_TARGET_RE = re.compile(
    r"(?<![A-Za-z0-9_])placeholder(?![A-Za-z0-9_])"
    r"(?:(?:와|및)\s*)?(?:\s*(?:변형|표식|마커|토큰|리터럴|식별자|문자열|계획|값|상태))?\s*(?:을|를)",
    re.IGNORECASE,
)
PLACEHOLDER_DESCRIBED_TARGET_RE = re.compile(
    r"(?<![A-Za-z0-9_])placeholder(?![A-Za-z0-9_])"
    r"\s+(?:변형|표식|마커|토큰|리터럴|식별자|문자열|계획|값|상태)",
    re.IGNORECASE,
)
PLACEHOLDER_DEFERRAL_USAGE_RE = re.compile(
    r"(?<![A-Za-z0-9_])placeholder(?![A-Za-z0-9_])"
    r"(?:\s+(?:변형|표식|마커|토큰|리터럴|식별자|문자열|계획|값|상태))?"
    r"\s*(?:로|으로|에|을|를)?\s*"
    r"(?:둔다|두고|처리한다|처리하고|작성한다|작성하고|고정한다|고정하고|설정한다|설정하고|"
    r"유지한다|유지하고|남긴다|남기고|넣는다|넣고|삽입한다|삽입하고)",
    re.IGNORECASE,
)
PLACEHOLDER_TARGET_ACTION_RE = re.compile(
    r"(?:제거|교체|차단|검증|탐지|거부|치환|삭제)(?:한다|하고|하며|하도록|해|하여|할\b)"
)
PLACEHOLDER_REGRESSION_FIX_RE = re.compile(r"(?:테스트.{0,40}고정|고정.{0,40}테스트)")
OUTCOME_TARGET_RE = re.compile(r"(?:사용자|요청|상태|동작|응답|출력|파일|흐름|요구사항|Goal|plan)", re.IGNORECASE)
OUTCOME_METHOD_RE = re.compile(r"(?:명령|테스트|validator|출력|응답|파일|경로|사용자\s*흐름|상태\s*필드|diff|증거)", re.IGNORECASE)
OUTCOME_PROOF_RE = re.compile(r"(?:확인|관찰|통과|일치|반환|표시|검증|증명|대조|가능)")
GENERIC_OUTCOME_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:잘|정상적으로)?\s*(?:완료|동작|처리)(?:한다|된다)?[.!]?\s*$")
EVIDENCE_SOURCE_RE = re.compile(
    r"(?:테스트|validator|명령|출력|응답|상태|파일|경로|diff|사용자\s*흐름|검사)",
    re.IGNORECASE,
)
EVIDENCE_TARGET_RE = re.compile(
    r"(?:REQ-\d{3}|동작|결과|상태|흐름|요구|규칙|경계|순서|fingerprint|plan|Goal|승인|섹션|열|셀|버전|호환|복구|경고|범위|출력|증거|소스|cache|캐시|설치|plugin|플러그인)",
    re.IGNORECASE,
)
EVIDENCE_PROOF_RE = re.compile(
    r"(?:통과|일치|반환|표시|확인|비교|검증|관찰|차단|거부|성공|실패|보존)",
    re.IGNORECASE,
)

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
  "workflow_version": 2,
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


def validate_meta(ctx: Ctx, errors: list[str]) -> None:
    phase = metadata_phase(ctx.state)
    if not phase:
        errors.append("`state.json` must include `phase`")
    elif phase not in PHASES:
        errors.append(f"`state.json` phase `{phase}` is not allowed")
    version = ctx.state.get("workflow_version")
    if version is not None and (type(version) is not int or version != 2):
        errors.append("`state.json` workflow_version must be integer `2` when present")


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
        if not meaningful_outcome(outcome):
            errors.append("`plan.md` Outcome And Completion Criteria must define a concrete observable outcome")
    coverage = section(text, "## Requirements Coverage")
    if is_v2(ctx.state):
        header = coverage_header(coverage)
        if [norm(cell) for cell in header] != ["requirement", "plan", "completion evidence"]:
            errors.append("`plan.md` v2 Requirements Coverage header must be exactly `Requirement | Plan | Completion Evidence`")
    for rid in ids:
        row = coverage_row(coverage, rid)
        if not row:
            errors.append(f"`plan.md` Requirements Coverage must include a table row for `{rid}`")
        elif not meaningful_plan_cell(row):
            errors.append(f"`plan.md` Requirements Coverage must include a concrete plan for `{rid}`")
        elif is_v2(ctx.state) and not meaningful_evidence_cell(row):
            errors.append(f"`plan.md` Requirements Coverage must include concrete completion evidence for `{rid}`")


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
    if not exact_pass(section(text, "## Verdict")):
        errors.append("`review.md` verdict must be `PASS` before goal execution")
    if norm(section(text, "## Blocking Issues")) not in BLOCKING_OK:
        errors.append("`review.md` Blocking Issues must say `No blocking issues` or `None`")
    if norm(section(text, "## Flow Check")) not in FLOW_OK:
        errors.append("`review.md` Flow Check must say there are no unreported relevant flow issues")
    if norm(section(text, "## Question Depth Check")) not in QUESTION_DEPTH_OK:
        errors.append("`review.md` Question Depth Check must say `No unresolved higher-level questions` or `None`")
    validate_review_language(text, errors)


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
    for heading, allowed in (
        ("## Blocking Issues", BLOCKING_OK),
        ("## Flow Check", FLOW_OK),
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


def coverage_header(coverage: str) -> list[str]:
    for line in coverage.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and norm(cells[0]) == "requirement":
            return cells
    return []


def meaningful_outcome(value: str) -> bool:
    prose = INLINE_CODE_RE.sub("", value).strip()
    if len(prose) < 40 or not HANGUL_RE.search(prose) or GENERIC_OUTCOME_RE.fullmatch(prose):
        return False
    if (
        PLAN_PLACEHOLDER_RE.search(prose)
        or PLACEHOLDER_DEFERRAL_USAGE_RE.search(prose)
        or has_inline_placeholder(value)
    ):
        return False
    return bool(
        OUTCOME_TARGET_RE.search(prose)
        and OUTCOME_METHOD_RE.search(prose)
        and OUTCOME_PROOF_RE.search(prose)
    )


def meaningful_evidence_cell(row: list[str]) -> bool:
    if len(row) < 3:
        return False
    evidence = row[2].strip()
    prose = INLINE_CODE_RE.sub("", evidence).strip()
    if len(prose) < 20 or evidence == "-":
        return False
    if (
        PLAN_PLACEHOLDER_RE.search(prose)
        or PLACEHOLDER_DEFERRAL_USAGE_RE.search(prose)
        or has_inline_placeholder(evidence)
    ):
        return False
    return bool(
        EVIDENCE_SOURCE_RE.search(prose)
        and EVIDENCE_TARGET_RE.search(prose)
        and EVIDENCE_PROOF_RE.search(prose)
    )


def has_inline_placeholder(value: str) -> bool:
    return any(PLACEHOLDER_CODE_RE.search(match.group(1).strip()) for match in INLINE_CODE_RE.finditer(value))


def meaningful_plan_cell(row: list[str]) -> bool:
    if len(row) < 2:
        return False
    plan = row[1].strip()
    inline_placeholders = [
        match
        for match in INLINE_CODE_RE.finditer(plan)
        if PLACEHOLDER_CODE_RE.search(match.group(1).strip())
    ]
    prose = INLINE_CODE_RE.sub("", plan)
    if PLACEHOLDER_DEFERRAL_USAGE_RE.search(prose):
        return False
    regression_fix = bool(PLACEHOLDER_REGRESSION_FIX_RE.search(prose))
    target_action = bool(PLACEHOLDER_TARGET_ACTION_RE.search(prose) or regression_fix)
    plain_target = bool(
        PLACEHOLDER_PLAIN_TARGET_RE.search(prose)
        or (regression_fix and PLACEHOLDER_DESCRIBED_TARGET_RE.search(prose))
    )
    if inline_placeholders:
        shared_literal_target = bool(PLACEHOLDER_TARGET_LABEL_RE.search(plan[inline_placeholders[-1].end() :]))
        if not target_action or not (shared_literal_target or plain_target):
            return False
    if PLACEHOLDER_WORD_RE.search(prose) and not (plain_target and target_action):
        return False
    return bool(plan) and plan != "-" and not PLAN_PLACEHOLDER_RE.search(prose)


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
    if not v2:
        return
    validate_v2_approval_metadata(state, goal_status, request_dir, errors)


def validate_v2_approval_metadata(
    state: dict[str, Any],
    goal_status: str,
    request_dir: Path,
    errors: list[str],
) -> None:
    approval_status = str(state.get("plan_approval_status") or "").strip()
    if approval_status not in PLAN_APPROVAL_STATUSES:
        errors.append("`state.json` v2 requests require plan_approval_status `pending` or `approved`")
    if goal_status == "pending" and approval_status and approval_status != "pending":
        errors.append("`state.json` v2 pending goal_status requires plan_approval_status `pending`")
    approved = str(state.get("approved_plan_fingerprint") or "").strip().lower()
    if approved and not FINGERPRINT_RE.fullmatch(approved):
        errors.append("`state.json` approved_plan_fingerprint must use `sha256:<hex>`")
    if goal_status in {"active", "completing", "completed"} and not FINGERPRINT_RE.fullmatch(approved):
        errors.append(
            "`state.json` v2 active/completing/completed goal_status requires `approved_plan_fingerprint: sha256:<hex>`"
        )
    elif approval_status == "approved" and goal_status in {"active", "completing", "completed"} and approved.removeprefix("sha256:") != plan_fp(request_dir):
        errors.append("`state.json` approved_plan_fingerprint must match the current `plan.md` when approved")


def is_v2(state: dict[str, Any]) -> bool:
    return type(state.get("workflow_version")) is int and state.get("workflow_version") == 2


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
