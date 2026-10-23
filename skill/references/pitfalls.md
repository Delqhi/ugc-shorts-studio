# Pitfalls — die Fehler, die in diesem Skill wirklich passiert sind

Jeder Punkt ist ein konkreter Fehler aus dem Referenzbau (carVertical, 20.–22.10.2026).
Sie sind hier gesammelt, weil **alle drei Erstfassungen des Videos an ihnen gescheitert sind**
und keiner davon per Augenmaß auffiel — erst Pixel-Messung bzw. Frame-Sweep haben sie gezeigt.

## A. Text/Layout (die teuersten)

1. **Text sitzt ~28 px zu tief.** `PIL.ImageDraw.text` auf eine RGBA-Ebene zeichnet die
   Glyphen *innerhalb* der Font-Ascent-Box; wer die Ebene einfach bei `y` klebt, schiebt
   alles um den Ascent-Überhang nach unten. Alle Headlines lagen dann 28 px zu tief und
   überlappten die Kopfleiste.
   **Fix:** Ebene rendern, `getchannel("A").getbbox()` messen, auf die Tinte zuschneiden,
   dann mit Anker setzen (siehe `engine/render.py: ink_layer/place`).
2. **Untertitel lag neben der Platte.** Platte fest 116 px hoch an `H-244`, Text einzeln an
   `H-210` → ~28 px Versatz, in manchen Szenen halb auf, halb neben dem Kasten.
   **Fix:** Textzuerst auf **einer** Grundlinie rendern, Bbox messen, Platte = Bbox + Padding,
   beide deckungsgleich kleben.
3. **Zwei Untertitel-Ebenen gleichzeitig.** Überlappende ASS-Events + libass-Kollision →
   der Text wurde gestapelt und mitten im Bild gezeigt.
   **Fix:** Events strikt sequenziell (Ende = Start des nächsten − 0,02 s) **oder** — besser —
   gar kein libass: Untertitel selbst in PIL rendern (kein libass nötig).
4. **Headline abgeschnitten** („UND DANN DER SCHAD" statt „SCHADEN"). Festes Layout ohne
   Breitenprüfung. **Fix:** `fit_size()` skaliert die Headline auf die Maximalbreite.
