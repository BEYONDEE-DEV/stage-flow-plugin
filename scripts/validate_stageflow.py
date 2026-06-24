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
            "Requirements",
            "Acceptance Criteria",
            "Normal Behavior Model",
            "User Flow",
            "State And Policy Model",
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
                    "Question Depth",
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
            "Work Items",
            "Coverage Matrix",
            "Edge Cases And Failure Modes",
            "Validation Strategy",
            "Risks",
            "Constraints",
        ),
        "02-implementation-plan",
        "implementation-plan-writing-and-review-rules.md",
        "Implementation Plan Writing And Review Rules",
        (
            TableRequirement("Work Items", ("ID", "Implementation Unit", "Technical Design", "Completion Evidence")),
            TableRequirement(
                "Coverage Matrix",
                ("Service Rule ID", "Work Item ID", "Change Area", "Validation Evidence", "Risk/Constraint"),
            ),
        ),
    ),
    Stage(
        "implementation",
        "03-implementation",
        "implementation.md",
        "Implementation",
        ("Work Completed", "Plan Compliance And Deviations", "Validation", "Review Result", "Completion Summary"),
        "03-implementation",
        "implementation-writing-and-review-rules.md",
        "Implementation Writing And Review Rules",
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
    r"\b(implementation plan|proceed|go ahead|approve|approved|yes|stop asking|enough)\b"
    r"|구현\s*계획|질문\s*그만|충분|진행|승인",
    re.IGNORECASE,
)
PENDING_STATUS_RE = re.compile(r"^(pending|awaiting|awaiting_user|대기|답변\s*대기)$", re.IGNORECASE)
OPTION_LABEL_RE = re.compile(r"^(?:Option\s*[1-9]\d*|선택지\s*[1-9]\d*|[A-Z])\s*:", re.IGNORECASE)
PENDING_DEPTHS = ("broad", "mid", "detail")
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
PURPOSE_CONFIDENCES = {"confirmed", "inferred", "unknown"}
PURPOSE_KEYWORD_RE = re.compile(
    r"\b(purpose|why|intent|value|goal|outcome|success)\b|목적|왜|의도|가치|목표|성과|성공",
    re.IGNORECASE,
)
NO_PENDING_STATUS_RE = re.compile(r"^(none|n/a|no|없음)$", re.IGNORECASE)
AWAITING_USER_GOAL_STATUSES = {"complete", "completed"}
AWAITING_USER_GOAL_REASON = "awaiting user clarification"
FINGERPRINT_RE = re.compile(r"sha256:([0-9a-fA-F]{64})")
REFERENCE_ROOT_ENV = "STAGEFLOW_REFERENCE_ROOT"


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
    review_path = stage_dir / "review.md"
    approval_path = stage_dir / "approval.md"

    rule_ids = validate_stage_rule_document(stage, errors)
    validate_stage_review_agent_prompt(stage, errors)

    artifact_text = read_required_text(artifact_path, errors)
    pending_messages: list[str] = []
    if artifact_text is not None:
        pending_messages = pending_clarification_messages(stage, artifact_text, artifact_path, errors)
        validate_artifact(stage, artifact_text, artifact_path, errors, bool(pending_messages))
        artifact_fingerprint = sha256_file(artifact_path)
    else:
        artifact_fingerprint = None

    if stage.phase == "definition" and artifact_text is not None and artifact_fingerprint is not None:
        validate_transition_risk_gate(stage_dir, artifact_text, artifact_fingerprint, errors, bool(pending_messages))
    if stage.phase != "definition":
        validate_goal(stage, goal_path, artifact_fingerprint, errors, bool(pending_messages))
    if pending_messages:
        awaiting.extend(pending_messages)
        return
    validate_review(stage, review_path, artifact_fingerprint, rule_ids, errors)
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
        "## Writing And Review Rule Checklist",
        "## Latest Verdict",
        "## Blocking Issues",
        "## Final Verdict",
        "PASS or FAIL",
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
    if stage.phase == "implementation-plan":
        validate_implementation_plan_depth(path, text, errors)



