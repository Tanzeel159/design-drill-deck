from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.export_plugin import REQUIRED, export, validate_sources


class PluginZipExportTests(unittest.TestCase):
    def test_sources_are_the_six_trmnl_files(self) -> None:
        files = validate_sources()
        self.assertEqual(tuple(files), REQUIRED)
        self.assertIn("name: Design Drill Deck", files["settings.yml"].decode("utf-8"))
        self.assertIn("polling_url:", files["settings.yml"].decode("utf-8"))
        self.assertIn("daily.json", files["settings.yml"].decode("utf-8"))
        self.assertIn(
            "prompts, daily_picks, difficulty_levels, display_date",
            files["settings.yml"].decode("utf-8"),
        )
        shared = files["shared.liquid"].decode("utf-8")
        self.assertIn("assign feed_empty", shared)
        self.assertIn("default: all_categories", files["settings.yml"].decode("utf-8"))
        self.assertIn("All categories: all_categories", files["settings.yml"].decode("utf-8"))
        self.assertIn("lowercase category key", files["settings.yml"].decode("utf-8"))
        self.assertNotIn("ddd-", files["full.liquid"].decode("utf-8"))

    def test_zip_is_flat_and_importable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "design-drill-deck-trmnl.zip"
            result = export(output)
            self.assertEqual(result["files"], list(REQUIRED))
            self.assertGreater(result["bytes"], 0)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertEqual(names[0], "settings.yml")
                self.assertEqual(names, list(REQUIRED))
                self.assertTrue(all("/" not in name and "\\" not in name for name in names))
                info = archive.getinfo("settings.yml")
                self.assertEqual(info.filename, "settings.yml")
                self.assertFalse(info.is_dir())
                self.assertIn(b"strategy: polling", archive.read("settings.yml"))
                self.assertIn(b"{% assign p", archive.read("shared.liquid"))
                leaked = " ".join(names).lower()
                self.assertNotIn(".env", leaked)
                self.assertNotIn("prompts.json", leaked)
                self.assertNotIn("preview", leaked)


if __name__ == "__main__":
    unittest.main()
