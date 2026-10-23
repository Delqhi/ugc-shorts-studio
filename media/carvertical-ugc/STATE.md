# Projekt-State (carvertical-ugc)

Zuletzt aktualisiert: 2026-10-23

## Fertig (diese Pipeline)

| Short | Datei | Länge | Preflight | Status |
|---|---|---|---|---|
| carVertical v5 (Danger-Hook) | `out/short_carvertical_v5.mp4` | 27,20 s | 14 Checks, **0 FAIL** | Fertig, wartet auf Freigabe |
| NVIDIA GTC 2026 (DPCcars) | `out/short_nvidia_robots_v4.mp4` | 31,74 s | 13 Checks, **0 FAIL** | Fertig |
| App-Promo (Einfachhausen) | `out/short_einfachhausen_app_v4.mp4` | 34,24 s | 13 Checks, **0 FAIL** | Fertig |

Alle drei ursprünglichen MP4s: 1080x1920, 30 fps, AAC Stereo, ca. −14 LUFS. Der carVertical-Originalton hat beim erneuten Messen **−14,1 LUFS / −1,3 dBTP** (Preflight-Grenze −1,0 dBTP); die frühere pauschale Angabe „≤ −1,5 dBTP“ war für diesen Track zu streng/ungenau.

## P1 in Arbeit (23.10.2026)

`hooks/storyboard_{cv5,yt,app}_v{1,2,3}.json`: neun **Konzept**-Storyboards mit drei verschiedenen Triggern pro Short. `tools/check_hook_storyboards.py` prüft den Plan (9/9 gültig). Sechs **stumme** V2-/V3-Hooks (1,5 s) sind mit `tools/render_hook_trials.py --all` abspielbar; `tools/check_hook_previews.py` misst echte Bewegung im MP4 (6/6 PASS). Das lokale Hook Lab stellt sie blind gegen die drei bisherigen Intros.

**Neu, Sichtung – keine Posting-Freigabe:** `out/short_carvertical_v6_v3.mp4` (27,20 s, 816 Frames, 1080×1920/30 fps). Nur Frame 0–44 (V3) neu, ab Frame 45 v5-Body; Original-AAC-Pakete bitidentisch. Echter Report-Cut bei Frame 24 / 0,8 s. Offizieller MP4-Preflight: **15 Checks, 0 FAIL, 1 WARN im alten Body, 1 SKIP ASR**; 45-Frame-Motion-Gate am vollen Export PASS. [Bewertung mit deutlichen Qualitätsgrenzen](../../docs/P1_CV5_FULL_REVIEW.md). Echte V1-Creator-Aufnahmen, neue VO/ASR-Timings, übrige volle Varianten und Zuschauervergleich stehen weiter aus. Die Tabelle oben enthält weiterhin nur die **drei alten, bereits freigegebenen** MP4s.

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
