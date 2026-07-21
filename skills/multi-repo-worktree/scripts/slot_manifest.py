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

SCHEMA_VERSION = 2
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
    if set(identity) != {"branch", "generation", "pr"}:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has unexpected fields")
    if not isinstance(identity["branch"], str) or not identity["branch"]:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid branch")
    if type(identity["generation"]) is not int or identity["generation"] < 0:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid generation")
    pr = identity["pr"]
    if pr is not None and (not isinstance(pr, str) or not pr):
        raise ManifestError(f"slot {slot_name!r} repository {name!r} has an invalid PR")
    if identity["generation"] == 0 and pr is not None:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} generation 0 must not have a PR")
    if identity["generation"] > 0 and pr is None:
        raise ManifestError(f"slot {slot_name!r} repository {name!r} generation requires a PR")


def validate_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported manifest schema: {data.get('schema_version')!r}; "
            "legacy active/released manifests require manual correction"
        )
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
    validate_manifest(data)
    write_json_atomic(path, data, "slots.")


def require_slot(data: dict[str, Any], name: str) -> dict[str, Any]:
    slot = data["slots"].get(name)
    if slot is None:
        raise ManifestError(f"slot does not exist: {name}")
    return slot


def parse_repository_bindings(values: list[str]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ManifestError(f"repository binding must use <repo>=<branch>: {value!r}")
        repo, branch = value.split("=", 1)
        if not repo or not branch:
            raise ManifestError(f"repository binding must use <repo>=<branch>: {value!r}")
        if repo in bindings:
            raise ManifestError(f"duplicate repository binding: {repo}")
        bindings[repo] = branch
    if not bindings:
        raise ManifestError("at least one repository binding is required")
    return bindings


def initialize(data: dict[str, Any], name: str, path: str, bindings: dict[str, str]) -> dict[str, Any]:
    requested_path = str(Path(path).resolve())
    requested = {
        "path": requested_path,
        "repositories": {
            repo: {"branch": branch, "generation": 0, "pr": None}
            for repo, branch in sorted(bindings.items())
        },
    }
    current = data["slots"].get(name)
    if current is not None:
        current_bindings = {
            repo: identity["branch"]
            for repo, identity in current["repositories"].items()
        }
        if current["path"] != requested_path or current_bindings != bindings:
            raise ManifestError(f"permanent slot binding mismatch for {name}")
        return current
    data["slots"][name] = requested
    return requested


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
    expected_generation: int,
    repository_prs: list[tuple[str, str]],
) -> dict[str, Any]:
    if expected_generation < 0:
        raise ManifestError("expected generation must be non-negative")
    if not repository_prs:
        raise ManifestError("at least one repository PR update is required")
    updates: dict[str, str] = {}
    for repo, pr in repository_prs:
        if not repo or not pr:
            raise ManifestError("repository and PR must not be empty")
        if repo in updates:
            raise ManifestError(f"duplicate repository PR update: {repo}")
        updates[repo] = pr

    slot = require_slot(data, name)
    repositories = slot["repositories"]
    missing = sorted(set(updates) - set(repositories))
    if missing:
        raise ManifestError(f"slot {name!r} has no repository binding for: {', '.join(missing)}")

    if all(
        repositories[repo]["generation"] == expected_generation + 1
        and repositories[repo]["pr"] == pr
        for repo, pr in updates.items()
    ):
        return slot

    for repo in updates:
        identity = repositories[repo]
        if identity["generation"] != expected_generation:
            raise ManifestError(
                f"repository {repo!r} generation mismatch: "
                f"expected {expected_generation}, found {identity['generation']}"
            )
        if expected_generation == 0 and identity["pr"] is not None:
            raise ManifestError(f"repository {repo!r} initial generation already has a PR")
        if expected_generation > 0 and identity["pr"] is None:
            raise ManifestError(f"repository {repo!r} generation has no current PR")

    for repo, pr in updates.items():
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
        metavar="REPO=BRANCH",
        help="Repository and its fixed worktree branch; repeat for every repository",
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
    record.add_argument("--expected-generation", required=True, type=int)
    record.add_argument(
        "--repository-pr",
        action="append",
        required=True,
        nargs=2,
        metavar=("REPO", "PR"),
        help="Repository and its new PR identity; repeat for every updated repository",
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
            require_slot(data, args.slot)
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
                else:
                    require_operation_lock(args.root, args.slot, args.token)
                    payload = record_batch(
                        data,
                        args.slot,
                        args.expected_generation,
                        [tuple(item) for item in args.repository_pr],
                    )
                write_manifest(path, data)
        print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False, sort_keys=True))
        return 0
    except ManifestError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
