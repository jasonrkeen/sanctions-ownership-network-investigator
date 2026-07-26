from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Iterable

from .models import Entity, Relationship


@dataclass(slots=True)
class OwnershipFinding:
    entity_id: str
    status: str
    blocked_owner_ids: list[str]
    aggregate_pct: float
    iteration: int
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def derive_ownership_status(
    entities: Iterable[Entity],
    relationships: Iterable[Relationship],
    threshold_pct: float = 50.0,
) -> dict[str, OwnershipFinding]:
    entities_by_id = {entity.entity_id: entity for entity in entities}
    blocked = {entity.entity_id for entity in entities_by_id.values() if entity.designated}
    findings: dict[str, OwnershipFinding] = {
        entity_id: OwnershipFinding(
            entity_id=entity_id,
            status="direct_designation",
            blocked_owner_ids=[],
            aggregate_pct=100.0,
            iteration=0,
            explanation="Entity is directly designated in the loaded source data.",
        )
        for entity_id in blocked
    }

    ownership_by_target: dict[str, list[Relationship]] = defaultdict(list)
    for relationship in relationships:
        if (
            relationship.relationship_type.upper() == "OWNS"
            and relationship.ownership_pct is not None
        ):
            ownership_by_target[relationship.target_id].append(relationship)

    iteration = 0
    while True:
        iteration += 1
        additions: dict[str, OwnershipFinding] = {}
        for target_id, ownerships in ownership_by_target.items():
            if target_id in blocked or target_id not in entities_by_id:
                continue
            relevant = [
                relationship
                for relationship in ownerships
                if relationship.source_id in blocked
            ]
            aggregate = sum(relationship.ownership_pct or 0 for relationship in relevant)
            if aggregate >= threshold_pct:
                owner_ids = sorted({item.source_id for item in relevant})
                additions[target_id] = OwnershipFinding(
                    entity_id=target_id,
                    status="ownership_derived_candidate",
                    blocked_owner_ids=owner_ids,
                    aggregate_pct=round(aggregate, 2),
                    iteration=iteration,
                    explanation=(
                        f"Loaded relationships show {aggregate:.2f}% aggregate direct "
                        "ownership by entities already marked directly or "
                        "ownership-derived. Requires compliance validation."
                    ),
                )
        if not additions:
            break
        findings.update(additions)
        blocked.update(additions)
    return findings


def find_ownership_path(
    target_id: str,
    findings: dict[str, OwnershipFinding],
    max_depth: int = 8,
) -> list[str]:
    if target_id not in findings:
        return []
    queue = deque([(target_id, [target_id])])
    visited: set[str] = set()
    while queue:
        entity_id, path = queue.popleft()
        if entity_id in visited or len(path) > max_depth:
            continue
        visited.add(entity_id)
        finding = findings.get(entity_id)
        if finding and finding.status == "direct_designation":
            return path
        if finding:
            for owner_id in finding.blocked_owner_ids:
                queue.append((owner_id, [*path, owner_id]))
    return []


def control_exposures(
    relationships: Iterable[Relationship], blocked_ids: set[str]
) -> list[dict]:
    exposures = []
    for relationship in relationships:
        if (
            relationship.relationship_type.upper() == "CONTROLS"
            and relationship.source_id in blocked_ids
        ):
            exposures.append(
                {
                    "entity_id": relationship.target_id,
                    "controller_id": relationship.source_id,
                    "classification": "control_related_exposure",
                    "explanation": (
                        "A blocked entity is recorded as a controller. Control alone "
                        "is not an automatic OFAC 50 Percent Rule determination."
                    ),
                }
            )
    return exposures
