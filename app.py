from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "Streamlit is not installed. Run: pip install -e '.[dashboard]'"
    ) from exc

from sowni import __version__
from sowni.cases import (
    build_queue_rows,
    discover_cases,
    filter_case_queue,
    queue_rows_to_csv,
)
from sowni.comparison import compare_cases
from sowni.dashboard import build_dot_graph, load_case
from sowni.database import InvestigatorDatabase
from sowni.gleif import GleifClient, GleifError
from sowni.matching import EntityMatcher
from sowni.models import AnalystReview, CaseWorkflowEvent
from sowni.ownership import derive_ownership_status, find_ownership_path
from sowni.report import CLASSIFICATION_LABELS
from sowni.sample_data import load_sample_data


st.set_page_config(
    page_title="Sanctions Ownership Network Investigator",
    page_icon="🔎",
    layout="wide",
)


@st.cache_data
def load_demo():
    return load_sample_data(PROJECT_ROOT / "data" / "sample")


def load_case_registry() -> list[dict]:
    cases = discover_cases(PROJECT_ROOT / "outputs")
    for case in cases:
        database = InvestigatorDatabase(
            Path(case["path"]) / "investigator.sqlite"
        )
        try:
            run_id = str(case["run_id"])
            case["workflow"] = database.get_case_workflow_state(run_id)
            case["analyst_review_count"] = database.count_analyst_reviews(run_id)
            case["workflow_event_count"] = database.count_case_workflow_events(
                run_id
            )
        finally:
            database.close()
    return cases


REVIEW_LABELS = {
    "Needs more information": "needs_more_information",
    "Identity confirmed": "identity_confirmed",
    "Identity rejected": "identity_rejected",
    "Escalated for compliance review": "escalated_for_compliance_review",
    "Closed - no material indicator": "closed_no_material_indicator",
}
WORKFLOW_STATUS_LABELS = {
    "Open": "open",
    "In review": "in_review",
    "Pending information": "pending_information",
    "Escalated": "escalated",
    "Closed": "closed",
}
WORKFLOW_PRIORITY_LABELS = {
    "Low": "low",
    "Normal": "normal",
    "High": "high",
    "Critical": "critical",
}

st.title("Sanctions Ownership Network Investigator")
st.caption(
    "Entity screening, relationship exploration, and ownership-derived risk review"
)
st.warning(
    "Results support analyst review and are not legal advice or final compliance "
    "determinations. A recorded disposition does not alter the system classification.",
    icon="⚠️",
)

with st.sidebar:
    st.header("Workspace")
    workspace = st.radio(
        "Data workflow",
        [
            "Case investigations",
            "Case comparison",
            "Fictional demonstration",
            "GLEIF legal-entity lookup",
        ],
    )
    st.caption(f"Application version {__version__}")

