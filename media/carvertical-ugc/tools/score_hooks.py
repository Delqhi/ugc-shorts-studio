#!/usr/bin/env python3
"""Verdichtet exportierte Hook-Lab-CSVs (keine Viralitäts- oder Signifikanzbehauptung).

    python3 tools/score_hooks.py exports/*.csv --out qa/hook_test_summary.md

Doppelte Exporte derselben anonymen session_id werden nicht doppelt gezählt.
Das ist ein winziger qualitativer Vorabtest; Plattform-Retention folgt separat.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

SHORTS = ("cv5", "app", "yt")
VARIANTS = ("baseline", "v1", "v2", "v3")


def read_rows(paths: list[Path]) -> list[dict]:
    rows = []
    seen = set()
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"short", "variant", "stay", "understood"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"{path}: CSV-Spalten fehlen: {sorted(required - set(reader.fieldnames or []))}")
            for rownum, row in enumerate(reader, start=2):
                short, variant = row["short"], row["variant"]
                if short not in SHORTS or variant not in VARIANTS or row["stay"] not in ("yes", "no") or row["understood"] not in ("yes", "no"):
                    raise ValueError(f"{path}:{rownum}: ungültige Kampagne/Variante/Antwort")
                session = row.get("session_id") or f"{path.resolve()}:{rownum}"   # ältere Exporte
                key = (session, short, variant)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({**row, "session_id": session})
    return rows


def rate(k: int, n: int) -> str:
    return f"{k}/{n} ({k/n:.0%})" if n else "—"


def summarize(rows: list[dict]) -> str:
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["short"], row["variant"])].append(row)
    lines = ["# Hook-Lab: explorativer Blindtest", "",
             f"{len(rows)} eindeutige Bewertungen (session_id + Short + Variante). Keine Signifikanz- oder Viralitätsaussage.", ""]
    for short in SHORTS:
        data = [(v, buckets[(short, v)]) for v in VARIANTS]
        if not any(v for _, v in data):
            continue
        lines += [f"## {short}", "", "| Variante | Weiterschauen | Sofort verstanden |", "|---|---:|---:|"]
        for variant, answers in data:
            n = len(answers)
            stay = sum(a["stay"] == "yes" for a in answers)
            understand = sum(a["understood"] == "yes" for a in answers)
            lines.append(f"| {variant} | {rate(stay, n)} | {rate(understand, n)} |")
        lines.append("")
        adequate = [(sum(a["stay"] == "yes" for a in answers) / len(answers),
                     sum(a["understood"] == "yes" for a in answers) / len(answers), variant)
                    for variant, answers in data if len(answers) >= 8]
        needed = ("baseline", "v2", "v3") + (("v1",) if buckets[(short, "v1")] else ())
        if any(len(buckets[(short, variant)]) < 8 for variant in needed):
            lines.append("**Kein Gewinner:** mindestens acht getrennte, möglichst unabhängige Durchläufe für *jede* getestete Variante und die Kontrolle nötig.")
        else:
            ranked = sorted(adequate, reverse=True)
            top, runner = ranked[:2]
            if top[:2] == runner[:2]:
                lines.append("**Gleichstand:** keine Sieger-Behauptung. Hook-Idee ändern oder mehr Blindtests sammeln.")
            elif top[2] == "baseline":
                lines.append("**Kontroll-Hook vorn:** noch keine neue Variante rechtfertigt einen vollen Re-Render.")
            else:
                lines.append(f"**Nächster Kandidat: {top[2]}.** Nur Explorationssignal – erst VO/ASR und anschließend Plattform-Retention prüfen.")
        lines.append("")
    lines += ["Die Metrik ist eine Antwort nach einmaligem stummen 1,5-s-Sehen. Sie misst nicht Feed-Algorithmus, Audio-Wirkung oder reale Zuschauer-Retention.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path, help="ein oder mehrere Exporte aus Hook Lab")
    parser.add_argument("--out", type=Path, help="Markdown-Report (optional)")
    args = parser.parse_args(argv)
    try:
        text = summarize(read_rows(args.csv))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Fehler: {exc}\n")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
