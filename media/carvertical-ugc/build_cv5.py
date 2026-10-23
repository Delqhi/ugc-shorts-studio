#!/usr/bin/env python3
"""Baut den carVertical-Danger-Short v5 (Harness: sin-media-proof-short).

- Neuer Hook: "Kein Unfall? Ueber 20.000 Euro Schaden!" (Modal-Chatterbox, ASR-verifiziert)
  ueber dem Unfallbild, mit Rhythmus-Textschlaegen und Stempel.
- Der gepruefte Alt-VO (vo_v5_cut.wav, 22,55 s) haengt mit 0,25 s Pause dahinter.
- Wort-Timings: Hook-Worte + Alt-Worte (um die Verschiebung geschaetzt).
- Storyboard: Szene 1 = danger (Unfallbild), danach die v4-Beweisszenen,
  am Ende die Coupon-Karte USC20.

Aufruf: python3 build_cv5.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FF = "/usr/local/bin/ffmpeg"

HOOK_WAV = ROOT / "tts" / "hook_v5.wav"
HOOK_WORDS = ROOT / "tts" / "hook_v5.words.json"
OLD_WAV = ROOT / "tts" / "vo_v5_cut.wav"
OLD_WORDS = ROOT / "tts" / "vo_v5.words.json"
NEW_WAV = ROOT / "tts" / "vo_cv5.wav"
NEW_WORDS = ROOT / "tts" / "vo_cv5.words.json"
OUT = ROOT / "storyboard_cv5.json"

HOOK_KEEP = 2.95          # Hook-Audio auf 2,95 s beschneiden (letztes Wort endet 2,66 s)
GAP = 0.25                # Beat zwischen Hook und Beweis


def dur(path: Path) -> float:
    out = subprocess.run(["/usr/local/bin/ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def build_audio() -> float:
    """Hook + Pause + Alt-VO -> vo_cv5.wav. Gibt den Shift zurueck."""
    subprocess.run([FF, "-y", "-v", "error", "-i", str(HOOK_WAV), "-t", str(HOOK_KEEP),
                    "-c:a", "pcm_s16le", "/tmp/cv5_hook.wav"], check=True)
    subprocess.run([FF, "-y", "-v", "error", "-i", "/tmp/cv5_hook.wav",
                    "-f", "lavfi", "-t", str(GAP), "-i", "anullsrc=r=48000:cl=stereo",
                    "-filter_complex", "[0:a]aresample=48000[a];[1:a]aresample=48000[b];"
                                      "[a][b]concat=n=2:v=0:a=1[ab]",
                    "-map", "[ab]", "-c:a", "pcm_s16le", "/tmp/cv5_head.wav"], check=True)
    subprocess.run([FF, "-y", "-v", "error", "-i", "/tmp/cv5_head.wav", "-i", str(OLD_WAV),
                    "-filter_complex", "[0:a]aresample=48000[a];[1:a]aresample=48000[b];"
                                      "[a][b]concat=n=2:v=0:a=1[ab]",
                    "-map", "[ab]", "-c:a", "pcm_s16le", str(NEW_WAV)], check=True)
    shift = HOOK_KEEP + GAP
    print(f"VO neu: {NEW_WAV.name} {dur(NEW_WAV):.2f}s (Shift {shift:.2f}s)")
    return shift


def build_words(shift: float) -> float:
    hook = json.loads(HOOK_WORDS.read_text())["words"]
    old = json.loads(OLD_WORDS.read_text())["words"]
    words = [{"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
             for w in hook if w["word"].strip()]
    for w in old:
        if not w["word"].strip():
            continue
        words.append({"word": w["word"], "start": round(w["start"] + shift, 3),
                      "end": round(w["end"] + shift, 3)})
    end = max(w["end"] for w in words)
    NEW_WORDS.write_text(json.dumps({"text": " ".join(w["word"] for w in words),
                                     "words": words}, ensure_ascii=False, indent=1))
    print(f"Wort-Timings: {NEW_WORDS.name} ({len(words)} Woerter, ende {end:.2f}s)")
    return end


def main() -> int:
    shift = build_audio()
    vo_end = build_words(shift)
    # Szenengrenzen: Alt-VO (0/2.45/6.00/12.00/16.55/19.72) + Shift
    b = [round(x + shift, 2) for x in (0.0, 2.45, 6.00, 12.00, 16.55, 19.72)]
    dur_total = round(24.0 + shift, 2)          # 1,45 s Code-Endkarte wie v4
    vo_end = round(min(vo_end, dur_total - 1.0), 2)

    sb = {
        "meta": {
            "fps": 30,
            "duration": dur_total,
            "vo_end": vo_end,
            "out": "out/cv5.mp4",
            "ffmpeg": "/usr/local/bin/ffmpeg",
            "frame_style": "hazard",
            "fonts": {"display": "assets/fonts/Anton-Regular.ttf",
                      "text": "assets/fonts/Montserrat-ExtraBold.ttf"},
            "vo": "tts/vo_cv5.wav",
            "words": "tts/vo_cv5.words.json",
            "code": {"label": "CODE USC20 · −20 %", "from": round(0.60 * vo_end, 2)},
        },
        "scenes": [
            {   # 1: DANGER-HOOK - Unfallbild ab Frame 1
                "kind": "danger",
                "tag": "BEWEIS 01 · UNFALLFOTO",
                "start": 0.0,
                "end": b[1],
                "fit": "card",
                "media": {"path": "m/v4_wreck.png", "unit": 2.4, "span": 1.0,
                          "fx": 560, "fx_to": 820, "fy": 330,
                          "anchor": [0.5, 0.5], "dur": b[1], "punch_step": 0.06,
                          "card_y": 60},
                "ring": {"center": [885, 375], "rx": 205, "ry": 150, "width": 11,
                         "at": 0.50, "dur": 0.35},
                "chops": [[0.00, "KEIN UNFALL?", "white"],
                          [1.06, "20.000 €", "yellow"],
                          [2.16, "SCHADEN", "yellow"]],
                "chop_y": 0.20,
                "stamp": {"text": "WAHNSINN!", "at": 2.70, "x": 0.5, "y": 0.56,
                          "deg": -7, "size": 170},
                "headlines": [],
            },
            {   # 2: Kilometerstand
                "kind": "evidence",
                "tag": "BEWEIS 02 · KILOMETERSTAND",
                "start": b[1],
                "end": b[2],
                "media": {"path": "m/km.png", "span": 1290, "span_to": 1200, "fx": 645,
                          "fy": 620, "anchor": [0.5, 0.33], "dur": b[2] - b[1]},
                "headlines": [[0.00, "DER REPORT SAGT:", "white"],
                              [1.43, "KILOMETER-MANIPULATION", "yellow"]],
                "annotations": [
                    {"type": "rect", "box": [176, 538, 1212, 738], "color": "yellow",
                     "width": 9, "at": 1.45, "dur": 0.8},
                    {"type": "arrow", "from": [1150, 330], "to": [1060, 515], "color": "red",
                     "width": 10, "at": 2.0, "dur": 0.4},
                ],
            },
            {   # 3: KM-Verlauf
                "kind": "evidence",
                "tag": "BEWEIS 03 · KM-VERLAUF",
                "start": b[2],
                "end": b[3],
                "media": {"path": "m/chart.png", "span": 1290, "span_to": 1200, "fx": 645,
                          "fy": 1050, "anchor": [0.5, 0.5], "dur": b[3] - b[2]},
                "headlines": [[0.00, "LETZTER STAND", "white"],
                              [1.18, "75.026 KM", "yellow"],
                              [3.34, "TYPISCH: 153.150 KM", "white"]],
                "annotations": [
                    {"type": "rect", "box": [212, 554, 460, 618], "color": "yellow",
                     "width": 7, "at": 1.18, "dur": 0.6},
                    {"type": "ring", "center": [786, 1446], "rx": 74, "ry": 74, "color": "red",
                     "width": 9, "at": 1.95, "dur": 0.5},
                    {"type": "ring", "center": [786, 1446], "rx": 92, "ry": 92, "color": "yellow",
                     "width": 4, "at": 2.30, "dur": 0.45},
                    {"type": "rect", "box": [712, 600, 924, 656], "color": "yellow",
                     "width": 7, "at": 4.94, "dur": 0.5},
                    {"type": "label", "text": "KILOMETER-RÜCKSTELLUNG", "at_xy": [706, 1446],
                     "at": 2.55, "dur": 0.4, "size": 32, "color": "yellow",
                     "border": "red"},
                ],
            },
            {   # 4: Schaden
                "kind": "evidence",
                "tag": "BEWEIS 04 · ZUSTANDSHISTORIE",
                "start": b[3],
                "end": b[4],
                "media": {"path": "m/cost.png", "span": 1290, "span_to": 1200, "fx": 645,
                          "fy": 1010, "anchor": [0.5, 0.42], "dur": b[4] - b[3]},
                "headlines": [[0.00, "UND DANN DER SCHADEN", "white"],
                              [1.32, "22.501 – 25.000 €", "yellow"],
                              [3.18, "48 % DES FAHRZEUGWERTS", "white"]],
                "annotations": [
                    {"type": "rect", "box": [118, 870, 674, 957], "color": "yellow",
                     "width": 9, "at": 1.32, "dur": 0.7},
                    {"type": "arrow", "from": [1150, 700], "to": [720, 890], "color": "red",
                     "width": 10, "at": 1.7, "dur": 0.4},
                    {"type": "rect", "box": [146, 1094, 980, 1165], "color": "yellow",
                     "width": 7, "at": 3.18, "dur": 0.6},
                ],
            },
            {   # 5: Check
                "kind": "evidence",
                "tag": "CHECK · ZUSAMMENFASSUNG",
                "start": b[4],
                "end": b[5],
                "media": {"path": "m/summary.png", "span": 1290, "fx": 645, "fy": 640,
                          "fy_to": 1160, "anchor": [0.5, 0.35], "dur": b[5] - b[4]},
                "headlines": [[0.09, "2 MINUTEN VIN-CHECK", "white"],
                              [1.89, "BEVOR DU ZAHLST", "yellow"]],
                "annotations": [
                    {"type": "rect", "box": [95, 582, 1195, 646], "color": "yellow",
                     "width": 7, "at": 0.35, "dur": 0.55},
                    {"type": "rect", "box": [95, 933, 1195, 997], "color": "yellow",
                     "width": 7, "at": 1.05, "dur": 0.55},
                    {"type": "rect", "box": [95, 1281, 1195, 1345], "color": "yellow",
                     "width": 7, "at": 1.75, "dur": 0.55},
                ],
            },
            {   # 6: Coupon
                "kind": "coupon",
                "tag": "DEIN RABATT",
                "start": b[5],
                "end": dur_total,
                "code": "USC20",
                "sub": "−20 % AUF DEINEN REPORT",
                "cta": "VIN-Check auf carvertical.com",
                "y": 1120,
                "size": 300,
            },
        ],
    }
    OUT.write_text(json.dumps(sb, ensure_ascii=False, indent=1))
    print(f"Storyboard: {OUT.name}  Szenen: {[round(x, 2) for x in b]} -> {dur_total}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
