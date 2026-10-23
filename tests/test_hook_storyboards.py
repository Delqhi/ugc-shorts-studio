"""Regressionstests für die neun P1-Konzept-Storyboards (nur stdlib)."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "media/carvertical-ugc/tools/check_hook_storyboards.py"
spec = importlib.util.spec_from_file_location("hookcheck", SCRIPT)
hookcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookcheck)


def board(short, variant):
    name = f"storyboard_{short}_{variant}.json"
    return name, json.loads((hookcheck.BOARDS / name).read_text(encoding="utf-8"))


class HookStoryboardTests(unittest.TestCase):
    def test_nine_distinct_concepts_pass(self):
        for short in hookcheck.SHORTS:
            for variant in hookcheck.VARIANTS:
                with self.subTest(short=short, variant=variant):
                    name, data = board(short, variant)
                    pending = hookcheck.validate(data, name)
                    self.assertEqual(len(pending), 1 if variant == "v1" else 0)
        self.assertEqual(len(list(hookcheck.BOARDS.glob("storyboard_*.json"))), 9)

    def test_unverified_number_fails(self):
        name, data = board("cv5", "v2")
        changed = copy.deepcopy(data)
        changed["beats"][0]["on_screen"][0]["value"] = "99 %"
        with self.assertRaisesRegex(hookcheck.ConceptError, "Zahl 99"):
            hookcheck.validate(changed, name)

    def test_timing_gap_fails(self):
        name, data = board("app", "v3")
        data["beats"][1]["start"] = 0.9
        with self.assertRaisesRegex(hookcheck.ConceptError, "Lücke/Überlappung"):
            hookcheck.validate(data, name)

    def test_no_fake_creator_face(self):
        name, data = board("yt", "v1")
        data["beats"][0]["face"] = {"kind": "source_person", "asset": "yt/yt_12.png"}
        with self.assertRaisesRegex(hookcheck.ConceptError, "V1 muss ab Frame 1 einen echten Creator"):
            hookcheck.validate(data, name)

    def test_widerspruch_reveal_at_08(self):
        name, data = board("cv5", "v3")
        data["beats"][1]["motion"] = "push_in: kein Schnitt"
        with self.assertRaisesRegex(hookcheck.ConceptError, "Konter bei 0,8"):
            hookcheck.validate(data, name)

    def test_missing_proof_image_fails(self):
        name, data = board("yt", "v2")
        data["beats"][0]["images"] = ["yt/yt_12.png"]
        with self.assertRaisesRegex(hookcheck.ConceptError, "Beleg nicht im selben Beat"):
            hookcheck.validate(data, name)


if __name__ == "__main__":
    unittest.main()
