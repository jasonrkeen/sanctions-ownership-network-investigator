from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.matching import EntityMatcher, name_similarity
from sowni.models import Alias, Entity
from sowni.normalize import normalize_name


class NormalizeMatchingTests(unittest.TestCase):
    def test_normalization_removes_punctuation_and_suffix(self):
        self.assertEqual(
            normalize_name("Harbor-Meridian Trading, LLC", strip_legal_suffixes=True),
            "HARBOR MERIDIAN TRADING",
        )

    def test_legal_suffix_variant_scores_high(self):
        self.assertGreaterEqual(
            name_similarity("Meridian Holdings", "Meridian Holdings PLC"),
            98,
        )

    def test_alias_is_searchable(self):
        entity = Entity(
            entity_id="E1",
            name="Meridian Holdings PLC",
            entity_type="Entity",
            source="test",
            designated=True,
        )
        alias = Alias(
            alias_id="A1",
            entity_id="E1",
            name="Meridian HLDGS",
            alias_type="aka",
            source="test",
        )
        results = EntityMatcher([entity], [alias]).search(
            "Meridian HLDGS", designated_only=True, threshold=75
        )
        self.assertEqual(results[0].entity_id, "E1")
        self.assertEqual(results[0].matched_name, "Meridian HLDGS")


if __name__ == "__main__":
    unittest.main()
