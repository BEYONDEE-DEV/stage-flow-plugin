#!/usr/bin/env python3
"""Validate deterministic atomic-docs structure in a target project."""
from __future__ import annotations

import argparse
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
        help="Atomic Docs request id; required only for selection validation",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    if args.expect_atom_key and args.phase != "docs":
        errors.append("`--expect-atom-key` requires `--phase docs`")
    if args.phase == "selection" and not args.request_id:
        errors.append("`--phase selection` requires `--request-id`")
    if args.request_id and args.phase != "selection":
        errors.append("`--request-id` requires `--phase selection`")
    config = load_config(Path(args.root).resolve(), errors)
    atoms: list[Atom] = []
    aid_count = 0
    if config is not None:
        validate_bootstrap(config, errors)
        if args.phase == "selection" and args.request_id:
            validate_selection(config, args.request_id, errors)
        if args.phase in {"docs", "baseline"}:
            scope_keys = args.expect_atom_key if args.phase == "docs" else []
            atoms, aid_count = validate_docs(config, errors, scope_keys)
        if args.phase == "baseline":
            validate_baseline(config, errors)

    if errors:
        print(f"FAIL {args.phase}:")
        for error in errors:
            print(f"- {error}")
        return 1

    scope = " scoped" if args.expect_atom_key else ""
    detail = f" ({len(atoms)}{scope} atoms, {aid_count}{scope} AIDs)" if atoms else ""
    print(f"PASS {args.phase}: {Path(args.root).resolve()}{detail}")
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

    return Config(project_root, docs_root, source_root, baseline_path)


def validate_bootstrap(config: Config, errors: list[str]) -> None:
    if not config.docs_root.is_dir():
        errors.append(f"missing managed docs root `{rel(config.project_root, config.docs_root)}`")
    criteria = config.docs_root / "project" / "atomization-criteria.md"
    if not criteria.is_file():
        errors.append(f"missing criteria document `{rel(config.project_root, criteria)}`")
    if not config.source_root.is_dir():
        errors.append(f"missing configured source root `{rel(config.project_root, config.source_root)}`")


def validate_selection(config: Config, request_id: str, errors: list[str]) -> None:
    if not request_id.strip() or Path(request_id).name != request_id or request_id in {".", ".."}:
        errors.append("atomic docs `request_id` must be one safe path segment")
        return

    request_root = (
        config.project_root / ".stageflow" / "atomic-docs" / "requests" / request_id
    ).resolve()
    requests_root = (
        config.project_root / ".stageflow" / "atomic-docs" / "requests"
    ).resolve()
    if not inside(requests_root, request_root):
        errors.append("atomic docs `request_id` must stay inside the requests root")
        return

    inventory_path = request_root / "inventory.md"
    if not inventory_path.is_file():
        errors.append(f"missing `{rel(config.project_root, inventory_path)}`")

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

    accepted_scope = string_list(
        state.get("accepted_scope"), "work-state `accepted_scope`", errors
    )
    accepted_domains = set(accepted_scope)
    if not accepted_domains:
        errors.append("work-state `accepted_scope` must contain at least one approved domain path")

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
    if context_selection.get("version") != "1":
        errors.append("work-state `context_selection.version` must be `1`")
    raw_candidates = context_selection.get("candidates")
    if not isinstance(raw_candidates, list):
        errors.append("work-state `context_selection.candidates` must be a list")
        return

    planned_keys: set[str] = set()
    planned_key_domains: dict[str, str] = {}
    pending_merge_targets: list[tuple[int, str]] = []
    candidate_targets: dict[str, set[str]] = {}
    candidate_dispositions: dict[str, str] = {}
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

    validate_selection_risk_triggers(
        state.get("risk_triggers", []), candidate_targets, candidate_dispositions, errors
    )


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
) -> None:
    if not isinstance(value, list):
        errors.append("work-state `risk_triggers` must be a list")
        return
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
        triggers = string_list(item.get("triggers"), f"{label} `triggers`", errors)
        if not triggers:
            errors.append(f"{label} must include at least one trigger")
        if nonempty_string(item.get("basis")) is None:
            errors.append(f"{label} must include non-empty `basis`")


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
