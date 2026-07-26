from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sowni.ofac import download_sdn_files, load_sdn_files
from sowni.cases import (
    archive_latest_case,
    create_run_id,
    publish_latest_snapshot,
    register_case,
)
from sowni.gleif import GleifClient, GleifError
from sowni.pipeline import run_investigation
from sowni.sample_data import load_sample_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Screen entities and investigate ownership paths."
    )
    parser.add_argument(
        "--mode",
        choices=("sample", "live"),
        default="sample",
        help="Use bundled fictional data or download current OFAC SDN files.",
    )
    parser.add_argument(
        "--query",
        default="Harbor Meridian Trading LLC",
        help="Entity name to investigate.",
    )
    parser.add_argument(
        "--country",
        default="",
        help="Optional ISO country code used to narrow GLEIF name results.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=75.0,
        help="Minimum sanctions-screening name score.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="In live mode, reuse existing data/raw/ofac files.",
    )
    parser.add_argument(
        "--gleif-enrich",
        action="store_true",
        help="In live mode, add GLEIF identity and accounting-parent data.",
    )
    parser.add_argument(
        "--gleif-lei",
        default="",
        help="Optional exact LEI to use instead of selecting the first name result.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.gleif_enrich and args.mode != "live":
        raise SystemExit("--gleif-enrich is available with --mode live.")

    data_dir = PROJECT_ROOT / "data"
    outputs_root = PROJECT_ROOT / "outputs"
    archived_latest = archive_latest_case(outputs_root)
    run_id = create_run_id()
    output_dir = outputs_root / "cases" / run_id
    database_path = output_dir / "investigator.sqlite"
    if archived_latest:
        print(f"Previous case retained: {archived_latest}")

    if args.mode == "sample":
        total_steps = 3
        print(f"[1/{total_steps}] Loading bundled fictional data...")
        entities, aliases, addresses, relationships = load_sample_data(
            data_dir / "sample"
        )
    else:
        total_steps = 5 if args.gleif_enrich else 4
        ofac_dir = data_dir / "raw" / "ofac"
        if not args.skip_download:
            print(f"[1/{total_steps}] Downloading OFAC SDN relational CSV files...")
            download_sdn_files(ofac_dir)
        else:
            print(f"[1/{total_steps}] Reusing downloaded OFAC SDN files...")
        print(f"[2/{total_steps}] Parsing current OFAC files...")
        loaded = load_sdn_files(ofac_dir)
        entities, aliases, addresses = (
            loaded.entities,
            loaded.aliases,
            loaded.addresses,
        )
        relationships = []

    enrichment_summary = None
    if args.gleif_enrich:
        print(
            f"[3/{total_steps}] Retrieving GLEIF identity and "
            "accounting-parent data..."
        )
        try:
            enrichment = GleifClient().enrich(
                name=args.query,
                lei=args.gleif_lei,
                country=args.country,
            )
        except GleifError as exc:
            raise SystemExit(f"GLEIF enrichment failed: {exc}") from exc
        entities.extend(enrichment.entities)
        aliases.extend(enrichment.aliases)
        addresses.extend(enrichment.addresses)
        relationships.extend(enrichment.relationships)
        enrichment_summary = enrichment.summary()
        print(
            f"GLEIF selected: {enrichment.selected_name} "
            f"({enrichment.selected_lei})"
        )
        print(
            "GLEIF parent links are accounting-consolidation relationships and "
            "are excluded from percentage-ownership propagation."
        )

    analysis_step = total_steps - 1
    print(
        f"[{analysis_step}/{total_steps}] Running entity screening and "
        "ownership analysis..."
    )
    result = run_investigation(
        query=args.query,
        entities=entities,
        aliases=aliases,
        addresses=addresses,
        relationships=relationships,
        output_dir=output_dir,
        database_path=database_path,
        mode=args.mode,
        match_threshold=args.threshold,
        enrichment_summary=enrichment_summary,
        run_id=run_id,
    )
    register_case(outputs_root, output_dir, result)
    publish_latest_snapshot(outputs_root, output_dir)
    print(f"[{total_steps}/{total_steps}] Investigation complete.")
    print(f"Classification: {result['classification']}")
    print(f"Target: {(result.get('target_entity') or {}).get('name', 'Unresolved')}")
    print(f"Case: {output_dir}")
    print(f"Brief: {output_dir / 'investigation_brief.md'}")
    pdf_path = output_dir / "investigation_brief.pdf"
    if pdf_path.exists():
        print(f"PDF: {pdf_path}")
    print(f"Graph: {output_dir / 'investigation_graph.json'}")
    print(f"Database: {database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
