# Demonstration walkthrough

This walkthrough gives a reviewer a reproducible 8–10 minute tour. Start with
the fictional dataset so the ownership result is deterministic and does not
depend on network access.

## 1. Run the fictional ownership case

From the project root:

```powershell
python main.py --mode sample --query "Harbor Meridian Trading LLC"
```

Expected classification:

```text
ownership_derived_candidate
```

Explain that the target is not directly designated in the sample. The result is
derived from two loaded majority-ownership edges:

```text
Alex Riverstone -> Meridian Holdings PLC -> Harbor Meridian Trading LLC
```

This is a review candidate, not a legal determination.

## 2. Open the analyst dashboard

```powershell
python -m streamlit run app.py
```

In **Case investigations**:

1. Select the Harbor Meridian case.
2. Review the executive finding and system classification.
3. Open the graph and trace the ownership path.
4. Inspect identity-resolution and sanctions-screening evidence separately.
5. Open **Case workflow**, assign a fictional reviewer, add tags, and save an
   append-only update.
6. Open **Analyst review**, record a disposition with a reason, and show that
   the system classification remains unchanged.

Use fictional reviewer names and notes in screenshots.

## 3. Create a contrasting sample case

Stop Streamlit with `Ctrl+C`, then run:

```powershell
python main.py --mode sample --query "Northstar Maritime Services SA"
```

Restart the dashboard. The case registry should now contain both runs.

In **Case comparison**, select the Harbor Meridian case as the baseline and the
Northstar case as the comparison. Review classification, candidate, graph,
source, indicator, workflow, and analyst-review differences. Download the
comparison JSON.

## 4. Export the case queue

Return to **Case investigations**, apply a status or priority filter, then
download the CSV and JSON queue exports. Explain that routing metadata is
separate from analytical findings.

## 5. Optional live-source demonstration

When network access is available:

```powershell
python main.py --mode live --gleif-enrich --country US --query "JPMorgan Chase & Co."
```

The expected result may change as official data changes. Confirm the selected
LEI and explain that GLEIF accounting-parent links are contextual evidence and
are excluded from percentage-ownership propagation.

## Suggested screenshots

Capture these at a consistent browser size and with no sensitive data:

1. Case queue with two fictional runs and visible filters
2. Harbor Meridian executive finding and ownership graph
3. Source evidence or candidate table
4. Append-only case workflow history
5. Append-only analyst review history
6. Case comparison summary

Recommended repository paths are `docs/images/01-case-queue.png` through
`docs/images/06-case-comparison.png`.

## Reviewer talking points

- Source provenance is retained through the investigation.
- Identity, designation, ownership, contextual control, workflow, and analyst
  judgment are deliberately distinct concepts.
- The fictional case proves multi-level ownership propagation.
- Archived cases and comparison outputs make changes reproducible.
- Limitations are explicit: no automated legal conclusion, no calibrated name
  probability, incomplete ownership coverage, and no production access control.
