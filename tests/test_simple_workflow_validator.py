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

    def test_print_template_outputs_plan_centered_templates(self) -> None:
        expected = {
            "index": "\"version\": \"1\"",
            "current": "\"request_id\"",
            "state": "\"phase\": \"plan\"",
            "plan": "사용자 동선",
            "review": "사용자에게 알려야 할 관련 흐름 문제 없음",
        }
        for name, fragment in expected.items():
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--print-template", name],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(fragment, result.stdout)
        for removed in ("requirements", "goal", "approval"):
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--print-template", removed],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_missing_plan_fails(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_plan=False)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("plan.md", result.stdout)

    def test_plan_requires_existing_sections(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body="# Plan\n\n## Summary\n\nToo small.\n")
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Requirements Coverage", result.stdout)

    def test_plan_requires_requirement_ids(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(req="TASK-1"))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("REQ-###", result.stdout)

    def test_plan_requires_requirement_coverage_row(self) -> None:
        with temp_project() as td:
            body = plan_text(req="REQ-001") + "\nExtra mention: `REQ-002`.\n"
            root = make_project(Path(td), plan_body=body)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("REQ-002", result.stdout)

    def test_plan_requires_concrete_requirement_plan(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(plan_cell="TODO"))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("concrete plan", result.stdout)

    def test_plan_requires_flow_check(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=plan_text(include_flow_check=False))
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Flow Check", result.stdout)

    def test_plan_requires_korean_body_text(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), plan_body=english_plan_text())
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "plan", expect_success=False)
            self.assertIn("Korean body text", result.stdout)

    def test_review_missing_fails_for_review_phase(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), write_review=False)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("review.md", result.stdout)

    def test_review_rejects_stale_fingerprint(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_stale=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("fingerprint is stale", result.stdout)

    def test_review_blocking_issues_block_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_blocking=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Blocking Issues", result.stdout)

    def test_review_flow_issues_block_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_flow_issue=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Flow Check", result.stdout)

    def test_review_requires_question_depth_check(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_missing_question_depth=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Question Depth Check", result.stdout)

    def test_review_question_depth_issue_blocks_goal_execution(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_question_depth_issue=True)
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Question Depth Check", result.stdout)

    def test_review_requires_korean_notes(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td), review_body=review_text("0" * 64, notes="Reviewed."))
            request_dir = root / ".simple" / "requests" / REQUEST_ID
            fp = sha256(request_dir / "plan.md")
            (request_dir / "review.md").write_text(review_text(fp, notes="Reviewed."), encoding="utf-8")
            result = self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "review", expect_success=False)
            self.assertIn("Korean body text", result.stdout)

    def test_all_passes_with_plan_and_internal_review_only(self) -> None:
        with temp_project() as td:
            root = make_project(Path(td))
            self.assertFalse((root / ".simple" / "requests" / REQUEST_ID / "requirements.md").exists())
            self.assertFalse((root / ".simple" / "requests" / REQUEST_ID / "goal.md").exists())
            self.run_validator(root, "--current", "--session-id", SESSION_ID, "--phase", "all")


def make_project(
    root: Path,
    *,
    write_plan: bool = True,
    write_review: bool = True,
    plan_body: str | None = None,
    review_stale: bool = False,
    review_blocking: bool = False,
    review_flow_issue: bool = False,
    review_missing_question_depth: bool = False,
    review_question_depth_issue: bool = False,
    review_body: str | None = None,
    phase: str = "review",
) -> Path:
    req_dir = root / ".simple" / "requests" / REQUEST_ID
    session_dir = root / ".simple" / "sessions" / SESSION_ID
    req_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)
    write_json(root / ".simple" / "index.json", {"version": "1", "requests": [{"id": REQUEST_ID, "title": "Test", "status": phase}]})
    write_json(session_dir / "current.json", {"request_id": REQUEST_ID, "phase": phase, "activated_by": "test"})
    write_json(req_dir / "state.json", {"request_id": REQUEST_ID, "phase": phase, "last_validated_at": None})
    if write_plan:
        (req_dir / "plan.md").write_text(plan_body if plan_body is not None else plan_text(), encoding="utf-8")
    if write_review:
        fp = sha256(req_dir / "plan.md")
        review_fp = "0" * 64 if review_stale else fp
        (req_dir / "review.md").write_text(
            review_body if review_body is not None else
            review_text(
                review_fp,
                review_blocking,
                review_flow_issue,
                missing_question_depth=review_missing_question_depth,
                question_depth_issue=review_question_depth_issue,
            ),
            encoding="utf-8",
        )
    return root


def plan_text(req: str = "REQ-001", plan_cell: str | None = None, include_flow_check: bool = True) -> str:
    plan = plan_cell if plan_cell is not None else f"`{req}`에서 요구한 동작을 구현한다."
    flow_check = """## Flow Check

- 계획된 변경과 관련된 사용자 동선, 상태 전이, 데이터 흐름, 실패/재시도 경로, 검증 흐름을 확인한다.
- 이번 변경이 만든 문제가 아니더라도 관련 흐름 문제를 발견하면 사용자에게 알리고, 범위 밖이면 범위 밖이라고 명시한다.

""" if include_flow_check else ""
    return f"""# Plan

## Summary

워크플로 구현을 단순화하고 검증 가능한 계획 중심 흐름으로 정리한다.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| {req} | {plan} |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` and `skills/simple-workflow/` | 여러 산출물 검사를 계획 중심 검사로 교체한다. |

{flow_check}## Validation

- `{req}`를 검증하기 위해 validator와 hook 테스트를 실행한다.

## Out Of Scope

- 사용자-facing requirements와 goal 산출물은 범위에서 제외한다.
"""


def english_plan_text() -> str:
    return """# Plan

## Summary

Simplify the workflow implementation.

## Requirements Coverage

| Requirement | Plan |
| --- | --- |
| REQ-001 | Implement the behavior described by `REQ-001`. |

## Change Targets

| Target | Planned Change |
| --- | --- |
| `scripts/` | Replace checks with plan-centered checks. |

## Flow Check

- The planned change does not break the affected user, state, data, failure, or validation flow.

## Validation

- Run validator and hook tests.

## Out Of Scope

- User-facing requirements and goal artifacts.
"""


def review_text(
    fp: str,
    blocking: bool = False,
    flow_issue: bool = False,
    *,
    missing_question_depth: bool = False,
    question_depth_issue: bool = False,
    notes: str = "검토 완료.",
) -> str:
    issues = "차단 이슈가 남아 있다" if blocking else "차단 없음"
    flow = "관련 사용자 동선의 실패 복구 흐름 문제가 사용자에게 보고되지 않았다" if flow_issue else "사용자에게 알려야 할 관련 흐름 문제 없음"
    question_depth = "해결되지 않은 대분류 질문이 남아 있다" if question_depth_issue else "상위 질문 없음"
    verdict = "FAIL" if blocking or flow_issue or question_depth_issue else "PASS"
    question_depth_section = "" if missing_question_depth else f"""
## Question Depth Check

{question_depth}
"""
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
{question_depth_section}

## Notes

{notes}
"""


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()
