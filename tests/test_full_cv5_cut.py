"""Regressions: the complete screening cut really contains the new 0.8-s reveal."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "media/carvertical-ugc/tools"
sys.path.insert(0, str(TOOLS))
try:
    import av
    from PIL import Image
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAS_DEPS, "pip install -r media/carvertical-ugc/hooks/requirements.txt")
class FullCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cut = load("build_cv5_v3_full", TOOLS / "build_cv5_v3_full.py")
        cls.qa = load("qa_preflight_full_cut", ROOT / "skill/scripts/qa_preflight.py")
        cls.output = cls.cut.DEFAULT_OUTPUT
        if not cls.output.is_file():
            raise AssertionError(f"Der dokumentierte volle Sichtungscut fehlt: {cls.output}")

    def test_probe_without_ffprobe_checks_real_mp4(self):
        with patch.object(self.qa, "FFPROBE", None):
            info = self.qa.probe(self.output)
        self.assertEqual((info["streams"][0]["width"], info["streams"][0]["height"]), (1080, 1920))
        self.assertEqual(info["streams"][0]["r_frame_rate"], "30/1")
        self.assertEqual(info["streams"][1]["codec_name"], "aac")
        self.assertAlmostEqual(info["format"]["duration"], 27.2, places=2)

    def test_cut_preserves_all_frames_and_original_audio_packets(self):
        source = self.cut.describe_video(self.cut.SOURCE, count_decoded=False)
        output = self.cut.describe_video(self.output, count_decoded=False)
        self.assertEqual(source, output)
        self.assertEqual(self.cut.audio_packets(self.cut.SOURCE), self.cut.audio_packets(self.output))

    def test_cut_on_exact_frames_and_original_body_handoff(self):
        def selected_frames(path: Path):
            wanted = {0, 12, 23, 24, 27, 42, 44, 45, 70}
            result = {}
            with av.open(str(path)) as container:
                for index, frame in enumerate(container.decode(video=0)):
                    if index in wanted:
                        result[index] = frame.to_image().resize((270, 480), Image.Resampling.BILINEAR)
                    if index >= max(wanted):
                        break
            return result

        def diff(a, b):
            from PIL import ImageChops, ImageStat
            return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3

        before, after = selected_frames(self.cut.SOURCE), selected_frames(self.output)
        self.assertGreater(diff(after[23], after[24]), 12, "0,8-s-Reveal fehlt")
        self.assertGreater(diff(before[0], after[0]), 10, "alter Hook nicht ersetzt")
        self.assertGreater(diff(before[44], after[44]), 10, "neuer Hook endet vor Frame 45")
        self.assertLess(diff(before[45], after[45]), 6, "Handoff muss bei Original-Frame 45 liegen")
        self.assertLess(diff(before[70], after[70]), 6, "nach 1,5 s keine geänderten Aussagen")

    def test_refuses_overwrite_of_original(self):
        with self.assertRaisesRegex(ValueError, "Original nicht überschreiben"):
            self.cut.build(self.cut.SOURCE)


if __name__ == "__main__":
    unittest.main()
