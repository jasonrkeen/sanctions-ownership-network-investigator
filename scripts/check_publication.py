from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sowni.publication import project_version, validate_publication


def main() -> int:
    issues = validate_publication(PROJECT_ROOT)
    if issues:
        print("Publication audit failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"Publication audit passed for version {project_version(PROJECT_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
