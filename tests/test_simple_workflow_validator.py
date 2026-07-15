from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_simple_workflow.py"
REQUEST_ID = "20260609-1120-test-request"
SESSION_ID = "test-session"
TEST_TMP = ROOT / "tests" / ".tmp"
MISSING = object()


class TempProject:
    def __enter__(self) -> str:
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.path = TEST_TMP / f"case-{uuid.uuid4().hex}"
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def temp_project() -> TempProject:
    return TempProject()


class ValidatorTests(unittest.TestCase):
    def run_validator(self, root: Path, *args: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if expect_success and result.returncode != 0:
            self.fail(result.stdout)
        if not expect_success and result.returncode == 0:
            self.fail("validator unexpectedly passed")
        return result

    def validate(self, root: Path, phase: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_validator(
            root,
            "--current",
            "--session-id",
            SESSION_ID,
            "--phase",
            phase,
            expect_success=expect_success,
        )

    def test_templates_remain_plan_centered(self) -> None:
        for name, fragment in {
            "index": '"version": "1"',
            "current": '"request_id"',
            "state": '"phase": "plan"',
            "plan": "사용자 동선",
            "review": "Question Depth Check",
        }.items():
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--print-template", name],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(fragment, result.stdout)
        state = subprocess.run(
            [sys.executable, str(VALIDATOR), "--print-template", "state"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        review = subprocess.run(
            [sys.executable, str(VALIDATOR), "--print-template", "review"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertIn('"intent_challenge_version": 1', state.stdout)
        self.assertIn("## Intent Challenge Check", review.stdout)

    def test_plan_requires_sections_korean_and_exact_coverage_header(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan", plan_body="# Plan\n\n## Summary\n\n짧다.\n")
            self.assertIn("Requirements Coverage", self.validate(root, "plan", False).stdout)
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan", plan_body=english_plan_text())
            self.assertIn("Korean body text", self.validate(root, "plan", False).stdout)
        with temp_project() as td:
            body = v2_plan_text().replace("| Requirement | Plan | Completion Evidence |", "| Requirement | Notes | Completion Evidence |")
            root = make_v2_project(Path(td), phase="plan", plan_body=body)
            self.assertIn("header must be exactly", self.validate(root, "plan", False).stdout)

    def test_plan_uses_structural_nonempty_checks_without_korean_keyword_scoring(self) -> None:
        body = v2_plan_text(
            outcome="사용자 화면에 종료 상태가 남는다.",
            plan_cell="상태 기록기를 새 계약에 맞춘다.",
            evidence="콘솔에는 종료 코드 0과 요청 식별자가 남는다.",
        )
        with temp_project() as td:
            self.validate(make_v2_project(Path(td), phase="plan", plan_body=body), "plan")

    def test_plan_rejects_only_empty_or_obvious_placeholder_cells(self) -> None:
        for value in ("", "-", "TODO", "`TBD`", "미정", "추후"):
            with self.subTest(value=value), temp_project() as td:
                root = make_v2_project(Path(td), phase="plan", plan_body=v2_plan_text(plan_cell=value))
                self.assertIn("obvious placeholder", self.validate(root, "plan", False).stdout)
        for value in (
            "`TODO` 표식을 제거하고 상태를 기록한다.",
            "placeholder 오탐 회귀를 막는 구조 검사를 추가한다.",
            "추후라는 단어를 포함한 사용자 입력도 보존한다.",
        ):
            with self.subTest(value=value), temp_project() as td:
                self.validate(make_v2_project(Path(td), phase="plan", plan_body=v2_plan_text(plan_cell=value)), "plan")

    def test_plan_requires_exactly_one_row_per_requirement(self) -> None:
        duplicate = v2_plan_text().replace(
            "| REQ-001 | `REQ-001` 동작을 구현한다. | 실제 출력으로 결과를 확인한다. |",
            "| REQ-001 | `REQ-001` 동작을 구현한다. | 실제 출력으로 결과를 확인한다. |\n"
            "| REQ-001 | 같은 요구를 다시 쓴다. | 다른 출력으로 확인한다. |",
        )
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="plan", plan_body=duplicate)
            self.assertIn("exactly one", self.validate(root, "plan", False).stdout)

    def test_review_requires_current_fingerprint_exact_pass_and_no_blocker(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), review_stale=True)
            self.assertIn("fingerprint is stale", self.validate(root, "review", False).stdout)
        with temp_project() as td:
            root = make_v2_project(Path(td), review_verdict="PASS with notes")
            self.assertIn("verdict must be `PASS`", self.validate(root, "review", False).stdout)
        with temp_project() as td:
            root = make_v2_project(Path(td), review_blocking=True)
            self.assertIn("Blocking Issues", self.validate(root, "review", False).stdout)

    def test_nonblocking_flow_and_question_depth_findings_are_structurally_valid(self) -> None:
        body = review_text(
            "0" * 64,
            flow="기존 retry 경로가 범위 밖이라는 비차단 관찰을 기록했다.",
            question_depth="상위 결정은 확정됐고 세부 표현만 구현자가 선택한다.",
        )
        with temp_project() as td:
            root = make_v2_project(Path(td), review_body=body)
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            (request_dir / "review.md").write_text(
                review_text(
                    sha256(request_dir / "plan.md"),
                    flow="기존 retry 경로가 범위 밖이라는 비차단 관찰을 기록했다.",
                    question_depth="상위 결정은 확정됐고 세부 표현만 구현자가 선택한다.",
                ),
                encoding="utf-8",
            )
            self.validate(root, "review")

    def test_review_flow_and_question_depth_must_be_nonempty_and_korean(self) -> None:
        for kwargs, expected in (
            ({"flow": ""}, "Flow Check"),
            ({"question_depth": ""}, "Question Depth Check"),
            ({"flow": "A detailed review result"}, "Korean body text"),
        ):
            with self.subTest(kwargs=kwargs), temp_project() as td:
                root = make_v2_project(Path(td), review_kwargs=kwargs)
                self.assertIn(expected, self.validate(root, "review", False).stdout)

    def test_intent_challenge_marker_requires_valid_structured_review(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), intent_challenge_version=1)
            self.validate(root, "review")
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                intent_challenge_version=1,
                review_kwargs={
                    "intent_challenge": intent_challenge_text(
                        rows=(
                            "| IC-001 | 사용자가 비가역 위험을 수용했다. | PASS |\n"
                            "| IC-002 | 더 단순한 대안을 최종 요구에 반영했다. | PASS |"
                        )
                    )
                },
            )
            self.validate(root, "review")
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                intent_challenge_version=1,
                review_body=review_text("0" * 64),
            )
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            (request_dir / "review.md").write_text(
                review_text(sha256(request_dir / "plan.md")),
                encoding="utf-8",
            )
            self.assertIn("Intent Challenge Check", self.validate(root, "review", False).stdout)

    def test_intent_challenge_rejects_invalid_table_and_unresolved_findings(self) -> None:
        cases = (
            (
                intent_challenge_text(header="Finding | Resolution | Verdict"),
                "header must be exactly",
            ),
            (intent_challenge_text(rows=""), "at least one data row"),
            (
                intent_challenge_text(
                    rows=(
                        "| IC-001 | 사용자가 위험을 수용했다. | PASS |\n"
                        "| IC-001 | 같은 결정을 중복 기록했다. | PASS |"
                    )
                ),
                "finding ids must be unique",
            ),
            (
                intent_challenge_text(
                    rows=(
                        "| NONE | 사용자 결정이 필요한 finding이 없다. | PASS |\n"
                        "| IC-001 | 사용자가 위험을 수용했다. | PASS |"
                    )
                ),
                "`NONE` must be the only",
            ),
            (
                intent_challenge_text(rows="| IC-1 | 사용자가 위험을 수용했다. | PASS |"),
                "must be `IC-###` or `NONE`",
            ),
            (
                intent_challenge_text(rows="| IC-001 | TODO | PASS |"),
                "obvious placeholder",
            ),
            (
                intent_challenge_text(rows="| IC-001 | User accepted the risk. | PASS |"),
                "must include Korean body text",
            ),
            (
                intent_challenge_text(rows="| IC-001 | 사용자가 위험을 수용했다. | FAIL |"),
                "must be exactly `PASS`",
            ),
            (
                intent_challenge_text(rows="| IC-001 | 사용자가 위험을 수용했다. | PASS | extra |"),
                "exactly three cells",
            ),
            (intent_challenge_text(final_verdict="FAIL"), "Final Verdict must be exactly `PASS`"),
        )
        for challenge, expected in cases:
            with self.subTest(expected=expected), temp_project() as td:
                root = make_v2_project(
                    Path(td),
                    intent_challenge_version=1,
                    review_kwargs={"intent_challenge": challenge},
                )
                self.assertIn(expected, self.validate(root, "review", False).stdout)

    def test_intent_challenge_marker_preserves_markerless_v2_and_legacy_reviews(self) -> None:
        with temp_project() as td:
            self.validate(make_v2_project(Path(td)), "review")
        with temp_project() as td:
            self.validate(make_project(Path(td)), "review")

    def test_intent_challenge_marker_rejects_unknown_values_and_legacy_use(self) -> None:
        for marker in (0, 2, "1", True, None):
            with self.subTest(marker=marker), temp_project() as td:
                root = make_v2_project(Path(td), intent_challenge_version=marker)
                self.assertIn("exact integer `1`", self.validate(root, "review", False).stdout)
        with temp_project() as td:
            root = make_project(Path(td))
            state_path = root / ".simple" / "requests" / REQUEST_ID / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["intent_challenge_version"] = 1
            write_json(state_path, state)
            self.assertIn("requires workflow_version `2`", self.validate(root, "review", False).stdout)

    def test_all_seven_v2_state_combinations_are_allowed(self) -> None:
        combinations = (
            ("plan", "pending", "pending"),
            ("review", "pending", "pending"),
            ("review", "approved", "pending"),
            ("review", "approved", "active"),
            ("review", "pending", "active"),
            ("review", "approved", "completing"),
            ("completed", "approved", "completed"),
        )
        for phase, approval, goal in combinations:
            with self.subTest(state=(phase, approval, goal)), temp_project() as td:
                root = make_v2_project(Path(td), phase=phase, approval_status=approval, goal_status=goal)
                self.validate(root, "all" if phase == "completed" else phase)

    def test_unlisted_v2_state_combinations_are_rejected(self) -> None:
        for phase, approval, goal in (
            ("plan", "approved", "pending"),
            ("review", "pending", "completing"),
            ("completed", "pending", "completed"),
        ):
            with self.subTest(state=(phase, approval, goal)), temp_project() as td:
                root = make_v2_project(Path(td), phase=phase, approval_status=approval, goal_status=goal)
                result = self.validate(root, "all" if phase == "completed" else phase, False)
                self.assertIn("combination is not allowed", result.stdout)

    def test_approved_pending_records_current_fingerprint_without_goal_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            self.validate(root, "review")
            state_path = root / ".simple" / "requests" / REQUEST_ID / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["approved_plan_fingerprint"] = "sha256:" + "0" * 64
            write_json(state_path, state)
            self.assertIn("must match", self.validate(root, "review", False).stdout)

    def test_pending_goal_rejects_goal_fingerprint_and_goal_failure_retry_keeps_approval(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="pending")
            state_path = root / ".simple" / "requests" / REQUEST_ID / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["goal_plan_fingerprint"] = state["approved_plan_fingerprint"]
            write_json(state_path, state)
            self.assertIn("must not set", self.validate(root, "review", False).stdout)

    def test_material_replan_preserves_old_goal_and_approval_fingerprints(self) -> None:
        old_goal = "sha256:" + "1" * 64
        old_approval = "sha256:" + "2" * 64
        with temp_project() as td:
            root = make_v2_project(
                Path(td),
                phase="review",
                approval_status="pending",
                goal_status="active",
                goal_fingerprint=old_goal,
                approved_fingerprint=old_approval,
            )
            self.validate(root, "review")

    def test_completion_requires_durable_section(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            self.assertIn("Completion Review", self.validate(root, "completion", False).stdout)

    def test_completion_accepts_code_and_read_only_actual_evidence(self) -> None:
        for evidence in (
            "회귀 테스트 12건이 통과했고 상태 파일의 approved 값이 확인됐다.",
            "읽기 전용 명령 출력에서 현재 branch와 clean 상태를 관찰했다.",
        ):
            with self.subTest(evidence=evidence), temp_project() as td:
                root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
                add_completion_review(root, evidence=evidence)
                self.validate(root, "completion")

    def test_completion_rejects_missing_duplicate_empty_stale_or_failed_evidence(self) -> None:
        cases = (
            ({"include_row": False}, "exactly one row"),
            ({"duplicate_row": True}, "exactly one row"),
            ({"evidence": "TODO"}, "obvious placeholder"),
            ({"fingerprint": "0" * 64}, "Fingerprint is stale"),
            ({"row_verdict": "FAIL"}, "must be exactly `PASS`"),
            ({"completion_verdict": "FAIL"}, "Completion Verdict"),
            ({"outcome": "미정"}, "Observable Outcome Evidence"),
        )
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs), temp_project() as td:
                root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
                add_completion_review(root, **kwargs)
                self.assertIn(expected, self.validate(root, "completion", False).stdout)

    def test_completion_rejects_duplicate_completion_review_sections(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="review", approval_status="approved", goal_status="active")
            add_completion_review(root)
            add_completion_review(root, completion_verdict="FAIL")
            self.assertIn("exactly one", self.validate(root, "completion", False).stdout)

    def test_all_allows_old_completed_v2_but_validates_section_when_present(self) -> None:
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="completed", approval_status="approved", goal_status="completed")
            self.validate(root, "all")
        with temp_project() as td:
            root = make_v2_project(Path(td), phase="completed", approval_status="approved", goal_status="completed")
            add_completion_review(root, row_verdict="FAIL")
            self.assertIn("must be exactly `PASS`", self.validate(root, "all", False).stdout)


def make_project(
    root: Path,
    *,
    write_plan: bool = True,
    write_review: bool = True,
    plan_body: str | None = None,
    review_stale: bool = False,
    review_blocking: bool = False,
    review_verdict: str = "PASS",
    review_body: str | None = None,
    review_kwargs: dict[str, str] | None = None,
    phase: str = "review",
) -> Path:
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    session_dir = root / ".simple" / "sessions" / SESSION_ID
    request_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)
    write_json(root / ".simple" / "index.json", {"version": "1", "requests": [{"id": REQUEST_ID, "status": phase}]})
    write_json(session_dir / "current.json", {"request_id": REQUEST_ID, "phase": phase, "activated_by": "test"})
    write_json(request_dir / "state.json", {"request_id": REQUEST_ID, "phase": phase})
    if write_plan:
        (request_dir / "plan.md").write_text(plan_body or plan_text(), encoding="utf-8")
    if write_review:
        fp = "0" * 64 if review_stale else sha256(request_dir / "plan.md")
        kwargs = dict(review_kwargs or {})
        kwargs.setdefault("blocking", review_blocking)
        kwargs.setdefault("verdict", review_verdict)
        (request_dir / "review.md").write_text(review_body or review_text(fp, **kwargs), encoding="utf-8")
    return root


