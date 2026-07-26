from __future__ import annotations

import csv
import io
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path


CASE_INDEX_SCHEMA_VERSION = 1


def create_run_id() -> str:
    return f"soni-{uuid.uuid4().hex[:12]}"


def _validated_run_id(run_id: str) -> str:
    value = run_id.strip()
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or Path(value).name != value
    ):
        raise ValueError("Run ID must be one safe directory name.")
    return value


def _read_result(case_dir: Path) -> dict:
    result_path = case_dir / "investigation_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"{result_path} must contain a JSON object.")
    if not result.get("run_id") or not result.get("classification"):
        raise ValueError(f"{result_path} is missing required case fields.")
    return result


def build_case_summary(case_dir: Path, result: dict | None = None) -> dict:
    payload = result or _read_result(case_dir)
    target = payload.get("target_entity") or {}
    return {
        "run_id": str(payload["run_id"]),
        "generated_at": str(payload.get("generated_at") or ""),
        "query": str(payload.get("query") or ""),
        "target_name": str(target.get("name") or payload.get("query") or "Unresolved"),
        "classification": str(payload["classification"]),
        "mode": str(payload.get("mode") or ""),
        "software_version": str(payload.get("software_version") or ""),
        "case_directory": case_dir.name,
    }


def discover_cases(outputs_root: Path) -> list[dict]:
    root = outputs_root.resolve()
    cases_root = root / "cases"
    discovered: dict[str, dict] = {}
    if cases_root.exists():
        for case_dir in cases_root.iterdir():
            if not case_dir.is_dir():
                continue
            if not (case_dir / "investigation_graph.json").is_file():
                continue
            try:
                summary = build_case_summary(case_dir)
            except (FileNotFoundError, ValueError, json.JSONDecodeError):
                continue
            summary["path"] = str(case_dir)
            summary["storage"] = "archived"
            discovered[summary["run_id"]] = summary

    latest_dir = root / "latest"
    try:
        latest_summary = (
            build_case_summary(latest_dir)
            if (latest_dir / "investigation_graph.json").is_file()
            else None
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        latest_summary = None
    if latest_summary and latest_summary["run_id"] not in discovered:
        latest_summary["path"] = str(latest_dir)
        latest_summary["storage"] = "legacy_latest"
        discovered[latest_summary["run_id"]] = latest_summary

    return sorted(
        discovered.values(),
        key=lambda item: (item.get("generated_at", ""), item["run_id"]),
        reverse=True,
    )


def filter_case_queue(
    cases: list[dict],
    *,
    search: str = "",
    status: str = "",
    priority: str = "",
) -> list[dict]:
    normalized_search = search.strip().casefold()
    filtered: list[dict] = []
    for case in cases:
        workflow = case.get("workflow") or {}
        searchable = " ".join(
            [
                str(case.get("target_name") or ""),
                str(case.get("query") or ""),
                str(case.get("run_id") or ""),
                str(case.get("classification") or ""),
                str(workflow.get("assignee") or ""),
                " ".join(workflow.get("tags") or []),
            ]
        ).casefold()
        if normalized_search and normalized_search not in searchable:
            continue
        if status and workflow.get("status") != status:
            continue
        if priority and workflow.get("priority") != priority:
            continue
        filtered.append(case)
    return filtered


def build_queue_rows(cases: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for case in cases:
        workflow = case.get("workflow") or {}
        rows.append(
            {
                "run_id": str(case.get("run_id") or ""),
                "generated_at": str(case.get("generated_at") or ""),
                "target_name": str(case.get("target_name") or ""),
                "query": str(case.get("query") or ""),
                "classification": str(case.get("classification") or ""),
                "mode": str(case.get("mode") or ""),
                "software_version": str(case.get("software_version") or ""),
                "status": str(workflow.get("status") or "open"),
                "priority": str(workflow.get("priority") or "normal"),
                "assignee": str(workflow.get("assignee") or ""),
                "tags": ", ".join(workflow.get("tags") or []),
                "workflow_updated_at": str(workflow.get("updated_at") or ""),
                "workflow_updated_by": str(workflow.get("updated_by") or ""),
                "workflow_event_count": int(
                    case.get("workflow_event_count") or 0
                ),
                "analyst_review_count": int(
                    case.get("analyst_review_count") or 0
                ),
                "case_directory": str(case.get("case_directory") or ""),
            }
        )
    return rows


def queue_rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def refresh_case_index(outputs_root: Path) -> Path:
    root = outputs_root.resolve()
    cases_root = root / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)
    summaries = [
        {
            key: value
            for key, value in item.items()
            if key not in {"path", "storage"}
        }
        for item in discover_cases(root)
        if item.get("storage") == "archived"
    ]
    payload = {
        "schema_version": CASE_INDEX_SCHEMA_VERSION,
        "updated_at": datetime.now(UTC).isoformat(),
        "case_count": len(summaries),
        "cases": summaries,
    }
    destination = cases_root / "index.json"
    temporary = cases_root / f".index-{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def archive_latest_case(outputs_root: Path) -> Path | None:
    root = outputs_root.resolve()
    latest_dir = root / "latest"
    try:
        result = _read_result(latest_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None

    run_id = _validated_run_id(str(result["run_id"]))
    destination = root / "cases" / run_id
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(latest_dir, destination)
    refresh_case_index(root)
    return destination


def register_case(outputs_root: Path, case_dir: Path, result: dict) -> Path:
    run_id = _validated_run_id(str(result["run_id"]))
    if case_dir.resolve().name != run_id:
        raise ValueError("Case directory name must match the investigation run ID.")
    expected_parent = outputs_root.resolve() / "cases"
    if case_dir.resolve().parent != expected_parent:
        raise ValueError("Case directory must be stored under outputs/cases.")
    if not (case_dir / "investigation_graph.json").is_file():
        raise FileNotFoundError("Case is missing investigation_graph.json.")
    return refresh_case_index(outputs_root)


def publish_latest_snapshot(outputs_root: Path, case_dir: Path) -> Path:
    root = outputs_root.resolve()
    source = case_dir.resolve()
    required = ("investigation_result.json", "investigation_graph.json")
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Cannot publish an incomplete case. Missing: " + ", ".join(missing)
        )

    latest_dir = root / "latest"
    temporary = root / f".latest-{uuid.uuid4().hex}.tmp"
    root.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, temporary)
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        temporary.replace(latest_dir)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return latest_dir


__all__ = [
    "CASE_INDEX_SCHEMA_VERSION",
    "archive_latest_case",
    "build_case_summary",
    "build_queue_rows",
    "create_run_id",
    "discover_cases",
    "filter_case_queue",
    "publish_latest_snapshot",
    "queue_rows_to_csv",
    "refresh_case_index",
    "register_case",
]
