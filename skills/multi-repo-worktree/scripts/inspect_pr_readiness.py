#!/usr/bin/env python3
"""Read and evaluate immutable Stageflow PR readiness without GitHub writes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

READY_LABEL = "merge-ready"
READY_SHA_PATTERN = re.compile(r"<!--\s*stageflow-ready-sha:\s*([0-9a-fA-F]{40,64})\s*-->")
PR_FIELDS = [
    "number", "url", "isDraft", "baseRefName", "headRefName", "headRefOid",
    "labels", "reviewDecision", "statusCheckRollup", "mergeStateStatus",
    "mergeable", "comments", "updatedAt",
]
PASSING_CHECKS = {"SUCCESS", "NEUTRAL", "SKIPPED"}


class ReadinessError(RuntimeError):
    pass


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def load_pr(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        try:
            data = json.loads(args.input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReadinessError(f"cannot read PR fixture: {exc}") from exc
    else:
        auth = run(["gh", "auth", "status"])
        if auth.returncode != 0:
            raise ReadinessError(f"gh authentication failed: {auth.stderr.strip()}")
        viewed = run([
            "gh", "pr", "view", args.pr, "--repo", args.repo,
            "--json", ",".join(PR_FIELDS),
        ])
        if viewed.returncode != 0:
            raise ReadinessError(f"gh pr view failed: {viewed.stderr.strip()}")
        try:
            data = json.loads(viewed.stdout)
        except json.JSONDecodeError as exc:
            raise ReadinessError(f"gh pr view returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReadinessError("PR data must be a JSON object")
    return data


def text_values(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return [
        item[key]
        for item in items
        if isinstance(item, dict) and isinstance(item.get(key), str)
    ]


def ready_declarations(pr: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    comments = pr.get("comments")
    if not isinstance(comments, list):
        return result
    for comment in comments:
        if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
            continue
        created_at = comment.get("createdAt")
        for match in READY_SHA_PATTERN.findall(comment["body"]):
            result.append({
                "sha": match.lower(),
                "created_at": created_at if isinstance(created_at, str) else "",
            })
    return result


def check_state(item: dict[str, Any]) -> str:
    conclusion = item.get("conclusion")
    if isinstance(conclusion, str) and conclusion:
        return conclusion.upper()
    state = item.get("state") or item.get("status")
    return str(state or "UNKNOWN").upper()


def evaluate(pr: dict[str, Any], expected_base: str, require_review: bool) -> dict[str, Any]:
    failures: list[str] = []
    labels = set(text_values(pr.get("labels"), "name"))
    head = str(pr.get("headRefOid") or "").lower()
    declarations = ready_declarations(pr)
    declared_shas = [declaration["sha"] for declaration in declarations]
    checks = pr.get("statusCheckRollup")

    if pr.get("isDraft") is not False:
        failures.append("PR is still draft")
    if pr.get("baseRefName") != expected_base:
        failures.append(f"base branch mismatch: expected {expected_base!r}")
    if READY_LABEL not in labels:
        failures.append(f"missing label: {READY_LABEL}")
    if not head:
        failures.append("current head SHA is missing")
    elif head not in declared_shas:
        failures.append("current head SHA has no matching Ready SHA declaration")
    if declarations:
        if any(not declaration["created_at"] for declaration in declarations):
            failures.append("Ready SHA declaration timestamps are unavailable")
        else:
            latest = max(declarations, key=lambda declaration: declaration["created_at"])
            updated_at = pr.get("updatedAt")
            if latest["sha"] != head:
                failures.append("latest Ready SHA declaration does not match current head")
            if not isinstance(updated_at, str) or latest["created_at"] != updated_at:
                failures.append("PR changed after the latest Ready SHA declaration")
    if require_review and str(pr.get("reviewDecision") or "").upper() != "APPROVED":
        failures.append("required review is not approved")
    if not isinstance(checks, list):
        failures.append("status checks are unavailable")
        check_states: list[str] = []
    else:
        check_states = [check_state(item) for item in checks if isinstance(item, dict)]
        if not check_states:
            failures.append("no status checks were reported")
        elif any(state not in PASSING_CHECKS for state in check_states):
            failures.append("one or more status checks are pending or failing")
    if str(pr.get("mergeable") or "").upper() != "MERGEABLE":
        failures.append("PR is not currently mergeable")
    if str(pr.get("mergeStateStatus") or "").upper() != "CLEAN":
        failures.append("PR merge state is not clean")

    return {
        "ready": not failures,
        "failures": failures,
        "pr": pr.get("number"),
        "url": pr.get("url"),
        "base": pr.get("baseRefName"),
        "head_branch": pr.get("headRefName"),
        "head_sha": head or None,
        "ready_shas": declared_shas,
        "ready_declarations": declarations,
        "check_states": check_states,
        "merge_state": pr.get("mergeStateStatus"),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    source = result.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Read PR JSON from a fixture")
    source.add_argument("--pr", help="PR number or URL to inspect with gh")
    result.add_argument("--repo", help="OWNER/REPO; required with --pr")
    result.add_argument("--base", required=True, help="Expected source/base branch")
    result.add_argument("--no-require-review", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.pr and not args.repo:
        print(json.dumps({"ready": False, "error": "--repo is required with --pr"}), file=sys.stderr)
        return 2
    try:
        result = evaluate(load_pr(args), args.base, not args.no_require_review)
    except (ReadinessError, FileNotFoundError) as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
