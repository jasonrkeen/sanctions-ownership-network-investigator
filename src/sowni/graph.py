from __future__ import annotations

import csv
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Iterable

from .models import Address, Entity, Relationship


def build_graph_payload(
    entities: Iterable[Entity],
    addresses: Iterable[Address],
    relationships: Iterable[Relationship],
    *,
    center_id: str | None = None,
    depth: int = 2,
) -> dict:
    entity_map = {entity.entity_id: entity for entity in entities}
    relationship_list = list(relationships)
    allowed_ids = set(entity_map)

    if center_id and center_id in entity_map:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for rel in relationship_list:
            adjacency[rel.source_id].add(rel.target_id)
            adjacency[rel.target_id].add(rel.source_id)
        allowed_ids = {center_id}
        queue = deque([(center_id, 0)])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for neighbor in adjacency[current]:
                if neighbor not in allowed_ids:
                    allowed_ids.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

    nodes = [
        {
            "id": entity.entity_id,
            "label": entity.name,
            "node_type": entity.entity_type,
            "designated": entity.designated,
            "programs": entity.programs,
            "source": entity.source,
        }
        for entity in entity_map.values()
        if entity.entity_id in allowed_ids
    ]
    edges = [
        {
            "id": rel.relationship_id,
            "source": rel.source_id,
            "target": rel.target_id,
            "type": rel.relationship_type,
            "ownership_pct": rel.ownership_pct,
            "confidence": rel.confidence,
            "evidence": rel.evidence,
            "data_source": rel.source,
        }
        for rel in relationship_list
        if rel.source_id in allowed_ids and rel.target_id in allowed_ids
    ]

    for address in addresses:
        if address.entity_id not in allowed_ids:
            continue
        nodes.append(
            {
                "id": address.address_id,
                "label": address.display,
                "node_type": "Address",
                "designated": False,
                "programs": [],
                "source": address.source,
            }
        )
        edges.append(
            {
                "id": f"registered:{address.entity_id}:{address.address_id}",
                "source": address.entity_id,
                "target": address.address_id,
                "type": "REGISTERED_AT",
                "ownership_pct": None,
                "confidence": 1.0,
                "evidence": address.remarks,
                "data_source": address.source,
            }
        )
    return {"nodes": nodes, "edges": edges}


def export_graph_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_neo4j_csv(payload: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "nodes.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "id:ID",
            "label",
            "node_type",
            "designated:boolean",
            "programs:string[]",
            "source",
            ":LABEL",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for node in payload["nodes"]:
            writer.writerow(
                {
                    "id:ID": node["id"],
                    "label": node["label"],
                    "node_type": node["node_type"],
                    "designated:boolean": str(node["designated"]).lower(),
                    "programs:string[]": ";".join(node["programs"]),
                    "source": node["source"],
                    ":LABEL": "Address" if node["node_type"] == "Address" else "Entity",
                }
            )

    with (directory / "relationships.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        fields = [
            ":START_ID",
            ":END_ID",
            ":TYPE",
            "relationship_id",
            "ownership_pct:float",
            "confidence:float",
            "source",
            "evidence",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for edge in payload["edges"]:
            writer.writerow(
                {
                    ":START_ID": edge["source"],
                    ":END_ID": edge["target"],
                    ":TYPE": edge["type"],
                    "relationship_id": edge["id"],
                    "ownership_pct:float": edge["ownership_pct"] or "",
                    "confidence:float": edge["confidence"],
                    "source": edge["data_source"],
                    "evidence": edge["evidence"],
                }
            )
