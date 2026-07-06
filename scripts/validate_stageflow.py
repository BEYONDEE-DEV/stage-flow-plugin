#!/usr/bin/env python3
"""Validate three-stage `.stageflow` request artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TableRequirement:
    section: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class Stage:
    phase: str
    folder: str
    artifact: str
    title: str
    required_sections: tuple[str, ...]
    rule_folder: str
    rule_file: str
    rule_title: str
    artifact_tables: tuple[TableRequirement, ...] = ()


STAGES: tuple[Stage, ...] = (
    Stage(
        "definition",
        "01-definition",
        "definition.md",
        "Definition",
        (
            "User Goal",
            "Purpose And Intent",
            "Request Profile",
            "Desired Outcomes",
            "Current Problems",
            "Problem-To-Requirement Mapping",
            "User-Specified Constraints",
            "Discovered Constraints",
            "Pending Clarifications",
            "Clarification History",
            "Open Questions",
            "Resolved Decisions",
            "Intent Fidelity",
            "Requirements",
            "Acceptance Criteria",
            "Normal Behavior Model",
            "User Flow",
            "State And Policy Model",
            "Approved Flow Inventory",
            "Policy Rules",
            "Integration Flow And Data Responsibilities",
            "Boundaries",
            "Regression Prevention",
            "Failure And Recovery Behavior",
        ),
        "01-definition",
        "definition-writing-and-review-rules.md",
        "Definition Writing And Review Rules",
        (
            TableRequirement("Purpose And Intent", ("Purpose", "User Value", "Business/Product Value", "Source", "Confidence")),
            TableRequirement("Desired Outcomes", ("ID", "Outcome", "Source", "Success Signal")),
            TableRequirement(
                "Current Problems",
                ("ID", "Problem", "Expected Behavior", "Actual Behavior", "Evidence Or Reproduction", "Impact"),
            ),
            TableRequirement("Problem-To-Requirement Mapping", ("Problem ID", "Requirement ID", "Resolution")),
            TableRequirement(
                "Pending Clarifications",
                (
                    "ID",
                    "Question Scope",
                    "Question",
                    "Options",
                    "Recommended Option",
                    "Transition Option",
                    "Why This Matters",
                    "Status",
                ),
            ),
            TableRequirement(
                "Clarification History",
                (
                    "Round ID",
                    "Questions Asked",
                    "User Response",
                    "Implementation Plan Option Offered",
                    "User Transition Signal",
                    "Reflected In",
                ),
            ),
            TableRequirement(
                "Open Questions",
                (
                    "ID",
                    "Decision Needed",
                    "Context Or Conflict",
                    "Recommended Option",
                    "Alternatives",
                    "Impact",
                    "Blocking",
                    "Resolution Target",
                ),
            ),
            TableRequirement(
                "Resolved Decisions",
                ("ID", "Source Question ID", "Answer Source", "Decision", "Reflected In"),
            ),
            TableRequirement(
                "Intent Fidelity",
                (
                    "ID",
                    "User Wording",
                    "Normalized Requirement",
                    "Allowed Interpretations",
                    "Disallowed Interpretations",
                    "Linked Requirement/Policy",
                ),
            ),
            TableRequirement(
                "Requirements",
                (
                    "ID",
                    "Type",
                    "Source",
                    "Requirement Detail",
                    "Boundary Or Exclusion",
                    "Linked Outcomes Or Problems",
                ),
            ),
            TableRequirement(
                "Policy Rules",
                (
                    "Rule ID",
                    "Trigger Or Condition",
                    "Policy",
                    "User/System Response",
                    "State/Data Responsibility",
                    "Failure/Recovery Behavior",
                    "Source Requirement IDs",
                ),
            ),
            TableRequirement(
                "Approved Flow Inventory",
                (
                    "Definition Flow ID",
                    "Source IDs",
                    "Trigger Or Entry",
                    "Actor Or Consumer",
                    "Target Outcome",
                    "State/Data Responsibility",
                    "Failure Or Empty Behavior",
                    "Boundary Status",
                ),
            ),
        ),
    ),
    Stage(
        "implementation-plan",
        "02-implementation-plan",
        "implementation-plan.md",
        "Implementation Plan",
        (
            "Technical Approach",
            "Implementation Architecture",
            "Change Areas",
            "Cause Or Design Notes",
            "Implementation Flow Model",
            "Flow Completeness Matrix",
            "Work Items",
            "Coverage Matrix",
            "Definition Fidelity Matrix",
            "Edge Cases And Failure Modes",
            "Validation Strategy",
            "Risks",
            "Constraints",
        ),
        "02-implementation-plan",
        "implementation-plan-writing-and-review-rules.md",
        "Implementation Plan Writing And Review Rules",
        (
            TableRequirement(
                "Implementation Flow Model",
                (
                    "Flow ID",
                    "Definition Flow ID",
                    "Definition Source",
                    "Trigger Or Entry",
                    "Target Outcome",
                    "Primary Work Items",
                    "Flow Status",
                    "Status Rationale",
                ),
            ),
            TableRequirement(
                "Flow Completeness Matrix",
                (
                    "Flow ID",
                    "Ordered Implementation Path",
                    "State/Data Transitions",
                    "Failure Or Empty States",
                    "Observable Completion",
                    "Validation Evidence",
                ),
            ),
            TableRequirement("Work Items", ("ID", "Implementation Unit", "Technical Design", "Completion Evidence")),
            TableRequirement(
                "Coverage Matrix",
                ("Service Rule ID", "Work Item ID", "Change Area", "Validation Evidence", "Risk/Constraint"),
            ),
            TableRequirement(
                "Definition Fidelity Matrix",
                (
                    "Work Item ID",
                    "Definition Source",
                    "Approved Meaning",
                    "Technical Interpretation",
                    "Must Not Interpret As",
                    "If Ambiguous",
                ),
            ),
        ),
    ),
    Stage(
        "implementation",
        "03-implementation",
        "implementation.md",
        "Implementation",
        (
            "Work Completed",
            "Plan Compliance And Deviations",
            "Work Item Completion Evidence",
            "Flow Completion Evidence",
            "Validation",
            "Review Result",
            "Completion Summary",
        ),
        "03-implementation",
        "implementation-writing-and-review-rules.md",
        "Implementation Writing And Review Rules",
        (
            TableRequirement(
                "Work Item Completion Evidence",
                (
                    "Work Item ID",
                    "Planned Unit",
                    "Actual Change",
                    "Validation Evidence",
                    "Linked Flow IDs",
                    "Status",
                ),
            ),
            TableRequirement(
                "Flow Completion Evidence",
                (
                    "Flow ID",
                    "Definition Flow ID",
                    "Planned Outcome",
                    "Actual Result",
                    "Validation Evidence",
                    "Observable Completion",
                    "Status",
                ),
            ),
        ),
    ),
)
STAGE_BY_PHASE = {stage.phase: stage for stage in STAGES}
PHASES = {stage.phase for stage in STAGES} | {"completed"}
VALIDATION_PHASES = {stage.phase for stage in STAGES} | {"all"}
APPROVAL_RE = re.compile(
    r"\b(approve|approved|go ahead|proceed|yes)\b|\uc2b9\uc778|\uc9c4\ud589",
    re.IGNORECASE,
)
NEGATIVE_APPROVAL_RE = re.compile(
    r"\b(not approved|do not approve|don't approve|reject|rejected)\b"
    r"|\ubbf8\uc2b9\uc778|\uac70\uc808",
    re.IGNORECASE,
)
PASS_RE = re.compile(r"\bpass\b", re.IGNORECASE)
NO_BLOCKING_RE = re.compile(
    r"\b(no blocking issues|zero blocking issues|none|0|zero)\b",
    re.IGNORECASE,
)
BLOCKING_OPEN_QUESTION_RE = re.compile(r"^(yes|true|blocking|block)$", re.IGNORECASE)
USER_STOP_SIGNAL_RE = re.compile(
    r"\b(implementation plan|proceed|go ahead|stop asking|enough)\b"
    r"|구현\s*계획|질문\s*그만|충분",
    re.IGNORECASE,
)
PENDING_STATUS_RE = re.compile(r"^(pending|awaiting|awaiting_user|대기|답변\s*대기)$", re.IGNORECASE)
OPTION_LABEL_RE = re.compile(r"^(?:Option\s*[1-9]\d*|선택지\s*[1-9]\d*|[A-Z])\s*:", re.IGNORECASE)
QUESTION_SCOPES = ("큰방향", "주요결정", "세부확인")
QUESTION_SCOPE_ORDER = {scope: index for index, scope in enumerate(QUESTION_SCOPES)}
QUESTION_SCOPE_TRANSITION_LABELS = {
    ("큰방향", "주요결정"): "큰방향 -> 주요결정",
    ("주요결정", "세부확인"): "주요결정 -> 세부확인",
}
QUESTION_SCOPE_TRANSITION_REVIEW_COLUMNS = (
    "Transition",
    "Definition Artifact Fingerprint",
    "Evidence Reviewed",
    "Remaining Higher-Scope Questions",
    "Reviewer",
    "Verdict",
)
RISK_LEVELS = {"low", "medium", "high"}
SYNC_STATUSES = {
    "pending",
    "working-set-only",
    "targeted-synced",
    "full-synced",
    "synced",
}
TARGETED_SYNC_STATUSES = {"targeted-synced", "full-synced", "synced"}
FULL_SYNC_STATUSES = {"full-synced", "synced"}
STORE_PENDING_GATES = {"pending-answer", "store-only", "store-only-next-question"}
STORE_SYNC_GATES = {"targeted-sync-required", "full-consistency-required", "snapshot-current"}
STORE_GATES = STORE_PENDING_GATES | STORE_SYNC_GATES
TARGETED_SYNC_GATE = "targeted-sync-required"
FULL_CONSISTENCY_GATE = "full-consistency-required"
SNAPSHOT_CURRENT_GATE = "snapshot-current"
PENDING_ID_RE = re.compile(r"\bPENDING-\d+\b", re.IGNORECASE)
DEC_ID_RE = re.compile(r"\bDEC-\d+\b", re.IGNORECASE)
DEFINITION_STORE_AFFECTED_ID_RE = re.compile(r"\b(?:REQ|SP|DFLOW|DEC|INTENT)-\d+\b", re.IGNORECASE)
TRANSITION_RISK_CATEGORIES = {
    "scope",
    "acceptance",
    "policy-data",
    "failure-recovery",
    "regression",
    "integration",
    "user-flow",
    "security-privacy",
    "implementation-readiness",
}
TRANSITION_RISK_DISPOSITIONS = {
    "apply-to-definition",
    "ask-follow-up",
    "out-of-scope",
    "accepted-risk",
    "duplicate",
    "not-applicable",
}
TRANSITION_RISK_COVERAGE = {"uncovered", "conflicting", "ambiguous", "not-applicable"}
TRANSITION_RISK_PRIOR_ANSWER_CHECKS = {"not-answered", "answered-not-reflected", "answered-conflicting", "not-applicable"}
ALREADY_DECIDED_RISK_RE = re.compile(
    r"\b(already|previously)\s+(confirmed|decided|covered|approved|resolved|answered|responded)\b"
    r"|이미.{0,20}(답변|대답|응답|확인|결정|정해|반영|승인)"
    r"|기존.{0,20}(확인|결정|반영|승인)",
    re.IGNORECASE,
)
ACCEPTED_RISK_CONFIRMATION_RE = re.compile(
    r"\b(accept|accepted|accepts|explicitly accepts|residual risk)\b|감수|수용",
    re.IGNORECASE,
)
SCOPE_NARROWING_LIMIT_RE = re.compile(
    r"\b("
    r"out[-\s]+of[-\s]+scope|outside\s+scope|excluded?|exclusion|"
    r"read[-\s]*only|readonly|"
    r"manual\s+(?:(?:operation|operations|process|registration|handling|work)\s+(?:only|required|deferred|future)|only)|"
    r"manually\s+(?:registered|created|managed|handled)|"
    r"future\s+(?:work|scope|request|phase)|deferred?|assignment[-\s]*only"
    r")\b"
    r"|범위\s*(?:밖|외|아님|아니다)|제외|읽기\s*전용|조회\s*전용|"
    r"수동(?:\s*(?:처리|등록|생성|관리|운영))?\s*(?:만|으로만|으로\s*한정|으로\s*제한)|"
    r"(?:향후|예정|나중)(?:\s*(?:작업|범위|요청|단계|phase))?\s*(?:로|으로)?\s*(?:미룬다|넘긴다|제외|처리|한정)|"
    r"배정만",
    re.IGNORECASE,
)
TRACEABLE_SCOPE_SOURCE_RE = re.compile(r"\b(?:DEC|REQ|SP|INTENT)-\d+\b", re.IGNORECASE)
PURPOSE_CONFIDENCES = {"confirmed", "inferred", "unknown"}
PURPOSE_KEYWORD_RE = re.compile(
    r"\b(purpose|why|intent|value|goal|outcome|success)\b|목적|왜|의도|가치|목표|성과|성공",
    re.IGNORECASE,
)
IMPLEMENTATION_PLAN_ONLY_QUESTION_RE = re.compile(
    r"\b("
    r"file|files|module|modules|component|components|function|functions|class|classes|method|methods|"
    r"architecture|library|libraries|package|packages|dependency|dependencies|"
    r"test command|test commands|validation strategy|work item|work items|implementation order|"
    r"schema|interface|interfaces|type|types|hook|hooks|script|scripts"
    r")\b"
    r"|파일|모듈|컴포넌트|함수|클래스|메서드|아키텍처|라이브러리|패키지|의존성|"
    r"테스트\s*명령|검증\s*전략|작업\s*항목|구현\s*순서|스키마|인터페이스|타입|훅|스크립트",
    re.IGNORECASE,
)
DEFINITION_LEVEL_QUESTION_RE = re.compile(
    r"\b("
    r"user-visible|user facing|service behavior|service meaning|product policy|policy|"
    r"acceptance outcome|acceptance criteria|success signal|failure behavior|recovery behavior|"
    r"security|privacy|authorization|authentication|payment|data responsibility|integration responsibility|"
    r"scope|boundary|intent|purpose|user flow"
    r")\b"
    r"|사용자.{0,12}(동작|결과|흐름|화면|의미)|서비스.{0,12}(동작|의미)|정책|승인\s*기준|"
    r"성공\s*판정|실패|복구|보안|개인정보|권한|인증|결제|데이터\s*책임|연동\s*책임|범위|경계|목적|의도",
    re.IGNORECASE,
)
NO_PENDING_STATUS_RE = re.compile(r"^(none|n/a|no|없음)$", re.IGNORECASE)
AWAITING_USER_GOAL_STATUSES = {"complete", "completed"}
AWAITING_USER_GOAL_REASON = "awaiting user clarification"
FINGERPRINT_RE = re.compile(r"sha256:([0-9a-fA-F]{64})")
REFERENCE_ROOT_ENV = "STAGEFLOW_REFERENCE_ROOT"
FLOW_STATUSES = {
    "complete",
    "return-to-definition",
    "out-of-scope-by-definition",
    "external-boundary-by-definition",
}
DEFINITION_FLOW_BOUNDARY_STATUSES = {
    "in-scope",
    "out-of-scope-by-definition",
    "external-boundary-by-definition",
}
FLOW_COMPLETION_STATUSES = {"completed", "complete"}
WORK_COMPLETION_STATUSES = {"completed"}
WORK_ID_RE = re.compile(r"\bWORK-\d+\b", re.IGNORECASE)
FLOW_ID_RE = re.compile(r"\bFLOW-\d+\b", re.IGNORECASE)
DFLOW_ID_RE = re.compile(r"\bDFLOW-\d+\b", re.IGNORECASE)
EXTERNAL_BOUNDARY_RATIONALE_RE = re.compile(
    r"\b(consumer|external|boundary|repo|repository|interface|contract|responsibility)\b|"
    r"외부|consumer|컨슈머|소비자|경계|repo|repository|저장소|책임|계약",
    re.IGNORECASE,
)
PLACEHOLDER_CELL_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "no",
    "tbd",
    "todo",
    "unknown",
    "미정",
    "없음",
    "해당 없음",
    "-",
}
FLOW_GENERIC_RE = re.compile(
    r"^(?:"
    r"implement(?:\s+(?:service|ui|code|logic|behavior))*|"
    r"implement\s+service\s+and\s+ui|"
    r"add(?:\s+(?:service|ui|code|logic|behavior))*|"
    r"run\s+tests?|"
    r"write\s+tests?|"
    r"handle\s+errors?|"
    r"as\s+needed|"
    r"구현|구현한다|테스트\s*실행|오류\s*처리|필요시\s*처리"
    r")\.?$",
    re.IGNORECASE,
)


@dataclass
class MarkdownTable:
    headers: list[str]
    rows: list[dict[str, str]]


@dataclass
class ValidationContext:
    root: Path
    stageflow_dir: Path
    request_id: str
    request_dir: Path
    index: dict[str, Any]
    current: dict[str, Any]
    state: dict[str, Any]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_root() -> Path:
    override = os.environ.get(REFERENCE_ROOT_ENV)
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1] / "skills" / "stageflow" / "references"


def read_json_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing `{display_path(path)}`")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        errors.append(f"`{display_path(path)}` is invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"`{display_path(path)}` must contain a JSON object")
        return None
    return value


def display_path(path: Path) -> str:
    return path.as_posix()


def safe_segment(value: str) -> str:
    value = value.strip()
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)[:120]


def current_pointer_path(stageflow_dir: Path, session_id: str | None) -> Path:
    return stageflow_dir / "sessions" / (safe_segment(session_id or "") or "no-session") / "current.json"


def string_value(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def load_context(
    root: Path,
    use_current: bool,
    requested_id: str | None,
    session_id: str | None,
    errors: list[str],
) -> ValidationContext | None:
    stageflow_dir = root / ".stageflow"
    index = read_json_object(stageflow_dir / "index.json", errors)
    if index is None:
        return None

    current: dict[str, Any] = {}
    request_id = requested_id
    if use_current or not request_id:
        current = read_json_object(current_pointer_path(stageflow_dir, session_id), errors) or {}
        request_id = string_value(current, "request_id")

    if not request_id:
        errors.append("no request id selected; use --current or --request <request-id>")
        return None

    requests = index.get("requests")
    if not isinstance(requests, list):
        errors.append("`.stageflow/index.json` field `requests` must be an array")
    elif not any(isinstance(item, dict) and item.get("id") == request_id for item in requests):
        errors.append(f"request `{request_id}` is not registered in `.stageflow/index.json`")

    current_phase = string_value(current, "phase")
    if current_phase and current_phase not in PHASES:
        errors.append(f"selected session current pointer phase `{current_phase}` is not allowed")

    request_dir = stageflow_dir / "requests" / request_id
    if not request_dir.is_dir():
        errors.append(f"missing request folder `.stageflow/requests/{request_id}`")
        return None

    state = read_json_object(request_dir / "state.json", errors) or {}
    validate_state(request_id, state, errors)

    return ValidationContext(root, stageflow_dir, request_id, request_dir, index, current, state)


def validate_state(request_id: str, state: dict[str, Any], errors: list[str]) -> None:
    if string_value(state, "request_id") != request_id:
        errors.append("`state.json` field `request_id` must match selected request")
    phase = string_value(state, "phase")
    if phase not in PHASES:
        errors.append("`state.json` field `phase` must be one of the three stages or `completed`")


def stages_for_phase(phase: str) -> tuple[Stage, ...]:
    if phase == "all":
        return STAGES
    index = STAGES.index(STAGE_BY_PHASE[phase])
    return STAGES[: index + 1]


def validate_phase(context: ValidationContext, phase: str, errors: list[str]) -> list[str]:
    awaiting: list[str] = []
    for stage in stages_for_phase(phase):
        validate_stage(context, stage, errors, awaiting)
    if phase == "all" and string_value(context.state, "phase") != "completed":
        errors.append("`state.json` phase must be `completed` for `--phase all`")
    return awaiting


def validate_stage(context: ValidationContext, stage: Stage, errors: list[str], awaiting: list[str]) -> None:
    stage_dir = context.request_dir / stage.folder
    artifact_path = stage_dir / stage.artifact
    goal_path = stage_dir / "goal.md"
    review_path = stage_dir / "review" / "final.md"
    approval_path = stage_dir / "approval.md"

    rule_ids = validate_stage_rule_document(stage, errors)
    validate_stage_review_agent_prompt(stage, errors)

    artifact_text = read_required_text(artifact_path, errors)
    pending_messages: list[str] = []
    if artifact_text is not None:
        pending_messages = pending_clarification_messages(stage, artifact_text, artifact_path, errors)
        if stage.phase == "definition":
            store_messages = store_pending_messages(stage_dir)
            if store_messages:
                pending_messages = store_messages
        validate_artifact(stage, artifact_text, artifact_path, errors, bool(pending_messages))
        if stage.phase == "implementation-plan":
            validate_implementation_plan_against_definition(context, artifact_path, artifact_text, errors)
        if stage.phase == "implementation":
            validate_implementation_against_plan(context, artifact_path, artifact_text, errors)
        artifact_fingerprint = sha256_file(artifact_path)
    else:
        artifact_fingerprint = None

    if stage.phase == "definition" and artifact_text is not None and artifact_fingerprint is not None:
        store_question_rows = validate_definition_store(stage_dir, artifact_path, artifact_text, artifact_fingerprint, bool(pending_messages), errors)
        validate_question_scope_transition_review(
            stage_dir,
            artifact_path,
            artifact_text,
            artifact_fingerprint,
            errors,
            active_rows=store_question_rows if store_question_rows else None,
        )
    if stage.phase == "definition" and artifact_text is not None and artifact_fingerprint is not None:
        validate_transition_risk_gate(stage_dir, artifact_text, artifact_fingerprint, errors, bool(pending_messages))
    if stage.phase != "definition":
        validate_goal(stage, goal_path, artifact_fingerprint, errors, bool(pending_messages))
    if pending_messages:
        awaiting.extend(pending_messages)
        return
    validate_review(context, stage, review_path, artifact_fingerprint, rule_ids, errors)
    validate_approval(stage, approval_path, errors)


def read_required_text(path: Path, errors: list[str]) -> str | None:
    if not path.is_file():
        errors.append(f"missing `{display_path(path)}`")
        return None
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        errors.append(f"`{display_path(path)}` must not be empty")
    return text


def validate_stage_rule_document(stage: Stage, errors: list[str]) -> list[str]:
    path = reference_root() / "stages" / stage.rule_folder / stage.rule_file
    text = read_required_text(path, errors)
    if text is None:
        return []

    if f"# {stage.rule_title}" not in text:
        errors.append(f"`{display_path(path)}` must include `# {stage.rule_title}`")
    target = f"Target: `{stage.folder}/{stage.artifact}`"
    if target not in section_text(text, "## Stage Artifact"):
        errors.append(f"`{display_path(path)}` Stage Artifact must record `{target}`")

    for required_reference_section in ("Stage Responsibility", "Request Type Profiles"):
        if not section_text(text, f"## {required_reference_section}").strip():
            errors.append(
                f"`{display_path(path)}` must include non-empty `## {required_reference_section}`"
            )

    artifact_format = fenced_code_block_after_heading(text, "## Stage Artifact Format")
    if not artifact_format.strip():
        errors.append(f"`{display_path(path)}` must include non-empty `## Stage Artifact Format`")
    if f"# {stage.title}" not in artifact_format:
        errors.append(f"`{display_path(path)}` Stage Artifact Format must include `# {stage.title}`")
    for section in stage.required_sections:
        if f"## {section}" not in artifact_format:
            errors.append(f"`{display_path(path)}` Stage Artifact Format must include `## {section}`")

    required_sections = section_text(text, "## Required Artifact Sections")
    for section in stage.required_sections:
        if f"`## {section}`" not in required_sections:
            errors.append(f"`{display_path(path)}` Required Artifact Sections must list `## {section}`")

    table = parse_required_table(
        path,
        section_text(text, "## Writing And Review Rule Table"),
        ("Rule ID", "Writing Rule", "Required Artifact Evidence", "Review Check", "Blocking Condition"),
        "## Writing And Review Rule Table",
        errors,
    )
    rule_ids = [row.get("Rule ID", "").strip() for row in table.rows if row.get("Rule ID", "").strip()]
    if not rule_ids:
        errors.append(f"`{display_path(path)}` Writing And Review Rule Table must include at least one Rule ID")
    duplicates = sorted({rule_id for rule_id in rule_ids if rule_ids.count(rule_id) > 1})
    for rule_id in duplicates:
        errors.append(f"`{display_path(path)}` has duplicate Rule ID `{rule_id}`")
    if stage.phase == "implementation-plan":
        flow_contract = parse_required_table(
            path,
            section_text(text, "## Flow Completeness Contract"),
            ("Rule ID", "Flow Rule", "Plan Must Record", "Reviewer Must Confirm", "Blocking Condition"),
            "## Flow Completeness Contract",
            errors,
        )
        flow_rule_ids = [
            row.get("Rule ID", "").strip()
            for row in flow_contract.rows
            if row.get("Rule ID", "").strip()
        ]
        if not flow_rule_ids:
            errors.append(f"`{display_path(path)}` Flow Completeness Contract must include at least one Rule ID")
        missing_flow_prefix = [rule_id for rule_id in flow_rule_ids if not rule_id.startswith("IP-FLOW-")]
        for rule_id in missing_flow_prefix:
            errors.append(f"`{display_path(path)}` Flow Completeness Contract Rule ID `{rule_id}` must start with `IP-FLOW-`")
        all_rule_ids = rule_ids + flow_rule_ids
        duplicates = sorted({rule_id for rule_id in all_rule_ids if all_rule_ids.count(rule_id) > 1})
        for rule_id in duplicates:
            errors.append(f"`{display_path(path)}` has duplicate Rule ID `{rule_id}`")
        return all_rule_ids
    return rule_ids


def validate_stage_review_agent_prompt(stage: Stage, errors: list[str]) -> None:
    artifact_stem = stage.artifact[:-3] if stage.artifact.endswith(".md") else stage.artifact
    prompt_file = f"{artifact_stem}-review-agent-prompt.md"
    path = reference_root() / "stages" / stage.rule_folder / prompt_file
    text = read_required_text(path, errors)
    if text is None:
        return

    expected_title = f"# {stage.title} Review Agent Prompt"
    if expected_title not in text:
        errors.append(f"`{display_path(path)}` must include `{expected_title}`")
    if label_value(text, "Stage") != stage.phase:
        errors.append(f"`{display_path(path)}` must record `Stage: {stage.phase}`")
    expected_artifact = f"Stage Artifact: `{stage.folder}/{stage.artifact}`"
    if expected_artifact not in text:
        errors.append(f"`{display_path(path)}` must record `{expected_artifact}`")
    expected_rule_file = f"Writing And Review Rule File: `references/stages/{stage.rule_folder}/{stage.rule_file}`"
    if expected_rule_file not in text:
        errors.append(f"`{display_path(path)}` must record `{expected_rule_file}`")

    for section in ("Review Mission", "Required Inputs", "Review Instructions", "Required Output"):
        if not section_text(text, f"## {section}").strip():
            errors.append(f"`{display_path(path)}` must include non-empty `## {section}`")

    for phrase in (
        "Do not review unrelated files",
        "Do not implement changes",
        "Self-review never satisfies",
    ):
        if phrase not in text:
            errors.append(f"`{display_path(path)}` must include `{phrase}`")

    for marker in (
        "# Subagent Review Shard",
        "Shard Scope",
        "## Inputs Read",
        "## Verdict",
        "## Blocking Issues",
        "PASS or FAIL",
        "Do not write `review/final.md`",
    ):
        if marker not in text:
            errors.append(f"`{display_path(path)}` Required Output must include `{marker}`")


def validate_artifact(stage: Stage, text: str, path: Path, errors: list[str], has_pending_clarifications: bool = False) -> None:
    if f"# {stage.title}" not in text:
        errors.append(f"`{display_path(path)}` must start with or include `# {stage.title}`")
    for section in stage.required_sections:
        if not section_text(text, f"## {section}").strip():
            errors.append(f"`{display_path(path)}` must include non-empty `## {section}`")
    for requirement in stage.artifact_tables:
        validate_table_columns(path, text, requirement, errors)
    if stage.phase == "definition":
        validate_definition_purpose(path, text, errors, has_pending_clarifications)
        validate_definition_blocking_questions(path, text, errors)
        validate_definition_clarification_history(path, text, errors, has_pending_clarifications)
        validate_definition_scope_narrowing_evidence(path, text, errors, has_pending_clarifications)
        validate_definition_approved_flow_inventory(path, text, errors)
    if stage.phase == "implementation-plan":
        validate_implementation_plan_depth(path, text, errors)
        validate_implementation_plan_flow_completeness(path, text, errors)



def is_placeholder_question_text(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return not normalized or normalized in {"n/a", "none", "no open question", "no pending clarification", "없음"}


def validate_definition_question_stage_boundary(
    path: Path,
    section: str,
    question_id: str,
    combined_question_text: str,
    errors: list[str],
) -> None:
    if is_placeholder_question_text(combined_question_text):
        return
    if IMPLEMENTATION_PLAN_ONLY_QUESTION_RE.search(combined_question_text) and not DEFINITION_LEVEL_QUESTION_RE.search(combined_question_text):
        errors.append(
            f"`{display_path(path)}` {section} row `{question_id}` asks an implementation-plan-only question; "
            "defer module/file/test command/architecture/work-item decisions to implementation-plan unless the answer changes definition-level service meaning"
        )


def pending_clarification_messages(stage: Stage, text: str, path: Path, errors: list[str]) -> list[str]:
    if stage.phase != "definition":
        return []
    table = parse_first_markdown_table(section_text(text, "## Pending Clarifications"))
    if not table.rows:
        return []

    messages: list[str] = []
    scopes: list[str] = []
    seen_ids: set[str] = set()
    for row in table.rows:
        status = row.get("Status", "").strip()
        if not status or NO_PENDING_STATUS_RE.fullmatch(status):
            continue
        pending_id = row.get("ID", "").strip() or "<unknown>"
        if pending_id in seen_ids:
            errors.append(f"`{display_path(path)}` Pending Clarifications repeats pending ID `{pending_id}`")
            continue
        seen_ids.add(pending_id)
        if not PENDING_STATUS_RE.fullmatch(status):
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` must use Status `pending`/`awaiting` or `none`"
            )
            continue

        scope = row.get("Question Scope", "").strip()
        question = row.get("Question", "").strip()
        options = row.get("Options", "").strip()
        recommended = row.get("Recommended Option", "").strip()
        transition = row.get("Transition Option", "").strip()
        why = row.get("Why This Matters", "").strip()
        missing = [
            name
            for name, value in (
                ("Question Scope", scope),
                ("Question", question),
                ("Options", options),
                ("Recommended Option", recommended),
                ("Why This Matters", why),
            )
            if not value or value.lower() in {"n/a", "none"}
        ]
        if missing:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` is missing user-answerable fields: {', '.join(missing)}"
            )
            continue
        scopes.append(scope)
        if scope not in QUESTION_SCOPES:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` Question Scope must be one of {', '.join(QUESTION_SCOPES)}"
            )
        labeled_options = labeled_proposal_options(options)
        if len(labeled_options) < 2:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` must include at least two explicit labeled proposal options such as `Option 1:` and `Option 2:`"
            )
        if any(is_stop_signal_option_item(option) for option in split_option_items(options)):
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` must not include the user stop signal as a question option"
            )
        if USER_STOP_SIGNAL_RE.search(transition):
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` must not include the user stop signal in `Transition Option`; "
                "record stop signals only in Clarification History.User Transition Signal"
            )
        if transition.strip().lower() != "n/a":
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` Transition Option must be `N/A` while the question is pending"
            )
        validate_definition_question_stage_boundary(
            path,
            "Pending Clarifications",
            pending_id,
            " ".join((question, options, recommended, why)),
            errors,
        )
        messages.append(
            f"`{display_path(path)}` pending clarification `{pending_id}`: 질문 범위: {scope} [{scope}] Question: {question} Options: {options} Recommended: {recommended} Transition option: {transition} Why this matters: {why}"
        )
    if len(messages) > 5:
        errors.append(
            f"`{display_path(path)}` Pending Clarifications must ask no more than five active questions per batch before the user explicitly stops"
        )
    validate_pending_clarification_scope_batch(path, active_pending_rows(text), errors)
    return messages


def validate_pending_clarification_scope_batch(path: Path, rows: list[dict[str, str]], errors: list[str]) -> None:
    valid_scopes = [
        row.get("Question Scope", "").strip()
        for row in rows
        if row.get("Question Scope", "").strip() in QUESTION_SCOPE_ORDER
    ]
    if len(set(valid_scopes)) <= 1:
        return
    ordered_scopes = sorted(set(valid_scopes), key=lambda scope: QUESTION_SCOPE_ORDER[scope])
    errors.append(
        f"`{display_path(path)}` Pending Clarifications active batch must use one Question Scope at a time; "
        f"finish higher-scope questions before adding lower-scope questions ({', '.join(ordered_scopes)})"
    )


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


def normalize_store_pending_question(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    question_id = json_string(raw, "id", "pending_id", "pendingId", "ID").upper()
    status = json_string(raw, "status", "Status") or "pending"
    if not PENDING_STATUS_RE.fullmatch(status.strip()):
        return None
    return {
        "ID": question_id,
        "Question Scope": json_string(raw, "scope", "question_scope", "questionScope", "Question Scope"),
        "Question": json_string(raw, "question", "Question"),
        "Options": store_question_options_text(raw.get("options", raw.get("Options", ""))),
        "Recommended Option": json_string(raw, "recommended_option", "recommendedOption", "recommended", "Recommended Option"),
        "Transition Option": json_string(raw, "transition_option", "transitionOption", "Transition Option") or "N/A",
        "Why This Matters": json_string(raw, "why_this_matters", "whyThisMatters", "why", "Why This Matters"),
        "Status": status,
    }


def store_active_pending_questions(working_set: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in json_list(working_set, "active_pending_questions", "activePendingQuestions"):
        row = normalize_store_pending_question(raw)
        if row is not None:
            rows.append(row)
    return rows


def validate_store_active_pending_questions(working_set: dict[str, Any], path: Path, errors: list[str]) -> list[dict[str, str]]:
    raw_questions = json_list(working_set, "active_pending_questions", "activePendingQuestions")
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, dict):
            errors.append(f"`{display_path(path)}` active_pending_questions[{index}] must be an object")
            continue
        row = normalize_store_pending_question(raw)
        if row is None:
            errors.append(f"`{display_path(path)}` active_pending_questions[{index}] must use pending/awaiting status")
            continue
        pending_id = row.get("ID", "")
        if not fullmatch_id(PENDING_ID_RE, pending_id):
            errors.append(f"`{display_path(path)}` active_pending_questions[{index}] must include `PENDING-*` id")
        elif pending_id in seen_ids:
            errors.append(f"`{display_path(path)}` active_pending_questions repeats pending ID `{pending_id}`")
        seen_ids.add(pending_id)

        scope = row.get("Question Scope", "").strip()
        question = row.get("Question", "").strip()
        options = row.get("Options", "").strip()
        recommended = row.get("Recommended Option", "").strip()
        transition = row.get("Transition Option", "").strip()
        why = row.get("Why This Matters", "").strip()
        missing = [
            name
            for name, value in (
                ("Question Scope", scope),
                ("Question", question),
                ("Options", options),
                ("Recommended Option", recommended),
                ("Why This Matters", why),
            )
            if not value or value.lower() in {"n/a", "none"}
        ]
        if missing:
            errors.append(
                f"`{display_path(path)}` active_pending_questions row `{pending_id or index}` is missing user-answerable fields: {', '.join(missing)}"
            )
        if scope and scope not in QUESTION_SCOPES:
            errors.append(f"`{display_path(path)}` active_pending_questions row `{pending_id or index}` Question Scope must be one of {', '.join(QUESTION_SCOPES)}")
        if options and len(labeled_proposal_options(options)) < 2:
            errors.append(
                f"`{display_path(path)}` active_pending_questions row `{pending_id or index}` must include at least two explicit labeled proposal options"
            )
        if any(is_stop_signal_option_item(option) for option in split_option_items(options)):
            errors.append(
                f"`{display_path(path)}` active_pending_questions row `{pending_id or index}` must not include the user stop signal as a question option"
            )
        if transition.lower() != "n/a":
            errors.append(f"`{display_path(path)}` active_pending_questions row `{pending_id or index}` Transition Option must be `N/A` while pending")
        validate_definition_question_stage_boundary(
            path,
            "definition-store active_pending_questions",
            pending_id or f"active_pending_questions[{index}]",
            " ".join((question, options, recommended, why)),
            errors,
        )
        rows.append(row)

    if len(rows) > 5:
        errors.append(f"`{display_path(path)}` active_pending_questions must contain no more than five active questions")
    validate_pending_clarification_scope_batch(path, rows, errors)
    return rows


def store_pending_messages(stage_dir: Path) -> list[str]:
    working_set_path = stage_dir / "definition-store" / "working-set.json"
    if not working_set_path.is_file():
        return []
    try:
        value = json.loads(working_set_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if not isinstance(value, dict):
        return []
    rows = store_active_pending_questions(value)
    if not rows:
        return []
    messages: list[str] = []
    for row in rows:
        scope = row.get("Question Scope", "").strip()
        messages.append(
            f"`{display_path(working_set_path)}` pending clarification `{row.get('ID', '<unknown>')}`: "
            f"질문 범위: {scope} [{scope}] Question: {row.get('Question', '')} "
            f"Options: {row.get('Options', '')} Recommended: {row.get('Recommended Option', '')} "
            f"Transition option: {row.get('Transition Option', 'N/A')} Why this matters: {row.get('Why This Matters', '')}"
        )
    return messages


def uppercase_json_ids(pattern: re.Pattern[str], values: list[Any]) -> set[str]:
    ids: set[str] = set()
    for value in values:
        if isinstance(value, str) and pattern.fullmatch(value.strip()):
            ids.add(value.strip().upper())
    return ids


def read_store_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing `{display_path(path)}`")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        errors.append(f"`{display_path(path)}` is invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"`{display_path(path)}` must contain a JSON object")
        return None
    return value


def read_decision_ledger(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        errors.append(f"missing `{display_path(path)}`")
        return []
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"`{display_path(path)}` line {index} is invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"`{display_path(path)}` line {index} must contain a JSON object")
            continue
        rows.append(value)
    return rows


def trace_index_entries(trace_index: dict[str, Any], path: Path, errors: list[str]) -> dict[tuple[str, str], set[str]]:
    entries: dict[tuple[str, str], set[str]] = {}

    def add_entry(pending_id: str, decision_id: str, affected_values: list[Any], label: str) -> None:
        pending = pending_id.strip().upper()
        decision = decision_id.strip().upper()
        if not fullmatch_id(PENDING_ID_RE, pending):
            errors.append(f"`{display_path(path)}` trace `{label}` must include a `PENDING-*` pending id")
            return
        if not fullmatch_id(DEC_ID_RE, decision):
            errors.append(f"`{display_path(path)}` trace `{label}` must include a `DEC-*` decision id")
            return
        affected = uppercase_json_ids(DEFINITION_STORE_AFFECTED_ID_RE, affected_values)
        if not affected:
            errors.append(f"`{display_path(path)}` trace `{label}` must include non-empty affected IDs")
        entries[(pending, decision)] = affected

    pending_map = trace_index.get("pending")
    if isinstance(pending_map, dict):
        for pending_id, item in pending_map.items():
            if not isinstance(item, dict):
                errors.append(f"`{display_path(path)}` pending trace `{pending_id}` must be an object")
                continue
            decision_id = json_string(item, "decision_id", "decisionId", "decision")
            add_entry(str(pending_id), decision_id, json_list(item, "affected_ids", "affectedIds", "affected"), str(pending_id))

    traces = trace_index.get("traces")
    if isinstance(traces, list):
        for index, item in enumerate(traces, start=1):
            if not isinstance(item, dict):
                errors.append(f"`{display_path(path)}` traces[{index}] must be an object")
                continue
            pending_id = json_string(item, "pending_id", "pendingId", "pending")
            decision_id = json_string(item, "decision_id", "decisionId", "decision")
            add_entry(pending_id, decision_id, json_list(item, "affected_ids", "affectedIds", "affected"), f"traces[{index}]")

    return entries


def validate_gate_json_fingerprint(path: Path, value: dict[str, Any], expected_fingerprint: str, errors: list[str]) -> None:
    fingerprint = json_string(value, "definition_fingerprint", "definitionFingerprint", "snapshot_fingerprint", "snapshotFingerprint")
    if fingerprint and fingerprint != expected_fingerprint:
        errors.append(f"`{display_path(path)}` definition_fingerprint must match current definition.md `{expected_fingerprint}`")


def validate_definition_store_gate_artifacts(
    store_dir: Path,
    current_gate: str,
    expected_fingerprint: str,
    errors: list[str],
) -> None:
    if current_gate == TARGETED_SYNC_GATE:
        plan_path = store_dir / "targeted-sync-plan.json"
        plan = read_store_json(plan_path, errors)
        if plan is not None:
            validate_gate_json_fingerprint(plan_path, plan, expected_fingerprint, errors)
        return

    if current_gate == FULL_CONSISTENCY_GATE:
        report_path = store_dir / "full-consistency-report.json"
        report = read_store_json(report_path, errors)
        if report is not None:
            validate_gate_json_fingerprint(report_path, report, expected_fingerprint, errors)
            verdict = json_string(report, "verdict", "Verdict", "status", "Status")
            if verdict.upper() != "PASS":
                errors.append(f"`{display_path(report_path)}` verdict must be PASS for full-consistency-required")


def validate_definition_store(
    stage_dir: Path,
    artifact_path: Path,
    definition_text: str,
    definition_fingerprint: str,
    has_pending_clarifications: bool,
    errors: list[str],
) -> list[dict[str, str]] | None:
    store_dir = stage_dir / "definition-store"
    if not store_dir.exists():
        if has_pending_clarifications:
            errors.append(
                f"`{display_path(store_dir)}` is required while definition has active Pending Clarifications; "
                "create the definition-store hot path before processing the next user answer"
            )
        return None
    if not store_dir.is_dir():
        errors.append(f"`{display_path(store_dir)}` must be a directory")
        return None

    working_set_path = store_dir / "working-set.json"
    decision_ledger_path = store_dir / "decision-ledger.jsonl"
    trace_index_path = store_dir / "trace-index.json"
    sync_state_path = store_dir / "sync-state.json"

    working_set = read_store_json(working_set_path, errors)
    trace_index = read_store_json(trace_index_path, errors)
    sync_state = read_store_json(sync_state_path, errors)
    ledger_rows = read_decision_ledger(decision_ledger_path, errors)
    if working_set is None or trace_index is None or sync_state is None:
        return None

    store_question_rows = validate_store_active_pending_questions(working_set, working_set_path, errors)
    store_question_ids = {row.get("ID", "").strip().upper() for row in store_question_rows if row.get("ID", "").strip()}
    active_pending_ids = {row.get("ID", "").strip().upper() for row in active_pending_rows(definition_text) if row.get("ID", "").strip()}
    store_pending_ids = uppercase_json_ids(PENDING_ID_RE, json_list(working_set, "active_pending_ids", "activePendingIds"))
    if store_pending_ids and not store_question_ids:
        errors.append(
            f"`{display_path(working_set_path)}` active_pending_questions is required when active_pending_ids are present; "
            "repair the definition-store canonical pending batch"
        )
    if store_question_ids:
        if store_pending_ids and store_pending_ids != store_question_ids:
            errors.append(
                f"`{display_path(working_set_path)}` active_pending_ids must match active_pending_questions "
                f"({', '.join(sorted(store_question_ids))})"
            )
    elif store_pending_ids != active_pending_ids:
        errors.append(
            f"`{display_path(working_set_path)}` active pending IDs must match definition.md Pending Clarifications "
            f"({', '.join(sorted(active_pending_ids)) or 'none'})"
        )

    current_scope = json_string(working_set, "current_scope", "currentScope")
    store_scopes = {row.get("Question Scope", "").strip() for row in store_question_rows if row.get("Question Scope", "").strip()}
    active_scopes = store_scopes or {row.get("Question Scope", "").strip() for row in active_pending_rows(definition_text) if row.get("Question Scope", "").strip()}
    if active_scopes and not current_scope:
        errors.append(f"`{display_path(working_set_path)}` must include current_scope while Pending Clarifications are active")
    if current_scope and current_scope not in QUESTION_SCOPES:
        errors.append(f"`{display_path(working_set_path)}` current_scope must be one of {', '.join(QUESTION_SCOPES)}")
    if active_scopes and current_scope and current_scope not in active_scopes:
        errors.append(f"`{display_path(working_set_path)}` current_scope must match active Pending Clarifications scope")

    working_risk = json_string(working_set, "risk_level", "riskLevel")
    if working_risk and working_risk not in RISK_LEVELS:
        errors.append(f"`{display_path(working_set_path)}` risk_level must be one of {', '.join(sorted(RISK_LEVELS))}")

    trace_entries = trace_index_entries(trace_index, trace_index_path, errors)
    sync_entries = sync_state.get("decision_sync")
    if not isinstance(sync_entries, dict):
        errors.append(f"`{display_path(sync_state_path)}` must include object `decision_sync`")
        sync_entries = {}

    current_gate = json_string(sync_state, "current_gate", "currentGate", "gate") or json_string(working_set, "current_gate", "currentGate", "gate")
    if current_gate and current_gate not in STORE_GATES:
        errors.append(f"`{display_path(sync_state_path)}` current_gate must be one of {', '.join(sorted(STORE_GATES))}")
    if not store_question_rows and current_gate not in STORE_SYNC_GATES:
        errors.append(
            f"`{display_path(working_set_path)}` must keep active pending questions until "
            "`sync-state.current_gate` moves to a recognized sync gate"
        )

    snapshot_fingerprint = json_string(sync_state, "definition_fingerprint", "definitionFingerprint", "snapshot_fingerprint", "snapshotFingerprint")
    expected_fingerprint = f"sha256:{definition_fingerprint}"
    if not snapshot_fingerprint:
        errors.append(f"`{display_path(sync_state_path)}` must include current definition snapshot fingerprint")
    elif snapshot_fingerprint != expected_fingerprint and (not has_pending_clarifications or current_gate == SNAPSHOT_CURRENT_GATE):
        errors.append(f"`{display_path(sync_state_path)}` snapshot fingerprint must match current definition.md `{expected_fingerprint}` before review or approval")

    validate_definition_store_gate_artifacts(store_dir, current_gate, expected_fingerprint, errors)

    valid_decision_risks: dict[str, str] = {}
    for row in ledger_rows:
        decision_id = json_string(row, "decision_id", "decisionId", "id").upper()
        pending_id = json_string(row, "source_pending_id", "sourcePendingId", "pending_id", "pendingId").upper()
        affected_ids = uppercase_json_ids(DEFINITION_STORE_AFFECTED_ID_RE, json_list(row, "affected_ids", "affectedIds", "affected"))
        risk_level = json_string(row, "risk_level", "riskLevel")
        row_valid = True
        if not fullmatch_id(DEC_ID_RE, decision_id):
            errors.append(f"`{display_path(decision_ledger_path)}` decision row must include `DEC-*` decision_id")
            continue
        if not fullmatch_id(PENDING_ID_RE, pending_id):
            errors.append(f"`{display_path(decision_ledger_path)}` decision `{decision_id}` must include `PENDING-*` source_pending_id")
            row_valid = False
        if not affected_ids:
            errors.append(f"`{display_path(decision_ledger_path)}` decision `{decision_id}` must include non-empty affected_ids")
            row_valid = False
        if risk_level not in RISK_LEVELS:
            errors.append(f"`{display_path(decision_ledger_path)}` decision `{decision_id}` risk_level must be one of {', '.join(sorted(RISK_LEVELS))}")
            row_valid = False

        trace_affected = trace_entries.get((pending_id, decision_id), set())
        if not trace_affected:
            errors.append(f"`{display_path(trace_index_path)}` must include trace for `{pending_id}` -> `{decision_id}`")
            row_valid = False
        for affected_id in sorted(affected_ids - trace_affected):
            errors.append(f"`{display_path(decision_ledger_path)}` decision `{decision_id}` affected ID `{affected_id}` must appear in trace-index")
            row_valid = False

        sync_entry = sync_entries.get(decision_id)
        if not isinstance(sync_entry, dict):
            errors.append(f"`{display_path(sync_state_path)}` decision_sync must include `{decision_id}`")
            row_valid = False
            continue
        sync_status = json_string(sync_entry, "status")
        if sync_status not in SYNC_STATUSES:
            errors.append(f"`{display_path(sync_state_path)}` decision `{decision_id}` status must be one of {', '.join(sorted(SYNC_STATUSES))}")
            row_valid = False
        if risk_level == "medium" and not has_pending_clarifications and sync_status not in TARGETED_SYNC_STATUSES:
            errors.append(f"`{display_path(sync_state_path)}` medium-risk decision `{decision_id}` requires targeted sync before review or approval")
        if risk_level == "high" and sync_status not in FULL_SYNC_STATUSES:
            errors.append(f"`{display_path(sync_state_path)}` high-risk decision `{decision_id}` requires full consistency sync before continuing")
        if row_valid:
            valid_decision_risks[decision_id] = risk_level

    if current_gate == TARGETED_SYNC_GATE and "medium" not in set(valid_decision_risks.values()):
        errors.append(f"`{display_path(sync_state_path)}` targeted-sync-required requires a valid medium-risk store decision")
    if current_gate == FULL_CONSISTENCY_GATE and "high" not in set(valid_decision_risks.values()):
        errors.append(f"`{display_path(sync_state_path)}` full-consistency-required requires a valid high-risk store decision")

    return store_question_rows


def required_question_scope_transitions(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    ranks = [
        QUESTION_SCOPE_ORDER[scope]
        for row in rows
        for scope in [row.get("Question Scope", "").strip()]
        if scope in QUESTION_SCOPE_ORDER
    ]
    if not ranks:
        return []
    max_rank = max(ranks)
    required: list[tuple[str, str]] = []
    if max_rank >= QUESTION_SCOPE_ORDER["주요결정"]:
        required.append(("큰방향", "주요결정"))
    if max_rank >= QUESTION_SCOPE_ORDER["세부확인"]:
        required.append(("주요결정", "세부확인"))
    return required


def validate_question_scope_transition_review(
    stage_dir: Path,
    artifact_path: Path,
    definition_text: str,
    definition_fingerprint: str,
    errors: list[str],
    *,
    active_rows: list[dict[str, str]] | None = None,
) -> None:
    rows_for_transition = active_rows if active_rows is not None else active_pending_rows(definition_text)
    required_transitions = required_question_scope_transitions(rows_for_transition)
    if not required_transitions:
        return

    review_path = stage_dir / "question-scope-transition-review.md"
    if not review_path.is_file():
        for transition in required_transitions:
            label = QUESTION_SCOPE_TRANSITION_LABELS[transition]
            errors.append(
                f"`{display_path(artifact_path)}` pending `{transition[1]}` questions require PASS in "
                f"`01-definition/question-scope-transition-review.md` for `{label}`"
            )
        return
    review_text = read_required_text(review_path, errors)
    if review_text is None:
        return
    if "# Question Scope Transition Review" not in review_text:
        errors.append(f"`{display_path(review_path)}` must include `# Question Scope Transition Review`")
    validate_table_columns(
        review_path,
        review_text,
        TableRequirement("Transition Checks", QUESTION_SCOPE_TRANSITION_REVIEW_COLUMNS),
        errors,
    )

    table = parse_first_markdown_table(section_text(review_text, "## Transition Checks"))
    if not table.rows:
        errors.append(f"`{display_path(review_path)}` Transition Checks must include required question scope transition rows")
        return

    allowed_labels = set(QUESTION_SCOPE_TRANSITION_LABELS.values())
    rows_by_transition: dict[str, dict[str, str]] = {}
    for row in table.rows:
        transition = normalized_cell(row.get("Transition", ""))
        display_transition = transition or "<unknown>"
        if transition not in allowed_labels:
            errors.append(f"`{display_path(review_path)}` Transition Checks row `{display_transition}` uses an unknown transition")
            continue
        if transition in rows_by_transition:
            errors.append(f"`{display_path(review_path)}` Transition Checks repeats transition `{transition}`")
        rows_by_transition[transition] = row

        for column in (
            "Definition Artifact Fingerprint",
            "Evidence Reviewed",
            "Remaining Higher-Scope Questions",
            "Reviewer",
        ):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(review_path)}` Transition Checks row `{transition}` must include substantive `{column}`")

        expected_fingerprint = f"sha256:{definition_fingerprint}"
        if expected_fingerprint not in row.get("Definition Artifact Fingerprint", ""):
            errors.append(
                f"`{display_path(review_path)}` Transition Checks row `{transition}` must reference current "
                f"definition fingerprint `{expected_fingerprint}`"
            )

        verdict = row.get("Verdict", "").strip()
        if verdict != "PASS":
            errors.append(f"`{display_path(review_path)}` Transition Checks row `{transition}` Verdict must be PASS before lower-scope questions are pending")

    for transition in required_transitions:
        label = QUESTION_SCOPE_TRANSITION_LABELS[transition]
        if label not in rows_by_transition:
            errors.append(
                f"`{display_path(artifact_path)}` pending `{transition[1]}` questions require PASS in "
                f"`01-definition/question-scope-transition-review.md` for `{label}`"
            )


def split_option_items(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?:<br\s*/?>|[;\n|])", text, flags=re.IGNORECASE) if item.strip()]


def option_item_body(item: str) -> str:
    return OPTION_LABEL_RE.sub("", item, count=1).strip()


def is_stop_signal_option_item(item: str) -> bool:
    if not OPTION_LABEL_RE.match(item):
        return False
    body = option_item_body(item)
    normalized = re.sub(r"[\s.。!！]+", " ", body.lower()).strip()
    if normalized in {
        "proceed",
        "go ahead",
        "approve",
        "approved",
        "yes",
        "stop asking",
        "enough",
        "질문 그만",
        "충분",
        "충분해",
        "진행",
        "승인",
    }:
        return True
    references_implementation_plan = "implementation plan" in normalized or ("구현" in normalized and "계획" in normalized)
    moves_to_next_stage = any(token in normalized for token in ("넘어", "진행", "시작", "proceed", "go ahead", "move"))
    return references_implementation_plan and moves_to_next_stage


def labeled_proposal_options(text: str) -> list[str]:
    labeled: list[str] = []
    for item in split_option_items(text):
        if is_stop_signal_option_item(item):
            continue
        if OPTION_LABEL_RE.match(item) and option_item_body(item):
            labeled.append(item)
    return labeled

def has_at_least_two_proposals(text: str) -> bool:
    return len(labeled_proposal_options(text)) >= 2


def is_empty_clarification_history_row(row: dict[str, str]) -> bool:
    values = [value.strip().lower() for value in row.values()]
    if not values:
        return True
    joined = " ".join(values)
    return (
        "no completed clarification" in joined
        or "no clarification" in joined
        or all(value in {"", "n/a", "none", "없음"} for value in values)
    )

def active_pending_rows(text: str) -> list[dict[str, str]]:
    table = parse_first_markdown_table(section_text(text, "## Pending Clarifications"))
    return [row for row in table.rows if PENDING_STATUS_RE.fullmatch(row.get("Status", "").strip())]


def has_user_stop_signal(text: str) -> bool:
    table = parse_first_markdown_table(section_text(text, "## Clarification History"))
    for row in table.rows:
        if USER_STOP_SIGNAL_RE.search(row.get("User Transition Signal", "")):
            return True
    return False


def is_purpose_focused_pending(row: dict[str, str]) -> bool:
    if row.get("Question Scope", "").strip() != "큰방향":
        return False
    combined = " ".join(row.get(column, "") for column in ("Question", "Options", "Why This Matters"))
    return bool(PURPOSE_KEYWORD_RE.search(combined))


def purpose_confidence_rank(confidences: list[str]) -> str:
    if "confirmed" in confidences:
        return "confirmed"
    if "inferred" in confidences:
        return "inferred"
    return "unknown"


def validate_definition_purpose(path: Path, text: str, errors: list[str], has_pending_clarifications: bool) -> None:
    table = parse_first_markdown_table(section_text(text, "## Purpose And Intent"))
    if not table.rows:
        return

    confidences: list[str] = []
    for index, row in enumerate(table.rows, start=1):
        row_label = f"Purpose And Intent row {index}"
        for column in ("Purpose", "User Value", "Business/Product Value", "Source", "Confidence"):
            value = row.get(column, "").strip()
            if not value or value.lower() in {"n/a", "none"}:
                errors.append(f"`{display_path(path)}` {row_label} must include `{column}`")
        confidence = row.get("Confidence", "").strip().lower()
        if confidence and confidence not in PURPOSE_CONFIDENCES:
            errors.append(
                f"`{display_path(path)}` {row_label} Confidence must be one of confirmed, inferred, unknown"
            )
        if confidence in PURPOSE_CONFIDENCES:
            confidences.append(confidence)

    confidence_rank = purpose_confidence_rank(confidences)
    pending_rows = active_pending_rows(text)
    if confidence_rank in {"unknown", "inferred"} and pending_rows:
        if not any(is_purpose_focused_pending(row) for row in pending_rows):
            errors.append(
                f"`{display_path(path)}` Purpose And Intent is {confidence_rank}; Pending Clarifications must include at least one purpose-focused 큰방향 question"
            )
    if confidence_rank != "confirmed" and has_user_stop_signal(text):
        errors.append(
            f"`{display_path(path)}` Purpose And Intent must be confirmed before definition clarification can stop"
        )


def validate_definition_blocking_questions(path: Path, text: str, errors: list[str]) -> None:
    table = parse_first_markdown_table(section_text(text, "## Open Questions"))
    for row in table.rows:
        question_id = row.get("ID", "").strip() or "<unknown>"
        validate_definition_question_stage_boundary(
            path,
            "Open Questions",
            question_id,
            " ".join(
                row.get(column, "")
                for column in (
                    "Decision Needed",
                    "Context Or Conflict",
                    "Recommended Option",
                    "Alternatives",
                    "Impact",
                    "Resolution Target",
                )
            ),
            errors,
        )
        blocking_value = row.get("Blocking", "").strip()
        if BLOCKING_OPEN_QUESTION_RE.fullmatch(blocking_value):
            errors.append(
                f"`{display_path(path)}` Open Questions row `{question_id}` is still blocking; "
                "resolve it before definition approval"
            )


def validate_definition_clarification_history(path: Path, text: str, errors: list[str], has_pending_clarifications: bool) -> None:
    table = parse_first_markdown_table(section_text(text, "## Clarification History"))
    if not table.rows:
        return
    has_transition_signal = False
    for index, row in enumerate(table.rows):
        if is_empty_clarification_history_row(row):
            continue
        round_id = row.get("Round ID", "").strip() or "<unknown>"
        questions = row.get("Questions Asked", "").strip()
        transition_signal = row.get("User Transition Signal", "").strip()
        if not has_meaningful_proposal_options(questions):
            errors.append(
                f"`{display_path(path)}` Clarification History row `{round_id}` must include a concrete question with at least two proposal options"
            )
        is_transition = bool(USER_STOP_SIGNAL_RE.search(transition_signal))
        if is_transition:
            has_transition_signal = True
        elif index == len(table.rows) - 1 and not has_pending_clarifications:
            errors.append(
                f"`{display_path(path)}` Clarification History row `{round_id}` records a user answer but no following clarification round or user stop signal; keep asking until the user explicitly stops"
            )
    if not has_transition_signal and not has_pending_clarifications:
        errors.append(
            f"`{display_path(path)}` Clarification History must record an explicit user stop signal before approval; the agent cannot decide the definition is clear enough"
        )


def has_meaningful_proposal_options(text: str) -> bool:
    lower = text.lower()
    if "options:" in lower:
        option_text = text[lower.find("options:") + len("options:") :]
    elif "선택지:" in text:
        option_text = text[text.find("선택지:") + len("선택지:") :]
    else:
        return False
    options = [item.strip().lower() for item in re.split(r"[,;/|]", option_text) if item.strip()]
    proposal_options = [item for item in options if item not in {"n/a", "none", "없음"}]
    return len(proposal_options) >= 2


def validate_implementation_plan_depth(path: Path, text: str, errors: list[str]) -> None:
    shallow_phrases = (
        "code and tests",
        "implement behavior",
        "implement the reviewed service behavior",
        "run tests",
        "target code, docs, tests, or assets",
    )
    for section in ("Technical Approach", "Implementation Architecture", "Edge Cases And Failure Modes", "Validation Strategy"):
        section_body = section_text(text, f"## {section}")
        if any(phrase in section_body.lower() for phrase in shallow_phrases):
            errors.append(f"`{display_path(path)}` `## {section}` is too generic for a technical implementation plan")

    work_items = parse_first_markdown_table(section_text(text, "## Work Items"))
    for row in work_items.rows:
        work_id = row.get("ID", "").strip() or "<unknown>"
        combined = " ".join(
            row.get(column, "")
            for column in ("Implementation Unit", "Technical Design", "Completion Evidence")
        ).lower()
        if any(phrase in combined for phrase in shallow_phrases):
            errors.append(f"`{display_path(path)}` Work Items row `{work_id}` is too generic for execution")


def uppercase_ids(pattern: re.Pattern[str], text: str) -> set[str]:
    return {match.group(0).upper() for match in pattern.finditer(text)}


def fullmatch_id(pattern: re.Pattern[str], value: str) -> bool:
    return bool(pattern.fullmatch(value.strip()))


def approved_definition_flow_rows(definition_text: str) -> dict[str, dict[str, str]]:
    table = parse_first_markdown_table(section_text(definition_text, "## Approved Flow Inventory"))
    rows: dict[str, dict[str, str]] = {}
    for row in table.rows:
        flow_id = row.get("Definition Flow ID", "").strip().upper()
        if flow_id:
            rows[flow_id] = row
    return rows


def validate_definition_approved_flow_inventory(path: Path, text: str, errors: list[str]) -> None:
    table = parse_first_markdown_table(section_text(text, "## Approved Flow Inventory"))
    if not table.rows:
        errors.append(f"`{display_path(path)}` Approved Flow Inventory must include at least one `DFLOW-*` row")
    valid_source_ids = traceable_scope_source_ids(text)
    covered_source_ids: set[str] = set()
    seen: set[str] = set()
    for row in table.rows:
        definition_flow_id = row.get("Definition Flow ID", "").strip().upper()
        display_id = definition_flow_id or "<unknown>"
        if not definition_flow_id:
            errors.append(f"`{display_path(path)}` Approved Flow Inventory row must include `Definition Flow ID`")
            continue
        if not fullmatch_id(DFLOW_ID_RE, definition_flow_id):
            errors.append(f"`{display_path(path)}` Approved Flow Inventory row `{display_id}` must use a `DFLOW-*` Definition Flow ID")
        if definition_flow_id in seen:
            errors.append(f"`{display_path(path)}` Approved Flow Inventory repeats Definition Flow ID `{definition_flow_id}`")
        seen.add(definition_flow_id)
        for column in (
            "Source IDs",
            "Trigger Or Entry",
            "Actor Or Consumer",
            "Target Outcome",
            "State/Data Responsibility",
            "Failure Or Empty Behavior",
        ):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(path)}` Approved Flow Inventory row `{display_id}` must include substantive `{column}`")
        source_ids = referenced_scope_source_ids(row.get("Source IDs", ""))
        covered_source_ids.update(source_ids)
        if not source_ids:
            errors.append(f"`{display_path(path)}` Approved Flow Inventory row `{display_id}` must cite traceable Source IDs")
        unknown_source_ids = sorted(source_ids - valid_source_ids)
        for source_id in unknown_source_ids:
            errors.append(f"`{display_path(path)}` Approved Flow Inventory row `{display_id}` cites unknown Source ID `{source_id}`")
        boundary_status = row.get("Boundary Status", "").strip()
        if boundary_status not in DEFINITION_FLOW_BOUNDARY_STATUSES:
            errors.append(
                f"`{display_path(path)}` Approved Flow Inventory row `{display_id}` Boundary Status must be one of "
                f"{', '.join(sorted(DEFINITION_FLOW_BOUNDARY_STATUSES))}"
            )

    for required_source_id in sorted(required_flow_source_ids(text) - covered_source_ids):
        errors.append(
            f"`{display_path(path)}` Approved Flow Inventory must include Source ID `{required_source_id}` "
            "in at least one `DFLOW-*` row"
        )


def normalized_cell(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).strip()


def is_placeholder_cell(value: str) -> bool:
    return normalized_cell(value).lower() in PLACEHOLDER_CELL_VALUES


def is_generic_flow_cell(value: str) -> bool:
    normalized = normalized_cell(value)
    if not normalized:
        return True
    return bool(FLOW_GENERIC_RE.fullmatch(normalized))


def validate_implementation_plan_flow_completeness(path: Path, text: str, errors: list[str]) -> None:
    work_items = parse_first_markdown_table(section_text(text, "## Work Items"))
    work_ids: set[str] = set()
    work_flow_refs: dict[str, set[str]] = {}
    for row in work_items.rows:
        work_id = row.get("ID", "").strip().upper()
        display_work_id = work_id or "<unknown>"
        if not work_id:
            errors.append(f"`{display_path(path)}` Work Items row must include `ID`")
            continue
        if not fullmatch_id(WORK_ID_RE, work_id):
            errors.append(f"`{display_path(path)}` Work Items row `{display_work_id}` must use a `WORK-*` ID")
        if work_id in work_ids:
            errors.append(f"`{display_path(path)}` Work Items repeats ID `{work_id}`")
        work_ids.add(work_id)
        combined = " ".join(row.get(column, "") for column in ("Technical Design", "Completion Evidence"))
        work_flow_refs[work_id] = uppercase_ids(FLOW_ID_RE, combined)

    flow_model = parse_first_markdown_table(section_text(text, "## Implementation Flow Model"))
    flow_matrix = parse_first_markdown_table(section_text(text, "## Flow Completeness Matrix"))
    if not flow_model.rows:
        errors.append(f"`{display_path(path)}` Implementation Flow Model must include at least one `FLOW-*` row")
    flow_ids: set[str] = set()
    complete_flow_ids: set[str] = set()
    flow_primary_work_ids: dict[str, set[str]] = {}

    for row in flow_model.rows:
        flow_id = row.get("Flow ID", "").strip().upper()
        display_flow_id = flow_id or "<unknown>"
        if not flow_id:
            errors.append(f"`{display_path(path)}` Implementation Flow Model row must include `Flow ID`")
            continue
        if not fullmatch_id(FLOW_ID_RE, flow_id):
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{display_flow_id}` must use a `FLOW-*` Flow ID")
        if flow_id in flow_ids:
            errors.append(f"`{display_path(path)}` Implementation Flow Model repeats Flow ID `{flow_id}`")
        flow_ids.add(flow_id)
        for column in ("Definition Flow ID", "Definition Source", "Trigger Or Entry", "Target Outcome", "Status Rationale"):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` must include substantive `{column}`")
        definition_flow_id = row.get("Definition Flow ID", "").strip().upper()
        if definition_flow_id and not fullmatch_id(DFLOW_ID_RE, definition_flow_id):
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` must use a `DFLOW-*` Definition Flow ID")
        status = row.get("Flow Status", "").strip()
        if status not in FLOW_STATUSES:
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` Flow Status must be one of {', '.join(sorted(FLOW_STATUSES))}"
            )
        if status == "return-to-definition":
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` is `return-to-definition`; "
                "resolve the definition gap before approval"
            )
        primary_work_ids = uppercase_ids(WORK_ID_RE, row.get("Primary Work Items", ""))
        flow_primary_work_ids[flow_id] = primary_work_ids
        unknown_primary_work_ids = sorted(primary_work_ids - work_ids)
        for work_id in unknown_primary_work_ids:
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` references unknown Primary Work Item `{work_id}`")
        if status == "complete":
            if not primary_work_ids:
                errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` complete flow must list at least one `WORK-*` Primary Work Item")
            complete_flow_ids.add(flow_id)

    matrix_rows_by_id: dict[str, dict[str, str]] = {}
    for row in flow_matrix.rows:
        flow_id = row.get("Flow ID", "").strip().upper()
        if not flow_id:
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix row must include `Flow ID`")
            continue
        if not fullmatch_id(FLOW_ID_RE, flow_id):
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix row `{flow_id}` must use a `FLOW-*` Flow ID")
        if flow_id in matrix_rows_by_id:
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix repeats Flow ID `{flow_id}`")
        matrix_rows_by_id[flow_id] = row
        if flow_ids and flow_id not in flow_ids:
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix row `{flow_id}` is not listed in Implementation Flow Model")

    for flow_id in sorted(complete_flow_ids):
        row = matrix_rows_by_id.get(flow_id)
        if row is None:
            errors.append(f"`{display_path(path)}` complete flow `{flow_id}` must have a Flow Completeness Matrix row")
            continue
        for column in (
            "Ordered Implementation Path",
            "State/Data Transitions",
            "Failure Or Empty States",
            "Observable Completion",
            "Validation Evidence",
        ):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(path)}` Flow Completeness Matrix row `{flow_id}` must include substantive `{column}`")
        if is_generic_flow_cell(row.get("Ordered Implementation Path", "")):
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix row `{flow_id}` Ordered Implementation Path is too generic for flow execution")
        if is_generic_flow_cell(row.get("Validation Evidence", "")):
            errors.append(f"`{display_path(path)}` Flow Completeness Matrix row `{flow_id}` Validation Evidence is too generic for flow completion")

    for work_id, referenced_flow_ids in work_flow_refs.items():
        unknown_flow_ids = sorted(referenced_flow_ids - flow_ids)
        for flow_id in unknown_flow_ids:
            errors.append(f"`{display_path(path)}` Work Items row `{work_id}` references unknown Flow ID `{flow_id}`")
        if flow_ids and not referenced_flow_ids.intersection(flow_ids):
            errors.append(f"`{display_path(path)}` Work Items row `{work_id}` must reference a Flow ID in Technical Design or Completion Evidence")

    for flow_id in sorted(complete_flow_ids):
        primary_work_ids = flow_primary_work_ids.get(flow_id, set())
        if not any(flow_id in work_flow_refs.get(work_id, set()) for work_id in primary_work_ids):
            errors.append(f"`{display_path(path)}` complete flow `{flow_id}` must be referenced by one of its Primary Work Items")

    for section, column in (
        ("## Coverage Matrix", "Work Item ID"),
        ("## Definition Fidelity Matrix", "Work Item ID"),
    ):
        table = parse_first_markdown_table(section_text(text, section))
        for row in table.rows:
            row_label = row.get(column, "").strip() or "<unknown>"
            referenced_work_ids = uppercase_ids(WORK_ID_RE, row.get(column, ""))
            if not referenced_work_ids:
                errors.append(f"`{display_path(path)}` {section} row `{row_label}` must reference at least one `WORK-*` ID")
                continue
            for work_id in sorted(referenced_work_ids - work_ids):
                errors.append(f"`{display_path(path)}` {section} row `{row_label}` references unknown Work Item ID `{work_id}`")


def traceable_scope_source_ids(text: str, *, narrowing_only: bool = False) -> set[str]:
    ids: set[str] = set()
    table_sources = (
        ("## Resolved Decisions", "ID"),
        ("## Requirements", "ID"),
        ("## Policy Rules", "Rule ID"),
        ("## Intent Fidelity", "ID"),
    )
    for section, column in table_sources:
        table = parse_first_markdown_table(section_text(text, section))
        for row in table.rows:
            value = row.get(column, "").strip()
            joined = " ".join(row.values()).lower()
            if "no resolved decision" in joined or "확정된 결정 없음" in joined:
                continue
            if TRACEABLE_SCOPE_SOURCE_RE.fullmatch(value):
                if narrowing_only and not contains_scope_narrowing_limit(" ".join(row.values())):
                    continue
                ids.add(value.upper())
    return ids


def source_ids_from_table(text: str, section: str, column: str, prefix: str) -> set[str]:
    ids: set[str] = set()
    pattern = re.compile(rf"{re.escape(prefix)}-\d+", re.IGNORECASE)
    table = parse_first_markdown_table(section_text(text, section))
    for row in table.rows:
        value = row.get(column, "").strip()
        if pattern.fullmatch(value):
            ids.add(value.upper())
    return ids


def required_flow_source_ids(text: str) -> set[str]:
    return source_ids_from_table(text, "## Requirements", "ID", "REQ") | source_ids_from_table(
        text,
        "## Policy Rules",
        "Rule ID",
        "SP",
    )


def referenced_scope_source_ids(text: str) -> set[str]:
    return {match.group(0).upper() for match in TRACEABLE_SCOPE_SOURCE_RE.finditer(text)}


def contains_scope_narrowing_limit(text: str) -> bool:
    return bool(SCOPE_NARROWING_LIMIT_RE.search(text))


def validate_definition_scope_narrowing_evidence(
    path: Path,
    text: str,
    errors: list[str],
    has_pending_clarifications: bool,
) -> None:
    if has_pending_clarifications:
        return
    source_ids = traceable_scope_source_ids(text)
    chunks: list[tuple[str, str, set[str]]] = [
        ("Boundaries", section_text(text, "## Boundaries"), set()),
    ]
    for section, id_column in (
        ("## Requirements", "ID"),
        ("## Policy Rules", "Rule ID"),
        ("## Resolved Decisions", "ID"),
        ("## Intent Fidelity", "ID"),
    ):
        table = parse_first_markdown_table(section_text(text, section))
        for row in table.rows:
            row_id = row.get(id_column, "").strip()
            local_ids = {row_id.upper()} if TRACEABLE_SCOPE_SOURCE_RE.fullmatch(row_id) else set()
            chunks.append((f"{section.removeprefix('## ')} row `{row_id or '<unknown>'}`", " ".join(row.values()), local_ids))

    for label, chunk_text, local_ids in chunks:
        if not chunk_text or not contains_scope_narrowing_limit(chunk_text):
            continue
        referenced_ids = referenced_scope_source_ids(chunk_text)
        if source_ids.intersection(referenced_ids) or source_ids.intersection(local_ids):
            continue
        errors.append(
            f"`{display_path(path)}` {label} records a scope narrowing or exclusion without a traceable source ID; "
            "cite one of `DEC-*`, `REQ-*`, `SP-*`, or `INTENT-*`, or keep the decision in Pending Clarifications/transition-risk before approval"
        )


def validate_implementation_plan_scope_narrowing_evidence(
    path: Path,
    text: str,
    definition_text: str,
    errors: list[str],
) -> None:
    valid_source_ids = traceable_scope_source_ids(definition_text, narrowing_only=True)
    table = parse_first_markdown_table(section_text(text, "## Definition Fidelity Matrix"))
    for row in table.rows:
        work_id = row.get("Work Item ID", "").strip() or "<unknown>"
        combined = " ".join(row.values())
        if not contains_scope_narrowing_limit(combined):
            continue
        definition_source_ids = referenced_scope_source_ids(row.get("Definition Source", ""))
        if valid_source_ids.intersection(definition_source_ids):
            continue
        errors.append(
            f"`{display_path(path)}` Definition Fidelity Matrix row `{work_id}` records a scope narrowing or exclusion without a valid definition source ID in `Definition Source`; "
            "cite an approved `DEC-*`, `REQ-*`, `SP-*`, or `INTENT-*` from the definition, or return to definition before narrowing the plan"
        )


def validate_implementation_plan_against_definition(
    context: ValidationContext,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    definition_path = context.request_dir / "01-definition" / "definition.md"
    definition_text = read_required_text(definition_path, errors)
    if definition_text is None:
        return
    validate_implementation_plan_scope_narrowing_evidence(
        artifact_path,
        artifact_text,
        definition_text,
        errors,
    )
    validate_implementation_plan_definition_flow_mapping(
        artifact_path,
        artifact_text,
        definition_text,
        errors,
    )


def validate_implementation_plan_definition_flow_mapping(
    path: Path,
    text: str,
    definition_text: str,
    errors: list[str],
) -> None:
    approved_flows = approved_definition_flow_rows(definition_text)
    if not approved_flows:
        return
    valid_source_ids = traceable_scope_source_ids(definition_text)
    flow_model = parse_first_markdown_table(section_text(text, "## Implementation Flow Model"))
    referenced_definition_flow_ids: set[str] = set()
    for row in flow_model.rows:
        flow_id = row.get("Flow ID", "").strip().upper() or "<unknown>"
        definition_flow_id = row.get("Definition Flow ID", "").strip().upper()
        if not definition_flow_id:
            continue
        referenced_definition_flow_ids.add(definition_flow_id)
        definition_flow_row = approved_flows.get(definition_flow_id)
        if definition_flow_row is None:
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` references unknown Definition Flow ID `{definition_flow_id}`")
            continue
        plan_source_ids = referenced_scope_source_ids(row.get("Definition Source", ""))
        if not plan_source_ids:
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` must cite traceable Definition Source IDs")
        for source_id in sorted(plan_source_ids - valid_source_ids):
            errors.append(f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` cites unknown Definition Source `{source_id}`")
        definition_source_ids = referenced_scope_source_ids(definition_flow_row.get("Source IDs", ""))
        if plan_source_ids and definition_source_ids and not plan_source_ids.intersection(definition_source_ids):
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` Definition Source must overlap "
                f"Definition Flow `{definition_flow_id}` Source IDs"
            )
        boundary_status = definition_flow_row.get("Boundary Status", "").strip()
        flow_status = row.get("Flow Status", "").strip()
        if boundary_status == "out-of-scope-by-definition" and flow_status != "out-of-scope-by-definition":
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` must use `out-of-scope-by-definition` "
                f"because `{definition_flow_id}` is out of scope by definition"
            )
        if boundary_status == "external-boundary-by-definition" and flow_status != "external-boundary-by-definition":
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` must use `external-boundary-by-definition` "
                f"because `{definition_flow_id}` is an external boundary by definition"
            )
        if boundary_status == "in-scope" and flow_status in {"out-of-scope-by-definition", "external-boundary-by-definition"}:
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` cannot mark in-scope Definition Flow "
                f"`{definition_flow_id}` as `{flow_status}`"
            )
        if flow_status in {"out-of-scope-by-definition", "external-boundary-by-definition"}:
            rationale_ids = referenced_scope_source_ids(" ".join((row.get("Definition Source", ""), row.get("Status Rationale", ""))))
            if definition_source_ids and not rationale_ids.intersection(definition_source_ids):
                errors.append(
                    f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` non-complete rationale must cite "
                    f"Definition Flow `{definition_flow_id}` source support"
                )
        if flow_status == "external-boundary-by-definition" and not EXTERNAL_BOUNDARY_RATIONALE_RE.search(row.get("Status Rationale", "")):
            errors.append(
                f"`{display_path(path)}` Implementation Flow Model row `{flow_id}` external-boundary rationale must record "
                "the observable repo boundary and consumer responsibility"
            )

    for definition_flow_id in sorted(set(approved_flows) - referenced_definition_flow_ids):
        errors.append(f"`{display_path(path)}` Implementation Flow Model must include approved Definition Flow `{definition_flow_id}`")


def validate_implementation_against_plan(
    context: ValidationContext,
    artifact_path: Path,
    artifact_text: str,
    errors: list[str],
) -> None:
    plan_path = context.request_dir / "02-implementation-plan" / "implementation-plan.md"
    plan_text = read_required_text(plan_path, errors)
    if plan_text is None:
        return
    plan_work_items = parse_first_markdown_table(section_text(plan_text, "## Work Items"))
    approved_work_items: dict[str, dict[str, str]] = {}
    for row in plan_work_items.rows:
        work_id = row.get("ID", "").strip().upper()
        if work_id:
            approved_work_items[work_id] = row

    complete_flows: dict[str, dict[str, str]] = {}
    plan_flow_ids: set[str] = set()
    plan_flow_model = parse_first_markdown_table(section_text(plan_text, "## Implementation Flow Model"))
    for row in plan_flow_model.rows:
        flow_id = row.get("Flow ID", "").strip().upper()
        if flow_id:
            plan_flow_ids.add(flow_id)
        if flow_id and row.get("Flow Status", "").strip() == "complete":
            complete_flows[flow_id] = row

    work_evidence_table = parse_first_markdown_table(section_text(artifact_text, "## Work Item Completion Evidence"))
    work_evidence_by_id: dict[str, dict[str, str]] = {}
    for row in work_evidence_table.rows:
        work_id = row.get("Work Item ID", "").strip().upper()
        if not work_id:
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row must include `Work Item ID`")
            continue
        if not fullmatch_id(WORK_ID_RE, work_id):
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` must use a `WORK-*` Work Item ID")
        if work_id in work_evidence_by_id:
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence repeats Work Item ID `{work_id}`")
        work_evidence_by_id[work_id] = row
        if approved_work_items and work_id not in approved_work_items:
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` is not in the approved implementation plan")
        for column in ("Planned Unit", "Actual Change", "Validation Evidence", "Linked Flow IDs"):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` must include substantive `{column}`")
        linked_flow_ids = uppercase_ids(FLOW_ID_RE, row.get("Linked Flow IDs", ""))
        if not linked_flow_ids:
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` must link at least one `FLOW-*`")
        for flow_id in sorted(linked_flow_ids - plan_flow_ids):
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` references unknown Flow ID `{flow_id}`")
        status = row.get("Status", "").strip().lower()
        if status not in WORK_COMPLETION_STATUSES:
            errors.append(f"`{display_path(artifact_path)}` Work Item Completion Evidence row `{work_id}` Status must be completed")

    for work_id in sorted(approved_work_items):
        if work_id not in work_evidence_by_id:
            errors.append(f"`{display_path(artifact_path)}` approved work item `{work_id}` must have Work Item Completion Evidence with Status `completed`")

    evidence_table = parse_first_markdown_table(section_text(artifact_text, "## Flow Completion Evidence"))
    evidence_by_flow: dict[str, dict[str, str]] = {}
    for row in evidence_table.rows:
        flow_id = row.get("Flow ID", "").strip().upper()
        if not flow_id:
            errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence row must include `Flow ID`")
            continue
        if not fullmatch_id(FLOW_ID_RE, flow_id):
            errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence row `{flow_id}` must use a `FLOW-*` Flow ID")
        if flow_id in evidence_by_flow:
            errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence repeats Flow ID `{flow_id}`")
        evidence_by_flow[flow_id] = row
        if complete_flows and flow_id not in complete_flows:
            errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence row `{flow_id}` is not a complete flow in the approved implementation plan")

    for flow_id, plan_row in sorted(complete_flows.items()):
        evidence_row = evidence_by_flow.get(flow_id)
        if evidence_row is None:
            errors.append(f"`{display_path(artifact_path)}` complete flow `{flow_id}` must have Flow Completion Evidence")
            continue
        expected_definition_flow_id = plan_row.get("Definition Flow ID", "").strip().upper()
        actual_definition_flow_id = evidence_row.get("Definition Flow ID", "").strip().upper()
        if actual_definition_flow_id != expected_definition_flow_id:
            errors.append(
                f"`{display_path(artifact_path)}` Flow Completion Evidence row `{flow_id}` Definition Flow ID must be `{expected_definition_flow_id}`"
            )
        for column in (
            "Planned Outcome",
            "Actual Result",
            "Validation Evidence",
            "Observable Completion",
        ):
            if is_placeholder_cell(evidence_row.get(column, "")):
                errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence row `{flow_id}` must include substantive `{column}`")
        status = evidence_row.get("Status", "").strip().lower()
        if status not in FLOW_COMPLETION_STATUSES:
            errors.append(f"`{display_path(artifact_path)}` Flow Completion Evidence row `{flow_id}` Status must be completed")


def validate_table_columns(path: Path, text: str, requirement: TableRequirement, errors: list[str]) -> None:
    parse_required_table(
        path,
        section_text(text, f"## {requirement.section}"),
        requirement.columns,
        f"## {requirement.section}",
        errors,
    )


def transition_risk_file_present(stage_dir: Path) -> bool:
    return (stage_dir / "transition-risk.md").is_file() or (stage_dir / "transition-risk-goal.md").is_file()


def validate_transition_risk_goal(path: Path, definition_fingerprint: str, errors: list[str]) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Transition Risk Goal" not in text and "# Goal" not in text:
        errors.append(f"`{display_path(path)}` must include `# Transition Risk Goal` or `# Goal`")
    if label_value(text, "Stage") != "definition":
        errors.append(f"`{display_path(path)}` must record `Stage: definition`")
    if label_value(text, "Purpose") != "transition-risk":
        errors.append(f"`{display_path(path)}` must record `Purpose: transition-risk`")
    artifact_path = label_value(text, "Artifact Path").strip("`")
    if artifact_path != "01-definition/transition-risk.md":
        errors.append(f"`{display_path(path)}` must record `Artifact Path: 01-definition/transition-risk.md`")
    if "Tool: create_goal" not in text:
        errors.append(f"`{display_path(path)}` Goal Invocation must record `Tool: create_goal`")
    if "Invocation recorded: yes" not in text:
        errors.append(f"`{display_path(path)}` Goal Invocation must record `Invocation recorded: yes`")
    if "Goal created: yes" not in text:
        errors.append(f"`{display_path(path)}` Goal Tool Status must record `Goal created: yes`")
    if label_value(text, "Goal status").lower() != "completed":
        errors.append(f"`{display_path(path)}` must record `Goal status: completed`")
    validate_fingerprint(path, text, "Definition Artifact Fingerprint", definition_fingerprint, errors)


def reflected_definition_sections(text: str) -> str:
    sections = (
        "## Requirements",
        "## Acceptance Criteria",
        "## Policy Rules",
        "## Boundaries",
        "## Failure And Recovery Behavior",
        "## Regression Prevention",
    )
    return "\n".join(section_text(text, section) for section in sections)


def validate_transition_risk_file(path: Path, definition_text: str, has_pending_clarifications: bool, errors: list[str]) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Transition Risk" not in text:
        errors.append(f"`{display_path(path)}` must include `# Transition Risk`")
    for section in (
        "## Risk Generation Basis",
        "## Generated Risk Cases",
        "## Suggested Definition Updates",
        "## User Confirmation",
        "## Final Disposition",
    ):
        if not section_text(text, section).strip():
            errors.append(f"`{display_path(path)}` must include non-empty `{section}`")

    table = parse_required_table(
        path,
        section_text(text, "## Generated Risk Cases"),
        ("ID", "Category", "Risk Case", "Affected Definition Area", "Definition Coverage", "Prior Answer Check", "Suggested Handling", "User Confirmation", "Disposition"),
        "## Generated Risk Cases",
        errors,
    )
    reflected = reflected_definition_sections(definition_text).lower()
    for row in table.rows:
        risk_id = row.get("ID", "").strip() or "<unknown>"
        category = row.get("Category", "").strip()
        risk_case = row.get("Risk Case", "").strip()
        coverage = row.get("Definition Coverage", "").strip()
        prior_answer_check = row.get("Prior Answer Check", "").strip()
        suggested = row.get("Suggested Handling", "").strip()
        confirmation = row.get("User Confirmation", "").strip()
        disposition = row.get("Disposition", "").strip()
        is_no_material = "no material transition risks found" in risk_case.lower()
        combined_row_text = " ".join((risk_case, coverage, prior_answer_check, suggested, confirmation, disposition))
        if category not in TRANSITION_RISK_CATEGORIES:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Category is not allowed")
        if coverage not in TRANSITION_RISK_COVERAGE:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Definition Coverage must be one of uncovered, conflicting, ambiguous, or not-applicable")
        if prior_answer_check not in TRANSITION_RISK_PRIOR_ANSWER_CHECKS:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Prior Answer Check must be one of not-answered, answered-not-reflected, answered-conflicting, or not-applicable")
        if ALREADY_DECIDED_RISK_RE.search(combined_row_text):
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` records already-decided or already answered/reflected definition content as a risk; move confirmed decisions to implementation-plan constraints or coverage instead")
        if not is_no_material and coverage == "not-applicable":
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` must use Definition Coverage `uncovered`, `conflicting`, or `ambiguous` for material risks")
        if not is_no_material and prior_answer_check == "not-applicable":
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` must use Prior Answer Check `not-answered`, `answered-not-reflected`, or `answered-conflicting` for material risks")
        if is_no_material and coverage != "not-applicable":
            errors.append(f"`{display_path(path)}` no-material risk row `{risk_id}` must use Definition Coverage `not-applicable`")
        if is_no_material and prior_answer_check != "not-applicable":
            errors.append(f"`{display_path(path)}` no-material risk row `{risk_id}` must use Prior Answer Check `not-applicable`")
        if prior_answer_check in {"answered-not-reflected", "answered-conflicting"} and disposition not in {"apply-to-definition", "ask-follow-up"}:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` is based on an existing user answer, so it must be resolved by `apply-to-definition` or `ask-follow-up`, not parked as a risk")
        if not is_no_material and len(labeled_proposal_options(suggested)) < 2:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Suggested Handling must explain at least two labeled resolution options such as `Option 1:` and `Option 2:`")
        if not confirmation or confirmation.lower() in {"n/a", "none", "pending", "unconfirmed"}:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` must record User Confirmation")
        if disposition not in TRANSITION_RISK_DISPOSITIONS:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Disposition is not allowed")
        if disposition == "accepted-risk" and not ACCEPTED_RISK_CONFIRMATION_RE.search(confirmation):
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` uses accepted-risk without explicit user risk acceptance")
        if disposition == "ask-follow-up" and not has_pending_clarifications:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` asks follow-up, so definition must have active Pending Clarifications")
        if disposition == "apply-to-definition" and risk_id.lower() not in reflected and "transition-risk" not in reflected:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` is apply-to-definition but reflected definition evidence is missing")
        if is_no_material and disposition != "not-applicable":
            errors.append(f"`{display_path(path)}` no-material risk row `{risk_id}` must use Disposition `not-applicable`")


def validate_transition_risk_gate(stage_dir: Path, artifact_text: str, artifact_fingerprint: str, errors: list[str], has_pending_clarifications: bool) -> None:
    stop_signal = has_user_stop_signal(artifact_text)
    if not stop_signal and not transition_risk_file_present(stage_dir):
        return
    if stop_signal and not has_pending_clarifications:
        validate_transition_risk_goal(stage_dir / "transition-risk-goal.md", artifact_fingerprint, errors)
        validate_transition_risk_file(stage_dir / "transition-risk.md", artifact_text, has_pending_clarifications, errors)
    elif transition_risk_file_present(stage_dir):
        validate_transition_risk_goal(stage_dir / "transition-risk-goal.md", artifact_fingerprint, errors)
        validate_transition_risk_file(stage_dir / "transition-risk.md", artifact_text, has_pending_clarifications, errors)


def validate_goal(
    stage: Stage,
    path: Path,
    artifact_fingerprint: str | None,
    errors: list[str],
    has_pending_clarifications: bool = False,
) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Goal" not in text:
        errors.append(f"`{display_path(path)}` must include `# Goal`")
    if label_value(text, "Stage") != stage.phase:
        errors.append(f"`{display_path(path)}` must record `Stage: {stage.phase}`")
    if "Tool: create_goal" not in text:
        errors.append(f"`{display_path(path)}` Goal Invocation must record `Tool: create_goal`")
    if "Invocation recorded: yes" not in text:
        errors.append(f"`{display_path(path)}` Goal Invocation must record `Invocation recorded: yes`")
    if "Goal created: yes" not in text:
        errors.append(f"`{display_path(path)}` Goal Tool Status must record `Goal created: yes`")
    status = label_value(text, "Goal status").lower()
    if has_pending_clarifications:
        reason = label_value(text, "Goal completion reason").lower()
        if status not in AWAITING_USER_GOAL_STATUSES:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications require `Goal status: completed` before AWAITING_USER; close the Codex goal after showing the pending questions"
            )
        if AWAITING_USER_GOAL_REASON not in reason:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications require `Goal completion reason: awaiting user clarification`"
            )
    elif status in {"", "pending", "blocked", "failed", "no"}:
        errors.append(f"`{display_path(path)}` Goal Tool Status must record an active or completed goal status")
    validate_fingerprint(path, text, "Artifact Fingerprint", artifact_fingerprint, errors)


def validate_review(
    context: ValidationContext,
    stage: Stage,
    path: Path,
    artifact_fingerprint: str | None,
    rule_ids: list[str],
    errors: list[str],
) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Review" not in text:
        errors.append(f"`{display_path(path)}` must include `# Review`")
    if label_value(text, "Stage") != stage.phase:
        errors.append(f"`{display_path(path)}` must record `Stage: {stage.phase}`")
    method = section_text(text, "## Review Method")
    if "Subagent review." not in method:
        errors.append(f"`{display_path(path)}` review method must be `Subagent review.`")
    if "self-review" in method.lower():
        errors.append(f"`{display_path(path)}` self-review does not satisfy the review gate")
    if not PASS_RE.search(section_text(text, "## Latest Verdict")):
        errors.append(f"`{display_path(path)}` Latest Verdict must be PASS")
    if not NO_BLOCKING_RE.search(section_text(text, "## Blocking Issues")):
        errors.append(f"`{display_path(path)}` Blocking Issues must record no blocking issues")
    if not NO_BLOCKING_RE.search(section_text(text, "## Final Verdict")):
        errors.append(f"`{display_path(path)}` Final Verdict must confirm no blocking issues")
    if not section_text(text, "## Review Cycle").strip():
        errors.append(f"`{display_path(path)}` must include `## Review Cycle` history")
    validate_subagent_review_shards(context, stage, path, text, artifact_fingerprint, errors)
    validate_rule_checklist(path, text, rule_ids, errors)
    validate_fingerprint(path, text, "Reviewed Artifact Fingerprint", artifact_fingerprint, errors)


def validate_subagent_review_shards(
    context: ValidationContext,
    stage: Stage,
    final_path: Path,
    final_text: str,
    artifact_fingerprint: str | None,
    errors: list[str],
) -> None:
    table = parse_required_table(
        final_path,
        section_text(final_text, "## Subagent Review Shards"),
        ("Shard File", "Scope", "Verdict", "Blocking Issue"),
        "## Subagent Review Shards",
        errors,
    )
    stage_dir = final_path.parent.parent
    has_flow_completeness_shard = False
    for row in table.rows:
        shard_file = row.get("Shard File", "").strip().strip("`")
        scope = row.get("Scope", "").strip().lower()
        if stage.phase == "implementation-plan" and scope == "flow-completeness":
            has_flow_completeness_shard = True
        if not shard_file:
            errors.append(f"`{display_path(final_path)}` Subagent Review Shards row must include `Shard File`")
            continue
        if not shard_file.startswith("review/subagents/"):
            errors.append(f"`{display_path(final_path)}` shard file `{shard_file}` must be under `review/subagents/`")
            continue
        if row.get("Verdict", "").strip().upper() != "PASS":
            errors.append(f"`{display_path(final_path)}` shard `{shard_file}` verdict must be PASS")
        if not NO_BLOCKING_RE.search(row.get("Blocking Issue", "")):
            errors.append(f"`{display_path(final_path)}` shard `{shard_file}` must record no blocking issue")
        shard_path = stage_dir / shard_file
        validate_subagent_review_shard(context, stage, shard_path, artifact_fingerprint, errors, scope)
    if stage.phase == "implementation-plan" and not has_flow_completeness_shard:
        errors.append(f"`{display_path(final_path)}` implementation-plan review must include a `flow-completeness` subagent shard")


def validate_subagent_review_shard(
    context: ValidationContext,
    stage: Stage,
    path: Path,
    artifact_fingerprint: str | None,
    errors: list[str],
    expected_scope: str = "",
) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Subagent Review Shard" not in text:
        errors.append(f"`{display_path(path)}` must include `# Subagent Review Shard`")
    if label_value(text, "Stage") != stage.phase:
        errors.append(f"`{display_path(path)}` must record `Stage: {stage.phase}`")
    shard_scope = label_value(text, "Shard Scope")
    if not shard_scope:
        errors.append(f"`{display_path(path)}` must record `Shard Scope`")
    elif expected_scope and shard_scope.strip().lower() != expected_scope:
        errors.append(f"`{display_path(path)}` Shard Scope must match final review scope `{expected_scope}`")
    if not section_text(text, "## Inputs Read").strip():
        errors.append(f"`{display_path(path)}` must include non-empty `## Inputs Read`")
    if not PASS_RE.search(section_text(text, "## Verdict")):
        errors.append(f"`{display_path(path)}` Verdict must be PASS")
    if not NO_BLOCKING_RE.search(section_text(text, "## Blocking Issues")):
        errors.append(f"`{display_path(path)}` Blocking Issues must record no blocking issues")
    if stage.phase == "implementation-plan" and expected_scope == "flow-completeness":
        validate_flow_completeness_shard(context, path, text, errors)
    validate_fingerprint(path, text, "Reviewed Artifact Fingerprint", artifact_fingerprint, errors)


def validate_flow_completeness_shard(
    context: ValidationContext,
    path: Path,
    text: str,
    errors: list[str],
) -> None:
    checklist = parse_required_table(
        path,
        section_text(text, "## Flow Rule Checklist"),
        ("Rule ID", "Evidence", "Verdict", "Blocking Issue"),
        "## Flow Rule Checklist",
        errors,
    )
    rows_by_id = {row.get("Rule ID", "").strip(): row for row in checklist.rows if row.get("Rule ID", "").strip()}
    for index in range(1, 8):
        rule_id = f"IP-FLOW-{index:03d}"
        row = rows_by_id.get(rule_id)
        if row is None:
            errors.append(f"`{display_path(path)}` Flow Rule Checklist must include Rule ID `{rule_id}`")
            continue
        if row.get("Verdict", "").strip().upper() != "PASS":
            errors.append(f"`{display_path(path)}` Flow Rule Checklist Rule ID `{rule_id}` verdict must be PASS")
        if not NO_BLOCKING_RE.search(row.get("Blocking Issue", "")):
            errors.append(f"`{display_path(path)}` Flow Rule Checklist Rule ID `{rule_id}` must record no blocking issue")
        if is_placeholder_cell(row.get("Evidence", "")):
            errors.append(f"`{display_path(path)}` Flow Rule Checklist Rule ID `{rule_id}` must include evidence")

    audit = parse_required_table(
        path,
        section_text(text, "## Flow Coverage Audit"),
        ("Flow ID", "Definition Sources Checked", "IP-FLOW-001..007 Verdict", "Gap", "Decision"),
        "## Flow Coverage Audit",
        errors,
    )
    if not audit.rows:
        errors.append(f"`{display_path(path)}` Flow Coverage Audit must include at least one row")

    definition_text = read_required_text(context.request_dir / "01-definition" / "definition.md", errors)
    plan_text = read_required_text(context.request_dir / "02-implementation-plan" / "implementation-plan.md", errors)
    approved_definition_flows = approved_definition_flow_rows(definition_text) if definition_text is not None else {}
    plan_flow_model = parse_first_markdown_table(section_text(plan_text or "", "## Implementation Flow Model"))
    plan_flow_ids = {
        row.get("Flow ID", "").strip().upper()
        for row in plan_flow_model.rows
        if row.get("Flow ID", "").strip()
    }
    audited_definition_flow_ids: set[str] = set()
    audited_plan_flow_ids: set[str] = set()

    for row in audit.rows:
        flow_id = row.get("Flow ID", "").strip() or "<unknown>"
        for column in ("Flow ID", "Definition Sources Checked", "IP-FLOW-001..007 Verdict", "Gap", "Decision"):
            if is_placeholder_cell(row.get(column, "")):
                errors.append(f"`{display_path(path)}` Flow Coverage Audit row `{flow_id}` must include substantive `{column}`")
        row_definition_flow_ids = uppercase_ids(DFLOW_ID_RE, flow_id)
        row_plan_flow_ids = uppercase_ids(FLOW_ID_RE, flow_id)
        if not row_definition_flow_ids or not row_plan_flow_ids:
            errors.append(f"`{display_path(path)}` Flow Coverage Audit row `{flow_id}` must include a `DFLOW-* -> FLOW-*` mapping")
        for definition_flow_id in sorted(row_definition_flow_ids):
            if approved_definition_flows and definition_flow_id not in approved_definition_flows:
                errors.append(f"`{display_path(path)}` Flow Coverage Audit row `{flow_id}` references unknown Definition Flow ID `{definition_flow_id}`")
            audited_definition_flow_ids.add(definition_flow_id)
        for plan_flow_id in sorted(row_plan_flow_ids):
            if plan_flow_ids and plan_flow_id not in plan_flow_ids:
                errors.append(f"`{display_path(path)}` Flow Coverage Audit row `{flow_id}` references unknown Flow ID `{plan_flow_id}`")
            audited_plan_flow_ids.add(plan_flow_id)

    for definition_flow_id in sorted(set(approved_definition_flows) - audited_definition_flow_ids):
        errors.append(f"`{display_path(path)}` Flow Coverage Audit must include approved Definition Flow `{definition_flow_id}`")
    for plan_flow_id in sorted(plan_flow_ids - audited_plan_flow_ids):
        errors.append(f"`{display_path(path)}` Flow Coverage Audit must include plan Flow `{plan_flow_id}`")


def validate_rule_checklist(path: Path, text: str, rule_ids: list[str], errors: list[str]) -> None:
    table = parse_required_table(
        path,
        section_text(text, "## Writing And Review Rule Checklist"),
        ("Rule ID", "Evidence Read", "Verdict", "Blocking Issue"),
        "## Writing And Review Rule Checklist",
        errors,
    )
    rows_by_id = {row.get("Rule ID", "").strip(): row for row in table.rows if row.get("Rule ID", "").strip()}
    for rule_id in rule_ids:
        row = rows_by_id.get(rule_id)
        if row is None:
            errors.append(f"`{display_path(path)}` Writing And Review Rule Checklist must include Rule ID `{rule_id}`")
            continue
        if row.get("Verdict", "").strip().upper() != "PASS":
            errors.append(f"`{display_path(path)}` Rule ID `{rule_id}` checklist verdict must be PASS")
        if not NO_BLOCKING_RE.search(row.get("Blocking Issue", "")):
            errors.append(f"`{display_path(path)}` Rule ID `{rule_id}` checklist must record no blocking issue")


def validate_approval(stage: Stage, path: Path, errors: list[str]) -> None:
    text = read_required_text(path, errors)
    if text is None:
        return
    if "# Approval" not in text:
        errors.append(f"`{display_path(path)}` must include `# Approval`")
    if label_value(text, "Stage") != stage.phase:
        errors.append(f"`{display_path(path)}` must record `Stage: {stage.phase}`")
    if "Stage approved: yes" not in text:
        errors.append(f"`{display_path(path)}` must record `Stage approved: yes`")
    if not label_value(text, "Approved By"):
        errors.append(f"`{display_path(path)}` must record `Approved By`")
    if not label_value(text, "Approved At"):
        errors.append(f"`{display_path(path)}` must record `Approved At`")
    approval_text = section_text(text, "## Approval Text")
    if NEGATIVE_APPROVAL_RE.search(approval_text) or not APPROVAL_RE.search(approval_text):
        errors.append(f"`{display_path(path)}` Approval Text must contain explicit positive approval")


def validate_fingerprint(
    path: Path,
    text: str,
    label: str,
    expected: str | None,
    errors: list[str],
) -> None:
    if expected is None:
        return
    value = label_value(text, label)
    match = FINGERPRINT_RE.search(value)
    if not match:
        errors.append(f"`{display_path(path)}` must record `{label}: sha256:<artifact-fingerprint>`")
        return
    if match.group(1).lower() != expected.lower():
        errors.append(f"`{display_path(path)}` {label} does not match the current artifact")


def label_value(text: str, label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    next_heading = re.search(r"^#{1,6}\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def fenced_code_block_after_heading(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    fence_start = text.find("```", start + len(heading))
    if fence_start == -1:
        return ""
    content_start = text.find("\n", fence_start)
    if content_start == -1:
        return ""
    fence_end = text.find("```", content_start + 1)
    if fence_end == -1:
        return text[content_start + 1 :].strip()
    return text[content_start + 1 : fence_end].strip()


def parse_required_table(
    path: Path,
    section: str,
    required_columns: tuple[str, ...],
    section_name: str,
    errors: list[str],
) -> MarkdownTable:
    table = parse_first_markdown_table(section)
    if not table.headers:
        errors.append(f"`{display_path(path)}` {section_name} must include a markdown table")
        return table
    for column in required_columns:
        if column not in table.headers:
            errors.append(f"`{display_path(path)}` {section_name} table must include column `{column}`")
    if not table.rows:
        errors.append(f"`{display_path(path)}` {section_name} table must include at least one data row")
    return table


def parse_first_markdown_table(text: str) -> MarkdownTable:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        headers = parse_table_row(line)
        if not headers:
            continue
        data_start = index + 1
        if data_start < len(lines) and is_separator_row(parse_table_row(lines[data_start])):
            data_start += 1
        rows: list[dict[str, str]] = []
        for row_line in lines[data_start:]:
            if not row_line.startswith("|"):
                break
            cells = parse_table_row(row_line)
            if not cells or is_separator_row(cells):
                continue
            rows.append({header: cells[pos] if pos < len(cells) else "" for pos, header in enumerate(headers)})
        return MarkdownTable(headers, rows)
    return MarkdownTable([], [])


def parse_table_row(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|"):
        return []
    if line.endswith("|"):
        line = line[1:-1]
    else:
        line = line[1:]
    return [cell.strip() for cell in line.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(cell and set(cell) <= {"-", ":", " "} for cell in cells)


def render_stage_tree() -> str:
    rows: list[str] = []
    for stage in STAGES:
        parts = []
        if stage.phase == "definition":
            parts.extend([
                f"`{stage.folder}/{stage.artifact}`",
                f"`{stage.folder}/definition-store/working-set.json`",
                f"`{stage.folder}/definition-store/decision-ledger.jsonl`",
                f"`{stage.folder}/definition-store/trace-index.json`",
                f"`{stage.folder}/definition-store/sync-state.json`",
                f"`{stage.folder}/question-scope-transition-review.md` (before lower-scope pending questions)",
                f"`{stage.folder}/transition-risk-goal.md` (after stop signal)",
                f"`{stage.folder}/transition-risk.md` (after stop signal)",
            ])
        else:
            parts.append(f"`{stage.folder}/goal.md`")
            parts.append(f"`{stage.folder}/{stage.artifact}`")
        parts.extend([
            f"`{stage.folder}/review/final.md`",
            f"`{stage.folder}/review/subagents/001-full-bounded-review.md`",
        ])
        if stage.phase == "implementation-plan":
            parts.append(f"`{stage.folder}/review/subagents/002-flow-completeness-review.md`")
        parts.append(f"`{stage.folder}/approval.md`")
        rows.append("- " + ", ".join(parts))
    return "\n".join(rows)


VALIDATOR_TEMPLATES: dict[str, str] = {
    "index": """{
  "version": "1",
  "requests": [
    {
      "id": "20260621-1200-three-stage-workflow",
      "title": "Three stage workflow",
      "status": "definition",
      "created_at": "2026-06-21T03:00:00Z",
      "updated_at": "2026-06-21T03:00:00Z"
    }
  ]
}
""",
    "current": """{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "activated_by": "explicit_skill_invocation"
}
""",
    "state": """{
  "request_id": "20260621-1200-three-stage-workflow",
  "phase": "definition",
  "last_validated_at": null
}
""",
    "goal": """# Goal

