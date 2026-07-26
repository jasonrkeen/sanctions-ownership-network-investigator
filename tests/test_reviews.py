from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.database import InvestigatorDatabase
from sowni.models import AnalystReview


def review(disposition: str, notes: str = "Reviewed authoritative identifiers.") -> AnalystReview:
    return AnalystReview(
        run_id="test-run",
        entity_id="ENTITY-1",
        target_name="Example Entity",
        system_classification="no_material_indicator",
        system_version="0.3.1",
        disposition=disposition,
        reviewer="JK",
        notes=notes,
        created_at="2026-07-26T12:00:00+00:00",
    )


class AnalystReviewTests(unittest.TestCase):
    def test_reviews_are_append_only_and_returned_newest_first(self):
        with tempfile.TemporaryDirectory() as temp:
            database = InvestigatorDatabase(Path(temp) / "investigator.sqlite")
            try:
                first_id = database.save_analyst_review(
                    review("needs_more_information")
                )
                second = review(
                    "identity_confirmed",
                    "Confirmed name, LEI, jurisdiction, and registered address.",
                )
                second.created_at = "2026-07-26T13:00:00+00:00"
                second_id = database.save_analyst_review(second)
                reviews = database.list_analyst_reviews(run_id="test-run")
                review_count = database.count_analyst_reviews("test-run")
            finally:
                database.close()
        self.assertEqual((first_id, second_id), (1, 2))
        self.assertEqual([item.review_id for item in reviews], [2, 1])
        self.assertEqual(reviews[0].disposition, "identity_confirmed")
        self.assertEqual(reviews[1].disposition, "needs_more_information")
        self.assertEqual(review_count, 2)

    def test_review_requires_supported_disposition_and_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            database = InvestigatorDatabase(Path(temp) / "investigator.sqlite")
            try:
                with self.assertRaises(ValueError):
                    database.save_analyst_review(review("unsupported"))
                with self.assertRaises(ValueError):
                    database.save_analyst_review(
                        review("needs_more_information", notes="")
                    )
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
