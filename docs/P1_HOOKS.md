# P1 – neun Hook-Storyboards, noch keine neun neuen Shorts

**Stand 23.10.2026:** Für **jeden** der drei bestehenden Shorts liegen drei **unterschiedliche Ideen-Trigger** als eigene, sekundengenau getaktete [Konzept-Storyboards](../media/carvertical-ugc/hooks/) vor. Alle neun bestehen den **Konzept-Check** (Timing, Bildbewegungsplan, Gesicht/Zahl bis 1,5 s, Quellenverweise, Handoff zum Basisshort). **Sechs davon (V2/V3) sind inzwischen als 1,5-s-Stummtests abspielbar** – mit realem Bild-Cut bei 0,8 s; V1 bleibt ohne echte Creator-Aufnahme gesperrt. Diese stummen Roh-Experimente sind **nicht** der MP4-Preflight: echte VO/ASR, vollständige Shorts und Ausspielung fehlen. Die P1-Abnahme „Preflight 0 FAIL am fertigen Export“ ist **offen**.

Die JSON-Dateien haben absichtlich `format: ugc-hook-storyboard/v1` und `beats` statt `meta/scenes`: **nicht** an `skill/engine/render.py` oder `qa_preflight.py` als fertiges Video-Storyboard übergeben. Sie sind Dreh-/Schnittentscheidungen, keine als renderfertig getarnten Screenshots. Der unveränderte Basisshort übernimmt jeweils nach `handoff_at` (cv5 5,65 s; YT 3,56 s; App 4,58 s).

## Die neun Tests (0,0 s → Konter bei 0,8 s)

| Short | V1: Gesicht + Vorwurf/Frage | V2: **nur eine** Zahl im ersten Frame | V3: Widerspruchs-Blitz |
|---|---|---|---|
| carVertical | [v1](../media/carvertical-ugc/hooks/storyboard_cv5_v1.json): echter Creator hält das Unfallfoto hoch: „Unfallfrei? Glaubst du das?“ → kalkulierte Kosten im Musterbericht | [v2](../media/carvertical-ugc/hooks/storyboard_cv5_v2.json): **48 %** → Bericht zeigt „Bewertung der Reparaturkosten / 48 % des damaligen Fahrzeugwerts“ | [v3](../media/carvertical-ugc/hooks/storyboard_cv5_v3.json): redaktionelle Frage **„UNFALLFREI?“** → Schadenfoto **und** 22.501–25.000 € kalkulierte Kosten |
| NVIDIA/DPCcars | [v1](../media/carvertical-ugc/hooks/storyboard_yt_v1.json): echter Creator reagiert auf Huang + Roboter → Originalframe mit Quellzeit 0:12 | [v2](../media/carvertical-ugc/hooks/storyboard_yt_v2.json): **4** → vier kleine Roboter im Quellframe bei 2:32 (sichtbar nachzählen) | [v3](../media/carvertical-ugc/hooks/storyboard_yt_v3.json): **„NUR SOFTWARE?“** über Huang am Laptop → Originalframe mit echten Bühnenrobotern |
| Einfach Hausen | [v1](../media/carvertical-ugc/hooks/storyboard_app_v1.json): echter Creator fragt nach Zahlung, dreht das Telefon → Beleg „Bezahlt 150,90 €“ | [v2](../media/carvertical-ugc/hooks/storyboard_app_v2.json): **150,90 €** → scharfe Bezahlt-Zeile im echten App-Beleg | [v3](../media/carvertical-ugc/hooks/storyboard_app_v3.json): **„NUR VEREINBART?“** → **„Bezahlt 150,90 €“**, beides im *selben* Beleg |

**Vergleichslogik:** V1 testet menschlichen Blick/Emotion (kein KI-Gesicht), V2 die einzelne belegte Zahl statt Typo-Folge, V3 die offene Frage mit hartem Beleg-Schnitt bei 0,8 s. Alle drei brauchen reale Bewegung in den ersten 1,5 s – Kamera/Hand, Zahl-Punch bzw. Cut. Nicht drei Farbvarianten desselben Templates.

## Wahrheitsgrenzen, bevor jemand schneidet

