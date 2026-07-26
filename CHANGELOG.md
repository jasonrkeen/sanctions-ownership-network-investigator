# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-26

### Added

- Public-release documentation, including a reproducible demonstration
  walkthrough, portfolio brief, architecture overview, and release notes
- Contribution, security-reporting, citation, issue, and pull-request guidance
- Automated publication-readiness audit for required files, synchronized
  version metadata, documentation links, and release-boundary checks

### Changed

- Promoted the validated portfolio MVP to its first stable public release
- Expanded the README with project status, evaluator quick start, documentation
  map, and explicit production-use boundary
- Strengthened the release builder's required-file checks

### Validation

- Standard-library test suite
- Python bytecode compilation
- End-to-end fictional demonstration
- Clean ZIP construction and CRC validation
- Publication-readiness audit

## [0.6.0] - 2026-07-26

### Added

- Consolidated case-queue exports in CSV and JSON
- Archived-case comparison for classifications, identity scores, candidates,
  graph relationships, sources, indicators, workflow state, and review counts

## [0.5.0] - 2026-07-26

### Added

- Append-only case workflow events
- Controlled status and priority values
- Local assignment, tags, queue search, and workflow filters

## [0.4.0] - 2026-07-26

### Added

- Multi-case registry with archived run reopening
- Backward-compatible `outputs/latest` snapshot
- Legacy latest-run migration that preserves analyst reviews

## [0.3.0] - 2026-07-26

### Added

- Append-only analyst review and disposition history
- Analyst review workspace in the Streamlit dashboard

## [0.2.0] - 2026-07-26

### Added

- Targeted GLEIF identity and accounting-parent enrichment
- Streamlit legal-entity lookup workspace
- Clean release builder and expanded validation

## [0.1.0] - 2026-07-26

### Added

- Fictional end-to-end sample pipeline
- OFAC relational CSV ingestion
- Entity normalization and sanctions screening
- Ownership propagation, SQLite evidence store, graph export, and reports
