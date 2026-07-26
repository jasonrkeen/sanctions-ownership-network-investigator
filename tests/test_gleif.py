from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.gleif import GleifClient, GleifError


CHILD_LEI = "11111111111111111111"
PARENT_LEI = "22222222222222222222"
ULTIMATE_LEI = "33333333333333333333"


def lei_resource(lei: str, name: str, country: str = "US") -> dict:
    return {
        "type": "lei-records",
        "id": lei,
        "attributes": {
            "lei": lei,
            "entity": {
                "legalName": {"name": name, "language": "en"},
                "otherNames": [
                    {"name": f"{name} Former", "type": "PREVIOUS_LEGAL_NAME"}
                ],
                "transliteratedOtherNames": [],
                "legalAddress": {
                    "addressLines": ["100 Test Avenue"],
                    "city": "Chicago",
                    "region": "US-IL",
                    "country": country,
                    "postalCode": "60601",
                },
                "headquartersAddress": {
                    "addressLines": ["200 Headquarters Street"],
                    "city": "Chicago",
                    "region": "US-IL",
                    "country": country,
                    "postalCode": "60602",
                },
                "registeredAs": "TEST-123",
                "jurisdiction": "US-IL",
                "legalForm": {"id": "H1UM"},
                "status": "ACTIVE",
            },
            "registration": {
                "status": "ISSUED",
                "corroborationLevel": "FULLY_CORROBORATED",
            },
        },
    }


def relationship_resource(child: str, parent: str, relationship_type: str) -> dict:
    return {
        "type": "relationship-records",
        "id": f"{child}-{parent}",
        "attributes": {
            "relationship": {
                "startNode": {"id": child, "type": "LEI"},
                "endNode": {"id": parent, "type": "LEI"},
                "relationshipType": relationship_type,
                "periods": [
                    {
                        "startDate": "2024-01-01T00:00:00Z",
                        "endDate": None,
                        "type": "ACCOUNTING_PERIOD",
                    }
                ],
            },
            "registration": {"status": "PUBLISHED"},
        },
    }


class GleifTests(unittest.TestCase):
    def setUp(self):
        self.routes = {
            f"lei-records/{CHILD_LEI}": {"data": lei_resource(CHILD_LEI, "Test Child LLC")},
            f"lei-records/{PARENT_LEI}": {
                "data": lei_resource(PARENT_LEI, "Test Direct Parent Inc.")
            },
            f"lei-records/{ULTIMATE_LEI}": {
                "data": lei_resource(ULTIMATE_LEI, "Test Ultimate Parent PLC", "GB")
            },
            f"lei-records/{CHILD_LEI}/direct-parent-relationship": {
                "data": relationship_resource(
                    CHILD_LEI,
                    PARENT_LEI,
                    "IS_DIRECTLY_CONSOLIDATED_BY",
                )
            },
            f"lei-records/{CHILD_LEI}/ultimate-parent-relationship": {
                "data": relationship_resource(
                    CHILD_LEI,
                    ULTIMATE_LEI,
                    "IS_ULTIMATELY_CONSOLIDATED_BY",
                )
            },
        }

    def transport(self, url: str) -> dict:
        path = url.split("/api/v1/", 1)[1].split("?", 1)[0]
        if path == "lei-records":
            return {
                "data": [
                    lei_resource(CHILD_LEI, "Test Child LLC"),
                    lei_resource(ULTIMATE_LEI, "Test Child International", "GB"),
                ]
            }
        return self.routes[path]

    def test_search_extracts_identity_fields_and_filters_country(self):
        client = GleifClient(transport=self.transport)
        candidates = client.search("Test Child", country="US")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].lei, CHILD_LEI)
        self.assertEqual(candidates[0].registration_status, "ISSUED")
        self.assertEqual(candidates[0].jurisdiction, "US-IL")
        self.assertEqual(candidates[0].match_score, 98.0)
        self.assertEqual(
            candidates[0].ranking_basis,
            "Legal-suffix-normalized name",
        )

    def test_search_reranks_spacing_variants_and_returns_requested_limit(self):
        chase_lei = "44444444444444444444"
        securities_lei = "55555555555555555555"
        fund_lei = "66666666666666666666"

        def transport(url: str) -> dict:
            path = url.split("/api/v1/", 1)[1].split("?", 1)[0]
            self.assertEqual(path, "lei-records")
            return {
                "data": [
                    lei_resource(fund_lei, "BEST JP MORGAN"),
                    lei_resource(securities_lei, "JP MORGAN SECURITIES PLC"),
                    lei_resource(chase_lei, "JPMORGAN CHASE & CO."),
                ]
            }

        candidates = GleifClient(transport=transport).search(
            "JP Morgan",
            country="US",
            limit=2,
        )
        self.assertEqual(
            [candidate.lei for candidate in candidates],
            [chase_lei, securities_lei],
        )
        self.assertGreater(
            candidates[0].match_score,
            candidates[1].match_score,
        )
        self.assertEqual(candidates[0].ranking_basis, "Compact-name prefix match")

    def test_search_rejects_invalid_country_code(self):
        client = GleifClient(transport=self.transport)
        with self.assertRaisesRegex(GleifError, "two-letter ISO code"):
            client.search("Test Child", country="USA")

    def test_enrichment_builds_identity_and_parent_graph(self):
        result = GleifClient(transport=self.transport).enrich(lei=CHILD_LEI)
        self.assertEqual(result.selected_name, "Test Child LLC")
        self.assertEqual(len(result.entities), 3)
        self.assertEqual(len(result.relationships), 2)
        direct = next(
            item
            for item in result.relationships
            if item.relationship_type.startswith("DIRECT_")
        )
        self.assertEqual(direct.source_id, f"gleif:{PARENT_LEI}")
        self.assertEqual(direct.target_id, f"gleif:{CHILD_LEI}")
        self.assertIsNone(direct.ownership_pct)
        self.assertIn("does not establish percentage ownership", direct.evidence)
        self.assertEqual(result.summary()["relationship_count"], 2)

    def test_missing_parent_links_are_reported_without_failure(self):
        routes = {
            f"lei-records/{CHILD_LEI}": {
                "data": lei_resource(CHILD_LEI, "Standalone Test LLC")
            }
        }

        def transport(url: str) -> dict:
            path = url.split("/api/v1/", 1)[1].split("?", 1)[0]
            return routes[path]

        result = GleifClient(transport=transport).enrich(lei=CHILD_LEI)
        self.assertEqual(result.relationships, [])
        self.assertEqual(len(result.warnings), 2)


if __name__ == "__main__":
    unittest.main()