Stage: implementation-plan

Artifact Path: `02-implementation-plan/implementation-plan.md`

Artifact Fingerprint: sha256:<artifact-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Advance this stage artifact to the next required user input or approval gate. If pending clarifications are presented, stop at user-answer waiting instead of continuing review or next-stage work.

## Goal Tool Status

Goal created: yes

Goal status: active
""",
    "definition": """# Definition

## User Goal

사용자의 목표를 사용자가 말한 언어로 요약한다.

## Purpose And Intent

| Purpose | User Value | Business/Product Value | Source | Confidence |
| --- | --- | --- | --- | --- |
| 아직 목적은 사용자 확인이 필요하다. | 사용자에게 이 결과가 왜 필요한지 확인한다. | 구현 계획 전에 제품 또는 workflow 가치를 확인한다. | user request needs clarification | unknown |

## Request Profile

Primary: feature
Secondary: none

## Desired Outcomes

| ID | Outcome | Source | Success Signal |
| --- | --- | --- | --- |
| OUT-001 | 요청한 결과가 화면, 산출물, 검증 절차 중 하나로 확인된다. | 사용자 요청. | 리뷰어가 결과 충족 여부를 확인할 수 있다. |

## Current Problems

| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |
| --- | --- | --- | --- | --- | --- |
| PROB-001 | 현재 확인된 문제 없음. | N/A | N/A | N/A | N/A |

