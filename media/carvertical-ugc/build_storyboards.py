"""Erzeugt die v3-Storyboards aus den echten Wort-Timings der Voice."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
YT_TOTAL = 246.0

# (Ankerwort, media, zeitstempel, zitat, headline, chip, stamp, punch)
YT_BEATS = [
    ("20", "yt/yt_12.png", "0:12", "you have a camera. oh yeah, don't trip",
     "20 CM ROBOTER", "SIE LAUFEN SELBSTSTÄNDIG", "WAHNSINN", True),
    ("Die wurden", "yt/yt_38.png", "0:35", "you were created on the RTX Spark",
     "RTX SPARK", None, None, False),
    ("Ihre", "yt/yt_66.png", "1:05", "Your parents are called Pollen",
     "POLLEN ROBOTICS", None, None, False),
    ("Die Firma", "yt/yt_46.png", "0:46",
     "Trained you in the cloud on a whole bunch of NVIDIA supercomputers",
     "IN DER CLOUD", None, None, False),
    ("NVIDIA", "yt/yt_112.png", "1:48", "Can you do a somersault?",
     "EIN SALTO?", None, None, False),
    ("Und", "yt/yt_158.png", "2:32", "Don't just run models anymore",
     "NUR AGENTEN", None, None, False),
    ("Was", "yt/yt_200.png", "3:20",
     "we're also extending into the next generation, which is where you guys come in",
     "PHYSICAL AI", None, None, False),
    ("genau", "yt/yt_215.png", "3:35", "Every company in Europe will become an AI company",
     "JEDE FIRMA KI-FIRMA", None, None, False),
    ("Roboter", "yt/yt_240.png", "4:00", "Everybody can build agents",
     "ECHTE PHYSIK", None, None, False),
]

# (Ankerwort, media, headline, stamp)
APP_BEATS = [
    ("Der", "app/s1_receipt.png", "150,90 € SOFORT", "BEZAHLT"),
    ("Jeder", "app/s2_team.png", "WER MACHT WAS?", None),
    ("Termine", "app/s4_gebucht.png", "GEBUCHT. FERTIG.", None),
    ("Dokumente", "app/s3_haus.png", "ALLES AN EINEM ORT", None),
    ("Bezahlt", "app/s5_zahlung.png", "DIREKT BEZAHLT", None),
    ("Und", "app/s7_historie.png", "HAUSAKTE MERKT ALLES", None),
    ("Dazu", "app/s6_passport.png", "EIN HAUSPASS", None),
    ("Eine", "app/s8_oinvoice.png", "STATT FÜNF MAILS", None),
]


def _norm(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


def sent_starts(words, anchors):
    """Satzstarts sequenziell ueber die Ankerwoerter finden (ASR-verstaendlich)."""
    starts, pos = [], 0
    for anchor in anchors:
        parts = [_norm(p) for p in anchor.split()]
        found = None
        for i in range(pos, len(words)):
            if _norm(words[i]["word"]) == parts[0]:
                ok = True
                for k, p in enumerate(parts[1:]):
                    if i + 1 + k >= len(words) or _norm(words[i + 1 + k]["word"]) != p:
                        ok = False
                        break
                if ok:
                    found = i
                    break
        if found is None:
            raise SystemExit(f"Anker '{anchor}' nicht im Transcript gefunden")
        starts.append(words[found]["start"])
        pos = found + 1
    return starts


def _ts(ts):
    m, s = ts.split(":")
    return int(m) * 60 + int(s)


def build(name, words, beats, kind, meta_extra, cta, source_total=None, hook=None):
    starts = sent_starts(words, [b[0] for b in beats])
    end_vo = words[-1]["end"]
    scenes = []
    for i, b in enumerate(beats):
        t0 = starts[i]
        t1 = starts[i + 1] if i + 1 < len(starts) else end_vo
        if i == 0 and hook:
            # DANGER-HOOK: Bild ab Frame 1, Rhythmus-Textschlaege, Stempel
            sc = {"kind": "danger", "start": round(t0, 2), "end": round(t1, 2),
                  "tag": hook.get("tag", "BEWEIS 01")}
            sc.update(hook["scene"])
            sc["media"] = dict(hook["media"], dur=max(0.4, t1 - t0))
            scenes.append(sc)
            continue
        sc = {"kind": kind, "start": round(t0, 2), "end": round(t1, 2),
              "tag": f"BEWEIS {i+1:02d}"}
        if kind == "clip":
            _, media, ts, quote, head, chip, stamp, punch = b
            sc.update({
                # span/span_to = Zoomfaktor (1.0 = ganzes 16:9-Bild); die clip-Szene
                # rechnet cw = breite/span. 1280 wuerde ein 1-Pixel-Fenster ergeben.
                "media": {"path": media, "span": 1.0, "span_to": 1.06, "fx": 640, "fy": 360,
                          "dur": max(0.4, t1 - t0), "punch": punch},
                "fit": "card",                      # Original-Frame als Karte (G8-Beleg)
                "timestamp": ts, "quote": quote,
                "headlines": [[0.0, head, "yellow"]]})
            if source_total:
                sc["source"] = {"duration": source_total, "span": [_ts(ts), _ts(ts) + 9]}
            if chip:
                sc["chip"] = {"text": chip, "at": 0.25, "x": 34, "y": 60, "size": 54}
            if stamp:
                sc["stamp"] = {"text": stamp, "at": 1.25, "x": 0.56, "y": 0.64, "deg": -7, "size": 150}
        else:
            _, media, head, stamp = b
            sc.update({
                "media": {"path": media, "span": 1080, "span_to": 1044, "fx": 540, "fy": 960,
                          "dur": max(0.4, t1 - t0), "punch": i == 0},
                "headlines": [[0.0, head, "yellow"]]})
            if stamp:
                sc["stamp"] = {"text": stamp, "at": 1.25, "x": 0.56, "y": 0.64, "deg": -7, "size": 150}
        scenes.append(sc)
    cta = dict(cta)
    cta["start"] = round(end_vo, 2)
    cta["end"] = round(end_vo + 2.4, 2)
    scenes.append(cta)
    meta = {"fps": 30, "duration": round(scenes[-1]["end"], 2), "out": f"out/{name}.mp4",
            "ffmpeg": "/usr/local/bin/ffmpeg",
            "fonts": {"display": "assets/fonts/Anton-Regular.ttf",
                      "text": "assets/fonts/Montserrat-ExtraBold.ttf"}}
    meta.update(meta_extra)
    (ROOT / f"storyboard_{name}.json").write_text(
        json.dumps({"meta": meta, "scenes": scenes}, ensure_ascii=False, indent=2))
    print(name, "->", len(scenes), "Szenen,", round(meta["duration"], 1), "s")


def main():
    ytw = json.loads((ROOT / "tts/shorts/yt.words.json").read_text())["words"]
    apw = json.loads((ROOT / "tts/shorts/app.words.json").read_text())["words"]

    YT_HOOK = {
        "tag": "BEWEIS 01",
        "scene": {
            "fit": "card",
            "chops": [[0.00, "20 CM", "yellow"], [0.72, "ROBOTER", "white"],
                      [1.84, "SELBSTSTÄNDIG", "yellow"]],
            "chop_y": 0.20,
            "timestamp": "0:12",
            "quote": "you have a camera. oh yeah, don't trip",
            "source": {"duration": YT_TOTAL, "span": [12, 21]},
            "stamp": {"text": "WAHNSINN!", "at": 2.90, "x": 0.5, "y": 0.30,
                      "deg": -7, "size": 170},
            "headlines": [],
        },
        "media": {"path": "yt/yt_12.png", "span": 1.0, "fx": 640, "fy": 360,
                  "card_y": 200, "punch_step": 0.05},
    }
    APP_HOOK = {
        "tag": "BEWEIS 01 · BELEG",
        "scene": {
            "fit": "cover",
            "chops": [[0.00, "150,90 €", "yellow"], [0.80, "SOFORT", "white"],
                      [1.55, "BEZAHLT", "yellow"]],
            "chop_y": 0.68,          # Chops unter die Belegzeilen, nicht darueber
            "pulse": 0.04,
            "headlines": [],
        },
        "media": {"path": "app/s1_receipt.png", "span": 1.0, "fx": 540, "fy": 1020,
                  "punch_step": 0.04},
    }

    build("yt", ytw, YT_BEATS, "clip",
          {"vo": "tts/shorts/yt.wav", "words": "tts/shorts/yt.words.json"},
          {"kind": "coupon", "start": 0, "end": 0, "tag": "VIDEO",
           "code": "GANZES VIDEO", "sub": "NVIDIA GTC 2026 · DPCCARS", "cta": "Link in Bio",
           "y": 720, "size": 110},
          source_total=YT_TOTAL, hook=YT_HOOK)

    build("app", apw, APP_BEATS, "evidence",
          {"vo": "tts/shorts/app.wav", "words": "tts/shorts/app.words.json"},
          {"kind": "coupon", "start": 0, "end": 0, "tag": "EINFACH HAUSEN",
           "code": "EINFACH HAUSEN", "sub": "FÜR HANDWERKER & EIGENTÜMER",
           "cta": "einfachhausen.de", "y": 700, "size": 110},
          hook=APP_HOOK)


if __name__ == "__main__":
    main()
