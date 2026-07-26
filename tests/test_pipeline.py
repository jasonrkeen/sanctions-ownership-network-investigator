from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.pipeline import run_investigation
from sowni.sample_data import load_sample_data


class PipelineTests(unittest.TestCase):
    def test_demo_pipeline(self):
        entities, aliases, addresses, relationships = load_sample_data(
            PROJECT_ROOT / "data" / "sample"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = run_investigation(
                query="Harbor Meridian Trading LLC",
                entities=entities,
                aliases=aliases,
                addresses=addresses,
                relationships=relationships,
                output_dir=root / "outputs",
                database_path=root / "outputs" / "investigator.sqlite",
                mode="sample",
            )
            self.assertEqual(result["classification"], "ownership_derived_candidate")
            self.assertEqual(
                result["ownership_path"],
                ["DEMO-E001", "DEMO-E002", "DEMO-E003"],
            )
            self.assertTrue((root / "outputs" / "investigation_brief.md").exists())
            self.assertTrue((root / "outputs" / "investigation_graph.json").exists())
            self.assertTrue((root / "outputs" / "investigator.sqlite").exists())
            payload = json.loads(
                (root / "outputs" / "investigation_result.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["target_entity"]["name"], "Harbor Meridian Trading LLC")
            self.assertEqual(payload["software_version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
