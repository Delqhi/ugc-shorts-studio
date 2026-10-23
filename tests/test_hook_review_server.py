"""Der öffentliche Live-Preview-Port darf nie Rohmaterial oder Repo-Daten ausliefern."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "media/carvertical-ugc/tools/serve_hook_review.py"
spec = importlib.util.spec_from_file_location("hookserver", SCRIPT)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class HookServerTests(unittest.TestCase):
    def test_whitelist_only_ui_and_expected_videos(self):
        self.assertEqual(len(server.ALLOWED), 2 + 9 + 3)
        self.assertIn("/hooks/review.html", server.ALLOWED)
        self.assertIn("/hooks/previews/cv5_v1_SILENT_PREVIEW.mp4", server.ALLOWED)
        self.assertIn("/out/short_carvertical_v5.mp4", server.ALLOWED)
        self.assertNotIn("/.git/HEAD", server.ALLOWED)
        self.assertFalse(any("raw/" in path or path.endswith(".json") for path in server.ALLOWED))


if __name__ == "__main__":
    unittest.main()
