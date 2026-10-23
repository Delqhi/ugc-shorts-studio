#!/usr/bin/env python3
"""Erstellt einen VOLLEN carVertical-Sichtungscut aus V3-Hook + bestehendem Short.

Nur der 0,00–1,50-s-Bildteil wird ersetzt. Die 27,20-s-Original-AAC-Spur
wird ohne Neukodierung übernommen, der restliche Bildteil stammt unverändert
in der Timeline aus dem bisherigen Short (bei der Verkettung neu kodiert).
Dies ist KEIN V1-Creator-Take und kein neuer VO-/Publikumstest.

    .venv/bin/python media/carvertical-ugc/tools/build_cv5_v3_full.py
    .venv/bin/python skill/scripts/qa_preflight.py \
      media/carvertical-ugc/out/short_carvertical_v6_v3.mp4 \
      --storyboard media/carvertical-ugc/storyboard_cv5.json \
      --brief media/carvertical-ugc/brief_cv5.json \
      --json media/carvertical-ugc/qa/cv5_v3_full_preflight.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from render_hook_trials import DURATION, FPS, ROOT, Trial, ffmpeg_exe

SOURCE = ROOT / "out/short_carvertical_v5.mp4"
DEFAULT_OUTPUT = ROOT / "out/short_carvertical_v6_v3.mp4"
SIZE = (1080, 1920)
HOOK_FRAMES = round(DURATION * FPS)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def describe_video(path: Path, *, count_decoded: bool = False) -> tuple[int, float, int]:
    """Reads actual container streams; decoding final video guards against silent truncation."""
    import av

    with av.open(str(path)) as container:
        if len(container.streams.video) != 1:
            raise ValueError(f"{path.name}: genau ein Videostream nötig")
        v = container.streams.video[0]
        rate = v.average_rate
        if (v.codec_context.width, v.codec_context.height) != SIZE or rate != Fraction(FPS, 1):
            raise ValueError(f"{path.name}: 1080x1920/30 fps erforderlich")
        frames = sum(1 for _ in container.decode(video=0)) if count_decoded else v.frames
        duration = float(container.duration / av.time_base) if container.duration is not None else 0
        return frames, duration, len(container.streams.audio)


def audio_packets(path: Path) -> tuple[str, int, float | None]:
    """AAC-Payloads (ohne Container-Header) vergleichen; keine bloßen Metadaten."""
    import av

    with av.open(str(path)) as container:
        if len(container.streams.audio) != 1:
            raise ValueError(f"{path.name}: genau ein Original-Audiostream nötig")
        stream = container.streams.audio[0]
        if stream.codec_context.name != "aac":
            raise ValueError(f"{path.name}: Audiocodec ist nicht AAC")
        h = hashlib.sha256()
        count = 0
        first_pts = None
        for packet in container.demux(stream):
            if packet.size:
                h.update(bytes(packet))
                count += 1
                if first_pts is None and packet.pts is not None:
                    first_pts = float(packet.pts * stream.time_base)
        return h.hexdigest(), count, first_pts


def build(output: Path) -> dict:
    if output.suffix.lower() != ".mp4" or output.resolve() == SOURCE.resolve():
        raise ValueError("Ausgabe muss ein neues .mp4 sein (Original nicht überschreiben)")
    source_frames, duration, source_audio = describe_video(SOURCE)
    if source_frames <= HOOK_FRAMES or source_audio != 1 or not 26.5 <= duration <= 28:
        raise ValueError(f"Originalmaster ist unvollständig: {source_frames} Frames, {duration}s, Audio {source_audio}")

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.stem + ".part.mp4")
    if tmp.is_file():
        raise ValueError(f"Ausstehender Teil-Export existiert bereits: {tmp}")
    ffmpeg = ffmpeg_exe()
    qa = ROOT / "qa"
    qa.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cv5_v3_", dir=qa) as work:
        hook = Path(work) / "cv5_v3_1080_SILENT_PREVIEW.mp4"
        Trial("cv5", "v3", SIZE).render(hook, ffmpeg)
        hook_frames, hook_duration, hook_audio = describe_video(hook, count_decoded=True)
        if hook_frames != HOOK_FRAMES or abs(hook_duration - DURATION) > 0.02 or hook_audio:
            raise ValueError(f"Hook: {hook_frames} Frames, {hook_duration:.2f}s, Audio {hook_audio}")

        # Frame-genau: 45 neue Frames, danach Original ab Frame 45. Das Audio
        # kommt als Stream-Copy von Eingang 1, nie aus der stummen Vorschau.
        graph = ("[0:v]setpts=PTS-STARTPTS[h];"
                 "[1:v]trim=start_frame=45,setpts=PTS-STARTPTS[b];"
                 "[h][b]concat=n=2:v=1:a=0,fps=30,format=yuv420p[v]")
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(hook),
               "-i", str(SOURCE), "-filter_complex", graph,
               "-map", "[v]", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium",
               "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
               "-map_metadata", "1", "-movflags", "+faststart", str(tmp)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode:
                raise RuntimeError(f"FFmpeg-Export fehlgeschlagen: {result.stderr[-1200:]}")
            frames, final_duration, audio_count = describe_video(tmp, count_decoded=True)
            if frames != source_frames or abs(final_duration - duration) > 0.04 or audio_count != 1:
                raise RuntimeError(f"Frame-/Dauer-Check: {frames} statt {source_frames} Frames, "
                                   f"{final_duration:.3f} statt {duration:.3f}s, Audio {audio_count}")
            src_audio = audio_packets(SOURCE)
            dst_audio = audio_packets(tmp)
            if src_audio != dst_audio:
                raise RuntimeError(f"Original-Audio nicht identisch: {src_audio} != {dst_audio}")
            receipt = {
                "format": "screening-cut/v1",
                "source": str(SOURCE.relative_to(ROOT)),
                "source_sha256": sha256(SOURCE),
                "preview_board": "hooks/storyboard_cv5_v3.json",
                "hook_frames": HOOK_FRAMES,
                "handoff_frame": HOOK_FRAMES,
                "body_from": "original frame 45; visual frames are re-encoded",
                "audio": "original AAC packets copied bit-identically, no new VO/ASR",
                "audio_packets": dst_audio[1],
                "audio_payload_sha256": dst_audio[0],
                "first_audio_pts_seconds": dst_audio[2],
                "video_frames": frames,
                "duration_seconds": final_duration,
                "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
                "output_sha256": sha256(tmp),
                "note": "V3 screening candidate, not winner; storyboard_cv5.json describes unchanged body, not edited opening.",
            }
            tmp.replace(output)
            receipt_path = output.with_suffix(".provenance.json")
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return receipt
        except Exception:
            tmp.unlink(missing_ok=True)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        receipt = build(args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Export gesperrt: {exc}\n")
    print(f"Voller Sichtungscut: {receipt['output']} — {receipt['video_frames']} Frames, "
          f"{receipt['duration_seconds']:.2f}s; AAC-Payload bitidentisch. "
          "VO/ASR oder Publikumsergebnis wurden NICHT neu geprüft.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
