from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Entity:
    entity_id: str
    name: str
    entity_type: str
    source: str
    designated: bool = False
    programs: list[str] = field(default_factory=list)
    country: str = ""
    identifiers: dict[str, str] = field(default_factory=dict)
    remarks: str = ""
    retrieved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Alias:
    alias_id: str
    entity_id: str
    name: str
    alias_type: str
    source: str
    weak: bool = False
    remarks: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Address:
    address_id: str
    entity_id: str
    address: str
    city_state_postal: str
    country: str
    source: str
    remarks: str = ""

    @property
    def display(self) -> str:
        return ", ".join(
            part
            for part in (self.address, self.city_state_postal, self.country)
            if part
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Relationship:
    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    source: str
    ownership_pct: float | None = None
    confidence: float = 1.0
    valid_from: str = ""
    valid_to: str = ""
    evidence: str = ""
    analyst_status: str = "unreviewed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MatchResult:
    query: str
    entity_id: str
    entity_name: str
    matched_name: str
    match_type: str
    score: float
    designated: bool
    programs: list[str]
    country: str
    reasons: list[str]
    review_status: str = "unreviewed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalystReview:
    run_id: str
    entity_id: str
    target_name: str
    system_classification: str
    system_version: str
    disposition: str
    reviewer: str
    notes: str
    created_at: str
    review_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaseWorkflowEvent:
    run_id: str
    status: str
    priority: str
    assignee: str
    tags: list[str]
    actor: str
    notes: str
    created_at: str
    event_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
