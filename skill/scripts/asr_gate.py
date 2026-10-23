#!/usr/bin/env python3
"""ASR-Gate: Das Voiceover muss dem Skript entsprechen.

Warum: TTS halluziniert (englische Fetzen), verwechselt Wörter ("unfallfrei" ->
"unfallsfrei") und verschluckt Zahlen. Ein Transkript, das nicht dem Skript folgt,
ist im Video ein Sachfehler — deshalb wird das Audio vor dem Schnitt geprüft.

Aufruf:
  asr_gate.py --audio tts/vo.wav --script "Der Verkäufer sagt: kein Unfall. 75.000 Kilometer."
  [--words tts/vo.words.json] [--backend groq|whisperx] [--max-wer 0.12]

Exit 0 = passt, Exit 1 = weicht ab (Text/Abweichung auf stdout), Exit 2 = Backend fehlt.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def norm(t: str) -> list[str]:
    t = t.lower().replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ")
    t = re.sub(r"[^a-zäöüß0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.split()


def transcribe_groq(audio: Path) -> tuple[str, list[dict]]:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        r = subprocess.run(["sin-infisical", "get", "GROQ_API_KEY", "--reveal"],
                           capture_output=True, text=True)
        key = r.stdout.strip()
    if not key:
        raise SystemExit("kein GROQ_API_KEY")
    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "a.mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(audio), "-vn",
                        "-ar", "16000", "-ac", "1", "-b:a", "32k", str(mp3)], check=True)
        p = subprocess.run(["curl", "-s", "-m", "120", "https://api.groq.com/openai/v1/audio/transcriptions",
                            "-H", f"Authorization: Bearer {key}", "-F", f"file=@{mp3}",
                            "-F", "model=whisper-large-v3", "-F", "language=de",
                            "-F", "response_format=verbose_json", "-F", "timestamp_granularities[]=word"],
                           capture_output=True, text=True)
    data = json.loads(p.stdout)
    if "text" not in data:
        raise SystemExit(f"ASR-Fehler: {p.stdout[:200]}")
    return data["text"], data.get("words", [])


def transcribe_whisperx(audio: Path) -> tuple[str, list[dict]]:
    cmd = ["whisperx", str(audio), "--model", os.environ.get("WHISPERX_MODEL", "small"),
           "--language", "de", "--output_format", "json"]
    if not shutil.which(cmd[0]):
        raise SystemExit("whisperx nicht installiert")
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(cmd + ["--output_dir", td], check=True, capture_output=True)
        f = next(Path(td).glob("*.json"))
        data = json.loads(f.read_text())
    text = " ".join(s.get("text", "") for s in data.get("segments", []))
    words = [{"word": w.get("word", ""), "start": w.get("start"), "end": w.get("end")}
             for s in data.get("segments", []) for w in s.get("words", [])]
    return text, words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--words", help="Zielpfad für Wort-Timings (JSON)")
    ap.add_argument("--backend", default="groq", choices=["groq", "whisperx"])
    ap.add_argument("--max-wer", type=float, default=0.12)
    ap.add_argument("--language", default="de")
    a = ap.parse_args()

    audio = Path(a.audio)
    try:
        text, words = (transcribe_groq if a.backend == "groq" else transcribe_whisperx)(audio)
    except SystemExit as e:
        print(f"FEHLER: {e}")
        return 2

    want, got = norm(a.script), norm(text)
    sm = difflib.SequenceMatcher(None, want, got)
    wer = 1 - sm.ratio()
    print(f"ASR: {text}")
    print(f"WER = {wer:.3f} (Grenze {a.max_wer})")
    if wer > a.max_wer:
        print("GATE VERLETZT — Skript und Stimme passen nicht zusammen.")
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                print(f"  {tag}: skript={' '.join(want[i1:i2])!r} asr={' '.join(got[j1:j2])!r}")
        return 1
    if a.words:
        Path(a.words).write_text(json.dumps({"text": text, "words": words}, ensure_ascii=False, indent=1))
        print(f"Wort-Timings -> {a.words}")
    print("GATE ERFÜLLT — Stimme entspricht dem Skript.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
