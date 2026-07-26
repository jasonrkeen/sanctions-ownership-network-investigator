from __future__ import annotations

from typing import Any


def _best_identity_score(result: dict) -> float | None:
    candidates = result.get("resolution_candidates") or []
    if not candidates or candidates[0].get("score") is None:
        return None
    return round(float(candidates[0]["score"]), 2)


def _target_name(result: dict) -> str:
    target = result.get("target_entity") or {}
    return str(target.get("name") or result.get("query") or "Unresolved")


def _candidate_map(result: dict, field: str) -> dict[str, dict]:
    mapped: dict[str, dict] = {}
    for candidate in result.get(field) or []:
        key = str(
            candidate.get("entity_id")
            or candidate.get("entity_name")
            or candidate.get("matched_name")
            or ""
        )
        if key:
            mapped[key] = candidate
    return mapped


def _edge_map(graph: dict) -> dict[tuple[str, str, str, str], dict]:
    mapped: dict[tuple[str, str, str, str], dict] = {}
    for edge in graph.get("edges") or []:
        key = (
            str(edge.get("source") or ""),
            str(edge.get("target") or ""),
            str(edge.get("type") or ""),
            str(edge.get("ownership_pct")),
        )
        mapped[key] = edge
    return mapped


def _named_set(items: list[dict], field: str) -> set[str]:
    return {
        str(item.get(field) or "")
        for item in items
        if str(item.get(field) or "")
    }


def summarize_case(
    result: dict,
    graph: dict,
    *,
    workflow: dict | None = None,
    review_count: int = 0,
    workflow_event_count: int = 0,
) -> dict:
    state = workflow or {}
    enrichment = result.get("identity_enrichment") or {}
    return {
        "run_id": str(result.get("run_id") or ""),
        "generated_at": str(result.get("generated_at") or ""),
        "query": str(result.get("query") or ""),
        "target_name": _target_name(result),
        "classification": str(result.get("classification") or ""),
        "mode": str(result.get("mode") or ""),
        "software_version": str(result.get("software_version") or ""),
        "identity_score": _best_identity_score(result),
        "resolution_candidate_count": len(
            result.get("resolution_candidates") or []
        ),
        "direct_candidate_count": len(result.get("matches") or []),
        "graph_node_count": len(graph.get("nodes") or []),
        "graph_edge_count": len(graph.get("edges") or []),
        "indicator_count": len(result.get("indicators") or []),
        "source_count": len(result.get("sources") or []),
        "gleif_enriched": bool(enrichment),
        "gleif_lei": str(enrichment.get("selected_lei") or ""),
        "review_count": int(review_count),
        "workflow_event_count": int(workflow_event_count),
        "workflow_status": str(state.get("status") or "open"),
        "workflow_priority": str(state.get("priority") or "normal"),
        "workflow_assignee": str(state.get("assignee") or ""),
    }


def _delta(right: int | float | None, left: int | float | None) -> float | None:
    if right is None or left is None:
        return None
    return round(float(right) - float(left), 2)


def _comparison_rows(left: dict, right: dict) -> list[dict[str, Any]]:
    fields = (
        "run_id",
        "generated_at",
        "query",
        "target_name",
        "classification",
        "mode",
        "software_version",
        "gleif_enriched",
        "gleif_lei",
        "workflow_status",
        "workflow_priority",
        "workflow_assignee",
    )
    return [
        {
            "field": field,
            "baseline": left.get(field),
            "comparison": right.get(field),
            "changed": left.get(field) != right.get(field),
        }
        for field in fields
    ]


def _changed_candidates(
    baseline: dict[str, dict],
    comparison: dict[str, dict],
) -> list[dict]:
    changed: list[dict] = []
    for key in sorted(baseline.keys() & comparison.keys()):
        left = baseline[key]
        right = comparison[key]
        if left == right:
            continue
        baseline_score = left.get("score")
        comparison_score = right.get("score")
        score_delta = (
            _delta(comparison_score, baseline_score)
            if baseline_score is not None and comparison_score is not None
            else None
        )
        changed.append(
            {
                "entity_id": key,
                "baseline_name": str(
                    left.get("entity_name") or left.get("matched_name") or ""
                ),
                "comparison_name": str(
                    right.get("entity_name") or right.get("matched_name") or ""
                ),
                "baseline_score": baseline_score,
                "comparison_score": comparison_score,
                "score_delta": score_delta,
            }
        )
    return changed


