---
name: sin-media-proof-short
description: "Baut UGC-/Beleg-Shorts (9:16, 20–40 s) für Marken aus echtem Belegmaterial: Screenshots, Fotos, Report-/Produktseiten, YouTube-Clips. Nutze diesen Skill für jedes UGC-Beleg-Video mit Pflicht-Code und Beleg je Claim."
---

# sin-media-proof-short — UGC-Beleg-Shorts bauen

Erzeugt vertikale Kurzvideos, die wie echte UGC-Werbung wirken, aber **ausschließlich auf
belegtem Material** basieren. Kernidee: Das Video zeigt **Beweis** (Screenshot, Foto, Report),
nicht Behauptung — und die Markierungen, die sich über das Beweismaterial zeichnen, sind die
„Motion Graphics", die aus einem Screenshot-Folgen-Bau ein werbliches Video machen.

Erster Produktionseinsatz: carVertical-UGC (21./22.10.2026, Kampagne carVertical UGC,
Entwurf bei Content Rewards eingereicht). Referenz: `media/` in diesem Repo (drei Beispiel-Shorts).

## 1. Modus bestimmen (zuerst, immer)

| Modus | Wann | Was gilt |
|---|---|---|
| **proof** (Standard) | Es gibt echtes Belegmaterial: Screenshots, Fotos, Produkt-/Reportseiten, Videos | Jede Zahl/Behauptung muss aus dem Material stammen. Pflicht-Code der Marke sichtbar + in der Caption. |
| **synthetic** | Es gibt nur Produkt/Wunsch, kein Material | Nur Stimmung/Erklärung, **keine** Beleg-Claims, keine erfundenen Personen/Produkte, KI-Kennzeichnung nötig. Viele Clip-Kampagnen schließen das per Regel aus → Gate blockiert dann. |

Wenn nur „Produkt + Claims" vorliegen und der Nutzer keine Materialien liefert: **nicht
erfinden.** Erst nach Material fragen oder den synthetischen Modus mit klarer Kennzeichnung
vorschlagen. Das spart eine Freigabe-Runde und verhindert abgelehnte Clips.

## 2. Eingabe-Vertrag (Brief)

Siehe `schema/brief.schema.json`. Minimal:

```json
{
  "brand": "carVertical",
  "product": "Fahrzeughistorie-Report",
  "language": "de",
  "coupon": {"code": "USC20", "discount": "20 %", "on_screen_from_pct": 55},
  "claims": [
    {"text": "75.026 km letzter bekannter Stand", "evidence": "m/km.png", "region": [192,591,1194,717]},
    {"text": "22.501 – 25.000 € Schaden", "evidence": "m/cost.png", "region": [135,876,660,954]}
  ],
  "material": [
    {"kind": "url", "value": "https://viewer.carvertical.com/de/sample.json", "role": "evidence"},
    {"kind": "image", "value": "/pfad/zu/foto.jpg", "role": "hero"},
    {"kind": "video", "value": "/pfad/zu/clip.mp4", "role": "broll"},
    {"kind": "youtube", "value": "https://youtu.be/…", "role": "broll"}
  ],
  "vo": {"script": "…", "voice": "chatterbox-de"},
  "platforms": ["tiktok", "instagram_reels", "youtube_shorts"]
}
```

Jeder Claim braucht `evidence` + `region` (Pixelkoordinaten im Bild). Ohne Beleg → Claim
fliegt raus (Gate G2).

## 3. Ablauf

1. **Material beschaffen** (`scripts/capture_evidence.py`)
   - Webseiten/Reports: echter Browser (bsk) auf Mobil-Emulation (430x932 @3x → 1290x2796),
     Screenshot je relevantem Abschnitt; **Koordinaten der Textstellen mitmessen** (die
     Browser-Elementrechtecke sind die Annotation-Koordinaten).
   - YouTube: `watch`-Skill (Frames + Transcript) oder `yt-dlp` + ffmpeg-Frames.
   - Lokale Bilder/Videos: unverändert übernehmen, Crop-Koordinaten notieren.
2. **Storyboard** (`templates/storyboards/hook-claim-proof-cta.json`)
   Hook → Behauptung → Beweis → Beweis → Lösung/CTA. 5–6 Szenen, 20–40 s.
3. **Voice** — TTS auf **Modal GPU (T4)**: Chatterbox Multilingual, `language_id="de"`.
   **Einmal im Kontext synthetisieren** (satzweise Synthese halluziniert englische Fetzen).
   **ASR-Gate:** das Transkript muss dem Skript entsprechen; Abweichung = neu synthetisieren
   oder schneiden. Rezepte (inkl. Modal-ASR als Ausweichweg, wenn Infisical/Groq klemmt):
   `references/voice.md`.
