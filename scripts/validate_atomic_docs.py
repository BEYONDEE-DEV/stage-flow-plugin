#!/usr/bin/env python3
"""Validate deterministic atomic-docs structure in a target project."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in incomplete runtimes
    yaml = None

PHASES = (
    "bootstrap",
    "selection",
    "docs",
    "baseline",
    "metrics-preterminal",
    "metrics-final",
)
REQUIRED_CONFIG = ("storage_mode", "docs_root", "source_root", "baseline_metadata_path")
REQUIRED_SECTIONS = (
    "Intent",
    "Outcomes",
    "Boundaries",
    "Rules",
    "Current Implementation",
    "Planned Changes",
    "Gaps",
)
SECTION_CODES = {
    "intent": "Intent",
    "outcome": "Outcomes",
    "boundary": "Boundaries",
    "rules": "Rules",
    "impl": "Current Implementation",
    "source": "Current Implementation",
    "plan": "Planned Changes",
    "gap": "Gaps",
}
ATOM_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
AID_TOKEN_RE = re.compile(r"\[AID:[^\]\n]+\]")
AID_RE = re.compile(
    r"^\[AID:(?P<key>[a-z0-9]+(?:-[a-z0-9]+)*)\."
    r"(?P<section>intent|outcome|boundary|rules|impl|plan|gap|source)\."
    r"(?P<number>\d{3})\]$"
)
COMMIT_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:[Zz]|[+-]\d{2}:\d{2})$"
)
SEMANTIC_REVIEW_ROLES = {"development", "risk", "integration", "baseline"}
SEMANTIC_REVIEW_STATUSES = {"current", "stale", "superseded"}
OPERATION_METRIC_KINDS = {
    "bundle",
    "writer",
    "development-review",
    "risk-review",
    "integration-review",
    "baseline-review",
    "validation",
}
OPERATION_METRIC_OUTCOMES = {"PASS", "FAIL", "completed"}
REVIEW_METRIC_KINDS = {
    "development": "development-review",
    "risk": "risk-review",
    "integration": "integration-review",
    "baseline": "baseline-review",
}
SEMANTIC_INVALIDATION_TRIGGERS = {
    "candidate-disposition",
    "atom-merge",
    "ownership",
    "glossary-source",
    "shared-decision-owner",
    "graph-relationship",
    "documented-meaning",
}
SHARED_CONTRACT_KINDS = {
    "permission",
    "shared-identifier",
    "money-entitlement",
    "final-projection",
    "integration",
}
SEMANTIC_FAIL_ROOT_CATEGORIES = {
    "candidate-admission",
    "contract-routing",
    "owner-evidence",
    "consumer-closure",
    "evidence-depth",
    "selected-claim-fidelity",
}
EVIDENCE_COMMIT_RE = re.compile(
    r"^source_commit_observed:[ ]*`([0-9a-fA-F]{40}|[0-9a-fA-F]{64})`[ ]*$",
    re.MULTILINE,
)
RAW_HTML_RE = re.compile(
    r"<!--|<!\[CDATA\[|<\?|<![A-Za-z]|</?[A-Za-z]"
)


@dataclass
class Config:
    project_root: Path
    docs_root: Path
    source_root: Path
    baseline_path: Path
    storage_mode: str


@dataclass
class Atom:
    path: Path
    rel_path: str
    atom_key: str
    edges: list[dict[str, str]]
    body_lines: list[str]


class DuplicateJsonKeyError(ValueError):
    """Raised when a JSON object repeats a key."""


def construct_unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


if yaml is not None:
    class UniqueKeyLoader(yaml.SafeLoader):
        """Safe YAML loader that rejects duplicate mapping keys."""


    def construct_unique_mapping(
        loader: UniqueKeyLoader, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        loader.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping


    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate plugin-managed atomic docs without modifying the target project."
    )
    parser.add_argument("--root", default=".", help="Target project root")
    parser.add_argument("--phase", choices=PHASES, default="docs")
    parser.add_argument(
        "--expect-atom-key",
        action="append",
        default=[],
        help="Atom key expected from the active bundle; repeat for multiple atoms",
    )
    parser.add_argument(
        "--request-id",
        help="Atomic Docs request id; required for selection and optional for final docs/baseline closure",
    )
    parser.add_argument(
        "--require-actions-final",
        action="store_true",
        help="Require every recorded removal/delete/merge action to be terminal",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    if args.expect_atom_key and args.phase != "docs":
        errors.append("`--expect-atom-key` requires `--phase docs`")
    request_required_phases = {"selection", "metrics-preterminal", "metrics-final"}
    if args.phase in request_required_phases and not args.request_id:
        errors.append(f"`--phase {args.phase}` requires `--request-id`")
    request_phases = {
        "selection",
        "docs",
        "baseline",
        "metrics-preterminal",
        "metrics-final",
    }
    if args.request_id and args.phase not in request_phases:
        errors.append(
            "`--request-id` requires `--phase selection`, `docs`, `baseline`, "
            "`metrics-preterminal`, or `metrics-final`"
        )
    if args.require_actions_final and args.phase != "selection":
        errors.append("`--require-actions-final` requires `--phase selection`")
    config = load_config(Path(args.root).resolve(), errors)
    atoms: list[Atom] = []
    aid_count = 0
    if config is not None:
        validate_bootstrap(config, errors)
        if args.phase == "selection" and args.request_id:
            validate_selection(
                config,
                args.request_id,
                errors,
                require_actions_final=args.require_actions_final,
            )
        if args.phase in {"docs", "baseline"}:
            scope_keys = args.expect_atom_key if args.phase == "docs" else []
            atoms, aid_count = validate_docs(config, errors, scope_keys)
            if args.request_id:
                final_request_validation = (
                    args.phase == "baseline" or not args.expect_atom_key
                )
                validate_selection(
                    config,
                    args.request_id,
                    errors,
                    require_actions_final=final_request_validation,
                    require_final=final_request_validation,
                    metrics_mode=(
                        "final-validation" if final_request_validation else "active"
                    ),
                    validation_scope=args.phase,
                )
        if args.phase == "baseline":
            validate_baseline(config, errors)
        if args.phase in {"metrics-preterminal", "metrics-final"} and args.request_id:
            if args.phase == "metrics-preterminal":
                validate_request_preterminal_artifacts(
                    config,
                    args.request_id,
                    errors,
                )
            terminal_mode = (
                "preterminal"
                if args.phase == "metrics-preterminal"
                else "final"
            )
            validate_selection(
                config,
                args.request_id,
                errors,
                require_actions_final=True,
                require_final=True,
                metrics_mode=terminal_mode,
                validation_scope=None,
            )

    if errors:
        print(f"FAIL {args.phase}:")
        for error in errors:
            print(f"- {error}")
        return 1

    scope = " scoped" if args.expect_atom_key else ""
    detail = f" ({len(atoms)}{scope} atoms, {aid_count}{scope} AIDs)" if atoms else ""
    final = " final" if args.require_actions_final else ""
    print(f"PASS {args.phase}{final}: {Path(args.root).resolve()}{detail}")
    return 0


def load_config(project_root: Path, errors: list[str]) -> Config | None:
    config_path = project_root / ".stageflow" / "atomic-docs.json"
    data = read_json(config_path, rel(project_root, config_path), errors)
    if data is None:
        return None

    for key in REQUIRED_CONFIG:
        if key not in data:
            errors.append(f"atomic docs config must include `{key}`")

    storage_mode = data.get("storage_mode")
    if storage_mode not in {"repository", "submodule"}:
        errors.append("atomic docs config `storage_mode` must be `repository` or `submodule`")

    docs_value = path_value(data.get("docs_root"), "docs_root", errors, allow_dot=False)
    source_value = path_value(data.get("source_root"), "source_root", errors, allow_dot=True)
    baseline_value = path_value(
        data.get("baseline_metadata_path"),
        "baseline_metadata_path",
        errors,
        allow_dot=False,
    )
    if docs_value is None or source_value is None or baseline_value is None:
        return None

    docs_root = (project_root / docs_value).resolve()
    source_root = (project_root / source_value).resolve()
    baseline_path = (docs_root / baseline_value).resolve()
    if not inside(project_root, docs_root):
        errors.append("configured `docs_root` must stay inside the target project")
    if not inside(project_root, source_root):
        errors.append("configured `source_root` must stay inside the target project")
    if not inside(docs_root, baseline_path):
        errors.append("configured `baseline_metadata_path` must stay inside `docs_root`")

    return Config(project_root, docs_root, source_root, baseline_path, storage_mode)


def validate_bootstrap(config: Config, errors: list[str]) -> None:
    if not config.docs_root.is_dir():
        errors.append(f"missing managed docs root `{rel(config.project_root, config.docs_root)}`")
    criteria = config.docs_root / "project" / "atomization-criteria.md"
    if not criteria.is_file():
        errors.append(f"missing criteria document `{rel(config.project_root, criteria)}`")
    if not config.source_root.is_dir():
        errors.append(f"missing configured source root `{rel(config.project_root, config.source_root)}`")


def validate_selection(
    config: Config,
    request_id: str,
    errors: list[str],
    *,
    require_actions_final: bool,
    require_final: bool | None = None,
    metrics_mode: str = "active",
    validation_scope: str | None = None,
) -> None:
    request_root = atomic_docs_request_root(config, request_id, errors)
    if request_root is None:
        return

    inventory_path = request_root / "inventory.md"
    inventory_text = read_text(
        inventory_path, rel(config.project_root, inventory_path), errors
    )

    evidence_path = request_root / "evidence.md"
    evidence_text = read_text(
        evidence_path, rel(config.project_root, evidence_path), errors
    )
    if evidence_text is not None:
        validate_evidence_markdown(evidence_text, errors)

    state_path = request_root / "work-state.json"
    state = read_json(state_path, rel(config.project_root, state_path), errors)
    if state is None:
        return

    context_selection = state.get("context_selection")
    if not isinstance(context_selection, dict):
        errors.append("work-state must contain a `context_selection` object")
        return
    selection_version = context_selection.get("version")
    if selection_version != "4":
        errors.append("work-state `context_selection.version` must be exact `4`")
        return

    if require_final is None:
        require_final = require_actions_final
    required_final_role = None
    if (
        require_final
        and metrics_mode in {"final-validation", "preterminal", "final"}
        and required_final_validation_scope(state) == "baseline"
    ):
        required_final_role = "baseline"
    validate_semantic_review_closure(
        state,
        errors,
        require_final=require_final,
        required_final_role=required_final_role,
    )
    validate_operation_metrics(
        state,
        errors,
        mode=metrics_mode,
        validation_scope=validation_scope,
    )

    accepted_scope = string_list(
        state.get("accepted_scope"), "work-state `accepted_scope`", errors
    )
    accepted_domains = set(accepted_scope)
    if not accepted_domains:
        errors.append("work-state `accepted_scope` must contain at least one approved domain path")
    for domain in sorted(accepted_domains):
        if safe_relative(domain) is None:
            errors.append(f"accepted domain path `{domain}` must be a safe relative path")

    source_commit = nonempty_string(state.get("source_commit_observed"))
    if source_commit is None or not COMMIT_RE.fullmatch(source_commit):
        errors.append(
            "work-state `source_commit_observed` must be a 40- or 64-character Git hash"
        )
    else:
        if not git_commit_exists(config.source_root, source_commit):
            errors.append(
                f"source commit `{source_commit}` is not reachable from "
                f"`{rel(config.project_root, config.source_root)}`"
            )
        if evidence_text is not None:
            validate_evidence_revision(evidence_text, source_commit, errors)

    raw_candidates = context_selection.get("candidates")
    if not isinstance(raw_candidates, list):
        errors.append("work-state `context_selection.candidates` must be a list")
        return

    planned_keys: set[str] = set()
    planned_key_domains: dict[str, str] = {}
    pending_merge_targets: list[tuple[int, str]] = []
    candidate_targets: dict[str, set[str]] = {}
    candidate_dispositions: dict[str, str] = {}
    candidate_domains: dict[str, str] = {}
    evidence_sections = parse_evidence_sections(evidence_text, evidence_path, config, errors)
    for index, candidate in enumerate(raw_candidates, start=1):
        label = f"context candidate {index}"
        if not isinstance(candidate, dict):
            errors.append(f"{label} must be an object")
            continue
        candidate_id = nonempty_string(candidate.get("candidate_id"))
        if candidate_id is None or not ATOM_KEY_RE.fullmatch(candidate_id):
            errors.append(f"{label} must include lower-kebab-case `candidate_id`")
            candidate_id = None
        elif candidate_id in candidate_dispositions:
            errors.append(f"context candidate id `{candidate_id}` appears more than once")

        domain = nonempty_string(candidate.get("domain"))
        if domain is None:
            errors.append(f"{label} must include non-empty `domain`")
        elif domain not in accepted_domains:
            errors.append(f"{label} domain `{domain}` is outside `accepted_scope`")
        if nonempty_string(candidate.get("candidate")) is None:
            errors.append(f"{label} must include non-empty `candidate`")
        disposition = candidate.get("disposition")
        if disposition not in {"write", "merge", "drop"}:
            errors.append(f"{label} disposition must be `write`, `merge`, or `drop`")
            continue
        if candidate_id is not None:
            candidate_dispositions.setdefault(candidate_id, disposition)
            if domain is not None:
                candidate_domains.setdefault(candidate_id, domain)
            validate_candidate_evidence(candidate_id, evidence_sections, errors)
        if nonempty_string(candidate.get("selection_basis")) is None:
            errors.append(f"{label} must include non-empty `selection_basis`")

        keys = atom_key_list(candidate.get("candidate_atom_keys", []), label, errors)
        merge_target = nonempty_string(candidate.get("merge_target_atom_key"))
        if disposition == "write":
            if not keys:
                errors.append(f"{label} with disposition `write` needs `candidate_atom_keys`")
            if merge_target is not None:
                errors.append(f"{label} with disposition `write` must not set `merge_target_atom_key`")
            for key in keys:
                if key in planned_keys:
                    errors.append(f"planned atom key `{key}` is owned by more than one write candidate")
                planned_keys.add(key)
                if domain is not None:
                    planned_key_domains.setdefault(key, domain)
            if candidate_id is not None:
                candidate_targets[candidate_id] = set(keys)
        elif disposition == "merge":
            if keys:
                errors.append(f"{label} with disposition `merge` must not create atom keys")
            if merge_target is None or not ATOM_KEY_RE.fullmatch(merge_target):
                errors.append(
                    f"{label} with disposition `merge` needs lower-kebab-case `merge_target_atom_key`"
                )
            else:
                pending_merge_targets.append((index, merge_target))
                if candidate_id is not None:
                    candidate_targets[candidate_id] = {merge_target}
        else:
            if keys:
                errors.append(f"{label} with disposition `drop` must not create atom keys")
            if merge_target is not None:
                errors.append(f"{label} with disposition `drop` must not set `merge_target_atom_key`")
            if candidate_id is not None:
                candidate_targets[candidate_id] = set()

    for index, target in pending_merge_targets:
        if target not in planned_keys:
            errors.append(f"context candidate {index} merge target `{target}` is not a write candidate atom")

    queue_keys = validate_selection_queue(
        state.get("bundle_queue"), accepted_domains, planned_key_domains, errors
    )
    for key in sorted(planned_keys - queue_keys):
        errors.append(f"planned atom key `{key}` is missing from `bundle_queue.expected_atom_keys`")
    for key in sorted(queue_keys - planned_keys):
        errors.append(f"bundle queue atom key `{key}` has no write candidate")

    risk_keys = validate_selection_risk_triggers(
        state.get("risk_triggers", []), candidate_targets, candidate_dispositions, errors
    )
    validate_owner_readiness_v4(
        state,
        candidate_targets,
        candidate_dispositions,
        candidate_domains,
        errors,
        require_final=require_final,
    )
    validate_operation_artifact_state(
        config,
        request_root,
        state,
        candidate_targets,
        candidate_dispositions,
        candidate_domains,
        accepted_domains,
        planned_keys | queue_keys | risk_keys,
        inventory_text,
        require_actions_final,
        errors,
    )


def atomic_docs_request_root(
    config: Config, request_id: str, errors: list[str]
) -> Path | None:
    if (
        not request_id.strip()
        or Path(request_id).name != request_id
        or request_id in {".", ".."}
    ):
        errors.append("atomic docs `request_id` must be one safe path segment")
        return None
    requests_root = (
        config.project_root / ".stageflow" / "atomic-docs" / "requests"
    ).resolve()
    request_root = (requests_root / request_id).resolve()
    if not inside(requests_root, request_root):
        errors.append("atomic docs `request_id` must stay inside the requests root")
        return None
    return request_root


def validate_request_preterminal_artifacts(
    config: Config,
    request_id: str,
    errors: list[str],
) -> None:
    request_root = atomic_docs_request_root(config, request_id, errors)
    if request_root is None:
        return
    state_path = request_root / "work-state.json"
    state = read_json(state_path, rel(config.project_root, state_path), errors)
    if state is None:
        return
    metrics = state.get("operation_metrics")
    spans = metrics.get("spans") if isinstance(metrics, dict) else None
    if not isinstance(spans, list):
        return
    final_validations = [
        span
        for span in spans
        if isinstance(span, dict)
        and span.get("kind") == "validation"
        and span.get("scope") in {"docs", "baseline"}
        and span.get("status") == "finished"
    ]
    if not final_validations:
        return
    validation_scope = final_validations[-1].get("scope")
    required_scope = required_final_validation_scope(state)
    if validation_scope != required_scope:
        errors.append(
            f"operation requires final `{required_scope}` validation, not "
            f"`{validation_scope}`"
        )
    validate_docs(config, errors, [])
    if required_scope == "baseline":
        validate_baseline(config, errors)


def required_final_validation_scope(state: dict[str, Any]) -> str:
    if state.get("operation_profile") in {"initial-baseline", "baseline-diff-refresh"}:
        return "baseline"
    closure = state.get("semantic_review_closure")
    if not isinstance(closure, dict):
        return "docs"
    final_gate = closure.get("final_gate")
    review_id = final_gate.get("review_id") if isinstance(final_gate, dict) else None
    reviews = closure.get("review_passes")
    if isinstance(reviews, list):
        for review in reviews:
            if (
                isinstance(review, dict)
                and review.get("review_id") == review_id
                and review.get("status") == "current"
                and review.get("reviewer_role") == "baseline"
                and review.get("scope") == "project-wide"
            ):
                return "baseline"
    return "docs"


def validate_operation_metrics(
    state: dict[str, Any],
    errors: list[str],
    *,
    mode: str,
    validation_scope: str | None,
) -> None:
    selection = state.get("context_selection")
    selection_version = selection.get("version") if isinstance(selection, dict) else None
    metrics = state.get("operation_metrics")
    if selection_version != "4":
        errors.append(
            "work-state `operation_metrics` requires "
            "`context_selection.version` exact `4`"
        )
        return
    if not isinstance(metrics, dict):
        errors.append("v4 work-state must contain `operation_metrics`")
        return

    required = {"version", "status", "started_at", "spans"}
    validate_object_keys(
        metrics,
        required | {"finished_at"},
        required,
        "operation metrics",
        errors,
    )
    if metrics.get("version") != "1":
        errors.append("operation metrics `version` must be `1`")
    operation_status = nonempty_string(metrics.get("status"))
    if operation_status not in {"active", "finished"}:
        errors.append("operation metrics `status` must be `active` or `finished`")
    if mode in {"active", "final-validation", "preterminal"} and operation_status != "active":
        errors.append(f"operation metrics `{mode}` validation requires an active operation")
    operation_started = rfc3339_value(
        metrics.get("started_at"), "operation metrics `started_at`", errors
    )
    operation_finished: datetime | None = None
    if operation_status == "active":
        if "finished_at" in metrics:
            errors.append("active operation metrics must omit `finished_at`")
    elif operation_status == "finished":
        operation_finished = rfc3339_value(
            metrics.get("finished_at"), "operation metrics `finished_at`", errors
        )
        if (
            operation_started is not None
            and operation_finished is not None
            and operation_finished < operation_started
        ):
            errors.append("operation metrics `finished_at` must not precede `started_at`")

    spans = metrics.get("spans")
    if not isinstance(spans, list):
        errors.append("operation metrics `spans` must be a list")
        spans = []
    metric_bundle_scopes: set[str] = set()
    queue = state.get("bundle_queue")
    if isinstance(queue, list):
        metric_bundle_scopes.update(
            bundle["bundle_id"]
            for bundle in queue
            if isinstance(bundle, dict)
            and isinstance(bundle.get("bundle_id"), str)
        )
    registry = state.get("selection_retirements")
    retired_bundles = (
        registry.get("retired_bundles") if isinstance(registry, dict) else None
    )
    if isinstance(retired_bundles, list):
        metric_bundle_scopes.update(
            bundle["bundle_id"]
            for bundle in retired_bundles
            if isinstance(bundle, dict)
            and isinstance(bundle.get("bundle_id"), str)
        )
    parsed_spans: list[dict[str, Any]] = []
    spans_by_id: dict[str, dict[str, Any]] = {}
    active_spans: list[dict[str, Any]] = []
    for index, span in enumerate(spans, start=1):
        label = f"operation metric span {index}"
        if not isinstance(span, dict):
            errors.append(f"{label} must be an object")
            continue
        required_span = {
            "span_id",
            "kind",
            "scope",
            "attempt_id",
            "status",
            "started_at",
        }
        validate_object_keys(
            span,
            required_span
            | {"finished_at", "outcome", "rerun_of", "rerun_reason"},
            required_span,
            label,
            errors,
        )
        span_id = lower_kebab_value(span.get("span_id"), f"{label} `span_id`", errors)
        if span_id is not None:
            if span_id in spans_by_id:
                errors.append(f"operation metric span id `{span_id}` appears more than once")
            else:
                spans_by_id[span_id] = span
        kind = nonempty_string(span.get("kind"))
        if kind not in OPERATION_METRIC_KINDS:
            errors.append(f"{label} has unsupported `kind`")
            kind = None
        scope = single_line_string(span.get("scope"), f"{label} `scope`", errors)
        if kind == "validation" and scope in {"metrics-preterminal", "metrics-final"}:
            errors.append(f"{label} must not instrument a terminal metrics check")
        if kind == "development-review":
            if scope != "selection-readiness" and scope not in metric_bundle_scopes:
                errors.append(
                    f"{label} v4 development-review scope must be `selection-readiness` "
                    "or an active/retired stable bundle_id"
                )
        if kind == "risk-review" and scope not in metric_bundle_scopes:
            errors.append(
                f"{label} v4 risk-review scope must be an active/retired stable "
                "bundle_id"
            )
        attempt_id = lower_kebab_value(
            span.get("attempt_id"), f"{label} `attempt_id`", errors
        )
        span_status = nonempty_string(span.get("status"))
        if span_status not in {"active", "finished"}:
            errors.append(f"{label} `status` must be `active` or `finished`")
        started = rfc3339_value(span.get("started_at"), f"{label} `started_at`", errors)
        finished: datetime | None = None
        if span_status == "active":
            if "finished_at" in span or "outcome" in span:
                errors.append(f"active {label} must omit `finished_at` and `outcome`")
            active_spans.append(span)
        elif span_status == "finished":
            finished = rfc3339_value(
                span.get("finished_at"), f"{label} `finished_at`", errors
            )
            if nonempty_string(span.get("outcome")) not in OPERATION_METRIC_OUTCOMES:
                errors.append(f"finished {label} has unsupported `outcome`")
            if started is not None and finished is not None and finished < started:
                errors.append(f"{label} `finished_at` must not precede `started_at`")

        rerun_of = span.get("rerun_of")
        rerun_reason = span.get("rerun_reason")
        if (rerun_of is None) != (rerun_reason is None):
            errors.append(f"{label} must set `rerun_of` and `rerun_reason` together")
        parsed_rerun = None
        if rerun_of is not None:
            parsed_rerun = lower_kebab_value(
                rerun_of, f"{label} `rerun_of`", errors
            )
            single_line_string(rerun_reason, f"{label} `rerun_reason`", errors)

        if operation_started is not None and started is not None and started < operation_started:
            errors.append(f"{label} starts before the operation")
        if operation_finished is not None:
            if started is not None and started > operation_finished:
                errors.append(f"{label} starts after the operation finished")
            if finished is not None and finished > operation_finished:
                errors.append(f"{label} finishes after the operation")
        parsed_spans.append(
            {
                "span_id": span_id,
                "kind": kind,
                "scope": scope,
                "attempt_id": attempt_id,
                "rerun_of": parsed_rerun,
            }
        )

    seen_ids: set[str] = set()
    for span in parsed_spans:
        span_id = span["span_id"]
        rerun_of = span["rerun_of"]
        if rerun_of is not None:
            prior = spans_by_id.get(rerun_of)
            if rerun_of not in seen_ids or not isinstance(prior, dict):
                errors.append(
                    f"operation metric span `{span_id or '<unknown>'}` `rerun_of` "
                    "must reference an earlier span"
                )
            elif prior.get("kind") != span["kind"] or prior.get("scope") != span["scope"]:
                errors.append(
                    f"operation metric span `{span_id or '<unknown>'}` rerun must keep "
                    "the prior kind and scope"
                )
        if span_id is not None:
            seen_ids.add(span_id)

    if operation_status == "finished" and active_spans:
        errors.append("finished operation metrics must not contain active spans")
    final_validation_spans = [
        span
        for span in spans
        if isinstance(span, dict)
        and span.get("kind") == "validation"
        and span.get("scope") in {"docs", "baseline"}
        and span.get("status") == "finished"
    ]
    latest_final_is_last = bool(
        final_validation_spans
        and spans
        and final_validation_spans[-1] is spans[-1]
    )
    required_final_scope = required_final_validation_scope(state)
    if mode in {"final-validation", "preterminal", "final"}:
        validate_operation_metric_completion_coverage(state, spans, errors)
    if mode == "final-validation":
        if validation_scope != required_final_scope:
            errors.append(
                f"operation requires final `{required_final_scope}` validation, not "
                f"`{validation_scope}`"
            )
        if len(active_spans) != 1:
            errors.append(
                "final docs/baseline validation requires exactly one active validation span"
            )
        elif (
            active_spans[0].get("kind") != "validation"
            or active_spans[0].get("scope") != validation_scope
        ):
            errors.append(
                "final docs/baseline active span must be the current validation phase"
            )
        elif not spans or active_spans[0] is not spans[-1]:
            errors.append("final docs/baseline validation span must be the last recorded span")
    elif mode == "preterminal":
        if active_spans:
            errors.append("metrics preterminal validation requires every span to be finished")
        if not final_validation_spans or final_validation_spans[-1].get("outcome") != "PASS":
            errors.append(
                "metrics preterminal validation requires the latest final validation "
                "span to have outcome `PASS`"
            )
        elif not latest_final_is_last:
            errors.append(
                "metrics preterminal validation requires the latest final validation "
                "span to be the last recorded span"
            )
        if (
            final_validation_spans
            and final_validation_spans[-1].get("scope") != required_final_scope
        ):
            errors.append(
                f"metrics preterminal validation requires final "
                f"`{required_final_scope}` validation"
            )
    elif mode == "final":
        if operation_status != "finished":
            errors.append("metrics final validation requires a finished operation")
        if active_spans:
            errors.append("metrics final validation requires no active spans")
        if not final_validation_spans or final_validation_spans[-1].get("outcome") != "PASS":
            errors.append(
                "metrics final validation requires the latest final validation span "
                "to have outcome `PASS`"
            )
        elif not latest_final_is_last:
            errors.append(
                "metrics final validation requires the latest final validation span "
                "to be the last recorded span"
            )
        if (
            final_validation_spans
            and final_validation_spans[-1].get("scope") != required_final_scope
        ):
            errors.append(
                f"metrics final validation requires final `{required_final_scope}` "
                "validation"
            )


def validate_operation_metric_completion_coverage(
    state: dict[str, Any],
    spans: list[Any],
    errors: list[str],
) -> None:
    successful_spans = [
        span
        for span in spans
        if isinstance(span, dict)
        and span.get("status") == "finished"
        and span.get("outcome") in {"PASS", "completed"}
    ]
    queue = state.get("bundle_queue")
    required_bundle_counts: dict[str, int] = {}
    if isinstance(queue, list):
        for item in queue:
            domain = item.get("domain") if isinstance(item, dict) else None
            if isinstance(domain, str) and domain:
                required_bundle_counts[domain] = required_bundle_counts.get(domain, 0) + 1
    for domain, required_count in sorted(required_bundle_counts.items()):
        bundle_attempts = {
            span.get("attempt_id")
            for span in successful_spans
            if span.get("kind") == "bundle" and span.get("scope") == domain
        }
        writer_attempts = {
            span.get("attempt_id")
            for span in successful_spans
            if span.get("kind") == "writer" and span.get("scope") == domain
        }
        completed_attempts = bundle_attempts & writer_attempts
        if len(completed_attempts) < required_count:
            errors.append(
                f"operation metrics need {required_count} completed bundle/writer "
                f"attempt(s) for queue scope `{domain}`"
            )

    closure = state.get("semantic_review_closure")
    closure_basis = closure.get("basis_revision") if isinstance(closure, dict) else None
    reviews = closure.get("review_passes") if isinstance(closure, dict) else None
    spans_by_id = {
        span.get("span_id"): span
        for span in successful_spans
        if isinstance(span.get("span_id"), str)
    }
    if isinstance(reviews, list) and type(closure_basis) is int:
        for review in reviews:
            if (
                not isinstance(review, dict)
                or review.get("status") != "current"
                or review.get("basis_revision") != closure_basis
            ):
                continue
            review_id = review.get("review_id")
            reviewer_role = review.get("reviewer_role")
            expected_kind = REVIEW_METRIC_KINDS.get(reviewer_role)
            metric = spans_by_id.get(review_id)
            if (
                not isinstance(metric, dict)
                or metric.get("kind") != expected_kind
                or metric.get("scope") != review.get("scope")
                or metric.get("outcome") != "PASS"
            ):
                errors.append(
                    f"current semantic review PASS `{review_id}` at the latest basis "
                    "needs a matching finished operation metric span"
                )

    risk_scope_by_atom = {
        atom_key: bundle.get("bundle_id")
        for bundle in queue or []
        if isinstance(bundle, dict) and isinstance(bundle.get("bundle_id"), str)
        for atom_key in (
            bundle.get("expected_atom_keys")
            if isinstance(bundle.get("expected_atom_keys"), list)
            else []
        )
        if isinstance(atom_key, str)
    }
    risk_scopes = {
        risk_scope_by_atom.get(trigger.get("atom_key"))
        for trigger in state.get("risk_triggers") or []
        if isinstance(trigger, dict)
        and risk_scope_by_atom.get(trigger.get("atom_key")) is not None
    }
    for domain in sorted(risk_scopes):
        if not any(
            span.get("kind") == "risk-review" and span.get("scope") == domain
            for span in successful_spans
        ):
            errors.append(
                f"risk-triggered scope `{domain}` needs a finished risk-review metric span"
            )


def rfc3339_value(value: Any, label: str, errors: list[str]) -> datetime | None:
    text = single_line_string(value, label, errors)
    if text is None:
        return None
    if not RFC3339_RE.fullmatch(text):
        errors.append(f"{label} must be RFC 3339 with a timezone")
        return None
    normalized = text[:-1] + "+00:00" if text[-1] in {"Z", "z"} else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{label} must be RFC 3339 with a timezone")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{label} must be RFC 3339 with a timezone")
        return None
    return parsed


def validate_semantic_review_closure(
    state: dict[str, Any],
    errors: list[str],
    *,
    require_final: bool,
    required_final_role: str | None,
) -> None:
    selection = state.get("context_selection")
    selection_version = selection.get("version") if isinstance(selection, dict) else None
    if selection_version != "4":
        errors.append(
            "work-state `semantic_review_closure` requires "
            "`context_selection.version` exact `4`"
        )
        return
    if "semantic_review_closure" not in state:
        errors.append("v4 work-state must contain `semantic_review_closure`")
        return
    closure = state["semantic_review_closure"]
    if not isinstance(closure, dict):
        errors.append("work-state `semantic_review_closure` must be an object")
        return
    validate_object_keys(
        closure,
        {"version", "basis_revision", "review_passes", "invalidations", "final_gate"},
        {"version", "basis_revision", "review_passes", "invalidations", "final_gate"},
        "semantic review closure",
        errors,
    )
    if closure.get("version") != "1":
        errors.append("semantic review closure `version` must be `1`")
    basis_revision = positive_integer(
        closure.get("basis_revision"),
        "semantic review closure `basis_revision`",
        errors,
    )
    bundle_scopes = semantic_review_bundle_scopes(state, errors)

    review_passes = closure.get("review_passes")
    if not isinstance(review_passes, list):
        errors.append("semantic review closure `review_passes` must be a list")
        review_passes = []
    passes_by_id: dict[str, dict[str, Any]] = {}
    current_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for index, review in enumerate(review_passes, start=1):
        label = f"semantic review pass {index}"
        if not isinstance(review, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            review,
            {
                "review_id",
                "reviewer_role",
                "scope",
                "basis_revision",
                "verdict",
                "status",
            },
            {
                "review_id",
                "reviewer_role",
                "scope",
                "basis_revision",
                "verdict",
                "status",
            },
            label,
            errors,
        )
        review_id = lower_kebab_value(
            review.get("review_id"), f"{label} `review_id`", errors
        )
        if review_id is not None:
            if review_id in passes_by_id:
                errors.append(f"semantic review id `{review_id}` appears more than once")
            else:
                passes_by_id[review_id] = review
        role = review.get("reviewer_role")
        if role not in SEMANTIC_REVIEW_ROLES:
            errors.append(
                f"{label} `reviewer_role` must be development, risk, integration, or baseline"
            )
            role = None
        scope = single_line_string(review.get("scope"), f"{label} `scope`", errors)
        validate_semantic_review_scope(
            role,
            scope,
            bundle_scopes,
            label,
            errors,
        )
        revision = positive_integer(
            review.get("basis_revision"), f"{label} `basis_revision`", errors
        )
        if revision is not None and basis_revision is not None and revision > basis_revision:
            errors.append(f"{label} basis revision exceeds the current semantic basis")
        if review.get("verdict") != "PASS":
            errors.append(f"{label} `verdict` must be exact `PASS`")
        status = review.get("status")
        if status not in SEMANTIC_REVIEW_STATUSES:
            errors.append(f"{label} `status` must be current, stale, or superseded")
        if status == "current" and role is not None and scope is not None:
            pair = (role, scope)
            if pair in current_by_pair:
                errors.append(
                    f"semantic review role/scope `{role}`/`{scope}` has more than one current PASS"
                )
            else:
                current_by_pair[pair] = review

    invalidations = closure.get("invalidations")
    if not isinstance(invalidations, list):
        errors.append("semantic review closure `invalidations` must be a list")
        invalidations = []
    invalidation_ids: set[str] = set()
    referenced_prior_passes: dict[str, str] = {}
    parsed_invalidations: list[dict[str, Any]] = []
    for index, invalidation in enumerate(invalidations, start=1):
        label = f"semantic invalidation {index}"
        if not isinstance(invalidation, dict):
            errors.append(f"{label} must be an object")
            continue
        status = invalidation.get("status")
        required_fields = {
            "invalidation_id",
            "trigger",
            "cause",
            "opened_revision",
            "affected_artifacts",
            "affected_bundles",
            "stale_review_ids",
            "required_reviews",
            "status",
        }
        if status == "resolved":
            required_fields.add("resolved_revision")
        validate_object_keys(
            invalidation,
            required_fields | {"resolved_revision"},
            required_fields,
            label,
            errors,
        )
        invalidation_id = lower_kebab_value(
            invalidation.get("invalidation_id"),
            f"{label} `invalidation_id`",
            errors,
        )
        if invalidation_id is not None:
            if invalidation_id in invalidation_ids:
                errors.append(
                    f"semantic invalidation id `{invalidation_id}` appears more than once"
                )
            invalidation_ids.add(invalidation_id)
        if invalidation.get("trigger") not in SEMANTIC_INVALIDATION_TRIGGERS:
            errors.append(f"{label} has unsupported semantic invalidation trigger")
        single_line_string(invalidation.get("cause"), f"{label} `cause`", errors)
        opened_revision = positive_integer(
            invalidation.get("opened_revision"),
            f"{label} `opened_revision`",
            errors,
        )
        if (
            opened_revision is not None
            and basis_revision is not None
            and opened_revision > basis_revision
        ):
            errors.append(f"{label} opened revision exceeds the current semantic basis")

        validate_semantic_affected_artifacts(
            invalidation.get("affected_artifacts"), label, errors
        )
        affected_bundles = string_list(
            invalidation.get("affected_bundles"),
            f"{label} `affected_bundles`",
            errors,
        )
        if not affected_bundles:
            errors.append(f"{label} must affect at least one bundle")
        if len(affected_bundles) != len(set(affected_bundles)):
            errors.append(f"{label} repeats an affected bundle")
        for bundle in affected_bundles:
            if bundle not in bundle_scopes:
                errors.append(
                    f"{label} affected bundle `{bundle}` does not resolve to a v4 "
                    "`bundle_queue.bundle_id`"
                )

        stale_review_ids = string_list(
            invalidation.get("stale_review_ids"),
            f"{label} `stale_review_ids`",
            errors,
        )
        if not stale_review_ids:
            errors.append(f"{label} must name at least one prior PASS made stale")
        if len(stale_review_ids) != len(set(stale_review_ids)):
            errors.append(f"{label} repeats a stale review id")
        for review_id in stale_review_ids:
            previous = referenced_prior_passes.get(review_id)
            if previous is not None:
                errors.append(
                    f"semantic review id `{review_id}` is stale in more than one invalidation"
                )
            elif invalidation_id is not None:
                referenced_prior_passes[review_id] = invalidation_id

        required_reviews = invalidation.get("required_reviews")
        if not isinstance(required_reviews, list):
            errors.append(f"{label} `required_reviews` must be a list")
            required_reviews = []
        required_pairs: set[tuple[str, str]] = set()
        for review_index, required_review in enumerate(required_reviews, start=1):
            review_label = f"{label} required review {review_index}"
            if not isinstance(required_review, dict):
                errors.append(f"{review_label} must be an object")
                continue
            validate_object_keys(
                required_review,
                {"reviewer_role", "scope"},
                {"reviewer_role", "scope"},
                review_label,
                errors,
            )
            role = required_review.get("reviewer_role")
            if role not in SEMANTIC_REVIEW_ROLES:
                errors.append(f"{review_label} has unsupported reviewer role")
                continue
            scope = single_line_string(
                required_review.get("scope"), f"{review_label} `scope`", errors
            )
            if scope is None:
                continue
            validate_semantic_review_scope(
                role,
                scope,
                bundle_scopes,
                review_label,
                errors,
            )
            if role in {"development", "risk"} and scope not in affected_bundles:
                errors.append(
                    f"{review_label} scope `{scope}` is not an affected bundle"
                )
            pair = (role, scope)
            if pair in required_pairs:
                errors.append(
                    f"{label} repeats required review `{role}`/`{scope}`"
                )
            required_pairs.add(pair)
        if not required_pairs:
            errors.append(f"{label} must require at least one semantic review")
        for review_id in stale_review_ids:
            stale_review = passes_by_id.get(review_id)
            if not isinstance(stale_review, dict):
                continue
            stale_role = stale_review.get("reviewer_role")
            stale_scope = stale_review.get("scope")
            if (
                stale_role in {"development", "risk"}
                and isinstance(stale_scope, str)
                and (stale_role, stale_scope) not in required_pairs
            ):
                errors.append(
                    f"{label} stale v4 PASS `{review_id}` must include exact "
                    f"required review `{stale_role}`/`{stale_scope}`"
                )

        if status not in {"open", "resolved"}:
            errors.append(f"{label} `status` must be `open` or `resolved`")
        resolved_revision = None
        if status == "open" and "resolved_revision" in invalidation:
            errors.append(f"{label} with status `open` must not set `resolved_revision`")
        if status == "resolved":
            resolved_revision = positive_integer(
                invalidation.get("resolved_revision"),
                f"{label} `resolved_revision`",
                errors,
            )
            if (
                resolved_revision is not None
                and opened_revision is not None
                and resolved_revision < opened_revision
            ):
                errors.append(f"{label} resolved revision precedes its opened revision")
            if (
                resolved_revision is not None
                and basis_revision is not None
                and resolved_revision > basis_revision
            ):
                errors.append(f"{label} resolved revision exceeds the current semantic basis")
        parsed_invalidations.append(
            {
                "label": label,
                "status": status,
                "opened_revision": opened_revision,
                "resolved_revision": resolved_revision,
                "stale_review_ids": stale_review_ids,
                "required_pairs": required_pairs,
            }
        )

    open_prior_ids: set[str] = set()
    resolved_prior_ids: set[str] = set()
    for invalidation in parsed_invalidations:
        expected_status = "stale" if invalidation["status"] == "open" else "superseded"
        target_set = open_prior_ids if invalidation["status"] == "open" else resolved_prior_ids
        for review_id in invalidation["stale_review_ids"]:
            target_set.add(review_id)
            review = passes_by_id.get(review_id)
            if review is None:
                errors.append(
                    f"{invalidation['label']} references unknown semantic review id `{review_id}`"
                )
                continue
            if review.get("status") != expected_status:
                errors.append(
                    f"{invalidation['label']} prior PASS `{review_id}` must be `{expected_status}`"
                )
            review_revision = review.get("basis_revision")
            opened_revision = invalidation["opened_revision"]
            if (
                type(review_revision) is int
                and opened_revision is not None
                and review_revision >= opened_revision
            ):
                errors.append(
                    f"{invalidation['label']} prior PASS `{review_id}` must predate its opened revision"
                )
        resolved_revision = invalidation["resolved_revision"]
        if invalidation["status"] == "resolved" and resolved_revision is not None:
            for pair in invalidation["required_pairs"]:
                review = current_by_pair.get(pair)
                if review is None or review.get("basis_revision", 0) < resolved_revision:
                    errors.append(
                        f"{invalidation['label']} is missing current PASS for "
                        f"`{pair[0]}`/`{pair[1]}` at its resolved basis"
                    )

    for review_id, review in passes_by_id.items():
        if review.get("status") == "stale" and review_id not in open_prior_ids:
            errors.append(f"stale semantic review `{review_id}` has no open invalidation")
        if review.get("status") == "superseded" and review_id not in resolved_prior_ids:
            errors.append(
                f"superseded semantic review `{review_id}` has no resolved invalidation"
            )

    final_gate = closure.get("final_gate")
    if not isinstance(final_gate, dict):
        errors.append("semantic review closure `final_gate` must be an object")
        final_gate = {}
    else:
        validate_object_keys(
            final_gate,
            {"required", "review_id", "review_history"},
            {"required", "review_history"},
            "semantic review final gate",
            errors,
        )
    final_required = final_gate.get("required")
    if type(final_required) is not bool:
        errors.append("semantic review final gate `required` must be boolean")
        final_required = False
    final_review_id = nonempty_string(final_gate.get("review_id"))
    if "review_id" in final_gate and final_review_id is None:
        errors.append("semantic review final gate `review_id` must be non-empty")
    if not final_required and "review_id" in final_gate:
        errors.append("semantic review final gate must omit `review_id` when not required")
    final_history = string_list(
        final_gate.get("review_history"),
        "semantic review final gate `review_history`",
        errors,
    )
    if len(final_history) != len(set(final_history)):
        errors.append("semantic review final gate repeats a review history id")
    history_revisions: list[int] = []
    for review_id in final_history:
        review = passes_by_id.get(review_id)
        if review is None:
            errors.append(
                f"semantic review final gate history references unknown review `{review_id}`"
            )
            continue
        if review.get("reviewer_role") not in {"integration", "baseline"}:
            errors.append(
                f"semantic review final gate history `{review_id}` must reference "
                "an integration/baseline PASS"
            )
        revision = review.get("basis_revision")
        if type(revision) is int:
            history_revisions.append(revision)
    if history_revisions != sorted(history_revisions):
        errors.append("semantic review final gate history must follow basis revision order")
    if not final_required and final_history:
        errors.append("semantic review final gate history must be empty when not required")
    if final_review_id is not None and (
        not final_history or final_history[-1] != final_review_id
    ):
        errors.append(
            "semantic review final gate `review_id` must equal the latest review history id"
        )
    if final_review_id is not None:
        review = passes_by_id.get(final_review_id)
        if review is None:
            errors.append(
                f"semantic review final gate references unknown review `{final_review_id}`"
            )
        elif (
            review.get("status") != "current"
            or review.get("reviewer_role") not in {"integration", "baseline"}
            or review.get("basis_revision") != basis_revision
        ):
            errors.append(
                "semantic review final gate must reference a current integration/baseline PASS "
                "at the latest basis revision"
            )
    elif final_history:
        latest_review = passes_by_id.get(final_history[-1])
        if latest_review is not None and latest_review.get("status") == "current":
            errors.append(
                "semantic review final gate must point to its latest current history PASS"
            )

    if require_final:
        for invalidation in parsed_invalidations:
            if invalidation["status"] == "open":
                errors.append(f"{invalidation['label']} is still open at final validation")
        for review_id, review in passes_by_id.items():
            if review.get("status") == "stale":
                errors.append(f"semantic review `{review_id}` is still stale at final validation")
        if final_required and final_review_id is None:
            errors.append("semantic review final gate requires a recorded final PASS")
        if required_final_role is not None:
            if final_required is not True:
                errors.append(
                    f"semantic review final gate must be required for `{required_final_role}` validation"
                )
            if final_review_id is not None:
                review = passes_by_id.get(final_review_id)
                if (
                    review is None
                    or review.get("reviewer_role") != required_final_role
                    or review.get("scope") != "project-wide"
                ):
                    errors.append(
                        f"semantic review final gate must reference a current "
                        f"`{required_final_role}`/`project-wide` PASS"
                    )


def semantic_review_bundle_scopes(
    state: dict[str, Any], errors: list[str]
) -> set[str]:
    queue = state.get("bundle_queue")
    if not isinstance(queue, list):
        errors.append(
            "v4 semantic review closure requires work-state `bundle_queue` as a list"
        )
        return set()
    bundle_ids: set[str] = set()
    for index, bundle in enumerate(queue, start=1):
        if not isinstance(bundle, dict):
            continue
        bundle_id = single_line_string(
            bundle.get("bundle_id"),
            f"v4 semantic review bundle item {index} `bundle_id`",
            errors,
        )
        if bundle_id is not None:
            bundle_ids.add(bundle_id)
    registry = state.get("selection_retirements")
    retired = registry.get("retired_bundles") if isinstance(registry, dict) else None
    if isinstance(retired, list):
        for bundle in retired:
            if isinstance(bundle, dict) and isinstance(bundle.get("bundle_id"), str):
                bundle_ids.add(bundle["bundle_id"])
    return bundle_ids


def validate_semantic_review_scope(
    role: Any,
    scope: str | None,
    bundle_scopes: set[str],
    label: str,
    errors: list[str],
) -> None:
    if scope is None or role not in SEMANTIC_REVIEW_ROLES:
        return
    if role in {"development", "risk"} and scope not in bundle_scopes:
        errors.append(
            f"{label} scope `{scope}` does not resolve to a v4 "
            "`bundle_queue.bundle_id`"
        )
    if role == "integration" and scope not in {"affected-closure", "project-wide"}:
        errors.append(
            f"{label} integration scope must be `affected-closure` or `project-wide`"
        )
    if role == "baseline" and scope != "project-wide":
        errors.append(f"{label} baseline scope must be `project-wide`")


def validate_semantic_affected_artifacts(
    value: Any, label: str, errors: list[str]
) -> None:
    if not isinstance(value, list):
        errors.append(f"{label} `affected_artifacts` must be a list")
        return
    if not value:
        errors.append(f"{label} must affect at least one artifact")
    identities: set[tuple[str, str]] = set()
    for index, artifact in enumerate(value, start=1):
        artifact_label = f"{label} affected artifact {index}"
        if not isinstance(artifact, dict):
            errors.append(f"{artifact_label} must be an object")
            continue
        validate_object_keys(
            artifact,
            {"location", "path"},
            {"location", "path"},
            artifact_label,
            errors,
        )
        location = artifact.get("location")
        if location not in {"managed-docs", "request"}:
            errors.append(f"{artifact_label} has unsupported location")
            continue
        path_text = single_line_string(
            artifact.get("path"), f"{artifact_label} `path`", errors
        )
        path = safe_relative(path_text) if path_text is not None else None
        if path is None or path == Path("."):
            errors.append(f"{artifact_label} path must be a safe relative path")
            continue
        normalized = path.as_posix()
        if location == "request" and normalized == "work-state.json":
            errors.append(f"{artifact_label} must not reference work-state.json itself")
        identity = (location, normalized)
        if identity in identities:
            errors.append(f"{label} repeats affected artifact `{location}:{normalized}`")
        identities.add(identity)


def positive_integer(value: Any, label: str, errors: list[str]) -> int | None:
    if type(value) is not int or value < 1:
        errors.append(f"{label} must be a positive integer")
        return None
    return value


def single_line_string(value: Any, label: str, errors: list[str]) -> str | None:
    text = nonempty_string(value)
    if text is None or "\n" in text or "\r" in text:
        errors.append(f"{label} must be a non-empty single-line string")
        return None
    return text


def validate_selection_queue(
    value: Any,
    accepted_domains: set[str],
    planned_key_domains: dict[str, str],
    errors: list[str],
) -> set[str]:
    if not isinstance(value, list):
        errors.append("work-state `bundle_queue` must be a list")
        return set()
    queue_keys: set[str] = set()
    for index, bundle in enumerate(value, start=1):
        label = f"bundle queue item {index}"
        if not isinstance(bundle, dict):
            errors.append(f"{label} must be an object")
            continue
        domain = nonempty_string(bundle.get("domain"))
        if domain is None:
            errors.append(f"{label} must include non-empty `domain`")
        elif domain not in accepted_domains:
            errors.append(f"{label} domain `{domain}` is outside `accepted_scope`")
        keys = atom_key_list(
            bundle.get("expected_atom_keys", []), label, errors, "expected_atom_keys"
        )
        if not keys:
            errors.append(f"{label} must include at least one expected atom key")
        for key in keys:
            if key in queue_keys:
                errors.append(f"bundle queue atom key `{key}` appears more than once")
            queue_keys.add(key)
            owner_domain = planned_key_domains.get(key)
            if domain is not None and owner_domain is not None and domain != owner_domain:
                errors.append(
                    f"bundle queue atom key `{key}` belongs to domain `{owner_domain}`, not `{domain}`"
                )
    return queue_keys


def validate_selection_risk_triggers(
    value: Any,
    candidate_targets: dict[str, set[str]],
    candidate_dispositions: dict[str, str],
    errors: list[str],
) -> set[str]:
    risk_keys: set[str] = set()
    if not isinstance(value, list):
        errors.append("work-state `risk_triggers` must be a list")
        return risk_keys
    for index, item in enumerate(value, start=1):
        label = f"risk trigger {index}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        candidate_id = nonempty_string(item.get("candidate_id"))
        if candidate_id is None or not ATOM_KEY_RE.fullmatch(candidate_id):
            errors.append(f"{label} must include lower-kebab-case `candidate_id`")
        elif candidate_id not in candidate_targets:
            errors.append(f"{label} candidate_id `{candidate_id}` does not resolve")
        elif candidate_dispositions.get(candidate_id) == "drop":
            errors.append(f"{label} must not reference dropped candidate `{candidate_id}`")

        atom_key = nonempty_string(item.get("atom_key"))
        if atom_key is None or not ATOM_KEY_RE.fullmatch(atom_key):
            errors.append(f"{label} must include lower-kebab-case `atom_key`")
        elif candidate_id in candidate_targets and atom_key not in candidate_targets[candidate_id]:
            errors.append(
                f"{label} atom_key `{atom_key}` is not the output or merge target of "
                f"candidate `{candidate_id}`"
            )
        else:
            risk_keys.add(atom_key)
        triggers = string_list(item.get("triggers"), f"{label} `triggers`", errors)
        if not triggers:
            errors.append(f"{label} must include at least one trigger")
        if nonempty_string(item.get("basis")) is None:
            errors.append(f"{label} must include non-empty `basis`")
    return risk_keys


def validate_owner_readiness_v4(
    state: dict[str, Any],
    candidate_targets: dict[str, set[str]],
    candidate_dispositions: dict[str, str],
    candidate_domains: dict[str, str],
    errors: list[str],
    *,
    require_final: bool,
) -> None:
    """Validate v4 references and lifecycle without judging semantic correctness."""
    queue = state.get("bundle_queue")
    bundles_by_id: dict[str, dict[str, Any]] = {}
    bundle_dependencies: dict[str, set[str]] = {}
    atom_bundles: dict[str, str] = {}
    if isinstance(queue, list):
        for index, bundle in enumerate(queue, start=1):
            label = f"v4 bundle queue item {index}"
            if not isinstance(bundle, dict):
                continue
            validate_object_keys(
                bundle,
                {"bundle_id", "domain", "expected_atom_keys", "depends_on_contract_ids"},
                {"bundle_id", "domain", "expected_atom_keys", "depends_on_contract_ids"},
                label,
                errors,
            )
            bundle_id = lower_kebab_value(
                bundle.get("bundle_id"), f"{label} `bundle_id`", errors
            )
            if bundle_id is not None:
                if bundle_id in bundles_by_id:
                    errors.append(f"v4 bundle id `{bundle_id}` appears more than once")
                else:
                    bundles_by_id[bundle_id] = bundle
            dependencies = string_list(
                bundle.get("depends_on_contract_ids"),
                f"{label} `depends_on_contract_ids`",
                errors,
            )
            if len(dependencies) != len(set(dependencies)):
                errors.append(f"{label} repeats a shared contract dependency")
            atom_keys = atom_key_list(
                bundle.get("expected_atom_keys"), label, errors, "expected_atom_keys"
            )
            if bundle_id is not None:
                bundle_dependencies[bundle_id] = set(dependencies)
            for atom_key in atom_keys:
                if bundle_id is not None:
                    atom_bundles[atom_key] = bundle_id
    else:
        errors.append("v4 owner readiness requires `bundle_queue` as a list")

    contracts = state.get("shared_contracts")
    contracts_by_id: dict[str, dict[str, Any]] = {}
    contract_consumers: dict[str, set[str]] = {}
    contract_consumer_bundles: dict[str, set[str]] = {}
    if not isinstance(contracts, list):
        errors.append("v4 work-state `shared_contracts` must be a list")
        contracts = []
    for index, contract in enumerate(contracts, start=1):
        label = f"shared contract {index}"
        if not isinstance(contract, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            contract,
            {
                "contract_id",
                "kind",
                "owner_candidate_id",
                "owner_atom_key",
                "direct_consumer_candidate_ids",
                "evidence_routes",
                "owner_bundle_id",
                "consumer_bundle_ids",
            },
            {
                "contract_id",
                "kind",
                "owner_candidate_id",
                "owner_atom_key",
                "direct_consumer_candidate_ids",
                "evidence_routes",
                "owner_bundle_id",
                "consumer_bundle_ids",
            },
            label,
            errors,
        )
        contract_id = lower_kebab_value(
            contract.get("contract_id"), f"{label} `contract_id`", errors
        )
        if contract_id is not None:
            if contract_id in contracts_by_id:
                errors.append(f"shared contract id `{contract_id}` appears more than once")
            else:
                contracts_by_id[contract_id] = contract
        contract_kind = nonempty_string(contract.get("kind"))
        if contract_kind not in SHARED_CONTRACT_KINDS:
            errors.append(f"{label} has unsupported `kind`")
        owner_candidate_id = lower_kebab_value(
            contract.get("owner_candidate_id"),
            f"{label} `owner_candidate_id`",
            errors,
        )
        owner_atom_key = lower_kebab_value(
            contract.get("owner_atom_key"), f"{label} `owner_atom_key`", errors
        )
        if owner_candidate_id not in candidate_targets:
            errors.append(f"{label} owner candidate does not resolve")
        elif candidate_dispositions.get(owner_candidate_id) == "drop":
            errors.append(f"{label} owner candidate must not be dropped")
        elif owner_atom_key not in candidate_targets.get(owner_candidate_id, set()):
            errors.append(f"{label} owner atom is not produced by its owner candidate")
        owner_bundle_id = lower_kebab_value(
            contract.get("owner_bundle_id"), f"{label} `owner_bundle_id`", errors
        )
        if owner_bundle_id not in bundles_by_id:
            errors.append(f"{label} owner bundle does not resolve")
        elif atom_bundles.get(owner_atom_key or "") != owner_bundle_id:
            errors.append(f"{label} owner atom is not queued by its owner bundle")

        consumers = string_list(
            contract.get("direct_consumer_candidate_ids"),
            f"{label} `direct_consumer_candidate_ids`",
            errors,
        )
        if not consumers:
            errors.append(f"{label} must name at least one direct consumer candidate")
        if len(consumers) != len(set(consumers)):
            errors.append(f"{label} repeats a direct consumer candidate")
        for candidate_id in consumers:
            if candidate_id == owner_candidate_id:
                errors.append(f"{label} owner candidate cannot also be a direct consumer")
            elif candidate_id not in candidate_targets:
                errors.append(f"{label} direct consumer `{candidate_id}` does not resolve")
            elif candidate_dispositions.get(candidate_id) == "drop":
                errors.append(f"{label} direct consumer `{candidate_id}` is dropped")

        evidence_routes = string_list(
            contract.get("evidence_routes"), f"{label} `evidence_routes`", errors
        )
        if not evidence_routes:
            errors.append(f"{label} must include at least one evidence route")
        if any("\n" in route or "\r" in route for route in evidence_routes):
            errors.append(f"{label} evidence routes must be single-line strings")
        consumer_bundle_ids = string_list(
            contract.get("consumer_bundle_ids"),
            f"{label} `consumer_bundle_ids`",
            errors,
        )
        if not consumer_bundle_ids:
            errors.append(f"{label} must name at least one consumer bundle")
        if len(consumer_bundle_ids) != len(set(consumer_bundle_ids)):
            errors.append(f"{label} repeats a consumer bundle")
        if contract_id is not None:
            contract_consumers[contract_id] = set(consumers)
            contract_consumer_bundles[contract_id] = set(consumer_bundle_ids)
        queue_positions = {bundle_id: index for index, bundle_id in enumerate(bundles_by_id)}
        expected_consumer_bundles: set[str] = set()
        for candidate_id in consumers:
            for atom_key in candidate_targets.get(candidate_id, set()):
                bundle_id = atom_bundles.get(atom_key)
                if bundle_id is not None:
                    expected_consumer_bundles.add(bundle_id)
        if set(consumer_bundle_ids) != expected_consumer_bundles:
            errors.append(
                f"{label} consumer bundles must exactly cover direct consumer candidates"
            )
        for bundle_id in consumer_bundle_ids:
            bundle = bundles_by_id.get(bundle_id)
            if bundle is None:
                errors.append(f"{label} consumer bundle `{bundle_id}` does not resolve")
                continue
            if contract_id not in bundle_dependencies.get(bundle_id, set()):
                errors.append(
                    f"{label} consumer bundle `{bundle_id}` is missing its contract dependency"
                )
            if (
                owner_bundle_id in queue_positions
                and bundle_id in queue_positions
                and queue_positions[owner_bundle_id] >= queue_positions[bundle_id]
            ):
                errors.append(
                    f"{label} owner bundle must precede consumer bundle `{bundle_id}`"
                )

    retired_bundles, retired_contracts = validate_selection_retirements_v4(
        state,
        bundles_by_id,
        contracts_by_id,
        errors,
    )
    validate_v4_retirement_history_obligations(
        state,
        retired_bundles,
        retired_contracts,
        errors,
    )

    referenced_contract_ids: set[str] = set()
    routed_candidates_by_contract: dict[str, set[str]] = {}
    risks = state.get("risk_triggers")
    if isinstance(risks, list):
        for index, risk in enumerate(risks, start=1):
            label = f"v4 risk trigger {index}"
            if not isinstance(risk, dict):
                continue
            validate_object_keys(
                risk,
                {
                    "candidate_id",
                    "atom_key",
                    "triggers",
                    "basis",
                    "route",
                    "shared_contract_id",
                },
                {"candidate_id", "atom_key", "triggers", "basis", "route"},
                label,
                errors,
            )
            route = risk.get("route")
            contract_id = nonempty_string(risk.get("shared_contract_id"))
            if route == "local":
                if "shared_contract_id" in risk:
                    errors.append(f"{label} local route must omit `shared_contract_id`")
            elif route == "shared-contract":
                if contract_id is None:
                    errors.append(f"{label} shared route needs `shared_contract_id`")
                elif contract_id not in contracts_by_id:
                    errors.append(
                        f"{label} shared_contract_id `{contract_id}` does not resolve"
                    )
                else:
                    referenced_contract_ids.add(contract_id)
                    candidate_id = nonempty_string(risk.get("candidate_id"))
                    if candidate_id is not None:
                        routed_candidates_by_contract.setdefault(contract_id, set()).add(
                            candidate_id
                        )
                    contract = contracts_by_id[contract_id]
                    owner_candidate = nonempty_string(
                        contract.get("owner_candidate_id")
                    )
                    allowed_candidates = set(
                        contract_consumers.get(contract_id, set())
                    )
                    if owner_candidate is not None:
                        allowed_candidates.add(owner_candidate)
                    if candidate_id not in allowed_candidates:
                        errors.append(
                            f"{label} candidate is not the owner or a direct consumer of "
                            f"shared contract `{contract_id}`"
                        )
            else:
                errors.append(f"{label} `route` must be `local` or `shared-contract`")
    for contract_id in sorted(set(contracts_by_id) - referenced_contract_ids):
        errors.append(f"shared contract `{contract_id}` is orphaned from risk routing")
    for contract_id, contract in contracts_by_id.items():
        required_routes = set(contract_consumers.get(contract_id, set()))
        owner_candidate = nonempty_string(contract.get("owner_candidate_id"))
        if owner_candidate is not None:
            required_routes.add(owner_candidate)
        missing_candidates = required_routes - (
            routed_candidates_by_contract.get(contract_id, set())
        )
        for candidate_id in sorted(
            value for value in missing_candidates if isinstance(value, str)
        ):
            errors.append(
                f"shared contract `{contract_id}` candidate `{candidate_id}` is missing "
                "its shared risk route"
            )
    for bundle_id in bundles_by_id:
        for contract_id in bundle_dependencies.get(bundle_id, set()):
            contract = contracts_by_id.get(contract_id)
            if contract is None:
                errors.append(
                    f"v4 bundle `{bundle_id}` dependency `{contract_id}` does not resolve"
                )
            elif bundle_id not in contract_consumer_bundles.get(contract_id, set()):
                errors.append(
                    f"v4 bundle `{bundle_id}` has unrelated dependency `{contract_id}`"
                )

    readiness = validate_selection_readiness_v4(state, errors)
    validate_late_discovery_and_diagnostics_v4(
        state,
        {**retired_contracts, **contracts_by_id},
        {**retired_bundles, **bundles_by_id},
        candidate_dispositions,
        readiness,
        errors,
        require_final=require_final,
    )


def validate_selection_retirements_v4(
    state: dict[str, Any],
    active_bundles: dict[str, dict[str, Any]],
    active_contracts: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    registry = state.get("selection_retirements")
    retired_bundles: dict[str, dict[str, Any]] = {}
    retired_contracts: dict[str, dict[str, Any]] = {}
    if not isinstance(registry, dict):
        errors.append("v4 work-state `selection_retirements` must be an object")
        return retired_bundles, retired_contracts
    validate_object_keys(
        registry,
        {"version", "retired_bundles", "retired_contracts"},
        {"version", "retired_bundles", "retired_contracts"},
        "selection retirements",
        errors,
    )
    if registry.get("version") != "1":
        errors.append("selection retirements `version` must be `1`")

    raw_bundles = registry.get("retired_bundles")
    bundle_revisions: list[int] = []
    if not isinstance(raw_bundles, list):
        errors.append("selection retirements `retired_bundles` must be a list")
        raw_bundles = []
    bundle_fields = {
        "bundle_id",
        "domain",
        "expected_atom_keys",
        "depends_on_contract_ids",
        "retired_basis_revision",
        "reason",
    }
    for index, bundle in enumerate(raw_bundles, start=1):
        label = f"retired bundle {index}"
        if not isinstance(bundle, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(bundle, bundle_fields, bundle_fields, label, errors)
        bundle_id = lower_kebab_value(
            bundle.get("bundle_id"), f"{label} `bundle_id`", errors
        )
        if bundle_id is not None:
            if bundle_id in retired_bundles:
                errors.append(f"retired bundle id `{bundle_id}` appears more than once")
            else:
                retired_bundles[bundle_id] = bundle
            if bundle_id in active_bundles:
                errors.append(f"v4 bundle id `{bundle_id}` cannot be active and retired")
        single_line_string(bundle.get("domain"), f"{label} `domain`", errors)
        atom_keys = atom_key_list(
            bundle.get("expected_atom_keys"), label, errors, "expected_atom_keys"
        )
        if not atom_keys:
            errors.append(f"{label} must retain at least one expected atom key")
        dependencies = string_list(
            bundle.get("depends_on_contract_ids"),
            f"{label} `depends_on_contract_ids`",
            errors,
        )
        if len(dependencies) != len(set(dependencies)):
            errors.append(f"{label} repeats a shared contract dependency")
        revision = positive_integer(
            bundle.get("retired_basis_revision"),
            f"{label} `retired_basis_revision`",
            errors,
        )
        if revision is not None:
            bundle_revisions.append(revision)
        single_line_string(bundle.get("reason"), f"{label} `reason`", errors)
    if bundle_revisions != sorted(bundle_revisions):
        errors.append("retired bundles must follow retirement basis revision order")

    raw_contracts = registry.get("retired_contracts")
    contract_revisions: list[int] = []
    if not isinstance(raw_contracts, list):
        errors.append("selection retirements `retired_contracts` must be a list")
        raw_contracts = []
    contract_fields = {
        "contract_id",
        "kind",
        "owner_candidate_id",
        "owner_atom_key",
        "direct_consumer_candidate_ids",
        "evidence_routes",
        "owner_bundle_id",
        "consumer_bundle_ids",
        "retired_basis_revision",
        "reason",
    }
    for index, contract in enumerate(raw_contracts, start=1):
        label = f"retired shared contract {index}"
        if not isinstance(contract, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(contract, contract_fields, contract_fields, label, errors)
        contract_id = lower_kebab_value(
            contract.get("contract_id"), f"{label} `contract_id`", errors
        )
        if contract_id is not None:
            if contract_id in retired_contracts:
                errors.append(
                    f"retired shared contract id `{contract_id}` appears more than once"
                )
            else:
                retired_contracts[contract_id] = contract
            if contract_id in active_contracts:
                errors.append(
                    f"shared contract id `{contract_id}` cannot be active and retired"
                )
        if contract.get("kind") not in SHARED_CONTRACT_KINDS:
            errors.append(f"{label} has unsupported `kind`")
        lower_kebab_value(
            contract.get("owner_candidate_id"),
            f"{label} `owner_candidate_id`",
            errors,
        )
        lower_kebab_value(
            contract.get("owner_atom_key"), f"{label} `owner_atom_key`", errors
        )
        consumers = string_list(
            contract.get("direct_consumer_candidate_ids"),
            f"{label} `direct_consumer_candidate_ids`",
            errors,
        )
        if not consumers:
            errors.append(f"{label} must retain direct consumer candidates")
        if len(consumers) != len(set(consumers)):
            errors.append(f"{label} repeats a direct consumer candidate")
        evidence = string_list(
            contract.get("evidence_routes"), f"{label} `evidence_routes`", errors
        )
        if not evidence:
            errors.append(f"{label} must retain evidence routes")
        if any("\n" in route or "\r" in route for route in evidence):
            errors.append(f"{label} evidence routes must be single-line strings")
        lower_kebab_value(
            contract.get("owner_bundle_id"),
            f"{label} `owner_bundle_id`",
            errors,
        )
        consumer_bundle_ids = string_list(
            contract.get("consumer_bundle_ids"),
            f"{label} `consumer_bundle_ids`",
            errors,
        )
        if not consumer_bundle_ids:
            errors.append(f"{label} must retain consumer bundles")
        if len(consumer_bundle_ids) != len(set(consumer_bundle_ids)):
            errors.append(f"{label} repeats a consumer bundle")
        revision = positive_integer(
            contract.get("retired_basis_revision"),
            f"{label} `retired_basis_revision`",
            errors,
        )
        if revision is not None:
            contract_revisions.append(revision)
        single_line_string(contract.get("reason"), f"{label} `reason`", errors)
    if contract_revisions != sorted(contract_revisions):
        errors.append("retired shared contracts must follow retirement basis revision order")

    all_bundles = {**retired_bundles, **active_bundles}
    for contract_id, contract in retired_contracts.items():
        for field in ("owner_bundle_id", "consumer_bundle_ids"):
            raw_ids = contract.get(field)
            bundle_ids = raw_ids if isinstance(raw_ids, list) else [raw_ids]
            for bundle_id in bundle_ids:
                if isinstance(bundle_id, str) and bundle_id not in all_bundles:
                    errors.append(
                        f"retired shared contract `{contract_id}` {field} bundle "
                        f"`{bundle_id}` does not resolve"
                    )
    readiness = state.get("selection_readiness")
    readiness_basis = (
        readiness.get("basis_revision") if isinstance(readiness, dict) else None
    )
    if type(readiness_basis) is int:
        for item in [*retired_bundles.values(), *retired_contracts.values()]:
            revision = item.get("retired_basis_revision")
            if type(revision) is int and revision > readiness_basis:
                errors.append(
                    "selection retirement basis exceeds current readiness basis"
                )
    return retired_bundles, retired_contracts


def validate_v4_retirement_history_obligations(
    state: dict[str, Any],
    retired_bundles: dict[str, dict[str, Any]],
    retired_contracts: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    """Keep retirement invalidation obligations enforceable without a rollback."""
    obligations: dict[tuple[str, int], set[str]] = {}
    for bundle_id, bundle in retired_bundles.items():
        revision = bundle.get("retired_basis_revision")
        if type(revision) is int:
            obligations.setdefault((bundle_id, revision), set()).add(
                f"retired bundle `{bundle_id}`"
            )
    for contract_id, contract in retired_contracts.items():
        revision = contract.get("retired_basis_revision")
        if type(revision) is not int:
            continue
        related_bundle_ids = [contract.get("owner_bundle_id")]
        consumer_bundle_ids = contract.get("consumer_bundle_ids")
        if isinstance(consumer_bundle_ids, list):
            related_bundle_ids.extend(consumer_bundle_ids)
        for bundle_id in related_bundle_ids:
            if not isinstance(bundle_id, str):
                continue
            retired_bundle = retired_bundles.get(bundle_id)
            retired_bundle_revision = (
                retired_bundle.get("retired_basis_revision")
                if isinstance(retired_bundle, dict)
                else None
            )
            if (
                type(retired_bundle_revision) is int
                and retired_bundle_revision < revision
            ):
                continue
            obligations.setdefault((bundle_id, revision), set()).add(
                f"retired shared contract `{contract_id}`"
            )

    closure = state.get("semantic_review_closure")
    if not isinstance(closure, dict):
        return
    raw_reviews = closure.get("review_passes")
    raw_invalidations = closure.get("invalidations")
    if not isinstance(raw_reviews, list) or not isinstance(raw_invalidations, list):
        return
    reviews = {
        review.get("review_id"): review
        for review in raw_reviews
        if isinstance(review, dict) and isinstance(review.get("review_id"), str)
    }
    reported_required_pairs: set[tuple[str, str, str]] = set()
    for (bundle_id, revision), sources in obligations.items():
        retirement_prior_passes = [
            review
            for review in reviews.values()
            if review.get("reviewer_role") in {"development", "risk"}
            and review.get("scope") == bundle_id
            and type(review.get("basis_revision")) is int
            and review["basis_revision"] < revision
            and not any(
                isinstance(invalidation, dict)
                and invalidation.get("status") == "resolved"
                and review.get("review_id")
                in semantic_string_set(invalidation.get("stale_review_ids"))
                and type(invalidation.get("resolved_revision")) is int
                and invalidation["resolved_revision"] < revision
                for invalidation in raw_invalidations
            )
        ]
        for review in retirement_prior_passes:
            review_id = review["review_id"]
            required_pair = (review.get("reviewer_role"), bundle_id)
            matching = [
                invalidation
                for invalidation in raw_invalidations
                if isinstance(invalidation, dict)
                and invalidation.get("status") in {"open", "resolved"}
                and invalidation.get("opened_revision") == revision
                and bundle_id
                in semantic_string_set(invalidation.get("affected_bundles"))
                and review_id
                in semantic_string_set(invalidation.get("stale_review_ids"))
                and required_pair
                in semantic_required_review_set(
                    invalidation.get("required_reviews")
                )
            ]
            if not matching:
                errors.append(
                    f"selection retirement history {' and '.join(sorted(sources))} "
                    f"needs invalidation opened at retirement basis {revision} for "
                    f"prior PASS `{review_id}` on bundle `{bundle_id}`, including "
                    f"required review `{required_pair[0]}`/`{bundle_id}`"
                )

        retirement_invalidations = [
            invalidation
            for invalidation in raw_invalidations
            if isinstance(invalidation, dict)
            and invalidation.get("opened_revision") == revision
            and bundle_id
            in semantic_string_set(invalidation.get("affected_bundles"))
        ]
        for invalidation in retirement_invalidations:
            required_pairs = semantic_required_review_set(
                invalidation.get("required_reviews")
            )
            invalidation_id = invalidation.get("invalidation_id")
            for review_id in semantic_string_set(
                invalidation.get("stale_review_ids")
            ):
                review = reviews.get(review_id)
                if (
                    not isinstance(review, dict)
                    or review.get("reviewer_role") not in {"development", "risk"}
                    or review.get("scope") != bundle_id
                    or type(review.get("basis_revision")) is not int
                    or review["basis_revision"] >= revision
                ):
                    continue
                required_pair = (review.get("reviewer_role"), bundle_id)
                report_key = (
                    invalidation_id if isinstance(invalidation_id, str) else "<unknown>",
                    review_id,
                    bundle_id,
                )
                if required_pair not in required_pairs and report_key not in reported_required_pairs:
                    reported_required_pairs.add(report_key)
                    errors.append(
                        f"selection retirement invalidation `{report_key[0]}` for prior "
                        f"PASS `{review_id}` must include required review "
                        f"`{required_pair[0]}`/`{bundle_id}`"
                    )


def validate_selection_readiness_v4(
    state: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    readiness = state.get("selection_readiness")
    reviews_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(readiness, dict):
        errors.append("v4 work-state `selection_readiness` must be an object")
        return reviews_by_id
    validate_object_keys(
        readiness,
        {"version", "basis_revision", "reviews"},
        {"version", "basis_revision", "reviews"},
        "selection readiness",
        errors,
    )
    if readiness.get("version") != "1":
        errors.append("selection readiness `version` must be `1`")
    basis_revision = positive_integer(
        readiness.get("basis_revision"), "selection readiness `basis_revision`", errors
    )
    persistent = state.get("persistent_agent_ids")
    reviewer_agent_id = (
        nonempty_string(persistent.get("reviewer"))
        if isinstance(persistent, dict)
        else None
    )
    if reviewer_agent_id is None:
        errors.append(
            "v4 selection readiness requires non-empty `persistent_agent_ids.reviewer`"
        )
    metrics = state.get("operation_metrics")
    spans = metrics.get("spans") if isinstance(metrics, dict) else []
    if not isinstance(spans, list):
        spans = []
    spans_by_id = {
        span.get("span_id"): span
        for span in spans or []
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    span_positions = {
        span.get("span_id"): index
        for index, span in enumerate(spans or [])
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    current_reviews: list[dict[str, Any]] = []
    review_finish_times: list[datetime] = []
    review_revisions: list[int] = []
    review_metric_positions: list[int] = []
    reviews = readiness.get("reviews")
    if not isinstance(reviews, list):
        errors.append("selection readiness `reviews` must be a list")
        reviews = []
    for index, review in enumerate(reviews, start=1):
        label = f"selection readiness review {index}"
        if not isinstance(review, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            review,
            {
                "review_id",
                "reviewer_role",
                "reviewer_agent_id",
                "basis_revision",
                "verdict",
                "status",
            },
            {
                "review_id",
                "reviewer_role",
                "reviewer_agent_id",
                "basis_revision",
                "verdict",
                "status",
            },
            label,
            errors,
        )
        review_id = lower_kebab_value(
            review.get("review_id"), f"{label} `review_id`", errors
        )
        if review_id is not None:
            if review_id in reviews_by_id:
                errors.append(f"selection readiness review id `{review_id}` is duplicated")
            reviews_by_id[review_id] = review
        if review.get("reviewer_role") != "development":
            errors.append(f"{label} `reviewer_role` must be `development`")
        if review.get("reviewer_agent_id") != reviewer_agent_id:
            errors.append(f"{label} must reuse `persistent_agent_ids.reviewer`")
        revision = positive_integer(
            review.get("basis_revision"), f"{label} `basis_revision`", errors
        )
        if revision is not None and basis_revision is not None and revision > basis_revision:
            errors.append(f"{label} exceeds the current readiness basis")
        if revision is not None:
            review_revisions.append(revision)
        if review.get("verdict") != "PASS":
            errors.append(f"{label} `verdict` must be exact `PASS`")
        review_status = nonempty_string(review.get("status"))
        if review_status not in SEMANTIC_REVIEW_STATUSES:
            errors.append(f"{label} has unsupported `status`")
        if review_status == "current":
            current_reviews.append(review)
        metric = spans_by_id.get(review_id)
        if not isinstance(metric, dict) or not (
            metric.get("kind") == "development-review"
            and metric.get("scope") == "selection-readiness"
            and metric.get("status") == "finished"
            and metric.get("outcome") == "PASS"
        ):
            errors.append(f"{label} needs a matching finished readiness metric PASS")
        else:
            metric_position = span_positions.get(review_id)
            if metric_position is not None:
                review_metric_positions.append(metric_position)
            finished = rfc3339_value(
                metric.get("finished_at"), f"{label} metric `finished_at`", errors
            )
            if finished is not None:
                review_finish_times.append(finished)
    if review_revisions != sorted(review_revisions):
        errors.append("selection readiness reviews must follow basis revision order")
    if review_metric_positions != sorted(review_metric_positions):
        errors.append("selection readiness reviews must follow metric span order")
    if len(current_reviews) > 1:
        errors.append("selection readiness has more than one current PASS")
    dispatch = state.get("dispatch_control")
    dispatch_status = dispatch.get("status") if isinstance(dispatch, dict) else None
    if dispatch_status == "ready":
        if len(current_reviews) != 1:
            errors.append("ready dispatch requires exactly one current readiness PASS")
        elif current_reviews[0].get("basis_revision") != basis_revision:
            errors.append("current readiness PASS must use the latest readiness basis")
        stale_ids = [
            review.get("review_id")
            for review in reviews
            if isinstance(review, dict) and review.get("status") == "stale"
        ]
        if stale_ids:
            errors.append("ready dispatch must not retain stale readiness PASSes")
    writer_positions = [
        index
        for index, span in enumerate(spans)
        if isinstance(span, dict) and span.get("kind") == "writer"
    ]
    review_positions = [
        span_positions.get(review_id)
        for review_id in reviews_by_id
        if span_positions.get(review_id) is not None
    ]
    if writer_positions and (
        not review_positions or min(review_positions) >= min(writer_positions)
    ):
        errors.append("selection readiness PASS must precede the first writer span")
    writer_start_times = [
        parsed
        for index, span in enumerate(spans, start=1)
        if isinstance(span, dict) and span.get("kind") == "writer"
        for parsed in [
            rfc3339_value(
                span.get("started_at"), f"writer span {index} `started_at`", errors
            )
        ]
        if parsed is not None
    ]
    if (
        writer_start_times
        and review_finish_times
        and min(review_finish_times) > min(writer_start_times)
    ):
        errors.append("selection readiness PASS must finish before the first writer starts")
    return reviews_by_id


def validate_late_discovery_and_diagnostics_v4(
    state: dict[str, Any],
    contracts_by_id: dict[str, dict[str, Any]],
    bundles_by_id: dict[str, dict[str, Any]],
    candidate_dispositions: dict[str, str],
    readiness_reviews: dict[str, dict[str, Any]],
    errors: list[str],
    *,
    require_final: bool,
) -> None:
    closure = state.get("semantic_review_closure")
    closure_invalidations = (
        closure.get("invalidations") if isinstance(closure, dict) else []
    )
    if not isinstance(closure_invalidations, list):
        closure_invalidations = []
    closure_reviews = closure.get("review_passes") if isinstance(closure, dict) else []
    if not isinstance(closure_reviews, list):
        closure_reviews = []
    invalidations_by_id = {
        item.get("invalidation_id"): item
        for item in closure_invalidations
        if isinstance(item, dict) and isinstance(item.get("invalidation_id"), str)
    }
    readiness = state.get("selection_readiness")
    readiness_basis = (
        readiness.get("basis_revision") if isinstance(readiness, dict) else None
    )

    discoveries = state.get("late_shared_contract_discoveries")
    discoveries_by_id: dict[str, dict[str, Any]] = {}
    discovery_revisions: list[int] = []
    if not isinstance(discoveries, list):
        errors.append("v4 work-state `late_shared_contract_discoveries` must be a list")
        discoveries = []
    for index, discovery in enumerate(discoveries, start=1):
        label = f"late shared-contract discovery {index}"
        if not isinstance(discovery, dict):
            errors.append(f"{label} must be an object")
            continue
        stage = nonempty_string(discovery.get("stage"))
        status = nonempty_string(discovery.get("status"))
        required = {
            "discovery_id",
            "contract_id",
            "stage",
            "basis_revision",
            "affected_bundle_ids",
            "status",
        }
        allowed = required | {
            "stale_readiness_review_id",
            "semantic_invalidation_ids",
            "resolved_revision",
            "resolution_readiness_review_id",
        }
        if stage == "post-readiness":
            required |= {
                "stale_readiness_review_id",
                "semantic_invalidation_ids",
            }
        if status == "resolved" and stage == "post-readiness":
            required |= {"resolved_revision", "resolution_readiness_review_id"}
        validate_object_keys(discovery, allowed, required, label, errors)
        discovery_id = lower_kebab_value(
            discovery.get("discovery_id"), f"{label} `discovery_id`", errors
        )
        if discovery_id is not None:
            if discovery_id in discoveries_by_id:
                errors.append(f"late discovery id `{discovery_id}` appears more than once")
            discoveries_by_id[discovery_id] = discovery
        contract_id = lower_kebab_value(
            discovery.get("contract_id"), f"{label} `contract_id`", errors
        )
        contract = contracts_by_id.get(contract_id or "")
        if contract is None:
            errors.append(f"{label} contract does not resolve")
        elif (
            type(contract.get("retired_basis_revision")) is int
            and status == "open"
        ):
            errors.append(f"{label} open discovery must reference an active contract")
        if stage not in {"pre-readiness", "post-readiness"}:
            errors.append(f"{label} `stage` must be `pre-readiness` or `post-readiness`")
        revision = positive_integer(
            discovery.get("basis_revision"), f"{label} `basis_revision`", errors
        )
        if revision is not None:
            discovery_revisions.append(revision)
            retired_revision = (
                contract.get("retired_basis_revision")
                if isinstance(contract, dict)
                else None
            )
            if type(retired_revision) is int and revision > retired_revision:
                errors.append(f"{label} occurs after its shared contract retirement")
        affected = string_list(
            discovery.get("affected_bundle_ids"),
            f"{label} `affected_bundle_ids`",
            errors,
        )
        if not affected:
            errors.append(f"{label} must name at least one affected bundle")
        if len(affected) != len(set(affected)):
            errors.append(f"{label} repeats an affected bundle")
        related_bundles = set()
        if contract is not None:
            raw_consumer_bundles = contract.get("consumer_bundle_ids")
            consumer_bundles = (
                [value for value in raw_consumer_bundles if isinstance(value, str)]
                if isinstance(raw_consumer_bundles, list)
                else []
            )
            related_bundles = {
                *consumer_bundles,
            }
            owner_bundle = nonempty_string(contract.get("owner_bundle_id"))
            if owner_bundle is not None:
                related_bundles.add(owner_bundle)
        for bundle_id in affected:
            bundle = bundles_by_id.get(bundle_id)
            if bundle is None:
                errors.append(f"{label} affected bundle `{bundle_id}` does not resolve")
            elif bundle_id not in related_bundles:
                errors.append(
                    f"{label} affected bundle `{bundle_id}` is unrelated to its contract"
                )
            elif (
                revision is not None
                and type(bundle.get("retired_basis_revision")) is int
                and revision > bundle["retired_basis_revision"]
            ):
                errors.append(
                    f"{label} occurs after affected bundle `{bundle_id}` retirement"
                )
        if status not in {"open", "resolved"}:
            errors.append(f"{label} `status` must be `open` or `resolved`")
        if (
            revision is not None
            and type(readiness_basis) is int
            and revision > readiness_basis
        ):
            errors.append(f"{label} exceeds the current readiness basis")
        if stage == "pre-readiness":
            if status != "resolved":
                errors.append(f"{label} pre-readiness discovery must be `resolved`")
            for field in (
                "stale_readiness_review_id",
                "semantic_invalidation_ids",
                "resolved_revision",
                "resolution_readiness_review_id",
            ):
                if field in discovery:
                    errors.append(f"{label} pre-readiness discovery must omit `{field}`")
            if (
                revision is not None
                and type(readiness_basis) is int
                and revision > readiness_basis
            ):
                errors.append(f"{label} occurs after the current readiness basis")
            continue

        stale_id = nonempty_string(discovery.get("stale_readiness_review_id"))
        stale_review = readiness_reviews.get(stale_id or "")
        expected_stale_status = "stale" if status == "open" else "superseded"
        if stale_review is None:
            errors.append(f"{label} stale readiness review does not resolve")
        elif stale_review.get("status") != expected_stale_status:
            errors.append(
                f"{label} prior readiness PASS must be `{expected_stale_status}`"
            )
        elif revision is not None and stale_review.get("basis_revision", revision) >= revision:
            errors.append(f"{label} prior readiness PASS must predate discovery")
        invalidation_ids = string_list(
            discovery.get("semantic_invalidation_ids"),
            f"{label} `semantic_invalidation_ids`",
            errors,
        )
        if len(invalidation_ids) != len(set(invalidation_ids)):
            errors.append(f"{label} repeats a semantic invalidation ID")
        invalidations_at_discovery = [
            item
            for item in closure_invalidations
            if isinstance(item, dict) and item.get("opened_revision") == revision
        ]
        invalidated_review_ids = {
            review_id
            for item in invalidations_at_discovery
            for review_id in (
                item.get("stale_review_ids")
                if isinstance(item.get("stale_review_ids"), list)
                else []
            )
            if isinstance(review_id, str)
        }
        affected_prior_passes = [
            review
            for review in closure_reviews
            if isinstance(review, dict)
            and review.get("scope") in set(affected)
            and type(review.get("basis_revision")) is int
            and revision is not None
            and review.get("basis_revision") < revision
            and (
                review.get("status") in {"current", "stale"}
                or (
                    review.get("status") == "superseded"
                    and review.get("review_id") in invalidated_review_ids
                )
            )
        ]
        if affected_prior_passes and not invalidation_ids:
            errors.append(
                f"{label} must link affected semantic invalidation(s) because an "
                "affected prior PASS exists"
            )
        expected_bundle_ids = set(affected)
        linked_bundle_ids: set[str] = set()
        linked_invalidations: list[dict[str, Any]] = []
        for invalidation_id in invalidation_ids:
            invalidation = invalidations_by_id.get(invalidation_id)
            if invalidation is None:
                errors.append(
                    f"{label} semantic invalidation `{invalidation_id}` does not resolve"
                )
                continue
            linked_invalidations.append(invalidation)
            expected_status = "open" if status == "open" else "resolved"
            if invalidation.get("status") != expected_status:
                errors.append(
                    f"{label} semantic invalidation `{invalidation_id}` must be "
                    f"`{expected_status}`"
                )
            if revision is not None and invalidation.get("opened_revision") != revision:
                errors.append(
                    f"{label} semantic invalidation `{invalidation_id}` must open at "
                    "the discovery basis"
                )
            raw_domains = invalidation.get("affected_bundles")
            if isinstance(raw_domains, list):
                linked_bundle_ids.update(
                    bundle_id
                    for bundle_id in raw_domains
                    if isinstance(bundle_id, str)
                )
        if invalidation_ids and linked_bundle_ids != expected_bundle_ids:
            errors.append(
                f"{label} semantic invalidations must cover only its affected bundles"
            )
        if status == "open":
            for field in ("resolved_revision", "resolution_readiness_review_id"):
                if field in discovery:
                    errors.append(f"{label} open discovery must omit `{field}`")
        elif status == "resolved":
            resolved_revision = positive_integer(
                discovery.get("resolved_revision"),
                f"{label} `resolved_revision`",
                errors,
            )
            if (
                resolved_revision is not None
                and revision is not None
                and resolved_revision < revision
            ):
                errors.append(f"{label} resolved revision precedes discovery")
            for invalidation in linked_invalidations:
                invalidation_revision = invalidation.get("resolved_revision")
                if (
                    resolved_revision is not None
                    and type(invalidation_revision) is int
                    and invalidation_revision > resolved_revision
                ):
                    errors.append(
                        f"{label} resolves before linked semantic invalidation "
                        f"`{invalidation.get('invalidation_id')}`"
                    )
            resolution_id = nonempty_string(
                discovery.get("resolution_readiness_review_id")
            )
            resolution = readiness_reviews.get(resolution_id or "")
            if resolution is None:
                errors.append(f"{label} resolution readiness review does not resolve")
            elif resolution.get("basis_revision") != resolved_revision:
                errors.append(
                    f"{label} resolution must reference a PASS at resolved basis"
                )
            elif (
                resolution.get("status") != "current"
                and not (
                    type(readiness_basis) is int
                    and resolved_revision is not None
                    and readiness_basis > resolved_revision
                )
            ):
                errors.append(
                    f"{label} non-current resolution PASS needs a later readiness basis"
                )

    if discovery_revisions != sorted(discovery_revisions):
        errors.append("late shared-contract discoveries must follow basis revision order")
    discovery_positions = {
        discovery_id: index for index, discovery_id in enumerate(discoveries_by_id)
    }

    metrics = state.get("operation_metrics")
    spans = metrics.get("spans") if isinstance(metrics, dict) else []
    if not isinstance(spans, list):
        spans = []
    spans_by_id = {
        span.get("span_id"): span
        for span in spans
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    span_positions = {
        span.get("span_id"): index
        for index, span in enumerate(spans)
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    diagnostics = state.get("semantic_fail_diagnostics")
    diagnostics_by_id: dict[str, dict[str, Any]] = {}
    diagnostic_refs: dict[str, set[tuple[str, str]]] = {}
    diagnostic_roots: dict[str, str] = {}
    ordered_diagnostics: list[dict[str, Any]] = []
    diagnostic_revisions: list[int] = []
    if not isinstance(diagnostics, list):
        errors.append("v4 work-state `semantic_fail_diagnostics` must be a list")
        diagnostics = []
    prior_position = -1
    diagnosed_span_ids: set[str] = set()
    for index, diagnostic in enumerate(diagnostics, start=1):
        label = f"semantic FAIL diagnostic {index}"
        if not isinstance(diagnostic, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            diagnostic,
            {
                "diagnostic_id",
                "review_span_id",
                "first_attempt",
                "root_category",
                "candidate_ids",
                "contract_ids",
                "basis_revision",
            },
            {
                "diagnostic_id",
                "review_span_id",
                "first_attempt",
                "root_category",
                "candidate_ids",
                "contract_ids",
                "basis_revision",
            },
            label,
            errors,
        )
        diagnostic_id = lower_kebab_value(
            diagnostic.get("diagnostic_id"), f"{label} `diagnostic_id`", errors
        )
        if diagnostic_id is not None:
            if diagnostic_id in diagnostics_by_id:
                errors.append(f"semantic diagnostic id `{diagnostic_id}` is duplicated")
            diagnostics_by_id[diagnostic_id] = diagnostic
        review_span_id = lower_kebab_value(
            diagnostic.get("review_span_id"), f"{label} `review_span_id`", errors
        )
        if review_span_id is not None:
            if review_span_id in diagnosed_span_ids:
                errors.append(
                    f"semantic review FAIL span `{review_span_id}` is diagnosed more than once"
                )
            diagnosed_span_ids.add(review_span_id)
        metric = spans_by_id.get(review_span_id or "")
        if not isinstance(metric, dict) or not (
            metric.get("kind")
            in {
                "development-review",
                "risk-review",
                "integration-review",
                "baseline-review",
            }
            and metric.get("status") == "finished"
            and metric.get("outcome") == "FAIL"
            and "rerun_of" not in metric
        ):
            errors.append(f"{label} must reference a first-attempt semantic review FAIL")
        position = span_positions.get(review_span_id or "")
        if position is not None:
            if position <= prior_position:
                errors.append("semantic FAIL diagnostics must follow metric span order")
            prior_position = position
        if diagnostic.get("first_attempt") is not True:
            errors.append(f"{label} `first_attempt` must be exact `true`")
        root_category = nonempty_string(diagnostic.get("root_category"))
        if root_category not in SEMANTIC_FAIL_ROOT_CATEGORIES:
            errors.append(f"{label} has unsupported `root_category`")
        candidate_ids = string_list(
            diagnostic.get("candidate_ids"), f"{label} `candidate_ids`", errors
        )
        contract_ids = string_list(
            diagnostic.get("contract_ids"), f"{label} `contract_ids`", errors
        )
        if len(candidate_ids) != len(set(candidate_ids)):
            errors.append(f"{label} repeats a candidate ID")
        if len(contract_ids) != len(set(contract_ids)):
            errors.append(f"{label} repeats a contract ID")
        if diagnostic_id is not None:
            diagnostic_refs[diagnostic_id] = {
                ("candidate", value) for value in candidate_ids
            } | {("contract", value) for value in contract_ids}
            if root_category is not None:
                diagnostic_roots[diagnostic_id] = root_category
        if not candidate_ids and not contract_ids:
            errors.append(f"{label} must reference a candidate or shared contract")
        for candidate_id in candidate_ids:
            if candidate_id not in candidate_dispositions:
                errors.append(f"{label} candidate `{candidate_id}` does not resolve")
        for contract_id in contract_ids:
            if contract_id not in contracts_by_id:
                errors.append(f"{label} contract `{contract_id}` does not resolve")
        diagnostic_revision = positive_integer(
            diagnostic.get("basis_revision"), f"{label} `basis_revision`", errors
        )
        if diagnostic_revision is not None:
            diagnostic_revisions.append(diagnostic_revision)
            for contract_id in contract_ids:
                contract = contracts_by_id.get(contract_id)
                retired_revision = (
                    contract.get("retired_basis_revision")
                    if isinstance(contract, dict)
                    else None
                )
                if (
                    type(retired_revision) is int
                    and diagnostic_revision > retired_revision
                ):
                    errors.append(
                        f"{label} references contract `{contract_id}` after retirement"
                    )
        ordered_diagnostics.append(diagnostic)

    if diagnostic_revisions != sorted(diagnostic_revisions):
        errors.append("semantic FAIL diagnostics must follow basis revision order")

    undiagnosed_spans = {
        span.get("span_id")
        for span in spans
        if isinstance(span, dict)
        and isinstance(span.get("span_id"), str)
        and span.get("kind")
        in {
            "development-review",
            "risk-review",
            "integration-review",
            "baseline-review",
        }
        and span.get("status") == "finished"
        and span.get("outcome") == "FAIL"
        and "rerun_of" not in span
        and span.get("span_id") not in diagnosed_span_ids
    }
    for span_id in sorted(value for value in undiagnosed_spans if isinstance(value, str)):
        errors.append(
            f"first-attempt semantic review FAIL `{span_id}` needs a bounded diagnostic"
        )

    control = state.get("dispatch_control")
    if not isinstance(control, dict):
        errors.append("v4 work-state `dispatch_control` must be an object")
        return
    validate_object_keys(
        control,
        {"version", "status", "episodes"},
        {"version", "status", "episodes"},
        "dispatch control",
        errors,
    )
    if control.get("version") != "1":
        errors.append("dispatch control `version` must be `1`")
    control_status = nonempty_string(control.get("status"))
    if control_status not in {"ready", "paused"}:
        errors.append("dispatch control `status` must be `ready` or `paused`")
    episodes = control.get("episodes")
    parsed_episodes: list[dict[str, Any]] = []
    if not isinstance(episodes, list):
        errors.append("dispatch control `episodes` must be a list")
        episodes = []
    episode_ids: set[str] = set()
    episode_trigger_sets: list[tuple[Any, set[str]]] = []
    episode_revisions: list[int] = []
    late_episode_trigger_ids: set[str] = set()
    for index, episode in enumerate(episodes, start=1):
        label = f"dispatch pause episode {index}"
        if not isinstance(episode, dict):
            errors.append(f"{label} must be an object")
            continue
        status = nonempty_string(episode.get("status"))
        episode_cause = nonempty_string(episode.get("cause"))
        required = {
            "episode_id",
            "cause",
            "trigger_ids",
            "basis_revision",
            "status",
        }
        allowed = required | {
            "diagnosis",
            "action",
            "resume_basis_revision",
            "readiness_review_id",
        }
        if status == "resolved":
            required |= {
                "diagnosis",
                "action",
                "resume_basis_revision",
                "readiness_review_id",
            }
        if episode_cause == "late-shared-contract":
            required.add("pause_after_span_id")
            required.add("paused_at")
            allowed.add("pause_after_span_id")
            allowed.add("paused_at")
        validate_object_keys(episode, allowed, required, label, errors)
        episode_id = lower_kebab_value(
            episode.get("episode_id"), f"{label} `episode_id`", errors
        )
        if episode_id is not None:
            if episode_id in episode_ids:
                errors.append(f"dispatch pause episode id `{episode_id}` is duplicated")
            episode_ids.add(episode_id)
        cause = episode_cause
        latest_trigger_span_position: int | None = None
        if cause not in {"late-shared-contract", "shared-root-semantic-fail"}:
            errors.append(f"{label} has unsupported `cause`")
        trigger_ids = string_list(
            episode.get("trigger_ids"), f"{label} `trigger_ids`", errors
        )
        if not trigger_ids:
            errors.append(f"{label} must include trigger IDs")
        if len(trigger_ids) != len(set(trigger_ids)):
            errors.append(f"{label} repeats a trigger ID")
        for trigger_id in trigger_ids:
            if cause == "late-shared-contract" and trigger_id in late_episode_trigger_ids:
                errors.append(
                    f"{label} reuses `{trigger_id}` in more than one `{cause}` episode"
                )
            if cause == "late-shared-contract":
                late_episode_trigger_ids.add(trigger_id)
        episode_trigger_sets.append((cause, set(trigger_ids)))
        episode_revision = positive_integer(
            episode.get("basis_revision"), f"{label} `basis_revision`", errors
        )
        if episode_revision is not None:
            episode_revisions.append(episode_revision)
        episode_paused_at: datetime | None = None
        if cause == "late-shared-contract":
            episode_paused_at = rfc3339_value(
                episode.get("paused_at"), f"{label} `paused_at`", errors
            )
            pause_after_span_id = lower_kebab_value(
                episode.get("pause_after_span_id"),
                f"{label} `pause_after_span_id`",
                errors,
            )
            pause_after_span = spans_by_id.get(pause_after_span_id or "")
            if not isinstance(pause_after_span, dict):
                errors.append(f"{label} dispatch cutoff metric span does not resolve")
            elif pause_after_span.get("status") != "finished":
                errors.append(f"{label} dispatch cutoff metric span must be finished")
            elif episode_paused_at is not None:
                cutoff_finished_at = rfc3339_value(
                    pause_after_span.get("finished_at"),
                    f"{label} dispatch cutoff metric `finished_at`",
                    errors,
                )
                if (
                    cutoff_finished_at is not None
                    and cutoff_finished_at > episode_paused_at
                ):
                    errors.append(
                        f"{label} dispatch cutoff metric finishes after immutable "
                        "`paused_at`"
                    )
            pause_after_position = span_positions.get(pause_after_span_id or "")
            if type(pause_after_position) is int:
                latest_trigger_span_position = pause_after_position
            linked = [discoveries_by_id.get(value) for value in trigger_ids]
            if any(item is None or item.get("stage") != "post-readiness" for item in linked):
                errors.append(f"{label} must reference post-readiness discoveries")
            linked_revisions = [
                item.get("basis_revision")
                for item in linked
                if isinstance(item, dict) and type(item.get("basis_revision")) is int
            ]
            if (
                episode_revision is not None
                and linked_revisions
                and episode_revision != max(linked_revisions)
            ):
                errors.append(f"{label} must use its latest linked discovery basis")
            linked_positions = [
                discovery_positions[value]
                for value in trigger_ids
                if value in discovery_positions
            ]
            if linked_positions != sorted(linked_positions):
                errors.append(f"{label} discovery triggers must follow discovery order")
        elif cause == "shared-root-semantic-fail":
            linked = [diagnostics_by_id.get(value) for value in trigger_ids]
            if len(linked) < 2 or any(item is None for item in linked):
                errors.append(f"{label} must reference at least two semantic diagnostics")
            else:
                positions = [ordered_diagnostics.index(item) for item in linked]
                roots = {
                    diagnostic_roots.get(item.get("diagnostic_id")) for item in linked
                }
                shared_refs = set(
                    diagnostic_refs.get(linked[0].get("diagnostic_id"), set())
                )
                for item in linked[1:]:
                    shared_refs &= diagnostic_refs.get(
                        item.get("diagnostic_id"), set()
                    )
                if positions != list(range(positions[0], positions[0] + len(positions))):
                    errors.append(f"{label} diagnostics must be consecutive")
                if len(roots) != 1:
                    errors.append(f"{label} diagnostics must share one root category")
                if not shared_refs:
                    errors.append(f"{label} diagnostics must share a candidate or contract root")
                linked_revisions = [
                    item.get("basis_revision")
                    for item in linked
                    if type(item.get("basis_revision")) is int
                ]
                if (
                    episode_revision is not None
                    and linked_revisions
                    and episode_revision != max(linked_revisions)
                ):
                    errors.append(f"{label} must use its latest linked diagnostic basis")
                linked_span_positions = [
                    span_positions.get(item.get("review_span_id"))
                    for item in linked
                    if isinstance(item, dict)
                ]
                concrete_positions = [
                    position
                    for position in linked_span_positions
                    if type(position) is int
                ]
                if concrete_positions:
                    latest_trigger_span_position = max(concrete_positions)
        if status == "open":
            for field in (
                "diagnosis",
                "action",
                "resume_basis_revision",
                "readiness_review_id",
            ):
                if field in episode:
                    errors.append(f"{label} open episode must omit `{field}`")
        elif status == "resolved":
            single_line_string(episode.get("diagnosis"), f"{label} `diagnosis`", errors)
            single_line_string(episode.get("action"), f"{label} `action`", errors)
            resume_revision = positive_integer(
                episode.get("resume_basis_revision"),
                f"{label} `resume_basis_revision`",
                errors,
            )
            if (
                cause == "shared-root-semantic-fail"
                and resume_revision is not None
                and episode_revision is not None
                and resume_revision <= episode_revision
            ):
                errors.append(
                    f"{label} resume basis must advance beyond its pause/trigger basis"
                )
            elif (
                cause != "shared-root-semantic-fail"
                and resume_revision is not None
                and episode_revision is not None
                and resume_revision < episode_revision
            ):
                errors.append(f"{label} resume basis precedes its pause basis")
            if cause == "late-shared-contract" and resume_revision is not None:
                linked_resolution_revisions = [
                    item.get("resolved_revision")
                    for item in linked
                    if isinstance(item, dict)
                    and type(item.get("resolved_revision")) is int
                ]
                if (
                    linked_resolution_revisions
                    and resume_revision < max(linked_resolution_revisions)
                ):
                    errors.append(
                        f"{label} resumes before linked late discovery resolution"
                    )
            review_id = nonempty_string(episode.get("readiness_review_id"))
            review = readiness_reviews.get(review_id or "")
            resume_metric_position = span_positions.get(review_id or "")
            if review is None:
                errors.append(f"{label} resume readiness review does not resolve")
            elif review.get("basis_revision") != resume_revision:
                errors.append(
                    f"{label} resume must reference a PASS at resume basis"
                )
            elif (
                review.get("status") != "current"
                and not (
                    type(readiness_basis) is int
                    and resume_revision is not None
                    and readiness_basis > resume_revision
                )
            ):
                errors.append(
                    f"{label} non-current resume PASS needs a later readiness basis"
                )
            if (
                cause == "shared-root-semantic-fail"
                and latest_trigger_span_position is not None
                and (
                    type(resume_metric_position) is not int
                    or resume_metric_position <= latest_trigger_span_position
                )
            ):
                errors.append(
                    f"{label} resume readiness PASS must be recorded after its "
                    "triggering semantic FAILs"
                )
            if (
                cause == "late-shared-contract"
                and latest_trigger_span_position is not None
                and (
                    type(resume_metric_position) is not int
                    or resume_metric_position <= latest_trigger_span_position
                )
            ):
                errors.append(
                    f"{label} resolution readiness PASS must be recorded after its "
                    "dispatch cutoff"
                )
        else:
            errors.append(f"{label} `status` must be `open` or `resolved`")
        if (
            cause in {"late-shared-contract", "shared-root-semantic-fail"}
            and latest_trigger_span_position is not None
        ):
            resume_position = None
            if status == "resolved":
                resume_id = nonempty_string(episode.get("readiness_review_id"))
                resume_position = span_positions.get(resume_id or "")
            intervening_dispatch = [
                span
                for position, span in enumerate(spans)
                if isinstance(span, dict)
                and span.get("kind") in {"bundle", "writer"}
                and position > latest_trigger_span_position
                and (
                    status == "open"
                    or type(resume_position) is not int
                    or position < resume_position
                )
            ]
            if intervening_dispatch:
                errors.append(
                    f"{label} must not dispatch bundle/writer work after its pause "
                    "cutoff and before a new readiness PASS"
                )
            if cause == "late-shared-contract" and episode_paused_at is not None:
                dispatch_after_pause = []
                for position, span in enumerate(spans):
                    if (
                        not isinstance(span, dict)
                        or span.get("kind") not in {"bundle", "writer"}
                        or (
                            status == "resolved"
                            and type(resume_position) is int
                            and position >= resume_position
                        )
                    ):
                        continue
                    dispatch_started_at = rfc3339_value(
                        span.get("started_at"),
                        f"{label} dispatch span `started_at`",
                        errors,
                    )
                    if (
                        dispatch_started_at is not None
                        and dispatch_started_at > episode_paused_at
                    ):
                        dispatch_after_pause.append(span)
                if dispatch_after_pause:
                    errors.append(
                        f"{label} must not move its cutoff past bundle/writer work "
                        "started after immutable `paused_at`"
                    )
        parsed_episodes.append(episode)

    if episode_revisions != sorted(episode_revisions):
        errors.append("dispatch pause episodes must follow basis revision order")

    open_episodes = [episode for episode in parsed_episodes if episode.get("status") == "open"]
    if len(open_episodes) > 1:
        errors.append("dispatch control must not have more than one open pause episode")
    if open_episodes and parsed_episodes[-1] is not open_episodes[0]:
        errors.append("the open dispatch pause episode must be last")
    expected_status = "paused" if open_episodes else "ready"
    if control_status != expected_status:
        errors.append(f"dispatch control status must be `{expected_status}` for its episodes")
    if require_final and control_status != "ready":
        errors.append("final v4 selection requires ready dispatch with no open pause")
    if control_status == "paused":
        active_dispatch = [
            span
            for span in spans
            if isinstance(span, dict)
            and span.get("status") == "active"
            and span.get("kind") in {"bundle", "writer"}
        ]
        if active_dispatch:
            errors.append("paused dispatch must not contain an active bundle/writer span")

    for discovery_id, discovery in discoveries_by_id.items():
        if discovery.get("stage") != "post-readiness":
            continue
        matches = [
            episode
            for episode, (cause, trigger_ids) in zip(
                parsed_episodes, episode_trigger_sets
            )
            if cause == "late-shared-contract" and discovery_id in trigger_ids
        ]
        if len(matches) != 1 or matches[0].get("status") != discovery.get("status"):
            errors.append(
                f"post-readiness discovery `{discovery_id}` needs exactly one matching "
                "pause episode"
            )
    for prior, latest in zip(ordered_diagnostics, ordered_diagnostics[1:]):
        prior_id = prior.get("diagnostic_id")
        latest_id = latest.get("diagnostic_id")
        shared_refs = diagnostic_refs.get(prior_id, set()) & diagnostic_refs.get(
            latest_id, set()
        )
        if (
            diagnostic_roots.get(prior_id) == diagnostic_roots.get(latest_id)
            and prior_id in diagnostic_roots
            and shared_refs
        ):
            pair = {prior_id, latest_id}
            matching_episodes = [
                trigger_ids
                for cause, trigger_ids in episode_trigger_sets
                if cause == "shared-root-semantic-fail" and pair <= trigger_ids
            ]
            if len(matching_episodes) != 1:
                errors.append(
                    "consecutive first-attempt semantic FAILs with one root require "
                    "a dispatch pause/diagnosis episode exactly once"
                )


def validate_operation_artifact_state(
    config: Config,
    request_root: Path,
    state: dict[str, Any],
    candidate_targets: dict[str, set[str]],
    candidate_dispositions: dict[str, str],
    candidate_domains: dict[str, str],
    accepted_domains: set[str],
    active_route_keys: set[str],
    inventory_text: str | None,
    require_actions_final: bool,
    errors: list[str],
) -> None:
    created = state.get("operation_created_artifacts")
    approved = state.get("approved_existing_actions")
    executions = state.get("action_execution")
    if created is None and approved is None and executions is None:
        return

    _, atoms_by_path, atoms_by_key, incoming = scan_operation_atoms(config, errors)
    created_paths, created_keys = validate_created_artifacts(
        created,
        config,
        request_root,
        state,
        atoms_by_path,
        atoms_by_key,
        incoming,
        candidate_targets,
        candidate_dispositions,
        candidate_domains,
        active_route_keys,
        inventory_text,
        require_actions_final,
        errors,
    )
    manifests = parse_approved_actions(
        approved, config, incoming, accepted_domains, errors
    )
    validate_artifact_contract_ownership(
        created_paths, created_keys, manifests, errors
    )
    validate_action_executions(
        executions,
        manifests,
        config,
        request_root,
        state,
        atoms_by_path,
        atoms_by_key,
        incoming,
        active_route_keys,
        require_actions_final,
        errors,
    )


def validate_created_artifacts(
    value: Any,
    config: Config,
    request_root: Path,
    state: dict[str, Any],
    atoms_by_path: dict[str, Atom],
    atoms_by_key: dict[str, list[Atom]],
    incoming: dict[str, set[str]],
    candidate_targets: dict[str, set[str]],
    candidate_dispositions: dict[str, str],
    candidate_domains: dict[str, str],
    active_route_keys: set[str],
    inventory_text: str | None,
    require_actions_final: bool,
    errors: list[str],
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    if value is None:
        return {}, {}
    if not isinstance(value, list):
        errors.append("work-state `operation_created_artifacts` must be a list")
        return {}, {}
    seen_paths: set[str] = set()
    seen_keys: set[str] = set()
    created_paths: dict[str, dict[str, str]] = {}
    created_keys: dict[str, dict[str, str]] = {}
    for index, item in enumerate(value, start=1):
        label = f"operation-created artifact {index}"
        identity: dict[str, str] | None = None
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            item,
            {
                "candidate_id",
                "atom_key",
                "path",
                "created_attempt_id",
                "last_operation_sha256",
                "status",
                "rollback_path",
                "state_rollback_path",
                "state_rollback_sha256",
            },
            {
                "candidate_id",
                "atom_key",
                "path",
                "created_attempt_id",
                "last_operation_sha256",
                "status",
            },
            label,
            errors,
        )
        candidate_id = lower_kebab_value(item.get("candidate_id"), f"{label} `candidate_id`", errors)
        atom_key = lower_kebab_value(item.get("atom_key"), f"{label} `atom_key`", errors)
        rel_path, path = managed_atom_path(item.get("path"), label, config, errors)
        if rel_path is not None:
            if rel_path in seen_paths:
                errors.append(f"operation-created artifact path `{rel_path}` appears more than once")
            seen_paths.add(rel_path)
        if atom_key is not None:
            if atom_key in seen_keys:
                errors.append(f"operation-created atom_key `{atom_key}` appears more than once")
            seen_keys.add(atom_key)
        if nonempty_string(item.get("created_attempt_id")) is None:
            errors.append(f"{label} must include non-empty `created_attempt_id`")
        digest = sha256_value(item.get("last_operation_sha256"), f"{label} `last_operation_sha256`", errors)
        status = item.get("status")
        if status not in {"present", "removal_pending", "removed"}:
            errors.append(f"{label} status must be `present`, `removal_pending`, or `removed`")
            continue
        if rel_path is not None and atom_key is not None and candidate_id is not None:
            identity = {
                "candidate_id": candidate_id,
                "atom_key": atom_key,
                "path": rel_path,
                "created_attempt_id": str(item.get("created_attempt_id", "")),
                "last_operation_sha256": digest or "",
            }
            created_paths[rel_path] = identity
            created_keys[atom_key] = identity
        if candidate_id is not None and candidate_id not in candidate_dispositions:
            errors.append(f"{label} candidate_id `{candidate_id}` does not resolve")
        if rel_path is not None and candidate_id is not None:
            domain = candidate_domains.get(candidate_id)
            if domain is not None and not managed_path_in_scope(rel_path, {domain}):
                errors.append(
                    f"{label} path `{rel_path}` is outside candidate domain `{domain}`"
                )
        if rel_path is not None:
            validate_created_path_untracked(
                config,
                rel_path,
                nonempty_string(state.get("source_commit_observed")),
                label,
                errors,
            )
        if status == "present":
            if candidate_id is not None and candidate_dispositions.get(candidate_id) != "write":
                errors.append(f"{label} with status `present` must reference a `write` candidate")
            if (
                candidate_id is not None
                and atom_key is not None
                and atom_key not in candidate_targets.get(candidate_id, set())
            ):
                errors.append(f"{label} atom_key `{atom_key}` is not an output of candidate `{candidate_id}`")
            validate_present_managed_member(label, rel_path, path, atom_key, digest, atoms_by_path, errors)
            for field in (
                "rollback_path",
                "state_rollback_path",
                "state_rollback_sha256",
            ):
                if field in item:
                    errors.append(f"{label} with status `present` must not set `{field}`")
            continue

        if candidate_id is not None and candidate_dispositions.get(candidate_id) != "drop":
            errors.append(f"{label} with status `{status}` must reference a `drop` candidate")
        if atom_key is not None and atom_key in active_route_keys:
            errors.append(f"{label} atom_key `{atom_key}` remains in selected queue or risk routes")
        if candidate_id is not None and not inventory_mentions_candidate(
            inventory_text, candidate_id
        ):
            errors.append(
                f"{label} dropped candidate `{candidate_id}` is missing from operation inventory"
            )
        if status == "removed" and path is not None and path.exists():
            errors.append(f"{label} with status `removed` requires managed path `{rel_path}` to be absent")
        if atom_key is not None and atoms_by_key.get(atom_key):
            locations = {atom.rel_path for atom in atoms_by_key[atom_key]}
            own_pending = status == "removal_pending" and rel_path in locations
            unexpected = locations - ({rel_path} if own_pending else set())
            if unexpected or not own_pending:
                joined = ", ".join(sorted(locations))
                errors.append(f"{label} removed atom_key `{atom_key}` still exists in `{joined}`")
        if status == "removal_pending" and path is not None and path.exists():
            validate_present_managed_member(
                label, rel_path, path, atom_key, digest, atoms_by_path, errors
            )
        if atom_key is not None:
            for owner in sorted(incoming.get(atom_key, set())):
                errors.append(f"{label} removed atom_key `{atom_key}` is still targeted by `{owner}`")
        rollback = request_rollback_path(item.get("rollback_path"), label, request_root, errors)
        validate_file_hash(rollback, digest, f"{label} rollback", errors)
        state_rollback = request_rollback_path(
            item.get("state_rollback_path"),
            label,
            request_root,
            errors,
            field="state_rollback_path",
        )
        state_digest = sha256_value(
            item.get("state_rollback_sha256"),
            f"{label} `state_rollback_sha256`",
            errors,
        )
        validate_file_hash(
            state_rollback, state_digest, f"{label} operation-state rollback", errors
        )
        validate_created_state_snapshot(
            state_rollback, state, identity, label, errors
        )
        if require_actions_final and status != "removed":
            errors.append(f"{label} must be `removed` for final action validation")
    return created_paths, created_keys


def parse_approved_actions(
    value: Any,
    config: Config,
    incoming: dict[str, set[str]],
    accepted_domains: set[str],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, list):
        errors.append("work-state `approved_existing_actions` must be a list")
        return {}
    manifests: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(value, start=1):
        label = f"approved existing action {index}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        action_id = lower_kebab_value(item.get("action_id"), f"{label} `action_id`", errors)
        action = item.get("action")
        if action not in {"delete", "merge"}:
            errors.append(f"{label} action must be `delete` or `merge`")
            continue
        action_keys = {
            "action_id",
            "action",
            "source",
            "reference_owners",
            "approved_action_fingerprint",
        }
        if action == "merge":
            action_keys.add("target")
        validate_object_keys(item, action_keys, action_keys, label, errors)
        source = parse_manifest_member(item.get("source"), f"{label} source", config, errors)
        target_value = item.get("target")
        target = parse_manifest_member(target_value, f"{label} target", config, errors) if target_value is not None else None
        if action == "delete" and target is not None:
            errors.append(f"{label} delete action must not set `target`")
        if action == "merge" and target is None:
            errors.append(f"{label} merge action requires `target`")
        raw_owners = item.get("reference_owners")
        owners: list[dict[str, str]] = []
        if not isinstance(raw_owners, list):
            errors.append(f"{label} `reference_owners` must be a list")
        else:
            for owner_index, owner_value in enumerate(raw_owners, start=1):
                owner = parse_manifest_member(
                    owner_value, f"{label} reference owner {owner_index}", config, errors
                )
                if owner is not None:
                    owners.append(owner)
        members = [member for member in [source, target, *owners] if member is not None]
        member_paths = [member["path"] for member in members]
        if len(set(member_paths)) != len(member_paths):
            errors.append(f"{label} member paths must be unique")
        for member in members:
            if not managed_path_in_scope(member["path"], accepted_domains):
                errors.append(
                    f"{label} member path `{member['path']}` is outside `accepted_scope`"
                )
        fingerprint = sha256_value(
            item.get("approved_action_fingerprint"),
            f"{label} `approved_action_fingerprint`",
            errors,
        )
        if action_id is None or source is None:
            continue
        if action_id in manifests:
            errors.append(f"approved existing action id `{action_id}` appears more than once")
            continue
        canonical = canonical_action_fingerprint(action_id, action, source, target, owners)
        if fingerprint is not None and fingerprint != canonical:
            errors.append(f"{label} approved_action_fingerprint does not match its immutable manifest")
        allowed_incoming = {source["path"], *(owner["path"] for owner in owners)}
        if target is not None:
            allowed_incoming.add(target["path"])
        for owner_path in sorted(incoming.get(source["atom_key"], set()) - allowed_incoming):
            errors.append(f"{label} has unapproved incoming graph owner `{owner_path}`")
        role_members: dict[str, tuple[str, dict[str, str]]] = {source["path"]: ("source", source)}
        if target is not None:
            role_members[target["path"]] = ("target", target)
        for owner in owners:
            role_members[owner["path"]] = ("reference_owner", owner)
        manifests[action_id] = {
            "action": action,
            "source": source,
            "target": target,
            "owners": owners,
            "fingerprint": canonical,
            "members": role_members,
        }
    return manifests


def validate_artifact_contract_ownership(
    created_paths: dict[str, dict[str, str]],
    created_keys: dict[str, dict[str, str]],
    manifests: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    for action_id, manifest in manifests.items():
        for role, member in [
            ("source", manifest["source"]),
            ("target", manifest["target"]),
            *(('reference_owner', owner) for owner in manifest["owners"]),
        ]:
            if member is None:
                continue
            created_by_path = created_paths.get(member["path"])
            created_by_key = created_keys.get(member["atom_key"])
            if created_by_path is not None:
                errors.append(
                    f"approved existing action `{action_id}` {role} path "
                    f"`{member['path']}` is also operation-created"
                )
            if created_by_key is not None:
                errors.append(
                    f"approved existing action `{action_id}` {role} atom_key "
                    f"`{member['atom_key']}` is also operation-created"
                )


def parse_manifest_member(
    value: Any, label: str, config: Config, errors: list[str]
) -> dict[str, str] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    validate_object_keys(
        value,
        {"atom_key", "path", "preimage_sha256"},
        {"atom_key", "path", "preimage_sha256"},
        label,
        errors,
    )
    atom_key = lower_kebab_value(value.get("atom_key"), f"{label} `atom_key`", errors)
    rel_path, _ = managed_atom_path(value.get("path"), label, config, errors)
    digest = sha256_value(value.get("preimage_sha256"), f"{label} `preimage_sha256`", errors)
    if atom_key is None or rel_path is None or digest is None:
        return None
    return {"atom_key": atom_key, "path": rel_path, "preimage_sha256": digest}


def canonical_action_fingerprint(
    action_id: str,
    action: str,
    source: dict[str, str],
    target: dict[str, str] | None,
    owners: list[dict[str, str]],
) -> str:
    payload: dict[str, Any] = {
        "action_id": action_id,
        "action": action,
        "source": source,
        "reference_owners": sorted(owners, key=lambda owner: owner["path"]),
    }
    if target is not None:
        payload["target"] = target
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def validate_action_executions(
    value: Any,
    manifests: dict[str, dict[str, Any]],
    config: Config,
    request_root: Path,
    state: dict[str, Any],
    atoms_by_path: dict[str, Atom],
    atoms_by_key: dict[str, list[Atom]],
    incoming: dict[str, set[str]],
    active_route_keys: set[str],
    require_actions_final: bool,
    errors: list[str],
) -> None:
    if value is None:
        if manifests:
            errors.append("work-state `action_execution` is required for approved existing actions")
        return
    if not isinstance(value, list):
        errors.append("work-state `action_execution` must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        label = f"action execution {index}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        validate_object_keys(
            item,
            {
                "action_id",
                "approved_action_fingerprint",
                "status",
                "members",
                "state_rollback_path",
                "state_rollback_sha256",
            },
            {"action_id", "approved_action_fingerprint", "status", "members"},
            label,
            errors,
        )
        action_id = lower_kebab_value(item.get("action_id"), f"{label} `action_id`", errors)
        if action_id is None:
            continue
        if action_id in seen:
            errors.append(f"action execution id `{action_id}` appears more than once")
            continue
        seen.add(action_id)
        manifest = manifests.get(action_id)
        if manifest is None:
            errors.append(f"{label} action_id `{action_id}` has no approved manifest")
            continue
        fingerprint = sha256_value(
            item.get("approved_action_fingerprint"),
            f"{label} `approved_action_fingerprint`",
            errors,
        )
        if fingerprint is not None and fingerprint != manifest["fingerprint"]:
            errors.append(f"{label} fingerprint does not match approved action `{action_id}`")
        status = item.get("status")
        if status not in {"approved", "applying", "rolling_back", "applied"}:
            errors.append(f"{label} status must be `approved`, `applying`, `rolling_back`, or `applied`")
            continue
        state_rollback: Path | None = None
        state_digest: str | None = None
        if status == "approved":
            for field in ("state_rollback_path", "state_rollback_sha256"):
                if field in item:
                    errors.append(f"{label} with status `approved` must not set `{field}`")
        else:
            state_rollback = request_rollback_path(
                item.get("state_rollback_path"),
                label,
                request_root,
                errors,
                field="state_rollback_path",
            )
            state_digest = sha256_value(
                item.get("state_rollback_sha256"),
                f"{label} `state_rollback_sha256`",
                errors,
            )
            validate_file_hash(
                state_rollback,
                state_digest,
                f"{label} operation-state rollback",
                errors,
            )
            validate_action_state_snapshot(
                state_rollback, state, action_id, manifest, label, errors
            )
        raw_members = item.get("members")
        if not isinstance(raw_members, list):
            errors.append(f"{label} `members` must be a list")
            continue
        runtime_paths: set[str] = set()
        runtime: dict[str, dict[str, Any]] = {}
        for member_index, raw_member in enumerate(raw_members, start=1):
            member_label = f"{label} member {member_index}"
            member = parse_runtime_member(
                raw_member, member_label, status, config, request_root, errors
            )
            if member is None:
                continue
            path = member["path"]
            if path in runtime_paths:
                errors.append(f"{label} runtime path `{path}` appears more than once")
                continue
            runtime_paths.add(path)
            runtime[path] = member
        expected_members: dict[str, tuple[str, dict[str, str]]] = manifest["members"]
        if runtime_paths != set(expected_members):
            errors.append(f"{label} runtime members must exactly match the approved manifest")
        for path, member in runtime.items():
            expected = expected_members.get(path)
            if expected is None:
                continue
            role, immutable = expected
            if member["role"] != role or member["atom_key"] != immutable["atom_key"]:
                errors.append(f"{label} runtime member `{path}` changes approved role or atom_key")
            if role != "source" and member["expected_state"] != "present":
                errors.append(f"{label} {role} member `{path}` must remain present")
            if status == "approved":
                if member["expected_state"] != "present":
                    errors.append(f"{label} approved member `{path}` must be present")
                if member.get("last_operation_sha256") != immutable["preimage_sha256"]:
                    errors.append(f"{label} approved member `{path}` must match its preimage hash")
            validate_runtime_current_state(
                member,
                member_label=f"{label} member `{path}`",
                atoms_by_path=atoms_by_path,
                errors=errors,
            )
            rollback_path = member.get("rollback_path")
            if status in {"applying", "rolling_back", "applied"}:
                validate_file_hash(
                    rollback_path,
                    immutable["preimage_sha256"],
                    f"{label} member `{path}` rollback",
                    errors,
                )
        source = manifest["source"]
        allowed_incoming = {source["path"], *(owner["path"] for owner in manifest["owners"])}
        if manifest["target"] is not None:
            allowed_incoming.add(manifest["target"]["path"])
        for owner_path in sorted(incoming.get(source["atom_key"], set()) - allowed_incoming):
            errors.append(f"{label} discovered unapproved incoming graph owner `{owner_path}`")
        if status == "applied":
            validate_applied_action(
                label,
                manifest,
                runtime,
                atoms_by_key,
                incoming,
                active_route_keys,
                errors,
            )
        if require_actions_final and status != "applied":
            errors.append(f"{label} must be `applied` for final action validation")
    for missing in sorted(set(manifests) - seen):
        errors.append(f"approved existing action `{missing}` has no action execution")


def parse_runtime_member(
    value: Any,
    label: str,
    status: str,
    config: Config,
    request_root: Path,
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    validate_object_keys(
        value,
        {
            "role",
            "atom_key",
            "path",
            "expected_state",
            "last_operation_sha256",
            "rollback_path",
        },
        {"role", "atom_key", "path", "expected_state"},
        label,
        errors,
    )
    role = value.get("role")
    if role not in {"source", "target", "reference_owner"}:
        errors.append(f"{label} role must be `source`, `target`, or `reference_owner`")
    atom_key = lower_kebab_value(value.get("atom_key"), f"{label} `atom_key`", errors)
    rel_path, absolute_path = managed_atom_path(value.get("path"), label, config, errors)
    expected_state = value.get("expected_state")
    if expected_state not in {"present", "absent"}:
        errors.append(f"{label} expected_state must be `present` or `absent`")
    digest: str | None = None
    if expected_state == "present":
        digest = sha256_value(
            value.get("last_operation_sha256"),
            f"{label} `last_operation_sha256`",
            errors,
        )
    elif "last_operation_sha256" in value:
        errors.append(f"{label} with expected_state `absent` must not set `last_operation_sha256`")
    rollback: Path | None = None
    if status in {"applying", "rolling_back", "applied"}:
        rollback = request_rollback_path(value.get("rollback_path"), label, request_root, errors)
    elif "rollback_path" in value:
        errors.append(f"{label} with status `{status}` must not set `rollback_path`")
    if (
        role not in {"source", "target", "reference_owner"}
        or atom_key is None
        or rel_path is None
        or absolute_path is None
    ):
        return None
    return {
        "role": role,
        "atom_key": atom_key,
        "path": rel_path,
        "absolute_path": absolute_path,
        "expected_state": expected_state,
        "last_operation_sha256": digest,
        "rollback_path": rollback,
    }


def validate_runtime_current_state(
    member: dict[str, Any],
    member_label: str,
    atoms_by_path: dict[str, Atom],
    errors: list[str],
) -> None:
    atom = atoms_by_path.get(member["path"])
    if member["expected_state"] == "absent":
        if member["absolute_path"].exists():
            errors.append(f"{member_label} expected path to be absent")
        return
    if atom is None:
        errors.append(f"{member_label} expected path to be present")
        return
    if atom.atom_key != member["atom_key"]:
        errors.append(f"{member_label} expected atom_key `{member['atom_key']}`, got `{atom.atom_key}`")
    digest = sha256_file(atom.path)
    if digest != member.get("last_operation_sha256"):
        errors.append(f"{member_label} current hash does not match runtime postimage")


def validate_applied_action(
    label: str,
    manifest: dict[str, Any],
    runtime: dict[str, dict[str, Any]],
    atoms_by_key: dict[str, list[Atom]],
    incoming: dict[str, set[str]],
    active_route_keys: set[str],
    errors: list[str],
) -> None:
    source = manifest["source"]
    source_runtime = runtime.get(source["path"])
    if source_runtime is None or source_runtime.get("expected_state") != "absent":
        errors.append(f"{label} applied action requires source `{source['path']}` to be absent")
    if atoms_by_key.get(source["atom_key"]):
        errors.append(f"{label} applied source atom_key `{source['atom_key']}` still exists")
    if source["atom_key"] in active_route_keys:
        errors.append(f"{label} applied source atom_key `{source['atom_key']}` remains in selected routes")
    for owner_path in sorted(incoming.get(source["atom_key"], set())):
        errors.append(f"{label} applied source atom_key `{source['atom_key']}` is still targeted by `{owner_path}`")
    target = manifest["target"]
    if manifest["action"] == "merge":
        target_runtime = runtime.get(target["path"]) if target is not None else None
        if target_runtime is None or target_runtime.get("expected_state") != "present":
            errors.append(f"{label} applied merge requires approved target to be present")
    for owner in manifest["owners"]:
        owner_runtime = runtime.get(owner["path"])
        if owner_runtime is None or owner_runtime.get("expected_state") != "present":
            errors.append(f"{label} applied action requires reference owner `{owner['path']}` to be present")


def scan_operation_atoms(
    config: Config, errors: list[str]
) -> tuple[list[Atom], dict[str, Atom], dict[str, list[Atom]], dict[str, set[str]]]:
    atoms: list[Atom] = []
    for path in sorted(config.docs_root.rglob("*-atom.md")) if config.docs_root.is_dir() else []:
        local_errors: list[str] = []
        atom = parse_atom(path, config, local_errors)
        if atom is None or local_errors:
            errors.extend(f"operation artifact closure: {error}" for error in local_errors)
        if atom is not None:
            atoms.append(atom)
    by_path = {atom.rel_path: atom for atom in atoms}
    by_key: dict[str, list[Atom]] = {}
    incoming: dict[str, set[str]] = {}
    for atom in atoms:
        by_key.setdefault(atom.atom_key, []).append(atom)
        for edge in atom.edges:
            target_key = edge.get("target_key")
            if target_key:
                incoming.setdefault(target_key, set()).add(atom.rel_path)
    return atoms, by_path, by_key, incoming


def validate_present_managed_member(
    label: str,
    rel_path: str | None,
    path: Path | None,
    atom_key: str | None,
    digest: str | None,
    atoms_by_path: dict[str, Atom],
    errors: list[str],
) -> None:
    if rel_path is None or path is None:
        return
    atom = atoms_by_path.get(rel_path)
    if atom is None:
        errors.append(f"{label} expected managed path `{rel_path}` to exist")
        return
    if atom_key is not None and atom.atom_key != atom_key:
        errors.append(f"{label} expected atom_key `{atom_key}`, got `{atom.atom_key}`")
    if digest is not None and sha256_file(path) != digest:
        errors.append(f"{label} current hash does not match `last_operation_sha256`")


def managed_atom_path(
    value: Any, label: str, config: Config, errors: list[str]
) -> tuple[str | None, Path | None]:
    text = nonempty_string(value)
    relative = safe_relative(text) if text is not None else None
    if relative is None or relative == Path(".") or not relative.as_posix().endswith("-atom.md"):
        errors.append(f"{label} `path` must be a safe managed-docs-relative `*-atom.md` path")
        return None, None
    path = (config.docs_root / relative).resolve()
    if not inside(config.docs_root, path):
        errors.append(f"{label} `path` must stay inside managed docs root")
        return None, None
    return relative.as_posix(), path


def request_rollback_path(
    value: Any,
    label: str,
    request_root: Path,
    errors: list[str],
    *,
    field: str = "rollback_path",
) -> Path | None:
    text = nonempty_string(value)
    relative = safe_relative(text) if text is not None else None
    if relative is None or not relative.parts or relative.parts[0] != "rollback":
        errors.append(f"{label} `{field}` must stay under request-relative `rollback/`")
        return None
    path = (request_root / relative).resolve()
    if not inside(request_root / "rollback", path):
        errors.append(f"{label} `{field}` must stay under request-relative `rollback/`")
        return None
    return path


def validate_file_hash(
    path: Path | None, expected: str | None, label: str, errors: list[str]
) -> None:
    if path is None or expected is None:
        return
    if not path.is_file():
        errors.append(f"{label} file is missing")
        return
    if sha256_file(path) != expected:
        errors.append(f"{label} hash does not match approved preimage")


def lower_kebab_value(value: Any, label: str, errors: list[str]) -> str | None:
    text = nonempty_string(value)
    if text is None or not ATOM_KEY_RE.fullmatch(text):
        errors.append(f"{label} must be lower-kebab-case")
        return None
    return text


def validate_object_keys(
    value: dict[str, Any],
    allowed: set[str],
    required: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    for key in unknown:
        errors.append(f"{label} has unsupported field `{key}`")
    for key in missing:
        errors.append(f"{label} is missing required field `{key}`")


def sha256_value(value: Any, label: str, errors: list[str]) -> str | None:
    text = nonempty_string(value)
    if text is None or not SHA256_RE.fullmatch(text):
        errors.append(f"{label} must be a lowercase 64-character SHA-256")
        return None
    return text


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def managed_path_in_scope(rel_path: str, accepted_domains: set[str]) -> bool:
    path = Path(rel_path)
    for raw_domain in accepted_domains:
        domain = safe_relative(raw_domain)
        if domain is None:
            continue
        if domain == Path(".") or path == domain or domain in path.parents:
            return True
    return False


def validate_created_path_untracked(
    config: Config,
    rel_path: str,
    source_commit: str | None,
    label: str,
    errors: list[str],
) -> None:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    root_result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(config.docs_root),
            "rev-parse",
            "--show-toplevel",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if root_result.returncode != 0:
        errors.append(
            f"{label} cannot prove creation provenance because managed docs are not in Git"
        )
        return
    git_root = Path(root_result.stdout.strip()).resolve()
    managed_path = (config.docs_root / rel_path).resolve()
    try:
        git_path = managed_path.relative_to(git_root).as_posix()
    except ValueError:
        errors.append(f"{label} managed path is outside its Git worktree")
        return

    fixed_revision = resolve_managed_docs_revision(
        config, git_root, source_commit, env
    )
    if fixed_revision is None:
        errors.append(
            f"{label} cannot bind creation provenance to `source_commit_observed`"
        )
    elif git_path_exists(git_root, fixed_revision, git_path, env):
        errors.append(
            f"{label} path `{rel_path}` exists at the operation's fixed docs revision"
        )

    tracked = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(git_root),
            "ls-files",
            "--error-unmatch",
            "--",
            git_path,
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode == 0:
        errors.append(
            f"{label} path `{rel_path}` is already tracked and is not operation-created"
        )

    if git_path_exists(git_root, "HEAD", git_path, env):
        errors.append(
            f"{label} path `{rel_path}` already exists in managed docs Git HEAD"
        )


def resolve_managed_docs_revision(
    config: Config,
    managed_git_root: Path,
    source_commit: str | None,
    env: dict[str, str],
) -> str | None:
    if source_commit is None or not COMMIT_RE.fullmatch(source_commit):
        return None
    if git_commit_exists(managed_git_root, source_commit):
        return source_commit
    if config.storage_mode != "submodule":
        return None

    source_root_result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(config.source_root),
            "rev-parse",
            "--show-toplevel",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if source_root_result.returncode != 0:
        return None
    source_git_root = Path(source_root_result.stdout.strip()).resolve()
    try:
        docs_path = config.docs_root.relative_to(source_git_root).as_posix()
    except ValueError:
        return None
    tree_result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(source_git_root),
            "ls-tree",
            source_commit,
            "--",
            docs_path,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if tree_result.returncode != 0:
        return None
    fields = tree_result.stdout.strip().split(None, 3)
    if len(fields) < 3 or fields[0] != "160000" or fields[1] != "commit":
        return None
    revision = fields[2]
    return revision if git_commit_exists(managed_git_root, revision) else None


def git_path_exists(
    git_root: Path,
    revision: str,
    git_path: str,
    env: dict[str, str],
) -> bool:
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(git_root),
            "cat-file",
            "-e",
            f"{revision}:{git_path}",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def inventory_mentions_candidate(text: str | None, candidate_id: str) -> bool:
    if text is None:
        return False
    return re.search(rf"`{re.escape(candidate_id)}`", text) is not None


def validate_created_state_snapshot(
    path: Path | None,
    current_state: dict[str, Any],
    identity: dict[str, str] | None,
    label: str,
    errors: list[str],
) -> None:
    if path is None or not path.is_file() or identity is None:
        return
    snapshot = read_json(path, f"{label} operation-state rollback", errors)
    if snapshot is None:
        return
    validate_state_snapshot_completeness(
        snapshot,
        current_state,
        label,
        errors,
        active_created_path=identity["path"],
        active_candidate_id=identity["candidate_id"],
        active_atom_key=identity["atom_key"],
        active_semantic_paths={identity["path"]},
    )
    artifacts = snapshot.get("operation_created_artifacts")
    match = None
    if isinstance(artifacts, list):
        match = next(
            (
                item
                for item in artifacts
                if isinstance(item, dict) and item.get("path") == identity["path"]
            ),
            None,
        )
    if not isinstance(match, dict) or any(
        match.get(field) != identity[field]
        for field in (
            "candidate_id",
            "atom_key",
            "created_attempt_id",
            "last_operation_sha256",
        )
    ) or match.get("status") != "present":
        errors.append(
            f"{label} operation-state rollback does not contain the pre-removal artifact state"
        )
    selection = snapshot.get("context_selection")
    candidates = selection.get("candidates") if isinstance(selection, dict) else None
    candidate = None
    if isinstance(candidates, list):
        candidate = next(
            (
                item
                for item in candidates
                if isinstance(item, dict)
                and item.get("candidate_id") == identity["candidate_id"]
            ),
            None,
        )
    candidate_keys = candidate.get("candidate_atom_keys") if isinstance(candidate, dict) else None
    if (
        not isinstance(candidate, dict)
        or candidate.get("disposition") != "write"
        or not isinstance(candidate_keys, list)
        or identity["atom_key"] not in candidate_keys
    ):
        errors.append(
            f"{label} operation-state rollback does not contain the pre-removal write candidate"
        )


def validate_action_state_snapshot(
    path: Path | None,
    current_state: dict[str, Any],
    action_id: str,
    manifest: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if path is None or not path.is_file():
        return
    snapshot = read_json(path, f"{label} operation-state rollback", errors)
    if snapshot is None:
        return
    validate_state_snapshot_completeness(
        snapshot,
        current_state,
        label,
        errors,
        active_action_id=action_id,
        active_semantic_paths=action_manifest_paths(manifest),
    )
    actions = snapshot.get("approved_existing_actions")
    action = None
    if isinstance(actions, list):
        action = next(
            (
                item
                for item in actions
                if isinstance(item, dict) and item.get("action_id") == action_id
            ),
            None,
        )
    if not snapshot_action_matches(action, action_id, manifest):
        errors.append(
            f"{label} operation-state rollback does not contain the approved action manifest"
        )

    executions = snapshot.get("action_execution")
    execution = None
    if isinstance(executions, list):
        execution = next(
            (
                item
                for item in executions
                if isinstance(item, dict) and item.get("action_id") == action_id
            ),
            None,
        )
    validate_snapshot_approved_execution(execution, label, errors)
    members = execution.get("members") if isinstance(execution, dict) else None
    runtime_by_path = {
        item.get("path"): item
        for item in members
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    } if isinstance(members, list) else {}
    expected_members: dict[str, tuple[str, dict[str, str]]] = manifest["members"]
    runtime_valid = (
        isinstance(execution, dict)
        and execution.get("status") == "approved"
        and execution.get("approved_action_fingerprint") == manifest["fingerprint"]
        and set(runtime_by_path) == set(expected_members)
    )
    if runtime_valid:
        for member_path, (role, immutable) in expected_members.items():
            member = runtime_by_path[member_path]
            if (
                member.get("role") != role
                or member.get("atom_key") != immutable["atom_key"]
                or member.get("expected_state") != "present"
                or member.get("last_operation_sha256") != immutable["preimage_sha256"]
            ):
                runtime_valid = False
                break
    if not runtime_valid:
        errors.append(
            f"{label} operation-state rollback does not contain the pre-mutation execution state"
        )


def validate_snapshot_approved_execution(
    execution: Any,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(execution, dict):
        return
    execution_label = f"{label} snapshot approved execution"
    validate_object_keys(
        execution,
        {"action_id", "approved_action_fingerprint", "status", "members"},
        {"action_id", "approved_action_fingerprint", "status", "members"},
        execution_label,
        errors,
    )
    if execution.get("status") != "approved":
        errors.append(f"{execution_label} status must be `approved`")
    members = execution.get("members")
    if not isinstance(members, list):
        errors.append(f"{execution_label} members must be a list")
        return
    for index, member in enumerate(members, start=1):
        member_label = f"{execution_label} member {index}"
        if not isinstance(member, dict):
            errors.append(f"{member_label} must be an object")
            continue
        validate_object_keys(
            member,
            {
                "role",
                "atom_key",
                "path",
                "expected_state",
                "last_operation_sha256",
            },
            {
                "role",
                "atom_key",
                "path",
                "expected_state",
                "last_operation_sha256",
            },
            member_label,
            errors,
        )
        if member.get("role") not in {"source", "target", "reference_owner"}:
            errors.append(f"{member_label} has invalid role")
        lower_kebab_value(
            member.get("atom_key"), f"{member_label} `atom_key`", errors
        )
        path_text = nonempty_string(member.get("path"))
        path = safe_relative(path_text) if path_text is not None else None
        if path is None or not path.as_posix().endswith("-atom.md"):
            errors.append(f"{member_label} path must be a safe *-atom.md path")
        if member.get("expected_state") != "present":
            errors.append(f"{member_label} expected_state must be `present`")
        sha256_value(
            member.get("last_operation_sha256"),
            f"{member_label} `last_operation_sha256`",
            errors,
        )


def validate_state_snapshot_completeness(
    snapshot: dict[str, Any],
    current_state: dict[str, Any],
    label: str,
    errors: list[str],
    *,
    active_created_path: str | None = None,
    active_candidate_id: str | None = None,
    active_atom_key: str | None = None,
    active_action_id: str | None = None,
    active_semantic_paths: set[str] | None = None,
) -> None:
    required = {
        "accepted_scope",
        "source_commit_observed",
        "context_selection",
        "bundle_queue",
        "risk_triggers",
    }
    missing_required = sorted(required - set(snapshot))
    if missing_required:
        errors.append(
            f"{label} operation-state rollback is missing core field(s): "
            + ", ".join(missing_required)
        )
    missing_current = sorted(set(current_state) - set(snapshot))
    if missing_current:
        errors.append(
            f"{label} operation-state rollback is not a complete work-state snapshot; "
            "missing current field(s): " + ", ".join(missing_current)
        )
    active_state_owners = {
        "context_selection",
        "bundle_queue",
        "risk_triggers",
        "operation_created_artifacts",
        "approved_existing_actions",
        "action_execution",
        "semantic_review_closure",
        "operation_metrics",
        "shared_contracts",
        "selection_readiness",
        "late_shared_contract_discoveries",
        "semantic_fail_diagnostics",
        "selection_retirements",
        "dispatch_control",
    }
    for field in sorted((set(snapshot) | set(current_state)) - active_state_owners):
        if (
            field not in snapshot
            or field not in current_state
            or snapshot[field] != current_state[field]
        ):
            errors.append(
                f"{label} operation-state rollback changes unrelated top-level owner `{field}`"
            )
    for field in ("accepted_scope", "source_commit_observed"):
        if snapshot.get(field) != current_state.get(field):
            errors.append(
                f"{label} operation-state rollback changes `{field}`"
            )

    identity_specs = (
        ("operation_created_artifacts", "path"),
        ("approved_existing_actions", "action_id"),
        ("action_execution", "action_id"),
    )
    for field, identity_key in identity_specs:
        current_ids = object_identity_set(current_state.get(field), identity_key)
        snapshot_ids = object_identity_set(snapshot.get(field), identity_key)
        if current_ids != snapshot_ids:
            errors.append(
                f"{label} operation-state rollback changes `{field}` membership"
            )
        for duplicate in duplicate_object_identities(
            snapshot.get(field), identity_key
        ):
            errors.append(
                f"{label} operation-state rollback repeats `{field}` identity "
                f"`{duplicate}`"
            )
    for duplicate in duplicate_object_identities(
        snapshot.get("operation_created_artifacts"), "atom_key"
    ):
        errors.append(
            f"{label} operation-state rollback repeats operation-created atom_key "
            f"`{duplicate}`"
        )
    if operation_artifact_identity_map(
        current_state.get("operation_created_artifacts")
    ) != operation_artifact_identity_map(snapshot.get("operation_created_artifacts")):
        errors.append(
            f"{label} operation-state rollback changes operation-created provenance"
        )
    if immutable_action_map(
        current_state.get("approved_existing_actions")
    ) != immutable_action_map(snapshot.get("approved_existing_actions")):
        errors.append(
            f"{label} operation-state rollback changes an immutable approved action"
        )
    if execution_identity_map(
        current_state.get("action_execution")
    ) != execution_identity_map(snapshot.get("action_execution")):
        errors.append(
            f"{label} operation-state rollback changes action execution membership"
        )
    if exact_object_map(
        current_state.get("operation_created_artifacts"),
        "path",
        exclude=active_created_path,
    ) != exact_object_map(
        snapshot.get("operation_created_artifacts"),
        "path",
        exclude=active_created_path,
    ):
        errors.append(
            f"{label} operation-state rollback changes an unrelated created artifact"
        )
    if exact_object_map(
        current_state.get("action_execution"),
        "action_id",
        exclude=active_action_id,
    ) != exact_object_map(
        snapshot.get("action_execution"),
        "action_id",
        exclude=active_action_id,
    ):
        errors.append(
            f"{label} operation-state rollback changes an unrelated action execution"
        )
    current_selection = current_state.get("context_selection")
    snapshot_selection = snapshot.get("context_selection")
    current_selection_version = (
        current_selection.get("version")
        if isinstance(current_selection, dict)
        else None
    )
    snapshot_selection_version = (
        snapshot_selection.get("version")
        if isinstance(snapshot_selection, dict)
        else None
    )
    if current_selection_version != "4" or snapshot_selection_version != "4":
        errors.append(
            f"{label} operation-state rollback requires context selection version `4`"
        )
    else:
        validate_v4_owner_readiness_progression(snapshot, current_state, label, errors)
    current_closure = current_state.get("semantic_review_closure")
    snapshot_closure = snapshot.get("semantic_review_closure")
    if isinstance(current_closure, dict) and isinstance(snapshot_closure, dict):
        validate_semantic_closure_progression(
            snapshot_closure,
            current_closure,
            label,
            errors,
        )
    snapshot_metrics = snapshot.get("operation_metrics")
    current_metrics = current_state.get("operation_metrics")
    if isinstance(snapshot_metrics, dict) and isinstance(current_metrics, dict):
        validate_operation_metrics_progression(
            snapshot_metrics,
            current_metrics,
            label,
            errors,
        )
    current_candidates = (
        current_selection.get("candidates")
        if isinstance(current_selection, dict)
        else None
    )
    snapshot_candidates = (
        snapshot_selection.get("candidates")
        if isinstance(snapshot_selection, dict)
        else None
    )
    if object_identity_set(current_candidates, "candidate_id") != object_identity_set(
        snapshot_candidates, "candidate_id"
    ):
        errors.append(
            f"{label} operation-state rollback changes context candidate membership"
        )
    for duplicate in duplicate_object_identities(snapshot_candidates, "candidate_id"):
        errors.append(
            f"{label} operation-state rollback repeats context candidate id `{duplicate}`"
        )
    if object_field_map(current_candidates, "candidate_id", "domain") != object_field_map(
        snapshot_candidates, "candidate_id", "domain"
    ):
        errors.append(
            f"{label} operation-state rollback changes context candidate domain ownership"
        )
    if exact_object_map(
        current_candidates,
        "candidate_id",
        exclude=active_candidate_id,
    ) != exact_object_map(
        snapshot_candidates,
        "candidate_id",
        exclude=active_candidate_id,
    ):
        errors.append(
            f"{label} operation-state rollback changes an unrelated context candidate"
        )
    retired_contract_ids = v4_retirement_delta(snapshot, current_state)
    current_queue = normalized_bundle_queue(
        current_state.get("bundle_queue"),
        active_atom_key,
        retired_contract_ids,
    )
    snapshot_queue = normalized_bundle_queue(
        snapshot.get("bundle_queue"),
        active_atom_key,
        retired_contract_ids,
    )
    if current_queue != snapshot_queue:
        errors.append(
            f"{label} operation-state rollback changes unrelated bundle queue state"
        )
    current_risk = normalized_risk_triggers(
        current_state.get("risk_triggers"),
        active_candidate_id,
        active_atom_key,
        retired_contract_ids,
    )
    snapshot_risk = normalized_risk_triggers(
        snapshot.get("risk_triggers"),
        active_candidate_id,
        active_atom_key,
        retired_contract_ids,
    )
    if current_risk != snapshot_risk:
        errors.append(
            f"{label} operation-state rollback changes unrelated risk routing"
        )
    validate_snapshot_semantic_mutation_guard(
        snapshot,
        current_state,
        active_semantic_paths or set(),
        label,
        errors,
    )
    if snapshot_selection_version == "4":
        validate_snapshot_selection_routing(snapshot, label, errors)


def action_manifest_paths(manifest: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for field in ("source", "target"):
        member = manifest.get(field)
        if isinstance(member, dict) and isinstance(member.get("path"), str):
            paths.add(member["path"])
    owners = manifest.get("reference_owners")
    if isinstance(owners, list):
        for owner in owners:
            if isinstance(owner, dict) and isinstance(owner.get("path"), str):
                paths.add(owner["path"])
    return paths


def validate_semantic_closure_progression(
    snapshot: dict[str, Any],
    current: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if snapshot.get("version") != current.get("version"):
        errors.append(
            f"{label} operation-state rollback changes semantic review closure version"
        )
    snapshot_basis = snapshot.get("basis_revision")
    current_basis = current.get("basis_revision")
    if (
        type(snapshot_basis) is int
        and type(current_basis) is int
        and snapshot_basis > current_basis
    ):
        errors.append(
            f"{label} operation-state rollback semantic basis exceeds current revision"
        )

    snapshot_reviews = semantic_objects_by_id(snapshot.get("review_passes"), "review_id")
    current_reviews = semantic_objects_by_id(current.get("review_passes"), "review_id")
    status_transitions = {
        "current": {"current", "stale", "superseded"},
        "stale": {"stale", "superseded"},
        "superseded": {"superseded"},
    }
    for review_id, prior in snapshot_reviews.items():
        review = current_reviews.get(review_id)
        if review is None:
            errors.append(
                f"{label} operation-state rollback semantic history drops review PASS "
                f"`{review_id}`"
            )
            continue
        for field in ("reviewer_role", "scope", "basis_revision", "verdict"):
            if review.get(field) != prior.get(field):
                errors.append(
                    f"{label} operation-state rollback rewrites semantic review "
                    f"`{review_id}` field `{field}`"
                )
        prior_status = prior.get("status")
        if review.get("status") not in status_transitions.get(prior_status, set()):
            errors.append(
                f"{label} operation-state rollback reverses semantic review "
                f"`{review_id}` status"
            )

    snapshot_invalidations = semantic_objects_by_id(
        snapshot.get("invalidations"), "invalidation_id"
    )
    current_invalidations = semantic_objects_by_id(
        current.get("invalidations"), "invalidation_id"
    )
    for invalidation_id, prior in snapshot_invalidations.items():
        invalidation = current_invalidations.get(invalidation_id)
        if invalidation is None:
            errors.append(
                f"{label} operation-state rollback semantic history drops invalidation "
                f"`{invalidation_id}`"
            )
            continue
        if prior.get("status") == "resolved":
            if invalidation != prior:
                errors.append(
                    f"{label} operation-state rollback rewrites resolved semantic "
                    f"invalidation `{invalidation_id}`"
                )
            continue
        for field in ("trigger", "opened_revision"):
            if invalidation.get(field) != prior.get(field):
                errors.append(
                    f"{label} operation-state rollback rewrites semantic invalidation "
                    f"`{invalidation_id}` field `{field}`"
                )
        prior_cause = prior.get("cause")
        current_cause = invalidation.get("cause")
        if (
            isinstance(prior_cause, str)
            and isinstance(current_cause, str)
            and not current_cause.startswith(prior_cause)
        ):
            errors.append(
                f"{label} operation-state rollback replaces semantic invalidation "
                f"`{invalidation_id}` cause instead of appending it"
            )
        prior_artifacts = semantic_artifact_set(prior.get("affected_artifacts"))
        current_artifacts = semantic_artifact_set(
            invalidation.get("affected_artifacts")
        )
        prior_bundles = semantic_string_set(prior.get("affected_bundles"))
        current_bundles = semantic_string_set(invalidation.get("affected_bundles"))
        prior_stale_ids = semantic_string_set(prior.get("stale_review_ids"))
        current_stale_ids = semantic_string_set(invalidation.get("stale_review_ids"))
        prior_required = semantic_required_review_set(prior.get("required_reviews"))
        current_required = semantic_required_review_set(
            invalidation.get("required_reviews")
        )
        semantic_subset(
            prior_artifacts,
            current_artifacts,
            f"{label} operation-state rollback shrinks semantic invalidation "
            f"`{invalidation_id}` affected artifacts",
            errors,
        )
        semantic_subset(
            prior_bundles,
            current_bundles,
            f"{label} operation-state rollback shrinks semantic invalidation "
            f"`{invalidation_id}` affected bundles",
            errors,
        )
        semantic_subset(
            prior_stale_ids,
            current_stale_ids,
            f"{label} operation-state rollback shrinks semantic invalidation "
            f"`{invalidation_id}` stale review IDs",
            errors,
        )
        semantic_subset(
            prior_required,
            current_required,
            f"{label} operation-state rollback shrinks semantic invalidation "
            f"`{invalidation_id}` required reviews",
            errors,
        )
        expanded = (
            current_cause != prior_cause
            or current_artifacts > prior_artifacts
            or current_bundles > prior_bundles
            or current_stale_ids > prior_stale_ids
            or current_required > prior_required
        )
        if (
            expanded
            and type(snapshot_basis) is int
            and type(current_basis) is int
            and current_basis <= snapshot_basis
        ):
            errors.append(
                f"{label} operation-state rollback expands semantic invalidation "
                f"`{invalidation_id}` without advancing basis revision"
            )
        if invalidation.get("status") not in {"open", "resolved"}:
            errors.append(
                f"{label} operation-state rollback invalidates semantic transition "
                f"for `{invalidation_id}`"
            )

    snapshot_gate = snapshot.get("final_gate")
    current_gate = current.get("final_gate")
    if (
        isinstance(snapshot_gate, dict)
        and isinstance(current_gate, dict)
        and snapshot_gate.get("required") is True
        and current_gate.get("required") is not True
    ):
        errors.append(
            f"{label} operation-state rollback disables a required semantic final gate"
        )
    if isinstance(snapshot_gate, dict) and isinstance(current_gate, dict):
        snapshot_history = snapshot_gate.get("review_history")
        current_history = current_gate.get("review_history")
        if isinstance(snapshot_history, list) and isinstance(current_history, list):
            if current_history[: len(snapshot_history)] != snapshot_history:
                errors.append(
                    f"{label} operation-state rollback rewrites semantic final gate history"
                )


def validate_v4_owner_readiness_progression(
    snapshot: dict[str, Any],
    current: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    snapshot_readiness = snapshot.get("selection_readiness")
    current_readiness = current.get("selection_readiness")
    if not isinstance(snapshot_readiness, dict) or not isinstance(current_readiness, dict):
        return
    snapshot_basis = snapshot_readiness.get("basis_revision")
    current_basis = current_readiness.get("basis_revision")
    if (
        type(snapshot_basis) is int
        and type(current_basis) is int
        and snapshot_basis > current_basis
    ):
        errors.append(f"{label} operation-state rollback readiness basis exceeds current")

    _, retired_contract_ids = validate_v4_retirement_progression(
        snapshot, current, label, errors
    )

    snapshot_reviews = semantic_objects_by_id(snapshot_readiness.get("reviews"), "review_id")
    current_reviews = semantic_objects_by_id(current_readiness.get("reviews"), "review_id")
    validate_v4_append_only_records(
        snapshot_readiness.get("reviews"),
        current_readiness.get("reviews"),
        "review_id",
        {"status"},
        f"{label} readiness reviews",
        errors,
    )
    readiness_transitions = {
        "current": {"current", "stale", "superseded"},
        "stale": {"stale", "superseded"},
        "superseded": {"superseded"},
    }
    for review_id, prior in snapshot_reviews.items():
        review = current_reviews.get(review_id)
        if review is None:
            errors.append(
                f"{label} operation-state rollback drops readiness review `{review_id}`"
            )
            continue
        for field in (
            "reviewer_role",
            "reviewer_agent_id",
            "basis_revision",
            "verdict",
        ):
            if review.get(field) != prior.get(field):
                errors.append(
                    f"{label} operation-state rollback rewrites readiness review "
                    f"`{review_id}` field `{field}`"
                )
        if review.get("status") not in readiness_transitions.get(
            prior.get("status"), set()
        ):
            errors.append(
                f"{label} operation-state rollback reverses readiness review `{review_id}`"
            )

    snapshot_contracts = semantic_objects_by_id(
        snapshot.get("shared_contracts"), "contract_id"
    )
    current_contracts = semantic_objects_by_id(
        current.get("shared_contracts"), "contract_id"
    )
    current_discoveries = current.get("late_shared_contract_discoveries")
    if not isinstance(current_discoveries, list):
        current_discoveries = []
    for contract_id, prior in snapshot_contracts.items():
        contract = current_contracts.get(contract_id)
        if contract is None:
            if contract_id not in retired_contract_ids:
                errors.append(
                    f"{label} operation-state rollback drops shared contract "
                    f"`{contract_id}`"
                )
        elif contract != prior and not any(
            isinstance(discovery, dict)
            and discovery.get("contract_id") == contract_id
            and type(discovery.get("basis_revision")) is int
            and type(snapshot_basis) is int
            and discovery["basis_revision"] > snapshot_basis
            for discovery in current_discoveries
        ):
            errors.append(
                f"{label} operation-state rollback rewrites shared contract "
                f"`{contract_id}` without a later discovery"
            )

    validate_v4_append_only_records(
        snapshot.get("semantic_fail_diagnostics"),
        current.get("semantic_fail_diagnostics"),
        "diagnostic_id",
        set(),
        f"{label} semantic FAIL diagnostics",
        errors,
    )
    validate_v4_append_only_records(
        snapshot.get("late_shared_contract_discoveries"),
        current.get("late_shared_contract_discoveries"),
        "discovery_id",
        {"status", "resolved_revision", "resolution_readiness_review_id"},
        f"{label} late discoveries",
        errors,
    )
    snapshot_control = snapshot.get("dispatch_control")
    current_control = current.get("dispatch_control")
    if isinstance(snapshot_control, dict) and isinstance(current_control, dict):
        validate_v4_append_only_records(
            snapshot_control.get("episodes"),
            current_control.get("episodes"),
            "episode_id",
            {
                "status",
                "diagnosis",
                "action",
                "resume_basis_revision",
                "readiness_review_id",
            },
            f"{label} dispatch episodes",
            errors,
        )


def validate_v4_retirement_progression(
    snapshot: dict[str, Any],
    current: dict[str, Any],
    label: str,
    errors: list[str],
) -> tuple[set[str], set[str]]:
    snapshot_registry = snapshot.get("selection_retirements")
    current_registry = current.get("selection_retirements")
    if not isinstance(snapshot_registry, dict) or not isinstance(current_registry, dict):
        return set(), set()
    if snapshot_registry.get("version") != current_registry.get("version"):
        errors.append(f"{label} selection retirements changes version")
    snapshot_readiness = snapshot.get("selection_readiness")
    current_readiness = current.get("selection_readiness")
    snapshot_basis = (
        snapshot_readiness.get("basis_revision")
        if isinstance(snapshot_readiness, dict)
        else None
    )
    current_basis = (
        current_readiness.get("basis_revision")
        if isinstance(current_readiness, dict)
        else None
    )

    specs = (
        (
            "retired_bundles",
            "bundle_id",
            "bundle_queue",
            {"retired_basis_revision", "reason"},
            "bundle",
        ),
        (
            "retired_contracts",
            "contract_id",
            "shared_contracts",
            {"retired_basis_revision", "reason"},
            "shared contract",
        ),
    )
    retired_id_sets: list[set[str]] = []
    appended_by_field: dict[str, list[dict[str, Any]]] = {}
    for history_field, identity_key, active_field, metadata, noun in specs:
        prior_records = snapshot_registry.get(history_field)
        current_records = current_registry.get(history_field)
        if not isinstance(prior_records, list) or not isinstance(current_records, list):
            retired_id_sets.append(set())
            continue
        prior_ids = [
            item.get(identity_key) if isinstance(item, dict) else None
            for item in prior_records
        ]
        current_ids = [
            item.get(identity_key) if isinstance(item, dict) else None
            for item in current_records
        ]
        if current_ids[: len(prior_ids)] != prior_ids:
            errors.append(f"{label} {history_field} must be append-only")
        for index, prior in enumerate(prior_records):
            if index >= len(current_records) or current_records[index] != prior:
                identity = (
                    prior.get(identity_key)
                    if isinstance(prior, dict)
                    else "<unknown>"
                )
                errors.append(
                    f"{label} {history_field} rewrites retired {noun} `{identity}`"
                )
        snapshot_active = semantic_objects_by_id(
            snapshot.get(active_field), identity_key
        )
        current_active = semantic_objects_by_id(current.get(active_field), identity_key)
        appended = current_records[len(prior_records) :]
        appended_by_field[history_field] = [
            record for record in appended if isinstance(record, dict)
        ]
        appended_ids: set[str] = set()
        for record in appended:
            if not isinstance(record, dict):
                continue
            identity = record.get(identity_key)
            if not isinstance(identity, str):
                continue
            appended_ids.add(identity)
            prior_active = snapshot_active.get(identity)
            retired_identity = {
                key: value for key, value in record.items() if key not in metadata
            }
            if not isinstance(prior_active, dict) or retired_identity != prior_active:
                errors.append(
                    f"{label} forged retired {noun} `{identity}` was not the exact "
                    "active snapshot identity"
                )
            if identity in current_active:
                errors.append(
                    f"{label} retired {noun} `{identity}` remains active in current state"
                )
            retired_basis = record.get("retired_basis_revision")
            if (
                type(retired_basis) is int
                and type(snapshot_basis) is int
                and retired_basis <= snapshot_basis
            ):
                errors.append(
                    f"{label} retired {noun} `{identity}` basis must advance beyond "
                    "the snapshot readiness basis"
                )
            if (
                type(retired_basis) is int
                and type(current_basis) is int
                and retired_basis > current_basis
            ):
                errors.append(
                    f"{label} retired {noun} `{identity}` basis exceeds current "
                    "readiness basis"
                )
        for identity in snapshot_active:
            if identity not in current_active and identity not in appended_ids:
                errors.append(
                    f"{label} drops active snapshot {noun} `{identity}` without an "
                    "append-only retirement record"
                )
        retired_id_sets.append(
            {
                value
                for value in current_ids
                if isinstance(value, str)
            }
        )
    validate_v4_retirement_semantic_obligations(
        snapshot,
        appended_by_field.get("retired_bundles", []),
        appended_by_field.get("retired_contracts", []),
        label,
        errors,
    )
    return retired_id_sets[0], retired_id_sets[1]


def validate_v4_retirement_semantic_obligations(
    snapshot: dict[str, Any],
    retired_bundles: list[dict[str, Any]],
    retired_contracts: list[dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    """Bind each reviewed retirement scope to its pre-mutation invalidation basis."""
    obligations: dict[tuple[str, int], set[str]] = {}
    retired_bundle_revisions = {
        record.get("bundle_id"): record.get("retired_basis_revision")
        for record in retired_bundles
        if isinstance(record.get("bundle_id"), str)
        and type(record.get("retired_basis_revision")) is int
    }
    snapshot_registry = snapshot.get("selection_retirements")
    snapshot_retired_bundles = (
        snapshot_registry.get("retired_bundles")
        if isinstance(snapshot_registry, dict)
        else None
    )
    earlier_retired_bundle_revisions = {
        record.get("bundle_id"): record.get("retired_basis_revision")
        for record in snapshot_retired_bundles or []
        if isinstance(record, dict)
        and isinstance(record.get("bundle_id"), str)
        and type(record.get("retired_basis_revision")) is int
    }
    for bundle_id, revision in retired_bundle_revisions.items():
        obligations.setdefault((bundle_id, revision), set()).add(
            f"retired bundle `{bundle_id}`"
        )
    for contract in retired_contracts:
        contract_id = contract.get("contract_id")
        revision = contract.get("retired_basis_revision")
        if not isinstance(contract_id, str) or type(revision) is not int:
            continue
        related_bundle_ids = [contract.get("owner_bundle_id")]
        consumer_bundle_ids = contract.get("consumer_bundle_ids")
        if isinstance(consumer_bundle_ids, list):
            related_bundle_ids.extend(consumer_bundle_ids)
        for bundle_id in related_bundle_ids:
            if not isinstance(bundle_id, str):
                continue
            earlier_revision = earlier_retired_bundle_revisions.get(bundle_id)
            if type(earlier_revision) is int and earlier_revision < revision:
                continue
            obligations.setdefault((bundle_id, revision), set()).add(
                f"retired shared contract `{contract_id}`"
            )
            bundle_revision = retired_bundle_revisions.get(bundle_id)
            if bundle_revision is not None and bundle_revision != revision:
                errors.append(
                    f"{label} retired bundle `{bundle_id}` and related shared contract "
                    f"`{contract_id}` must use the same correction basis"
                )

    closure = snapshot.get("semantic_review_closure")
    if not isinstance(closure, dict):
        return
    reviews = closure.get("review_passes")
    invalidations = closure.get("invalidations")
    if not isinstance(reviews, list) or not isinstance(invalidations, list):
        return
    for (bundle_id, revision), sources in obligations.items():
        prior_passes = [
            review
            for review in reviews
            if isinstance(review, dict)
            and review.get("reviewer_role") in {"development", "risk"}
            and review.get("scope") == bundle_id
            and review.get("status") in {"current", "stale"}
            and isinstance(review.get("review_id"), str)
            and type(review.get("basis_revision")) is int
            and review["basis_revision"] < revision
        ]
        for review in prior_passes:
            review_id = review["review_id"]
            matching_invalidations = [
                invalidation
                for invalidation in invalidations
                if isinstance(invalidation, dict)
                and invalidation.get("status") == "open"
                and invalidation.get("opened_revision") == revision
                and bundle_id
                in semantic_string_set(invalidation.get("affected_bundles"))
                and review_id
                in semantic_string_set(invalidation.get("stale_review_ids"))
            ]
            if review.get("status") != "stale" or not matching_invalidations:
                errors.append(
                    f"{label} {' and '.join(sorted(sources))} needs snapshot open "
                    f"invalidation for prior PASS `{review_id}` on bundle `{bundle_id}` "
                    f"at retirement basis {revision}"
                )
                continue
            required_pair = (review.get("reviewer_role"), bundle_id)
            if not any(
                required_pair
                in semantic_required_review_set(
                    invalidation.get("required_reviews")
                )
                for invalidation in matching_invalidations
            ):
                errors.append(
                    f"{label} retirement invalidation for prior PASS `{review_id}` "
                    f"must include required review `{required_pair[0]}`/`{bundle_id}`"
                )


def validate_v4_append_only_records(
    snapshot_value: Any,
    current_value: Any,
    identity_key: str,
    mutable_fields: set[str],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(snapshot_value, list) or not isinstance(current_value, list):
        return
    snapshot_ids = [
        item.get(identity_key) if isinstance(item, dict) else None
        for item in snapshot_value
    ]
    current_ids = [
        item.get(identity_key) if isinstance(item, dict) else None
        for item in current_value
    ]
    if current_ids[: len(snapshot_ids)] != snapshot_ids:
        errors.append(f"{label} must be append-only")
        return
    current_by_id = {
        item.get(identity_key): item
        for item in current_value
        if isinstance(item, dict) and isinstance(item.get(identity_key), str)
    }
    for prior in snapshot_value:
        if not isinstance(prior, dict) or not isinstance(prior.get(identity_key), str):
            continue
        identity = prior[identity_key]
        current_item = current_by_id.get(identity)
        if not isinstance(current_item, dict):
            continue
        for field, value in prior.items():
            if field not in mutable_fields and current_item.get(field) != value:
                errors.append(f"{label} rewrites `{identity}` field `{field}`")
        if prior.get("status") == "resolved" and current_item != prior:
            errors.append(f"{label} rewrites resolved record `{identity}`")


def validate_operation_metrics_progression(
    snapshot: dict[str, Any],
    current: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    if snapshot.get("version") != current.get("version"):
        errors.append(f"{label} operation-state rollback changes operation metrics version")
    for field in ("started_at",):
        if snapshot.get(field) != current.get(field):
            errors.append(
                f"{label} operation-state rollback rewrites operation metrics `{field}`"
            )
    snapshot_status = snapshot.get("status")
    current_status = current.get("status")
    if snapshot_status == "finished" and current != snapshot:
        errors.append(f"{label} operation-state rollback rewrites finished operation metrics")
    elif snapshot_status == "active" and current_status not in {"active", "finished"}:
        errors.append(f"{label} operation-state rollback reverses operation metrics status")

    snapshot_spans = snapshot.get("spans")
    current_spans = current.get("spans")
    if not isinstance(snapshot_spans, list) or not isinstance(current_spans, list):
        return
    snapshot_ids = [
        span.get("span_id") if isinstance(span, dict) else None
        for span in snapshot_spans
    ]
    current_ids = [
        span.get("span_id") if isinstance(span, dict) else None
        for span in current_spans
    ]
    if current_ids[: len(snapshot_ids)] != snapshot_ids:
        errors.append(
            f"{label} operation-state rollback removes or reorders operation metric spans"
        )
    current_by_id = {
        span.get("span_id"): span
        for span in current_spans
        if isinstance(span, dict) and isinstance(span.get("span_id"), str)
    }
    immutable_fields = (
        "span_id",
        "kind",
        "scope",
        "attempt_id",
        "started_at",
        "rerun_of",
        "rerun_reason",
    )
    for prior in snapshot_spans:
        if not isinstance(prior, dict) or not isinstance(prior.get("span_id"), str):
            continue
        span_id = prior["span_id"]
        span = current_by_id.get(span_id)
        if span is None:
            errors.append(
                f"{label} operation-state rollback drops operation metric span `{span_id}`"
            )
            continue
        for field in immutable_fields:
            if span.get(field) != prior.get(field) or (field in span) != (field in prior):
                errors.append(
                    f"{label} operation-state rollback rewrites operation metric span "
                    f"`{span_id}` field `{field}`"
                )
        if prior.get("status") == "finished":
            if span != prior:
                errors.append(
                    f"{label} operation-state rollback rewrites finished operation metric "
                    f"span `{span_id}`"
                )
        elif prior.get("status") == "active" and span.get("status") not in {
            "active",
            "finished",
        }:
            errors.append(
                f"{label} operation-state rollback reverses operation metric span "
                f"`{span_id}` status"
            )


def semantic_objects_by_id(value: Any, identity: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    return {
        item[identity]: item
        for item in value
        if isinstance(item, dict) and isinstance(item.get(identity), str)
    }


def semantic_artifact_set(value: Any) -> set[tuple[str, str]]:
    if not isinstance(value, list):
        return set()
    return {
        (item["location"], item["path"])
        for item in value
        if isinstance(item, dict)
        and isinstance(item.get("location"), str)
        and isinstance(item.get("path"), str)
    }


def semantic_string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def semantic_required_review_set(value: Any) -> set[tuple[str, str]]:
    if not isinstance(value, list):
        return set()
    return {
        (item["reviewer_role"], item["scope"])
        for item in value
        if isinstance(item, dict)
        and isinstance(item.get("reviewer_role"), str)
        and isinstance(item.get("scope"), str)
    }


def semantic_subset(
    prior: set[Any],
    current: set[Any],
    message: str,
    errors: list[str],
) -> None:
    if not prior.issubset(current):
        errors.append(message)


def validate_snapshot_semantic_mutation_guard(
    snapshot: dict[str, Any],
    current_state: dict[str, Any],
    active_paths: set[str],
    label: str,
    errors: list[str],
) -> None:
    if not active_paths:
        return
    selection = snapshot.get("context_selection")
    if not isinstance(selection, dict) or selection.get("version") != "4":
        return
    snapshot_closure = snapshot.get("semantic_review_closure")
    current_closure = current_state.get("semantic_review_closure")
    if not isinstance(snapshot_closure, dict) or not isinstance(current_closure, dict):
        return

    domains: set[str] = set()
    path_atom_keys: dict[str, set[str]] = {}
    operation_artifact_paths: set[str] = set()
    artifacts = snapshot.get("operation_created_artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if (
                isinstance(artifact, dict)
                and isinstance(artifact.get("path"), str)
                and isinstance(artifact.get("atom_key"), str)
            ):
                operation_artifact_paths.add(artifact["path"])
                path_atom_keys.setdefault(artifact["path"], set()).add(
                    artifact["atom_key"]
                )
    actions = snapshot.get("approved_existing_actions")
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            members = [action.get("source"), action.get("target")]
            owners = action.get("reference_owners")
            if isinstance(owners, list):
                members.extend(owners)
            for member in members:
                if (
                    isinstance(member, dict)
                    and isinstance(member.get("path"), str)
                    and isinstance(member.get("atom_key"), str)
                ):
                    path_atom_keys.setdefault(member["path"], set()).add(
                        member["atom_key"]
                    )
    atom_bundle_ids: dict[str, set[str]] = {}
    queue = snapshot.get("bundle_queue")
    if isinstance(queue, list):
        for bundle in queue:
            if not isinstance(bundle, dict) or not isinstance(
                bundle.get("bundle_id"), str
            ):
                continue
            atom_keys = bundle.get("expected_atom_keys")
            if not isinstance(atom_keys, list):
                continue
            for atom_key in atom_keys:
                if isinstance(atom_key, str):
                    atom_bundle_ids.setdefault(atom_key, set()).add(
                        bundle["bundle_id"]
                    )
    for path in sorted(active_paths):
        atom_keys = path_atom_keys.get(path, set())
        bundle_ids = {
            bundle_id
            for atom_key in atom_keys
            for bundle_id in atom_bundle_ids.get(atom_key, set())
        }
        if len(atom_keys) == 1 and len(bundle_ids) == 1:
            domains.update(bundle_ids)
        elif path in operation_artifact_paths or len(atom_keys) > 1 or len(bundle_ids) > 1:
            errors.append(
                f"{label} operation-state rollback cannot map guarded v4 path "
                f"`{path}` through one snapshot atom_key to one bundle_id"
            )

    snapshot_passes = snapshot_closure.get("review_passes")
    relevant_current: list[str] = []
    relevant_stale: dict[str, str | None] = {}
    if isinstance(snapshot_passes, list):
        for review in snapshot_passes:
            if not isinstance(review, dict):
                continue
            if review.get("reviewer_role") not in {"development", "risk"}:
                continue
            if review.get("scope") not in domains:
                continue
            review_id = review.get("review_id")
            if not isinstance(review_id, str):
                continue
            if review.get("status") == "current":
                relevant_current.append(review_id)
            elif review.get("status") == "stale":
                relevant_stale[review_id] = (
                    review.get("scope") if isinstance(review.get("scope"), str) else None
                )
    snapshot_gate = snapshot_closure.get("final_gate")
    final_history = (
        snapshot_gate.get("review_history")
        if isinstance(snapshot_gate, dict)
        else None
    )
    final_review_id = (
        final_history[-1]
        if isinstance(final_history, list)
        and final_history
        and isinstance(final_history[-1], str)
        else None
    )
    final_review = (
        next(
            (
                review
                for review in snapshot_passes
                if isinstance(review, dict)
                and review.get("review_id") == final_review_id
            ),
            None,
        )
        if isinstance(snapshot_passes, list) and isinstance(final_review_id, str)
        else None
    )
    if isinstance(final_review, dict):
        if final_review.get("status") == "current":
            relevant_current.append(final_review_id)
        elif final_review.get("status") == "stale":
            relevant_stale[final_review_id] = None
    if relevant_current:
        errors.append(
            f"{label} operation-state rollback must open semantic invalidation and "
            "stale reviewed PASS(es) before guarded mutation: "
            + ", ".join(sorted(relevant_current))
        )

    snapshot_invalidations = snapshot_closure.get("invalidations")
    snapshot_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(snapshot_invalidations, list):
        for invalidation in snapshot_invalidations:
            if not isinstance(invalidation, dict):
                continue
            invalidation_id = invalidation.get("invalidation_id")
            if isinstance(invalidation_id, str):
                snapshot_by_id[invalidation_id] = invalidation
    for review_id, review_scope in relevant_stale.items():
        if not any(
            invalidation.get("status") == "open"
            and review_id in invalidation.get("stale_review_ids", [])
            and semantic_invalidation_affects_paths(invalidation, active_paths)
            and (
                review_scope is None
                or review_scope
                in semantic_string_set(invalidation.get("affected_bundles"))
            )
            for invalidation in snapshot_by_id.values()
        ):
            errors.append(
                f"{label} operation-state rollback stale PASS `{review_id}` lacks an "
                "open pre-mutation invalidation for the guarded artifact"
            )

    current_invalidations = current_closure.get("invalidations")
    if not isinstance(current_invalidations, list):
        return
    for invalidation in current_invalidations:
        if not isinstance(invalidation, dict) or not semantic_invalidation_affects_paths(
            invalidation, active_paths
        ):
            continue
        invalidation_id = invalidation.get("invalidation_id")
        prior = snapshot_by_id.get(invalidation_id)
        if (
            isinstance(prior, dict)
            and prior.get("status") == "resolved"
            and invalidation == prior
        ):
            continue
        if (
            not isinstance(invalidation_id, str)
            or not isinstance(prior, dict)
            or prior.get("status") != "open"
            or not semantic_invalidation_affects_paths(prior, active_paths)
        ):
            errors.append(
                f"{label} operation-state rollback must contain open invalidation "
                f"`{invalidation_id or '<unknown>'}` before guarded mutation"
            )


def semantic_invalidation_affects_paths(
    invalidation: dict[str, Any], active_paths: set[str]
) -> bool:
    artifacts = invalidation.get("affected_artifacts")
    if not isinstance(artifacts, list):
        return False
    return any(
        isinstance(artifact, dict)
        and artifact.get("location") == "managed-docs"
        and artifact.get("path") in active_paths
        for artifact in artifacts
    )


def validate_snapshot_selection_routing(
    snapshot: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    selection = snapshot.get("context_selection")
    selection_version = selection.get("version") if isinstance(selection, dict) else None
    if selection_version != "4":
        errors.append(
            f"{label} operation-state rollback is not restorable: "
            "snapshot context_selection must use exact version `4`"
        )
        return

    local: list[str] = []
    accepted_domains = set(
        string_list(
            snapshot.get("accepted_scope"),
            "snapshot `accepted_scope`",
            local,
        )
    )
    candidates = selection.get("candidates")
    if not isinstance(candidates, list):
        local.append("snapshot context_selection.candidates must be a list")
        candidates = []

    planned_keys: set[str] = set()
    planned_key_domains: dict[str, str] = {}
    candidate_targets: dict[str, set[str]] = {}
    candidate_dispositions: dict[str, str] = {}
    candidate_domains: dict[str, str] = {}
    merge_targets: list[tuple[int, str]] = []
    for index, candidate in enumerate(candidates, start=1):
        candidate_label = f"snapshot context candidate {index}"
        if not isinstance(candidate, dict):
            local.append(f"{candidate_label} must be an object")
            continue
        candidate_id = lower_kebab_value(
            candidate.get("candidate_id"),
            f"{candidate_label} `candidate_id`",
            local,
        )
        domain = nonempty_string(candidate.get("domain"))
        if domain is None or domain not in accepted_domains:
            local.append(f"{candidate_label} domain must be inside accepted scope")
        if nonempty_string(candidate.get("candidate")) is None:
            local.append(f"{candidate_label} must include candidate description")
        if nonempty_string(candidate.get("selection_basis")) is None:
            local.append(f"{candidate_label} must include selection_basis")
        disposition = candidate.get("disposition")
        if disposition not in {"write", "merge", "drop"}:
            local.append(f"{candidate_label} has invalid disposition")
            continue
        keys = atom_key_list(candidate.get("candidate_atom_keys", []), candidate_label, local)
        merge_target = nonempty_string(candidate.get("merge_target_atom_key"))
        if candidate_id is not None:
            if candidate_id in candidate_dispositions:
                local.append(f"snapshot candidate id `{candidate_id}` appears more than once")
            candidate_dispositions[candidate_id] = disposition
            if domain is not None:
                candidate_domains[candidate_id] = domain
        if disposition == "write":
            if not keys:
                local.append(f"{candidate_label} write needs candidate_atom_keys")
            if merge_target is not None:
                local.append(f"{candidate_label} write must not set merge_target_atom_key")
            for key in keys:
                if key in planned_keys:
                    local.append(f"snapshot planned atom key `{key}` appears more than once")
                planned_keys.add(key)
                if domain is not None:
                    planned_key_domains[key] = domain
            if candidate_id is not None:
                candidate_targets[candidate_id] = set(keys)
        elif disposition == "merge":
            if keys:
                local.append(f"{candidate_label} merge must not create atom keys")
            if merge_target is None or not ATOM_KEY_RE.fullmatch(merge_target):
                local.append(f"{candidate_label} merge needs a valid target")
            else:
                merge_targets.append((index, merge_target))
                if candidate_id is not None:
                    candidate_targets[candidate_id] = {merge_target}
        else:
            if keys or merge_target is not None:
                local.append(f"{candidate_label} drop must not create or target an atom key")
            if candidate_id is not None:
                candidate_targets[candidate_id] = set()

    for index, target in merge_targets:
        if target not in planned_keys:
            local.append(
                f"snapshot context candidate {index} merge target `{target}` is not planned"
            )
    queue_keys = validate_selection_queue(
        snapshot.get("bundle_queue"),
        accepted_domains,
        planned_key_domains,
        local,
    )
    for key in sorted(planned_keys - queue_keys):
        local.append(f"snapshot planned atom key `{key}` is missing from bundle queue")
    for key in sorted(queue_keys - planned_keys):
        local.append(f"snapshot bundle atom key `{key}` has no write candidate")
    validate_selection_risk_triggers(
        snapshot.get("risk_triggers"),
        candidate_targets,
        candidate_dispositions,
        local,
    )
    validate_owner_readiness_v4(
        snapshot,
        candidate_targets,
        candidate_dispositions,
        candidate_domains,
        local,
        require_final=False,
    )
    validate_semantic_review_closure(
        snapshot,
        local,
        require_final=False,
        required_final_role=None,
    )
    validate_operation_metrics(
        snapshot,
        local,
        mode="active",
        validation_scope=None,
    )
    snapshot_artifacts = snapshot.get("operation_created_artifacts")
    if snapshot_artifacts is not None and not isinstance(snapshot_artifacts, list):
        local.append("snapshot operation_created_artifacts must be a list")
    elif isinstance(snapshot_artifacts, list):
        for index, artifact in enumerate(snapshot_artifacts, start=1):
            artifact_label = f"snapshot operation-created artifact {index}"
            if not isinstance(artifact, dict):
                local.append(f"{artifact_label} must be an object")
                continue
            validate_object_keys(
                artifact,
                {
                    "candidate_id",
                    "atom_key",
                    "path",
                    "created_attempt_id",
                    "last_operation_sha256",
                    "status",
                    "rollback_path",
                    "state_rollback_path",
                    "state_rollback_sha256",
                },
                {
                    "candidate_id",
                    "atom_key",
                    "path",
                    "created_attempt_id",
                    "last_operation_sha256",
                    "status",
                },
                artifact_label,
                local,
            )
            candidate_id = lower_kebab_value(
                artifact.get("candidate_id"),
                f"{artifact_label} `candidate_id`",
                local,
            )
            atom_key = lower_kebab_value(
                artifact.get("atom_key"),
                f"{artifact_label} `atom_key`",
                local,
            )
            path_text = nonempty_string(artifact.get("path"))
            path = safe_relative(path_text) if path_text is not None else None
            if path is None or not path.as_posix().endswith("-atom.md"):
                local.append(f"{artifact_label} path must be a safe *-atom.md path")
            if nonempty_string(artifact.get("created_attempt_id")) is None:
                local.append(f"{artifact_label} must include created_attempt_id")
            sha256_value(
                artifact.get("last_operation_sha256"),
                f"{artifact_label} `last_operation_sha256`",
                local,
            )
            domain = candidate_domains.get(candidate_id or "")
            if candidate_id is None or domain is None:
                local.append(f"{artifact_label} candidate_id does not resolve")
            elif path is None or not managed_path_in_scope(path.as_posix(), {domain}):
                local.append(f"{artifact_label} path is outside candidate domain `{domain}`")
            status = artifact.get("status")
            disposition = candidate_dispositions.get(candidate_id or "")
            if status == "present":
                for field in (
                    "rollback_path",
                    "state_rollback_path",
                    "state_rollback_sha256",
                ):
                    if field in artifact:
                        local.append(
                            f"{artifact_label} present must not set `{field}`"
                        )
                if disposition != "write" or atom_key not in candidate_targets.get(
                    candidate_id or "", set()
                ):
                    local.append(
                        f"{artifact_label} present state does not resolve to its write output"
                    )
            elif status in {"removal_pending", "removed"}:
                for field in ("rollback_path", "state_rollback_path"):
                    if nonempty_string(artifact.get(field)) is None:
                        local.append(
                            f"{artifact_label} {status} must include `{field}`"
                        )
                sha256_value(
                    artifact.get("state_rollback_sha256"),
                    f"{artifact_label} `state_rollback_sha256`",
                    local,
                )
                if disposition != "drop":
                    local.append(
                        f"{artifact_label} removal state does not resolve to a drop candidate"
                    )
            else:
                local.append(f"{artifact_label} has invalid status")
    errors.extend(
        f"{label} operation-state rollback is not restorable: {error}"
        for error in local
    )


def object_identity_set(value: Any, key: str) -> set[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return set()
    result: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            return set()
        result.add(item[key])
    return result


def duplicate_object_identities(value: Any, key: str) -> set[str]:
    if not isinstance(value, list):
        return set()
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in value:
        identity = item.get(key) if isinstance(item, dict) else None
        if not isinstance(identity, str):
            continue
        if identity in seen:
            duplicates.add(identity)
        seen.add(identity)
    return duplicates


def operation_artifact_identity_map(value: Any) -> dict[str, tuple[Any, ...]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return {}
    result: dict[str, tuple[Any, ...]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            return {}
        result[item["path"]] = (
            item.get("candidate_id"),
            item.get("atom_key"),
            item.get("created_attempt_id"),
            item.get("last_operation_sha256"),
        )
    return result


def immutable_action_map(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return {}
    result: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("action_id"), str):
            return {}
        normalized = dict(item)
        owners = normalized.get("reference_owners")
        if isinstance(owners, list):
            try:
                normalized["reference_owners"] = sorted(
                    owners, key=lambda owner: owner["path"]
                )
            except (KeyError, TypeError):
                return {}
        result[item["action_id"]] = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return result


def execution_identity_map(value: Any) -> dict[str, tuple[Any, ...]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return {}
    result: dict[str, tuple[Any, ...]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("action_id"), str):
            return {}
        members = item.get("members")
        if not isinstance(members, list):
            return {}
        member_identities: list[tuple[Any, Any, Any]] = []
        for member in members:
            if not isinstance(member, dict):
                return {}
            member_identities.append(
                (member.get("path"), member.get("role"), member.get("atom_key"))
            )
        result[item["action_id"]] = (
            item.get("approved_action_fingerprint"),
            tuple(sorted(member_identities, key=lambda member: str(member[0]))),
        )
    return result


def object_field_map(
    value: Any,
    identity_key: str,
    field: str,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return {}
    result: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get(identity_key), str):
            return {}
        result[item[identity_key]] = item.get(field)
    return result


def exact_object_map(
    value: Any,
    identity_key: str,
    *,
    exclude: str | None,
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return {}
    result: dict[str, str] = {}
    for item in value:
        identity = item.get(identity_key) if isinstance(item, dict) else None
        if not isinstance(identity, str):
            return {}
        if identity == exclude:
            continue
        result[identity] = json.dumps(
            item,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return result


def v4_retirement_delta(
    snapshot: dict[str, Any], current: dict[str, Any]
) -> set[str]:
    snapshot_registry = snapshot.get("selection_retirements")
    current_registry = current.get("selection_retirements")
    if not isinstance(snapshot_registry, dict) or not isinstance(current_registry, dict):
        return set()
    prior = snapshot_registry.get("retired_contracts")
    latest = current_registry.get("retired_contracts")
    if not isinstance(prior, list) or not isinstance(latest, list):
        return set()
    appended = latest[len(prior) :]
    contract_ids = {
        item.get("contract_id")
        for item in appended
        if isinstance(item, dict) and isinstance(item.get("contract_id"), str)
    }
    return contract_ids


def normalized_bundle_queue(
    value: Any,
    removed_key: str | None,
    retired_contract_ids: set[str] | None = None,
) -> Any:
    if not isinstance(value, list):
        return value
    retired_contract_ids = retired_contract_ids or set()
    normalized: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        keys = item.get("expected_atom_keys")
        if not isinstance(keys, list):
            normalized.append(item)
            continue
        remaining = [key for key in keys if key != removed_key]
        if not remaining:
            continue
        copy = dict(item)
        copy["expected_atom_keys"] = remaining
        dependencies = copy.get("depends_on_contract_ids")
        if isinstance(dependencies, list):
            copy["depends_on_contract_ids"] = [
                contract_id
                for contract_id in dependencies
                if contract_id not in retired_contract_ids
            ]
        normalized.append(copy)
    return normalized


def normalized_risk_triggers(
    value: Any,
    removed_candidate_id: str | None,
    removed_atom_key: str | None,
    retired_contract_ids: set[str] | None = None,
) -> Any:
    if not isinstance(value, list):
        return value
    retired_contract_ids = retired_contract_ids or set()
    remaining = [
        item
        for item in value
        if not (
            isinstance(item, dict)
            and (
                item.get("candidate_id") == removed_candidate_id
                or item.get("atom_key") == removed_atom_key
                or item.get("shared_contract_id") in retired_contract_ids
            )
        )
    ]
    return sorted(
        remaining,
        key=lambda item: json.dumps(
            item,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def snapshot_action_matches(
    action: Any,
    action_id: str,
    manifest: dict[str, Any],
) -> bool:
    if not isinstance(action, dict) or action.get("action_id") != action_id:
        return False
    source = action.get("source")
    target = action.get("target")
    owners = action.get("reference_owners")
    if (
        action.get("action") not in {"delete", "merge"}
        or not isinstance(source, dict)
        or (target is not None and not isinstance(target, dict))
        or not isinstance(owners, list)
        or not all(isinstance(owner, dict) for owner in owners)
    ):
        return False
    try:
        fingerprint = canonical_action_fingerprint(
            action_id,
            action["action"],
            source,
            target,
            owners,
        )
    except (KeyError, TypeError):
        return False
    return (
        fingerprint == manifest["fingerprint"]
        and action.get("approved_action_fingerprint") == manifest["fingerprint"]
    )


def parse_evidence_sections(
    text: str | None, path: Path, config: Config, errors: list[str]
) -> dict[str, list[str]]:
    if text is None:
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if current in sections:
                errors.append(
                    f"`{rel(config.project_root, path)}` has duplicate `## {current}` section"
                )
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


def validate_evidence_revision(text: str, source_commit: str, errors: list[str]) -> None:
    declared = EVIDENCE_COMMIT_RE.findall(text)
    if len(declared) != 1:
        errors.append(
            "evidence index must declare exactly one `source_commit_observed` line "
            "with a backticked Git hash"
        )
    elif declared[0] != source_commit:
        errors.append(
            f"evidence source commit `{declared[0]}` does not match "
            f"work-state `{source_commit}`"
        )


def validate_candidate_evidence(
    candidate_id: str, sections: dict[str, list[str]], errors: list[str]
) -> None:
    lines = sections.get(candidate_id)
    if lines is None:
        errors.append(f"evidence index is missing `## {candidate_id}`")
        return
    has_locator = any(
        re.match(r"^[ ]{0,3}[-*][ ]+`[^`]+`[ ]+\S", line) for line in lines
    )
    if not has_locator:
        errors.append(
            f"evidence section `## {candidate_id}` needs a source locator and concise relevance"
        )


def validate_evidence_markdown(text: str, errors: list[str]) -> None:
    reported: set[str] = set()
    for line in text.splitlines():
        if "\t" in line and "tab" not in reported:
            errors.append("evidence index must not contain tab characters")
            reported.add("tab")
        if RAW_HTML_RE.search(line) and "html" not in reported:
            errors.append(
                "evidence index must not contain raw HTML-like syntax"
            )
            reported.add("html")
        if ("```" in line or "~~~" in line) and "fence" not in reported:
            errors.append("evidence index must not contain fenced code")
            reported.add("fence")
        if has_indented_code_prefix(line) and "indent" not in reported:
            errors.append("evidence index must not contain indented code")
            reported.add("indent")
        if not inline_code_is_line_local(line) and "inline" not in reported:
            errors.append("evidence inline code must open and close on the same line")
            reported.add("inline")


def inline_code_is_line_local(line: str) -> bool:
    cursor = 0
    while cursor < len(line):
        opening = next_unescaped_backtick(line, cursor)
        if opening < 0:
            return True
        run_end = opening
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        marker = line[opening:run_end]
        search_from = run_end
        while True:
            closing = line.find("`", search_from)
            if closing < 0:
                return False
            closing_end = closing
            while closing_end < len(line) and line[closing_end] == "`":
                closing_end += 1
            if closing_end - closing == len(marker):
                cursor = closing_end
                break
            search_from = closing_end
    return True


def next_unescaped_backtick(value: str, start: int) -> int:
    index = value.find("`", start)
    while index >= 0:
        slash_count = 0
        cursor = index - 1
        while cursor >= 0 and value[cursor] == "\\":
            slash_count += 1
            cursor -= 1
        if slash_count % 2 == 0:
            return index
        index = value.find("`", index + 1)
    return -1


def has_indented_code_prefix(line: str) -> bool:
    remainder = line
    while True:
        blockquote = re.match(r"^ {0,3}> ?", remainder)
        if blockquote is not None:
            remainder = remainder[blockquote.end():]
            continue
        list_item = re.match(
            r"^ {0,3}(?:[-+*]|\d{1,9}[.)])(?: |(?=\t))", remainder
        )
        if list_item is not None:
            remainder = remainder[list_item.end():]
            continue
        break
    return re.match(r"^(?: {4,}| *\t)", remainder) is not None


def validate_docs(
    config: Config, errors: list[str], expected_atom_keys: list[str]
) -> tuple[list[Atom], int]:
    paths = sorted(config.docs_root.rglob("*-atom.md")) if config.docs_root.is_dir() else []
    if not paths:
        errors.append("managed docs root contains no `*-atom.md` files")
        return [], 0

    parsed_with_errors: list[tuple[Atom | None, list[str]]] = []
    for path in paths:
        local_errors: list[str] = []
        parsed_with_errors.append((parse_atom(path, config, local_errors), local_errors))
    parsed = [atom for atom, _ in parsed_with_errors if atom is not None]

    expected = set(expected_atom_keys)
    scoped = bool(expected)
    selected = [atom for atom in parsed if not scoped or atom.atom_key in expected]
    for atom, local_errors in parsed_with_errors:
        if not scoped or (atom is not None and atom.atom_key in expected):
            errors.extend(local_errors)

    by_key_members: dict[str, list[Atom]] = {}
    for atom in parsed:
        by_key_members.setdefault(atom.atom_key, []).append(atom)
    by_key = {key: members[0] for key, members in by_key_members.items()}

    relevant_keys = set(expected)
    for atom in selected:
        relevant_keys.update(edge.get("target_key", "") for edge in atom.edges)
    for key, members in by_key_members.items():
        if len(members) > 1 and (not scoped or key in relevant_keys):
            paths_text = "`, `".join(atom.rel_path for atom in members)
            errors.append(f"duplicate atom_key `{key}` in `{paths_text}`")

    for expected_key in sorted(expected):
        if not ATOM_KEY_RE.fullmatch(expected_key):
            errors.append(f"expected atom key `{expected_key}` must be lower-kebab-case")
        elif expected_key not in by_key:
            errors.append(f"expected atom key `{expected_key}` does not exist in managed docs")

    aid_count = validate_aids(parsed, errors, expected if scoped else None)
    validate_graph(selected, by_key, config, errors)
    return selected, aid_count


def parse_atom(path: Path, config: Config, errors: list[str]) -> Atom | None:
    label = rel(config.project_root, path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"cannot read `{label}`: {exc}")
        return None
    if not lines or lines[0].strip() != "---":
        errors.append(f"`{label}` must start with YAML frontmatter")
        return None
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        errors.append(f"`{label}` has unterminated YAML frontmatter")
        return None

    top, edges = parse_yaml_frontmatter(lines[1:end], label, errors)
    atom_key = top.get("atom_key", "")
    if not isinstance(atom_key, str) or not atom_key:
        errors.append(f"`{label}` frontmatter must include `atom_key`")
        return None
    if not ATOM_KEY_RE.fullmatch(atom_key):
        errors.append(f"`{label}` atom_key `{atom_key}` must be lower-kebab-case")

    body = lines[end + 1 :]
    headings = [line[3:].strip() for line in body if line.startswith("## ")]
    for section in REQUIRED_SECTIONS:
        count = headings.count(section)
        if count != 1:
            errors.append(f"`{label}` must contain exactly one `## {section}` section")
    return Atom(path, path.relative_to(config.docs_root).as_posix(), atom_key, edges, body)


def parse_yaml_frontmatter(
    lines: list[str], label: str, errors: list[str]
) -> tuple[dict[str, str], list[dict[str, str]]]:
    if yaml is None:
        errors.append("standard YAML validation requires the `PyYAML` package")
        return {}, []
    try:
        data = yaml.load("\n".join(lines), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        errors.append(f"invalid YAML frontmatter in `{label}`: {exc}")
        return {}, []
    if data is None:
        data = {}
    if not isinstance(data, dict):
        errors.append(f"`{label}` frontmatter must contain a YAML mapping")
        return {}, []

    top = {key: value for key, value in data.items() if isinstance(key, str)}
    raw_edges = data.get("graph_edges", [])
    if not isinstance(raw_edges, list):
        errors.append(f"`{label}` graph_edges must be a YAML list or `[]`")
        return top, []

    edges: list[dict[str, str]] = []
    for index, raw_edge in enumerate(raw_edges, start=1):
        if not isinstance(raw_edge, dict):
            errors.append(f"`{label}` graph edge {index} must be a YAML mapping")
            continue
        edge: dict[str, str] = {}
        for key, value in raw_edge.items():
            if not isinstance(key, str) or not isinstance(value, str):
                errors.append(f"`{label}` graph edge {index} keys and values must be strings")
                continue
            edge[key] = value
        edges.append(edge)
    return top, edges


def validate_aids(
    atoms: list[Atom], errors: list[str], scoped_keys: set[str] | None = None
) -> int:
    seen: dict[str, tuple[str, bool]] = {}
    count = 0
    for atom in atoms:
        in_scope = scoped_keys is None or atom.atom_key in scoped_keys
        current_section: str | None = None
        for line in atom.body_lines:
            if line.startswith("## "):
                heading = line[3:].strip()
                current_section = heading if heading in REQUIRED_SECTIONS else None
            for token in AID_TOKEN_RE.findall(line):
                match = AID_RE.fullmatch(token)
                if match is None:
                    if in_scope:
                        errors.append(f"`{atom.rel_path}` has malformed AID `{token}`")
                    continue
                if in_scope:
                    count += 1
                prior = seen.get(token)
                if prior is not None and (in_scope or prior[1]):
                    errors.append(
                        f"duplicate AID `{token}` in `{prior[0]}` and `{atom.rel_path}`"
                    )
                if prior is None:
                    seen[token] = (atom.rel_path, in_scope)
                elif in_scope and not prior[1]:
                    seen[token] = (prior[0], True)
                expected = SECTION_CODES[match.group("section")]
                if in_scope and current_section != expected:
                    errors.append(
                        f"`{atom.rel_path}` AID `{token}` belongs under `## {expected}`, "
                        f"not `{current_section or 'no required section'}`"
                    )
    return count


def validate_graph(
    atoms: list[Atom], by_key: dict[str, Atom], config: Config, errors: list[str]
) -> None:
    required = ("type", "target_key", "target_path", "reason")
    for atom in atoms:
        for index, edge in enumerate(atom.edges, start=1):
            for key in required:
                if not edge.get(key):
                    errors.append(f"`{atom.rel_path}` graph edge {index} must include `{key}`")
            target_key = edge.get("target_key", "")
            target_path_value = edge.get("target_path", "")
            target = by_key.get(target_key)
            if target_key and target is None:
                errors.append(
                    f"`{atom.rel_path}` graph edge {index} target_key `{target_key}` does not resolve"
                )
            target_rel = safe_relative(target_path_value)
            if target_path_value and target_rel is None:
                errors.append(
                    f"`{atom.rel_path}` graph edge {index} target_path must be docs-root-relative"
                )
                continue
            if target_rel is None:
                continue
            target_path = (config.docs_root / target_rel).resolve()
            if not inside(config.docs_root, target_path) or not target_path.is_file():
                errors.append(
                    f"`{atom.rel_path}` graph edge {index} target_path `{target_path_value}` does not exist"
                )
                continue
            if target is not None and target.path.resolve() != target_path:
                errors.append(
                    f"`{atom.rel_path}` graph edge {index} target_key `{target_key}` and "
                    f"target_path `{target_path_value}` resolve to different atoms"
                )


def validate_baseline(config: Config, errors: list[str]) -> None:
    data = read_json(
        config.baseline_path,
        rel(config.project_root, config.baseline_path),
        errors,
    )
    if data is None:
        return
    expected_keys = {"version", "source_commit", "coverage"}
    actual_keys = set(data)
    if actual_keys != expected_keys:
        errors.append(
            "source baseline must contain exactly `version`, `source_commit`, and `coverage`"
        )
    if data.get("version") != "1":
        errors.append("source baseline `version` must be `1`")
    if data.get("coverage") != "project-wide":
        errors.append("source baseline `coverage` must be `project-wide`; partial baselines are invalid")
    commit = data.get("source_commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        errors.append("source baseline `source_commit` must be a 40- or 64-character Git hash")
        return
    if not git_commit_exists(config.source_root, commit):
        errors.append(
            f"source baseline commit `{commit}` is not reachable from "
            f"`{rel(config.project_root, config.source_root)}`"
        )


def read_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing `{label}`")
        return None
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=construct_unique_json_object,
        )
    except (OSError, json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        errors.append(f"invalid JSON in `{label}`: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"`{label}` must contain a JSON object")
        return None
    return data


def read_text(path: Path, label: str, errors: list[str]) -> str | None:
    if not path.is_file():
        errors.append(f"missing `{label}`")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read `{label}`: {exc}")
        return None


def nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list of non-empty strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value, start=1):
        text = nonempty_string(item)
        if text is None:
            errors.append(f"{label} item {index} must be a non-empty string")
            continue
        result.append(text)
    return result


def atom_key_list(
    value: Any,
    label: str,
    errors: list[str],
    field: str = "candidate_atom_keys",
) -> list[str]:
    keys = string_list(value, f"{label} `{field}`", errors)
    for key in keys:
        if not ATOM_KEY_RE.fullmatch(key):
            errors.append(f"{label} atom key `{key}` must be lower-kebab-case")
    return [key for key in keys if ATOM_KEY_RE.fullmatch(key)]


def path_value(
    value: Any, label: str, errors: list[str], *, allow_dot: bool
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"atomic docs config `{label}` must be a non-empty relative path")
        return None
    path = safe_relative(value.strip())
    if path is None or (not allow_dot and path == Path(".")):
        errors.append(f"atomic docs config `{label}` must be a safe relative path")
        return None
    return path


def safe_relative(value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def git_commit_exists(source_root: Path, commit: str) -> bool:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source_root), "cat-file", "-e", f"{commit}^{{commit}}"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
