#!/usr/bin/env python3
"""Read-only inspection for multi-repo Git worktree bundles."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".run",
    ".simple",
    ".stageflow",
    "build",
    "dist",
    "node_modules",
}


def run_git(path: Path, args: list[str]) -> str | None:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(path), *args],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def discover_candidates(root: Path, max_depth: int) -> list[Path]:
    candidates: list[Path] = []

    def walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        git_marker = path / ".git"
        if git_marker.exists():
            top_level = run_git(path, ["rev-parse", "--show-toplevel"])
            if top_level:
                candidates.append(Path(top_level).resolve())
        if depth == max_depth:
            return
        try:
            children = sorted(p for p in path.iterdir() if p.is_dir())
        except OSError:
            return
        for child in children:
            if child.name in SKIP_DIRS:
                continue
            walk(child, depth + 1)

    walk(root.resolve(), 0)
    return sorted(set(candidates))


def git_common_dir(repo: Path) -> Path | None:
    value = run_git(repo, ["rev-parse", "--git-common-dir"])
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def current_branch(path: Path) -> str:
    branch = run_git(path, ["branch", "--show-current"])
    if branch:
        return branch
    return "(detached)"


def upstream(path: Path) -> str:
    value = run_git(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    return value or "-"


def short_head(path: Path, fallback: str | None = None) -> str:
    value = run_git(path, ["rev-parse", "--short", "HEAD"])
    return value or fallback or "(no HEAD)"


def dirty_state(path: Path) -> str:
    value = run_git(path, ["status", "--porcelain"])
    if value is None:
        return "unknown"
    return "dirty" if value else "clean"


def parse_worktree_list(repo: Path) -> list[dict[str, str]]:
    output = run_git(repo, ["worktree", "list", "--porcelain"])
    if output is None:
        return []
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current:
                rows.append(current)
            current = {"path": value}
        elif key == "HEAD":
            current["head"] = value[:12]
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "bare":
            current["bare"] = "true"
        elif key == "detached":
            current["branch"] = "(detached)"
    if current:
        rows.append(current)
    return rows


def inspect(root: Path, max_depth: int) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    for repo in discover_candidates(root, max_depth):
        common = git_common_dir(repo)
        if common is None:
            continue
        key = str(common)
        if key not in groups:
            groups[key] = {
                "common_git_dir": key,
                "discovered_from": str(repo),
                "worktrees": [],
            }
            for item in parse_worktree_list(repo):
                path_text = item.get("path", "")
                path = Path(path_text)
                if path.is_dir():
                    branch = item.get("branch") or current_branch(path)
                    item.update(
                        {
                            "path": str(path),
                            "branch": branch,
                            "upstream": upstream(path),
                            "head": short_head(path, item.get("head")),
                            "dirty": dirty_state(path),
                        }
                    )
                groups[key]["worktrees"].append(item)

    ordered = sorted(groups.values(), key=lambda group: group["common_git_dir"])
    return {
        "root": str(root.resolve()),
        "repository_group_count": len(ordered),
        "worktree_count": sum(len(group["worktrees"]) for group in ordered),
        "groups": ordered,
    }


def print_markdown(data: dict[str, Any]) -> None:
    print(f"Workspace: `{data['root']}`")
    print(f"Repository groups: {data['repository_group_count']}")
    print(f"Worktrees: {data['worktree_count']}")
    for index, group in enumerate(data["groups"], start=1):
        print()
        print(f"## Repository Group {index}")
        print(f"Common git dir: `{group['common_git_dir']}`")
        print(f"Discovered from: `{group['discovered_from']}`")
        print()
        print("| Worktree Path | Branch | Upstream | HEAD | Dirty |")
        print("| --- | --- | --- | --- | --- |")
        for wt in group["worktrees"]:
            print(
                "| "
                + " | ".join(
                    [
                        f"`{wt.get('path', '-')}`",
                        wt.get("branch", "-"),
                        wt.get("upstream", "-"),
                        wt.get("head", "-"),
                        wt.get("dirty", "-"),
                    ]
                )
                + " |"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Git worktree bundle inspector.")
    parser.add_argument("--root", required=True, help="Workspace root to inspect.")
    parser.add_argument("--max-depth", type=int, default=4, help="Directory scan depth.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"--root is not a directory: {root}")
    data = inspect(root, args.max_depth)
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_markdown(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
