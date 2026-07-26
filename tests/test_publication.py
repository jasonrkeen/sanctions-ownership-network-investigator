from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.publication import validate_publication


class PublicationReadinessTests(unittest.TestCase):
    def test_current_project_passes_publication_audit(self):
        self.assertEqual(validate_publication(PROJECT_ROOT), [])

    def test_incomplete_project_reports_required_files(self):
        with tempfile.TemporaryDirectory() as temp:
            issues = validate_publication(Path(temp))

        self.assertTrue(issues)
        self.assertTrue(
            any("Missing required publication file" in issue for issue in issues)
        )


if __name__ == "__main__":
    unittest.main()