if workspace == "Case investigations":
    cases = load_case_registry()
    if not cases:
        st.error("No investigation cases are available. Run main.py first.")
        st.code(
            'python main.py --mode live --gleif-enrich --country US '
            '--query "ENTITY NAME"',
            language="powershell",
        )
        st.stop()

    def format_case_option(run_id: str) -> str:
        selected = next(
            item for item in filtered_cases if item["run_id"] == run_id
        )
        generated = str(selected.get("generated_at") or "")[:16].replace("T", " ")
        classification = str(selected.get("classification") or "").replace("_", " ")
        workflow = selected["workflow"]
        return (
            f"{selected['target_name']} — "
            f"{str(workflow['priority']).title()} / "
            f"{str(workflow['status']).replace('_', ' ').title()} — "
            f"{classification} — "
            f"{generated or 'date unavailable'}"
        )

    with st.sidebar:
        case_search = st.text_input(
            "Search cases",
            help="Search target, query, run ID, classification, assignee, or tags.",
        )
        case_filter_columns = st.columns(2)
        with case_filter_columns[0]:
            status_filter_label = st.selectbox(
                "Status filter",
                options=["All", *WORKFLOW_STATUS_LABELS],
            )
        with case_filter_columns[1]:
            priority_filter_label = st.selectbox(
                "Priority filter",
                options=["All", *WORKFLOW_PRIORITY_LABELS],
            )

        status_filter = (
            ""
            if status_filter_label == "All"
            else WORKFLOW_STATUS_LABELS[status_filter_label]
        )
        priority_filter = (
            ""
            if priority_filter_label == "All"
            else WORKFLOW_PRIORITY_LABELS[priority_filter_label]
        )
        filtered_cases = filter_case_queue(
            cases,
            search=case_search,
            status=status_filter,
            priority=priority_filter,
        )

        if not filtered_cases:
            st.warning("No cases match the selected queue filters.")
            st.stop()

        selected_run_id = st.selectbox(
            "Investigation case",
            options=[item["run_id"] for item in filtered_cases],
            format_func=format_case_option,
        )
        st.caption(
            f"{len(filtered_cases)} of {len(cases)} "
            f"case{'s' if len(cases) != 1 else ''} shown"
        )
        queue_rows = build_queue_rows(cases)
        with st.expander("Queue exports"):
            st.download_button(
                "Download queue CSV",
                data=queue_rows_to_csv(queue_rows),
                file_name="soni_case_queue.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download queue JSON",
                data=json.dumps(queue_rows, indent=2),
                file_name="soni_case_queue.json",
                mime="application/json",
            )

    selected_case = next(
        item for item in filtered_cases if item["run_id"] == selected_run_id
    )
    output_dir = Path(selected_case["path"])
    try:
        case_result, case_graph = load_case(output_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        st.error(str(exc))
        st.stop()

    if selected_case.get("storage") == "legacy_latest":
        st.info(
            "This case predates the case archive. The next CLI investigation will "
            "archive it automatically before publishing a new latest case."
        )

    target = case_result.get("target_entity") or {}
    target_id = str(target.get("entity_id") or "")
    classification = str(case_result.get("classification") or "")
    classification_label = CLASSIFICATION_LABELS.get(
        classification, classification.replace("_", " ").title()
    )
    resolution_candidates = case_result.get("resolution_candidates") or []
    best_score = resolution_candidates[0].get("score") if resolution_candidates else None
    enrichment = case_result.get("identity_enrichment")

    if case_result.get("mode") == "sample":
        st.warning(
            "The selected case contains the bundled fictional demonstration.",
            icon="🧪",
        )

    st.subheader(target.get("name") or case_result.get("query") or "Unresolved target")
    st.caption(
        f"Run {case_result['run_id']} · generated {case_result.get('generated_at', '')}"
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Classification", classification_label)
    metric_columns[1].metric(
        "Identity score",
        f"{float(best_score):.1f}" if best_score is not None else "Unresolved",
    )
    metric_columns[2].metric(
        "Direct screening candidates",
        len(case_result.get("matches") or []),
    )
    metric_columns[3].metric("GLEIF enriched", "Yes" if enrichment else "No")

    (
        summary_tab,
        workflow_tab,
        network_tab,
        screening_tab,
        sources_tab,
        review_tab,
    ) = st.tabs(
        [
            "Case summary",
            "Case workflow",
            "Network",
            "Screening evidence",
            "GLEIF and sources",
            "Analyst review",
        ]
    )

    with summary_tab:
        st.subheader("Executive finding")
        st.write(case_result.get("executive_finding") or "No finding supplied.")
        profile_column, finding_column = st.columns(2)
        with profile_column:
            st.subheader("Resolved entity")
            st.json(target or {"status": "Unresolved"})
        with finding_column:
            st.subheader("Ownership finding")
            st.json(
                case_result.get("ownership_finding")
                or {"status": "No ownership-derived finding"}
            )

        st.subheader("Investigative indicators")
        indicators = case_result.get("indicators") or []
        if indicators:
            for indicator in indicators:
                st.markdown(
                    f"**{indicator.get('title', 'Indicator')}:** "
                    f"{indicator.get('detail', '')}"
                )
        else:
            st.info("No additional investigative indicators were produced.")

        st.subheader("Recommended analyst actions")
        for action in case_result.get("recommended_actions") or []:
            st.markdown(f"- {action}")

        st.subheader("Case artifacts")
        artifact_columns = st.columns(4)
        artifacts = [
            (
                "Result JSON",
                output_dir / "investigation_result.json",
                "application/json",
            ),
            (
                "Graph JSON",
                output_dir / "investigation_graph.json",
                "application/json",
            ),
            (
                "Markdown brief",
                output_dir / "investigation_brief.md",
                "text/markdown",
            ),
            (
                "PDF brief",
                output_dir / "investigation_brief.pdf",
                "application/pdf",
            ),
        ]
        for column, (label, path, mime_type) in zip(
            artifact_columns, artifacts, strict=True
        ):
            with column:
                if path.exists():
                    st.download_button(
                        label,
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime=mime_type,
                    )
                else:
                    st.caption(f"{label} unavailable")

    with workflow_tab:
        database = InvestigatorDatabase(output_dir / "investigator.sqlite")
        try:
            workflow_state = database.get_case_workflow_state(
                str(case_result["run_id"])
            )
            workflow_history = [
                event.to_dict()
                for event in database.list_case_workflow_events(
                    run_id=str(case_result["run_id"]),
                    limit=100,
                )
            ]
        finally:
            database.close()

        st.subheader("Case workflow")
        state_placeholder = st.empty()
        st.caption(
            "Workflow events manage the local analyst queue. They do not alter "
            "the system classification or analyst disposition."
        )

        st.subheader("Record a workflow update")
        status_values = list(WORKFLOW_STATUS_LABELS.values())
        priority_values = list(WORKFLOW_PRIORITY_LABELS.values())
        current_status = str(workflow_state["status"])
        current_priority = str(workflow_state["priority"])
        with st.form(
            f"case_workflow_form_{case_result['run_id']}",
            clear_on_submit=False,
        ):
            workflow_actor = st.text_input(
                "Updated by",
                help="Required. Enter the analyst or supervisor making this update.",
            )
            workflow_columns = st.columns(2)
            with workflow_columns[0]:
                status_label = st.selectbox(
                    "Case status",
                    options=list(WORKFLOW_STATUS_LABELS),
                    index=status_values.index(current_status),
                )
            with workflow_columns[1]:
                priority_label = st.selectbox(
                    "Priority",
                    options=list(WORKFLOW_PRIORITY_LABELS),
                    index=priority_values.index(current_priority),
                )
            workflow_assignee = st.text_input(
                "Assignee",
                value=str(workflow_state["assignee"]),
                help="Optional local assignment label, name, or initials.",
            )
            workflow_tags = st.text_input(
                "Tags",
                value=", ".join(workflow_state["tags"]),
                help="Optional comma-separated tags. Duplicate tags are removed.",
            )
            workflow_notes = st.text_area(
                "Workflow update notes",
                help="Required. Explain why the status, priority, or assignment changed.",
            )
            workflow_submitted = st.form_submit_button(
                "Save workflow event",
                type="primary",
            )

        workflow_message = ""
        workflow_error = ""
        if workflow_submitted:
            event = CaseWorkflowEvent(
                run_id=str(case_result["run_id"]),
                status=WORKFLOW_STATUS_LABELS[status_label],
                priority=WORKFLOW_PRIORITY_LABELS[priority_label],
                assignee=workflow_assignee,
                tags=[
                    tag.strip()
                    for tag in workflow_tags.split(",")
                    if tag.strip()
                ],
                actor=workflow_actor,
                notes=workflow_notes,
                created_at=datetime.now(UTC).isoformat(),
            )
            database = InvestigatorDatabase(output_dir / "investigator.sqlite")
            try:
                event_id = database.save_case_workflow_event(event)
                workflow_state = database.get_case_workflow_state(
                    str(case_result["run_id"])
                )
                workflow_history = [
                    item.to_dict()
                    for item in database.list_case_workflow_events(
                        run_id=str(case_result["run_id"]),
                        limit=100,
                    )
                ]
                workflow_message = f"Saved workflow event #{event_id}."
            except ValueError as exc:
                workflow_error = str(exc)
            finally:
                database.close()

        with state_placeholder.container():
            state_columns = st.columns(4)
            state_columns[0].metric(
                "Status",
                str(workflow_state["status"]).replace("_", " ").title(),
            )
            state_columns[1].metric(
                "Priority",
                str(workflow_state["priority"]).title(),
            )
            state_columns[2].metric(
                "Assignee",
                workflow_state["assignee"] or "Unassigned",
            )
            state_columns[3].metric(
                "Tags",
                len(workflow_state["tags"]),
            )
            if workflow_state["updated_at"]:
                st.caption(
                    f"Last updated {workflow_state['updated_at']} by "
                    f"{workflow_state['updated_by']} · "
                    f"Tags: {', '.join(workflow_state['tags']) or 'none'}"
                )
            else:
                st.caption(
                    "No workflow event has been recorded. Default state: "
                    "Open / Normal / Unassigned."
                )

        if workflow_message:
            st.success(workflow_message)
        if workflow_error:
            st.error(workflow_error)

        st.subheader("Workflow history")
        if workflow_history:
            st.dataframe(workflow_history, width="stretch", hide_index=True)
            st.download_button(
                "Download workflow history",
                data=json.dumps(workflow_history, indent=2),
                file_name=f"{case_result['run_id']}_workflow_history.json",
                mime="application/json",
            )
        else:
            st.info("No workflow events have been recorded for this run.")

    with network_tab:
        include_addresses = st.checkbox(
            "Include address nodes",
            value=False,
            help="Address nodes can make large live graphs harder to read.",
        )
        st.graphviz_chart(
            build_dot_graph(
                case_graph,
                target_id=target_id,
                include_addresses=include_addresses,
            ),
            width="stretch",
        )
        st.caption(
            "Red = directly designated; gold = resolved target; blue = other "
            "entities; oval = address."
        )
        st.subheader("Loaded graph relationships")
        st.dataframe(
            case_graph.get("edges") or [],
            width="stretch",
            hide_index=True,
        )

    with screening_tab:
        st.subheader("Identity-resolution candidates")
        st.dataframe(
            resolution_candidates,
            width="stretch",
            hide_index=True,
        )
        st.subheader("Direct sanctions-screening candidates")
        matches = case_result.get("matches") or []
        if matches:
            st.dataframe(matches, width="stretch", hide_index=True)
        else:
            st.info("No direct candidate exceeded the configured threshold.")
        st.caption(
            "Scores rank candidates for review; they are not calibrated identity "
            "probabilities and do not prove a designation match."
        )

    with sources_tab:
        st.subheader("GLEIF enrichment")
        if enrichment:
            st.json(enrichment)
            st.warning(enrichment.get("scope_note", ""), icon="⚠️")
        else:
            st.info("This investigation did not include GLEIF enrichment.")
        st.subheader("Source register")
        st.dataframe(
            case_result.get("sources") or [],
            width="stretch",
            hide_index=True,
        )
        st.subheader("Methodology settings")
        st.json(case_result.get("methodology") or {})

    with review_tab:
        st.subheader("Record an analyst disposition")
        st.caption(
            "Reviews are append-only. They document human judgment without "
            "overwriting the system-generated classification."
        )
        with st.form(
            f"case_review_form_{case_result['run_id']}",
            clear_on_submit=True,
        ):
            reviewer = st.text_input("Reviewer name or initials")
            disposition_label = st.selectbox(
                "Disposition",
                options=list(REVIEW_LABELS),
            )
            notes = st.text_area(
                "Review notes",
                help="Required. Record the identifiers, evidence, and reasoning reviewed.",
            )
            submitted = st.form_submit_button(
                "Save disposition",
                type="primary",
            )

        review_message = ""
        review_error = ""
        if submitted:
            review = AnalystReview(
                run_id=str(case_result["run_id"]),
                entity_id=target_id,
                target_name=str(target.get("name") or case_result.get("query") or ""),
                system_classification=classification,
                system_version=str(case_result.get("software_version") or "pre-0.3.0"),
                disposition=REVIEW_LABELS[disposition_label],
                reviewer=reviewer,
                notes=notes,
                created_at=datetime.now(UTC).isoformat(),
            )
            database = InvestigatorDatabase(output_dir / "investigator.sqlite")
            try:
                review_id = database.save_analyst_review(review)
                review_message = f"Saved analyst review #{review_id}."
            except ValueError as exc:
                review_error = str(exc)
            finally:
                database.close()
        if review_message:
            st.success(review_message)
        if review_error:
            st.error(review_error)

        database = InvestigatorDatabase(output_dir / "investigator.sqlite")
        try:
            review_history = [
                item.to_dict()
                for item in database.list_analyst_reviews(
                    run_id=str(case_result["run_id"]),
                    limit=100,
                )
            ]
        finally:
            database.close()
        st.subheader("Review history")
        if review_history:
            st.dataframe(review_history, width="stretch", hide_index=True)
            st.download_button(
                "Download review history",
                data=json.dumps(review_history, indent=2),
                file_name=f"{case_result['run_id']}_review_history.json",
                mime="application/json",
            )
        else:
            st.info("No analyst reviews have been recorded for this run.")
    st.stop()

if workspace == "Case comparison":
    cases = load_case_registry()
    if len(cases) < 2:
        st.info(
            "At least two archived investigation cases are required for comparison."
        )
        st.stop()

    def format_comparison_case(run_id: str) -> str:
        case = next(item for item in cases if item["run_id"] == run_id)
        generated = str(case.get("generated_at") or "")[:16].replace("T", " ")
        return (
            f"{case['target_name']} — {generated or 'date unavailable'} — "
            f"{run_id}"
        )

    st.subheader("Investigation case comparison")
    st.caption(
        "Choose an older or reference case as the baseline and a second case as "
        "the comparison."
    )
    selector_columns = st.columns(2)
    with selector_columns[0]:
        baseline_run_id = st.selectbox(
            "Baseline case",
            options=[item["run_id"] for item in cases],
            index=1,
            format_func=format_comparison_case,
            key="comparison_baseline",
        )
    with selector_columns[1]:
        comparison_run_id = st.selectbox(
            "Comparison case",
            options=[item["run_id"] for item in cases],
            index=0,
            format_func=format_comparison_case,
            key="comparison_current",
        )

    if baseline_run_id == comparison_run_id:
        st.warning("Select two different investigation cases.")
        st.stop()

    baseline_case = next(
        item for item in cases if item["run_id"] == baseline_run_id
    )
    comparison_case = next(
        item for item in cases if item["run_id"] == comparison_run_id
    )
    try:
        baseline_result, baseline_graph = load_case(Path(baseline_case["path"]))
        comparison_result, comparison_graph = load_case(
            Path(comparison_case["path"])
        )
        comparison_report = compare_cases(
            baseline_result,
            baseline_graph,
            comparison_result,
            comparison_graph,
            baseline_workflow=baseline_case["workflow"],
            comparison_workflow=comparison_case["workflow"],
            baseline_review_count=baseline_case["analyst_review_count"],
            comparison_review_count=comparison_case["analyst_review_count"],
            baseline_workflow_event_count=baseline_case["workflow_event_count"],
            comparison_workflow_event_count=comparison_case[
                "workflow_event_count"
            ],
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        st.error(str(exc))
        st.stop()

    if not comparison_report["same_target"]:
        st.warning(
            "The selected cases resolve to different target names. Interpret this "
            "as a cross-case comparison, not a longitudinal change analysis.",
            icon="⚠️",
        )
    st.info(comparison_report["scope_note"])

    baseline_summary = comparison_report["baseline"]
    comparison_summary = comparison_report["comparison"]
    deltas = comparison_report["deltas"]
    metric_columns = st.columns(5)
    metric_columns[0].metric(
        "Classification",
        comparison_summary["classification"].replace("_", " ").title(),
        delta=(
            "Changed"
            if baseline_summary["classification"]
            != comparison_summary["classification"]
            else "Unchanged"
        ),
    )
    metric_columns[1].metric(
        "Identity score",
        (
            f"{comparison_summary['identity_score']:.1f}"
            if comparison_summary["identity_score"] is not None
            else "Unresolved"
        ),
        delta=deltas["identity_score"],
    )
    metric_columns[2].metric(
        "Graph nodes",
        comparison_summary["graph_node_count"],
        delta=deltas["graph_node_count"],
    )
    metric_columns[3].metric(
        "Graph edges",
        comparison_summary["graph_edge_count"],
        delta=deltas["graph_edge_count"],
    )
    metric_columns[4].metric(
        "Analyst reviews",
        comparison_summary["review_count"],
        delta=deltas["review_count"],
    )

    st.download_button(
        "Download comparison JSON",
        data=json.dumps(comparison_report, indent=2),
        file_name=(
            f"{baseline_run_id}_vs_{comparison_run_id}_comparison.json"
        ),
        mime="application/json",
    )

    (
        comparison_summary_tab,
        comparison_identity_tab,
        comparison_graph_tab,
        comparison_context_tab,
    ) = st.tabs(
        [
            "Summary changes",
            "Identity and screening",
            "Graph changes",
            "Sources and indicators",
        ]
    )

    with comparison_summary_tab:
        st.dataframe(
            comparison_report["field_comparison"],
            width="stretch",
            hide_index=True,
        )
        st.subheader("Numeric deltas")
        st.json(deltas)

    def render_added_removed(title: str, payload: dict) -> None:
        st.subheader(title)
        added_column, removed_column = st.columns(2)
        with added_column:
            st.markdown("**Added in comparison**")
            if payload["added"]:
                st.dataframe(
                    payload["added"],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("None")
        with removed_column:
            st.markdown("**Removed from baseline**")
            if payload["removed"]:
                st.dataframe(
                    payload["removed"],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("None")
        if payload.get("changed"):
            st.markdown("**Changed in both cases**")
            st.dataframe(
                payload["changed"],
                width="stretch",
                hide_index=True,
            )

    with comparison_identity_tab:
        render_added_removed(
            "Identity-resolution candidates",
            comparison_report["identity_candidates"],
        )
        render_added_removed(
            "Direct sanctions-screening candidates",
            comparison_report["sanctions_candidates"],
        )

    with comparison_graph_tab:
        render_added_removed(
            "Graph relationships",
            comparison_report["graph_edges"],
        )

    with comparison_context_tab:
        render_added_removed(
            "Sources",
            comparison_report["sources"],
        )
        render_added_removed(
            "Investigative indicators",
            comparison_report["indicators"],
        )
    st.stop()

if workspace == "GLEIF legal-entity lookup":
    st.subheader("GLEIF legal-entity identity and parent lookup")
    st.caption(
        "Search the Global LEI Index, select an LEI, and retrieve published direct "
        "and ultimate accounting-consolidating parent relationships."
    )
    lookup_col, country_col = st.columns([3, 1])
    with lookup_col:
        lookup_name = st.text_input("Legal-entity name", "")
    with country_col:
        lookup_country = st.text_input(
            "Country code", "", max_chars=2, help="Optional two-letter ISO code."
        )

    if st.button("Search GLEIF", type="primary"):
        st.session_state.pop("gleif_candidates", None)
        try:
            with st.spinner("Searching the Global LEI Index..."):
                candidates = GleifClient().search(
                    lookup_name,
                    country=lookup_country,
                    limit=10,
                )
            st.session_state["gleif_candidates"] = [
                candidate.to_dict() for candidate in candidates
            ]
        except GleifError as exc:
            st.error(str(exc))

    candidates = st.session_state.get("gleif_candidates", [])
    if candidates:
        display_candidates = [
            {"rank": rank, **candidate}
            for rank, candidate in enumerate(candidates, start=1)
        ]
        selected_lei = st.selectbox(
            "Candidate",
            options=[candidate["lei"] for candidate in candidates],
            format_func=lambda lei: next(
                (
                    f"{item['name']} — {item['country'] or 'country not supplied'} "
                    f"— score {float(item.get('match_score', 0.0)):.1f} — {lei}"
                    for item in candidates
                    if item["lei"] == lei
                ),
                lei,
            ),
        )
        st.dataframe(display_candidates, width="stretch", hide_index=True)
        st.caption(
            "Candidate scores rank legal-name similarity for analyst review. "
            "They are not identity probabilities and do not establish a match."
        )
        if len(candidates) > 1:
            score_margin = float(candidates[0].get("match_score", 0.0)) - float(
                candidates[1].get("match_score", 0.0)
            )
            if score_margin < 5:
                st.warning(
                    "The leading candidates are closely ranked. Confirm the LEI "
                    "using jurisdiction, registration status, identifiers, and address.",
                    icon="⚠️",
                )
        if st.button("Load identity and parent links"):
            try:
                with st.spinner("Retrieving GLEIF record and parent links..."):
                    enrichment = GleifClient().enrich(lei=selected_lei)
                summary = enrichment.summary()
                st.success(
                    f"Loaded {summary['selected_name']} ({summary['selected_lei']})."
                )
                profile_tab, network_tab, evidence_tab = st.tabs(
                    ["Identity profile", "Parent network", "Source evidence"]
                )
                entity_map = {
                    entity.entity_id: entity for entity in enrichment.entities
                }
                selected_id = f"gleif:{selected_lei}"
                with profile_tab:
                    selected = entity_map[selected_id]
                    st.json(selected.to_dict())
                    st.subheader("Addresses")
                    address_rows = [
                        item.to_dict() for item in enrichment.addresses
                    ]
                    if address_rows:
                        st.dataframe(
                            address_rows,
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "GLEIF did not return a legal or headquarters address "
                            "for the selected record."
                        )
                with network_tab:
                    dot = [
                        "digraph G {",
                        "rankdir=LR;",
                        'node [shape=box, style="rounded,filled", fillcolor="#DCE8F5"];',
                    ]
                    for entity in enrichment.entities:
                        label = entity.name.replace('"', '\\"')
                        fill = "#F3D58A" if entity.entity_id == selected_id else "#DCE8F5"
                        dot.append(
                            f'"{entity.entity_id}" '
                            f'[label="{label}", fillcolor="{fill}"];'
                        )
                    for relationship in enrichment.relationships:
                        label = (
                            "direct accounting parent"
                            if relationship.relationship_type.startswith("DIRECT_")
                            else "ultimate accounting parent"
                        )
                        dot.append(
                            f'"{relationship.source_id}" -> '
                            f'"{relationship.target_id}" [label="{label}"];'
                        )
                    dot.append("}")
                    st.graphviz_chart("\n".join(dot), width="stretch")
                    st.warning(summary["scope_note"], icon="⚠️")
                with evidence_tab:
                    relationship_rows = [
                        item.to_dict() for item in enrichment.relationships
                    ]
                    if relationship_rows:
                        st.dataframe(
                            relationship_rows,
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "No published direct or ultimate accounting-consolidating "
                            "parent relationship was returned for this LEI."
                        )
                    for warning in enrichment.warnings:
                        st.info(warning)
                    st.download_button(
                        "Download GLEIF enrichment JSON",
                        data=json.dumps(
                            {
                                "summary": summary,
                                "entities": [
                                    item.to_dict() for item in enrichment.entities
                                ],
                                "aliases": [
                                    item.to_dict() for item in enrichment.aliases
                                ],
                                "addresses": [
                                    item.to_dict() for item in enrichment.addresses
                                ],
                            },
                            indent=2,
                        ),
                        file_name=f"gleif_{selected_lei}.json",
                        mime="application/json",
                    )
            except GleifError as exc:
                st.error(str(exc))
    elif lookup_name:
        st.info("No stored candidates. Select Search GLEIF to run a lookup.")

    st.divider()
    st.caption(
        "This workspace does not perform OFAC screening by itself. Use "
        "`python main.py --mode live --gleif-enrich` to merge GLEIF enrichment "
        "with current OFAC screening."
    )
    st.stop()

entities, aliases, addresses, relationships = load_demo()
entity_map = {entity.entity_id: entity for entity in entities}
matcher = EntityMatcher(entities, aliases)

st.warning(
    "The fictional demonstration workspace contains invented entities, "
    "relationships, addresses, and programs.",
    icon="🧪",
)

with st.sidebar:
    st.header("Investigation")
    query = st.text_input("Entity name", "Harbor Meridian Trading LLC")
    threshold = st.slider("Screening threshold", 50, 100, 75)
    graph_depth = st.slider("Network depth", 1, 4, 3)
    designated_only = st.checkbox("Direct designations only", value=False)

results = matcher.search(
    query,
    designated_only=designated_only,
    threshold=float(threshold),
    limit=25,
)

if not results:
    st.info("No candidate exceeded the selected threshold.")
    st.stop()

best = results[0]
target = entity_map[best.entity_id]
ownership = derive_ownership_status(entities, relationships)
finding = ownership.get(target.entity_id)
path = find_ownership_path(target.entity_id, ownership)

col1, col2, col3 = st.columns(3)
col1.metric("Best identity score", f"{best.score:.1f}")
col2.metric("Directly designated", "Yes" if target.designated else "No")
col3.metric(
    "Ownership classification",
    finding.status.replace("_", " ").title() if finding else "No derived finding",
)

tab_profile, tab_network, tab_matches, tab_evidence = st.tabs(
    ["Entity profile", "Network", "Match review", "Evidence"]
)

with tab_profile:
    st.subheader(target.name)
    st.json(
        {
            "entity_id": target.entity_id,
            "type": target.entity_type,
            "country": target.country,
            "directly_designated": target.designated,
            "programs": target.programs,
            "identifiers": target.identifiers,
            "source": target.source,
        }
    )
    if finding:
        st.subheader("Ownership finding")
        st.json(finding.to_dict())
    if path:
        st.write("Ownership path:", " → ".join(entity_map[item].name for item in path))

with tab_network:
    adjacency: dict[str, list] = {}
    for relationship in relationships:
        adjacency.setdefault(relationship.source_id, []).append(relationship)
        adjacency.setdefault(relationship.target_id, []).append(relationship)

    allowed = {target.entity_id}
    frontier = {target.entity_id}
    for _ in range(graph_depth):
        next_frontier = set()
        for current in frontier:
            for relationship in adjacency.get(current, []):
                next_frontier.add(relationship.source_id)
                next_frontier.add(relationship.target_id)
        allowed.update(next_frontier)
        frontier = next_frontier

    dot = ["digraph G {", "rankdir=LR;", 'node [shape=box, style="rounded,filled"];']
    for entity_id in sorted(allowed):
        entity = entity_map[entity_id]
        fill = "#F4A6A6" if entity.designated else "#DCE8F5"
        if entity_id == target.entity_id:
            fill = "#F3D58A"
        label = entity.name.replace('"', '\\"')
        dot.append(f'"{entity_id}" [label="{label}", fillcolor="{fill}"];')
    for relationship in relationships:
        if relationship.source_id in allowed and relationship.target_id in allowed:
            edge_label = relationship.relationship_type
            if relationship.ownership_pct is not None:
                edge_label += f" {relationship.ownership_pct:g}%"
            dot.append(
                f'"{relationship.source_id}" -> "{relationship.target_id}" '
                f'[label="{edge_label}"];'
            )
    dot.append("}")
    st.graphviz_chart("\n".join(dot), width="stretch")
    st.caption("Red = directly designated; gold = selected target; blue = other entity.")

with tab_matches:
    rows = [
        {
            "entity": item.entity_name,
            "matched_name": item.matched_name,
            "match_type": item.match_type,
            "score": item.score,
            "directly_designated": item.designated,
            "country": item.country,
            "reasons": "; ".join(item.reasons),
        }
        for item in results
    ]
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption("A name score is a triage aid. Review identifiers and context before merging records.")

with tab_evidence:
    target_relationships = [
        relationship.to_dict()
        for relationship in relationships
        if relationship.source_id == target.entity_id
        or relationship.target_id == target.entity_id
    ]
    target_addresses = [
        address.to_dict() for address in addresses if address.entity_id == target.entity_id
    ]
    st.subheader("Relationships")
    st.dataframe(target_relationships, width="stretch", hide_index=True)
    st.subheader("Addresses")
    st.dataframe(target_addresses, width="stretch", hide_index=True)
    st.download_button(
        "Download case JSON",
        data=json.dumps(
            {
                "target": target.to_dict(),
                "match": best.to_dict(),
                "ownership_finding": finding.to_dict() if finding else None,
                "ownership_path": path,
                "relationships": target_relationships,
                "addresses": target_addresses,
            },
            indent=2,
        ),
        file_name="investigation_case.json",
        mime="application/json",
    )
