# Backlog für Verbesserungs-Agenten — priorisiert, mit Akzeptanzkriterien

> Kontext: Drei Shorts mit 0-FAIL-Preflight existieren. **Die technische Pipeline ist nicht die Bremse.**
> Die Bremse ist: Hook-Konzept, Test-Volume, Series-Denken. Die Zahlen (Kampagnen-Median 395–1.448 Views,
> Test-Batch 239–273 Views) zeigen: das Publikum verliert das Interesse **vor** dem ersten Beweis.

## Priorität 1 — Hook-Level neu denken (Ideen-Ebene!)

Jeder Short braucht **3 Hook-Varianten**, die unterschiedliche Trigger testen — nicht 3 Render-Variationen
des gleichen Typo-Konzepts:

- **V1 „Gesicht + Vorwurf":** echter Creator vor der Kamera (Smartphone-Requisite reicht) über dem
  Unfallfoto mit harter Eröffnungsfrage. In der Kategorie Gebrauchtwagen kümmert ein Gesicht das
  Autoplay-Sound-Problem; reine Typo-Frames werden auf Silent gescrollt.
- **V2 „Ein-Zahl-Hammer":** die Zahl füllt das Bild („48 %"), die noch aufzunehmende Stimme
  erklärt **korrekt**: „Kalkulierte Reparaturkosten: 48 % des damaligen Fahrzeugwerts.“
  **Nicht** als 48 % Wertverlust ausgeben. Kein anderes Textelement im ersten Frame, keine Etiketten.
- **V3 „Widerspruch-Blitz":** 0,0 s offene Frage („Unfallfrei?“ **ohne** fiktiven Verkäufer-/Chat-Absender) → 0,8 s Schnitt auf den Report. Der Widerspruch wird **nicht** erklärt — die Kluft macht die Spannung. Ein echtes Verkäufer-Statement braucht einen Originalbeleg, der hier fehlt.

Akzeptanz: Hook-Varianten liegen als eigene Storyboards, Preflight 0 FAIL, und die **ersten 1,5 s
enthalten Bewegung plus mindestens ein Gesichts- oder Zahlenelement**.

Datei-Zeiger: `media/carvertical-ugc/storyboard_cv5.json` (Szene 1 = `danger`), Engine-Hook:
`skill/engine/render.py` → `scene_danger`. Der Stempel ist entkoppelt (`stamp: null` allowed).

**Zwischenstand 23.10.2026:** [9/9 Konzept-Storyboards + Testplan](P1_HOOKS.md) erstellt. Sechs V2/V3-Hooks als **stumme 1,5-s-MP4-Previews** gerendert: Pixel-Gate für Bewegung/Reveals 6/6 PASS; Blindtest gegen alte Intros im Hook Lab vorbereitet, aber **keine Teilnehmenden-Ergebnisse**. Dazu [ein vollständiger carVertical-V3-Sichtungscut](../media/carvertical-ugc/out/short_carvertical_v6_v3.mp4) mit 0-FAIL-MP4-Preflight (1 WARN, 1 ASR-SKIP). Nur 0–1,5 s neu; Originalton bitidentisch, danach alter Body. [Kritische Sichtung](P1_CV5_FULL_REVIEW.md): Bruch bei 1,5 s, keine Gleichwertigkeit mit `/motion`. **P1 nicht abgenommen:** V1 braucht drei echte Creator-Takes; der Sieger muss noch im Panel ermittelt und mit passendem VO/ASR sowie eigenem Full-Storyboard und Preflight ausgearbeitet werden. Preview-Gate ersetzt keinen 0-FAIL-Preflight am fertigen Short.

## Priorität 2 — Retention-Mathematik vor dem Render prüfen

Vor jedem Render: in den ersten 10 s mindestens **3 Szenenwechsel** erzwingen (aktuell cv5: 2 in
den ersten 10 s). Werkzeug: `tools/peek.py` mit `--times 0.2 1.0 2.0 3.5 5.5 8 10`.
Danach Szenengrenzen nachziehen — nicht das Encoding.

Akzeptanz: mittlere Szenenlänge ≤ 2,5 s in den ersten 15 s; kein Screenshot bleibt länger als
1,2 s ohne aktive Annotation im Bild.

## Priorität 3 — Sounddesign ist 50 % des Feeds

Aktuelles Musik-Bett: ein CC0-Loop bei Gain 0,12. Konkrete Schritte:

- Die Szenengrenzen (`--cuts` in finalize.sh) auf den **Beat-Raster** der Musik quantisieren,
  nicht auf VO-Pausen.
- Einen **Impact/Hit** auf jeden Stempel und jeden Reveal (aktuell nur Whooshes an Szenenenden).
- Whooshes −6 bis −9 dB relativ zur VO absenken (aktuell zu präsent), Musik-Lead-In 0,4 s vor dem
  ersten Frame starten.

