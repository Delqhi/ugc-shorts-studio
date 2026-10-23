#!/usr/bin/env python3
"""qa_preflight.py — misst die fertige MP4 und das Storyboard, bevor eingereicht wird.

Zwei Prüfebenen, absichtlich getrennt:

  MP4-Ebene       Container, Dauer, Lautheit, Untertitel-Platte, erster Frame.
                  Misst das *Ergebnis*, nicht den Renderer — überlebt jede
                  Änderung an engine/render.py.
  Storyboard-Ebene  Headline-Passform inklusive Pop-Skalierung, Szenen-Zeitleiste,
                  Code-Zeitpunkt, Claim->Beleg. Fängt Layoutfehler *vor* dem Render.

Aufruf:
    python3 scripts/qa_preflight.py out/short.mp4 --storyboard storyboard.json
    python3 scripts/qa_preflight.py out/short.mp4 --brief brief.json --asr
    python3 scripts/qa_preflight.py out/short.mp4 --json qa/preflight.json

Exit: 0 = alle Checks PASS/WARN, 1 = mindestens ein FAIL, 2 = Aufruffehler.
Grundsätze: keine stillen Skips (jeder Skip steht mit Grund im Report), keine
Heuristik ohne gemessene Zahl im Detailtext.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

W, H, FPS = 1080, 1920, 30
SUBTITLE_BAND = (1470, 1770)
HEAD_TOP, HEAD_BOTTOM = 60, 320
POP_SCALE = 1.16          # render.py: sc = 1.0 + 0.16 * ...
HEAD_X, HEAD_MAX_W = 34, 1012
EDGE_TOL = 4             # px, die ein Glyph höchstens an den Rand darf

FFMPEG = next((p for p in (shutil.which("ffmpeg"), "/usr/local/bin/ffmpeg",
                           "/opt/homebrew/bin/ffmpeg") if p and Path(p).exists()), None)
FFPROBE = next((p for p in (shutil.which("ffprobe"), "/usr/local/bin/ffprobe",
                            "/opt/homebrew/bin/ffprobe") if p and Path(p).exists()), None)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, cid: str, status: str, detail: str) -> None:
        self.checks.append({"id": cid, "status": status, "detail": detail})
        if status != "PASS":
            print(f"  {status:4s} {cid}: {detail}")

    def fail(self, cid: str, detail: str) -> None:
        self.add(cid, "FAIL", detail)

    def warn(self, cid: str, detail: str) -> None:
        self.add(cid, "WARN", detail)

    def ok(self, cid: str, detail: str) -> None:
        self.add(cid, "PASS", detail)

    def skip(self, cid: str, reason: str) -> None:
        self.add(cid, "SKIP", reason)

    @property
    def failed(self) -> bool:
        return any(c["status"] == "FAIL" for c in self.checks)

    def dump(self, path: Path, extra: dict | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "checks": self.checks, "failed": self.failed}
        if extra:
            payload.update(extra)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


# --------------------------------------------------------------------------- #
# MP4 checks
# --------------------------------------------------------------------------- #
def probe(path: Path) -> dict:
    code, out, err = run([FFPROBE, "-v", "error", "-show_streams", "-show_format",
                          "-of", "json", str(path)])
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {err.strip()[:300]}")
    return json.loads(out)


def check_container(info: dict, rep: Report, min_d: float, max_d: float) -> None:
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        rep.fail("mp4.video", "kein Videostream")
        return
    if (v["width"], v["height"]) != (W, H):
        rep.fail("mp4.size", f"{v['width']}x{v['height']} statt {W}x{H}")
    else:
        rep.ok("mp4.size", f"{W}x{H}")

    num, _, den = v.get("r_frame_rate", "0/1").partition("/")
    fps = float(num) / float(den or 1)
    if abs(fps - FPS) > 0.01:
        rep.warn("mp4.fps", f"{fps:g} fps statt {FPS}")
    else:
        rep.ok("mp4.fps", f"{FPS} fps")

    dur = float(info.get("format", {}).get("duration") or v.get("duration") or 0)
    if dur < min_d or dur > max_d:
        rep.fail("mp4.duration", f"{dur:.2f}s außerhalb {min_d:g}–{max_d:g}s")
    else:
        rep.ok("mp4.duration", f"{dur:.2f}s")

    if a is None:
        rep.fail("mp4.audio", "kein Audiostream — Voiceover fehlt")
    else:
        rep.ok("mp4.audio", f"{a.get('codec_name', '?')} {a.get('channels', '?')}ch")


def check_loudness(path: Path, rep: Report, target: float = -14.0, tol: float = 1.5,
                   peak_max: float = -1.0) -> None:
    code, _, err = run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if code != 0 or not m:
        rep.skip("audio.loudness", "loudnorm lieferte kein JSON")
        return
    data = json.loads(m[-1])
    try:
        i = float(data["input_i"])
        tp = float(data["input_tp"])
    except (KeyError, ValueError):
        rep.skip("audio.loudness", f"unlesbare Werte: {data}")
        return
    if abs(i - target) > tol:
        rep.fail("audio.loudness", f"{i:.1f} LUFS statt {target:.0f} ± {tol:g}")
    else:
        rep.ok("audio.loudness", f"{i:.1f} LUFS")
    if tp > peak_max:
        rep.fail("audio.true_peak", f"{tp:.1f} dBTP über {peak_max:g}")
    else:
        rep.ok("audio.true_peak", f"{tp:.1f} dBTP")


def grab_frame(path: Path, t: float, dest: Path) -> bool:
    code, _, _ = run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
                      "-frames:v", "1", "-y", str(dest)])
    return code == 0 and dest.exists()


def _components(mask):
    """4-Nachbarschaft-Komponenten einer kleinen bool-Matrix -> [(area, bbox)]."""
    h = len(mask)
    w = len(mask[0]) if h else 0
    seen = [[False] * w for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(y, x)]
            seen[y][x] = True
            ys, xs = [], []
            while stack:
                cy, cx = stack.pop()
                ys.append(cy)
                xs.append(cx)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            out.append((len(ys), (min(ys), min(xs), max(ys), max(xs))))
    out.sort(reverse=True)
    return out


def _is_light(rgb):
    r, g, b = rgb[:3]
    if max(r, g, b) > 165 and min(r, g, b) > 85:
        return True
    return r > 190 and g > 150 and b < 125          # gelbe Tinte


def find_plate_ring(frame, band=SUBTITLE_BAND):
    """Untertitel-Platte ueber ihren hellen Rahmen finden.

    Warum nicht ueber die dunkle Flaeche: der Text zerteilt die Platte in
    dunkle Teilstuecke, und ein dunkler Hintergrund (Bokeh, Scrim) liefert
    noch groessere dunkle Flaechen - der Groessen-Ranking traf dann den
    Hintergrund statt der Platte (Fehl-FAIL 2026-10-22, YT-Short).
    Der helle Rahmen der Platte ist eindeutig und renderer-unabhaengig messbar.
    """
    y0, y1 = band
    strip = frame.crop((0, y0, frame.width, y1))
    px = strip.load()
    sw, sh = strip.size
    mask = [[_is_light(px[x, y]) for x in range(sw)] for y in range(sh)]
    best = None
    for area, (a, b, c, d) in _components(mask):
        X0, X1 = b, d
        Y0, Y1 = a + y0, c + y0
        wpx, hpx = X1 - X0, Y1 - Y0
        if not (240 <= wpx <= 960 and 60 <= hpx <= 240):
            continue
        fill = area / float(max(1, wpx * hpx))
        if fill > 0.45:                    # solide Flaeche -> kein Rahmen
            continue
        inset = 10
        ink = ink_bbox(frame, (X0, Y0, X1, Y1), inset=inset)
        if ink is None:
            continue
        # ink_bbox liefert Crop-Koordinaten -> auf Frame-Koordinaten umrechnen
        (ix0, iy0, ix1, iy1), _ = ink
        ink_frame = (X0 + inset + ix0, Y0 + inset + iy0,
                     X0 + inset + ix1, Y0 + inset + iy1)
        best = ((X0, Y0, X1, Y1), (ink_frame, ink[1]))
        break
    return best


def find_plate(frame, band=SUBTITLE_BAND, scale=4):
    """Sucht die dunkle Untertitel-Platte im Band. Gibt (bbox, fill, mean) oder None."""
    y0, y1 = band
    strip = frame.crop((0, y0, W, y1))
    small = strip.resize((strip.width // scale, strip.height // scale))
    px = small.load()
    sw, sh = small.size
    mask = [[max(px[x, y][:3]) < 50 for x in range(sw)] for y in range(sh)]
    for area, (a, b, c, d) in _components(mask)[:3]:
        X0, X1 = b * scale, d * scale
        Y0, Y1 = a * scale + y0, c * scale + y0
        wpx, hpx = X1 - X0, Y1 - Y0
        if not (80 <= wpx <= 920 and 55 <= hpx <= 200):
            continue
        crop = frame.crop((X0, Y0, X1 + 1, Y1 + 1))
        grey = crop.convert("L")
        hist = grey.histogram()
        total = sum(hist) or 1
        mean = sum(i * n for i, n in enumerate(hist)) / total
        fill = (area * scale * scale) / float((wpx + 1) * (hpx + 1))
        if mean < 95 and fill >= 0.5:
            return (X0, Y0, X1, Y1), fill, mean
    return None


def ink_bbox(frame, box, inset=6):
    """Helle/gelbe Tinte innerhalb der Platte (ohne Plattenrand)."""
    x0, y0, x1, y1 = box
    crop = frame.crop((x0 + inset, y0 + inset, x1 + 1 - inset, y1 + 1 - inset)).convert("RGB")
    w, h = crop.size
    px = crop.load()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            light = max(r, g, b) > 165 and min(r, g, b) > 85
            yellow = r > 190 and g > 150 and b < 125
            if light or yellow:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys)), (w, h)


def check_subtitles(path: Path, rep: Report, samples: int, tmp: Path) -> None:
    dur = float(probe(path)["format"]["duration"])
    times = [dur * (i + 0.5) / samples for i in range(samples)]
    plates = 0
    bad = 0
    for idx, t in enumerate(times):
        png = tmp / f"sample_{idx:02d}.png"
        if not grab_frame(path, t, png):
            continue
        from PIL import Image
        try:
            frame = Image.open(png).convert("RGB")
        except (OSError, SyntaxError):
            png.unlink(missing_ok=True)
            continue
        found = find_plate_ring(frame)
        if not found:
            continue
        plates += 1
        box, ink = found
        (ix0, iy0, ix1, iy1), _ = ink
        # Mitte der Tinte gegen die Mitte der Platte (die Platte kommt aus dem Rahmen)
        dx = ((ix0 + ix1) / 2) - ((box[0] + box[2]) / 2)
        dy = ((iy0 + iy1) / 2) - ((box[1] + box[3]) / 2)
        if abs(dx) > 12 or abs(dy) > 8:
            bad += 1
            rep.fail("subs.alignment",
                     f"t={t:.2f}s Text nicht mittig auf der Platte: dx={dx:+.0f}px "
                     f"dy={dy:+.0f}px (Platte {box[2]-box[0]}x{box[3]-box[1]})")
    if plates == 0:
        rep.skip("subs.alignment", f"keine Untertitel-Platte in {samples} Stichproben")
    elif bad == 0:
        rep.ok("subs.alignment", f"{plates} Platten geprüft, Text mittig auf der Platte")


def check_first_frame(path: Path, rep: Report, tmp: Path) -> None:
    png = tmp / "first.png"
    if not grab_frame(path, 0.0, png):
        rep.skip("video.first_frame", "Frame 0 nicht lesbar")
        return
    from PIL import Image
    grey = Image.open(png).convert("L")
    hist = grey.histogram()
    total = sum(hist) or 1
    mean = sum(i * n for i, n in enumerate(hist)) / total
    if mean < 12:
        rep.fail("video.first_frame", f"Frame 0 ist fast schwarz (mean {mean:.0f})")
    else:
        rep.ok("video.first_frame", f"mean {mean:.0f}")


# --------------------------------------------------------------------------- #
# Storyboard checks
# --------------------------------------------------------------------------- #
def font_path(meta: dict, key: str, root: Path) -> Path | None:
    rel = (meta.get("fonts") or {}).get(key) or {
        "display": "assets/fonts/Anton-Regular.ttf",
        "text": "assets/fonts/Montserrat-ExtraBold.ttf",
    }[key]
    for base in (root, Path(__file__).resolve().parent.parent):
        p = base / rel
        if p.exists():
            return p
    return None


def text_width(font, s: str, size: int, stroke: int = 8) -> int:
    from PIL import ImageFont
    ft = ImageFont.truetype(str(font), size)
    b = ft.getbbox(s, stroke_width=stroke)
    return b[2] - b[0]


def fit_size(font, s: str, start: int, max_w: int, stroke: int = 8) -> tuple[int, int]:
    size = start
    while size > 40 and text_width(font, s, size, stroke) > max_w:
        size -= 1
    return size, text_width(font, s, size, stroke)


def check_storyboard(path: Path, rep: Report) -> None:
    sb = json.loads(path.read_text(encoding="utf-8"))
    meta = sb.get("meta", {})
    scenes = sb.get("scenes", [])
    root = path.parent
    disp = font_path(meta, "display", root)

    total = float(meta.get("duration") or 0)
    cursor = 0.0
    for i, sc in enumerate(scenes):
        start = float(sc.get("start", 0))
        end = float(sc.get("end", start))
        if abs(start - cursor) > 0.05:
            rep.fail("sb.timeline", f"Szene {i} beginnt bei {start:.2f}s, vorheriges Ende {cursor:.2f}s")
        if end <= start:
            rep.fail("sb.timeline", f"Szene {i} hat keine Dauer ({start}–{end})")
        cursor = end
    if total and abs(cursor - total) > 0.5:
        rep.fail("sb.duration", f"Szenen enden bei {cursor:.2f}s, meta.duration {total:.2f}s")
    elif total:
        rep.ok("sb.duration", f"{total:.2f}s")

    if disp is None:
        rep.skip("sb.headline_fit", "Display-Font nicht gefunden")
    else:
        overflow = None
        clamped = None
        for i, sc in enumerate(scenes):
            for item in sc.get("headlines", []):
                s = item[1]
                size, w = fit_size(disp, s, 150, HEAD_MAX_W)
                end_at_rest = HEAD_X + w
                end_at_pop = HEAD_X + int(w * POP_SCALE)
                if end_at_rest > W - EDGE_TOL:
                    if overflow is None or end_at_rest > overflow[0]:
                        overflow = (end_at_rest, i, s, size, w)
                elif end_at_pop > W - EDGE_TOL:
                    if clamped is None or end_at_pop > clamped[0]:
                        clamped = (end_at_pop, i, s, size, w, end_at_rest)
        if overflow:
            end, i, s, size, w = overflow
            rep.fail("sb.headline_fit",
                     f"Szene {i} {s!r}: bereits in Ruhe x={end}, "
                     f"{end - (W - EDGE_TOL)}px über dem Rand (max_w={HEAD_MAX_W}).")
        elif clamped:
            end, i, s, size, w, rest = clamped
            rep.warn("sb.headline_pop",
                     f"Szene {i} {s!r}: Pop würde bis x={end} laufen "
                     f"({end - (W - EDGE_TOL)}px über dem Rand) und wird vom Renderer "
                     f"auf x={W - 6} geklemmt (Ruhestand x={rest}). Kein Clipping, "
                     f"aber die Pop-Bewegung endet vorzeitig.")
            rep.ok("sb.headline_fit", "alle Headlines passen in Ruhe")
        else:
            rep.ok("sb.headline_fit", f"alle Headlines passen, auch im Pop ({POP_SCALE}×)")

    code = (meta.get("code") or {})
    if code and total:
        cfrom = float(code.get("from", 0))
        if cfrom < 0.55 * total:
            rep.fail("sb.code_timing", f"Code ab {cfrom:.2f}s = {cfrom / total:.0%} (G2: ≥55 %)")
        else:
            rep.ok("sb.code_timing", f"Code ab {cfrom:.2f}s ({cfrom / total:.0%})")


def check_brief(path: Path, rep: Report) -> None:
    brief = json.loads(path.read_text(encoding="utf-8"))
    claims = brief.get("claims") or []
    if not claims:
        rep.warn("brief.claims", "keine Claims im Brief")
        return
    missing = [c.get("text", "?") for c in claims if not c.get("evidence") or not c.get("region")]
    if missing:
        rep.fail("brief.evidence", f"{len(missing)} Claim(s) ohne evidence/region: {missing[:3]}")
    else:
        rep.ok("brief.evidence", f"{len(claims)} Claims mit Beleg")
    mode = brief.get("mode")
    if mode == "synthetic" and claims:
        rep.fail("brief.mode", "synthetic mit Beleg-Claims — Gate G3")
    elif mode:
        rep.ok("brief.mode", f"Modus {mode}")


def check_asr(path: Path, rep: Report) -> None:
    script = Path(__file__).resolve().parent / "asr_gate.py"
    if not script.exists():
        rep.skip("audio.asr", "asr_gate.py nicht gefunden")
        return
    code, out, err = run([sys.executable, str(script), "--help"])
    if code != 0:
        rep.skip("audio.asr", "asr_gate.py nicht aufrufbar")
        return
    rep.skip("audio.asr", "manuell: asr_gate.py braucht TTS-Credentials; Ergebnis hier nicht geprüft")


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path, nargs="?", help="fertige MP4")
    ap.add_argument("--storyboard", type=Path, help="Storyboard-JSON (Layout-Checks)")
    ap.add_argument("--brief", type=Path, help="Brief-JSON (Claim/Beleg-Checks)")
    ap.add_argument("--json", type=Path, default=Path("qa/preflight.json"), help="Report-Ziel")
    ap.add_argument("--samples", type=int, default=12, help="Frame-Stichproben für Untertitel")
    ap.add_argument("--min-duration", type=float, default=8.0)
    ap.add_argument("--max-duration", type=float, default=45.0)
    ap.add_argument("--asr", action="store_true", help="ASR-Gate versuchen")
    args = ap.parse_args(argv)

    if not args.video and not args.storyboard:
        ap.error("mindestens eine MP4 oder ein Storyboard angeben")
    if (args.video or args.storyboard) and not FFMPEG:
        ap.error("ffmpeg nicht gefunden")

    rep = Report()
    label = args.video.stem if args.video else "storyboard"
    tmp = Path(args.json).parent / f"_preflight_{label}"
    tmp.mkdir(parents=True, exist_ok=True)

    if args.video:
        if not args.video.exists():
            ap.error(f"nicht gefunden: {args.video}")
        info = probe(args.video)
        check_container(info, rep, args.min_duration, args.max_duration)
        check_loudness(args.video, rep)
        check_first_frame(args.video, rep, tmp)
        check_subtitles(args.video, rep, args.samples, tmp)

    if args.storyboard:
        if not args.storyboard.exists():
            ap.error(f"nicht gefunden: {args.storyboard}")
        check_storyboard(args.storyboard, rep)

    if args.brief:
        check_brief(args.brief, rep)
    if args.asr:
        check_asr(args.video, rep)

    rep.dump(args.json)
    fails = [c for c in rep.checks if c["status"] == "FAIL"]
    print(f"preflight    : {args.json}")
    print(f"checks       : {len(rep.checks)} total, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
