#!/usr/bin/env python3
"""Schnell-Sichtpruefung: einzelne Frames aus einem Storyboard rendern (ohne Video).

Aufruf:
  python3 tools/peek.py storyboard_app.json . 0.5 2.0 4.5 --out qa/peek_app.png
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import os
from PIL import Image, ImageDraw

SKILL = Path(__file__).resolve().parents[3] / "skill"   # <- Repo-Wurzel/skill
if not SKILL.is_dir():
    SKILL = Path(os.environ.get("SKILL_DIR", "../../skill")).resolve()
spec = importlib.util.spec_from_file_location("rend", SKILL / "engine" / "render.py")
rend = importlib.util.module_from_spec(spec)
sys.modules["rend"] = rend
spec.loader.exec_module(rend)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("workdir")
    ap.add_argument("times", nargs="+", type=float)
    ap.add_argument("--out", default="qa/peek.png")
    ap.add_argument("--cols", type=int, default=3)
    a = ap.parse_args()

    sb = json.loads(Path(a.storyboard).read_text())
    eng = rend.Engine(sb, Path(a.workdir).resolve())
    imgs = []
    for t in a.times:
        frame = Image.new("RGBA", (rend.W, rend.H), (0, 0, 0, 255))
        eng.draw_scene(frame, t)
        eng.subs.draw(frame, t)
        imgs.append((t, frame.convert("RGB")))
    tw = 360
    th = round(tw * rend.H / rend.W)
    cols = min(a.cols, len(imgs))
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(imgs):
        x = (i % cols) * tw
        y = (i // cols) * (th + 26)
        sheet.paste(im.resize((tw, th), Image.Resampling.LANCZOS), (x, y))
        d.text((x + 6, y + th + 4), f"t={t:.2f}s", fill=(255, 220, 90))
    out = Path(a.workdir).resolve() / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    print("geschrieben:", out, sheet.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
