from __future__ import annotations

import json
from pathlib import Path


def load_case(output_dir: Path) -> tuple[dict, dict]:
    result_path = output_dir / "investigation_result.json"
    graph_path = output_dir / "investigation_graph.json"
    missing = [path.name for path in (result_path, graph_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "The selected investigation case is incomplete. "
            f"Missing: {', '.join(missing)}"
        )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not isinstance(graph, dict):
        raise ValueError("Investigation artifacts must contain JSON objects.")
    if "run_id" not in result or "classification" not in result:
        raise ValueError("Investigation result is missing required case fields.")
    if not isinstance(graph.get("nodes"), list) or not isinstance(
        graph.get("edges"), list
    ):
        raise ValueError("Investigation graph is missing nodes or edges.")
    return result, graph


def load_latest_case(output_dir: Path) -> tuple[dict, dict]:
    return load_case(output_dir)


def _dot_escape(value: object) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
    )


def build_dot_graph(
    graph: dict,
    *,
    target_id: str = "",
    include_addresses: bool = False,
) -> str:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    allowed_ids = {
        str(node.get("id"))
        for node in nodes
        if include_addresses or node.get("node_type") != "Address"
    }
    dot = [
        "digraph G {",
        "rankdir=LR;",
        'graph [bgcolor="transparent"];',
        'node [style="rounded,filled", fontname="Arial"];',
        'edge [fontname="Arial", fontsize=9];',
    ]
    for node in nodes:
        node_id = str(node.get("id"))
        if node_id not in allowed_ids:
            continue
        node_type = str(node.get("node_type") or "Entity")
        shape = "ellipse" if node_type == "Address" else "box"
        fill = "#F4A6A6" if node.get("designated") else "#DCE8F5"
        if node_id == target_id:
            fill = "#F3D58A"
        dot.append(
            f'"{_dot_escape(node_id)}" '
            f'[label="{_dot_escape(node.get("label"))}", '
            f'shape="{shape}", fillcolor="{fill}"];'
        )
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        if source not in allowed_ids or target not in allowed_ids:
            continue
        label = str(edge.get("type") or "RELATED_TO")
        if edge.get("ownership_pct") is not None:
            label += f" {edge['ownership_pct']:g}%"
        dot.append(
            f'"{_dot_escape(source)}" -> "{_dot_escape(target)}" '
            f'[label="{_dot_escape(label)}"];'
        )
    dot.append("}")
    return "\n".join(dot)


__all__ = ["build_dot_graph", "load_case", "load_latest_case"]
