from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.models import Entity, Relationship
from sowni.ownership import derive_ownership_status, find_ownership_path


class OwnershipTests(unittest.TestCase):
    def test_multilevel_propagation(self):
        entities = [
            Entity("A", "Blocked Owner", "Individual", "test", designated=True),
            Entity("B", "Holding Company", "Entity", "test"),
            Entity("C", "Target Company", "Entity", "test"),
        ]
        relationships = [
            Relationship("R1", "A", "B", "OWNS", "test", ownership_pct=60),
            Relationship("R2", "B", "C", "OWNS", "test", ownership_pct=55),
        ]
        findings = derive_ownership_status(entities, relationships)
        self.assertEqual(findings["A"].status, "direct_designation")
        self.assertEqual(findings["B"].status, "ownership_derived_candidate")
        self.assertEqual(findings["C"].status, "ownership_derived_candidate")
        self.assertEqual(findings["B"].iteration, 1)
        self.assertEqual(findings["C"].iteration, 2)
        self.assertEqual(find_ownership_path("C", findings), ["C", "B", "A"])

    def test_minority_interest_does_not_propagate(self):
        entities = [
            Entity("A", "Blocked Owner", "Individual", "test", designated=True),
            Entity("B", "Minority Company", "Entity", "test"),
        ]
        relationships = [
            Relationship("R1", "A", "B", "OWNS", "test", ownership_pct=49.9)
        ]
        findings = derive_ownership_status(entities, relationships)
        self.assertNotIn("B", findings)

    def test_accounting_parent_link_does_not_propagate(self):
        entities = [
            Entity("A", "Blocked Parent", "Entity", "test", designated=True),
            Entity("B", "Accounting Subsidiary", "Entity", "test"),
        ]
        relationships = [
            Relationship(
                "R1",
                "A",
                "B",
                "DIRECT_ACCOUNTING_CONSOLIDATING_PARENT_OF",
                "GLEIF",
                ownership_pct=None,
            )
        ]
        findings = derive_ownership_status(entities, relationships)
        self.assertNotIn("B", findings)


if __name__ == "__main__":
    unittest.main()
