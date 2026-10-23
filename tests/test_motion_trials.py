"""Motion-Hooktests: statische Clips dürfen den Pixel-Gate nicht bestehen."""
import importlib.util
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "media/carvertical-ugc/tools"
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load(name):
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAS_PIL, "Pillow ist nur für Motion-Tests nötig")
class MotionTrialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load("render_hook_trials")
        cls.gate = load("check_hook_previews")

    def test_real_creator_variant_cannot_be_faked(self):
        with self.assertRaisesRegex(Exception, "echten Creator-Take"):
            self.renderer.Trial("cv5", "v1", (360, 640))

    def test_static_video_fails_motion_and_reveal(self):
        still = Image.new("RGB", (360, 640), (43, 51, 55))
        frames = {index: still for index in self.gate.INDICES}
        outcome = self.gate.evaluate(frames)
        self.assertEqual(outcome["status"], "FAIL")
        self.assertIn("reveal_767_900ms", outcome["fails"])
        self.assertIn("movement_0_400ms", outcome["fails"])

    def test_each_board_has_visible_changes_before_and_after_cut(self):
        for short in ("cv5", "app", "yt"):
            for variant in ("v2", "v3"):
                with self.subTest(short=short, variant=variant):
                    trial = self.renderer.Trial(short, variant, (360, 640))
                    times = dict(zip(self.gate.INDICES, (0, 0.4, 23/30, 0.9, 1.4)))
                    frames = {i: trial.frame(t) for i, t in times.items()}
                    measured = self.gate.evaluate(frames)
                    self.assertEqual(measured["status"], "PASS", measured)

    def test_preview_duration_is_45_frames(self):
        self.assertEqual(round(self.renderer.DURATION * self.renderer.FPS), 45)
        self.assertEqual(self.gate.INDICES[-1], 42)


if __name__ == "__main__":
    unittest.main()