4. **Render** — `engine/render.py <storyboard.json> <workdir>` (PIL-Frames → ffmpeg-Pipe).
4b. **Preflight (Pflicht, blockierend)** — vor jedem Export:
   `python3 scripts/qa_preflight.py <out.mp4> --storyboard <storyboard.json> --json qa/preflight.json`.
   Geprüft werden Container/Dauer/Lautheit/Untertitel-Platte/erster Frame **und** die
   Storyboard-Geometrie (Headline-Passform inkl. Pop-Skalierung, Code-Zeitpunkt,
   Claim→Beleg). Exit ≠ 0 heißt: nicht weiter, nicht einreichen. WARNs werden gesichtet
   und im Report begründet, nicht ignoriert.
5. **Audio + Export** — `scripts/finalize.sh` (Whooshes an den Szenengrenzen, Two-Pass-
   loudnorm auf −14 LUFS, QA-Sheets).
   **Szenen-Typen:** `danger` (**Hook**: Bild ab Frame 1, Rhythmus-Textschläge `chops`,
   Stempel, optional `fit: card`), `hero` (Bild vollflächig + Chip + Stempel),
   `evidence` (Screenshot/App-Screen mit Annotationen), `clip` (Video-Frame 16:9 als
   Karte + Belegzitat + Zeitstempel-Pille + Quell-Timeline), `coupon` (Code-Karte am Ende).
   **Frame-Stil `hazard` (Standard):** Inhaltsfenster 1032x1728 = **86 %** der Fläche,
   Kopfleiste 88 px, Warnband 24 px ringsum, abgeschrägte Ecken, Blinklichter,
   Headline als Overlay, Untertitel als Band über dem Inhalt.
   **`fit`:** `cover` (Ausschnitt füllt den Inhalt) oder `card` (**das ganze Bild als
   Karte** auf unscharfem Grund — der „FRAMES"-Look: Originalbild vollständig sichtbar).
6. **Sichtprüfung** — `watch`-Skill über die fertige MP4 (Frames je Sekunde) **plus**
   Pixel-Messungen (siehe `references/pitfalls.md`). Nie „blind" abgeben: die ersten drei
   Fehlerstände dieses Skills waren alle nur per Pixel-Messung sichtbar.
7. **Caption** — Pflicht-Code, carVertical-Art Markennennung, Keyword, `#ad`; Claims
   deckungsgleich mit dem Beleg.
8. **Einreichen** (nur wenn eine Marken-Plattform im Spiel ist) — Entwurf einreichen,
   **vorher** prüfen, ob ein alter Entwurf zurückgezogen werden kann (Content Rewards hat
   **kein** Löschen/Zurückziehen → vor dem Einreichen den Stand finalisieren!).

## 4. Harte Gates (`gates/GATES.md`)

| Gate | Regel |
|---|---|
| G1 Beleg | Jeder Claim im Skript hat einen Beleg (Datei + Pixelregion). |
| G2 Code | Pflicht-Code der Marke ab ~55 % der Laufzeit im Bild **und** in der Caption. |
| G3 Wahrheit | Keine Zahl, die nicht im Material steht. Keine erfundenen Personen, Unfälle, Tests. |
| G4 Layout | Kein Text abgeschnitten; Untertitel **mittig auf** der Platte (Pixel-Messung!). |
| G5 Sichtprüfung | Alle Frames gesichtet (watch-Skill), Untertitel-Sync geprüft, Lautheit −14 LUFS. |
| G6 Markenregeln | Logo nicht in der ersten Bildhälfte, kein Musik ohne Lizenz, Dauer 20–40 s. |
| G7 Einreichung | Entwurf/Clip ist final (keine Nachbesserung nach dem Einreichen, wenn die Plattform kein Rückziehen erlaubt). |

## 5. Was der Skill kann — und was nicht

**Kann er heute (2026):** Screenshots von URLs (Browser), Voiceover (TTS, Modal),
Untertitel mit Wort-Timing (ASR), Annotationen/Frames/Headlines (PIL), Schnitt + Loudnorm,
Caption + Entwurf einreichen. Stills/Bild-KI: über `sin-comfyui-image` (GPT Image 2 via
APIMart). Clips: `sin-comfyui-video` (MiniMax H3 auf Modal, kreditbegrenzt).

**Kann er nicht:** echte Menschen vor der Kamera, echte Unfälle/Produkte, Brand-Assets,
Original-Ton, verifizierte Testimonials. Alles, was als „Beweis" im Video erscheint, muss
real sein — sonst ist es ein synthetischer Modus mit Kennzeichnung.

## 6. Qualitätsregeln (aus dem Referenzbau gelernt)

- **Erste Sekunde entscheidet.** Bild ab Frame 1, ein visueller Konflikt (z. B. zerstörtes
  Auto + Behauptung im Rotband), Text poppt, nichts ist „nur Text".
- **Inhalt ≥ 85 % der Fläche.** Kein Layout, bei dem der Beleg hinter einer 350-px-Kopfleiste
  verschwindet — das wirkt wie eine Standbild-Folge. `CH` ist die Inhaltshöhe
  (`CY1 - CY0`, **nicht** `CX1 - CY0` — sonst entstehen leere schwarze Flächen).
- **Der Hook trägt die erste Sekunde.** Bild ab Frame 1, der erste Satz der Stimme **ist**
  der Konflikt (keine Prämisse davor), Rhythmus-Textschläge statt eines langen Fließtexts.
  Ein Hook-Szenen-Kind `danger` mit `chops` ist der Normalfall; `headlines` bleibt leer,
  damit die Schläge die Aussage tragen.
- **Hauptinhalte in Frames.** Fotos/Videos als Karte im Gefahrenzone-Frame (`fit: card`),
  nicht als nackte Vollbild-Fläche — das Originalbild bleibt als Beleg vollständig sichtbar.
- **Der Frame-Stil trägt die Marke.** Absperrband + Sucher-Ecken + Beweis-Etikett (danger),
  Papier (paper), Gerätemock (device) — austauschbar, aber **immer ein Rahmen**, nie eine
  nackte flache Karte.
- **Text ist Tinte, nicht Layer.** Ebenen auf den Alpha-Rand zuschneiden, mit Anker setzen.
  Sonst sitzt alles ~30 px zu tief (das war der teuerste Fehler).
- **Untertitel-Platte aus der Text-Bbox bauen**, nicht fest. Sonst liegt der Text neben
  der Platte.
- **Kein `zoompan`.** Kamera als Subpixel-Box in PIL, sonst wackelt das Bild.
- **Nichts abschneiden.** Das Inhaltsfenster startet bei x0=0, sonst fehlen Überschriften.

Details + alle konkreten Fehler: `references/pitfalls.md`.
Hook-Muster (5 Varianten): `references/hooks.md`.

## 6b. Drei belegte Kurzformen (jeweils mit Storyboard-Template)

| Kurzform | Template | Material | Gate |
|---|---|---|---|
| **Beleg-Short** (Produkt/Report) | `templates/storyboards/hook-claim-proof-cta.json` | Screenshots/Fotos mit belegten Zahlen | G1–G7 |
| **App-Promo** | `templates/storyboards/app-promo.json` | echte App-Screenshots (keine Mockups) | G1–G7 |
| **Video-Highlight** | `templates/storyboards/youtube-highlight.json` | Originalvideo + Transcript | G1–G8 |

**Video-Highlight-Regeln (G8):** Jeder Beat braucht (a) einen Transcript-Span 2–20 s,
(b) das wörtliche Zitat aus diesem Span, (c) den **Original-Frame** an der Span-Position
(dHash-Abweichung ≤ 8, Frame nicht schwarz) und (d) eine daraus berechnete
Zeitstempel-Pille. Modellnoten („spannend") dürfen sortieren, nie freigeben. Bleiben
weniger als 3 Beats übrig, entsteht kein Short.
Transcript-Quellen: `yt-dlp` (AUTO-Untertitel, `--write-auto-subs --sub-langs en`) oder
eigene ASR (Modal/faster-whisper). YouTube-Sperren (403/429) sind kein Grund für
Cookie-Export — der Browser (bsk) liest das Transkript-Panel direkt.

## 7. Dateien

```
engine/render.py            Renderer (JSON-Storyboard -> Frames -> ffmpeg)
engine/subtitle.py          Untertitel (Platte aus Text-Bbox)  [in render.py integriert]
schema/brief.schema.json    Eingabe-Vertrag
templates/storyboards/      hook-claim-proof-cta.json
scripts/capture_evidence.py Screenshots + Koordinaten messen
scripts/asr_gate.py         ASR-Gate fürs Voiceover
scripts/finalize.sh         Mix, Loudnorm, QA-Sheets
scripts/qa_preflight.py     Pflicht-Preflight: MP4 + Storyboard messen, Exit 1 = FAIL
references/pitfalls.md      Fehlerhistorie (wichtigster Teil)
references/voice.md         TTS + ASR auf Modal (inkl. Infisical-Ausweichweg)
references/hooks.md         Hook-Muster
gates/GATES.md              Abnahme-Ledger
```