## Problem-To-Requirement Mapping

| Problem ID | Requirement ID | Resolution |
| --- | --- | --- |
| PROB-001 | REQ-001 | 요구사항이 해당 문제를 해결하거나 재발을 막는다. |

## User-Specified Constraints

- 명시된 제약 없음.

## Discovered Constraints

- 발견된 제약 없음.

## Pending Clarifications

| ID | Question Scope | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PENDING-001 | 큰방향 | 현재 목적은 아직 확인되지 않았습니다. 이 변경이 우선 달성해야 할 목적은 무엇인가요? | Option 1: 사용자가 제기한 즉시 workflow 문제를 해결한다; Option 2: 후속 변경에 대비한 재사용 가능한 제품 유연성을 만든다 | Option 1 | N/A | 이 답변은 `Purpose And Intent`와 `Desired Outcomes`에 반영되어 이후 범위와 검증 기준의 기준점이 됩니다. | pending |
| PENDING-002 | 큰방향 | 현재 요청 범위가 핵심 변경에만 머물지, 인접 동작까지 포함할지 열려 있습니다. 상위 범위는 어디까지로 잡을까요? | Option 1: 직접 요청된 동작으로 범위를 좁힌다; Option 2: 나중에 영향을 받을 인접 동작까지 포함한다 | Option 1 | N/A | 이 답변은 `Requirements`와 `Boundaries`에 반영되어 구현 계획이 불필요한 인접 동작까지 포함하지 않도록 합니다. | pending |
| PENDING-003 | 큰방향 | 현재 영향 대상이 사용자 화면/경험인지 내부 workflow인지 아직 확정되지 않았습니다. 주된 적용 표면은 무엇인가요? | Option 1: 사용자-facing 동작; Option 2: 내부 workflow 동작; Option 3: 둘 다 | Option 1 | N/A | 이 답변은 `User Flow`, `Normal Behavior Model`, `Policy Rules`에 반영되어 이후 동작 질문의 기준을 정합니다. | pending |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-000 | 완료된 clarification이 아직 없다. | N/A | no | N/A | N/A |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 열린 질문 없음. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | 확정된 결정 없음. | N/A |

