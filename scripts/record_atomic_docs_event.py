#!/usr/bin/env python3
"""Append and project Atomic Docs operation events.

Threat boundary: this module provides deterministic, request-local tamper evidence
for the journal bytes that remain beside ``work-state.json``.  The journal, pending
record, lock, and projection share one mutable filesystem trust domain.  A hostile
writer that can replace the whole request directory (or roll every file back to the
same earlier valid prefix) is outside the guarantee; use an external trusted anchor
when that attack must be detected.  Cooperative writers must use this helper.

The JSONL journal is authoritative.  ``operation_metrics`` is only an atomically
replaceable projection and can always be rebuilt with the ``sync`` command.
On Windows, Python exposes no portable directory ``fsync``; file contents are
flushed and replacements remain atomic, while parent-directory metadata survival
across sudden power loss is best-effort and checked through normal recovery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

_WINDOWS_LOCKING = os.name == "nt"
if _WINDOWS_LOCKING:
    import msvcrt
else:
    import fcntl

EVENT_VERSION = "1"
EVENT_HASH_DOMAIN = b"stageflow.atomic-docs.operation-event.v1\0"
ZERO_HASH = "0" * 64
JOURNAL_FILENAME = "operation-events.jsonl"
PENDING_FILENAME = "operation-events.pending"
LOCK_FILENAME = "operation-events.lock"
WORK_STATE_FILENAME = "work-state.json"
MAX_EVENT_LINE_BYTES = 64 * 1024

EVENT_TYPES = {
    "operation-started",
    "span-started",
    "span-finished",
    "operation-finished",
}
EVENT_KEYS = {
    "version",
    "sequence",
    "request_id",
    "event_type",
    "payload",
    "previous_hash",
    "event_hash",
}
PAYLOAD_KEYS = {
    "operation-started": ({"started_at"}, set()),
    "span-started": (
        {"span_id", "kind", "scope", "attempt_id", "basis_revision", "started_at"},
        {"rerun_of", "rerun_reason"},
    ),
    "span-finished": ({"span_id", "finished_at", "outcome"}, set()),
    "operation-finished": ({"finished_at"}, set()),
}
SPAN_KINDS = {
    "bundle",
    "writer",
    "development-review",
    "risk-review",
    "integration-review",
    "baseline-review",
    "validation",
}
SPAN_OUTCOMES = {"PASS", "FAIL", "completed"}
LOWER_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOWER_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)


class OperationEventError(ValueError):
    """Raised when an operation journal, event, path, or projection is unsafe."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the only accepted UTF-8 JSON representation for journal values."""
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise OperationEventError(f"value is not canonical-JSON encodable: {exc}") from exc


def canonical_event_hash(event: Mapping[str, Any]) -> str:
    """Hash an event using the v1 domain and its form without ``event_hash``."""
    if not isinstance(event, Mapping):
        raise OperationEventError("operation event must be an object")
    unsigned = dict(event)
    unsigned.pop("event_hash", None)
    return hashlib.sha256(
        EVENT_HASH_DOMAIN + canonical_json_bytes(unsigned)
    ).hexdigest()


def operation_event_journal_path(request_root: Path | str) -> Path:
    """Return the authoritative journal path below an already selected request."""
    return Path(request_root) / JOURNAL_FILENAME


def validate_operation_event_journal(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_request_id: str | None = None,
) -> None:
    """Validate the exact event schema, contiguous hash chain, and lifecycle."""
    _validate_chain(events, expected_request_id=expected_request_id, allow_empty=False)
    _reduce_validated_events(events)


