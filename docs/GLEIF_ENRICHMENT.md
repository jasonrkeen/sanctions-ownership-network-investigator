# GLEIF enrichment

## Purpose

The targeted GLEIF workflow adds authoritative legal-entity identity fields and
published corporate-accounting parent links to a live OFAC investigation. It is
designed for case-level enrichment rather than bulk ingestion.

## Data mapped

For the selected LEI and any returned parents, the client maps:

- Legal name and other or previous names
- LEI and local registration identifier
- Entity and LEI registration status
- Jurisdiction and legal-form code
- Legal and headquarters addresses
- Direct accounting consolidating parent
- Ultimate accounting consolidating parent
- Relationship status and available dates

Source-prefixed IDs such as `gleif:LEI` prevent collisions with OFAC and
demonstration identifiers.

## Candidate ranking

Name-based searches retrieve more records than the interface displays, score
their legal names, and then return the leading candidates. Ranking considers
normalized legal-name similarity, legal-suffix normalization, spacing variants
such as `JP Morgan` versus `JPMorgan`, and active or issued status as
tie-breakers.

The score is a review aid, not a probability of identity. Closely ranked
candidates trigger an ambiguity warning in the dashboard. Analysts should
confirm the correct LEI using jurisdiction, registration status, local
identifiers, and address. When a verified LEI is already known, use
`--gleif-lei` instead of relying on name ranking.

## Relationship boundary

GLEIF describes Level 2 data as direct and ultimate **accounting consolidating
parent** information. These relationships do not supply an ownership percentage
and do not necessarily represent beneficial ownership or legal control.

The application enforces that boundary in three ways:

1. GLEIF parent links use dedicated relationship types.
2. Their `ownership_pct` is always null.
3. The ownership engine only processes `OWNS` relationships with a numeric
   percentage.

This means GLEIF enrichment can expand the investigative graph and support
follow-up research, but it cannot independently produce an
`ownership_derived_candidate` classification.

## CLI use

Search by name:

```powershell
python main.py --mode live --gleif-enrich --query "ENTITY NAME"
```

Add optional country context:

```powershell
python main.py --mode live --gleif-enrich --country US --query "ENTITY NAME"
```

Use a verified LEI:

```powershell
python main.py --mode live --gleif-enrich --gleif-lei "LEI_HERE" --query "ENTITY NAME"
```

## Analyst checks

- Confirm the selected LEI using name, jurisdiction, registration identifier,
  and address.
- Review LEI registration and entity status.
- Treat a missing parent link as absence of published data, not proof that no
  parent exists.
- Corroborate accounting-parent links with filings or registry evidence.
- Obtain current ownership percentages before applying sanctions ownership
  rules.
- Recheck official sanctions sources and applicable legal guidance before
  making a decision.