## Intent Fidelity

| ID | User Wording | Normalized Requirement | Allowed Interpretations | Disallowed Interpretations | Linked Requirement/Policy |
| --- | --- | --- | --- | --- | --- |
| INTENT-001 | 사용자의 원문 또는 의미를 보존한 요약. | 사용자 표현에서 요구사항 의미를 보존한다. | 사용자 답변이나 resolved decision이 명시적으로 뒷받침한 해석. | 승인되지 않은 더 좁거나 넓거나 기술적인 해석. | REQ-001, SP-001 |

## Requirements

| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | feature | 사용자 요청. | 검증 가능한 요구사항 한 가지를 기록한다. | 제외되는 동작을 명시한다. | OUT-001 |

## Acceptance Criteria

- `REQ-001`은 `OUT-001`을 검증할 수 있을 때 충족된다.

## Normal Behavior Model

수정되거나 원하는 서비스 동작을 구조화된 모델로 설명한다.

## User Flow

사용자 또는 시스템이 무엇을 하고, 보고, 받는지 순서대로 설명한다.

## State And Policy Model

상태, 전이, 권한, 검증 규칙, 제품 정책을 설명한다.

## Approved Flow Inventory

| Definition Flow ID | Source IDs | Trigger Or Entry | Actor Or Consumer | Target Outcome | State/Data Responsibility | Failure Or Empty Behavior | Boundary Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DFLOW-001 | REQ-001, SP-001, INTENT-001 | 승인된 flow를 시작하는 사용자 또는 시스템 진입점. | 사용자, 관리자, 시스템 consumer 중 해당 주체. | 사용자가 보거나 시스템 consumer가 확인하는 완료 결과. | 생성, 수정, 조회, 캐시 갱신, no-op, 외부 책임 등 service-level 책임. | 검증 실패, 빈 상태, 권한 실패, 외부 consumer 책임 등 flow별 실패/빈 상태. | in-scope |

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | 관련 조건이 발생한다. | 서비스는 승인된 동작을 따른다. | 사용자 또는 시스템은 계획된 응답을 받는다. | 상태 또는 데이터 책임을 설명한다. | 복구 동작을 설명한다. | REQ-001 |