def load_operation_event_journal(
    path: Path | str,
    *,
    expected_request_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load a canonical JSONL journal, rejecting alternate bytes and bad chains."""
    journal_path = Path(path)
    events = _load_journal(
        journal_path,
        expected_request_id=expected_request_id,
        allow_missing=False,
        allow_empty=False,
    )
    validate_operation_event_journal(
        events,
        expected_request_id=expected_request_id,
    )
    return events


def reduce_operation_events(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_request_id: str | None = None,
) -> dict[str, Any]:
    """Reduce validated events to the exact ``operation_metrics.version: 1`` view."""
    _validate_chain(events, expected_request_id=expected_request_id, allow_empty=False)
    return _reduce_validated_events(events)


def record_operation_event(
    request_root: Path | str,
    request_id: str,
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Flush and append one event, then atomically synchronize its state projection."""
    root = _validated_request_root(Path(request_root), request_id=request_id)
    _validate_payload(event_type, payload)
    with _request_lock(root):
        state = _load_v5_state(root, request_id)
        pending = _recover_pending(root, request_id, state)
        events = _load_journal(
            operation_event_journal_path(root),
            expected_request_id=request_id,
            allow_missing=True,
            allow_empty=True,
        )
        if events:
            validate_operation_event_journal(events, expected_request_id=request_id)
            if pending is not None:
                state = _write_projection(root, state, events, request_id)
                _clear_pending(root)
            matching = [
                event
                for event in events
                if event["event_type"] == event_type
                and event["payload"] == dict(payload)
            ]
            if matching:
                _write_projection(root, state, events, request_id)
                return dict(matching[0])
        elif pending is not None:
            raise OperationEventError("recovered pending event is absent from the journal")

        _validate_event_against_state(state, event_type, payload, events)
        event = _make_event(events, request_id, event_type, payload)
        candidate_events = [*events, event]
        validate_operation_event_journal(
            candidate_events,
            expected_request_id=request_id,
        )
        line = canonical_json_bytes(event) + b"\n"
        if len(line) > MAX_EVENT_LINE_BYTES:
            raise OperationEventError(
                f"canonical event line exceeds {MAX_EVENT_LINE_BYTES} bytes"
            )
        _atomic_write_bytes(root / PENDING_FILENAME, line)
        _append_line(operation_event_journal_path(root), line)
        committed = load_operation_event_journal(
            operation_event_journal_path(root),
            expected_request_id=request_id,
        )
        _write_projection(root, state, committed, request_id)
        _clear_pending(root)
        return event


def sync_operation_metrics_projection(
    request_root: Path | str,
    *,
    expected_request_id: str | None = None,
) -> dict[str, Any]:
    """Rebuild only the projection; no sync event is added to the journal."""
    request_path = Path(request_root)
    request_id = expected_request_id or request_path.name
    root = _validated_request_root(request_path, request_id=request_id)
    with _request_lock(root):
        state = _load_v5_state(root, request_id)
        _recover_pending(root, request_id, state)
        events = load_operation_event_journal(
            operation_event_journal_path(root),
            expected_request_id=request_id,
        )
        for index, event in enumerate(events):
            if event.get("event_type") == "operation-finished":
                _validate_event_against_state(
                    state,
                    "operation-finished",
                    event["payload"],
                    events[:index],
                )
        projection = reduce_operation_events(
            events,
            expected_request_id=request_id,
        )
        _write_projection(root, state, events, request_id)
        _clear_pending(root)
        return projection


def _validate_chain(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_request_id: str | None,
    allow_empty: bool,
) -> None:
    if isinstance(events, (str, bytes, bytearray)) or not isinstance(events, Sequence):
        raise OperationEventError("operation event journal must be a sequence")
    if not events and not allow_empty:
        raise OperationEventError("operation event journal must not be empty")
    if expected_request_id is not None:
        _validate_request_id(expected_request_id)

    chain_request_id = expected_request_id
    previous_hash = ZERO_HASH
    for expected_sequence, event in enumerate(events, start=1):
        label = f"operation event {expected_sequence}"
        if not isinstance(event, Mapping):
            raise OperationEventError(f"{label} must be an object")
        if set(event) != EVENT_KEYS:
            raise OperationEventError(
                f"{label} must contain exactly {', '.join(sorted(EVENT_KEYS))}"
            )
        if event.get("version") != EVENT_VERSION:
            raise OperationEventError(f"{label} version must be exact `1`")
        sequence = event.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            raise OperationEventError(f"{label} sequence must be a positive integer")
        if sequence != expected_sequence:
            raise OperationEventError(
                f"{label} sequence must be contiguous `{expected_sequence}`"
            )
        request_id = event.get("request_id")
        if not isinstance(request_id, str):
            raise OperationEventError(f"{label} request_id must be a string")
        _validate_request_id(request_id)
        if chain_request_id is None:
            chain_request_id = request_id
        if request_id != chain_request_id:
            raise OperationEventError(
                f"{label} request_id `{request_id}` does not match `{chain_request_id}`"
            )
        event_type = event.get("event_type")
        payload = event.get("payload")
        _validate_payload(event_type, payload, label=label)
        recorded_previous = event.get("previous_hash")
        if not isinstance(recorded_previous, str) or not LOWER_HASH_RE.fullmatch(
            recorded_previous
        ):
            raise OperationEventError(f"{label} previous_hash must be lowercase SHA-256")
        if recorded_previous != previous_hash:
            raise OperationEventError(
                f"{label} previous_hash does not match the preceding event"
            )
        recorded_hash = event.get("event_hash")
        if not isinstance(recorded_hash, str) or not LOWER_HASH_RE.fullmatch(recorded_hash):
            raise OperationEventError(f"{label} event_hash must be lowercase SHA-256")
        calculated_hash = canonical_event_hash(event)
        if recorded_hash != calculated_hash:
            raise OperationEventError(f"{label} event_hash does not match canonical bytes")
        previous_hash = recorded_hash


def _validate_payload(
    event_type: Any,
    payload: Any,
    *,
    label: str = "operation event",
) -> None:
    if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
        raise OperationEventError(f"{label} has unsupported event_type `{event_type}`")
    if not isinstance(payload, Mapping):
        raise OperationEventError(f"{label} payload must be an object")
    required, optional = PAYLOAD_KEYS[event_type]
    keys = set(payload)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise OperationEventError(
            f"{label} {event_type} payload must contain required exact fields only"
        )
    if event_type == "span-started" and (
        ("rerun_of" in payload) != ("rerun_reason" in payload)
    ):
        raise OperationEventError(
            f"{label} span-started rerun_of and rerun_reason must be paired"
        )
    timestamp_key = "finished_at" if event_type.endswith("finished") else "started_at"
    _parse_rfc3339(payload.get(timestamp_key), f"{label} {timestamp_key}")
    if event_type.startswith("span-"):
        _lower_kebab(payload.get("span_id"), f"{label} span_id")
    if event_type == "span-started":
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in SPAN_KINDS:
            raise OperationEventError(f"{label} has unsupported span kind `{kind}`")
        scope = payload.get("scope")
        _lower_kebab(scope, f"{label} scope")
        if kind == "validation" and scope in {"metrics-preterminal", "metrics-final"}:
            raise OperationEventError(
                f"{label} must not record a terminal metrics self-check span"
            )
        _lower_kebab(payload.get("attempt_id"), f"{label} attempt_id")
        basis = payload.get("basis_revision")
        if isinstance(basis, bool) or not isinstance(basis, int) or basis <= 0:
            raise OperationEventError(
                f"{label} basis_revision must be a positive integer"
            )
        if "rerun_of" in payload:
            _lower_kebab(payload.get("rerun_of"), f"{label} rerun_of")
            reason = _single_line(payload.get("rerun_reason"), f"{label} rerun_reason")
            if len(reason) > 512:
                raise OperationEventError(f"{label} rerun_reason must not exceed 512 characters")
    if event_type == "span-finished":
        outcome = payload.get("outcome")
        if not isinstance(outcome, str) or outcome not in SPAN_OUTCOMES:
            raise OperationEventError(f"{label} has unsupported span outcome")


def _validate_span_basis_against_state(
    state: Mapping[str, Any], event_type: str, payload: Mapping[str, Any]
) -> None:
    if event_type != "span-started":
        return
    kind = payload.get("kind")
    scope = payload.get("scope")
    if scope == "selection-readiness" and kind in {"bundle", "writer", "risk-review"}:
        raise OperationEventError(
            "span-started scope `selection-readiness` is reserved for the readiness review"
        )
    queue = state.get("bundle_queue")
    registry = state.get("selection_retirements")
    retired = registry.get("retired_bundles") if isinstance(registry, Mapping) else None
    bundle_records = [
        *(queue if isinstance(queue, list) else []),
        *(retired if isinstance(retired, list) else []),
    ]
    bundle_ids = {
        bundle["bundle_id"]
        for bundle in bundle_records
        if isinstance(bundle, Mapping)
        and isinstance(bundle.get("bundle_id"), str)
        and bundle["bundle_id"] != "selection-readiness"
    }
    if any(
        isinstance(bundle, Mapping)
        and bundle.get("bundle_id") == "selection-readiness"
        for bundle in bundle_records
    ):
        raise OperationEventError(
            "v5 bundle_id `selection-readiness` is reserved for the readiness review"
        )
    if kind == "development-review" and (
        scope != "selection-readiness" and scope not in bundle_ids
    ):
        raise OperationEventError(
            "development-review scope must be `selection-readiness` or an "
            "active/retired stable bundle_id"
        )
    if kind == "risk-review" and scope not in bundle_ids:
        raise OperationEventError(
            "risk-review scope must be an active/retired stable bundle_id"
        )
    if kind in {"bundle", "writer"} and scope not in bundle_ids:
        raise OperationEventError(
            f"{kind} scope must be an active/retired stable bundle_id"
        )
    if kind == "integration-review" and scope not in {
        "affected-closure",
        "project-wide",
        "terminal-current-basis",
    }:
        raise OperationEventError(
            "integration-review scope must be `affected-closure`, `project-wide`, "
            "or `terminal-current-basis`"
        )
    if kind == "baseline-review" and scope != "project-wide":
        raise OperationEventError("baseline-review scope must be `project-wide`")
    readiness_review = (
        kind == "development-review" and scope == "selection-readiness"
    )
    owner_name = "selection_readiness" if readiness_review else "semantic_review_closure"
    owner = state.get(owner_name)
    expected = owner.get("basis_revision") if isinstance(owner, Mapping) else None
    if isinstance(expected, bool) or not isinstance(expected, int) or expected <= 0:
        raise OperationEventError(
            f"v5 work-state `{owner_name}.basis_revision` must be a positive integer "
            "before span-started"
        )
    if payload.get("basis_revision") != expected:
        raise OperationEventError(
            f"span-started basis_revision must equal current `{owner_name}` basis `{expected}`"
        )


def _required_final_scope(state: Mapping[str, Any]) -> str:
    if state.get("operation_profile") in {"initial-baseline", "baseline-diff-refresh"}:
        return "baseline"
    closure = state.get("semantic_review_closure")
    gate = closure.get("final_gate") if isinstance(closure, Mapping) else None
    review_id = gate.get("review_id") if isinstance(gate, Mapping) else None
    reviews = closure.get("review_passes") if isinstance(closure, Mapping) else None
    if isinstance(reviews, list):
        for review in reviews:
            if (
                isinstance(review, Mapping)
                and review.get("review_id") == review_id
                and review.get("status") == "current"
                and review.get("reviewer_role") == "baseline"
                and review.get("scope") == "project-wide"
            ):
                return "baseline"
    return "docs"


def _validate_event_against_state(
    state: Mapping[str, Any],
    event_type: str,
    payload: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> None:
    _validate_span_basis_against_state(state, event_type, payload)
    if (
        event_type == "span-started"
        and payload.get("kind") == "validation"
        and payload.get("scope") in {"docs", "baseline"}
    ):
        projection = _reduce_validated_events(events)
        active = [
            span.get("span_id")
            for span in projection.get("spans", [])
            if isinstance(span, Mapping) and span.get("status") == "active"
        ]
        if active:
            raise OperationEventError(
                "final docs/baseline validation must start after every other span "
                "finishes; active: " + ", ".join(str(span_id) for span_id in active)
            )
    if event_type != "operation-finished":
        return
    projection = _reduce_validated_events(events)
    spans = projection.get("spans")
    latest = max(
        (
            span
            for span in spans
            if isinstance(span, Mapping)
            and type(span.get("finished_sequence")) is int
        ),
        key=lambda span: span["finished_sequence"],
        default=None,
    ) if isinstance(spans, list) else None
    closure = state.get("semantic_review_closure")
    basis = closure.get("basis_revision") if isinstance(closure, Mapping) else None
    required_scope = _required_final_scope(state)
    if (
        not isinstance(latest, Mapping)
        or latest.get("kind") != "validation"
        or latest.get("scope") != required_scope
        or latest.get("basis_revision") != basis
        or latest.get("status") != "finished"
        or latest.get("outcome") != "PASS"
        or latest.get("finished_sequence") != len(events)
    ):
        raise OperationEventError(
            "operation-finished requires the latest span to be the current-basis "
            f"successful final `{required_scope}` validation"
        )


def _reduce_validated_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    projection: dict[str, Any] | None = None
    spans_by_id: dict[str, dict[str, Any]] = {}
    span_identity: dict[str, tuple[str, str]] = {}
    latest_span_by_identity: dict[tuple[str, str], str] = {}
    operation_started: datetime | None = None
    operation_finished = False

    for event in events:
        event_type = str(event["event_type"])
        payload = event["payload"]
        sequence = event["sequence"]
        if event_type == "operation-started":
            if projection is not None or sequence != 1:
                raise OperationEventError("operation-started must be the first and only start")
            operation_started = _parse_rfc3339(
                payload["started_at"], "operation-started started_at"
            )
            projection = {
                "version": "1",
                "status": "active",
                "started_at": payload["started_at"],
                "spans": [],
            }
            continue
        if projection is None:
            raise OperationEventError("operation-started must precede every other event")
        if operation_finished:
            raise OperationEventError("operation-finished must be the final event")

        if event_type == "span-started":
            span_id = payload["span_id"]
            if span_id in spans_by_id:
                raise OperationEventError(f"span `{span_id}` starts more than once")
            started = _parse_rfc3339(payload["started_at"], f"span `{span_id}` started_at")
            if operation_started is not None and started < operation_started:
                raise OperationEventError(f"span `{span_id}` starts before the operation")
            if payload["kind"] == "validation" and payload["scope"] in {
                "docs",
                "baseline",
            }:
                active = [
                    prior_id
                    for prior_id, prior in spans_by_id.items()
                    if prior.get("status") == "active"
                ]
                if active:
                    raise OperationEventError(
                        "final docs/baseline validation must start after every other "
                        "span finishes; active: " + ", ".join(active)
                    )
            identity = (payload["kind"], payload["scope"])
            if payload["kind"] in {"bundle", "writer"}:
                counterpart_kind = "writer" if payload["kind"] == "bundle" else "bundle"
                if any(
                    prior.get("kind") == counterpart_kind
                    and prior.get("scope") == payload["scope"]
                    and prior.get("attempt_id") == payload["attempt_id"]
                    and prior.get("basis_revision") != payload["basis_revision"]
                    for prior in spans_by_id.values()
                ):
                    raise OperationEventError(
                        f"span `{span_id}` bundle/writer attempt must keep one basis_revision"
                    )
            latest_id = latest_span_by_identity.get(identity)
            latest = spans_by_id.get(latest_id) if latest_id is not None else None
            if isinstance(latest, dict):
                if latest.get("status") == "active":
                    raise OperationEventError(
                        f"span `{span_id}` cannot start while same kind/scope span "
                        f"`{latest_id}` is active"
                    )
                latest_basis = latest.get("basis_revision")
                current_basis = payload["basis_revision"]
                if type(latest_basis) is int and current_basis < latest_basis:
                    raise OperationEventError(
                        f"span `{span_id}` basis_revision must not regress below its "
                        "prior kind/scope span"
                    )
                if latest.get("outcome") == "FAIL" and current_basis == latest_basis:
                    if payload.get("rerun_of") != latest_id:
                        raise OperationEventError(
                            f"span `{span_id}` same-basis retry must declare failed "
                            f"span `{latest_id}` as rerun_of"
                        )
                elif (
                    latest.get("outcome") == "FAIL"
                    and type(latest_basis) is int
                    and current_basis > latest_basis
                    and "rerun_of" in payload
                ):
                    raise OperationEventError(
                        f"span `{span_id}` later-basis first attempt must omit rerun provenance"
                    )
            span = {
                "span_id": span_id,
                "kind": payload["kind"],
                "scope": payload["scope"],
                "attempt_id": payload["attempt_id"],
                "basis_revision": payload["basis_revision"],
                "status": "active",
                "started_at": payload["started_at"],
                "started_sequence": sequence,
            }
            if "rerun_of" in payload:
                prior_id = payload["rerun_of"]
                prior = spans_by_id.get(prior_id)
                if prior is None:
                    raise OperationEventError(
                        f"span `{span_id}` rerun_of must reference an earlier span"
                    )
                if prior["status"] != "finished":
                    raise OperationEventError(
                        f"span `{span_id}` rerun_of must reference a finished span"
                    )
                if span_identity[prior_id] != (payload["kind"], payload["scope"]):
                    raise OperationEventError(
                        f"span `{span_id}` rerun must preserve kind and scope"
                    )
                if prior.get("outcome") != "FAIL":
                    raise OperationEventError(
                        f"span `{span_id}` rerun_of must reference a failed span"
                    )
                if latest_span_by_identity.get(identity) != prior_id:
                    raise OperationEventError(
                        f"span `{span_id}` rerun_of must reference the immediately "
                        "prior span with the same kind and scope"
                    )
                span["rerun_of"] = prior_id
                span["rerun_reason"] = payload["rerun_reason"]
            projection["spans"].append(span)
            spans_by_id[span_id] = span
            identity = (payload["kind"], payload["scope"])
            span_identity[span_id] = identity
            latest_span_by_identity[identity] = span_id
            continue

        if event_type == "span-finished":
            span_id = payload["span_id"]
            span = spans_by_id.get(span_id)
            if span is None:
                raise OperationEventError(
                    f"span-finished `{span_id}` has no preceding span-started"
                )
            if span["status"] != "active":
                raise OperationEventError(f"span `{span_id}` finishes more than once")
            span_kind = span.get("kind")
            outcome = payload.get("outcome")
            if span_kind in {"bundle", "writer"} and outcome == "PASS":
                raise OperationEventError(
                    f"{span_kind} span `{span_id}` outcome must be `completed` or `FAIL`"
                )
            if span_kind in {
                "development-review",
                "risk-review",
                "integration-review",
                "baseline-review",
                "validation",
            } and outcome == "completed":
                raise OperationEventError(
                    f"{span_kind} span `{span_id}` outcome must be `PASS` or `FAIL`"
                )
            finished = _parse_rfc3339(
                payload["finished_at"], f"span `{span_id}` finished_at"
            )
            started = _parse_rfc3339(span["started_at"], f"span `{span_id}` started_at")
            if finished < started:
                raise OperationEventError(f"span `{span_id}` finishes before it starts")
            span["status"] = "finished"
            span["finished_at"] = payload["finished_at"]
            span["finished_sequence"] = sequence
            span["outcome"] = payload["outcome"]
            continue

        if event_type == "operation-finished":
            active = [
                span_id
                for span_id, span in spans_by_id.items()
                if span["status"] == "active"
            ]
            if active:
                raise OperationEventError(
                    "operation-finished requires every span to be finished: "
                    + ", ".join(active)
                )
            finished = _parse_rfc3339(
                payload["finished_at"], "operation-finished finished_at"
            )
            if operation_started is not None and finished < operation_started:
                raise OperationEventError("operation finishes before it starts")
            for span in spans_by_id.values():
                span_finished = _parse_rfc3339(
                    span["finished_at"], f"span `{span['span_id']}` finished_at"
                )
                if span_finished > finished:
                    raise OperationEventError(
                        f"span `{span['span_id']}` finishes after the operation"
                    )
            projection["status"] = "finished"
            projection["finished_at"] = payload["finished_at"]
            operation_finished = True
            continue

        raise OperationEventError(f"unsupported operation event `{event_type}`")

    if projection is None:
        raise OperationEventError("operation event journal has no operation-started event")
    return projection


def _load_journal(
    path: Path,
    *,
    expected_request_id: str | None,
    allow_missing: bool,
    allow_empty: bool,
) -> list[dict[str, Any]]:
    _reject_symlink(path, "operation event journal")
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        if allow_missing:
            return []
        raise OperationEventError(f"missing operation event journal `{path}`") from None
    except OSError as exc:
        raise OperationEventError(f"cannot read operation event journal `{path}`: {exc}") from exc
    if not raw:
        if allow_empty:
            return []
        raise OperationEventError("operation event journal must not be empty")
    if b"\r" in raw:
        raise OperationEventError("operation event journal must not contain CR or CRLF bytes")
    if not raw.endswith(b"\n"):
        raise OperationEventError("operation event journal has a partial final line")

    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(keepends=True), start=1):
        if raw_line == b"\n":
            raise OperationEventError(f"operation event line {line_number} must not be blank")
        content = raw_line[:-1]
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OperationEventError(
                f"operation event line {line_number} is not valid UTF-8: {exc}"
            ) from exc
        try:
            value = json.loads(
                text,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, OperationEventError) as exc:
            raise OperationEventError(
                f"invalid JSON on operation event line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise OperationEventError(f"operation event line {line_number} must be an object")
        if canonical_json_bytes(value) != content:
            raise OperationEventError(
                f"operation event line {line_number} is not canonical JSON bytes"
            )
        events.append(value)

    _validate_chain(
        events,
        expected_request_id=expected_request_id,
        allow_empty=allow_empty,
    )
    return events


def _make_event(
    events: Sequence[Mapping[str, Any]],
    request_id: str,
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "version": EVENT_VERSION,
        "sequence": len(events) + 1,
        "request_id": request_id,
        "event_type": event_type,
        "payload": dict(payload),
        "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
    }
    event["event_hash"] = canonical_event_hash(event)
    return event


def _recover_pending(
    root: Path, request_id: str, state: Mapping[str, Any]
) -> dict[str, Any] | None:
    pending_path = root / PENDING_FILENAME
    _reject_symlink(pending_path, "operation event pending record")
    try:
        pending_bytes = pending_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OperationEventError(f"cannot read pending operation event: {exc}") from exc
    if not pending_bytes or not pending_bytes.endswith(b"\n") or pending_bytes.count(b"\n") != 1:
        raise OperationEventError("pending operation event must contain one complete line")
    if len(pending_bytes) > MAX_EVENT_LINE_BYTES:
        raise OperationEventError("pending operation event exceeds the line size limit")
    pending_event = _parse_single_canonical_line(pending_bytes, request_id)

    journal_path = operation_event_journal_path(root)
    _reject_symlink(journal_path, "operation event journal")
    try:
        journal_bytes = journal_path.read_bytes()
    except FileNotFoundError:
        journal_bytes = b""
    except OSError as exc:
        raise OperationEventError(f"cannot read operation event journal: {exc}") from exc

    complete_end = journal_bytes.rfind(b"\n") + 1
    complete_bytes = journal_bytes[:complete_end]
    partial_bytes = journal_bytes[complete_end:]
    prefix_events = _load_canonical_bytes_prefix(complete_bytes, request_id)

    if prefix_events and prefix_events[-1] == pending_event and not partial_bytes:
        validate_operation_event_journal(
            prefix_events,
            expected_request_id=request_id,
        )
        return pending_event
    _validate_event_against_state(
        state,
        pending_event["event_type"],
        pending_event["payload"],
        prefix_events,
    )
    expected = _make_event(
        prefix_events,
        request_id,
        pending_event["event_type"],
        pending_event["payload"],
    )
    if expected != pending_event:
        raise OperationEventError(
            "pending operation event does not extend the current canonical journal"
        )
    if partial_bytes and not pending_bytes.startswith(partial_bytes):
        raise OperationEventError(
            "partial journal bytes do not match the pending operation event"
        )
    validate_operation_event_journal(
        [*prefix_events, pending_event],
        expected_request_id=request_id,
    )
    _append_line(journal_path, pending_bytes[len(partial_bytes):])
    load_operation_event_journal(journal_path, expected_request_id=request_id)
    return pending_event


def _load_canonical_bytes_prefix(raw: bytes, request_id: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    temp_fd, temp_name = tempfile.mkstemp(prefix="atomic-docs-event-prefix-", suffix=".jsonl")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "wb") as stream:
            stream.write(raw)
        return _load_journal(
            temp_path,
            expected_request_id=request_id,
            allow_missing=False,
            allow_empty=True,
        )
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _parse_single_canonical_line(raw: bytes, request_id: str) -> dict[str, Any]:
    if b"\r" in raw:
        raise OperationEventError("pending operation event must use LF canonical bytes")
    content = raw[:-1]
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OperationEventError) as exc:
        raise OperationEventError(f"invalid pending operation event: {exc}") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != content:
        raise OperationEventError("pending operation event is not canonical JSON bytes")
    if set(value) != EVENT_KEYS:
        raise OperationEventError("pending operation event has invalid outer keys")
    if value.get("version") != EVENT_VERSION or value.get("request_id") != request_id:
        raise OperationEventError("pending operation event has invalid version or request_id")
    _validate_payload(value.get("event_type"), value.get("payload"), label="pending event")
    if (
        isinstance(value.get("sequence"), bool)
        or not isinstance(value.get("sequence"), int)
        or value["sequence"] <= 0
    ):
        raise OperationEventError("pending operation event has invalid sequence")
    for key in ("previous_hash", "event_hash"):
        field = value.get(key)
        if not isinstance(field, str) or not LOWER_HASH_RE.fullmatch(field):
            raise OperationEventError(f"pending operation event has invalid {key}")
    if value["event_hash"] != canonical_event_hash(value):
        raise OperationEventError("pending operation event has invalid event_hash")
    return value


def _load_v5_state(root: Path, request_id: str) -> dict[str, Any]:
    state_path = root / WORK_STATE_FILENAME
    _reject_symlink(state_path, "Atomic Docs work-state")
    try:
        raw = state_path.read_text(encoding="utf-8")
        state = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except FileNotFoundError:
        raise OperationEventError(f"missing v5 work-state for request `{request_id}`") from None
    except (OSError, UnicodeError, json.JSONDecodeError, OperationEventError) as exc:
        raise OperationEventError(
            f"invalid v5 work-state for request `{request_id}`: {exc}"
        ) from exc
    if not isinstance(state, dict):
        raise OperationEventError("Atomic Docs work-state must be a JSON object")
    selection = state.get("context_selection")
    if not isinstance(selection, dict) or selection.get("version") != "5":
        raise OperationEventError(
            "event recording requires exact context_selection.version `5`; "
            "create a new v5 request instead of migrating older state"
        )
    state_request_id = state.get("request_id")
    if state_request_id is not None and state_request_id != request_id:
        raise OperationEventError(
            f"work-state request_id `{state_request_id}` does not match `{request_id}`"
        )
    return state


def _write_projection(
    root: Path,
    state: dict[str, Any],
    events: Sequence[Mapping[str, Any]],
    request_id: str,
) -> dict[str, Any]:
    projection = reduce_operation_events(events, expected_request_id=request_id)
    updated = dict(state)
    updated["operation_metrics"] = projection
    state_path = root / WORK_STATE_FILENAME
    state_bytes = (
        json.dumps(updated, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    _atomic_write_bytes(state_path, state_bytes)
    return updated


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    _reject_symlink(path, path.name)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _append_line(path: Path, content: bytes) -> None:
    if not content:
        return
    _reject_symlink(path, "operation event journal")
    flags = _binary_open_flags(os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
        try:
            view = memoryview(content)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OperationEventError("short write while appending operation event")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_directory(path.parent)
    except OSError as exc:
        raise OperationEventError(f"cannot append operation event journal: {exc}") from exc


def _clear_pending(root: Path) -> None:
    pending_path = root / PENDING_FILENAME
    _reject_symlink(pending_path, "operation event pending record")
    try:
        pending_path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise OperationEventError(f"cannot remove committed pending event: {exc}") from exc
    _fsync_directory(root)


@contextmanager
def _request_lock(root: Path) -> Iterator[None]:
    lock_path = root / LOCK_FILENAME
    _reject_symlink(lock_path, "operation event lock")
    flags = _binary_open_flags(os.O_RDWR | os.O_CREAT)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise OperationEventError(f"cannot open operation event lock: {exc}") from exc
    locked = False
    try:
        try:
            if _WINDOWS_LOCKING:
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b"\0")
                    os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX)
            locked = True
        except OSError as exc:
            raise OperationEventError(f"operation event lock failed: {exc}") from exc
        yield
    finally:
        try:
            if locked:
                if _WINDOWS_LOCKING:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _validated_request_root(request_root: Path, *, request_id: str) -> Path:
    _validate_request_id(request_id)
    if request_root.name != request_id:
        raise OperationEventError(
            f"request root name `{request_root.name}` does not match request_id `{request_id}`"
        )
    if request_root.is_symlink():
        raise OperationEventError("Atomic Docs request root must not be a symlink")
    try:
        resolved = request_root.resolve(strict=True)
    except OSError as exc:
        raise OperationEventError(f"Atomic Docs request root does not exist: {exc}") from exc
    if not resolved.is_dir():
        raise OperationEventError("Atomic Docs request root must be a directory")
    expected_parts = (".stageflow", "atomic-docs", "requests", request_id)
    if len(resolved.parts) < len(expected_parts) or resolved.parts[-4:] != expected_parts:
        raise OperationEventError(
            "request root must be `.stageflow/atomic-docs/requests/<request-id>`"
        )
    requests_root = resolved.parent
    try:
        resolved.relative_to(requests_root)
    except ValueError:
        raise OperationEventError(
            "request root escapes the Atomic Docs requests directory"
        ) from None
    return resolved


def _validate_request_id(request_id: str) -> None:
    if (
        not isinstance(request_id, str)
        or not request_id
        or request_id in {".", ".."}
        or "/" in request_id
        or "\\" in request_id
        or "\x00" in request_id
        or Path(request_id).name != request_id
    ):
        raise OperationEventError("request_id must be one safe path segment")
    if not LOWER_KEBAB_RE.fullmatch(request_id):
        raise OperationEventError(
            "request_id must be a safe lower-kebab-case path segment"
        )


def _reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise OperationEventError(f"{label} must not be a symlink")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OperationEventError(f"duplicate JSON key `{key}`")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise OperationEventError(f"non-finite JSON number `{value}` is forbidden")


def _lower_kebab(value: Any, label: str) -> str:
    if not isinstance(value, str) or not LOWER_KEBAB_RE.fullmatch(value):
        raise OperationEventError(f"{label} must be lower-kebab-case")
    return value


def _single_line(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
        raise OperationEventError(f"{label} must be a non-empty single-line string")
    return value


def _parse_rfc3339(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        raise OperationEventError(f"{label} must be an RFC3339 timestamp with timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationEventError(f"{label} is not a valid RFC3339 timestamp") from exc


def _fsync_directory(path: Path) -> None:
    """Flush directory metadata where Python exposes a supported descriptor."""
    if _WINDOWS_LOCKING:
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise OperationEventError(f"cannot synchronize directory `{path}`: {exc}") from exc


def _binary_open_flags(flags: int) -> int:
    """Keep low-level Windows journal and lock writes out of text translation mode."""
    return flags | getattr(os, "O_BINARY", 0)


def _payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "operation-started":
        return {"started_at": args.started_at}
    if args.command == "span-started":
        payload = {
            "span_id": args.span_id,
            "kind": args.kind,
            "scope": args.scope,
            "attempt_id": args.attempt_id,
            "basis_revision": args.basis_revision,
            "started_at": args.started_at,
        }
        if args.rerun_of is not None:
            payload["rerun_of"] = args.rerun_of
        if args.rerun_reason is not None:
            payload["rerun_reason"] = args.rerun_reason
        return payload
    if args.command == "span-finished":
        return {
            "span_id": args.span_id,
            "finished_at": args.finished_at,
            "outcome": args.outcome,
        }
    if args.command == "operation-finished":
        return {"finished_at": args.finished_at}
    raise OperationEventError(f"unsupported command `{args.command}`")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append canonical Atomic Docs v5 operation events and sync work-state"
    )
    parser.add_argument("--root", default=".", help="Target project root")
    parser.add_argument("--request-id", required=True, help="Safe Atomic Docs request id")
    commands = parser.add_subparsers(dest="command", required=True)

    operation_started = commands.add_parser("operation-started")
    operation_started.add_argument("--started-at", required=True)

    span_started = commands.add_parser("span-started")
    span_started.add_argument("--span-id", required=True)
    span_started.add_argument("--kind", required=True, choices=sorted(SPAN_KINDS))
    span_started.add_argument("--scope", required=True)
    span_started.add_argument("--attempt-id", required=True)
    span_started.add_argument("--basis-revision", required=True, type=int)
    span_started.add_argument("--started-at", required=True)
    span_started.add_argument("--rerun-of")
    span_started.add_argument("--rerun-reason")

    span_finished = commands.add_parser("span-finished")
    span_finished.add_argument("--span-id", required=True)
    span_finished.add_argument("--finished-at", required=True)
    span_finished.add_argument("--outcome", required=True, choices=sorted(SPAN_OUTCOMES))

    operation_finished = commands.add_parser("operation-finished")
    operation_finished.add_argument("--finished-at", required=True)

    commands.add_parser("sync")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.root).resolve()
    request_root = (
        project_root / ".stageflow" / "atomic-docs" / "requests" / args.request_id
    )
    try:
        if args.command == "sync":
            projection = sync_operation_metrics_projection(
                request_root,
                expected_request_id=args.request_id,
            )
            events = load_operation_event_journal(
                operation_event_journal_path(request_root),
                expected_request_id=args.request_id,
            )
            print(
                f"SYNCED atomic-docs operation events: request={args.request_id} "
                f"events={len(events)} status={projection['status']}"
            )
            return 0
        event = record_operation_event(
            request_root,
            args.request_id,
            args.command,
            _payload_from_args(args),
        )
        print(
            f"RECORDED atomic-docs operation event: request={args.request_id} "
            f"sequence={event['sequence']} type={event['event_type']} "
            f"hash={event['event_hash']}"
        )
        return 0
    except OperationEventError as exc:
        print(f"FAIL operation-event: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
