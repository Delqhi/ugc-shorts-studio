#!/bin/bash
# Schriften fuer den Proof-Short-Renderer beschaffen (OFL, Google Fonts).
# Nicht im Repo committen (Binaerdateien -> pCloud-Regel), deshalb hier nachladen.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)/assets/fonts"
mkdir -p "$DIR"
dl() {  # name url
  if [ -s "$DIR/$1" ]; then echo "  vorhanden: $1"; return 0; fi
  curl -sL -m 120 -o "$DIR/$1" "$2" && echo "  geladen: $1" || { echo "  FEHLER: $1"; return 1; }
}
dl Anton-Regular.ttf "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
dl Montserrat-ExtraBold.ttf "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
ls -la "$DIR"
