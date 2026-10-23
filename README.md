# UGC Shorts Studio

Beweis-basierte UGC-Shorts (TikTok/Reels/Shorts, 9:16, 30 fps) als **wiederverwendbares Produktionssystem**: Renderengine + Hart-Gates + drei fertige Beispiel-Shorts.

> **Stand: ehrlich.** Das System produziert technisch saubere Shorts (0-FAIL-Preflight, wortgenaue Untertitel, −14 LUFS) — aber **keine viralen Zahlen**. Technische Renderqualität ist gelöst; virale Performance entsteht auf der Ideen-Ebene. Diese Repo-Doku sagt offen, wo die Lecks sind, damit Agenten genau dort ansetzen können (siehe [docs/BACKLOG.md](docs/BACKLOG.md)).

## Was drin ist

| Pfad | Inhalt |
|---|---|
| `skill/` | Der komplette Harness **sin-media-proof-short**: Renderengine, Preflight (Hart-Gates), ASR-Gate, Mix, Fehler-Wissen (`references/pitfalls.md` — 26 belegte Fehlerklassen), Storyboard-Templates |
| `media/carvertical-ugc/` | Die drei fertigen Shorts (MP4, ansehbar im Browser), Storyboards, Generatoren, Briefs, Captions, Wort-Timings, Quell-Medien, QA-Sheets |
| `docs/BACKLOG.md` | Priorisierte Aufgaben für Verbesserungs-Agenten — inklusive der **echten Bremse: Ideen-Ebene** |

## Die drei Shorts (Ergebnis dieser Pipeline)

| Datei | Länge | Was drin ist |
|---|---|---|
| `media/carvertical-ugc/out/short_carvertical_v5.mp4` | 27,2 s | carVertical VIN-Check: „Kein Unfall? Über 20.000 € Schaden!" — Unfallfoto als Karte, Rhythmus-Schläge, Stempel, Report-Belege mit Annotationen, Coupon USC20 |
| `media/carvertical-ugc/out/short_nvidia_robots_v4.mp4` | 31,7 s | NVIDIA GTC 2026 (DPCcars-Quelle): 9 belegte Beats — jeder mit Original-Video-Frame + Zeitstempel-Pille + Quote + Quell-Timeline |
| `media/carvertical-ugc/out/short_einfachhausen_app_v4.mp4` | 34,2 s | App-Promo (Eigenprodukt): 8 belegte App-Screens, Hook „150,90 € / SOFORT / BEZAHLT" |

QA-Sheets (Einzelbilder pro Sekunde) liegen je Short unter `out/qa/<name>/sheet_*.jpg` — für schnelle Sichtprüfung ohne Player.

## Warum noch keine viralen Videos — die wahrheitsgemäße Diagnose

