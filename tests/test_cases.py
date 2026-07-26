from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.cases import (
    archive_latest_case,
    build_queue_rows,
    discover_cases,
    filter_case_queue,
    publish_latest_snapshot,
    queue_rows_to_csv,
    refresh_case_index,
    register_case,
)
from sowni.database import InvestigatorDatabase
from sowni.models import AnalystReview


def write_case(
    case_dir: Path,
    run_id: str,
    *,
    generated_at: str = "2026-07-26T10:00:00+00:00",
) -> dict:
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "run_id": run_id,
        "software_version": "1.0.0",
        "generated_at": generated_at,
        "mode": "live",
        "query": "Example Company",
        "classification": "no_material_indicator",
        "target_entity": {"name": "Example Company"},
    }
    (case_dir / "investigation_result.json").write_text(
        json.dumps(result),
        encoding="utf-8",
    )
    (case_dir / "investigation_graph.json").write_text(
        json.dumps({"nodes": [], "edges": []}),
        encoding="utf-8",
    )
    return result


class CaseRegistryTests(unittest.TestCase):
    def test_archives_legacy_latest_with_analyst_review(self):
        with tempfile.TemporaryDirectory() as temp:
            outputs_root = Path(temp) / "outputs"
            latest_dir = outputs_root / "latest"
            write_case(latest_dir, "soni-legacy")
            database = InvestigatorDatabase(latest_dir / "investigator.sqlite")
            try:
                database.save_analyst_review(
                    AnalystReview(
                        run_id="soni-legacy",
                        entity_id="ENTITY-1",
                        target_name="Example Company",
                        system_classification="no_material_indicator",
                        system_version="0.3.2",
                        disposition="closed_no_material_indicator",
                        reviewer="JK",
                        notes="Reviewed identifiers and source records.",
                        created_at=datetime.now(UTC).isoformat(),
                    )
                )
            finally:
                database.close()

            archived_dir = archive_latest_case(outputs_root)
            self.assertEqual(
                archived_dir,
                outputs_root.resolve() / "cases" / "soni-legacy",
            )
            archived_database = InvestigatorDatabase(
                archived_dir / "investigator.sqlite"
            )
            try:
                reviews = archived_database.list_analyst_reviews(
                    run_id="soni-legacy"
                )
            finally:
                archived_database.close()
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0].reviewer, "JK")

            cases = discover_cases(outputs_root)
            self.assertEqual([item["run_id"] for item in cases], ["soni-legacy"])
            index = json.loads(
                (outputs_root / "cases" / "index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(index["case_count"], 1)

    def test_registers_sorts_and_publishes_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            outputs_root = Path(temp) / "outputs"
            older_dir = outputs_root / "cases" / "soni-older"
            newer_dir = outputs_root / "cases" / "soni-newer"
            older = write_case(
                older_dir,
                "soni-older",
                generated_at="2026-07-25T10:00:00+00:00",
            )
            newer = write_case(
                newer_dir,
                "soni-newer",
                generated_at="2026-07-26T10:00:00+00:00",
            )
            register_case(outputs_root, older_dir, older)
            register_case(outputs_root, newer_dir, newer)

            cases = discover_cases(outputs_root)
            self.assertEqual(
                [item["run_id"] for item in cases],
                ["soni-newer", "soni-older"],
            )

            latest_dir = outputs_root / "latest"
            latest_dir.mkdir(parents=True)
            (latest_dir / "stale.txt").write_text("stale", encoding="utf-8")
            published = publish_latest_snapshot(outputs_root, newer_dir)
            self.assertEqual(published, latest_dir.resolve())
            self.assertFalse((published / "stale.txt").exists())
            published_result = json.loads(
                (published / "investigation_result.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(published_result["run_id"], "soni-newer")

    def test_incomplete_case_is_not_indexed_or_published(self):
        with tempfile.TemporaryDirectory() as temp:
            outputs_root = Path(temp) / "outputs"
            incomplete = outputs_root / "cases" / "soni-incomplete"
            incomplete.mkdir(parents=True)
            (incomplete / "investigation_result.json").write_text(
                json.dumps(
                    {
                        "run_id": "soni-incomplete",
                        "classification": "no_material_indicator",
                    }
                ),
                encoding="utf-8",
            )
            refresh_case_index(outputs_root)
            self.assertEqual(discover_cases(outputs_root), [])
            with self.assertRaises(FileNotFoundError):
                publish_latest_snapshot(outputs_root, incomplete)

    def test_case_queue_filters_workflow_and_searchable_fields(self):
        cases = [
            {
                "run_id": "soni-one",
                "target_name": "Example Holdings",
                "query": "Example Holdings LLC",
                "classification": "no_material_indicator",
                "workflow": {
                    "status": "in_review",
                    "priority": "high",
                    "assignee": "Analyst One",
                    "tags": ["ownership", "urgent"],
                },
            },
            {
                "run_id": "soni-two",
                "target_name": "Second Company",
                "query": "Second Company",
                "classification": "direct_designation",
                "workflow": {
                    "status": "closed",
                    "priority": "normal",
                    "assignee": "Analyst Two",
                    "tags": ["resolved"],
                },
            },
        ]
        self.assertEqual(
            [item["run_id"] for item in filter_case_queue(cases, search="ownership")],
            ["soni-one"],
        )
        self.assertEqual(
            [
                item["run_id"]
                for item in filter_case_queue(
                    cases,
                    status="closed",
                    priority="normal",
                )
            ],
            ["soni-two"],
        )
        cases[0]["analyst_review_count"] = 2
        cases[0]["workflow_event_count"] = 3
        rows = build_queue_rows(cases)
        self.assertEqual(rows[0]["status"], "in_review")
        self.assertEqual(rows[0]["analyst_review_count"], 2)
        self.assertEqual(rows[0]["tags"], "ownership, urgent")
        csv_payload = queue_rows_to_csv(rows)
        self.assertIn("run_id,generated_at,target_name", csv_payload)
        self.assertIn("soni-one", csv_payload)


if __name__ == "__main__":
    unittest.main()
