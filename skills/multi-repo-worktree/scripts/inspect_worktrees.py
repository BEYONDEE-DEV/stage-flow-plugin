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


def bundle_info(root: Path, worktree_path: Path) -> tuple[str, Path, str] | None:
    try:
        rel = worktree_path.relative_to(root)
    except ValueError:
        return None
    if len(rel.parts) >= 3 and rel.parts[0] == "worktrees":
        bundle_rel = Path(*rel.parts[:2]).as_posix()
        bundle_base = root / rel.parts[0] / rel.parts[1]
        folder_rel = Path(*rel.parts[2:]).as_posix()
        return bundle_rel, bundle_base, folder_rel
    if root.parent.name == "worktrees" and rel.parts:
        return f"worktrees/{root.name}", root, rel.as_posix()
    if rel.parts:
        return "workspace", root, rel.as_posix()
    return "workspace", root, "."


def source_branch_for(root: Path, group: dict[str, Any], current_path: Path) -> str:
    branches: set[str] = set()
    for wt in group["worktrees"]:
        path_text = wt.get("path")
        if not path_text:
            continue
        path = Path(path_text)
        if path == current_path:
            continue
        info = bundle_info(root, path)
        branch = wt.get("branch", "-")
        if info and info[0] == "workspace" and branch not in {"-", "(detached)"}:
            branches.add(branch)
    if len(branches) == 1:
        return f"{next(iter(branches))} (추정)"
    return "확인 필요"


def print_status_block(bundle: dict[str, Any]) -> None:
    source_branches = sorted(set(bundle["source_branches"]))
    if bundle.get("source_unknown"):
        source_branch = "확인 필요"
    elif len(source_branches) == 1:
        source_branch = source_branches[0]
    elif source_branches:
        source_branch = "확인 필요"
    else:
        source_branch = "확인 필요"

    print(f"대상 묶음: {bundle['name']}")
    print(f"원본 브랜치: {source_branch}")
    print(f"기준 폴더: {bundle['base']}")
    print()
    for item in sorted(bundle["items"], key=lambda row: row["repo"]):
        print(
            f"{item['repo']}: 폴더 {item['folder']} / "
            f"현재 브랜치 {item['branch']} / 변경상태 {item['dirty']}"
        )


def print_markdown(data: dict[str, Any]) -> None:
    root = Path(data["root"])
    bundles: dict[str, dict[str, Any]] = {}

    for group in data["groups"]:
        for wt in group["worktrees"]:
            path_text = wt.get("path")
            if not path_text:
                continue
            path = Path(path_text)
            info = bundle_info(root, path)
            if info is None:
                continue
            name, base, folder = info
            bundle = bundles.setdefault(
                name,
                {
                    "name": name,
                    "base": str(base),
                    "items": [],
                    "source_branches": [],
                    "source_unknown": False,
                },
            )
            source_branch = source_branch_for(root, group, path)
            if source_branch != "확인 필요":
                bundle["source_branches"].append(source_branch)
            else:
                bundle["source_unknown"] = True
            bundle["items"].append(
                {
                    "repo": Path(folder).parts[0] if folder != "." else path.name,
                    "folder": folder,
                    "branch": wt.get("branch", "-"),
                    "dirty": wt.get("dirty", "-"),
                }
            )

    ordered_names = sorted(bundles, key=lambda name: (not name.startswith("worktrees/"), name))
    for index, name in enumerate(ordered_names, start=1):
        if index > 1:
            print()
        print_status_block(bundles[name])


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
