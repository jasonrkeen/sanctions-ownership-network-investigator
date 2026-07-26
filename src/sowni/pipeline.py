from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .cases import create_run_id
from .database import InvestigatorDatabase
from .graph import build_graph_payload, export_graph_json, export_neo4j_csv
from .gleif import GLEIF_SOURCE_URL
from .matching import EntityMatcher
from .models import Address, Alias, Entity, Relationship
from .ownership import derive_ownership_status, find_ownership_path
from .report import write_markdown, write_pdf


OFAC_SOURCE_URL = (
    "https://ofac.treasury.gov/specially-designated-nationals-and-blocked-"
    "persons-list-sdn-human-readable-lists"
)


def _find_target(
    query: str, entities: list[Entity], aliases: list[Alias]
) -> tuple[Entity | None, list[dict]]:
    matcher = EntityMatcher(entities, aliases)
    candidates = matcher.search(query, designated_only=False, threshold=70, limit=10)
    target = None
    if candidates:
        target = next(
            (entity for entity in entities if entity.entity_id == candidates[0].entity_id),
            None,
        )
    return target, [candidate.to_dict() for candidate in candidates]


def run_investigation(
    *,
    query: str,
    entities: list[Entity],
    aliases: list[Alias],
    addresses: list[Address],
    relationships: list[Relationship],
    output_dir: Path,
    database_path: Path,
    mode: str,
    match_threshold: float = 75.0,
    enrichment_summary: dict | None = None,
    run_id: str = "",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or create_run_id()
    generated_at = datetime.now(UTC).isoformat()
    target, resolution_candidates = _find_target(query, entities, aliases)

    matcher = EntityMatcher(entities, aliases)
    matches = matcher.search(
        query,
        designated_only=True,
        threshold=match_threshold,
        limit=20,
    )
    ownership_findings = derive_ownership_status(entities, relationships)
    target_finding = ownership_findings.get(target.entity_id) if target else None
    ownership_path = (
        find_ownership_path(target.entity_id, ownership_findings) if target else []
    )

    direct_match = next((match for match in matches if match.score >= 98), None)
    if direct_match:
        classification = "direct_designation"
        executive_finding = (
            "The query produced an exact or legal-suffix-normalized match to a "
            "directly designated record in the loaded data. The identity and current "
            "legal effect require analyst validation."
        )
    elif target_finding and target_finding.status == "ownership_derived_candidate":
        classification = "ownership_derived_candidate"
        executive_finding = (
            "The target did not produce a confirmed direct name match, but the loaded "
            "relationship graph indicates an ownership path that meets the configured "
            "50% aggregation threshold. Treat this as a compliance-review candidate, "
            "not a final legal determination."
        )
    else:
        classification = "no_material_indicator"
        executive_finding = (
            "No direct designation or ownership-derived designation candidate was "
            "identified in the loaded data. This does not establish that the subject "
            "is clear; coverage and ownership completeness remain material limitations."
        )

    indicators: list[dict] = []
    if target:
        target_addresses = {
            address.display
            for address in addresses
            if address.entity_id == target.entity_id and address.display
        }
        shared_entities = {
            address.entity_id
            for address in addresses
            if address.entity_id != target.entity_id
            and address.display in target_addresses
            and address.display
        }
        if shared_entities:
            names = sorted(
                entity.name for entity in entities if entity.entity_id in shared_entities
            )
            indicators.append(
                {
                    "title": "Shared address",
                    "detail": (
                        "The target shares a loaded address with: "
                        + ", ".join(names)
                        + ". This is an investigative lead only."
                    ),
                }
            )
    if ownership_path:
        entity_names = {entity.entity_id: entity.name for entity in entities}
        indicators.append(
            {
                "title": "Ownership path",
                "detail": " → ".join(
                    entity_names.get(entity_id, entity_id)
                    for entity_id in ownership_path
                ),
            }
        )
    if target:
        entity_names = {entity.entity_id: entity.name for entity in entities}
        parent_links = [
            relationship
            for relationship in relationships
            if relationship.target_id == target.entity_id
            and "ACCOUNTING_CONSOLIDATING_PARENT_OF"
            in relationship.relationship_type.upper()
        ]
        for relationship in parent_links:
            relationship_label = (
                "Direct accounting parent"
                if relationship.relationship_type.startswith("DIRECT_")
                else "Ultimate accounting parent"
            )
            indicators.append(
                {
                    "title": relationship_label,
                    "detail": (
                        f"GLEIF identifies "
                        f"{entity_names.get(relationship.source_id, relationship.source_id)} "
                        f"as an accounting consolidating parent. This link does not "
                        f"establish a percentage ownership interest and was not used "
                        f"in 50% ownership propagation."
                    ),
                }
            )

    recommended_actions = [
        "Validate the subject using authoritative identifiers, jurisdiction, and address data.",
        "Review every ownership percentage, effective date, and source document in the identified path.",
        "Separate ownership findings from control-related concerns and program-specific restrictions.",
        "Check the current official sanctions lists, licenses, and recent actions before making a decision.",
        "Record analyst confirmation or rejection for each proposed entity match.",
    ]
    if classification == "no_material_indicator":
        recommended_actions.insert(
            0,
            "Obtain additional ownership and corporate-registry data before treating the result as cleared.",
        )
    if enrichment_summary:
        recommended_actions.insert(
            1,
            "Corroborate GLEIF accounting-parent links with current ownership "
            "percentages and source filings.",
        )

    sources = [
        {
            "name": "OFAC SDN List",
            "url": OFAC_SOURCE_URL,
            "retrieved_at": generated_at if mode == "live" else "Represented by fictional sample",
        }
    ]
    if enrichment_summary:
        sources.append(
            {
                "name": "GLEIF Global LEI Index",
                "url": GLEIF_SOURCE_URL,
                "retrieved_at": enrichment_summary.get("retrieved_at", generated_at),
            }
        )

    result = {
        "run_id": run_id,
        "software_version": __version__,
        "generated_at": generated_at,
        "mode": mode,
        "query": query,
        "classification": classification,
        "data_confidence": "Demonstration" if mode == "sample" else "Source-dependent",
        "executive_finding": executive_finding,
        "target_entity": target.to_dict() if target else None,
        "resolution_candidates": resolution_candidates,
        "matches": [match.to_dict() for match in matches],
        "ownership_finding": target_finding.to_dict() if target_finding else None,
        "ownership_path": ownership_path,
        "indicators": indicators,
        "identity_enrichment": enrichment_summary,
        "recommended_actions": recommended_actions,
        "sources": sources,
        "methodology": {
            "match_threshold": match_threshold,
            "ownership_threshold_pct": 50.0,
            "graph_depth": 3,
            "gleif_parent_links_used_for_ownership_propagation": False,
        },
    }

    database = InvestigatorDatabase(database_path)
    try:
        database.upsert_entities(entities)
        database.upsert_aliases(aliases)
        database.upsert_addresses(addresses)
        database.upsert_relationships(relationships)
        database.save_matches(run_id, matches)
    finally:
        database.close()

    graph_payload = build_graph_payload(
        entities,
        addresses,
        relationships,
        center_id=target.entity_id if target else None,
        depth=3,
    )
    export_graph_json(graph_payload, output_dir / "investigation_graph.json")
    export_neo4j_csv(graph_payload, output_dir / "neo4j")
    write_markdown(result, output_dir / "investigation_brief.md")
    write_pdf(result, output_dir / "investigation_brief.pdf")
    (output_dir / "investigation_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return result
