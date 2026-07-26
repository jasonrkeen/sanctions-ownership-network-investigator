# Version 1.0.0 release notes

Release date: 2026-07-26

Version 1.0.0 is the first public portfolio release of the Sanctions Ownership
Network Investigator. It packages the validated analytical MVP with the
documentation, repository governance, and automated checks needed for external
review.

## Highlights

- OFAC relational-file ingestion and alias-aware sanctions screening
- Targeted GLEIF legal-entity and accounting-parent enrichment
- Source-backed identity ranking and evidence separation
- Iterative percentage-ownership candidate propagation
- Per-run case artifacts and backward-compatible latest snapshot
- Searchable case queue with append-only workflow history
- Append-only analyst dispositions that do not alter system output
- Archived-case comparison and CSV/JSON queue exports
- Markdown, optional PDF, graph JSON, SQLite, and Neo4j-compatible exports
- Reproducible fictional demonstration, automated tests, and clean ZIP builder

## Publication additions

- Changelog, citation metadata, contribution and security policies
- Architecture, demo, portfolio, and release documentation
- GitHub issue forms and pull-request template
- Automated publication audit for required files, version synchronization,
  local documentation links, and release boundaries

## Install

Extract the ZIP, open PowerShell in the extracted project directory, and run:

```powershell
python main.py --mode sample --query "Harbor Meridian Trading LLC"
```

For the dashboard:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dashboard,pdf]"
python -m streamlit run app.py
```

## Updating an existing copy

Generated cases and downloaded OFAC files are excluded from releases. Before a
full folder replacement, back up `outputs` and `data\raw\ofac` if they contain
work you need. Copying the new release files over an existing folder preserves
files that are not part of the ZIP, but a separate backup is still recommended.

## Known limitations

- The application is not production-ready compliance software or legal advice.
- Matching scores are not calibrated probabilities.
- OFAC list data does not provide a complete ownership graph.
- GLEIF accounting-parent links are not percentage ownership.
- Effective dates, program-specific restrictions, licenses, and divestments
  require analyst validation.
- The local workflow lacks authentication, authorization, concurrency control,
  centralized storage, and supervisory approval.
- Live-source results can change as official records change.

See the [model card](MODEL_CARD.md) and
[methodology](METHODOLOGY.md) for the full analytical boundary.
