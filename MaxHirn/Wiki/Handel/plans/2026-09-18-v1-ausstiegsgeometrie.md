# V1 — Schattenbücher „knapp" und „weit" (Ausstiegsgeometrie)

Stand: 19.09.2026 · Auftrag: „Beide" (V1 der Spezifikation 2026-09-18-filter-studie.md)

**Status: UMGESETZT und verdrahtet (19.09.2026).** Beide Schattenbuecher
laufen im Dauerlauf (Basis), spiegelstand meldet 27/27 byte-gleich, die
Bus-Suite ist gruen. Die Buecher fuellen sich; das Auswertungs-Protokoll
unten (30 Ausstiege je Arm, dann `auswertung.py --pfad ...`) bleibt offen,
bis genug Daten da sind.

## Zweck

Die Ausstiegsgeometrie der Spur `spiegel` ändern und MESSEN, bevor sie ins
Hauptbuch wandert: zwei Schattenbücher fahren dieselbe Signalquelle mit
anderen Stop/Trailing-Parametern. Das Hauptbuch bleibt unverändert und ist
die Vergleichsgrundlage.

## Warum diese Arme (gemessene Zahlen, Stand 18.09.2026)

- 53 % aller Ausstiege sind Stops; die realisieren Ø **−46 %** statt der
  gedachten −30 % (Durchrutschen).
- 56 % sind Trails und realisieren Ø **+65 %**.
- Erwartungswert heute je Runde: 0,25·(+65) + 0,75·(−46) = **−18,25 %-Punkte**.
- Die eine Frage: kappt ein früherer Ausstieg die Verluste schneller, als er
  Gewinner abschneidet? Das misst „knapp"; „weit" ist die Gegenrichtung
  (mehr Laufzeit für Gewinner, tiefere Verluste) als Spiegelkontrolle.

## Parameter je Arm

Alle anderen Wachen-Werte (Einsatz 50, Band 250k–1M, 60 Plätze, Frist 168 h,
Kosten) bleiben IDENTISCH — der Vergleich ist dann nur über die Geometrie.

| Feld | Hauptbuch (heute) | knapp | weit |
|---|---|---|---|
| stop_usd | 15 (30 % des Einsatzes) | **8 (16 %)** | **25 (50 %)** |
| trail_aktiv_ab | 30 % | **15 %** | **40 %** |
| trail_abstand | 25 % | **15 %** | **30 %** |
| frist_stunden | 168 | 168 | 168 |

Ableitung „knapp": der Stop ist die dominante Verlustquelle; 16 % bleiben
klar über dem Kosten-Durchrutschen (Slippage 3 % + Gebühr 1 % ≈ 4–5 pp).
Ableitung „weit": spiegelt die Obergrenze der alten Geometrie-Frage, ohne
in absurde Bereiche zu gehen.

## Mechanik (wie die Risikostufe, aber eigener Schalter)

- `spiegel.py` liest beim Start `HANDEL_BUCH` aus der Umgebung (leer =
  Hauptbuch). Eine Funktion `_buch_datei(pfad)` hängt `.knapp`/`.weit` vor
  die Endung an (Muster: `risikostufe.datei()`). Die fünf Datei-Konstanten
  (Zeilen 91–95: WACHEN, VERFOLGTE, ZUSTAND, JOURNAL, ABLEHNUNGEN) laufen
  dadurch durch — Hauptbuch-Suffix ist leer, Verhalten des Hauptbuchs
  identisch.
- Zwei Launcher-Skripte `spiegel/spiegel_knapp.py` und
  `spiegel/spiegel_weit.py` (je ~10 Zeilen): setzen `HANDEL_BUCH`, rufen
  `spiegel.main()` mit den übergebenen Argumenten auf.
- Zwei Arm-Wachen `spiegel/wachen.knapp.json`, `spiegel/wachen.weit.json`:
  Kopien des heutigen `wachen.json` mit den drei Parametern + Vermerk im
  Kommentarfeld und eigenem `journal_zweitziel` → `Q:\Handel_Journal\spiegel_knapp` bzw. `spiegel_weit` (Bedingung 4).
