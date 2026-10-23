#!/usr/bin/env python3
"""Baut den Audio-Mix-Filtergraphen fuer finalize.sh (und prueft ihn).

Warum eigenes Skript: der erste Versuch hatte den Music-Input an Index 12
verwendet, obwohl er Index 11 war -> "Invalid file index 12 in filtergraph".
Der Index wird jetzt an EINER Stelle berechnet und hier geprueft.

Aufruf:
  build_mix_filter.py --raw R.mp4 --vo vo.wav --cuts 1,2,3 --dur 30 \
      [--music bed.mp3 --music-gain 0.12] [--whoosh w.wav] [--ffmpeg /usr/bin/ffmpeg]
Printet:  ARGS=<shell-quotierte ffmpeg-Argumente>
"""
from __future__ import annotations

import argparse
import shlex
import sys


def build(raw: str, vo: str, cuts: list[float], dur: float, music: str | None,
          gain: float, whoosh: str) -> tuple[list[str], str, int]:
    inputs: list[str] = ["-i", raw, "-i", vo]
    filt: list[str] = ["[1:a]aresample=48000,volume=1.05,apad=whole_dur="
                       f"{dur}[voc];"]
    labels: list[str] = ["[voc]"]
    idx = 2
    for c in cuts:
        inputs += ["-i", whoosh]
        ms = int(c * 1000)
        filt.append(f"[{idx}:a]adelay={ms}|{ms},volume=0.13[w{idx}];")
        labels.append(f"[w{idx}]")
        idx += 1
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        filt.append(f"[{idx}:a]aresample=48000,volume={gain},atrim=0:{dur}[m0];")
        labels.append("[m0]")
        idx += 1
    filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first[mix];")
    return inputs, "".join(filt), len(labels)


def check(inputs: list[str], filt: str, n_labels: int) -> list[str]:
    """Prueft, ob jeder [N:a]-Index < Anzahl Inputs ist und der amix-Zahl passt."""
    problems: list[str] = []
    n_in = 0
    i = 0
    while i < len(inputs):
        if inputs[i] == "-i":
            n_in += 1
            i += 2
        else:
            i += 1
    import re
    for m in re.finditer(r"\[(\d+):a\]", filt):
        if int(m.group(1)) >= n_in:
            problems.append(f"Input-Index {m.group(1)} existiert nicht (nur {n_in} Inputs)")
    m = re.search(r"amix=inputs=(\d+)", filt)
    if m and int(m.group(1)) != n_labels:
        problems.append(f"amix=inputs={m.group(1)} passt nicht zu {n_labels} Labels")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--vo", required=True)
    ap.add_argument("--cuts", default="")
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--music")
    ap.add_argument("--music-gain", type=float, default=0.12)
    ap.add_argument("--whoosh", required=True)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    cuts = [float(x) for x in a.cuts.split(",") if x.strip()]
    inputs, filt, n_labels = build(a.raw, a.vo, cuts, a.dur, a.music, a.music_gain, a.whoosh)
    problems = check(inputs, filt, n_labels)
    if problems:
        print("FILTERGRAPH FEHLER:", "; ".join(problems), file=sys.stderr)
        return 1
    if a.check_only:
        print("FILTERGRAPH OK:", filt[:120], "...")
        return 0
    args = " ".join(shlex.quote(x) for x in inputs)
    print(f"ARGS={args}")
    print(f"FILT={filt}")   # unquotiert: wird per sed extrahiert und mit "$FILT" uebergeben
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