def compare_cases(
    baseline_result: dict,
    baseline_graph: dict,
    comparison_result: dict,
    comparison_graph: dict,
    *,
    baseline_workflow: dict | None = None,
    comparison_workflow: dict | None = None,
    baseline_review_count: int = 0,
    comparison_review_count: int = 0,
    baseline_workflow_event_count: int = 0,
    comparison_workflow_event_count: int = 0,
) -> dict:
    if baseline_result.get("run_id") == comparison_result.get("run_id"):
        raise ValueError("Select two different investigation runs to compare.")

    baseline = summarize_case(
        baseline_result,
        baseline_graph,
        workflow=baseline_workflow,
        review_count=baseline_review_count,
        workflow_event_count=baseline_workflow_event_count,
    )
    comparison = summarize_case(
        comparison_result,
        comparison_graph,
        workflow=comparison_workflow,
        review_count=comparison_review_count,
        workflow_event_count=comparison_workflow_event_count,
    )

    numeric_fields = (
        "identity_score",
        "resolution_candidate_count",
        "direct_candidate_count",
        "graph_node_count",
        "graph_edge_count",
        "indicator_count",
        "source_count",
        "review_count",
        "workflow_event_count",
    )
    deltas = {
        field: _delta(comparison.get(field), baseline.get(field))
        for field in numeric_fields
    }

    identity_baseline = _candidate_map(
        baseline_result, "resolution_candidates"
    )
    identity_comparison = _candidate_map(
        comparison_result, "resolution_candidates"
    )
    sanctions_baseline = _candidate_map(baseline_result, "matches")
    sanctions_comparison = _candidate_map(comparison_result, "matches")
    edge_baseline = _edge_map(baseline_graph)
    edge_comparison = _edge_map(comparison_graph)

    baseline_sources = _named_set(baseline_result.get("sources") or [], "name")
    comparison_sources = _named_set(
        comparison_result.get("sources") or [], "name"
    )
    baseline_indicators = _named_set(
        baseline_result.get("indicators") or [], "title"
    )
    comparison_indicators = _named_set(
        comparison_result.get("indicators") or [], "title"
    )

    return {
        "baseline": baseline,
        "comparison": comparison,
        "same_target": (
            baseline["target_name"].strip().casefold()
            == comparison["target_name"].strip().casefold()
        ),
        "field_comparison": _comparison_rows(baseline, comparison),
        "deltas": deltas,
        "identity_candidates": {
            "added": [
                identity_comparison[key]
                for key in sorted(identity_comparison.keys() - identity_baseline.keys())
            ],
            "removed": [
                identity_baseline[key]
                for key in sorted(identity_baseline.keys() - identity_comparison.keys())
            ],
            "changed": _changed_candidates(
                identity_baseline,
                identity_comparison,
            ),
        },
        "sanctions_candidates": {
            "added": [
                sanctions_comparison[key]
                for key in sorted(
                    sanctions_comparison.keys() - sanctions_baseline.keys()
                )
            ],
            "removed": [
                sanctions_baseline[key]
                for key in sorted(
                    sanctions_baseline.keys() - sanctions_comparison.keys()
                )
            ],
            "changed": _changed_candidates(
                sanctions_baseline,
                sanctions_comparison,
            ),
        },
        "graph_edges": {
            "added": [
                edge_comparison[key]
                for key in sorted(edge_comparison.keys() - edge_baseline.keys())
            ],
            "removed": [
                edge_baseline[key]
                for key in sorted(edge_baseline.keys() - edge_comparison.keys())
            ],
        },
        "sources": {
            "added": sorted(comparison_sources - baseline_sources),
            "removed": sorted(baseline_sources - comparison_sources),
        },
        "indicators": {
            "added": sorted(comparison_indicators - baseline_indicators),
            "removed": sorted(baseline_indicators - comparison_indicators),
        },
        "scope_note": (
            "This comparison reports differences between stored investigation "
            "artifacts. It does not establish causation, deterioration, improvement, "
            "or a change in legal status."
        ),
    }


__all__ = ["compare_cases", "summarize_case"]
