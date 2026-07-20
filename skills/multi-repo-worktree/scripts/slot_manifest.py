#!/usr/bin/env python3
"""Atomically manage Stageflow's local worktree-slot ownership manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
MANIFEST_RELATIVE_PATH = Path(".stageflow-worktrees") / "slots.json"


class ManifestError(RuntimeError):
    pass


def manifest_path(root: Path) -> Path:
    return root.resolve() / MANIFEST_RELATIVE_PATH


def empty_manifest() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "slots": {}}


def validate_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"unsupported manifest schema: {data.get('schema_version')!r}")
    slots = data.get("slots")
    if not isinstance(slots, dict):
        raise ManifestError("manifest slots must be a JSON object")
    for name, slot in slots.items():
        if not isinstance(name, str) or not name or not isinstance(slot, dict):
            raise ManifestError("manifest contains an invalid slot entry")
        if slot.get("state") not in {"active", "released"}:
            raise ManifestError(f"slot {name!r} has an invalid state")
        if not isinstance(slot.get("owner"), str) or not slot["owner"]:
            raise ManifestError(f"slot {name!r} has an invalid owner")
        if not isinstance(slot.get("path"), str) or not slot["path"]:
            raise ManifestError(f"slot {name!r} has an invalid path")
        if not isinstance(slot.get("repositories", {}), dict):
            raise ManifestError(f"slot {name!r} has invalid repository metadata")
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
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ManifestError(f"manifest is locked: {lock}")
            time.sleep(0.05)
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode())
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    validate_manifest(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="slots.", suffix=".tmp", dir=path.parent)
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


def require_slot(data: dict[str, Any], name: str) -> dict[str, Any]:
    slot = data["slots"].get(name)
    if slot is None:
        raise ManifestError(f"slot does not exist: {name}")
    return slot


def require_active_owner(slot: dict[str, Any], name: str, owner: str) -> None:
    if slot["state"] != "active":
        raise ManifestError(f"slot is not active: {name}")
    if slot["owner"] != owner:
        raise ManifestError(
            f"slot owner mismatch for {name}: expected {slot['owner']!r}, received {owner!r}"
        )


def claim(data: dict[str, Any], name: str, owner: str, path: str) -> dict[str, Any]:
    requested_path = str(Path(path).resolve())
    current = data["slots"].get(name)
    if current and current["path"] != requested_path:
        raise ManifestError(f"fixed slot path mismatch for {name}")
    if current and current["state"] == "active":
        require_active_owner(current, name, owner)
        return current
    data["slots"][name] = {
        "owner": owner,
        "path": requested_path,
        "repositories": {},
        "state": "active",
    }
    return data["slots"][name]


def record_repository(
    data: dict[str, Any],
    name: str,
    owner: str,
    repo: str,
    branch: str,
    head_sha: str,
    pushed_sha: str,
    pr: str,
) -> dict[str, Any]:
    slot = require_slot(data, name)
    require_active_owner(slot, name, owner)
    slot.setdefault("repositories", {})[repo] = {
        "branch": branch,
        "head_sha": head_sha,
        "pr": pr,
        "pushed_sha": pushed_sha,
    }
    return slot


def release(data: dict[str, Any], name: str, owner: str) -> dict[str, Any]:
    slot = require_slot(data, name)
    require_active_owner(slot, name, owner)
    slot["state"] = "released"
    return slot


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", required=True, type=Path, help="Workspace root")
    subparsers = result.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Read manifest state")
    status.add_argument("--slot")

    claim_parser = subparsers.add_parser("claim", help="Claim or re-enter a slot")
    claim_parser.add_argument("--slot", required=True)
    claim_parser.add_argument("--owner", required=True)
    claim_parser.add_argument("--path", required=True)

    record = subparsers.add_parser("record", help="Record pushed branch and PR identity")
    record.add_argument("--slot", required=True)
    record.add_argument("--owner", required=True)
    record.add_argument("--repo", required=True)
    record.add_argument("--branch", required=True)
    record.add_argument("--head-sha", required=True)
    record.add_argument("--pushed-sha", required=True)
    record.add_argument("--pr", required=True)

    release_parser = subparsers.add_parser("release", help="Release a slot as its exact owner")
    release_parser.add_argument("--slot", required=True)
    release_parser.add_argument("--owner", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    path = manifest_path(args.root)
    try:
        if args.command == "status":
            data = load_manifest(path)
            payload: Any = data if args.slot is None else require_slot(data, args.slot)
        else:
            with manifest_lock(path):
                data = load_manifest(path)
                if args.command == "claim":
                    payload = claim(data, args.slot, args.owner, args.path)
                elif args.command == "record":
                    payload = record_repository(
                        data,
                        args.slot,
                        args.owner,
                        args.repo,
                        args.branch,
                        args.head_sha,
                        args.pushed_sha,
                        args.pr,
                    )
                else:
                    payload = release(data, args.slot, args.owner)
                write_manifest(path, data)
        print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False, sort_keys=True))
        return 0
    except ManifestError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
