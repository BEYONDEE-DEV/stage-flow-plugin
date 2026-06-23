#!/usr/bin/env python3
"""Validate four-stage `.stageflow` request artifacts."""

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
        "requirements",
        "01-requirements",
        "requirements.md",
        "Requirements",
        (
            "User Goal",
            "Request Profile",
            "Desired Outcomes",
            "Current Problems",
            "Problem-To-Requirement Mapping",
            "User-Specified Constraints",
            "Discovered Constraints",
            "Clarification History",
            "Open Questions",
            "Resolved Decisions",
            "Requirements",
            "Acceptance Criteria",
        ),
        "01-requirements",
        "requirements-writing-and-review-rules.md",
        "Requirements Writing And Review Rules",
        (
            TableRequirement("Desired Outcomes", ("ID", "Outcome", "Source", "Success Signal")),
            TableRequirement(
                "Current Problems",
                ("ID", "Problem", "Expected Behavior", "Actual Behavior", "Evidence Or Reproduction", "Impact"),
            ),
            TableRequirement("Problem-To-Requirement Mapping", ("Problem ID", "Requirement ID", "Resolution")),
            TableRequirement(
                "Clarification History",
                (
                    "Round ID",
                    "Questions Asked",
                    "User Response",
                    "Service Plan Option Offered",
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
        ),
    ),
    Stage(
        "service-plan",
        "02-service-plan",
        "service-plan.md",
        "Service Plan",
        (
            "Normal Behavior Model",
            "User Flow",
            "State And Policy Model",
            "Policy Rules",
            "Integration Flow And Data Responsibilities",
            "Boundaries",
            "Regression Prevention",
            "Failure And Recovery Behavior",
        ),
        "02-service-plan",
        "service-plan-writing-and-review-rules.md",
        "Service Plan Writing And Review Rules",
        (
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
        "03-implementation-plan",
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
        "03-implementation-plan",
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
        "04-implementation",
        "implementation.md",
        "Implementation",
        ("Work Completed", "Plan Compliance And Deviations", "Validation", "Review Result", "Completion Summary"),
        "04-implementation",
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
SERVICE_PLAN_TRANSITION_RE = re.compile(
    r"\b(proceed|approved|approval|done|service plan|next stage)\b|승인|진행|서비스\s*계획|다음\s*단계",
    re.IGNORECASE,
)
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
        errors.append("`state.json` field `phase` must be one of the four stages or `completed`")


def stages_for_phase(phase: str) -> tuple[Stage, ...]:
    if phase == "all":
        return STAGES
    index = STAGES.index(STAGE_BY_PHASE[phase])
    return STAGES[: index + 1]


def validate_phase(context: ValidationContext, phase: str, errors: list[str]) -> None:
    for stage in stages_for_phase(phase):
        validate_stage(context, stage, errors)
    if phase == "all" and string_value(context.state, "phase") != "completed":
        errors.append("`state.json` phase must be `completed` for `--phase all`")


def validate_stage(context: ValidationContext, stage: Stage, errors: list[str]) -> None:
    stage_dir = context.request_dir / stage.folder
    artifact_path = stage_dir / stage.artifact
    goal_path = stage_dir / "goal.md"
    review_path = stage_dir / "review.md"
    approval_path = stage_dir / "approval.md"

    rule_ids = validate_stage_rule_document(stage, errors)
    validate_stage_review_agent_prompt(stage, errors)

    artifact_text = read_required_text(artifact_path, errors)
    if artifact_text is not None:
        validate_artifact(stage, artifact_text, artifact_path, errors)
        artifact_fingerprint = sha256_file(artifact_path)
    else:
        artifact_fingerprint = None

    validate_goal(stage, goal_path, artifact_fingerprint, errors)
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


def validate_artifact(stage: Stage, text: str, path: Path, errors: list[str]) -> None:
    if f"# {stage.title}" not in text:
        errors.append(f"`{display_path(path)}` must start with or include `# {stage.title}`")
    for section in stage.required_sections:
        if not section_text(text, f"## {section}").strip():
            errors.append(f"`{display_path(path)}` must include non-empty `## {section}`")
    for requirement in stage.artifact_tables:
        validate_table_columns(path, text, requirement, errors)
    if stage.phase == "requirements":
        validate_requirements_blocking_questions(path, text, errors)
        validate_requirements_clarification_history(path, text, errors)
    if stage.phase == "implementation-plan":
        validate_implementation_plan_depth(path, text, errors)


def validate_requirements_blocking_questions(path: Path, text: str, errors: list[str]) -> None:
    table = parse_first_markdown_table(section_text(text, "## Open Questions"))
    for row in table.rows:
        blocking_value = row.get("Blocking", "").strip()
        if BLOCKING_OPEN_QUESTION_RE.fullmatch(blocking_value):
            question_id = row.get("ID", "").strip() or "<unknown>"
            errors.append(
                f"`{display_path(path)}` Open Questions row `{question_id}` is still blocking; "
                "resolve it before requirements approval"
            )


def validate_requirements_clarification_history(path: Path, text: str, errors: list[str]) -> None:
    table = parse_first_markdown_table(section_text(text, "## Clarification History"))
    if not table.rows:
        return
    has_transition_signal = False
    for index, row in enumerate(table.rows):
        round_id = row.get("Round ID", "").strip() or "<unknown>"
        questions = row.get("Questions Asked", "").strip()
        offered = row.get("Service Plan Option Offered", "").strip()
        transition_signal = row.get("User Transition Signal", "").strip()
        if offered.lower() not in {"yes", "true"} and "서비스 계획" not in offered:
            errors.append(
                f"`{display_path(path)}` Clarification History row `{round_id}` must record that a service-plan transition option was offered"
            )
        if not has_meaningful_proposal_options(questions):
            errors.append(
                f"`{display_path(path)}` Clarification History row `{round_id}` must include a concrete question with at least two proposal options before the service-plan transition option"
            )
        is_transition = bool(SERVICE_PLAN_TRANSITION_RE.search(transition_signal))
        if is_transition:
            has_transition_signal = True
        elif index == len(table.rows) - 1:
            errors.append(
                f"`{display_path(path)}` Clarification History row `{round_id}` records a proposal answer but no following clarification round or service-plan transition"
            )
    if not has_transition_signal:
        errors.append(
            f"`{display_path(path)}` Clarification History must record an explicit user choice to move to service-plan before approval"
        )


def has_meaningful_proposal_options(text: str) -> bool:
    lower = text.lower()
    if "서비스 계획" not in text and "service plan" not in lower:
        return False
    if "options:" in lower:
        option_text = text[lower.find("options:") + len("options:") :]
    elif "선택지:" in text:
        option_text = text[text.find("선택지:") + len("선택지:") :]
    else:
        return False
    options = [item.strip().lower() for item in re.split(r"[,;/|]", option_text) if item.strip()]
    proposal_options = [item for item in options if "서비스 계획" not in item and "service plan" not in item and "next stage" not in item]
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


def validate_goal(
    stage: Stage,
    path: Path,
    artifact_fingerprint: str | None,
    errors: list[str],
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
    if status in {"", "pending", "blocked", "failed", "no"}:
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
    return "\n".join(
        f"- `{stage.folder}/goal.md`, `{stage.folder}/{stage.artifact}`, "
        f"`{stage.folder}/review.md`, `{stage.folder}/approval.md`"
        for stage in STAGES
    )


VALIDATOR_TEMPLATES: dict[str, str] = {
    "index": """{
  "version": "1",
  "requests": [
    {
      "id": "20260621-1200-four-stage-workflow",
      "title": "Four stage workflow",
      "status": "requirements",
      "created_at": "2026-06-21T03:00:00Z",
      "updated_at": "2026-06-21T03:00:00Z"
    }
  ]
}
""",
    "current": """{
  "request_id": "20260621-1200-four-stage-workflow",
  "phase": "requirements",
  "activated_by": "explicit_skill_invocation"
}
""",
    "state": """{
  "request_id": "20260621-1200-four-stage-workflow",
  "phase": "requirements",
  "last_validated_at": null
}
""",
    "goal": """# Goal

Stage: requirements

Artifact Path: `01-requirements/requirements.md`

Artifact Fingerprint: sha256:<artifact-fingerprint>

## Goal Invocation

Tool: create_goal

Invocation recorded: yes

Invocation result: goal created

## Goal Objective

Execute this stage from the current artifact only. Update the stage artifact, then require subagent review and user approval before advancing.

## Goal Tool Status

Goal created: yes

Goal status: active
""",
    "requirements": """# Requirements

## User Goal

Describe the user's goal in their language.

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

## Clarification History

| Round ID | Questions Asked | User Response | Service Plan Option Offered | User Transition Signal | Reflected In |
| --- | --- | --- | --- | --- | --- |
| CLAR-001 | Which concrete direction should requirements capture? Options: Proposal 1, Proposal 2, 서비스 계획으로 넘어가기. | User selected `서비스 계획으로 넘어가기`. | yes | 서비스 계획으로 넘어가기 | N/A |

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
""",
    "service-plan": """# Service Plan

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

Stage: requirements

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
| REQ-RULE-001 | Project context and requirements were checked. | PASS | None |

## Latest Verdict

PASS

## Blocking Issues

No blocking issues

## Final Verdict

No blocking issues.
""",
    "approval": """# Approval

Stage: requirements

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
    root = Path(args.root).resolve()
    context = load_context(root, args.current, args.request, args.session_id, errors)
    if context is not None:
        validate_phase(context, args.phase, errors)

    if errors:
        print(f"FAIL {args.phase}:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"PASS {args.phase}: {context.request_id if context else root}")


if __name__ == "__main__":
    main()
