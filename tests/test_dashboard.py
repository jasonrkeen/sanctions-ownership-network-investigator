from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.dashboard import build_dot_graph, load_latest_case


class DashboardTests(unittest.TestCase):
    def test_load_latest_case_validates_and_loads_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "investigation_result.json").write_text(
                json.dumps(
                    {
                        "run_id": "test-run",
                        "classification": "no_material_indicator",
                    }
                ),
                encoding="utf-8",
            )
            (root / "investigation_graph.json").write_text(
                json.dumps({"nodes": [], "edges": []}),
                encoding="utf-8",
            )
            result, graph = load_latest_case(root)
            self.assertEqual(result["run_id"], "test-run")
            self.assertEqual(graph["nodes"], [])

    def test_build_dot_graph_filters_addresses_and_marks_target(self):
        graph = {
            "nodes": [
                {
                    "id": "ENTITY-1",
                    "label": 'Example "Target"',
                    "node_type": "Entity",
                    "designated": False,
                },
                {
                    "id": "ENTITY-2",
                    "label": "Blocked Owner",
                    "node_type": "Entity",
                    "designated": True,
                },
                {
                    "id": "ADDRESS-1",
                    "label": "100 Test Street",
                    "node_type": "Address",
                    "designated": False,
                },
            ],
            "edges": [
                {
                    "source": "ENTITY-2",
                    "target": "ENTITY-1",
                    "type": "OWNS",
                    "ownership_pct": 60.0,
                },
                {
                    "source": "ENTITY-1",
                    "target": "ADDRESS-1",
                    "type": "REGISTERED_AT",
                    "ownership_pct": None,
                },
            ],
        }
        dot = build_dot_graph(graph, target_id="ENTITY-1", include_addresses=False)
        self.assertIn('fillcolor="#F3D58A"', dot)
        self.assertIn('label="OWNS 60%"', dot)
        self.assertIn('Example \\"Target\\"', dot)
        self.assertNotIn("ADDRESS-1", dot)


if __name__ == "__main__":
    unittest.main()
