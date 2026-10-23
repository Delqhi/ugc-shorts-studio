# Projekt-State (carvertical-ugc)

Zuletzt aktualisiert: 2026-10-22

## Fertig (diese Pipeline)

| Short | Datei | Länge | Preflight | Status |
|---|---|---|---|---|
| carVertical v5 (Danger-Hook) | `out/short_carvertical_v5.mp4` | 27,20 s | 14 Checks, **0 FAIL** | Fertig, wartet auf Freigabe |
| NVIDIA GTC 2026 (DPCcars) | `out/short_nvidia_robots_v4.mp4` | 31,74 s | 13 Checks, **0 FAIL** | Fertig |
| App-Promo (Einfachhausen) | `out/short_einfachhausen_app_v4.mp4` | 34,24 s | 13 Checks, **0 FAIL** | Fertig |

Alle CPA-norm: 1080x1920, 30 fps, AAC Stereo, −14,1 LUFS, True-Peak ≤ −1,5 dBTP.

## Pipeline-Zusammenfassung

1. Belege sammeln (`skill/scripts/capture_evidence.py`, Browser auf Mobil-Emulation; Koordinaten mitmessen)
2. Brief (`brief_*.json`): Modus `proof`, jeder Claim mit `evidence` + `region`
3. Voice: modal_tts.py (Chatterbox, de) → **ASR-Gate** = wortgenau gegen Skript
4. Storyboard: `build_storyboards.py` / `build_cv5.py` (Anker = VO-Wortstarts)
5. Render: `skill/engine/render.py` (Gefahrenzone-Frame, `danger`/`evidence`/`clip`/`coupon`, `fit` cover|card)
6. Mix: `skill/scripts/finalize.sh` (VO + Szenen-Whooshes + Musikbed, Two-Pass-loudnorm)
7. Preflight: `skill/scripts/qa_preflight.py` — **FAIL blockiert Abgabe**
8. Einzelbild-Sichtprüfung: `tools/peek.py` + `out/qa/<name>/sheet_*.jpg`

## Bekannte Grenzen (ehrlich)

- Jackpot-Anteile fehlen: Technik ✓, Idee-Level ✗ — siehe `docs/BACKLOG.md` Priorität 1–2.
- Das carVertical-Foto ist nur als 2,4x-Upscale vorhanden (Karte statt Cover ist die Folge).
- Die Musik ist ein einfaches Bett; Beat-Quantisierung fehlt (BACKLOG P3).
- Ein Widerspruch im App-Short (Beleg-Bild vs. VO-Zeile 1) ist dokumentiert (BACKLOG P8).

## Was NICHT im Repo ist

Die WAV-Stimmen (regenerierbar via modal_tts.py) und die Rohbäume (`build/`, `build_tmp/`).
Wort-Timings (`tts/*.words.json`) sind committed, Re-Renders brauchen nur Modal + die Medien.
