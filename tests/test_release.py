from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.release import DEFAULT_ARCHIVE_ROOT, build_release_archive


class ReleasePackagingTests(unittest.TestCase):
    def test_release_archive_excludes_machine_and_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "release.zip"
            summary = build_release_archive(PROJECT_ROOT, output_path)
            with ZipFile(output_path) as archive:
                members = archive.namelist()
                self.assertIsNone(archive.testzip())

        self.assertGreater(summary["file_count"], 0)
        self.assertTrue(
            all(member.startswith(f"{DEFAULT_ARCHIVE_ROOT}/") for member in members)
        )
        forbidden_fragments = (
            "/.venv",
            "/__pycache__/",
            ".egg-info/",
            "/tmp/",
            ".pyc",
            ".sqlite",
        )
        self.assertFalse(
            any(
                fragment in member
                for member in members
                for fragment in forbidden_fragments
            )
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/src/sowni/dashboard.py",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/src/sowni/cases.py",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/src/sowni/comparison.py",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/CHANGELOG.md",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/SECURITY.md",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/CITATION.cff",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/docs/RELEASE_NOTES_v1.0.0.md",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/.github/pull_request_template.md",
            members,
        )
        self.assertIn(
            f"{DEFAULT_ARCHIVE_ROOT}/outputs/.gitkeep",
            members,
        )
        self.assertNotIn(
            f"{DEFAULT_ARCHIVE_ROOT}/outputs/latest/investigation_result.json",
            members,
        )
        self.assertFalse(
            any(
                member.startswith(f"{DEFAULT_ARCHIVE_ROOT}/outputs/cases/")
                for member in members
            )
        )

    def test_release_builder_rejects_incomplete_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "incomplete"
            root.mkdir()
            with self.assertRaises(ValueError):
                build_release_archive(root, Path(temp) / "release.zip")


if __name__ == "__main__":
    unittest.main()
