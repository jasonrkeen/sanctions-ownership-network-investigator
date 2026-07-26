# Data dictionary

## Entity

| Field | Type | Description |
|---|---|---|
| `entity_id` | string | Stable source-prefixed entity identifier |
| `name` | string | Primary source name |
| `entity_type` | string | Person, entity, vessel, aircraft, or other type |
| `source` | string | Originating dataset |
| `designated` | boolean | Direct designation in the loaded source |
| `programs` | list | Source sanctions programs |
| `country` | string | Country context when available |
| `identifiers` | object | LEI, CIK, IMO, registration, or other identifiers |
| `remarks` | string | Source remarks |
| `retrieved_at` | timestamp | Retrieval or demonstration timestamp |

## Alias

| Field | Type | Description |
|---|---|---|
| `alias_id` | string | Stable alias identifier |
| `entity_id` | string | Parent entity |
| `name` | string | Alternate name |
| `alias_type` | string | Alias classification |
| `weak` | boolean | Weak-alias indicator |
| `remarks` | string | Source context |

## Address

| Field | Type | Description |
|---|---|---|
| `address_id` | string | Stable address record identifier |
| `entity_id` | string | Associated entity |
| `address` | string | Street address |
| `city_state_postal` | string | Locality and postal components |
| `country` | string | Address country |
| `source` | string | Originating dataset |

## Relationship

| Field | Type | Description |
|---|---|---|
| `relationship_id` | string | Stable relationship identifier |
| `source_id` | string | Origin node |
| `target_id` | string | Destination node |
| `relationship_type` | string | `OWNS`, `CONTROLS`, `DIRECT_ACCOUNTING_CONSOLIDATING_PARENT_OF`, `ULTIMATE_ACCOUNTING_CONSOLIDATING_PARENT_OF`, etc. |
| `ownership_pct` | decimal | Direct ownership percentage when known |
| `confidence` | decimal | Evidence confidence from 0 to 1 |
| `valid_from` | date | Relationship start date |
| `valid_to` | date | Relationship end date |
| `evidence` | string | Short evidence description |
| `analyst_status` | string | Unreviewed, confirmed, rejected, or other state |

GLEIF accounting-parent relationships always have a null `ownership_pct`.
Their direction is parent (`source_id`) to child (`target_id`). They are graph
context and are not interpreted as percentage ownership.

## Match result

| Field | Type | Description |
|---|---|---|
| `query` | string | Submitted subject name |
| `entity_id` | string | Candidate entity |
| `matched_name` | string | Primary or alias name producing the score |
| `match_type` | string | Primary, AKA, former name, etc. |
| `score` | decimal | Candidate-ranking score from 0 to 100 |
| `reasons` | list | Supporting comparison reasons |
| `review_status` | string | Analyst disposition |

## Analyst review

| Field | Type | Description |
|---|---|---|
| `review_id` | integer | Monotonic append-only review identifier |
| `run_id` | string | Investigation run being reviewed |
| `entity_id` | string | Resolved target identifier, if available |
| `target_name` | string | Target name represented at review time |
| `system_classification` | string | Immutable model classification recorded with the review |
| `system_version` | string | Software version that produced the classification |
| `disposition` | string | Controlled analyst disposition |
| `reviewer` | string | Reviewer name or initials |
| `notes` | string | Required evidence and reasoning notes |
| `created_at` | timestamp | UTC review timestamp |

Analyst reviews are append-only. They do not update the investigation result,
entity designation state, ownership finding, or earlier review records.

## Case workflow event

| Field | Type | Description |
|---|---|---|
| `event_id` | integer | Monotonic append-only workflow event identifier |
| `run_id` | string | Investigation case receiving the event |
| `status` | string | Controlled queue status |
| `priority` | string | Controlled queue priority |
| `assignee` | string | Optional local assignment label |
| `tags` | list | Up to 20 normalized case tags |
| `actor` | string | Person or initials recording the update |
| `notes` | string | Required reason for the workflow change |
| `created_at` | timestamp | UTC event timestamp |

Current workflow state is derived from the newest event. When no event exists,
the state is `open / normal / unassigned`. Workflow events do not change the
system classification or analyst-review disposition.

## Consolidated queue export

The CSV and JSON queue exports contain one row per discovered case:

| Field | Description |
|---|---|
| `run_id` | Investigation run identifier |
| `generated_at` | Investigation generation timestamp |
| `target_name` | Resolved target or submitted query |
| `classification` | Stored system classification |
| `status`, `priority` | Current derived workflow state |
| `assignee`, `tags` | Local routing metadata |
| `workflow_updated_at`, `workflow_updated_by` | Latest workflow event metadata |
| `workflow_event_count` | Number of append-only workflow events |
| `analyst_review_count` | Number of append-only analyst dispositions |
| `case_directory` | Archived run directory name |

## Case comparison

Comparison JSON contains `baseline` and `comparison` summaries, field-level
changes, numeric deltas, and added or removed identity candidates, sanctions
candidates, graph edges, sources, and indicators. Numeric deltas are calculated
as comparison minus baseline.

## Case index

`outputs/cases/index.json` contains a generated summary of archived
investigations.

| Field | Type | Description |
|---|---|---|
| `schema_version` | integer | Case-index schema version |
| `updated_at` | timestamp | UTC time the index was refreshed |
| `case_count` | integer | Number of indexed archived cases |
| `cases` | list | Newest-first case summaries |
| `case_directory` | string | Run-specific directory under `outputs/cases` |

Each case summary includes the run ID, generation time, query, resolved target
name, classification, mode, and software version. The index is derived from
case artifacts and does not replace the underlying investigation JSON or
SQLite review history.
