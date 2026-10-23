"""Hook-Scoring verhindert Doppelzählungen und vorschnelle Sieger-Meldungen."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "media/carvertical-ugc/tools/score_hooks.py"
spec = importlib.util.spec_from_file_location("hookscore", SCRIPT)
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class ScoreTests(unittest.TestCase):
    def test_duplicate_exports_count_once(self):
        csv = "tested_at,session_id,short,variant,stay,understood,interpretation\n2026-10-23,person1,cv5,v2,yes,yes,48 %\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv"
            path.write_text(csv, encoding="utf-8")
            rows = score.read_rows([path, path])
        self.assertEqual(len(rows), 1)
        self.assertIn("1/1 (100%)", score.summarize(rows))

    def test_small_sample_does_not_announce_winner(self):
        rows = [{"session_id": "one", "short": "cv5", "variant": "v2",
                 "stay": "yes", "understood": "yes"}]
        report = score.summarize(rows)
        self.assertIn("Kein Gewinner", report)
        self.assertNotIn("Nächster Kandidat", report)

    def test_control_beats_new_version(self):
        rows = []
        for n in range(8):
            for variant in ("baseline", "v2", "v3"):
                rows.append({"session_id": str(n), "short": "cv5", "variant": variant,
                             "stay": "yes" if variant == "baseline" else "no", "understood": "yes"})
        self.assertIn("Kontroll-Hook vorn", score.summarize(rows))

    def test_incomplete_controlled_comparison_has_no_winner(self):
        rows = []
        for n in range(8):
            for variant in ("baseline", "v2"):
                rows.append({"session_id": str(n), "short": "cv5", "variant": variant,
                             "stay": "yes", "understood": "yes"})
        self.assertIn("Kein Gewinner", score.summarize(rows))

    def test_invalid_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv"
            path.write_text("short,variant,stay,understood\ncv5,v2,viral,yes\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ungültige"):
                score.read_rows([path])


if __name__ == "__main__":
    unittest.main()
