#!/usr/bin/env python3
"""Konzept-Check für P1-Hook-Boards; KEIN MP4- oder ASR-Preflight.

Prüft Varianten-Vollständigkeit, 0–1,5-s-Timing/Bewegungsplan, Referenzen auf
bestehende Belege sowie den Übergang zum unveränderten Basisshort. Die echte
Bewegung im Export und die Authentizität der Creator-Aufnahme sind nur durch
Sichtprüfung zu verifizieren.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARDS = ROOT / "hooks"
SHORTS = ("cv5", "yt", "app")
VARIANTS = {"v1": "face_accusation", "v2": "one_number", "v3": "contradiction_flash"}
MOTION = {"handheld", "reframe", "push_in", "hard_cut", "scale_pulse", "focus_reveal", "swipe", "pull_out", "pan"}


class ConceptError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ConceptError(message)


def local_file(name: str, *, required: bool = True) -> Path:
    """Dateipfade im Board sind relativ zum Medienordner, nie aus dem Repo heraus."""
    p = (ROOT / name).resolve()
    require(p.is_relative_to(ROOT), f"Pfad außerhalb des Medienordners: {name}")
    if required:
        require(p.is_file(), f"Quelle fehlt: {name}")
    return p


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    require(header[:8] == b"\x89PNG\r\n\x1a\n" and len(header) == 24,
            f"Beleg ist kein PNG: {path}")
    return struct.unpack(">II", header[16:24])


def validate(board: dict, filename: str) -> list[str]:
    """Liefert noch fehlende Real-Assets; Konzeptfehler werfen ConceptError."""
    short = board.get("short")
    variant = board.get("variant")
    require(short in SHORTS and variant in VARIANTS, f"{filename}: unbekannter Short/Variante")
    require(filename == f"storyboard_{short}_{variant}.json", f"{filename}: Dateiname inkonsistent")
    require(board.get("format") == "ugc-hook-storyboard/v1", f"{filename}: falsches Konzeptformat")
    require(board.get("trigger") == VARIANTS[variant], f"{filename}: Trigger passt nicht zu {variant}")
    require(bool(board.get("hypothesis")) and bool(board.get("truth_guard")),
            f"{filename}: Hypothese oder Wahrheitsgrenze fehlt")
    baseline = json.loads(local_file(board["baseline_storyboard"]).read_text(encoding="utf-8"))
    brief = json.loads(local_file(board["brief"]).read_text(encoding="utf-8"))
    require(board["baseline_storyboard"] == {"cv5": "storyboard_cv5.json", "yt": "storyboard_yt.json", "app": "storyboard_app.json"}[short],
            f"{filename}: falscher Basisshort")
    require(board["brief"] == f"brief_{short}.json", f"{filename}: falscher Brief")
    handoff = float(baseline["scenes"][0]["end"])
    require(abs(board.get("handoff_at", -1) - handoff) < 0.001 and
            board.get("handoff_to") == baseline["scenes"][1]["tag"],
            f"{filename}: Übergabe an den Basisshort falsch")
    claims = {c["text"]: c for c in brief["claims"]}
    source_times = {s["media"]["path"]: s["timestamp"] for s in baseline["scenes"]
                    if s.get("timestamp") and s.get("media")}
    beats = board.get("beats", [])
    require(len(beats) >= 3, f"{filename}: zu wenig eigenständige Beats")
    cursor = 0.0
    found_hook_element = False
    found_motion = False
    pending: set[str] = set()
    for i, beat in enumerate(beats):
        start, end = float(beat["start"]), float(beat["end"])
        require(abs(start - cursor) < 0.001 and end > start,
                f"{filename}: Lücke/Überlappung in Beat {i} bei {start:g} s")
        cursor = end
        require(bool(beat.get("visual")) and bool(beat.get("vo_cue")),
                f"{filename}: Bild oder VO-Cue fehlt in Beat {i}")
        motion = beat.get("motion", "").split(":", 1)
        require(len(motion) == 2 and motion[0] in MOTION and bool(motion[1].strip()),
                f"{filename}: Bewegung bei Beat {i} muss konkret sein")
        if start < 1.5:
            found_motion = True
        images = beat.get("images")
        require(isinstance(images, list) and images, f"{filename}: Bildquelle fehlt in Beat {i}")
        for image in images:
            local_file(image)
        if "face" in beat:
            face = beat["face"]
            require(face.get("kind") in ("real_creator", "source_person"),
                    f"{filename}: kein echter oder belegter Gesichtstyp in Beat {i}")
            asset = face.get("asset", "")
            if face["kind"] == "real_creator":
                require(asset == f"hooks/raw/{short}_creator.mp4",
                        f"{filename}: Creator-Take muss eindeutig zu {short} gehören")
                raw = local_file(asset, required=False)
                if not raw.is_file() or raw.stat().st_size == 0:
                    pending.add(asset)
            else:
                require(asset in images, f"{filename}: Quellperson muss im Originalbild sein")
                local_file(asset)
            if start < 1.5:
                found_hook_element = True
        for text in beat.get("on_screen", []):
            role = text.get("role")
            value = text.get("value", "")
            if role == "editorial_question":
                require(value.endswith("?") and not text.get("brief_claim") and
                        not re.search(r"\d", value),
                        f"{filename}: redaktionelle Frage ohne erfundenen Absender/Zahl schreiben")
            elif role == "verified_claim":
                claim_name = text.get("brief_claim")
                require(claim_name in claims, f"{filename}: unbelegter On-Screen-Claim: {value}")
                require(claim_name in beat.get("brief_claims", []),
                        f"{filename}: On-Screen-Claim ohne VO/Beleg-Zuordnung: {value}")
                claim = claims[claim_name]
                require(claim.get("evidence") in images, f"{filename}: Beleg nicht im selben Beat wie {value}")
                image_path = local_file(claim["evidence"])
                w, h = png_size(image_path)
                x0, y0, x1, y1 = claim["region"]
                require(0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h,
                        f"{filename}: Belegregion für {value} liegt nicht im Quellbild")
                # Bei Zahlen-Hooks muss wenigstens die sichtbare Zahl im Beleg-Claim stehen.
                for number in re.findall(r"\d[\d.,]*", value):
                    require(number in claim_name, f"{filename}: Zahl {number} nicht im Brief-Claim")
                if start < 1.5 and re.search(r"\d", value):
                    found_hook_element = True
            else:
                raise ConceptError(f"{filename}: unbekannte Textrolle {role}")
        for claim_name in beat.get("brief_claims", []):
            require(claim_name in claims, f"{filename}: VO/Beleg-Zuordnung fehlt: {claim_name}")
            require(claims[claim_name]["evidence"] in images,
                    f"{filename}: VO-Beleg für Beat {i} nicht im Bild: {claim_name}")
        if short == "yt":
            require(bool(beat.get("source_time")), f"{filename}: Quellzeit für Highlight fehlt")
            require(any(source_times.get(image) == beat["source_time"] for image in images),
                    f"{filename}: Quellzeit passt zu keinem verwendeten Originalframe")
    require(abs(cursor - handoff) < 0.001,
            f"{filename}: letzte Einstellung endet nicht am Body-Handoff {handoff:g} s")
    require(found_motion and found_hook_element,
            f"{filename}: bis 1,5 s Bewegung + Gesicht oder belegte Zahl nötig")
    if variant == "v1":
        require(beats[0].get("face", {}).get("kind") == "real_creator",
                f"{filename}: V1 muss ab Frame 1 einen echten Creator zeigen")
    elif variant == "v2":
        texts = beats[0].get("on_screen", [])
        require(len(texts) == 1 and texts[0].get("role") == "verified_claim" and
                re.search(r"\d", texts[0].get("value", "")),
                f"{filename}: V2 muss in Frame 1 genau eine belegte Zahl ohne Zusatztext haben")
    else:
        require(any(t.get("role") == "editorial_question" for t in beats[0].get("on_screen", [])),
                f"{filename}: V3 muss mit offener Frage statt fingierter Behauptung öffnen")
        require(abs(beats[1]["start"] - 0.8) < 0.001 and
                beats[1]["motion"].startswith("hard_cut:"),
                f"{filename}: V3 braucht den visuellen Konter bei 0,8 s")
    return sorted(pending)


def run(strict_assets: bool = False) -> int:
    wanted = {f"storyboard_{s}_{v}.json" for s in SHORTS for v in VARIANTS}
    files = {p.name: p for p in BOARDS.glob("storyboard_*.json")}
    errors = [f"fehlt: {n}" for n in sorted(wanted - files.keys())]
    errors += [f"unerwartetes Board: {n}" for n in sorted(files.keys() - wanted)]
    pending: set[str] = set()
    valid_count = 0
    for name in sorted(wanted & files.keys()):
        try:
            missing = validate(json.loads(files[name].read_text(encoding="utf-8")), name)
            pending.update(missing)
            valid_count += 1
            print(f"  OK       {name} (Konzept/Timing/Belegverweise)")
        except (ConceptError, KeyError, ValueError, TypeError) as exc:
            errors.append(f"{name}: {exc}")
    for error in errors:
        print(f"  FEHLER   {error}")
    for asset in sorted(pending):
        print(f"  OFFEN    echter Creator-Take: {asset}")
    print(f"Konzept-Check: {valid_count}/{len(wanted)} validiert; "
          f"{len(pending)} Creator-Assets ausstehend.")
    print("MP4-/Audio-/ASR-Preflight: NICHT gelaufen. Ein Konzept-OK ist keine Export-Freigabe.")
    return 1 if errors or (strict_assets and pending) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-assets", action="store_true",
                        help="ausstehende echte Creator-Takes als Fehler behandeln")
    args = parser.parse_args()
    raise SystemExit(run(strict_assets=args.strict_assets))