def make_v2_project(
    root: Path,
    *,
    phase: str = "review",
    plan_body: str | None = None,
    goal_status: str | None = None,
    approval_status: str | None = None,
    goal_fingerprint: str | None = None,
    approved_fingerprint: str | None = None,
    review_stale: bool = False,
    review_blocking: bool = False,
    review_verdict: str = "PASS",
    review_body: str | None = None,
    review_kwargs: dict[str, str] | None = None,
    intent_challenge_version: object = MISSING,
) -> Path:
    kwargs = dict(review_kwargs or {})
    if type(intent_challenge_version) is int and intent_challenge_version == 1:
        kwargs.setdefault("intent_challenge", intent_challenge_text())
    root = make_project(
        root,
        phase=phase,
        plan_body=plan_body or v2_plan_text(),
        review_stale=review_stale,
        review_blocking=review_blocking,
        review_verdict=review_verdict,
        review_body=review_body,
        review_kwargs=kwargs,
    )
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    current = "sha256:" + sha256(request_dir / "plan.md")
    goal = goal_status or {"plan": "pending", "review": "active", "completed": "completed"}[phase]
    approval = approval_status or ("pending" if goal == "pending" else "approved")
    state: dict[str, object] = {
        "request_id": REQUEST_ID,
        "workflow_version": 2,
        "phase": phase,
        "plan_approval_status": approval,
        "goal_status": goal,
    }
    if intent_challenge_version is not MISSING:
        state["intent_challenge_version"] = intent_challenge_version
    if goal in {"active", "completing", "completed"}:
        state["goal_plan_fingerprint"] = goal_fingerprint or current
    if approval == "approved":
        state["approved_plan_fingerprint"] = approved_fingerprint or current
    elif goal == "active":
        state["approved_plan_fingerprint"] = approved_fingerprint or ("sha256:" + "1" * 64)
    write_json(request_dir / "state.json", state)
    return root


