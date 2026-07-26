from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Address, Alias, Entity, Relationship


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_sample_data(
    directory: Path,
) -> tuple[list[Entity], list[Alias], list[Address], list[Relationship]]:
    with (directory / "entities.csv").open(encoding="utf-8-sig", newline="") as handle:
        entities = [
            Entity(
                entity_id=row["entity_id"],
                name=row["name"],
                entity_type=row["entity_type"],
                source=row["source"],
                designated=_bool(row["designated"]),
                programs=json.loads(row["programs"] or "[]"),
                country=row["country"],
                identifiers=json.loads(row["identifiers"] or "{}"),
                remarks=row["remarks"],
                retrieved_at=row["retrieved_at"],
            )
            for row in csv.DictReader(handle)
        ]

    with (directory / "aliases.csv").open(encoding="utf-8-sig", newline="") as handle:
        aliases = [
            Alias(
                alias_id=row["alias_id"],
                entity_id=row["entity_id"],
                name=row["name"],
                alias_type=row["alias_type"],
                source=row["source"],
                weak=_bool(row["weak"]),
                remarks=row["remarks"],
            )
            for row in csv.DictReader(handle)
        ]

    with (directory / "addresses.csv").open(encoding="utf-8-sig", newline="") as handle:
        addresses = [
            Address(
                address_id=row["address_id"],
                entity_id=row["entity_id"],
                address=row["address"],
                city_state_postal=row["city_state_postal"],
                country=row["country"],
                source=row["source"],
                remarks=row["remarks"],
            )
            for row in csv.DictReader(handle)
        ]

    with (directory / "relationships.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        relationships = []
        for row in csv.DictReader(handle):
            percentage = row["ownership_pct"].strip()
            relationships.append(
                Relationship(
                    relationship_id=row["relationship_id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    relationship_type=row["relationship_type"],
                    source=row["source"],
                    ownership_pct=float(percentage) if percentage else None,
                    confidence=float(row["confidence"] or 1),
                    valid_from=row["valid_from"],
                    valid_to=row["valid_to"],
                    evidence=row["evidence"],
                    analyst_status=row["analyst_status"] or "unreviewed",
                )
            )
    return entities, aliases, addresses, relationships
