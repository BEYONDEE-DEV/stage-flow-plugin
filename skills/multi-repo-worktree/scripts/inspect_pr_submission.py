#!/usr/bin/env python3
"""Read and evaluate a Stageflow PR submission handoff without GitHub writes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SUBMITTED_SHA_PATTERN = re.compile(r"<!--\s*stageflow-submitted-sha:\s*([0-9a-fA-F]{40,64})\s*-->")
PR_FIELDS = [
    "number", "url", "state", "isDraft", "baseRefName", "headRefName",
    "headRefOid", "mergeable", "comments",
]


class InspectionError(RuntimeError):
    pass


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def load_pr(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        try:
            data = json.loads(args.input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InspectionError(f"cannot read PR fixture: {exc}") from exc
    else:
        auth = run(["gh", "auth", "status"])
        if auth.returncode != 0:
            raise InspectionError(f"gh authentication failed: {auth.stderr.strip()}")
        viewed = run([
            "gh", "pr", "view", args.pr, "--repo", args.repo,
            "--json", ",".join(PR_FIELDS),
        ])
        if viewed.returncode != 0:
            raise InspectionError(f"gh pr view failed: {viewed.stderr.strip()}")
        try:
            data = json.loads(viewed.stdout)
        except json.JSONDecodeError as exc:
            raise InspectionError(f"gh pr view returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InspectionError("PR data must be a JSON object")
    return data


def submitted_declarations(pr: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    comments = pr.get("comments")
    if not isinstance(comments, list):
        return result
    for comment in comments:
        if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
            continue
        created_at = comment.get("createdAt")
        for match in SUBMITTED_SHA_PATTERN.findall(comment["body"]):
            result.append({
                "sha": match.lower(),
                "created_at": created_at if isinstance(created_at, str) else "",
            })
    return result


def latest_declaration(declarations: list[dict[str, str]]) -> dict[str, str] | None:
    if not declarations:
        return None
    return max(
        enumerate(declarations),
        key=lambda item: (item[1]["created_at"], item[0]),
    )[1]


def evaluate(pr: dict[str, Any], expected_base: str) -> dict[str, Any]:
    failures: list[str] = []
    head = str(pr.get("headRefOid") or "").lower()
    declarations = submitted_declarations(pr)
    declared_shas = [declaration["sha"] for declaration in declarations]
    latest = latest_declaration(declarations)
    mergeable = str(pr.get("mergeable") or "UNKNOWN").upper()

    if str(pr.get("state") or "").upper() != "OPEN":
        failures.append("PR is not open")
    if pr.get("isDraft") is not False:
        failures.append("PR is still draft")
    if pr.get("baseRefName") != expected_base:
        failures.append(f"base branch mismatch: expected {expected_base!r}")
    if not head:
        failures.append("current head SHA is missing")
    elif latest is None:
        failures.append("PR has no submitted SHA declaration")
    elif latest["sha"] != head:
        failures.append("latest submitted SHA declaration does not match current head")
    if mergeable == "CONFLICTING":
        failures.append("PR has merge conflicts")

    return {
        "submitted": not failures,
        "failures": failures,
        "pr": pr.get("number"),
        "url": pr.get("url"),
        "base": pr.get("baseRefName"),
        "head_branch": pr.get("headRefName"),
        "head_sha": head or None,
        "submitted_shas": declared_shas,
        "latest_submitted_sha": latest["sha"] if latest else None,
        "submitted_declarations": declarations,
        "mergeable": mergeable,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    source = result.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Read PR JSON from a fixture")
    source.add_argument("--pr", help="PR number or URL to inspect with gh")
    result.add_argument("--repo", help="OWNER/REPO; required with --pr")
    result.add_argument("--base", required=True, help="Expected source/base branch")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.pr and not args.repo:
        print(json.dumps({"submitted": False, "error": "--repo is required with --pr"}), file=sys.stderr)
        return 2
    try:
        result = evaluate(load_pr(args), args.base)
    except (InspectionError, FileNotFoundError) as exc:
        print(json.dumps({"submitted": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["submitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
