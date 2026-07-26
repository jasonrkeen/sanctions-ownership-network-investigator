from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import (
    Address,
    Alias,
    AnalystReview,
    CaseWorkflowEvent,
    Entity,
    MatchResult,
    Relationship,
)


REVIEW_DISPOSITIONS = {
    "needs_more_information",
    "identity_confirmed",
    "identity_rejected",
    "escalated_for_compliance_review",
    "closed_no_material_indicator",
}
CASE_WORKFLOW_STATUSES = {
    "open",
    "in_review",
    "pending_information",
    "escalated",
    "closed",
}
CASE_PRIORITIES = {
    "low",
    "normal",
    "high",
    "critical",
}


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entity (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source TEXT NOT NULL,
    designated INTEGER NOT NULL DEFAULT 0,
    programs_json TEXT NOT NULL DEFAULT '[]',
    country TEXT NOT NULL DEFAULT '',
    identifiers_json TEXT NOT NULL DEFAULT '{}',
    remarks TEXT NOT NULL DEFAULT '',
    retrieved_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS alias (
    alias_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    name TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    source TEXT NOT NULL,
    weak INTEGER NOT NULL DEFAULT 0,
    remarks TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS address (
    address_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    address TEXT NOT NULL DEFAULT '',
    city_state_postal TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    remarks TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS relationship (
    relationship_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES entity(entity_id),
    target_id TEXT NOT NULL REFERENCES entity(entity_id),
    relationship_type TEXT NOT NULL,
    source TEXT NOT NULL,
    ownership_pct REAL,
    confidence REAL NOT NULL DEFAULT 1,
    valid_from TEXT NOT NULL DEFAULT '',
    valid_to TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    analyst_status TEXT NOT NULL DEFAULT 'unreviewed'
);

CREATE TABLE IF NOT EXISTS screening_result (
    screening_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    query TEXT NOT NULL,
    entity_id TEXT NOT NULL REFERENCES entity(entity_id),
    matched_name TEXT NOT NULL,
    match_type TEXT NOT NULL,
    score REAL NOT NULL,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    review_status TEXT NOT NULL DEFAULT 'unreviewed'
);

CREATE TABLE IF NOT EXISTS analyst_review (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    target_name TEXT NOT NULL DEFAULT '',
    system_classification TEXT NOT NULL,
    system_version TEXT NOT NULL DEFAULT '',
    disposition TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_workflow_event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assignee TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    actor TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_name ON entity(name);
CREATE INDEX IF NOT EXISTS idx_alias_name ON alias(name);
CREATE INDEX IF NOT EXISTS idx_relationship_source ON relationship(source_id);
CREATE INDEX IF NOT EXISTS idx_relationship_target ON relationship(target_id);
CREATE INDEX IF NOT EXISTS idx_analyst_review_run ON analyst_review(run_id);
CREATE INDEX IF NOT EXISTS idx_analyst_review_created ON analyst_review(created_at);
CREATE INDEX IF NOT EXISTS idx_case_workflow_run ON case_workflow_event(run_id);
CREATE INDEX IF NOT EXISTS idx_case_workflow_created ON case_workflow_event(created_at);
"""


class InvestigatorDatabase:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def upsert_entities(self, entities: Iterable[Entity]) -> None:
        self.connection.executemany(
            """
            INSERT INTO entity VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                name=excluded.name,
                entity_type=excluded.entity_type,
                source=excluded.source,
                designated=excluded.designated,
                programs_json=excluded.programs_json,
                country=excluded.country,
                identifiers_json=excluded.identifiers_json,
                remarks=excluded.remarks,
                retrieved_at=excluded.retrieved_at
            """,
            [
                (
                    entity.entity_id,
                    entity.name,
                    entity.entity_type,
                    entity.source,
                    int(entity.designated),
                    json.dumps(entity.programs),
                    entity.country,
                    json.dumps(entity.identifiers),
                    entity.remarks,
                    entity.retrieved_at,
                )
                for entity in entities
            ],
        )
        self.connection.commit()

    def upsert_aliases(self, aliases: Iterable[Alias]) -> None:
        self.connection.executemany(
            """
            INSERT INTO alias VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias_id) DO UPDATE SET
                entity_id=excluded.entity_id,
                name=excluded.name,
                alias_type=excluded.alias_type,
                source=excluded.source,
                weak=excluded.weak,
                remarks=excluded.remarks
            """,
            [
                (
                    alias.alias_id,
                    alias.entity_id,
                    alias.name,
                    alias.alias_type,
                    alias.source,
                    int(alias.weak),
                    alias.remarks,
                )
                for alias in aliases
            ],
        )
        self.connection.commit()

    def upsert_addresses(self, addresses: Iterable[Address]) -> None:
        self.connection.executemany(
            """
            INSERT INTO address VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address_id) DO UPDATE SET
                entity_id=excluded.entity_id,
                address=excluded.address,
                city_state_postal=excluded.city_state_postal,
                country=excluded.country,
                source=excluded.source,
                remarks=excluded.remarks
            """,
            [
                (
                    address.address_id,
                    address.entity_id,
                    address.address,
                    address.city_state_postal,
                    address.country,
                    address.source,
                    address.remarks,
                )
                for address in addresses
            ],
        )
        self.connection.commit()

    def upsert_relationships(self, relationships: Iterable[Relationship]) -> None:
        self.connection.executemany(
            """
            INSERT INTO relationship VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(relationship_id) DO UPDATE SET
                source_id=excluded.source_id,
                target_id=excluded.target_id,
                relationship_type=excluded.relationship_type,
                source=excluded.source,
                ownership_pct=excluded.ownership_pct,
                confidence=excluded.confidence,
                valid_from=excluded.valid_from,
                valid_to=excluded.valid_to,
                evidence=excluded.evidence,
                analyst_status=excluded.analyst_status
            """,
            [
                (
                    item.relationship_id,
                    item.source_id,
                    item.target_id,
                    item.relationship_type,
                    item.source,
                    item.ownership_pct,
                    item.confidence,
                    item.valid_from,
                    item.valid_to,
                    item.evidence,
                    item.analyst_status,
                )
                for item in relationships
            ],
        )
        self.connection.commit()

    def save_matches(
        self, run_id: str, matches: Iterable[MatchResult]
    ) -> None:
        self.connection.executemany(
            """
            INSERT INTO screening_result (
                run_id, query, entity_id, matched_name, match_type,
                score, reasons_json, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    match.query,
                    match.entity_id,
                    match.matched_name,
                    match.match_type,
                    match.score,
                    json.dumps(match.reasons),
                    match.review_status,
                )
                for match in matches
            ],
        )
        self.connection.commit()

    def save_analyst_review(self, review: AnalystReview) -> int:
        if review.disposition not in REVIEW_DISPOSITIONS:
            raise ValueError(f"Unsupported analyst disposition: {review.disposition}")
        if not review.reviewer.strip():
            raise ValueError("Reviewer name or initials are required.")
        if not review.notes.strip():
            raise ValueError("Analyst notes are required.")
        cursor = self.connection.execute(
            """
            INSERT INTO analyst_review (
                run_id, entity_id, target_name, system_classification,
                system_version, disposition, reviewer, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.run_id,
                review.entity_id,
                review.target_name,
                review.system_classification,
                review.system_version,
                review.disposition,
                review.reviewer.strip(),
                review.notes.strip(),
                review.created_at,
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_analyst_reviews(
        self,
        *,
        run_id: str | None = None,
        limit: int = 100,
    ) -> list[AnalystReview]:
        safe_limit = max(1, min(int(limit), 1000))
        if run_id:
            rows = self.connection.execute(
                """
                SELECT review_id, run_id, entity_id, target_name,
                       system_classification, system_version, disposition, reviewer,
                       notes, created_at
                FROM analyst_review
                WHERE run_id = ?
                ORDER BY review_id DESC
                LIMIT ?
                """,
                (run_id, safe_limit),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT review_id, run_id, entity_id, target_name,
                       system_classification, system_version, disposition, reviewer,
                       notes, created_at
                FROM analyst_review
                ORDER BY review_id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            AnalystReview(
                review_id=row[0],
                run_id=row[1],
                entity_id=row[2],
                target_name=row[3],
                system_classification=row[4],
                system_version=row[5],
                disposition=row[6],
                reviewer=row[7],
                notes=row[8],
                created_at=row[9],
            )
            for row in rows
        ]

    def save_case_workflow_event(self, event: CaseWorkflowEvent) -> int:
        if not event.run_id.strip():
            raise ValueError("Run ID is required for a case workflow event.")
        if event.status not in CASE_WORKFLOW_STATUSES:
            raise ValueError(f"Unsupported case status: {event.status}")
        if event.priority not in CASE_PRIORITIES:
            raise ValueError(f"Unsupported case priority: {event.priority}")
        if not event.actor.strip():
            raise ValueError("Workflow update actor is required.")
        if not event.notes.strip():
            raise ValueError("Workflow update notes are required.")

        normalized_tags: list[str] = []
        seen_tags: set[str] = set()
        for value in event.tags:
            tag = " ".join(str(value).split())
            if not tag:
                continue
            if len(tag) > 40:
                raise ValueError("Case tags must be 40 characters or fewer.")
            key = tag.casefold()
            if key in seen_tags:
                continue
            seen_tags.add(key)
            normalized_tags.append(tag)
        if len(normalized_tags) > 20:
            raise ValueError("A case can have no more than 20 tags.")

        cursor = self.connection.execute(
            """
            INSERT INTO case_workflow_event (
                run_id, status, priority, assignee, tags_json,
                actor, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.run_id.strip(),
                event.status,
                event.priority,
                event.assignee.strip(),
                json.dumps(normalized_tags),
                event.actor.strip(),
                event.notes.strip(),
                event.created_at,
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_case_workflow_events(
        self,
        *,
        run_id: str,
        limit: int = 100,
    ) -> list[CaseWorkflowEvent]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self.connection.execute(
            """
            SELECT event_id, run_id, status, priority, assignee,
                   tags_json, actor, notes, created_at
            FROM case_workflow_event
            WHERE run_id = ?
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (run_id, safe_limit),
        ).fetchall()
        return [
            CaseWorkflowEvent(
                event_id=row[0],
                run_id=row[1],
                status=row[2],
                priority=row[3],
                assignee=row[4],
                tags=json.loads(row[5]),
                actor=row[6],
                notes=row[7],
                created_at=row[8],
            )
            for row in rows
        ]

    def get_case_workflow_state(self, run_id: str) -> dict:
        events = self.list_case_workflow_events(run_id=run_id, limit=1)
        if not events:
            return {
                "event_id": None,
                "run_id": run_id,
                "status": "open",
                "priority": "normal",
                "assignee": "",
                "tags": [],
                "updated_by": "",
                "updated_at": "",
            }
        latest = events[0]
        return {
            "event_id": latest.event_id,
            "run_id": latest.run_id,
            "status": latest.status,
            "priority": latest.priority,
            "assignee": latest.assignee,
            "tags": latest.tags,
            "updated_by": latest.actor,
            "updated_at": latest.created_at,
        }

    def count_analyst_reviews(self, run_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM analyst_review WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return int(row[0] if row else 0)

    def count_case_workflow_events(self, run_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM case_workflow_event WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return int(row[0] if row else 0)
