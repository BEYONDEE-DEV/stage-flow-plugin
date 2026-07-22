from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.record_atomic_docs_event import (
    EVENT_HASH_DOMAIN,
    ZERO_HASH,
    OperationEventError,
    canonical_event_hash,
    canonical_json_bytes,
    load_operation_event_journal,
    operation_event_journal_path,
    record_operation_event,
    reduce_operation_events,
    sync_operation_metrics_projection,
    validate_operation_event_journal,
)

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "scripts" / "record_atomic_docs_event.py"
REQUEST_ID = "20260721-210000-semantic-integrity-v5"


class AtomicDocsEventRecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.request_root = (
            self.root
            / ".stageflow"
            / "atomic-docs"
            / "requests"
            / REQUEST_ID
        )
        self.request_root.mkdir(parents=True)
        self.state_path = self.request_root / "work-state.json"
        self.write_state(
            {
                "request_id": REQUEST_ID,
                "context_selection": {"version": "5", "candidates": []},
                "selection_readiness": {"basis_revision": 1},
                "semantic_review_closure": {"basis_revision": 1},
                "bundle_queue": [
                    {"bundle_id": "accounts-bundle"},
                    *(
                        {"bundle_id": f"bundle-{index}"}
                        for index in range(1, 5)
                    ),
                ],
                "unrelated_owner": {"preserved": True},
            }
        )
        self.journal_path = operation_event_journal_path(self.request_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_state(self, state: dict[str, object]) -> None:
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self) -> dict[str, object]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def make_event(
        self,
        events: list[dict[str, object]],
        event_type: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        if event_type == "span-started" and "basis_revision" not in payload:
            payload = {**payload, "basis_revision": 1}
        event: dict[str, object] = {
            "version": "1",
            "sequence": len(events) + 1,
            "request_id": REQUEST_ID,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
        }
        event["event_hash"] = canonical_event_hash(event)
        return event

    def write_events(self, events: list[dict[str, object]]) -> None:
        self.journal_path.write_bytes(
            b"".join(canonical_json_bytes(event) + b"\n" for event in events)
        )

    def started_event(self) -> dict[str, object]:
        return self.make_event(
            [],
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )

    def test_records_exact_canonical_chain_and_projection(self) -> None:
        first = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        second = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "accounts-writer-1",
                "kind": "writer",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        third = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "accounts-writer-1",
                "finished_at": "2026-07-21T21:02:00+09:00",
                "outcome": "completed",
            },
        )
        fourth = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "docs-validation-1",
                "kind": "validation",
                "scope": "docs",
                "attempt_id": "docs-validation-attempt-1",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:03:00+09:00",
            },
        )
        fifth = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "docs-validation-1",
                "finished_at": "2026-07-21T21:04:00+09:00",
                "outcome": "PASS",
            },
        )
        sixth = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-finished",
            {"finished_at": "2026-07-21T21:05:00+09:00"},
        )

        events = load_operation_event_journal(
            self.journal_path,
            expected_request_id=REQUEST_ID,
        )
        self.assertEqual([1, 2, 3, 4, 5, 6], [event["sequence"] for event in events])
        self.assertEqual(ZERO_HASH, first["previous_hash"])
        self.assertEqual(
            "08c385e88dfd3ce7b42a2d27084032f968e5d3dcbff08741a1f172f49aa9aa52",
            first["event_hash"],
        )
        self.assertEqual(first["event_hash"], second["previous_hash"])
        self.assertEqual(second["event_hash"], third["previous_hash"])
        self.assertEqual(third["event_hash"], fourth["previous_hash"])
        self.assertEqual(fourth["event_hash"], fifth["previous_hash"])
        self.assertEqual(fifth["event_hash"], sixth["previous_hash"])
        for event in events:
            self.assertEqual(
                {
                    "version",
                    "sequence",
                    "request_id",
                    "event_type",
                    "payload",
                    "previous_hash",
                    "event_hash",
                },
                set(event),
            )
            self.assertEqual(canonical_event_hash(event), event["event_hash"])
        self.assertEqual(
            b"".join(canonical_json_bytes(event) + b"\n" for event in events),
            self.journal_path.read_bytes(),
        )
        self.assertEqual(
            {
                "version": "1",
                "status": "finished",
                "started_at": "2026-07-21T21:00:00+09:00",
                "spans": [
                    {
                        "span_id": "accounts-writer-1",
                        "kind": "writer",
                        "scope": "accounts-bundle",
                        "attempt_id": "accounts-attempt-1",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": "2026-07-21T21:01:00+09:00",
                        "started_sequence": 2,
                        "finished_at": "2026-07-21T21:02:00+09:00",
                        "finished_sequence": 3,
                        "outcome": "completed",
                    },
                    {
                        "span_id": "docs-validation-1",
                        "kind": "validation",
                        "scope": "docs",
                        "attempt_id": "docs-validation-attempt-1",
                        "basis_revision": 1,
                        "status": "finished",
                        "started_at": "2026-07-21T21:03:00+09:00",
                        "started_sequence": 4,
                        "finished_at": "2026-07-21T21:04:00+09:00",
                        "finished_sequence": 5,
                        "outcome": "PASS",
                    },
                ],
                "finished_at": "2026-07-21T21:05:00+09:00",
            },
            self.read_state()["operation_metrics"],
        )
        self.assertEqual({"preserved": True}, self.read_state()["unrelated_owner"])
        self.assertEqual(
            b"stageflow.atomic-docs.operation-event.v1\0",
            EVENT_HASH_DOMAIN,
        )

    def test_rerun_is_a_paired_fixed_payload_and_projects_without_free_form_state(self) -> None:
        events = [self.started_event()]
        events.append(
            self.make_event(
                events,
                "span-started",
                {
                    "span_id": "docs-validation-1",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-attempt-1",
                    "started_at": "2026-07-21T21:01:00+09:00",
                },
            )
        )
        events.append(
            self.make_event(
                events,
                "span-finished",
                {
                    "span_id": "docs-validation-1",
                    "finished_at": "2026-07-21T21:02:00+09:00",
                    "outcome": "FAIL",
                },
            )
        )
        events.append(
            self.make_event(
                events,
                "span-started",
                {
                    "span_id": "docs-validation-2",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-attempt-2",
                    "started_at": "2026-07-21T21:03:00+09:00",
                    "rerun_of": "docs-validation-1",
                    "rerun_reason": "corrected validation finding",
                },
            )
        )
        projection = reduce_operation_events(events, expected_request_id=REQUEST_ID)
        self.assertEqual("docs-validation-1", projection["spans"][1]["rerun_of"])
        self.assertEqual("active", projection["spans"][1]["status"])

        unpaired = copy.deepcopy(events[-1])
        del unpaired["payload"]["rerun_reason"]
        unpaired["event_hash"] = canonical_event_hash(unpaired)
        with self.assertRaisesRegex(OperationEventError, "must be paired"):
            validate_operation_event_journal([*events[:-1], unpaired])

        state_patch = copy.deepcopy(events[-1])
        state_patch["payload"]["state_patch"] = {"status": "finished"}
        state_patch["event_hash"] = canonical_event_hash(state_patch)
        with self.assertRaisesRegex(OperationEventError, "required exact fields only"):
            validate_operation_event_journal([*events[:-1], state_patch])

        missing_basis = copy.deepcopy(events[1])
        del missing_basis["payload"]["basis_revision"]
        missing_basis["event_hash"] = canonical_event_hash(missing_basis)
        with self.assertRaisesRegex(OperationEventError, "required exact fields only"):
            validate_operation_event_journal([events[0], missing_basis])

        passing_events = [self.started_event()]
        passing_events.append(
            self.make_event(
                passing_events,
                "span-started",
                {
                    "span_id": "docs-pass-1",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-pass-attempt-1",
                    "started_at": "2026-07-21T21:01:00+09:00",
                },
            )
        )
        passing_events.append(
            self.make_event(
                passing_events,
                "span-finished",
                {
                    "span_id": "docs-pass-1",
                    "finished_at": "2026-07-21T21:02:00+09:00",
                    "outcome": "PASS",
                },
            )
        )
        passing_events.append(
            self.make_event(
                passing_events,
                "span-started",
                {
                    "span_id": "docs-pass-2",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-pass-attempt-2",
                    "started_at": "2026-07-21T21:03:00+09:00",
                    "rerun_of": "docs-pass-1",
                    "rerun_reason": "not actually a failed validation",
                },
            )
        )
        with self.assertRaisesRegex(OperationEventError, "reference a failed span"):
            reduce_operation_events(passing_events)

        skipped_events = [self.started_event()]
        for suffix, started_at, finished_at in (
            ("1", "2026-07-21T21:01:00+09:00", "2026-07-21T21:02:00+09:00"),
            ("2", "2026-07-21T21:03:00+09:00", "2026-07-21T21:04:00+09:00"),
        ):
            skipped_events.append(
                self.make_event(
                    skipped_events,
                    "span-started",
                    {
                        "span_id": f"docs-fail-{suffix}",
                        "kind": "validation",
                        "scope": "docs",
                        "attempt_id": f"docs-fail-attempt-{suffix}",
                        "started_at": started_at,
                        **(
                            {
                                "rerun_of": "docs-fail-1",
                                "rerun_reason": "retry the immediately prior failure",
                            }
                            if suffix == "2"
                            else {}
                        ),
                    },
                )
            )
            skipped_events.append(
                self.make_event(
                    skipped_events,
                    "span-finished",
                    {
                        "span_id": f"docs-fail-{suffix}",
                        "finished_at": finished_at,
                        "outcome": "FAIL",
                    },
                )
            )
        skipped_events.append(
            self.make_event(
                skipped_events,
                "span-started",
                {
                    "span_id": "docs-fail-3",
                    "kind": "validation",
                    "scope": "docs",
                    "attempt_id": "docs-fail-attempt-3",
                    "started_at": "2026-07-21T21:05:00+09:00",
                    "rerun_of": "docs-fail-1",
                    "rerun_reason": "skips the immediately prior failure",
                },
            )
        )
        with self.assertRaisesRegex(OperationEventError, "same-basis retry"):
            reduce_operation_events(skipped_events)

    def test_retry_of_committed_event_is_idempotent(self) -> None:
        payload = {"started_at": "2026-07-21T21:00:00+09:00"}
        first = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            payload,
        )
        retried = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            payload,
        )
        self.assertEqual(first, retried)
        self.assertEqual(1, len(load_operation_event_journal(self.journal_path)))

    def test_span_start_basis_must_match_its_current_state_owner(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        for kind, scope, owner in (
            ("writer", "accounts-bundle", "semantic_review_closure"),
            ("development-review", "selection-readiness", "selection_readiness"),
        ):
            with self.subTest(owner=owner), self.assertRaisesRegex(
                OperationEventError, owner
            ):
                record_operation_event(
                    self.request_root,
                    REQUEST_ID,
                    "span-started",
                    {
                        "span_id": f"wrong-{kind}",
                        "kind": kind,
                        "scope": scope,
                        "attempt_id": f"wrong-{kind}-attempt",
                        "basis_revision": 2,
                        "started_at": "2026-07-21T21:01:00+09:00",
                    },
                )
        self.assertEqual(1, len(load_operation_event_journal(self.journal_path)))

    def test_recorder_rejects_doomed_retry_basis_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        first_payload = {
            "span_id": "docs-fail-1",
            "kind": "validation",
            "scope": "docs",
            "attempt_id": "docs-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:01:00+09:00",
        }
        record_operation_event(
            self.request_root, REQUEST_ID, "span-started", first_payload
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "docs-fail-1",
                "finished_at": "2026-07-21T21:02:00+09:00",
                "outcome": "FAIL",
            },
        )
        before = self.journal_path.read_bytes()
        missing_rerun = {
            **first_payload,
            "span_id": "docs-fail-2",
            "attempt_id": "docs-attempt-2",
            "started_at": "2026-07-21T21:03:00+09:00",
        }
        with self.assertRaisesRegex(OperationEventError, "same-basis retry"):
            record_operation_event(
                self.request_root, REQUEST_ID, "span-started", missing_rerun
            )
        self.assertEqual(before, self.journal_path.read_bytes())

        state = self.read_state()
        state["semantic_review_closure"]["basis_revision"] = 2
        self.write_state(state)
        cross_basis_rerun = {
            **missing_rerun,
            "basis_revision": 2,
            "rerun_of": "docs-fail-1",
            "rerun_reason": "a new basis is not a retry",
        }
        with self.assertRaisesRegex(OperationEventError, "later-basis first attempt"):
            record_operation_event(
                self.request_root, REQUEST_ID, "span-started", cross_basis_rerun
            )
        self.assertEqual(before, self.journal_path.read_bytes())

        valid_later = dict(cross_basis_rerun)
        valid_later.pop("rerun_of")
        valid_later.pop("rerun_reason")
        record_operation_event(
            self.request_root, REQUEST_ID, "span-started", valid_later
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "docs-fail-2",
                "finished_at": "2026-07-21T21:04:00+09:00",
                "outcome": "PASS",
            },
        )
        after_later = self.journal_path.read_bytes()
        state = self.read_state()
        state["semantic_review_closure"]["basis_revision"] = 1
        self.write_state(state)
        regression = {
            **missing_rerun,
            "span_id": "docs-regression-1",
            "attempt_id": "docs-regression-attempt-1",
            "started_at": "2026-07-21T21:05:00+09:00",
        }
        with self.assertRaisesRegex(OperationEventError, "must not regress"):
            record_operation_event(
                self.request_root, REQUEST_ID, "span-started", regression
            )
        self.assertEqual(after_later, self.journal_path.read_bytes())
        self.assertEqual(5, len(load_operation_event_journal(self.journal_path)))

    def test_recorder_rejects_overlapping_same_identity_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        first = {
            "span_id": "docs-active-1",
            "kind": "validation",
            "scope": "bundle-check",
            "attempt_id": "docs-active-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:01:00+09:00",
        }
        record_operation_event(
            self.request_root, REQUEST_ID, "span-started", first
        )
        before = self.journal_path.read_bytes()
        for basis in (1, 2):
            state = self.read_state()
            state["semantic_review_closure"]["basis_revision"] = basis
            self.write_state(state)
            overlapping = {
                **first,
                "span_id": f"docs-active-{basis + 1}",
                "attempt_id": f"docs-active-attempt-{basis + 1}",
                "basis_revision": basis,
                "started_at": f"2026-07-21T21:0{basis + 1}:00+09:00",
            }
            with self.assertRaisesRegex(OperationEventError, "same kind/scope span"):
                record_operation_event(
                    self.request_root, REQUEST_ID, "span-started", overlapping
                )
        self.assertEqual(before, self.journal_path.read_bytes())
        self.assertEqual(2, len(load_operation_event_journal(self.journal_path)))

    def test_recorder_rejects_doomed_terminal_events_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        before = self.journal_path.read_bytes()

        with self.assertRaisesRegex(
            OperationEventError,
            "requires the latest span to be the current-basis successful final `docs`",
        ):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "operation-finished",
                {"finished_at": "2026-07-21T21:01:00+09:00"},
            )
        self.assertEqual(before, self.journal_path.read_bytes())
        self.assertEqual("active", self.read_state()["operation_metrics"]["status"])

        events = load_operation_event_journal(self.journal_path)
        pending = self.make_event(
            events,
            "operation-finished",
            {"finished_at": "2026-07-21T21:01:00+09:00"},
        )
        (self.request_root / "operation-events.pending").write_bytes(
            canonical_json_bytes(pending) + b"\n"
        )
        with self.assertRaisesRegex(OperationEventError, "current-basis successful"):
            sync_operation_metrics_projection(
                self.request_root,
                expected_request_id=REQUEST_ID,
            )
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_operation_finish_requires_final_pass_to_be_immediately_previous(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "accounts-writer-1",
                "kind": "writer",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        validation_start = {
            "span_id": "docs-validation-1",
            "kind": "validation",
            "scope": "docs",
            "attempt_id": "docs-validation-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:02:00+09:00",
        }
        before_overlap = self.journal_path.read_bytes()
        with self.assertRaisesRegex(OperationEventError, "after every other span finishes"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                validation_start,
            )
        self.assertEqual(before_overlap, self.journal_path.read_bytes())
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "accounts-writer-1",
                "finished_at": "2026-07-21T21:02:00+09:00",
                "outcome": "completed",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                **validation_start,
                "started_at": "2026-07-21T21:03:00+09:00",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "docs-validation-1",
                "finished_at": "2026-07-21T21:04:00+09:00",
                "outcome": "PASS",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "accounts-writer-2",
                "kind": "writer",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-2",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:05:00+09:00",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "accounts-writer-2",
                "finished_at": "2026-07-21T21:06:00+09:00",
                "outcome": "completed",
            },
        )
        before = self.journal_path.read_bytes()
        with self.assertRaisesRegex(OperationEventError, "current-basis successful"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "operation-finished",
                {"finished_at": "2026-07-21T21:07:00+09:00"},
            )
        self.assertEqual(before, self.journal_path.read_bytes())

        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "docs-validation-2",
                "kind": "validation",
                "scope": "docs",
                "attempt_id": "docs-validation-attempt-2",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:07:00+09:00",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "docs-validation-2",
                "finished_at": "2026-07-21T21:08:00+09:00",
                "outcome": "PASS",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-finished",
            {"finished_at": "2026-07-21T21:09:00+09:00"},
        )
        self.assertEqual("finished", self.read_state()["operation_metrics"]["status"])

    def test_recorder_rejects_invalid_scope_and_cross_basis_pair_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        before = self.journal_path.read_bytes()
        for scope, expected in (
            ("metrics-final", "terminal metrics self-check"),
            ("docs scope", "lower-kebab-case"),
        ):
            with self.subTest(scope=scope), self.assertRaisesRegex(
                OperationEventError, expected
            ):
                record_operation_event(
                    self.request_root,
                    REQUEST_ID,
                    "span-started",
                    {
                        "span_id": "invalid-validation",
                        "kind": "validation",
                        "scope": scope,
                        "attempt_id": "invalid-validation-attempt",
                        "basis_revision": 1,
                        "started_at": "2026-07-21T21:01:00+09:00",
                    },
                )
            self.assertEqual(before, self.journal_path.read_bytes())

        for kind, scope, expected in (
            ("risk-review", "selection-readiness", "reserved"),
            ("integration-review", "arbitrary-scope", "integration-review scope"),
            ("baseline-review", "affected-closure", "baseline-review scope"),
            ("bundle", "unknown-bundle", "active/retired stable bundle_id"),
            ("writer", "unknown-bundle", "active/retired stable bundle_id"),
        ):
            with self.subTest(kind=kind), self.assertRaisesRegex(
                OperationEventError, expected
            ):
                record_operation_event(
                    self.request_root,
                    REQUEST_ID,
                    "span-started",
                    {
                        "span_id": f"invalid-{kind}",
                        "kind": kind,
                        "scope": scope,
                        "attempt_id": f"invalid-{kind}-attempt",
                        "basis_revision": 1,
                        "started_at": "2026-07-21T21:01:00+09:00",
                    },
                )
            self.assertEqual(before, self.journal_path.read_bytes())

        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            {
                "span_id": "accounts-bundle-1",
                "kind": "bundle",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "basis_revision": 1,
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "accounts-bundle-1",
                "finished_at": "2026-07-21T21:02:00+09:00",
                "outcome": "completed",
            },
        )
        before_pair = self.journal_path.read_bytes()
        state = self.read_state()
        state["semantic_review_closure"]["basis_revision"] = 2
        self.write_state(state)
        with self.assertRaisesRegex(OperationEventError, "must keep one basis_revision"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                {
                    "span_id": "accounts-writer-1",
                    "kind": "writer",
                    "scope": "accounts-bundle",
                    "attempt_id": "accounts-attempt-1",
                    "basis_revision": 2,
                    "started_at": "2026-07-21T21:03:00+09:00",
                },
            )
        self.assertEqual(before_pair, self.journal_path.read_bytes())

    def test_recorder_rejects_reserved_bundle_id_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        state = self.read_state()
        state["bundle_queue"] = [{"bundle_id": "selection-readiness"}]
        self.write_state(state)
        before = self.journal_path.read_bytes()
        with self.assertRaisesRegex(OperationEventError, "bundle_id.*reserved"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                {
                    "span_id": "selection-readiness-1",
                    "kind": "development-review",
                    "scope": "selection-readiness",
                    "attempt_id": "selection-readiness-attempt-1",
                    "basis_revision": 1,
                    "started_at": "2026-07-21T21:01:00+09:00",
                },
            )
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_recorder_rejects_completed_outcome_for_every_review_kind(self) -> None:
        state = self.read_state()
        state["bundle_queue"] = [{"bundle_id": "accounts-bundle"}]
        self.write_state(state)
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        cases = (
            ("development-review", "selection-readiness"),
            ("risk-review", "accounts-bundle"),
            ("integration-review", "affected-closure"),
            ("baseline-review", "project-wide"),
        )
        for index, (kind, scope) in enumerate(cases, start=1):
            span_id = f"invalid-completed-{kind}"
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                {
                    "span_id": span_id,
                    "kind": kind,
                    "scope": scope,
                    "attempt_id": f"invalid-completed-{kind}-attempt",
                    "basis_revision": 1,
                    "started_at": f"2026-07-21T21:0{index}:00+09:00",
                },
            )
            before = self.journal_path.read_bytes()
            with self.assertRaisesRegex(OperationEventError, "PASS.*FAIL"):
                record_operation_event(
                    self.request_root,
                    REQUEST_ID,
                    "span-finished",
                    {
                        "span_id": span_id,
                        "finished_at": f"2026-07-21T21:0{index}:30+09:00",
                        "outcome": "completed",
                    },
                )
            self.assertEqual(before, self.journal_path.read_bytes())

    def test_recorder_enforces_the_kind_specific_outcome_matrix(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        cases = (
            ("bundle", "accounts-bundle", "PASS", "completed.*FAIL"),
            ("writer", "accounts-bundle", "PASS", "completed.*FAIL"),
            ("validation", "bundle-check", "completed", "PASS.*FAIL"),
        )
        for index, (kind, scope, outcome, expected) in enumerate(cases, start=1):
            span_id = f"invalid-outcome-{kind}"
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                {
                    "span_id": span_id,
                    "kind": kind,
                    "scope": scope,
                    "attempt_id": f"invalid-outcome-{kind}-attempt",
                    "basis_revision": 1,
                    "started_at": f"2026-07-21T21:0{index}:00+09:00",
                },
            )
            before = self.journal_path.read_bytes()
            with self.assertRaisesRegex(OperationEventError, expected):
                record_operation_event(
                    self.request_root,
                    REQUEST_ID,
                    "span-finished",
                    {
                        "span_id": span_id,
                        "finished_at": f"2026-07-21T21:0{index}:30+09:00",
                        "outcome": outcome,
                    },
                )
            self.assertEqual(before, self.journal_path.read_bytes())

    def test_late_retry_finds_the_original_event_without_reappending(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        start_payload = {
            "span_id": "accounts-writer-1",
            "kind": "writer",
            "scope": "accounts-bundle",
            "attempt_id": "accounts-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:01:00+09:00",
        }
        started = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            start_payload,
        )
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-finished",
            {
                "span_id": "accounts-writer-1",
                "finished_at": "2026-07-21T21:02:00+09:00",
                "outcome": "completed",
            },
        )

        retried = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            start_payload,
        )
        self.assertEqual(started, retried)
        self.assertEqual(3, len(load_operation_event_journal(self.journal_path)))

    def test_pending_partial_append_is_completed_once_on_retry(self) -> None:
        first = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        payload = {
            "span_id": "accounts-bundle-1",
            "kind": "bundle",
            "scope": "accounts-bundle",
            "attempt_id": "accounts-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:01:00+09:00",
        }
        pending = self.make_event([first], "span-started", payload)
        pending_line = canonical_json_bytes(pending) + b"\n"
        (self.request_root / "operation-events.pending").write_bytes(pending_line)
        with self.journal_path.open("ab") as stream:
            stream.write(pending_line[:31])

        recovered = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            payload,
        )
        self.assertEqual(pending, recovered)
        self.assertFalse((self.request_root / "operation-events.pending").exists())
        events = load_operation_event_journal(self.journal_path)
        self.assertEqual(2, len(events))
        self.assertEqual(
            "accounts-bundle-1",
            self.read_state()["operation_metrics"]["spans"][0]["span_id"],
        )

    def test_mismatched_pending_record_is_rejected_without_append(self) -> None:
        first = record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        before = self.journal_path.read_bytes()
        pending = self.make_event(
            [],
            "span-started",
            {
                "span_id": "wrong-predecessor",
                "kind": "bundle",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        self.assertNotEqual(first["event_hash"], pending["previous_hash"])
        (self.request_root / "operation-events.pending").write_bytes(
            canonical_json_bytes(pending) + b"\n"
        )

        with self.assertRaisesRegex(OperationEventError, "does not extend"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                pending["payload"],
            )
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_lifecycle_invalid_pending_record_is_rejected_before_append(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        payload = {
            "span_id": "accounts-bundle-1",
            "kind": "bundle",
            "scope": "accounts-bundle",
            "attempt_id": "accounts-attempt-1",
            "basis_revision": 1,
            "started_at": "2026-07-21T21:01:00+09:00",
        }
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "span-started",
            payload,
        )
        events = load_operation_event_journal(self.journal_path)
        invalid_pending = self.make_event(events, "span-started", payload)
        (self.request_root / "operation-events.pending").write_bytes(
            canonical_json_bytes(invalid_pending) + b"\n"
        )
        before = self.journal_path.read_bytes()

        with self.assertRaisesRegex(OperationEventError, "starts more than once"):
            sync_operation_metrics_projection(
                self.request_root,
                expected_request_id=REQUEST_ID,
            )
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_lock_serializes_concurrent_appenders(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )

        def append(index: int) -> dict[str, object]:
            return record_operation_event(
                self.request_root,
                REQUEST_ID,
                "span-started",
                {
                    "span_id": f"parallel-span-{index}",
                    "kind": "bundle",
                    "scope": f"bundle-{index}",
                    "attempt_id": f"attempt-{index}",
                    "basis_revision": 1,
                    "started_at": f"2026-07-21T21:0{index}:00+09:00",
                },
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(append, range(1, 5)))
        events = load_operation_event_journal(self.journal_path)
        self.assertEqual(list(range(1, 6)), [event["sequence"] for event in events])
        self.assertEqual(4, len(self.read_state()["operation_metrics"]["spans"]))

    def test_windows_full_operation_uses_binary_files_without_directory_fsync(
        self,
    ) -> None:
        probe = textwrap.dedent(
            f"""
            import argparse
            import contextlib
            import datetime
            import hashlib
            import json
            import os
            import pathlib
            import re
            import sys
            import tempfile
            import types
            import typing

            source_path = pathlib.Path({str(RECORDER)!r})
            calls = []
            fake_msvcrt = types.ModuleType("msvcrt")
            fake_msvcrt.LK_LOCK = 1
            fake_msvcrt.LK_UNLCK = 2

            def locking(descriptor, mode, length):
                calls.append((mode, length, os.lseek(descriptor, 0, os.SEEK_CUR)))

            fake_msvcrt.locking = locking
            sys.modules["msvcrt"] = fake_msvcrt
            original_name = os.name
            namespace = {{"__name__": "windows_recorder_probe", "__file__": str(source_path)}}
            try:
                os.name = "nt"
                exec(compile(source_path.read_bytes(), str(source_path), "exec"), namespace)
            finally:
                os.name = original_name

            assert namespace["_WINDOWS_LOCKING"] is True
            assert "fcntl" not in namespace
            with tempfile.TemporaryDirectory() as temporary:
                request_id = "20260721-210001-windows-recorder"
                root = (
                    pathlib.Path(temporary)
                    / ".stageflow"
                    / "atomic-docs"
                    / "requests"
                    / request_id
                )
                root.mkdir(parents=True)
                state_path = root / namespace["WORK_STATE_FILENAME"]
                state_path.write_text(
                    json.dumps(
                        {{
                            "request_id": request_id,
                            "context_selection": {{"version": "5", "candidates": []}},
                            "selection_readiness": {{"basis_revision": 1}},
                            "semantic_review_closure": {{"basis_revision": 1}},
                            "bundle_queue": [],
                        }}
                    ),
                    encoding="utf-8",
                )

                original_open = os.open
                binary_flag = 1 << 40
                binary_paths = set()

                def guarded_open(path, flags, mode=0o777, *, dir_fd=None):
                    assert not pathlib.Path(path).is_dir(), path
                    if pathlib.Path(path).name in {{
                        namespace["JOURNAL_FILENAME"],
                        namespace["LOCK_FILENAME"],
                    }}:
                        assert flags & binary_flag, (path, flags)
                        binary_paths.add(pathlib.Path(path).name)
                    flags &= ~binary_flag
                    if dir_fd is None:
                        return original_open(path, flags, mode)
                    return original_open(path, flags, mode, dir_fd=dir_fd)

                had_binary_flag = hasattr(os, "O_BINARY")
                original_binary_flag = getattr(os, "O_BINARY", None)
                os.O_BINARY = binary_flag
                os.open = guarded_open
                try:
                    namespace["record_operation_event"](
                        root,
                        request_id,
                        "operation-started",
                        {{"started_at": "2026-07-21T21:00:00+09:00"}},
                    )
                finally:
                    os.open = original_open
                    if had_binary_flag:
                        os.O_BINARY = original_binary_flag
                    else:
                        del os.O_BINARY

                assert binary_paths == {{
                    namespace["JOURNAL_FILENAME"],
                    namespace["LOCK_FILENAME"],
                }}, binary_paths

                journal_path = root / namespace["JOURNAL_FILENAME"]
                journal_bytes = journal_path.read_bytes()
                assert b"\\r" not in journal_bytes
                events = namespace["load_operation_event_journal"](
                    journal_path,
                    expected_request_id=request_id,
                )
                projection = namespace["reduce_operation_events"](
                    events,
                    expected_request_id=request_id,
                )
                assert json.loads(state_path.read_text(encoding="utf-8"))[
                    "operation_metrics"
                ] == projection
                assert not (root / namespace["PENDING_FILENAME"]).exists()
                assert (root / namespace["LOCK_FILENAME"]).read_bytes() == b"\\0"
            assert calls == [(1, 1, 0), (2, 1, 0)], calls
            """
        )
        result = subprocess.run(
            [sys.executable, "-B", "-S", "-c", probe],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_sync_repairs_projection_without_adding_an_event(self) -> None:
        record_operation_event(
            self.request_root,
            REQUEST_ID,
            "operation-started",
            {"started_at": "2026-07-21T21:00:00+09:00"},
        )
        before = self.journal_path.read_bytes()
        stale = self.read_state()
        stale["operation_metrics"] = {"version": "1", "status": "finished"}
        self.write_state(stale)

        projection = sync_operation_metrics_projection(
            self.request_root,
            expected_request_id=REQUEST_ID,
        )
        self.assertEqual("active", projection["status"])
        self.assertEqual(projection, self.read_state()["operation_metrics"])
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_sync_rejects_terminal_journal_without_current_final_pass(self) -> None:
        started = self.started_event()
        finished = self.make_event(
            [started],
            "operation-finished",
            {"finished_at": "2026-07-21T21:01:00+09:00"},
        )
        self.write_events([started, finished])

        with self.assertRaisesRegex(
            OperationEventError,
            "latest span to be the current-basis successful final",
        ):
            sync_operation_metrics_projection(
                self.request_root,
                expected_request_id=REQUEST_ID,
            )

    def test_loader_rejects_duplicate_keys_noncanonical_bytes_crlf_and_partial_line(self) -> None:
        event = self.started_event()
        canonical_line = canonical_json_bytes(event) + b"\n"
        mutations = {
            "duplicate JSON key": (
                b'{"event_hash":"' + str(event["event_hash"]).encode() + b'",'
                + canonical_json_bytes(event)[1:] + b"\n"
            ),
            "not canonical JSON bytes": (json.dumps(event).encode() + b"\n"),
            "CR or CRLF": canonical_line.replace(b"\n", b"\r\n"),
            "partial final line": canonical_line[:-1],
        }
        for expected, raw in mutations.items():
            with self.subTest(expected=expected):
                self.journal_path.write_bytes(raw)
                with self.assertRaisesRegex(OperationEventError, expected):
                    load_operation_event_journal(self.journal_path)

    def test_loader_rejects_bad_sequence_previous_hash_and_event_hash(self) -> None:
        first = self.started_event()
        second = self.make_event(
            [first],
            "span-started",
            {
                "span_id": "accounts-writer-1",
                "kind": "writer",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        cases: list[tuple[str, list[dict[str, object]]]] = []

        bad_sequence = copy.deepcopy(second)
        bad_sequence["sequence"] = 3
        bad_sequence["event_hash"] = canonical_event_hash(bad_sequence)
        cases.append(("sequence must be contiguous", [first, bad_sequence]))

        bad_previous = copy.deepcopy(second)
        bad_previous["previous_hash"] = "1" * 64
        bad_previous["event_hash"] = canonical_event_hash(bad_previous)
        cases.append(("previous_hash does not match", [first, bad_previous]))

        bad_hash = copy.deepcopy(second)
        bad_hash["event_hash"] = "f" * 64
        cases.append(("event_hash does not match", [first, bad_hash]))

        for expected, events in cases:
            with self.subTest(expected=expected):
                self.write_events(events)
                with self.assertRaisesRegex(OperationEventError, expected):
                    load_operation_event_journal(self.journal_path)

    def test_reducer_rejects_malformed_lifecycle_and_time_order(self) -> None:
        first = self.started_event()
        missing_start = self.make_event(
            [],
            "span-finished",
            {
                "span_id": "missing-span",
                "finished_at": "2026-07-21T21:01:00+09:00",
                "outcome": "FAIL",
            },
        )
        with self.assertRaisesRegex(OperationEventError, "operation-started must precede"):
            reduce_operation_events([missing_start])

        active = self.make_event(
            [first],
            "span-started",
            {
                "span_id": "active-span",
                "kind": "writer",
                "scope": "accounts-bundle",
                "attempt_id": "accounts-attempt-1",
                "started_at": "2026-07-21T21:01:00+09:00",
            },
        )
        overlapping_final = self.make_event(
            [first, active],
            "span-started",
            {
                "span_id": "docs-validation-1",
                "kind": "validation",
                "scope": "docs",
                "attempt_id": "docs-validation-attempt-1",
                "started_at": "2026-07-21T21:01:30+09:00",
            },
        )
        with self.assertRaisesRegex(OperationEventError, "after every other span finishes"):
            reduce_operation_events([first, active, overlapping_final])

        finish_operation = self.make_event(
            [first, active],
            "operation-finished",
            {"finished_at": "2026-07-21T21:02:00+09:00"},
        )
        with self.assertRaisesRegex(OperationEventError, "requires every span"):
            reduce_operation_events([first, active, finish_operation])

        early = copy.deepcopy(active)
        early["payload"]["started_at"] = "2026-07-21T20:59:00+09:00"
        early["event_hash"] = canonical_event_hash(early)
        with self.assertRaisesRegex(OperationEventError, "starts before the operation"):
            reduce_operation_events([first, early])

    def test_v5_and_safe_request_path_are_mandatory(self) -> None:
        old = self.read_state()
        old["context_selection"]["version"] = "4"
        self.write_state(old)
        with self.assertRaisesRegex(OperationEventError, "exact context_selection.version `5`"):
            record_operation_event(
                self.request_root,
                REQUEST_ID,
                "operation-started",
                {"started_at": "2026-07-21T21:00:00+09:00"},
            )
        self.assertFalse(self.journal_path.exists())

        with self.assertRaisesRegex(OperationEventError, "safe path segment"):
            record_operation_event(
                self.request_root,
                "../escape",
                "operation-started",
                {"started_at": "2026-07-21T21:00:00+09:00"},
            )

    def test_cli_records_and_sync_does_not_emit_an_event(self) -> None:
        command = [
            sys.executable,
            str(RECORDER),
            "--root",
            str(self.root),
            "--request-id",
            REQUEST_ID,
            "operation-started",
            "--started-at",
            "2026-07-21T21:00:00+09:00",
        ]
        recorded = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        self.assertTrue(recorded.stdout.startswith("RECORDED atomic-docs operation event:"))
        before = self.journal_path.read_bytes()

        synced = subprocess.run(
            [
                sys.executable,
                str(RECORDER),
                "--root",
                str(self.root),
                "--request-id",
                REQUEST_ID,
                "sync",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, synced.returncode, synced.stderr)
        self.assertTrue(synced.stdout.startswith("SYNCED atomic-docs operation events:"))
        self.assertEqual(before, self.journal_path.read_bytes())

    def test_module_documents_local_tamper_evidence_boundary(self) -> None:
        source = RECORDER.read_text(encoding="utf-8")
        self.assertIn("roll every file back to the", source)
        self.assertIn("external trusted anchor", source)
        self.assertIn("os.O_APPEND", source)
        self.assertNotIn("state_patch =", source)


if __name__ == "__main__":
    unittest.main()
