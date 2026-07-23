#!/usr/bin/env python3
"""Prepare and verify one Stageflow generation branch without rewriting refs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class TransitionError(RuntimeError):
    pass


GENERATION_WORKTREES_RELATIVE_PATH = Path(".stageflow-worktrees") / "generation-worktrees"


def git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise TransitionError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def object_id(repo: Path, revision: str, suffix: str = "") -> str:
    result = git(repo, "rev-parse", "--verify", f"{revision}{suffix}")
    return result.stdout.strip()


def ref_target(repo: Path, branch: str) -> str | None:
    result = git(repo, "rev-parse", "--verify", f"refs/heads/{branch}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def expected_target(branch_family: str, target_generation: int) -> str:
    if not branch_family or target_generation <= 1:
        raise TransitionError("target generation must be greater than one")
    return f"{branch_family}-stageflow-g{target_generation}"


def validate_target(repo: Path, branch: str) -> None:
    result = git(repo, "check-ref-format", "--branch", branch, check=False)
    if result.returncode != 0:
        raise TransitionError(f"invalid deterministic target branch: {branch}")


def compatible_target(repo: Path, commit: str, source_sha: str, result_tree_sha: str) -> bool:
    if object_id(repo, commit, "^{tree}") != result_tree_sha:
        return False
    if result_tree_sha == object_id(repo, source_sha, "^{tree}"):
        return commit == source_sha
    parents = git(repo, "show", "-s", "--format=%P", commit).stdout.strip().split()
    return parents == [source_sha]


def registered_worktrees(repo: Path) -> set[Path]:
    fields = git(repo, "worktree", "list", "--porcelain", "-z").stdout.split("\0")
    return {
        Path(field.removeprefix("worktree ")).resolve()
        for field in fields
        if field.startswith("worktree ")
    }


def expected_temporary_worktree(workspace_root: Path, slot: str, repository: str, target: str) -> Path:
    identity = "\0".join((slot, repository, target)).encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()
    return workspace_root.resolve() / GENERATION_WORKTREES_RELATIVE_PATH / f"{digest}.worktree"


def validate_temporary_worktree(
    repo: Path,
    value: Path,
    workspace_root: Path,
    slot: str,
    repository: str,
    target: str,
) -> Path:
    if not value.is_absolute():
        raise TransitionError("temporary generation worktree path must be absolute")
    if not workspace_root.is_absolute() or not slot or not repository:
        raise TransitionError("temporary generation worktree ownership is incomplete")
    temporary = value.resolve()
    expected = expected_temporary_worktree(workspace_root, slot, repository, target)
    if str(value) != str(expected) or temporary != expected:
        raise TransitionError(
            f"temporary generation worktree does not match its Stageflow journal identity: {expected}"
        )
    if temporary == repo or repo in temporary.parents or temporary in repo.parents:
        raise TransitionError("temporary generation worktree must be outside the repository worktree")
    return temporary


def has_untracked(repo: Path) -> bool:
    return bool(git(repo, "ls-files", "--others").stdout.strip())


def prepare_transfer_commit(
    repo: Path,
    temporary: Path,
    source: str,
    result_tree: str,
    message: str,
) -> str:
    registered = registered_worktrees(repo)
    if temporary in registered:
        if not temporary.is_dir():
            raise TransitionError(
                f"journaled temporary worktree is registered but missing: {temporary}"
            )
    else:
        if temporary.exists():
            raise TransitionError(
                f"journaled temporary path exists but is not a registered worktree: {temporary}"
            )
        temporary.parent.mkdir(parents=True, exist_ok=True)
        git(repo, "worktree", "add", "--detach", str(temporary), source)

    if git(temporary, "symbolic-ref", "-q", "HEAD", check=False).returncode == 0:
        raise TransitionError(
            f"journaled temporary worktree is not detached and will not be modified: {temporary}"
        )

    head = object_id(temporary, "HEAD")
    if head == source:
        source_tree = object_id(repo, source, "^{tree}")
        index_tree = object_id(temporary, git(temporary, "write-tree").stdout.strip(), "^{tree}")
        if index_tree not in {source_tree, result_tree}:
            raise TransitionError(
                f"journaled temporary worktree has an unexpected index tree: {temporary}"
            )
        if git(temporary, "diff", "--quiet", check=False).returncode != 0 or has_untracked(temporary):
            raise TransitionError(
                f"journaled temporary worktree has unexpected unstaged or untracked content: {temporary}"
            )
        git(
            temporary,
            "restore",
            "--source",
            result_tree,
            "--staged",
            "--worktree",
            "--",
            ":/",
        )
        if git(temporary, "write-tree").stdout.strip() != result_tree:
            raise TransitionError("temporary generation index does not match the journaled result tree")
        if git(temporary, "diff", "--quiet", check=False).returncode != 0 or has_untracked(temporary):
            raise TransitionError("temporary generation worktree does not match its exact index")
        git(temporary, "commit", "-m", message)
        commit = object_id(temporary, "HEAD")
    elif compatible_target(repo, head, source, result_tree):
        if git(temporary, "status", "--porcelain").stdout.strip() or has_untracked(temporary):
            raise TransitionError(
                f"completed temporary generation commit has additional changes: {temporary}"
            )
        commit = head
    else:
        raise TransitionError(
            f"journaled temporary worktree HEAD does not match source or result: {temporary}"
        )

    if not compatible_target(repo, commit, source, result_tree):
        raise TransitionError("normal Git commit did not produce the journaled generation commit")
    if git(temporary, "status", "--porcelain").stdout.strip() or has_untracked(temporary):
        raise TransitionError("temporary generation worktree is not clean after commit")
    remove = git(repo, "worktree", "remove", str(temporary), check=False)
    if remove.returncode != 0:
        detail = remove.stderr.strip() or remove.stdout.strip() or "unknown cleanup error"
        raise TransitionError(
            f"temporary generation worktree cleanup failed: {detail}; preserved at {temporary}"
        )
    return commit


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    from_head = object_id(repo, args.from_head)
    boundary = object_id(repo, args.boundary)
    source = object_id(repo, args.source)
    current = object_id(repo, "HEAD")
    if current != from_head:
        raise TransitionError(f"current HEAD changed: expected {from_head}, found {current}")
    ancestor = git(repo, "merge-base", "--is-ancestor", boundary, from_head, check=False)
    if ancestor.returncode != 0:
        raise TransitionError(
            "continuation boundary is not an ancestor of the current development head; "
            "no branch was changed"
        )
    target = expected_target(args.branch_family, args.target_generation)
    validate_target(repo, target)
    merge = git(
        repo,
        "merge-tree",
        "--write-tree",
        "--messages",
        "--merge-base",
        boundary,
        source,
        from_head,
        check=False,
    )
    if merge.returncode != 0:
        detail = merge.stdout.strip() or merge.stderr.strip() or "3-way tree conflict"
        raise TransitionError(f"generation tree conflicts; no branch was changed: {detail}")
    lines = merge.stdout.splitlines()
    if not lines:
        raise TransitionError("merge-tree returned no result tree")
    result_tree = lines[0].strip()
    object_id(repo, result_tree, "^{tree}")
    existing = ref_target(repo, target)
    if existing is not None and not compatible_target(repo, existing, source, result_tree):
        raise TransitionError(f"target branch already exists with a different tree: {target}")
    return {
        "repo": str(repo),
        "from_head_sha": from_head,
        "boundary_sha": boundary,
        "source_sha": source,
        "target_branch": target,
        "target_branch_generation": args.target_generation,
        "result_tree_sha": result_tree,
        "target_status": "existing-compatible" if existing is not None else "absent",
        "target_sha": existing,
    }


def create(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    source = object_id(repo, args.source)
    result_tree = object_id(repo, args.result_tree, "^{tree}")
    target = expected_target(args.branch_family, args.target_generation)
    validate_target(repo, target)
    temporary = validate_temporary_worktree(
        repo,
        args.temporary_worktree,
        args.workspace_root,
        args.slot,
        args.repository,
        target,
    )
    existing = ref_target(repo, target)
    if existing is not None:
        if not compatible_target(repo, existing, source, result_tree):
            raise TransitionError(f"target branch already exists with a different tree: {target}")
        if temporary in registered_worktrees(repo) or temporary.exists():
            raise TransitionError(
                f"compatible target exists but the journaled temporary worktree also remains: {temporary}"
            )
        return {"target_branch": target, "target_sha": existing, "created": False}

    source_tree = object_id(repo, source, "^{tree}")
    if result_tree == source_tree:
        if temporary in registered_worktrees(repo) or temporary.exists():
            raise TransitionError(
                f"empty transfer has an unexpected journaled temporary worktree: {temporary}"
            )
        commit = source
    else:
        try:
            commit = prepare_transfer_commit(
                repo,
                temporary,
                source,
                result_tree,
                args.message,
            )
        except TransitionError as exc:
            raise TransitionError(f"{exc}; journaled temporary worktree: {temporary}") from exc
    zero = "0" * len(commit)
    update = git(
        repo,
        "update-ref",
        f"refs/heads/{target}",
        commit,
        zero,
        check=False,
    )
    if update.returncode != 0:
        existing = ref_target(repo, target)
        if existing is None or not compatible_target(repo, existing, source, result_tree):
            detail = update.stderr.strip() or "target ref changed concurrently"
            raise TransitionError(f"cannot create target branch {target}: {detail}")
        commit = existing
        created = False
    else:
        created = True
    return {"target_branch": target, "target_sha": commit, "created": created}


def verify(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    source = object_id(repo, args.source)
    result_tree = object_id(repo, args.result_tree, "^{tree}")
    target = expected_target(args.branch_family, args.target_generation)
    validate_target(repo, target)
    commit = ref_target(repo, target)
    if commit is None:
        raise TransitionError(f"target branch does not exist: {target}")
    if not compatible_target(repo, commit, source, result_tree):
        raise TransitionError(f"target branch does not match the journal: {target}")
    return {"target_branch": target, "target_sha": commit, "verified": True}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Compute a 3-way result tree without refs")
    analyze_parser.add_argument("--repo", required=True, type=Path)
    analyze_parser.add_argument("--from-head", required=True)
    analyze_parser.add_argument("--boundary", required=True)
    analyze_parser.add_argument("--source", required=True)
    analyze_parser.add_argument("--branch-family", required=True)
    analyze_parser.add_argument("--target-generation", required=True, type=int)

    for name in ("create", "verify"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--repo", required=True, type=Path)
        subparser.add_argument("--source", required=True)
        subparser.add_argument("--result-tree", required=True)
        subparser.add_argument("--branch-family", required=True)
        subparser.add_argument("--target-generation", required=True, type=int)
        if name == "create":
            subparser.add_argument("--message", required=True)
            subparser.add_argument("--temporary-worktree", required=True, type=Path)
            subparser.add_argument("--workspace-root", required=True, type=Path)
            subparser.add_argument("--slot", required=True)
            subparser.add_argument("--repository", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "analyze":
            payload = analyze(args)
        elif args.command == "create":
            payload = create(args)
        else:
            payload = verify(args)
        print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False, sort_keys=True))
        return 0
    except TransitionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