## Integration Flow And Data Responsibilities

동작 이해에 필요한 경우에만 서비스 수준 통합 순서와 데이터 책임을 설명한다.

## Boundaries

포함 범위와 제외 범위의 동작을 설명한다.

## Regression Prevention

bugfix 또는 mixed 요청에서 회귀하면 안 되는 동작을 설명한다.

## Failure And Recovery Behavior

오류, 빈 상태, 권한, 검증 실패, 복구 동작을 설명한다.
""",
    "implementation-plan": """# Implementation Plan

## Technical Approach

승인된 definition의 `DFLOW-001`을 구현 가능한 기술 흐름으로 옮긴다. 기존 프로젝트 구조 안에서 필요한 변경 지점을 정하고, 새 서비스 의미를 만들지 않고 승인된 요구사항과 정책만 구현한다.

## Implementation Architecture

진입점, 처리 책임, 저장 또는 조회 책임, 결과 노출 책임을 구분한다. 각 책임은 `WORK-001`의 변경 단위와 연결하고, flow 완료 증거가 검증 전략에서 확인되도록 설계한다.

## Change Areas

- 승인된 동작을 처리하는 코드 또는 문서 영역.
- flow 결과를 노출하거나 소비하는 경계.
- 회귀를 막거나 완료를 증명하는 테스트와 확인 절차.

