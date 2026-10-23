#!/usr/bin/env python3
"""Lokaler Hook-Lab-Previewserver; nur Test-UI und die neun nötigen MP4s.

    python3 tools/serve_hook_review.py --port 4173

Bindet 0.0.0.0 für Arena-Live-Preview. Keine Uploads, APIs oder Analytics.
"""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"/hooks/review.html", "/hooks/review.js"}
ALLOWED.update(f"/hooks/previews/{short}_{variant}_SILENT_PREVIEW.mp4"
               for short in ("cv5", "app", "yt") for variant in ("v1", "v2", "v3"))
ALLOWED.update({"/out/short_carvertical_v5.mp4", "/out/short_einfachhausen_app_v4.mp4",
                "/out/short_nvidia_robots_v4.mp4"})


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _allowed(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/hooks/review.html")
            self.end_headers()
            return False
        if path not in ALLOWED:
            self.send_error(404, "Nur Hook-Lab und Kampagnen-Previews werden ausgeliefert")
            return False
        return True

    def do_GET(self):
        if self._allowed():
            super().do_GET()

    def do_HEAD(self):
        if self._allowed():
            super().do_HEAD()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    print(f"Hook Lab: http://0.0.0.0:{args.port}/ (nur UI + MP4s)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
