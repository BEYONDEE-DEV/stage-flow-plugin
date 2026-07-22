from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "atomic-docs-v5"
CORPUS = FIXTURE_ROOT / "corpus.json"
CHECKSUMS = FIXTURE_ROOT / "checksums.json"
EXPECTED_CASES = {
    "GOLDEN-V5-001": "case-001",
    "GOLDEN-V5-002": "case-002",
    "GOLDEN-V5-003": "case-003",
    "GOLDEN-V5-004": "case-004",
}
RAW_FILES = ["contract.md", "request.json", "source.py"]
EXPECTED_RECEIPT_OBSERVATIONS = {
    "GOLDEN-V5-001": {
        "reviewer_role": "risk",
        "scope": "BUNDLE-V5-001",
        "validation_question": (
            "Does PRINCIPAL-V5-001 project contact-summary only from the authorized and "
            "requested object?"
        ),
        "observed_result": (
            "The authorization checks OBJECT-V5-001-A, but source.py loads OBJECT-V5-001-B "
            "for contact-summary."
        ),
        "verdict": "FAIL",
        "required_finding_ids": ["FINDING-V5-001"],
    },
    "GOLDEN-V5-002": {
        "reviewer_role": "risk",
        "scope": "BUNDLE-V5-002",
        "validation_question": (
            "Does schedule_payload bind the outbound programId field to the verified canonical "
            "programId value?"
        ),
        "observed_result": (
            "The applicable owner contract requires programId, but source.py supplies displayId "
            "to the programId field."
        ),
        "verdict": "FAIL",
        "required_finding_ids": ["FINDING-V5-002"],
    },
    "GOLDEN-V5-003": {
        "reviewer_role": "development",
        "scope": "final-request-bound",
        "validation_question": (
            "Does every AID created by this v5 request have a managed or request-local "
            "[AID-REF:<aid>] consumer at the final gate?"
        ),
        "observed_result": (
            "AID-V5-003-ALPHA and AID-V5-003-BETA are defined, but neither has a managed or "
            "request-local reference consumer."
        ),
        "verdict": "FAIL",
        "required_finding_ids": [
            "FINDING-V5-003-ALPHA",
            "FINDING-V5-003-BETA",
        ],
    },
    "GOLDEN-V5-004": {
        "reviewer_role": "risk",
        "scope": "BUNDLE-V5-004",
        "validation_question": (
            "Do the retention and callback conflicts remain separate findings with their "
            "authoritative resolution owners?"
        ),
        "observed_result": (
            "The 72-hour retention and unsigned callback violate independent contracts owned by "
            "retention-owner and callback-owner."
        ),
        "verdict": "FAIL",
        "required_finding_ids": ["FINDING-V5-004-A", "FINDING-V5-004-B"],
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class AtomicDocsV5GoldenCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = load_json(CORPUS)
        self.cases = self.corpus["cases"]

    def test_corpus_is_complete_and_keeps_raw_inputs_separate(self) -> None:
        self.assertEqual(self.corpus["version"], "1")
        self.assertEqual(
            {case["case_id"]: case["slug"] for case in self.cases},
            EXPECTED_CASES,
        )

        for case in self.cases:
            raw_root = FIXTURE_ROOT / case["raw_root"]
            expected_path = FIXTURE_ROOT / case["expected"]
            self.assertEqual(case["raw_files"], RAW_FILES)
            self.assertEqual(
                sorted(path.name for path in raw_root.iterdir() if path.is_file()),
                RAW_FILES,
            )
            self.assertEqual(raw_root.parent.name, "raw")
            self.assertEqual(expected_path.parent.name, "expected")
            self.assertFalse(expected_path.is_relative_to(raw_root))
            self.assertEqual(load_json(raw_root / "request.json")["case_id"], case["case_id"])
            self.assertEqual(load_json(expected_path)["case_id"], case["case_id"])

    def test_machine_expectations_preserve_each_regression(self) -> None:
        expected = {
            case["case_id"]: load_json(FIXTURE_ROOT / case["expected"])
            for case in self.cases
        }

        pii = expected["GOLDEN-V5-001"]
        self.assertEqual(pii["expected_terminal_verdict"], "FAIL")
        self.assertEqual(pii["expected_findings"][0]["disposition"], "conflict")
        self.assertEqual(pii["expected_findings"][0]["trace_kind"], "permission-privacy")
        self.assertIs(pii["expected_findings"][0]["observed_conflict"], True)
        self.assertEqual(
            pii["expected_findings"][0]["permission_privacy"],
            {
                "principal": "PRINCIPAL-V5-001",
                "authorized_object_or_data": "OBJECT-V5-001-A",
                "loaded_object": "OBJECT-V5-001-B",
                "projection_or_use": "contact-summary",
            },
        )
        self.assertIn("Rule", pii["forbidden_outcomes"])

        identifier = expected["GOLDEN-V5-002"]
        finding = identifier["expected_findings"][0]
        self.assertEqual(finding["trace_kind"], "contract")
        self.assertEqual(finding["authority_status"], "verified")
        self.assertEqual(finding["applicability_status"], "verified")
        self.assertIs(finding["observed_conflict"], True)
        self.assertEqual(finding["verdict"], "bug_or_regression")
        self.assertIn("confirmation_needed", identifier["forbidden_outcomes"])

        orphan = expected["GOLDEN-V5-003"]
        self.assertEqual(orphan["expected_terminal_verdict"], "FAIL")
        self.assertEqual(
            {finding["aid"] for finding in orphan["expected_findings"]},
            {"AID-V5-003-ALPHA", "AID-V5-003-BETA"},
        )
        self.assertTrue(
            all(finding["gate"] == "final-request-bound" for finding in orphan["expected_findings"])
        )

        partitioned = expected["GOLDEN-V5-004"]
        self.assertEqual(
            partitioned["required_finding_partition"],
            [["CLAIM-V5-004-A"], ["CLAIM-V5-004-B"]],
        )
        self.assertEqual(
            partitioned["forbidden_groupings"],
            [
                {
                    "type": "single-merged-gap",
                    "label": "Gap",
                    "claim_ids": ["CLAIM-V5-004-A", "CLAIM-V5-004-B"],
                }
            ],
        )
        self.assertEqual(
            {finding["risk_id"] for finding in partitioned["expected_findings"]},
            {"RISK-V5-004-A", "RISK-V5-004-B"},
        )
        self.assertEqual(
            {finding["resolution_owner"] for finding in partitioned["expected_findings"]},
            {"retention-owner", "callback-owner"},
        )

    def test_expected_receipt_observations_bind_semantics_without_claiming_proof(self) -> None:
        for case in self.cases:
            expectation = load_json(FIXTURE_ROOT / case["expected"])
            observation = expectation["expected_receipt_observation"]
            expected = EXPECTED_RECEIPT_OBSERVATIONS[case["case_id"]]

            self.assertEqual(observation["reviewer_role"], expected["reviewer_role"])
            self.assertEqual(observation["scope"], expected["scope"])
            self.assertEqual(
                observation["validation_question"], expected["validation_question"]
            )
            self.assertEqual(observation["observed_result"], expected["observed_result"])
            self.assertEqual(observation["verdict"], expected["verdict"])
            self.assertEqual(observation["verdict"], expectation["expected_terminal_verdict"])

            report_binding = observation["report_binding"]
            self.assertEqual(report_binding["report_kind"], "findings-only")
            self.assertEqual(
                report_binding["required_finding_ids"], expected["required_finding_ids"]
            )
            self.assertEqual(
                set(report_binding["required_finding_ids"]),
                {finding["finding_id"] for finding in expectation["expected_findings"]},
            )
            self.assertIs(report_binding["request_local_path_required"], True)
            self.assertIs(report_binding["sha256_required"], True)
            self.assertIs(observation["cryptographic_semantic_proof_claimed"], False)

            # This is an immutable expected observation contract, not a fabricated review run.
            for actual_receipt_field in (
                "reviewer_agent_id",
                "review_run_id",
                "basis_manifest_sha256",
                "report_path",
                "report_sha256",
            ):
                self.assertNotIn(actual_receipt_field, observation)

    def test_case_finding_and_aid_definition_ids_are_unique(self) -> None:
        case_ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))

        finding_ids: list[str] = []
        definition_ids: list[str] = []
        claim_ids: list[str] = []
        risk_ids: list[str] = []
        bundle_ids: list[str] = []
        for case in self.cases:
            expectation = load_json(FIXTURE_ROOT / case["expected"])
            finding_ids.extend(finding["finding_id"] for finding in expectation["expected_findings"])
            raw_root = FIXTURE_ROOT / case["raw_root"]
            request = load_json(raw_root / "request.json")
            claim_ids.extend(claim["claim_id"] for claim in request.get("selected_claims", []))
            review_scope = request.get("review_scope", {})
            if "risk_id" in review_scope:
                risk_ids.append(review_scope["risk_id"])
            risk_ids.extend(review_scope.get("risk_ids", []))
            if "bundle_id" in review_scope:
                bundle_ids.append(review_scope["bundle_id"])
            raw_text = "\n".join(
                (raw_root / name).read_text(encoding="utf-8")
                for name in RAW_FILES
            )
            definition_ids.extend(re.findall(r"\[AID:([A-Z0-9-]+)\]", raw_text))

        self.assertEqual(len(finding_ids), len(set(finding_ids)))
        self.assertEqual(len(claim_ids), len(set(claim_ids)))
        self.assertEqual(len(risk_ids), len(set(risk_ids)))
        self.assertEqual(len(bundle_ids), len(set(bundle_ids)))
        self.assertEqual(len(definition_ids), len(set(definition_ids)))
        self.assertEqual(definition_ids, ["AID-V5-003-ALPHA", "AID-V5-003-BETA"])

        orphan_raw = FIXTURE_ROOT / "raw" / "case-003"
        orphan_text = "\n".join(path.read_text(encoding="utf-8") for path in orphan_raw.iterdir())
        self.assertNotIn("[AID-REF:", orphan_text)

    def test_corpus_contains_no_real_project_identity_or_absolute_paths(self) -> None:
        forbidden_fragments = (
            "stage-flow-plugin",
            "events-web",
            "majoong",
            "/home/",
            "c:\\users\\",
            "github.com/",
        )
        fixture_files = [
            path
            for path in FIXTURE_ROOT.rglob("*")
            if path.is_file() and path != CHECKSUMS
        ]
        for path in fixture_files:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, lowered, f"{path} contains forbidden `{fragment}`")
            self.assertIsNone(
                re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.IGNORECASE),
                f"{path} contains an email-like value",
            )

    def test_checksum_manifest_locks_every_corpus_file(self) -> None:
        manifest = load_json(CHECKSUMS)
        self.assertEqual(manifest["algorithm"], "sha256")
        actual_files = sorted(
            path.relative_to(FIXTURE_ROOT).as_posix()
            for path in FIXTURE_ROOT.rglob("*")
            if path.is_file() and path != CHECKSUMS
        )
        self.assertEqual(list(manifest["files"]), actual_files)
        for relative_path, expected_digest in manifest["files"].items():
            digest = hashlib.sha256((FIXTURE_ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(digest, expected_digest, relative_path)


if __name__ == "__main__":
    unittest.main()
