# carVertical V3: Sichtung des vollständigen 27,20-s-Sichtungscuts

**Stand: 23.10.2026.** [Video öffnen](../media/carvertical-ugc/out/short_carvertical_v6_v3.mp4) · [Board](../media/carvertical-ugc/hooks/storyboard_cv5_v3.json) · [Reproduzierbarer Schnitt](../media/carvertical-ugc/tools/build_cv5_v3_full.py) · [Provenienz mit SHA-256](../media/carvertical-ugc/out/short_carvertical_v6_v3.provenance.json)

## Was wirklich geändert wurde

45 neue Bilder (0,00–1,50 s): unscharfer dokumentierter Schaden mit **redaktioneller Frage** „UNFALLFREI?“ → **harter Cut bei Frame 24 / 0,80 s** auf dasselbe Foto plus Belegzeile aus dem **carVertical-Musterbericht** („Kalkulierte Kosten: 22.501 € – 25.000 €“). Ab **Frame 45 / 1,50 s** ist das Bild wieder der ursprüngliche Short; es wurde bei der Verkettung neu encodiert. **Alle 1.276 AAC-Audiopakete** sind aus v5 bitidentisch übernommen; der Audio-PTS beginnt weiterhin bei −0,0213 s. Kein neues VO, kein behauptetes Verkäuferzitat und keine künstliche Person. Die geplanten V3-Board-Beats von 1,5 bis 5,65 s wurden **nicht** als neues Bild umgesetzt. Dieser Cut ist eine Sichtungsvariante, kein neunfacher Varianten-Finalexport.

## Eigene Bild-/Ton-Sichtung am tatsächlichen MP4

| Stelle | Beobachtung | Bewertung / Risiko |
|---|---|---|
| 0,00–0,77 s | Gelbe Frage sofort gut lesbar, Hintergrund zunächst unscharf; Badge/Unterstrich und Hintergrund bewegen sich. VO sagt 0,00–0,70 „Kein Unfall,“ laut vorhandenem Worttiming. | Besserer offener Konflikt als eine reine Titelkarte, aber ohne Gesicht ist der Kontext des verschwommenen Bilds erst mit dem Reveal eindeutig. „Unfallfrei?“ ist **keine** Verkäufernachricht. |
| 0,80–1,47 s | Sichtbarer harter Reveal, groß „22.501 – 25.000 €“, die echte Kostenzeile fährt ins Bild; sie ist ab ca. 1,0 s ganz lesbar. Original-VO beginnt 1,06 „über 20.000 Euro Schaden“. | Visuell und semantisch vereinbar (gerundete VO vs. präziser Beleg). Die kurze Aufhellung (drei Frames) am Cut lässt die Belegzeile im ersten Reveal-Moment hell/abgeschnitten wirken. |
| 1,50–5,65 s | Abrupter Rücksprung zum alten Warnstreifen-Layout; „20.000 €“ wird **noch einmal** groß gezeigt, danach Unfallfoto/Stempel. VO/Untertitel stammen unverändert aus dem Original. | **Größte Schwäche:** Stilbruch und Zahlenwiederholung kosten Tempo. Kein neues Bewegtbild oder echter Creator; als hochwertiger finaler `/motion`-Ersatz nicht überzeugend. |
| 5,65–22,92 s | Original-Report (Kilometerstand, Kosten, Zusammenfassung); Ton und Bild bleiben auf den ursprünglichen Positionen. Die 48 % im Report bedeuten Reparaturkosten / damaliger Fahrzeugwert, nicht Wertverlust. | Belegkette bleibt erhalten. Weitere Standbild-/Kartenpassagen und dichter Informationsgrad stammen aus v5; keine Retention-Verbesserung nach 1,5 s behaupten. |
| 22,92–27,20 s | Bestehende USC20-Endkarte. | Call-to-Action bleibt statisch, nicht neu inszeniert. |

**Gesamturteil (redaktionell, kein Publikumstest):** Der 0,8-s-Belegkonter funktioniert als **prüfbarer Hook-Kandidat**. Das ganze Video ist **nicht** die vom Nutzer gewünschte deutliche Qualitätssteigerung: Nach 1,5 s kehrt die alte statische Machart samt Zahlendopplung zurück. Bevor man ihn postet, sollte man die ersten 5,65 s mit durchgehender visueller Sprache neu schneiden, einen echten Creator-Take testen und einen Zuschauer-/Hörtest machen. Kein Vergleich mit Claude `/motion` ohne konkreten Referenzclip möglich.

## Nachweise und verbleibende Grenzen

- Reproduktion: `.venv/bin/python media/carvertical-ugc/tools/build_cv5_v3_full.py`. Ergebnis: **1080×1920, H.264, 30 fps, 816 Frames, 27,20 s, AAC Stereo**. Source/Output-Payload-Hash der AAC-Pakete identisch; Ausgabe atomar nach Frame-/Dauer-/Tonprüfung. Automatische Tests sichern den echten Cut bei Frame 24 und die Rückkehr zum alten Body exakt bei Frame 45.
- `skill/scripts/qa_preflight.py` am fertigen Export mit `--storyboard storyboard_cv5.json --brief brief_cv5.json --asr`: **15 Checks: 13 PASS, 1 WARN, 1 SKIP, 0 FAIL**, −14,1 LUFS, **−1,3 dBTP**. WARN = bestehender Headline-Pop im **alten** Body-Storyboard (Engine klemmt den Pop ab). SKIP = unabhängiges ASR-Gate ohne Backend/Credentials nicht gelaufen; bitidentisches AAC ersetzt **keinen neuen ASR-Nachweis**. Untertitel-Alignment-Heuristik fand nur **2 Platten** in 12 Stichproben; kein Beleg für vollständige manuelle Caption-Sichtung.
- Der MP4-Preflight prüft Format/Audio/Platten-Stichproben am neuen MP4, aber sein `--storyboard` ist das **alte** Body-Storyboard. Die 1,5 s Sonderanimation sind durch Board-Beleg-Check, Frame-/Pixel-Tests und Einzelbildsichtung geprüft, **nicht** durch ein renderfähiges Full-V3-Storyboard. Keine Schein-Abnahme der geplanten Beats 1,5–5,65 s.
- Pixel-Gate **am vollen Export**: Frame-0-Mittelwert **83,90**, Differenz 0–0,4 s **8,83**, Reveal um 0,8 s **44,10**, 0,9–1,4 s **10,08** (alle Schwellen bestanden). Das misst Bewegung, **nicht** Verständlichkeit, Kreativqualität oder Watchtime.
- **Nicht vorhanden:** echte V1-Creator-Aufnahmen samt Rechteklärung; neues Hook-VO mit ASR; repräsentativer Blindtest/Retention; vollständige neue V2-/V3-Body-Cuts für die zwei anderen Kampagnen. **Nicht mit einer viralen Freigabe verwechseln.**
