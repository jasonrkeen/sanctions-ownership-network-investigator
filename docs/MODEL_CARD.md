# Model card

## Model name

SONI Entity Matching and Ownership Propagation MVP, version 1.0.0.

## Intended use

- Sanctions-screening demonstrations
- Corporate ownership research
- Entity-resolution education
- Compliance and due-diligence analyst support
- Portfolio demonstration

## Out-of-scope use

- Fully automated rejection or blocking decisions
- Legal determinations
- Adverse action based only on a name score
- Treating an offshore record or shared address as evidence of wrongdoing
- Surveillance or collection of nonpublic personal information

## Inputs

- Entity names and aliases
- Country context
- Authoritative identifiers when available
- Direct designation status
- Ownership and control relationships
- Relationship effective dates and evidence

## Outputs

- Ranked match candidates
- Direct-designation indicator
- Ownership-derived review candidate
- Ownership path
- Contextual indicators
- Source-backed investigation brief
- Multi-case dashboard and case-specific append-only analyst review history
- Searchable local case queue and append-only workflow-event history
- Consolidated queue exports and deterministic archived-case comparison

## Known limitations

- The name score is not calibrated as a probability.
- Standard-library transliteration is limited.
- Common names can generate false positives.
- Missing ownership data can generate false negatives.
- The current engine does not calculate economic interest through arbitrary
  multiplication; it propagates status stage by stage.
- Effective-date validation is not yet enforced.
- Program-specific restrictions and licenses are not modeled.
- Live OFAC mode alone does not supply corporate ownership relationships.
- GLEIF Level 2 links identify accounting-consolidating parents, not ownership
  percentages, beneficial owners, control findings, or sanctions status.
- When a name is used without an exact LEI, GLEIF candidate ranking remains
  sensitive to ambiguous, abbreviated, or common legal names. Analysts must
  verify the selected LEI before relying on the enrichment.
- The local case registry does not provide authentication, multi-user case
  assignment, concurrency controls, role-based access, or supervisory approval.
- Workflow status, priority, assignee, and tags are local routing metadata.
  They are not analytical findings or authenticated personnel assignments.
- Case-comparison deltas describe stored artifact differences. They do not
  establish causation, risk deterioration, improvement, or legal-status change.

## Human oversight

Analysts must confirm identifiers, source records, ownership, dates, applicable
programs, and current official guidance. Every proposed match should be
confirmed or rejected with a reason. Analyst dispositions are audit events and
do not overwrite system classifications.

## Testing status

The MVP has deterministic tests for normalization, aliases, multi-level
ownership propagation, relational OFAC-file parsing, GLEIF identity and parent
parsing, dashboard artifact loading and graph rendering, append-only review
persistence, legacy-case migration, multi-case indexing, append-only workflow
state derivation and validation, queue serialization, deterministic comparison
deltas, exclusion of accounting-parent links from ownership propagation, and
the end-to-end fictional demonstration. It has not yet been validated on a
representative production population.