Akzeptanz: Audio zeigt hörbare Transients an Szenengrenzen, True-Peak bleibt ≤ −1,5 dBTP
(Preflight-Checks bleiben grün).

## Priorität 4 — Series-Gerüst statt Einzel-Posts

Für jede Kampagne **5 Episoden** mit dominierendem Formatnamen bauen („Auto-Akten #1–5",
„Was dein Käufer verschweigt"). Gleiche Stimme, gleiche Intro-Karte, inkrementelle Beweise.
Dafür braucht es ein **Template-Storyboard mit Slot-Variablen** (Fahrzeug, Zahlen, Screenshot-Pfade) —
Episode n = neue Media-Liste + Claim-Liste, alles andere bleibt.

Akzeptanz: eine Template-JSON pro Serie; eine neue Episode braucht < 30 min Vorbereitung
(ohne Renderzeit). Renderdauer ca. 25 min pro Short (Dokumentation: 1 s/Frame).

## Priorität 5 — A/B-Mechanik bei Content Rewards

Content Rewards erlaubt kein Löschen nach dem Posten → **Entwurfs-Strategie**:

- Max 2–3 Entwürfe parallel im Konto (Plattform-Limit beachten), nur die beste Hook-Variante
  wird gepostet; die restlichen als Storyboard-Datei im Repo behalten.
- Caption-SEO: der Caption-Stil ist brauchbar, aber der **erste Satz** sollte die Hook-Variante
  spiegeln (Zahl-Variante → Zahl als erster Satz, nicht die Frage).
- Nach 48 h: Retention-Diagnose anhand der Plattform-Statistiken (wo wird gesprungen?) → die
  nächste Hook-Variante baut auf den Absprung-Zeitpunkten auf.

Akzeptanz: eine `data/learnings.jsonl` pro gepostetem Short:
```jsonl
{"short": "short_carvertical_v5.mp4", "hook_variant": "v1", "first_seen_drop": null, "notes": ""}
```

## Priorität 6 — Stimme: Wettbewerb gegen echte Creator-Videos

- Modal-Chatterbox mit `exaggeration 0.65` und `cfg_weight 0.4` testen (mehr Emotion, weniger flach).
- Globales VO-Tempo um **+6 %** straffen (`atempo=1.06`), danach Wort-Timings über das ASR-Gate
  neu einmessen — kurze Formate drücken unter 150 WPM langweilig.
- Zwischen Behauptungen eine Atem-Pause (0,25 s) einbauen statt konstanter Klick-Rate.

Akzeptanz: ein VO-Vergleichs-Ordner (alt/neu), das ASR-Gate bleibt 0 FAIL, und im Hörbote
dokumentiert, welche Variante nativer klingt.

## Priorität 7 — Bildqualität der Karten

- YouTube-Material: die Quelle per `yt-dlp` in **1080p** ziehen statt 720p-Frames — die Karten
  skalieren aktuell das 2,4-fache des Ausgangs hoch und wirken weich.
- carVertical-Fotos existieren nur als 2,4x-Upscale → falls das Layout es erlaubt, das Foto als
  Karte **60 % + ein Fakten-Chip-Doppeldecker 40 %** statt Foto allein, so dass der disruptive
  Kontrast von Bild und Text entsteht.

Akzeptanz: keine Karte im QA-Sheet wird stärker als 1,6x hochskaliert — automatisch messbar
(Prüfung der Skalierungsfaktoren in `render.py`/`tools/peek.py`).

## Priorität 8 — Kleinigkeiten, die Retention killen

- [ ] App-Short: Szene-1-Beleg passt nicht zur VO („Rollen und Plattform"). Bild-Reihenfolge an
      die VO-Anker anpassen (`build_storyboards.py` → `APP_BEATS`).
- [ ] Danger-Card: ~30 % leerer Bokeh-Bereich (oben). Lösung: **Foto + Fakten-Chip-Doppeldecker**
      statt Fülltext — das Bokeh bleibt, der Chip verdichtet die Lücke.
- [ ] `BEWEIS 01`-Etiketten im Hook: Eine Struktur-Ankündigung im ersten Frame tötet Neugier —
      das Chip-Band erst ab Szene 2 einblenden.
- [ ] Headline-Pop endet am Clamp-Wert (x=1074) vorzeitig (die bekannte WARN im Preflight):
      das ruhige Ziel (x=1046) direkt als Pop-Ziel setzen, damit die Bewegung nicht ruckartig
      vor dem Ende einschläft.
- [ ] Endkarten-Copy: „Link in Bio" ist schwach. Eine konkrete Nutzungszeile („VIN aus dem
      Kfz-Schein — der Check dauert 2 Min") hat mehr Aufforderungskraft.
- [ ] Kamera-Motion: die Subpixel-Kamera (kein zoompan-Wackeln) ist drin, aber auf bewegten
      Shots fehlt ein dezenter Bewegungsunschärfe-Sweep (Pillow: 1px-Shift bei > 0,3 s Bewegung).
