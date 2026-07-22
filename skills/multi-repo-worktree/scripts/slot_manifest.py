#!/usr/bin/env python3
"""Atomically manage Stageflow's permanent multi-repo worktree bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl

SCHEMA_VERSION = 3
LEGACY_PERMANENT_SCHEMA_VERSION = 2
MANIFEST_RELATIVE_PATH = Path(".stageflow-worktrees") / "slots.json"
LOCKS_RELATIVE_PATH = Path(".stageflow-worktrees") / "operation-locks"


class ManifestError(RuntimeError):
    pass


def manifest_path(root: Path) -> Path:
    return root.resolve() / MANIFEST_RELATIVE_PATH


def operation_lock_path(root: Path, slot: str) -> Path:
    digest = hashlib.sha256(slot.encode("utf-8")).hexdigest()
    return root.resolve() / LOCKS_RELATIVE_PATH / f"{digest}.json"


def empty_manifest() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "slots": {}}


def validate_repository(name: str, identity: Any, slot_name: str) -> None:
    if not isinstance(name, str) or not name or not isinstance(identity, dict):
        raise ManifestError(f"slot {slot_name!r} has an invalid repository identity")
    if set(identity) != {"branch", "source_branch", "remote", "generation", "pr"}:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has unexpected fields")
    if not isinstance(identity["branch"], str) or not identity["branch"]:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid branch")
    source_branch = identity["source_branch"]
    remote = identity["remote"]
    if (source_branch is None) != (remote is None):
        raise ManifestError(
            f"slot {slot_name!r} repository {name!r} must bind source branch and remote together"
        )
    if source_branch is not None and (
        not isinstance(source_branch, str)
        or not source_branch
        or not isinstance(remote, str)
        or not remote
    ):
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has invalid source context")
    if type(identity["generation"]) is not int or identity["generation"] < 0:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid generation")
    pr = identity["pr"]
    if pr is not None and (not isinstance(pr, str) or not pr):
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid PR")
    if identity["generation"] == 0 and pr is not None:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} generation 0 must not have a PR")
    if identity["generation"] > 0 and pr is None:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} generation requires a PR")


def validate_manifest_v3(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"manifest must use schema {SCHEMA_VERSION}")
    if set(data) != {"schema_version", "slots"}:
        raise ManifestError("manifest has unexpected top-level fields")
    slots = data.get("slots")
    if not isinstance(slots, dict):
        raise ManifestError("manifest slots must be a JSON object")
    for name, slot in slots.items():
        if not isinstance(name, str) or not name or not isinstance(slot, dict):
            raise ManifestError("manifest contains an invalid slot entry")
        if set(slot) != {"path", "repositories"}:
            raise ManifestError(f"slot {name!r} has unexpected fields")
        if (
            not isinstance(slot["path"], str)
            or not slot["path"]
            or not Path(slot["path"]).is_absolute()
        ):
            raise ManifestError(f"slot {name!r} has an invalid path")
        repositories = slot["repositories"]
        if not isinstance(repositories, dict) or not repositories:
            raise ManifestError(f"slot {name!r} must have repository bindings")
        for repo, identity in repositories.items():
            validate_repository(repo, identity, name)
    return data


def promote_v2_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if set(data) != {"schema_version", "slots"}:
        raise ManifestError("manifest has unexpected top-level fields")
    slots = data.get("slots")
    if not isinstance(slots, dict):
        raise ManifestError("manifest slots must be a JSON object")

    promoted: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "slots": {}}
    for name, slot in slots.items():
        if not isinstance(name, str) or not name or not isinstance(slot, dict):
            raise ManifestError("manifest contains an invalid slot entry")
        if set(slot) != {"path", "repositories"}:
            raise ManifestError(f"slot {name!r} has unexpected fields")
        if (
            not isinstance(slot["path"], str)
            or not slot["path"]
            or not Path(slot["path"]).is_absolute()
        ):
            raise ManifestError(f"slot {name!r} has an invalid path")
        repositories = slot["repositories"]
        if not isinstance(repositories, dict) or not repositories:
            raise ManifestError(f"slot {name!r} must have repository bindings")
        promoted_repositories: dict[str, Any] = {}
        for repo, identity in repositories.items():
            if not isinstance(repo, str) or not repo or not isinstance(identity, dict):
                raise ManifestError(f"slot {name!r} has an invalid repository identity")
            if set(identity) != {"branch", "generation", "pr"}:
                raise ManifestError(f"slot {name!r} repository {repo!r} has unexpected fields")
            candidate = {
                "branch": identity.get("branch"),
                "source_branch": None,
                "remote": None,
                "generation": identity.get("generation"),
                "pr": identity.get("pr"),
            }
            validate_repository(repo, candidate, name)
            promoted_repositories[repo] = candidate
        promoted["slots"][name] = {
            "path": slot["path"],
            "repositories": promoted_repositories,
        }
    return validate_manifest_v3(promoted)


def validate_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    version = data.get("schema_version")
    if type(version) is int and version == SCHEMA_VERSION:
        return validate_manifest_v3(data)
    if type(version) is int and version == LEGACY_PERMANENT_SCHEMA_VERSION:
        return promote_v2_manifest(data)
    raise ManifestError(
        f"unsupported manifest schema: {version!r}; "
        "legacy active/released manifests require manual correction"
    )


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest()
    try:
        return validate_manifest(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc


@contextmanager
def manifest_lock(path: Path, timeout_seconds: float = 3.0) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_seconds
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        if os.name == "nt" and os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise ManifestError(f"cannot initialize manifest lock {lock}: {exc}") from exc
    while not acquired:
        try:
            if os.name == "nt":
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as exc:
            if os.name != "nt" and not isinstance(exc, BlockingIOError):
                os.close(descriptor)
                raise ManifestError(f"cannot lock manifest {lock}: {exc}") from exc
            if time.monotonic() >= deadline:
                os.close(descriptor)
                raise ManifestError(f"manifest is locked: {lock}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            if os.name == "nt":
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def write_json_atomic(path: Path, data: Any, prefix: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    validate_manifest_v3(data)
    write_json_atomic(path, data, "slots.")


def require_slot(data: dict[str, Any], name: str) -> dict[str, Any]:
    slot = data["slots"].get(name)
    if slot is None:
        raise ManifestError(f"slot does not exist: {name}")
    return slot


def require_complete_context(slot: dict[str, Any], name: str) -> None:
    incomplete = sorted(
        repo
        for repo, identity in slot["repositories"].items()
        if identity["source_branch"] is None or identity["remote"] is None
    )
    if incomplete:
        raise ManifestError(
            f"slot {name!r} requires source context for: {', '.join(incomplete)}"
        )


def parse_repository_bindings(values: list[list[str]]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for repo, branch, source_branch, remote in values:
        if not repo or not branch or not source_branch or not remote:
            raise ManifestError("repository binding values must not be empty")
        if repo in bindings:
            raise ManifestError(f"duplicate repository binding: {repo}")
        bindings[repo] = {
            "branch": branch,
            "source_branch": source_branch,
            "remote": remote,
        }
    if not bindings:
        raise ManifestError("at least one repository binding is required")
    return bindings


def parse_repository_contexts(values: list[list[str]]) -> dict[str, dict[str, str]]:
    contexts: dict[str, dict[str, str]] = {}
    for repo, source_branch, remote in values:
        if not repo or not source_branch or not remote:
            raise ManifestError("repository context values must not be empty")
        if repo in contexts:
            raise ManifestError(f"duplicate repository context: {repo}")
        contexts[repo] = {"source_branch": source_branch, "remote": remote}
    if not contexts:
        raise ManifestError("at least one repository context is required")
    return contexts


def parse_repository_updates(values: list[list[str]]) -> list[tuple[str, int, str]]:
    updates: list[tuple[str, int, str]] = []
    for repo, expected_generation_text, pr in values:
        try:
            expected_generation = int(expected_generation_text)
        except ValueError as exc:
            raise ManifestError(
                f"repository {repo!r} expected generation must be an integer"
            ) from exc
        updates.append((repo, expected_generation, pr))
    return updates


def initialize(
    data: dict[str, Any],
    name: str,
    path: str,
    bindings: dict[str, dict[str, str]],
) -> dict[str, Any]:
    requested_path = str(Path(path).resolve())
    requested = {
        "path": requested_path,
        "repositories": {
            repo: {
                "branch": binding["branch"],
                "source_branch": binding["source_branch"],
                "remote": binding["remote"],
                "generation": 0,
                "pr": None,
            }
            for repo, binding in sorted(bindings.items())
        },
    }
    current = data["slots"].get(name)
    if current is not None:
        if current["path"] != requested_path or set(current["repositories"]) != set(bindings):
            raise ManifestError(f"permanent slot binding mismatch for {name}")
        for repo, binding in bindings.items():
            identity = current["repositories"][repo]
            if identity["branch"] != binding["branch"]:
                raise ManifestError(f"permanent slot binding mismatch for {name}")
            current_context = (identity["source_branch"], identity["remote"])
            requested_context = (binding["source_branch"], binding["remote"])
            if current_context == (None, None):
                identity["source_branch"], identity["remote"] = requested_context
            elif current_context != requested_context:
                raise ManifestError(f"permanent slot binding mismatch for {name}")
        return current
    data["slots"][name] = requested
    return requested


def bind_context(
    data: dict[str, Any],
    name: str,
    contexts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    slot = require_slot(data, name)
    repositories = slot["repositories"]
    if set(contexts) != set(repositories):
        missing = sorted(set(repositories) - set(contexts))
        extra = sorted(set(contexts) - set(repositories))
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unknown: {', '.join(extra)}")
        raise ManifestError(f"slot {name!r} context must cover every repository ({'; '.join(details)})")

    for repo, context in contexts.items():
        identity = repositories[repo]
        current = (identity["source_branch"], identity["remote"])
        requested = (context["source_branch"], context["remote"])
        if current != (None, None) and current != requested:
            raise ManifestError(f"repository {repo!r} source context mismatch")

    for repo, context in contexts.items():
        repositories[repo]["source_branch"] = context["source_branch"]
        repositories[repo]["remote"] = context["remote"]
    return slot


def load_operation_lock(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read operation lock {path}: {exc}") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"slot", "token", "pid", "created_at"}
        or not isinstance(data.get("slot"), str)
        or not data["slot"]
        or not isinstance(data.get("token"), str)
        or not data["token"]
        or type(data.get("pid")) is not int
        or not isinstance(data.get("created_at"), str)
        or not data["created_at"]
    ):
        raise ManifestError(f"operation lock is malformed: {path}")
    return data


def acquire_operation_lock(root: Path, slot: str, token: str) -> dict[str, Any]:
    if not token:
        raise ManifestError("operation lock token must not be empty")
    path = operation_lock_path(root, slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "slot": slot,
        "token": token,
        "pid": os.getpid(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    descriptor, candidate_name = tempfile.mkstemp(
        prefix=f"{path.stem}.",
        suffix=".tmp",
        dir=path.parent,
    )
    candidate = Path(candidate_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(candidate, path)
        except FileExistsError:
            current = load_operation_lock(path)
            if current is not None and current["slot"] == slot and current["token"] == token:
                return current
            raise ManifestError(f"slot operation is locked: {slot}") from None
        except OSError as exc:
            raise ManifestError(f"cannot publish operation lock {path}: {exc}") from exc
    finally:
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass
    return payload


def require_operation_lock(root: Path, slot: str, token: str) -> dict[str, Any]:
    current = load_operation_lock(operation_lock_path(root, slot))
    if current is None:
        raise ManifestError(f"slot operation is not locked: {slot}")
    if current["slot"] != slot or current["token"] != token:
        raise ManifestError(f"slot operation lock token mismatch: {slot}")
    return current


def release_operation_lock(root: Path, slot: str, token: str) -> dict[str, Any]:
    path = operation_lock_path(root, slot)
    current = require_operation_lock(root, slot, token)
    try:
        path.unlink()
    except FileNotFoundError as exc:
        raise ManifestError(f"slot operation is not locked: {slot}") from exc
    return current


def record_batch(
    data: dict[str, Any],
    name: str,
    repository_updates: list[tuple[str, int, str]],
) -> dict[str, Any]:
    if not repository_updates:
        raise ManifestError("at least one repository PR update is required")
    updates: dict[str, tuple[int, str]] = {}
    for repo, expected_generation, pr in repository_updates:
        if not repo or not pr:
            raise ManifestError("repository and PR must not be empty")
        if type(expected_generation) is not int or expected_generation < 0:
            raise ManifestError("expected generation must be a non-negative integer")
        if repo in updates:
            raise ManifestError(f"duplicate repository PR update: {repo}")
        updates[repo] = (expected_generation, pr)

    slot = require_slot(data, name)
    require_complete_context(slot, name)
    repositories = slot["repositories"]
    missing = sorted(set(updates) - set(repositories))
    if missing:
        raise ManifestError(f"slot {name!r} has no repository binding for: {', '.join(missing)}")

    pending: list[tuple[str, int, str]] = []
    for repo, (expected_generation, pr) in updates.items():
        identity = repositories[repo]
        if (
            identity["generation"] == expected_generation + 1
            and identity["pr"] == pr
        ):
            continue
        if identity["generation"] != expected_generation:
            raise ManifestError(
                f"repository {repo!r} generation mismatch: "
                f"expected {expected_generation}, found {identity['generation']}"
            )
        if expected_generation == 0 and identity["pr"] is not None:
            raise ManifestError(f"repository {repo!r} initial generation already has a PR")
        if expected_generation > 0 and identity["pr"] is None:
            raise ManifestError(f"repository {repo!r} generation has no current PR")
        if expected_generation > 0 and identity["pr"] == pr:
            raise ManifestError(f"repository {repo!r} new PR matches its current PR")
        pending.append((repo, expected_generation, pr))

    for repo, expected_generation, pr in pending:
        repositories[repo]["generation"] = expected_generation + 1
        repositories[repo]["pr"] = pr
    return slot


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", required=True, type=Path, help="Workspace root")
    subparsers = result.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Read permanent binding state")
    status.add_argument("--slot")

    initialize_parser = subparsers.add_parser("initialize", help="Initialize one permanent slot binding")
    initialize_parser.add_argument("--slot", required=True)
    initialize_parser.add_argument("--path", required=True)
    initialize_parser.add_argument(
        "--repository",
        action="append",
        required=True,
        nargs=4,
        metavar=("REPO", "TASK_BRANCH", "SOURCE_BRANCH", "REMOTE"),
        help="Repository and permanent Git context; repeat for every repository",
    )

    bind_context_parser = subparsers.add_parser(
        "bind-context",
        help="Atomically fill one legacy slot's permanent source context",
    )
    bind_context_parser.add_argument("--slot", required=True)
    bind_context_parser.add_argument(
        "--repository-context",
        action="append",
        required=True,
        nargs=3,
        metavar=("REPO", "SOURCE_BRANCH", "REMOTE"),
        help="Repository source branch and remote; repeat for every repository in the slot",
    )

    lock_parser = subparsers.add_parser("lock", help="Acquire a transient slot operation lock")
    lock_parser.add_argument("--slot", required=True)
    lock_parser.add_argument("--token", required=True)

    lock_status = subparsers.add_parser("lock-status", help="Read a slot operation lock")
    lock_status.add_argument("--slot", required=True)

    unlock_parser = subparsers.add_parser("unlock", help="Release an exact slot operation lock")
    unlock_parser.add_argument("--slot", required=True)
    unlock_parser.add_argument("--token", required=True)

    record = subparsers.add_parser("record-batch", help="Atomically advance repository PR generations")
    record.add_argument("--slot", required=True)
    record.add_argument("--token", required=True)
    record.add_argument(
        "--repository-update",
        action="append",
        required=True,
        nargs=3,
        metavar=("REPO", "EXPECTED_GENERATION", "PR"),
        help="Repository, current generation, and new PR; repeat for every updated repository",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    path = manifest_path(args.root)
    try:
        if args.command == "status":
            data = load_manifest(path)
            payload: Any = data if args.slot is None else require_slot(data, args.slot)
        elif args.command == "lock":
            data = load_manifest(path)
            slot = require_slot(data, args.slot)
            require_complete_context(slot, args.slot)
            payload = acquire_operation_lock(args.root, args.slot, args.token)
        elif args.command == "lock-status":
            data = load_manifest(path)
            require_slot(data, args.slot)
            payload = load_operation_lock(operation_lock_path(args.root, args.slot))
        elif args.command == "unlock":
            data = load_manifest(path)
            require_slot(data, args.slot)
            payload = release_operation_lock(args.root, args.slot, args.token)
        else:
            with manifest_lock(path):
                data = load_manifest(path)
                if args.command == "initialize":
                    bindings = parse_repository_bindings(args.repository)
                    payload = initialize(data, args.slot, args.path, bindings)
                elif args.command == "bind-context":
                    contexts = parse_repository_contexts(args.repository_context)
                    payload = bind_context(data, args.slot, contexts)
                else:
                    require_operation_lock(args.root, args.slot, args.token)
                    payload = record_batch(
                        data,
                        args.slot,
                        parse_repository_updates(args.repository_update),
                    )
                write_manifest(path, data)
        print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False, sort_keys=True))
        return 0
    except ManifestError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
