#!/usr/bin/env python3
"""Pixel-Gate für die STUMMEN 1,5-s-Hooktests, nicht der Short-Preflight.

Liest die encodierten MP4-Frames (nicht den Renderer) und misst Bildbewegung im
Hook und den echten harten Reveal bei 0,8 s. Besteht ein ruhiges Standbild,
bei dem nur die Metadaten „motion“ sagen, NICHT. Misst keine Emotion/Retention.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / "hooks/previews"
INDICES = (0, 12, 23, 27, 42)   # 0 / 0,4 / 0,77 / 0,9 / 1,4 s bei 30 fps


def difference(a: Image.Image, b: Image.Image) -> float:
    """Mittlere RGB-Pixeldifferenz nach Verkleinerung gegen Codec-Rauschen."""
    a = a.resize((108, 192), Image.Resampling.BILINEAR).convert("RGB")
    b = b.resize((108, 192), Image.Resampling.BILINEAR).convert("RGB")
    return round(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3, 2)


def evaluate(frames: dict[int, Image.Image]) -> dict:
    mean_first = round(sum(ImageStat.Stat(frames[0].resize((108, 192))).mean) / 3, 2)
    before = difference(frames[0], frames[12])
    cut = difference(frames[23], frames[27])
    after = difference(frames[27], frames[42])
    values = {"first_frame_mean": mean_first, "movement_0_400ms": before,
              "reveal_767_900ms": cut, "movement_900_1400ms": after}
    # Konservative Untergrenzen: es geht um einen nicht-statischen Export,
    # nicht um eine erfundene "Viralitätszahl" oder ein perfektes Qualitätsurteil.
    fails = [name for name, value, threshold in (
        ("first_frame_mean", mean_first, 12),
        ("movement_0_400ms", before, 2),
        ("reveal_767_900ms", cut, 9),
        ("movement_900_1400ms", after, 2),
    ) if value < threshold]
    return {"metrics": values, "fails": fails, "status": "FAIL" if fails else "PASS"}


def check_file(path: Path) -> dict:
    try:
        from imageio_ffmpeg import read_frames
    except ImportError as exc:
        raise RuntimeError("pip install imageio-ffmpeg nötig, um *encodierte* MP4-Frames zu prüfen") from exc
    reader = read_frames(str(path), pix_fmt="rgb24")
    try:
        meta = next(reader)
        width, height = meta["size"]
        if height * 9 != width * 16 or abs(meta["fps"] - 30) > 0.1:
            return {"status": "FAIL", "fails": ["format: nicht 9:16 @ 30 fps"], "metrics": meta}
        frames = {}
        count = 0
        for i, data in enumerate(reader):
            count += 1
            if i in INDICES:
                frames[i] = Image.frombytes("RGB", (width, height), data)
        if count != 45 or set(frames) != set(INDICES):
            return {"status": "FAIL", "fails": [f"frames: 45 erwartet, {count} decodiert"],
                    "metrics": {"decoded_frames": count}}
        out = evaluate(frames)
        out["metrics"].update({"decoded_frames": count, "size": [width, height], "fps": meta["fps"]})
        return out
    finally:
        reader.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=PREVIEWS)
    parser.add_argument("--json", type=Path, default=None, help="optional: Messergebnisse als JSON")
    args = parser.parse_args(argv)
    results = {}
    failed = False
    for short in ("cv5", "app", "yt"):
        for variant in ("v1", "v2", "v3"):
            name = f"{short}_{variant}_SILENT_PREVIEW.mp4"
            path = args.dir / name
            if not path.is_file() and variant == "v1":
                result = {"status": "BLOCKED", "fails": ["echter Creator-Take fehlt"], "metrics": {}}
            elif not path.is_file():
                result = {"status": "FAIL", "fails": ["Vorschau fehlt"], "metrics": {}}
            else:
                result = check_file(path)
            results[name] = result
            print(f"{result['status']:7s} {name}: {result['metrics']} {result['fails']}")
            failed |= result["status"] == "FAIL"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"kind": "silent-hook-motion-gate", "results": results,
                                         "failed": failed}, indent=2, ensure_ascii=False) + "\n")
    print("Nur Stumm-Preview-Bewegung gemessen; der separate CV5-V3-Ganzclip hat eigenen MP4-Preflight. ASR/Publikumstest weiter offen.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
