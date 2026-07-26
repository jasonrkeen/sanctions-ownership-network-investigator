# Analyst workflow

## Purpose

The dashboard connects a command-line investigation to a reviewable case. It
keeps source-derived facts, model classifications, and human decisions as
separate layers.

## Workflow

1. Run a sample or live investigation with `main.py`.
2. Start the dashboard with `python -m streamlit run app.py`.
3. Select **Case investigations**.
4. Select a prior or current run from **Investigation case**.
5. Review the executive finding, target identity, graph, match candidates,
   GLEIF enrichment, source register, and generated artifacts.
6. Use **Case workflow** to record status, priority, assignee, tags, and the
   reason for the update.
7. Record a disposition with reviewer identity and evidence-based notes.
8. Export workflow or review history when needed.
9. Use **Queue exports** for a consolidated CSV or JSON worklist.
10. Use **Case comparison** to compare any two archived investigation runs.

## Controlled workflow values

| Dimension | Values |
|---|---|
| Status | `open`, `in_review`, `pending_information`, `escalated`, `closed` |
| Priority | `low`, `normal`, `high`, `critical` |

Cases with no workflow event use the derived default
`open / normal / unassigned`. Every saved update requires an actor and notes.
The newest event supplies the displayed queue state; earlier events remain in
the history.

## Comparison workflow

1. Select **Case comparison**.
2. Choose a baseline case and a different comparison case.
3. Review summary-field changes and numeric deltas.
4. Review added and removed candidates, graph relationships, sources, and
   indicators.
5. Download the comparison JSON when a reproducible record is needed.

If the resolved target names differ, the dashboard labels the result as a
cross-case comparison. Every comparison is an artifact difference report, not
a causal or legal-status determination.

## Controlled dispositions

| Disposition | Intended meaning |
|---|---|
| `needs_more_information` | Evidence is insufficient to resolve the case |
| `identity_confirmed` | Reviewed identifiers support the proposed entity resolution |
| `identity_rejected` | Reviewed identifiers conflict with the proposed resolution |
| `escalated_for_compliance_review` | The case requires enhanced or legal/compliance review |
| `closed_no_material_indicator` | Review found no material indicator in the available evidence |

## Audit behavior

Reviews are append-only SQLite records. A new review receives a new monotonic
identifier and timestamp. Earlier reviews remain available in the history.

The review record captures the system classification as it existed at review
time. It does not modify:

- The investigation JSON
- Direct designation status
- Ownership-derived classification
- Match scores
- Graph relationships
- Earlier analyst reviews

This separation prevents a human disposition from being mistaken for a model
output and prevents later review activity from erasing the decision history.

## Case storage

Each CLI run is stored under `outputs/cases/<run_id>`. The dashboard discovers
those folders, orders them newest first, and routes artifact downloads and
analyst reviews to the selected case. `outputs/cases/index.json` provides a
portable summary index, while `outputs/latest` remains a compatibility snapshot.

The first 0.4.0-or-newer CLI run automatically archives an existing pre-0.4.0 latest
case before publishing a new one. This remains a local analyst workflow rather
than a multi-user case-management system. The assignee is a local workflow
label, not an authenticated account. Authentication, access controls, database
migration tooling, and supervisory approval remain future production features.