## Cause Or Design Notes

설계는 `REQ-001`, `SP-001`, `INTENT-001`의 승인된 의미를 보존한다. 구현 중 새 제품 정책이나 사용자-visible 의미가 필요해지면 이 plan에서 결정하지 않고 definition으로 돌아간다.

## Implementation Flow Model

| Flow ID | Definition Flow ID | Definition Source | Trigger Or Entry | Target Outcome | Primary Work Items | Flow Status | Status Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FLOW-001 | DFLOW-001 | REQ-001, SP-001, INTENT-001 | 승인된 사용자 또는 시스템 진입점에서 flow가 시작된다. | 사용자, 관리자, consumer, 테스트가 승인된 완료 결과를 확인한다. | WORK-001 | complete | `DFLOW-001`은 in-scope이고 구현 단계에서 새 definition 결정이 필요하지 않다. |

## Flow Completeness Matrix

| Flow ID | Ordered Implementation Path | State/Data Transitions | Failure Or Empty States | Observable Completion | Validation Evidence |
| --- | --- | --- | --- | --- | --- |
| FLOW-001 | 진입점 수신 -> 승인된 정책 적용 -> 필요한 상태/데이터 처리 -> 완료 결과 노출. | 승인된 flow에 필요한 생성, 수정, 조회, 저장, 캐시 갱신, no-op 중 실제 전이를 기록한다. | 검증 실패, 빈 상태, 권한 실패, 외부 consumer 책임 등 이 flow의 실패/빈 상태를 기록한다. | 사용자, 관리자, consumer, 테스트 중 누가 어떤 결과를 보고 완료를 판단하는지 기록한다. | `FLOW-001` 완료를 증명하는 자동 테스트, 수동 확인, 리뷰 증거, 명령을 기록한다. |

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | 승인된 flow를 구현하는 구체적인 작업 단위. | `FLOW-001`을 위해 변경할 책임, 데이터 흐름, 실패 처리, 호환성 경계를 기술한다. | 실제 변경 결과와 `FLOW-001` 완료를 증명하는 검증 증거를 남긴다. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | 승인된 정책이 적용되는 변경 영역. | `SP-001`과 `FLOW-001` 결과를 입증하는 구체적인 확인. | 승인된 definition 밖의 의미 확장을 하지 않는다. |

