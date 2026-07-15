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
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in incomplete runtimes
    yaml = None

PHASES = ("bootstrap", "selection", "docs", "baseline")
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
SEMANTIC_REVIEW_ROLES = {"development", "risk", "integration", "baseline"}
SEMANTIC_REVIEW_STATUSES = {"current", "stale", "superseded"}
SEMANTIC_INVALIDATION_TRIGGERS = {
    "candidate-disposition",
    "atom-merge",
    "ownership",
    "glossary-source",
    "shared-decision-owner",
    "graph-relationship",
    "documented-meaning",
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
    if args.phase == "selection" and not args.request_id:
        errors.append("`--phase selection` requires `--request-id`")
    if args.request_id and args.phase not in {"selection", "docs", "baseline"}:
        errors.append("`--request-id` requires `--phase selection`, `docs`, or `baseline`")
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
                validate_request_semantic_review_closure(
                    config,
                    args.request_id,
                    errors,
                    require_final=args.phase == "baseline" or not args.expect_atom_key,
                    required_final_role="baseline" if args.phase == "baseline" else None,
                )
        if args.phase == "baseline":
            validate_baseline(config, errors)

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

    validate_semantic_review_closure(
        state, errors, require_final=require_actions_final, required_final_role=None
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

    context_selection = state.get("context_selection")
    if not isinstance(context_selection, dict):
        errors.append("work-state must contain a `context_selection` object")
        return
    if context_selection.get("version") not in {"1", "2"}:
        errors.append("work-state `context_selection.version` must be `1` or `2`")
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


def validate_request_semantic_review_closure(
    config: Config,
    request_id: str,
    errors: list[str],
    *,
    require_final: bool,
    required_final_role: str | None,
) -> None:
    request_root = atomic_docs_request_root(config, request_id, errors)
    if request_root is None:
        return
    state_path = request_root / "work-state.json"
    state = read_json(state_path, rel(config.project_root, state_path), errors)
    if state is None:
        return
    validate_semantic_review_closure(
        state,
        errors,
        require_final=require_final,
        required_final_role=required_final_role,
    )


def validate_semantic_review_closure(
    state: dict[str, Any],
    errors: list[str],
    *,
    require_final: bool,
    required_final_role: str | None,
) -> None:
    selection = state.get("context_selection")
    selection_version = selection.get("version") if isinstance(selection, dict) else None
    if "semantic_review_closure" not in state:
        if selection_version == "2":
            errors.append(
                "work-state with `context_selection.version` `2` must contain "
                "`semantic_review_closure`"
            )
        return
    closure = state["semantic_review_closure"]
    if not isinstance(closure, dict):
        errors.append("work-state `semantic_review_closure` must be an object")
        return
    if selection_version != "2":
        errors.append(
            "work-state `semantic_review_closure` requires `context_selection.version` `2`"
        )
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
    accepted_domains = semantic_accepted_domains(state, errors)

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
        validate_semantic_review_scope(role, scope, accepted_domains, label, errors)
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
            if bundle not in accepted_domains:
                errors.append(
                    f"{label} affected bundle `{bundle}` is outside `accepted_scope`"
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
                role, scope, accepted_domains, review_label, errors
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


def semantic_accepted_domains(
    state: dict[str, Any], errors: list[str]
) -> set[str]:
    raw_scope = state.get("accepted_scope")
    if not isinstance(raw_scope, list):
        errors.append(
            "semantic review closure requires work-state `accepted_scope` as a list"
        )
        return set()
    domains: set[str] = set()
    for index, value in enumerate(raw_scope, start=1):
        domain = single_line_string(
            value, f"semantic review accepted scope item {index}", errors
        )
        if domain is not None:
            domains.add(domain)
    return domains


def validate_semantic_review_scope(
    role: Any,
    scope: str | None,
    accepted_domains: set[str],
    label: str,
    errors: list[str],
) -> None:
    if scope is None or role not in SEMANTIC_REVIEW_ROLES:
        return
    if role in {"development", "risk"} and scope not in accepted_domains:
        errors.append(f"{label} scope `{scope}` is outside `accepted_scope`")
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
    if snapshot_selection_version != current_selection_version:
        errors.append(
            f"{label} operation-state rollback changes context selection version"
        )
    current_closure = current_state.get("semantic_review_closure")
    snapshot_closure = snapshot.get("semantic_review_closure")
    if isinstance(current_closure, dict) and isinstance(snapshot_closure, dict):
        validate_semantic_closure_progression(
            snapshot_closure,
            current_closure,
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
    current_queue = normalized_bundle_queue(
        current_state.get("bundle_queue"), active_atom_key
    )
    snapshot_queue = normalized_bundle_queue(
        snapshot.get("bundle_queue"), active_atom_key
    )
    if current_queue != snapshot_queue:
        errors.append(
            f"{label} operation-state rollback changes unrelated bundle queue state"
        )
    current_risk = normalized_risk_triggers(
        current_state.get("risk_triggers"), active_candidate_id, active_atom_key
    )
    snapshot_risk = normalized_risk_triggers(
        snapshot.get("risk_triggers"), active_candidate_id, active_atom_key
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
    if not isinstance(selection, dict) or selection.get("version") != "2":
        return
    snapshot_closure = snapshot.get("semantic_review_closure")
    current_closure = current_state.get("semantic_review_closure")
    if not isinstance(snapshot_closure, dict) or not isinstance(current_closure, dict):
        return

    accepted_scope = snapshot.get("accepted_scope")
    domains: set[str] = set()
    if isinstance(accepted_scope, list):
        accepted = [value for value in accepted_scope if isinstance(value, str)]
        for path in active_paths:
            matches = [
                domain
                for domain in accepted
                if managed_path_in_scope(path, {domain})
            ]
            if matches:
                domains.add(max(matches, key=lambda value: len(Path(value).parts)))

    snapshot_passes = snapshot_closure.get("review_passes")
    relevant_current: list[str] = []
    relevant_stale: list[str] = []
    if isinstance(snapshot_passes, list):
        for review in snapshot_passes:
            if not isinstance(review, dict):
                continue
            if review.get("reviewer_role") != "development":
                continue
            if review.get("scope") not in domains:
                continue
            review_id = review.get("review_id")
            if not isinstance(review_id, str):
                continue
            if review.get("status") == "current":
                relevant_current.append(review_id)
            elif review.get("status") == "stale":
                relevant_stale.append(review_id)
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
            relevant_stale.append(final_review_id)
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
    for review_id in relevant_stale:
        if not any(
            invalidation.get("status") == "open"
            and review_id in invalidation.get("stale_review_ids", [])
            and semantic_invalidation_affects_paths(invalidation, active_paths)
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
    local: list[str] = []
    accepted_domains = set(
        string_list(
            snapshot.get("accepted_scope"),
            "snapshot `accepted_scope`",
            local,
        )
    )
    selection = snapshot.get("context_selection")
    if not isinstance(selection, dict) or selection.get("version") not in {"1", "2"}:
        local.append("snapshot context_selection must use version `1` or `2`")
        candidates: Any = None
    else:
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
    validate_semantic_review_closure(
        snapshot,
        local,
        require_final=False,
        required_final_role=None,
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


def normalized_bundle_queue(value: Any, removed_key: str | None) -> Any:
    if not isinstance(value, list) or removed_key is None:
        return value
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
        normalized.append(copy)
    return normalized


def normalized_risk_triggers(
    value: Any,
    removed_candidate_id: str | None,
    removed_atom_key: str | None,
) -> Any:
    if not isinstance(value, list):
        return value
    remaining = [
        item
        for item in value
        if not (
            isinstance(item, dict)
            and (
                item.get("candidate_id") == removed_candidate_id
                or item.get("atom_key") == removed_atom_key
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
