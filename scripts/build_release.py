from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sowni.release import build_release_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a clean, portable project release ZIP."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT.parent
        / "sanctions-ownership-network-investigator-mvp.zip",
        help="Destination ZIP path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_release_archive(PROJECT_ROOT, args.output)
    size_kib = summary["size_bytes"] / 1024
    print(
        f"Built {summary['output_path']} with {summary['file_count']} files "
        f"({size_kib:.1f} KiB)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