## Definition Fidelity Matrix

| Work Item ID | Definition Source | Approved Meaning | Technical Interpretation | Must Not Interpret As | If Ambiguous |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | REQ-001, SP-001, INTENT-001 | definition에서 승인된 요구사항과 정책 의미. | 승인된 의미를 보존하는 구현 책임과 경계. | 승인되지 않은 더 좁은 UX, route, screen, state, data, API 해석. | return-to-definition |

## Edge Cases And Failure Modes

검증 실패, 빈 상태, 권한 실패, 외부 consumer 책임, no-op, 하위 호환성, rollback 또는 recovery가 필요한 상황을 flow별로 기록한다.

## Validation Strategy

- `FLOW-001`의 observable completion을 증명하는 자동 또는 수동 확인을 실행한다.
- `WORK-001`의 실제 변경과 승인된 `SP-001` 정책 보존을 확인한다.
- 실패/빈 상태가 계획한 결과로 노출되는지 확인한다.

## Risks

승인된 definition이 다루지 않은 의미가 구현 중 드러나면 plan에서 임의 결정하지 않고 definition으로 돌아가야 한다.

## Constraints

승인된 definition, flow status, definition fidelity 범위를 벗어난 변경은 포함하지 않는다.
""",
    "implementation": """# Implementation

