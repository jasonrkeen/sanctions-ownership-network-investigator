from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.ofac import load_sdn_files


class OfacLoaderTests(unittest.TestCase):
    def test_relational_files_join_by_entity_number(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "sdn.csv").write_text(
                '42,"EXAMPLE ENTITY","Entity","DEMO",-0-,-0-,-0-,-0-,-0-,-0-,-0-,"Primary remarks"\n',
                encoding="utf-8",
            )
            (directory / "alt.csv").write_text(
                '42,7,"aka","EXAMPLE CO",-0-\n', encoding="utf-8"
            )
            (directory / "add.csv").write_text(
                '42,9,"1 Example Road","Example City","Exampleland",-0-\n',
                encoding="utf-8",
            )
            (directory / "sdn_comments.csv").write_text(
                '42,"Additional remarks"\n', encoding="utf-8"
            )
            result = load_sdn_files(directory)
            self.assertEqual(result.entities[0].entity_id, "ofac:42")
            self.assertIn("Additional remarks", result.entities[0].remarks)
            self.assertEqual(result.aliases[0].entity_id, "ofac:42")
            self.assertEqual(result.addresses[0].country, "Exampleland")
            self.assertEqual(len(result.file_hashes), 4)


if __name__ == "__main__":
    unittest.main()
