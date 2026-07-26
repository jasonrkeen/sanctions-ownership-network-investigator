from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.comparison import compare_cases


def result(run_id: str, *, classification: str, score: float) -> dict:
    return {
        "run_id": run_id,
        "generated_at": "2026-07-26T12:00:00+00:00",
        "query": "Example Company",
        "target_entity": {"name": "Example Company"},
        "classification": classification,
        "mode": "live",
        "software_version": "1.0.0",
        "resolution_candidates": [
            {"entity_id": "ENTITY-1", "entity_name": "Example Company", "score": score}
        ],
        "matches": [],
        "sources": [{"name": "OFAC SDN List"}],
        "indicators": [],
    }


class CaseComparisonTests(unittest.TestCase):
    def test_comparison_reports_deltas_and_added_graph_evidence(self):
        baseline = result(
            "soni-baseline",
            classification="no_material_indicator",
            score=80.0,
        )
        comparison = result(
            "soni-comparison",
            classification="ownership_derived_candidate",
            score=92.0,
        )
        comparison["matches"] = [
            {"entity_id": "ENTITY-2", "entity_name": "Direct Candidate"}
        ]
        comparison["sources"].append({"name": "GLEIF Global LEI Index"})
        comparison["indicators"].append({"title": "Ownership path"})
        baseline_graph = {"nodes": [{"id": "ENTITY-1"}], "edges": []}
        comparison_graph = {
            "nodes": [{"id": "ENTITY-1"}, {"id": "ENTITY-2"}],
            "edges": [
                {
                    "source": "ENTITY-2",
                    "target": "ENTITY-1",
                    "type": "OWNS",
                    "ownership_pct": 60.0,
                }
            ],
        }

        report = compare_cases(
            baseline,
            baseline_graph,
            comparison,
            comparison_graph,
            baseline_review_count=1,
            comparison_review_count=3,
        )

        self.assertTrue(report["same_target"])
        self.assertEqual(report["deltas"]["identity_score"], 12.0)
        self.assertEqual(report["deltas"]["graph_edge_count"], 1.0)
        self.assertEqual(report["deltas"]["review_count"], 2.0)
        self.assertEqual(
            report["sanctions_candidates"]["added"][0]["entity_id"],
            "ENTITY-2",
        )
        self.assertEqual(
            report["identity_candidates"]["changed"][0]["score_delta"],
            12.0,
        )
        self.assertEqual(report["sources"]["added"], ["GLEIF Global LEI Index"])
        self.assertEqual(report["indicators"]["added"], ["Ownership path"])

    def test_same_run_cannot_be_compared_to_itself(self):
        payload = result(
            "soni-same",
            classification="no_material_indicator",
            score=80.0,
        )
        with self.assertRaisesRegex(ValueError, "two different"):
            compare_cases(
                payload,
                {"nodes": [], "edges": []},
                payload,
                {"nodes": [], "edges": []},
            )


if __name__ == "__main__":
    unittest.main()