- `dauerlauf.py` `SPUREN`: zwei neue Einträge
  `spiegel_knapp`/`spiegel_weit` (ordner spiegel, skript spiegel_knapp.py/
  spiegel_weit.py) — der Startaufruf `[python, skript, modus]` unterstützt
  das ohne Änderung. Beide in `NUR_BASIS` aufnehmen (wie `spiegel`, sonst
  laufen sie im Mittel-Lauf doppelt).

## Nicht angefasst

- Hauptbuch-Logik und -Wachen (nur der Name `_buch_datei` dazwischen).
- `risikostufe.py` (die Arme sind KEINE Risikostufe — deren Semantik
  „stumm/live" bleibt unbeteiligt).
- `auswertung.py`: braucht keine Änderung — `--pfad handelsjournal.knapp.csv`
  liest ein Arm-Buch.
- Alle anderen Spuren.

## Auswertungs-Protokoll

- Mindestbesetzung **30 Ausstiege je Arm** (⇔ ~1–2 Tage Lauf, ~26
  Ausstiege/Tag/Buch), dann `auswertung.py --pfad ...` je Buch und Vergleich
  gegen das Hauptbuch auf demselben Zeitfenster.
- Zusätzlich der **gepaarte Vergleich**: gemeinsame Einstiege (gleicher
  Token, ähnliche Zeit) in zwei Büchern — dieselbe Kaufentscheidung, zwei
  Ausstiege. Ist der sauberste Beleg.
- Entscheidung über die Parameter des Hauptbuchs trifft Max nach dem Beleg
  (Stufe-1-Wechsel).

## Risiken und Grenzen

- **3× Feed-Last**: drei Spiegel-Bücher je Zyklus gegen denselben öffentlichen
  Feed (bisher 10+9 Spuren-Läufe/15 min; zwei mehr sind verkraftbar, Status
  wird im ersten Tag beobachtet).
- **Dauerlauf-Neustart nötig** (neue SPUREN-Einträge): kontrollierter
  Neustart mit Prüf-Checkliste (freigabe_fenster.json prüfen, nur per PID
  beenden, Basis- und Mittel-Lauf per Wrapper neu starten, spiegelstand.py
  muss danach 12/12 byte-gleich melden — vorhandene 10 + 2 neue Arme).
- Die Bücher füllen sich unabhängig (je 60 Plätze): Einstiege sind nicht
  identisch, ihre Verteilung auch nicht — deshalb der gepaarte Vergleich.
- Der erste Tag zeigt nur die Laufrichtung; Verdikte erst ab ~30 Ausstiegen.

## Tests (vor der Verdrahtung)

- `_buch_datei`: Suffix bei HANDEL_BUCH=knapp/weit, leerer Suffix ohne
  Variable, kein Schreiben.
- Launcher: subprocess mit gesetzter Variable und `--wachen` (lesend) →
  Ausgabe nennt die Arm-Wachen-Werte.
- Auswertung: `--pfad` auf ein Arm-Journal (Temp-Kopie) liefert dieselben
  Spalten.
- Modulwächter: kein Test schreibt in `spiegel/` (Dateiliste+Größen vorher/
  nachher, Muster der Spuren-Testsuiten).
- Gegenprobe Tor: die 6-Signalfälle aus dem Filter-Beleg (30k/60k/100k/
  200k/300k/2M) für die Arm-Wachen — alle drei Bücher müssen identisch
  entscheiden (die Arme ändern NUR die Ausstiege, nicht das Tor).

## Reihenfolge der Umsetzung

1. [x] `_buch_datei` + Konstanten-Umstellung in spiegel.py (Stufe-1: Sicherung,
   Diff-Kontrolle), Tests grün.
2. [x] Arm-Wachen + Launcher + .gitignore-Freigaben, Tests grün.
3. [x] SPUREN/NUR_BASIS + Neustart des Dauerlaufs (Checkliste oben) →
   spiegelstand 12/12 (tatsächlich 27/27, inkl. der 2 Arme).
4. [x] Tagesbericht/Bus übernehmen die zwei Namen automatisch (kommen aus
   SPUREN); nach dem ersten Lauf geprüft — die Arme melden sich am Bus
   (handel/spiegel_knapp, handel/spiegel_weit) und erscheinen im Bericht.