1. **Hook-Konzept, nicht Renderqualität.** Die Hooks sind beweisstark, aber *konzeptionell brav*: Text-Schläge über einem Screenshot. Virale UGC-Hooks sind meist **Gesicht + Stimme + unaufgelöste Spannung** in den ersten 1,5 s — kein Typo-Ballett.
2. **Kein Series-Denken.** Einzel-Posts mit 240–1.400 Views. Viralität kommt aus Folgen-Formaten („Ich prüfe dein Auto, Teil 3") und A/B-Varianten — nicht aus Einzelentwürfen.
3. **Volume fehlt.** Pro Woche wurden 1–2 Shorts *fertiggestellt* statt 5 Konzepte *getestet*. Der Funnel braucht Test-Volume auf Hook-Ebene, nicht Perfektion auf Frame-Ebene.
4. **Stimmt nicht die Karten-Reihenfolge mit der Stimme?** Teilweise (App-Short: Beleg-Bild läuft über einen Satz über Rollen). Klein, aber Retention killt genau so was.
5. **TTS-Stimme ist funktionabel, kein Creator-Voice.** Kein „authentischer" Vibe, keine Atemgeräusche, gleiche Lautstärkekurve überall.

Genau das steht als Arbeit in [docs/BACKLOG.md](docs/BACKLOG.md) — mit konkreten Akzeptanzkriterien und Dateizeigern.

## P1: Hook-Ideentests + ein voller Sichtungscut

Neun [Hook-Storyboards mit Testanleitung](docs/P1_HOOKS.md) liegen vor: je Short ein echter Creator-Take, ein belegter Ein-Zahl-Hook und ein Widerspruchs-Blitz. Der [Konzept-Check](media/carvertical-ugc/tools/check_hook_storyboards.py) validiert 9/9 Timing-/Beleg-Pläne. **Sechs Stummtests** (V2/V3) sind als 1,5-s-MP4s reproduzierbar; das [Hook Lab](media/carvertical-ugc/hooks/review.html) stellt sie blind gegen die drei alten Intros. Der [Pixel-Gate](media/carvertical-ugc/tools/check_hook_previews.py) prüft Bewegung im encodierten Video (6/6 PASS).

**Jetzt vollständiges Video zum Anschauen:** [carVertical V3 · 27,20 s](media/carvertical-ugc/out/short_carvertical_v6_v3.mp4) mit redaktionellem „UNFALLFREI?“-Hook, echtem Report-Reveal bei 0,8 s und **bitidentischer Originaltonspur**. Nur die ersten 1,5 s sind neu geschnitten; ab 1,5 s bleibt der alte Body. Der MP4-Preflight meldet **15 Checks, 0 FAIL** (1 bestehende WARN, **ASR SKIP**), nicht etwa eine neue VO-/Creator-/Retention-Freigabe. [Kritische Bild-/Tonbewertung und offene Punkte](docs/P1_CV5_FULL_REVIEW.md) · [Reproduzierbarer Export](media/carvertical-ugc/tools/build_cv5_v3_full.py). P1 über alle Varianten ist **nicht abgeschlossen**; insbesondere echte V1-Takes und ein Blindtest fehlen.

## Quick-Start (Render eines Shorts)

```bash
# 1. Skill-Umgebung: Pillow + ffmpeg (brew install ffmpeg; pip install pillow)
# 2. Einzelbilder sichten (ohne Video zu rendern):
cd media/carvertical-ugc
python3 tools/peek.py storyboard_cv5.json . 0.15 1.5 2.9 --out qa/peek.png
# 3. Video rendern (Schellkopf-Engine, ~1 s/Frame):
SKILL=../../skill
python3 "$SKILL/engine/render.py" storyboard_cv5.json .
# 4. Audio-Mix (VO + Whooshes an Szenengrenzen + Musik-Bett) → −14 LUFS:
FFPROBE=ffprobe bash "$SKILL/scripts/finalize.sh" \
  --raw out/cv5.mp4 --vo tts/vo_cv5.wav --out out/short_carvertical_v5.mp4 \
  --dur 27.2 --cuts 3.20,5.65,9.20,15.20,19.75,22.92 \
  --music music/641196_10862398-hq.mp3 --music-gain 0.12
# 5. Pflicht-Preflight (13–14 Checks; FAIL = blockiert Abgabe):
python3 "$SKILL/scripts/qa_preflight.py" out/short_carvertical_v5.mp4 \
  --storyboard storyboard_cv5.json --brief brief_cv5.json --json qa/preflight.json
```

TTS/ASR laufen auf Modal GPU (Chatterbox Multilingual, faster-whisper); angeredet über
`media/carvertical-ugc/modal_tts.py` bzw. `modal_asr.py`. Keine Secrets im Repo —
Auth läuft über die lokale `~/.modal.toml`.

## Hart-Gates (kein Short ohne diese Checks)

- **ASR-Gate:** das Transkript der fertigen VO muss wortgenau dem Skript entsprechen (TTS halluziniert).
- **Preflight:** 13–14 Checks (Format, Lautheit, erster Frame, Untertitel-Mittigkeit am Plattenrahmen, Headline-Clamp, Beleg-Mapping aus dem Brief). `FAIL` blockiert die Abgabe.
- **Beleg-Pflicht:** jeder On-Screen-Claim braucht `evidence` + `region` aus dem Brief (kein erfundener Claim).
- Alle Fehlschläge fließen zurück in `skill/references/pitfalls.md` (aktuell 26 Einträge).

## Dateirechte (wichtig)

Siehe [NOTICE.md](NOTICE.md): Fotos aus dem carVertical-**Musterbericht** und Frames aus dem
DPCcars-YouTube-Video sind unter Campaign-Einsatz geteilt und **nicht** zur Weiterverbreitung
freigegeben — die Repo-Medien sind ausschließlich für die Weiterentwicklung dieser Shorts gedacht.
Fonts (Anton, Montserrat, SIL-OFL), Musik (Pixabay CC0) und Eigenprodukt-Material (App-Screens)
dürfen frei weiterverwendet werden.

## License

Code: MIT. Medien: siehe NOTICE.md (nicht weiterverbreiten).