- **carVertical:** Die 48 % sind *Reparaturkosten relativ zum damaligen Fahrzeugwert*, **kein** Wertverlust. `m/cost.png`, Belegregion `[118,1020,1050,1165]`. „Unfallfrei?“ bleibt eine **Frage des Creators/Publikums**, **kein belegtes Verkäufer-Zitat**: im Material fehlt ein Inserat bzw. Chat. V3-Bubble ohne Absender, Avatar oder vorgetäuschten Screenshot. Ein echtes Verkäufer-Statement kann erst mit Originalbeleg an dessen Stelle treten.
- **NVIDIA:** „4“ ist eine **Bildzählung** in `yt/yt_158.png`, Region `[300,450,1280,720]`, Quellzeit 2:32 – nicht die Anzahl *aller* gezeigten Roboter. Ein Wert wie „20 cm“ wäre in den verfügbaren Brief-Claims nicht belegt; deshalb hier nicht als Zahl-Hook. Originalframes/-zitate weiter mit Quelle und Quellzeit behandeln (G8); die Quote gegen das Originalvideo vor Export nochmals hören.
- **App:** `app/s1_receipt.png` zeigt **vereinbart und bezahlt 150,90 €**, aber **nicht**, wie schnell Geld beim Handwerker ankam. Die Belegregion im Brief wurde auf Pixel `[60,670,1000,975]` des *gespeicherten* 1080×1920-Screens korrigiert (die vorherige Region lag im schwarzen Rand). V3 ist keine fingierte Kunden-Chatnachricht.
- Quellenrechte für Report/YouTube: [NOTICE.md](../NOTICE.md). Echte Creator-Aufnahmen nur mit Einwilligung; **keine KI-Person als „echter Creator“ ausgeben**.

## Motion-First-Hook-Lab: sechs **abspielbare** Stummtests

Das ist kein weiteres Polieren der 27-s-Renderengine: [`render_hook_trials.py`](../media/carvertical-ugc/tools/render_hook_trials.py) rendert ausschließlich die **ersten 45 Frames** (1,5 s) aus den V2-/V3-Boards. Zahl ab Frame 1, reale Bewegung im Bild, harter Reveal bei Frame 24 (0,8 s), anschließend sichtbarer Originalbeleg. Keine erfundene Stimme, kein KI-Gesicht, keine dekorativen Beweis-Claims. Alle sechs Clips sind **stumm**, 720×1280/30 fps und absichtlich *nicht postfertig*:

| carVertical | Einfach Hausen | NVIDIA / DPCcars |
|---|---|---|
| [V2 · 48 %](../media/carvertical-ugc/hooks/previews/cv5_v2_SILENT_PREVIEW.mp4) · [V3 · Unfallfrei?](../media/carvertical-ugc/hooks/previews/cv5_v3_SILENT_PREVIEW.mp4) | [V2 · 150,90 €](../media/carvertical-ugc/hooks/previews/app_v2_SILENT_PREVIEW.mp4) · [V3 · Vereinbart?](../media/carvertical-ugc/hooks/previews/app_v3_SILENT_PREVIEW.mp4) | [V2 · 4](../media/carvertical-ugc/hooks/previews/yt_v2_SILENT_PREVIEW.mp4) · [V3 · Nur Software?](../media/carvertical-ugc/hooks/previews/yt_v3_SILENT_PREVIEW.mp4) |

Das [Hook Lab](../media/carvertical-ugc/hooks/review.html) zeigt pro Short **bisherigen Anfang (Kontrolle), V2, V3** in zufälliger Reihenfolge jeweils einmal stumm für 1,5 s. Danach Daumenstopp, Verstehen und freie Wiedergabe erfassen; Browser speichert lokal, CSV-Export möglich. Keine Plattform-Uploads und keine privaten Testdaten auf einem Server. Für Arena-Live-Preview `tools/serve_hook_review.py` starten (Whitelist: nur UI + neun MP4s; kein Repo-/Secret-Serving).

```bash
python3 -m venv .venv
.venv/bin/pip install -r media/carvertical-ugc/hooks/requirements.txt
.venv/bin/python media/carvertical-ugc/tools/render_hook_trials.py --all
.venv/bin/python media/carvertical-ugc/tools/check_hook_previews.py --json media/carvertical-ugc/qa/hook_motion_metrics.json
python3 media/carvertical-ugc/tools/serve_hook_review.py --port 4173
# Browser: http://localhost:4173/  (in Arena: Live-Preview „Hook Lab“)
# Wenn ein echter Creator-Take unter hooks/raw/cv5_creator.mp4 vorliegt:
.venv/bin/python media/carvertical-ugc/tools/render_hook_trials.py --short cv5 --variant v1
# Danach Seite neu laden; V1 wird automatisch als zusätzlicher Blindtest erkannt.
# CSV-Exporte mehrerer Tester anschließend zusammenführen:
python3 media/carvertical-ugc/tools/score_hooks.py exports/*.csv --out media/carvertical-ugc/qa/hook_test_summary.md
```

`score_hooks.py` entfernt doppelte Exporte derselben anonymen Session. Bei kleinen Stichproben meldet es **keinen Gewinner**; selbst mit genug Antworten bleibt die Rangfolge nur ein Explorationssignal, kein Viralitätsnachweis.