## Work Completed

승인된 implementation-plan의 work item별로 실제로 완료한 작업을 기록한다.

## Plan Compliance And Deviations

구현이 승인된 plan과 일치했는지, deviation, 생략된 작업, 미완료 작업, work item별 완료 증거를 포함해 기록한다.

## Work Item Completion Evidence

| Work Item ID | Planned Unit | Actual Change | Validation Evidence | Linked Flow IDs | Status |
| --- | --- | --- | --- | --- | --- |
| WORK-001 | 승인된 implementation-plan의 작업 단위. | 실제 변경 내용과 영향 범위. | 실행한 테스트, 명령, 수동 확인 또는 리뷰 증거. | FLOW-001 | completed |

## Flow Completion Evidence

| Flow ID | Definition Flow ID | Planned Outcome | Actual Result | Validation Evidence | Observable Completion | Status |
| --- | --- | --- | --- | --- | --- | --- |
| FLOW-001 | DFLOW-001 | 승인된 implementation-plan의 target outcome. | 실제 구현 결과와 변경 증거. | 실행한 테스트, 명령, 수동 확인 또는 리뷰 증거. | 사용자, 관리자, consumer, 테스트가 확인한 완료 결과. | completed |

## Validation

명령, 확인 항목, 결과를 기록한다.

## Review Result

implementation review subagent의 work item 완료성 검수 결과를 기록한다.

## Completion Summary

사용자가 승인할 수 있도록 plan 대비 실제 완료 결과와 남은 work item 리스크를 기록한다.
""",
    "review": """# Review

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

## Review Method

Subagent review.

## Reviewer

main agent synthesis

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | main agent synthesis | PASS | Synthesized bounded subagent review shards. |

## Subagent Review Shards

| Shard File | Scope | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| review/subagents/001-full-bounded-review.md | full bounded review for a small stage | PASS | None |

## Writing And Review Rule Checklist

| Rule ID | Evidence Read | Verdict | Blocking Issue |
| --- | --- | --- | --- |
| DEF-RULE-001 | Project context and definition were checked. | PASS | None |

## Latest Verdict

PASS

## Blocking Issues

No blocking issues

## Final Verdict

No blocking issues.
""",
    "approval": """# Approval

Stage: definition

Stage approved: yes

Approved By: user

Approved At: 2026-06-21T03:00:00Z

## Approval Text

Approved.
""",
    "stage-tree": render_stage_tree() + "\n",
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root containing `.stageflow`.")
    parser.add_argument("--print-template", choices=sorted(VALIDATOR_TEMPLATES))
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--current", action="store_true")
    selector.add_argument("--request")
    parser.add_argument("--session-id")
    parser.add_argument("--phase", default="all", choices=sorted(VALIDATION_PHASES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.print_template:
        print(VALIDATOR_TEMPLATES[args.print_template].strip())
        return

    errors: list[str] = []
    awaiting: list[str] = []
    root = Path(args.root).resolve()
    context = load_context(root, args.current, args.request, args.session_id, errors)
    if context is not None:
        awaiting = validate_phase(context, args.phase, errors)

    if errors:
        print(f"FAIL {args.phase}:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    if awaiting:
        print(f"AWAITING_USER {args.phase}:")
        for item in awaiting:
            print(f"- {item}")
        raise SystemExit(3)

    print(f"PASS {args.phase}: {context.request_id if context else root}")


if __name__ == "__main__":
    main()