def plan_text(req: str = "REQ-001") -> str:
    return v2_plan_text(req=req).replace("\n## Outcome And Completion Criteria\n\n- 사용자가 종료 상태를 확인한다.\n", "")


def v2_plan_text(
    req: str = "REQ-001",
    *,
    outcome: str = "사용자가 종료 상태를 확인한다.",
    plan_cell: str | None = None,
    evidence: str = "실제 출력으로 결과를 확인한다.",
) -> str:
    plan = plan_cell if plan_cell is not None else f"`{req}` 동작을 구현한다."
    return f"""# Plan

## Summary

워크플로 상태를 검증 가능한 계획 중심으로 정리한다.

## Outcome And Completion Criteria

- {outcome}

## Requirements Coverage

| Requirement | Plan | Completion Evidence |
| --- | --- | --- |
| {req} | {plan} | {evidence} |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` | 상태 검사 규칙을 수정한다. |

## Flow Check

사용자, 상태, 실패 복구와 검증 흐름을 확인한다.

## Validation

대상 validator 검사를 실행한다.

## Out Of Scope

다른 workflow 변경은 제외한다.
"""


def english_plan_text() -> str:
    return v2_plan_text().replace("워크플로 상태를 검증 가능한 계획 중심으로 정리한다.", "Simplify workflow state.")


