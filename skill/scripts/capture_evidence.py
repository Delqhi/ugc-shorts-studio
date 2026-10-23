#!/usr/bin/env python3
"""Belegmaterial + Annotation-Koordinaten einsammeln (Browser-Screenshots).

Aufruf:
  capture_evidence.py <url> --out DIR [--width 430] [--height 932] [--dpr 3]
                       [--browser 9c4eeb57] [--scroll 0,1200,2400] [--text "Kilometerstand"]

Ergebnis in DIR:
  shot-<scroll>.png   Screenshot (Viewport, device pixels)
  evidence.json       Textinventar: jeder sichtbare Textknoten mit Rechteck (CSS-Pixel)
  elements.json       Elementrechtecke (für Annotation-Koordinaten)

Die Rechtecke aus elements.json sind die Annotation-Koordinaten (in CSS-Pixeln des
Viewports). Für den Renderer (Original-Pixel des PNG) gilt: px_png = px_css * dpr.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BSK = os.environ.get("BSK", "bsk")


def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        print(" ".join(args), "\n->", (p.stderr or p.stdout)[-800:], file=sys.stderr)
        raise SystemExit(1)
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", required=True)
    ap.add_argument("--browser", default=os.environ.get("BSK_BROWSER", "9c4eeb57"))
    ap.add_argument("--device", default="iphone-14-pro-max")
    ap.add_argument("--scroll", default="0", help="kommagetrennte Scrollpositionen (CSS px)")
    ap.add_argument("--text", default="", help="nur Elemente mit diesem Textfragment")
    ap.add_argument("--keep", action="store_true", help="Session offen lassen")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sess = run([BSK, "session", "start", "--name", "evidence", "--browser", a.browser]).splitlines()[-1].strip()
    try:
        run([BSK, "emulate", "--session", sess, "--device", a.device])
        run([BSK, "navigate", "--session", sess, a.url])
        time.sleep(9)
        dpr = int(run([BSK, "evaluate", "--session", sess, "window.devicePixelRatio"]))
        print(f"session={sess} dpr={dpr}")

        js = """
(function(){
  var want = %s;
  var out = [];
  document.querySelectorAll('*').forEach(function(e){
    if (e.children.length) return;
    var t = (e.textContent||'').trim();
    if (!t || t.length > 90) return;
    if (want && t.indexOf(want) < 0) return;
    var r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    out.push({text: t, x: Math.round(r.left), y: Math.round(r.top + scrollY),
              w: Math.round(r.width), h: Math.round(r.height)});
  });
  return JSON.stringify(out);
})()
""" % json.dumps(a.text)
        for pos in [int(x) for x in a.scroll.split(",") if x.strip() != ""]:
            run([BSK, "evaluate", "--session", sess, f"window.scrollTo(0,{pos}); 'ok'"])
            time.sleep(2)
            run([BSK, "screenshot", "--session", sess, "--out", str(out / f"shot-{pos}.png"), "--quiet"])
        raw = run([BSK, "evaluate", "--session", sess, js])
        data = json.loads(raw)
        (out / "evidence.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(f"{len(data)} Textknoten -> {out/'evidence.json'}")
        for item in data[:40]:
            print(f"  {item['text'][:52]:54s} x={item['x']:4d} y={item['y']:5d} "
                  f"w={item['w']:4d} h={item['h']:3d}  -> png x={item['x']*dpr} y={item['y']*dpr}")
    finally:
        if not a.keep:
            run([BSK, "session", "stop", "--session", sess], check=False)


if __name__ == "__main__":
    main()