5. **Report-Überschriften links abgeschnitten** („ilometerstand"). Das Kamerfenster war
   zentriert, der Screenshot ist aber breiter als das Fenster.
   **Fix:** Fenster bei `x0 = 0` starten (linke Kante sichtbar) bzw. `span` = volle Breite.

## B. Bewegung/Kamera

6. **Das Bild wackelte.** ffmpeg-`zoompan` rundet die Crop-Origin pro Frame auf ganze
   Pixel → 1-px-Jitter, bei langsamen Zooms sichtbar.
   **Fix:** Kamera als Subpixel-Box direkt in PIL (`Image.resize(box=...)`), kein `zoompan`.
7. **Szenenübergänge als Weißblitz zu lang** (0,16 s wirkt im Frame-Sweep wie ein
   Fehlframe). **Fix:** 0,1 s, und beim Sichtprüfen Frames in der Blitzphase ignorieren.

## C. Audio/Stimme

8. **Falsches Wort:** „unfallfrei" wurde zu „unfallsfrei" ausgesprochen. Im ASR fällt das
   sofort auf. **Fix:** Wortwahl im Skript ändern („kein Unfall"), ASR-Gate Pflicht.
9. **Halluzinierte englische Fetzen.** Satzweise TTS-Synthese hängt englische Phrasen an
   („The auctioned offer almost tricked over time").
   **Fix:** **einmal im Kontext** synthetisieren, nie satzweise; Ergebnis per ASR prüfen.
10. **Falsche Zahl durch ASR-Fehler** („22.500" statt „25.000"). Zahlen im Skript als Wörter
    schreiben („fünfundzwanzigtausend") und per ASR gegenprüfen.

## D. Prozess/Gates

11. **Entwürfe bei der Marke lassen sich nicht zurückziehen.** Content Rewards hat weder
    Löschen- noch Zurückziehen-Knopf (auch kein API-Pfad: alle Draft-Routen 404).
    **Fix:** Erst finalisieren, dann **einmal** einreichen. Jede Korrektur = ein neuer Entwurf.
12. **Plattform-Button war stumm-disabled**, bis das Konto per *echtem* Klick (bsk
    `click @ref`, nicht JS-`.click()`) gewählt war. **Fix:** Konto per echtem Klick wählen,
    dann prüfen, dass der Button nicht mehr `[disabled]` ist.
13. **Claim ohne Beleg.** „48 % vom Fahrzeugwert" war als „48 % des **damaligen**
    Fahrzeugwerts" im Report, im Video stand eine verkürzte, irreführende Fassung.
    **Fix:** Wortlaut der Claims deckungsgleich mit dem Beleg; Gate G3.

## E. Was die Sichtprüfung wirklich braucht

- **Frame-Sweep** je Sekunde (`watch`-Skill oder ffmpeg-Frames) — nicht nur 3 Stichproben.
- **Pixel-Messung** für: Banner-Kante vs. Textposition, Platte vs. Untertitel, Spielfeld
  links abgeschnitten? (ein Skript, das Zeilen auf „dunkel/weiß/gelb" prüft, reicht).
- **ASR über die fertige MP4** — nicht nur über die WAV, weil der Mix (Whooshes, loudnorm,
  Padding) sonst ungeprüft bleibt.
- **Lautheit messen** (−14 LUFS, True-Peak ≤ −1,5 dBTP) — Zwei-Pass-`loudnorm`, sonst
  landet der Mix 1–1,5 dB daneben.

## F. Posten: TikTok Studio füllt die Beschreibung vor

14. **Der Dateiname steht vor der Caption.** TikTok Studio füllt das Beschreibungsfeld
    mit dem Dateinamen („carvertical_ugc_de_v4"). Ein Paste hängt sich **dahinter** →
    die Live-Caption beginnt mit „carvertical_ugc_de_v4…". Genau so sind die alten
    Posts „TEST TEST“ und „codpodep12-…-cand_5“ entstanden.
    **Fix (verifiziert 22.10.2026):** 1) Editor fokussieren, 2) Caption pasten,
    3) **Caret an Position 0** setzen, 4) **N× Delete** (N = Länge des Dateinamens) →
    der Prefix verschwindet, 5) **gegen den Vorschautext prüfen, nicht gegen den DOM**.
    Der DraftJS-Editor spiegelt den Text **nicht** ins DOM (`innerText` = leer) und der
    Zeichen-Zähler zählt anders (432 statt 411) — nur der **Vorschautext** am Telefon
    ist die Wahrheit.
    Zusätzlich: `execCommand('insertText')` und `execCommand('delete')` als Clearweg
    sind unzuverlässig; `selectAll` + `insertText('')` crashed den Editor.

## G. ASR ohne Groq

15. **Infisical-CLI-Timeout (8 s) bricht Cloud-ASR ab.** Wenn `sin-infisical exec` mit
    „required Infisical secret unavailable" abbricht, ist der Key nicht weg, sondern der
    Abruf war langsam. **Ausweichweg:** ASR lokal auf Modal (faster-whisper, CPU/GPU) —
    siehe `scripts/`-Rezept in SKILL.md. Für schnelle Prüfungen genügt `modal run`,
    Modell-Cache liegt im Volume `sin-hf-cache`.

## H. Filtergraph-Index ≠ Input-Index (Harness-Fall 2026-10-22)

16. **„Invalid file index 12 in filtergraph"** nach dem Einbau eines Musikbetts.
    Der Musik-Input wurde an Index 11 angehängt, der Filter benutzte aber 12
    (Zähler vor/nach dem Inkrement falsch). Der Fehler ist im Log **ein** Zeichen
    und kostete einen ganzen Render-Durchlauf.
    **Fix:** Der Filtergraph wird jetzt in `scripts/build_mix_filter.py` an **einer**
    Stelle gebaut und dort geprüft (`--check-only`): jeder `[N:a]`-Index muss
    `< Anzahl Inputs` sein, und `amix=inputs=` muss zur Label-Zahl passen.
    `finalize.sh` ruft den Builder **und** den Check auf und bricht bei Abweichung ab.
    Negativtest: ein absichtlich falscher Index wird erkannt.

17. **Shell-Quoting im Filtergraph:** `shlex.quote()` um den Filtergraphen legt
    Anführungszeichen **in** den String, die ffmpeg dann als Teil des Filternamens
    liest („No such filter: '<ganzer Graph>'"). Der Graph wird deshalb unquotiert
    übergeben, die Argumentliste gequotet.

## I. Headline-Pop klemmt (bewusst, Gate G4)

18. Der Pop (1,16×) um den **linken** Anker schiebt lange Headlines über den
    rechten Rand (im 12-s-Frame von v4 war das „N" von „SCHADEN" abgeschnitten).
    `engine/render.py` klemmt den Pop jetzt:
    `sc = min(sc, (W - 6 - 34) / lay.width)` — **diese Klemme nicht entfernen.**
    Der Preflight meldet dafür `WARN sb.headline_pop` („Pop endet vorzeitig") — das
    ist **kein** Clipping und **kein** Fehler. Wer keine WARN will, kürzt die
    Headline auf ≤ 896 px in Ruhe (Pop 1,16× passt dann ohne Klemme).


## J. `span` ist je Szenen-Kind anders (Footgun 2026-10-22)

19. **`span` hat pro Szenen-Kind eine andere Semantik** und das erzeugt stille Leerflächen:
    - `evidence`/`hero`: sichtbare Breite in **Original-Pixeln** (1280/1080 = volle Breite).
      Werte < 20 werden als Zoomfaktor gelesen (`span = base.width * span`).
    - `clip`: **Zoomfaktor** (`cw = breite / span`); `span = 1280` ergibt ein 1-Pixel-Fenster
      → die Karte wird weiß/leer.
    - `danger`: **Zoomfaktor auf den Cover-Ausschnitt** (`cover_w = min(ow, oh*CW/CH)`);
      `span = 1.0` = voller Inhalt, `span = 1.4` = 1,4x näher.
    **Symptom:** weiße oder leere Content-Fläche. Immer `tools/peek.py`-Frames ansehen.

20. **`CH` war `CX1 - CY0` (= 766) statt `CY1 - CY0` (= 1728).** Folge: die Karte klebte
    oben, darunter blieb eine leere schwarze Fläche, und Annotationen wurden falsch
    positioniert. **Fix:** `CW, CH = CX1 - CX0, CY1 - CY0`.

21. **Vollbild-Cover bei 16:9-Quellen ist ein enger Hochschnitt** (Höhe begrenzt) und
    vergrößert 720p-Material um das 2,4-fache → matschig. Für Belege (Video-Frames,
    Unfallfotos) `fit: "card"` setzen: das ganze Originalbild als Karte auf unscharfem
    Grund. Das ist zugleich der geforderte „FRAMES"-Look.

22. **Der Unfallbild-Hook braucht eine neue Stimme.** Der alte Hook-Satz („Unfallfrei
    75.000 Kilometer") trug die Ironie allein. Für „WAAAHNSINN"-Hooks eine neue erste
    Zeile auf Modal-Chatterbox synthetisieren, per ASR-Gate prüfen und **vor** den
    Alt-VO setzen (0,25 s Pause). Die Szenengrenzen des Alt-VO verschieben sich um die
    Hooklänge — im Generator rechnen, nicht schätzen.


## K. Der Preflight maß die falsche Fläche (Fehl-FAIL 2026-10-22)

23. **„subs.plate_empty: Platte ohne Text"** obwohl die Untertitel korrekt mittig auf
    der Platte saßen (YT-Short, Gefahrenzone-Frame). Ursache: der Check suchte die
    Platte als **dunkle** Fläche und ranking die dunklen Komponenten nach Größe.
    Der Text zerteilt die Plattenfläche in dunkle Teilstücke, und ein dunkler
    Hintergrund (Bokeh + Scrim) liefert eine noch größere dunkle Fläche — der Check
    traf den Hintergrund (884x80 unter der Platte) statt der Platte.
    **Fix:** Die Platte wird jetzt über ihren **hellen Rahmen** gefunden
    (`find_plate_ring`), die Engine zeichnet den Rahmen mit Alpha 245/3 px.
    Gemessen wird die Mitte der Tinte gegen die Mitte der Platte (dx ≤ 12 px,
    dy ≤ 8 px). Renderer-unabhängig, kein Größen-Ranking mehr.

24. **`ink_bbox` liefert Crop-Koordinaten, nicht Frame-Koordinaten.** Wer sie gegen
    die Platten-Bbox rechnet, misst dx = −286 px und meldet jeden Frame als
    verschoben. Immer den Inset-Wert addieren.

25. **Parallele Shorts kollidierten im QA-Ordner:** `finalize.sh` schrieb alle
    Frames/Sheets nach `out/qa/` und räumte sie vorher weg — ein zweiter Lauf
    löschte die Sheets des ersten. **Fix:** eigener Temp- und QA-Ordner pro Ausgabe
    (`out/build_tmp/<name>`, `out/qa/<name>`), überschreibbar mit `--qa`.

26. **Background-Jobs mit `&` im Tool-Aufruf sterben beim Shell-Ende.** Für lange
    Renders die Background-Funktion des Shell-Tools nutzen, nicht `&` + `sleep`.