def pending_clarification_messages(stage: Stage, text: str, path: Path, errors: list[str]) -> list[str]:
    if stage.phase != "definition":
        return []
    table = parse_first_markdown_table(section_text(text, "## Pending Clarifications"))
    if not table.rows:
        return []

    messages: list[str] = []
    depths: list[str] = []
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

        depth = row.get("Question Depth", "").strip()
        question = row.get("Question", "").strip()
        options = row.get("Options", "").strip()
        recommended = row.get("Recommended Option", "").strip()
        transition = row.get("Transition Option", "").strip()
        why = row.get("Why This Matters", "").strip()
        missing = [
            name
            for name, value in (
                ("Question Depth", depth),
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
        depths.append(depth)
        if depth not in PENDING_DEPTHS:
            errors.append(
                f"`{display_path(path)}` Pending Clarifications row `{pending_id}` Question Depth must be one of {', '.join(PENDING_DEPTHS)}"
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
        messages.append(
            f"`{display_path(path)}` pending clarification `{pending_id}`: Depth: {depth} Question: {question} Options: {options} Recommended: {recommended} Transition option: {transition} Why this matters: {why}"
        )
    if len(messages) > 5:
        errors.append(
            f"`{display_path(path)}` Pending Clarifications must ask no more than five active questions per batch before the user explicitly stops"
        )
    return messages


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
    if row.get("Question Depth", "").strip() != "broad":
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
                f"`{display_path(path)}` Purpose And Intent is {confidence_rank}; Pending Clarifications must include at least one purpose-focused broad question"
            )
    if confidence_rank != "confirmed" and has_user_stop_signal(text):
        errors.append(
            f"`{display_path(path)}` Purpose And Intent must be confirmed before definition clarification can stop"
        )


def validate_definition_blocking_questions(path: Path, text: str, errors: list[str]) -> None:
    table = parse_first_markdown_table(section_text(text, "## Open Questions"))
    for row in table.rows:
        blocking_value = row.get("Blocking", "").strip()
        if BLOCKING_OPEN_QUESTION_RE.fullmatch(blocking_value):
            question_id = row.get("ID", "").strip() or "<unknown>"
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
        ("ID", "Category", "Risk Case", "Affected Definition Area", "Suggested Handling", "User Confirmation", "Disposition"),
        "## Generated Risk Cases",
        errors,
    )
    reflected = reflected_definition_sections(definition_text).lower()
    for row in table.rows:
        risk_id = row.get("ID", "").strip() or "<unknown>"
        category = row.get("Category", "").strip()
        risk_case = row.get("Risk Case", "").strip()
        confirmation = row.get("User Confirmation", "").strip()
        disposition = row.get("Disposition", "").strip()
        is_no_material = "no material transition risks found" in risk_case.lower()
        if category not in TRANSITION_RISK_CATEGORIES:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Category is not allowed")
        if not confirmation or confirmation.lower() in {"n/a", "none", "pending", "unconfirmed"}:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` must record User Confirmation")
        if disposition not in TRANSITION_RISK_DISPOSITIONS:
            errors.append(f"`{display_path(path)}` Generated Risk Cases row `{risk_id}` Disposition is not allowed")
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
    validate_rule_checklist(path, text, rule_ids, errors)
    validate_fingerprint(path, text, "Reviewed Artifact Fingerprint", artifact_fingerprint, errors)


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
                f"`{stage.folder}/transition-risk-goal.md` (after stop signal)",
                f"`{stage.folder}/transition-risk.md` (after stop signal)",
            ])
        else:
            parts.append(f"`{stage.folder}/goal.md`")
            parts.append(f"`{stage.folder}/{stage.artifact}`")
        parts.extend([
            f"`{stage.folder}/review.md`",
            f"`{stage.folder}/approval.md`",
        ])
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

Describe the user's goal in their language.

## Purpose And Intent

| Purpose | User Value | Business/Product Value | Source | Confidence |
| --- | --- | --- | --- | --- |
| The purpose still needs user confirmation. | Clarifies why the result matters to the user. | Clarifies product or workflow value before planning. | user request needs clarification | unknown |

## Request Profile

Primary: feature
Secondary: none

## Desired Outcomes

| ID | Outcome | Source | Success Signal |
| --- | --- | --- | --- |
| OUT-001 | The requested result is visible or verifiable. | User request. | A reviewer can confirm the outcome. |

## Current Problems

| ID | Problem | Expected Behavior | Actual Behavior | Evidence Or Reproduction | Impact |
| --- | --- | --- | --- | --- | --- |
| PROB-001 | No current problem identified. | N/A | N/A | N/A | N/A |

## Problem-To-Requirement Mapping

| Problem ID | Requirement ID | Resolution |
| --- | --- | --- |
| PROB-001 | REQ-001 | The requirement resolves or prevents the problem. |

## User-Specified Constraints

- None specified.

## Discovered Constraints

- None discovered.

## Pending Clarifications

| ID | Question Depth | Question | Options | Recommended Option | Transition Option | Why This Matters | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PENDING-001 | broad | Why is this request needed, and what purpose should the change serve? | Option 1: solve an immediate user workflow problem; Option 2: create product flexibility for follow-up changes | Option 1 | N/A | Purpose must be confirmed before deeper behavior or implementation planning. | pending |
| PENDING-002 | broad | Which top-level scope boundary should be clarified next? | Option 1: narrow the request boundary; Option 2: include adjacent behavior | Option 1 | N/A | Start with broad request identity and scope before details. | pending |
| PENDING-003 | broad | Which user or system surface should this request primarily affect? | Option 1: user-facing behavior; Option 2: internal workflow behavior; Option 3: both user-facing and internal behavior | Option 1 | N/A | Broad surface decisions shape later behavior questions. | pending |

## Clarification History

| Round ID | Questions Asked | User Response | Implementation Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-000 | No completed clarification yet. | N/A | no | N/A | N/A |

## Open Questions

| ID | Decision Needed | Context Or Conflict | Recommended Option | Alternatives | Impact | Blocking | Resolution Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | No open question. | N/A | N/A | N/A | N/A | no | N/A |

## Resolved Decisions

| ID | Source Question ID | Answer Source | Decision | Reflected In |
| --- | --- | --- | --- | --- |
| DEC-001 | N/A | N/A | No resolved decision yet. | N/A |

## Requirements

| ID | Type | Source | Requirement Detail | Boundary Or Exclusion | Linked Outcomes Or Problems |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | feature | User request. | One concrete requirement. | Out-of-scope behavior is explicit. | OUT-001 |

## Acceptance Criteria

- `REQ-001` is satisfied when `OUT-001` is verifiable.

## Normal Behavior Model

Describe the corrected or desired service behavior as an organized model.

## User Flow

Describe what the user or system does, sees, and receives in order.

## State And Policy Model

Describe states, transitions, permissions, validation rules, and product policies.

## Policy Rules

| Rule ID | Trigger Or Condition | Policy | User/System Response | State/Data Responsibility | Failure/Recovery Behavior | Source Requirement IDs |
| --- | --- | --- | --- | --- | --- | --- |
| SP-001 | A relevant condition occurs. | The service follows the approved behavior. | The user or system sees the planned response. | State or data responsibility is described. | Recovery behavior is described. | REQ-001 |

## Integration Flow And Data Responsibilities

Describe service-level integration sequence and data responsibilities only where needed for behavior.

## Boundaries

Describe in-scope and out-of-scope behavior.

## Regression Prevention

Describe bugfix or mixed-request behaviors that must not regress.

## Failure And Recovery Behavior

Describe errors, empty states, permissions, validation failures, and recovery behavior.
""",
    "implementation-plan": """# Implementation Plan

## Technical Approach

Use the existing validator-driven Stageflow architecture. Extend the stage metadata and markdown validators instead of adding a separate parser path so the same gate enforces artifact format, review checklist, and approval behavior.

## Implementation Architecture

`scripts/validate_stageflow.py` owns required section and table validation. Stage rule markdown owns authoring/review contracts. Tests create fixture requests that exercise the validator through subprocess, so fixtures must mirror the new artifact contract.

## Change Areas

- Stage metadata and validation helpers in `scripts/validate_stageflow.py`.
- Stage writing and review rules under `skills/stageflow/references/stages/`.
- Fixture artifacts and regression tests under `tests/`.

## Cause Or Design Notes

The implementation plan must prevent file-list-only plans by requiring architecture, flow, edge-case, and validation evidence before implementation approval.

## Work Items

| ID | Implementation Unit | Technical Design | Completion Evidence |
| --- | --- | --- | --- |
| WORK-001 | Stage validator contract. | Add required technical sections and table columns to the implementation-plan stage metadata. | Validator rejects artifacts missing technical sections or using legacy work-item columns. |

## Coverage Matrix

| Service Rule ID | Work Item ID | Change Area | Validation Evidence | Risk/Constraint |
| --- | --- | --- | --- | --- |
| SP-001 | WORK-001 | Validator, rules, and tests. | `python -m unittest discover -s tests` passes and targeted negative tests fail shallow plans. | Keep behavior scoped to implementation-plan artifact quality. |

## Edge Cases And Failure Modes

Legacy implementation-plan artifacts with only `Change Areas`, `Work Items`, and `Validation` fail validation. Missing technical sections fail before approval. Generic rows such as `Code and tests` or `Implement behavior` are rejected as too shallow.

## Validation Strategy

- Run `python -m unittest discover -s tests` to verify all Stageflow gates.
- Include negative tests for missing technical sections and shallow work item text.
- Confirm printed templates include the new technical sections.

## Risks

Stricter validation may require existing in-flight Stageflow requests to update implementation-plan artifacts.

## Constraints

Do not weaken approval, fingerprint, review, or stage-order gates.
""",
    "implementation": """# Implementation

## Work Completed

Record the actual work completed.

## Plan Compliance And Deviations

Record whether the implementation matched the approved plan, including deviations, skipped work, or incomplete work.

## Validation

Record commands, checks, and results.

## Review Result

Record the implementation review result.

## Completion Summary

Record the final plan-vs-actual outcome for the user.
""",
    "review": """# Review

Stage: definition

Reviewed Artifact Fingerprint: sha256:<artifact-fingerprint>

## Review Method

Subagent review.

## Reviewer

reviewer subagent

## Review Cycle

| Cycle | Reviewer | Result | Notes |
| --- | --- | --- | --- |
| 1 | reviewer subagent | PASS | No blocking issues. |

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