def review_text(
    fp: str,
    blocking: bool = False,
    *,
    verdict: str = "PASS",
    flow: str = "관련 흐름을 검토했고 비차단 문제만 기록했다.",
    question_depth: str = "상위 질문이 남아 있지 않다.",
    intent_challenge: str | None = None,
    notes: str = "검토 완료.",
) -> str:
    issues = "차단 이슈가 남아 있다." if blocking else "차단 없음"
    challenge = f"\n{intent_challenge.rstrip()}\n" if intent_challenge else ""
    return f"""# Review

## Reviewed Plan Fingerprint

Reviewed Plan Fingerprint: sha256:{fp}

## Reviewer

subagent

## Verdict

{verdict}

## Blocking Issues

{issues}

## Flow Check

{flow}

## Question Depth Check

{question_depth}
{challenge}
## Notes

{notes}
"""


def intent_challenge_text(
    *,
    header: str = "Finding | User Decision Or Resolution | Verdict",
    rows: str = "| NONE | 요구사항과 대안을 검토했으며 사용자 결정이 필요한 finding이 없다. | PASS |",
    final_verdict: str = "PASS",
) -> str:
    return f"""## Intent Challenge Check

### Findings

| {header} |
| --- | --- | --- |
{rows}

### Intent Challenge Final Verdict

{final_verdict}
"""


def add_completion_review(
    root: Path,
    *,
    fingerprint: str | None = None,
    include_row: bool = True,
    duplicate_row: bool = False,
    evidence: str = "회귀 테스트가 통과하고 상태 출력이 일치했다.",
    row_verdict: str = "PASS",
    outcome: str = "사용자가 최종 상태와 명령 출력을 확인했다.",
    completion_verdict: str = "PASS",
) -> None:
    request_dir = root / ".simple" / "requests" / REQUEST_ID
    review = request_dir / "review.md"
    rows = ""
    if include_row:
        rows = f"| REQ-001 | {evidence} | {row_verdict} |\n"
        if duplicate_row:
            rows += f"| REQ-001 | 두 번째 근거 | {row_verdict} |\n"
    value = review.read_text(encoding="utf-8") + f"""

## Completion Review

### Completion Plan Fingerprint

Completion Plan Fingerprint: sha256:{fingerprint or sha256(request_dir / 'plan.md')}

### Requirements Evidence

| Requirement | Actual Evidence | Verdict |
| --- | --- | --- |
{rows}
### Observable Outcome Evidence

{outcome}

### Completion Verdict

{completion_verdict}
"""
    review.write_text(value, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()


if __name__ == "__main__":
    unittest.main()