Der Pixel-Gate dekodiert **die MP4** und prüft Frame 0, sichtbare Bewegung vor dem Cut, den Reveal sowie Bewegung danach; hier **6/6 PASS, V1 3× BLOCKED**. Ein Standbild würde FAIL liefern. **Grenze:** Die Belegquellen sind Standbilder – Pan, Zahl-Punch und Cut sind echte Pixelbewegung, aber kein gefilmter Mensch und kein Original-Bewegtbild. Ohne echten Creator-Take bzw. konkreten `/motion`-Referenzclip wird hier keine Gleichwertigkeit mit dessen Ästhetik behauptet. Das belegt *nicht* Watchtime, Creator-Emotion oder 0-FAIL-Short-Preflight. Die sechs kleinen Previews unter `hooks/previews/` sind bewusst für die Schnellansicht im Repo enthalten und jederzeit reproduzierbar; Rechte an den Quellen siehe NOTICE.md. Falls `skill/assets/fonts` fehlen, nimmt der Preview-Renderer einen lokalen Bold-Fallback (Originalfont optional über `skill/scripts/setup_fonts.sh`).

## Heute Abend schnell testen (ohne Exportversprechen)

1. carVertical zuerst: **V1** als echten ~6-s-Smartphone-Take aufnehmen (`media/carvertical-ugc/hooks/raw/cv5_creator.mp4`, 9:16, Gesicht ab Frame 1, Foto sichtbar, keine gespielte Verkäufer-Aussage). `hooks/raw/` ist absichtlich nicht versioniert. Für App und YT analog `app_creator.mp4`, `yt_creator.mp4`. Natürlich sprechen, nicht monotone TTS-Pausen imitieren.
2. Zuerst im Hook Lab **bisherigen Hook gegen V2/V3** pro Short vergleichen. V1 erst nach Aufnahme des echten Creator-Takes als dritten Neuentwurf in den Test aufnehmen. Clip an **0,0 / 0,8 / 1,5 s** sichten: Kann eine unvoreingenommene Person den Konflikt bei stummem Autoplay erfassen? Sind Zahl/Gesicht wirklich sichtbar und bewegt sich das Bild statt nur ein Etikett? Danach die `vo_cue`-Zeilen zum Favoriten probeweise sprechen. Das ist ein **Ideentest**, keine gemessene Virality-Prognose.
3. **Blindes Mini-Panel** (z. B. fünf bis zehn Personen der Zielgruppe): dieselben 1,5-s-Rough-Cuts in zufälliger Reihenfolge, ohne Varianten-Namen und zuerst stumm zeigen. Pro Person/Variante `weitergeschaut? (ja/nein)` und `Konflikt in eigenen Worten erkannt? (ja/nein)` notieren. Primär die **Weitersehen-Quote**, sekundär korrekt verstandene Aussage vergleichen; bei so kleiner Stichprobe keine Signifikanz oder Viralität behaupten. Beispiel-Log: `cv5,v2,8/10,6/10,„48 % wovon?“,Testdatum`. Bei Gleichstand nur den schwachen Hook neu formulieren, nicht neun Shorts fertig rendern. Keine drei Drafts eines Content-Rewards-Accounts zum Test hochladen (P5).
4. Nur den Gewinner für ein volles Short vertonen: neues Hook-VO bis zum `handoff_at` aufnehmen/synthetisieren, zusammen mit dem Body **ASR-Worttimings neu prüfen** und den Original-Body synchron halten. Für YT/App fehlen zudem die im bisherigen Storyboard referenzierten `tts/shorts/{yt,app}.words.json` im Checkout; sie müssen vor einem Engine-Render rekonstruiert werden. Die Original-WAVs fehlen bei allen dreien. Nichts durch erfundene Wort-Timings „bestehen“ lassen.
5. Erst am **fertigen Varianten-MP4** `skill/scripts/qa_preflight.py <video> --storyboard <renderfähiges Storyboard> --brief <brief> --json <Report>` laufen lassen; danach die ersten **45 Frames** sichten und Bildbewegung/Gesicht oder Zahl 0–1,5 s manuell bestätigen. Das Tool misst MP4/Audio/Layout, **nicht** Virality oder authentische Gesichtsvideos. Ohne 0 FAIL und Bild-Sichtung keine Abnahme/kein Posting.

Konzept-Check (keine Zusatzpakete erforderlich):

```bash
python3 media/carvertical-ugc/tools/check_hook_storyboards.py
python3 -m unittest discover -s tests -v
# Wenn Creator-Takes vorhanden sein müssen: fehlende Takes => Exit 1
python3 media/carvertical-ugc/tools/check_hook_storyboards.py --strict-assets
```

**Offen für P1:** 3 echte Creator-Takes für V1; neue VO/ASR-Timings für **die Gewinner**; renderfähige Produktions-Storyboards, vollständiger Export + MP4-Preflight 0 FAIL; Sichtprüfung der tatsächlichen ersten 45 Frames. Die sechs Stummtests belegen nur visuellen Ansatz/Bewegung, keine Retention. Kein v1 mit Foto-/KI-Ersatz „grün“ melden. Andere Prioritäten (Retention, Sound, Series) erst nach dem Hook-Ideentest anfassen.
