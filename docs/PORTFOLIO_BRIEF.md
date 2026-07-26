# Portfolio brief

## One-line description

Built a source-backed sanctions and corporate-ownership investigation MVP that
combines entity resolution, graph analysis, reproducible case artifacts, local
workflow management, and append-only analyst review.

## Problem and approach

Name-only sanctions screening can blur identity matching, direct designation,
ownership, and contextual relationships. This project separates those
questions, preserves the source evidence behind each result, and gives an
analyst a reviewable workflow rather than an opaque pass/fail decision.

The application ingests OFAC relational files, optionally enriches legal-entity
identity and accounting-parent context from GLEIF, ranks identity candidates,
propagates loaded percentage ownership through a graph, archives each run, and
supports review, comparison, and queue export in Streamlit.

## Skills demonstrated

| Area | Evidence in the project |
|---|---|
| Python engineering | Typed domain models, modular standard-library pipeline, packaging, tests |
| Data engineering | Relational CSV parsing, normalization, provenance, SQLite persistence |
| Entity resolution | Alias screening, legal-suffix normalization, token-aware ranking |
| Graph analytics | Multi-hop extraction and iterative ownership propagation |
| Product design | Case queue, evidence views, workflow events, analyst dispositions |
| Governance | Model card, methodology, limitations, append-only audit history |
| Reproducibility | Per-run artifacts, archived-case comparison, clean release builder |
| DevOps | Docker environment, GitHub Actions, automated publication audit |

## Résumé bullets

- Built a Python sanctions and ownership-network investigation application that
  ingests OFAC relational data, enriches legal-entity context through GLEIF,
  ranks entity matches, and evaluates multi-level percentage ownership.
- Designed a Streamlit analyst workspace with searchable case queues,
  append-only workflow and disposition histories, evidence-backed graph views,
  archived-case comparison, and CSV/JSON exports.
- Implemented reproducible per-run JSON, Markdown, PDF, SQLite, and Neo4j-ready
  artifacts with a clean release pipeline and automated tests covering
  ingestion, matching, ownership, case management, review, and packaging.

## LinkedIn project description

Developed a portfolio MVP for sanctions screening and corporate-ownership
research using Python, Streamlit, SQLite, and graph-oriented data structures.
The system separates identity resolution, direct designation, ownership-derived
review candidates, and analyst judgment; retains source evidence; archives each
investigation; and supports queue management, case comparison, and append-only
review history. It includes OFAC ingestion, targeted GLEIF enrichment, a
fictional deterministic demonstration, automated tests, Docker configuration,
and explicit model and production limitations.

## Interview discussion

Be prepared to explain:

1. Why an identity score is a ranking aid rather than a probability.
2. Why GLEIF accounting-parent relationships cannot be treated as percentage
   ownership.
3. How ownership candidates propagate across multiple graph levels.
4. Why system classifications, workflow state, and analyst dispositions are
   stored separately.
5. How case-specific artifacts and deterministic comparisons improve auditability.
6. What must change before production use: calibrated thresholds, richer
   ownership sources, authentication, centralized persistence, concurrency
   controls, policy rules, observability, and independent validation.

## Honest scope statement

This is a public portfolio MVP and analyst decision-support demonstration. It
is not production-ready compliance software, a complete ownership database, or
legal advice. Its value is in the analytical decomposition, provenance,
workflow design, reproducibility, and explicit handling of uncertainty.
