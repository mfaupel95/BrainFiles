# Zahlen und fremde Fixes nachrechnen

Ein Commit, der einen Fehler behebt, ist eine Behauptung. Eine Zahl in einer
Auswertung ist eine Behauptung. Ein eigenes Messwerkzeug ist eine Behauptung.
Dieses Rezept belegt alle drei am Gegenstand - und benutzt den WIDERSPRUCH
zwischen zwei Rechenwegen als Suchgeraet.

## Der Drei-Wege-Test

Dieselbe Groesse ueber drei unabhaengige Wege rechnen. Erst wenn alle drei
zustimmen, ist sie belegt. Weichen sie ab, ist NICHT die Mehrheit richtig,
sondern einer hat einen Fehler - und der Ausreisser zeigt, wo.

| Weg | Was er tut | Wann er traegt |
|---|---|---|
| **Zeilenrechnung** | jede Zeile gegen ihre EIGENEN Felder (die Marke steht in der Austrittszeile) | immer, wenn die Zeile ihre Bezugsgroesse selbst traegt |
| **Schluessel-Paarung** | Einstieg und Ausstieg ueber `(inst, stop, ziel)` verbinden | wenn die Marken eine Position eindeutig identifizieren (0 ohne Partner = eindeutig) |
| **Hausfunktion** | `kosten_wendepunkt.paarung()` / `runden_aus_journal()` | immer - sie ist der Massstab, den die Auswertungen benutzen |

Belegter Fall (wavetrend, 2021-2026, zwei Laeufe vor/nach einem Ausstiegsfix):

```
Zeilenrechnung                  +492.26
Schluessel-Paarung              +492.26
kosten_wendepunkt.paarung        -47.71   <- der Ausreisser WAR der Fehler
```

Die Hausfunktion rechnete das Rundenergebnis als `preis/einstieg - 1` **ohne
die Handelsrichtung**. Bei einem SHORT war das Vorzeichen damit verkehrt: eine
Short-Runde, die im Ziel schloss, stand als Verlust im Buch. Gemessen:
Trefferquote 54,2 % statt 33,2 %, Summe +679 statt -513. Rund die Haelfte aller
Runden der betroffenen Spuren (squeeze, macd_mtf, supertrend, wavetrend: je
~50 % Shorts) war damit verfaelscht.

## Die zwei Fallen, die dabei zuschlagen

1. **Die Richtung fehlt.** Jedes Rundenergebnis braucht das Vorzeichen der
   Seite: `(preis/einstieg - 1) * (-1 bei short)`. Die Seite steht in der
   EINSTIEGSzeile (`seite`, Werte `long`/`short`). Fehlt sie, gilt long - und
die Zeile gehoert als `ohne_seite` ausgewiesen, nicht verschwiegen.
2. **Eine einseitige Summe ist keine Nettozahl.** Wer nur die Faelle zaehlt, die
   JENSEITS der Marke liegen ("zu weit gelaufen"), und die auf der guten Seite
   weglaesst, bekommt eine Summe mit dem falschen Vorzeichen. Belegter Fall:
   eine Fassung meldete +493, richtig waren -48. Fuer einen Long ist ein
   HOEHERER Ausstieg immer besser - egal ob Stop oder Ziel; fuer einen Short
   immer schlechter. Also EIN Vorzeichen je Richtung, nicht je Marke.

## Rezept

Alle Befehle aus `Agenten/Handel` ueber das `terminal`-Werkzeug.

1. **Was behauptet der Fix?** Den Commit lesen und die Gegenprobe suchen, die
er selbst mitbringt:

   ```bash
   git log --oneline -5 -- <datei>        # ZUERST: ist der Fix schon da?
   git show <commit> --stat
   ```

   Zuerst nachsehen, ob eine parallele Sitzung dieselbe Aufgabe schon gebaut hat
   - sonst entsteht eine zweite Umsetzung derselben Regel.

2. **Am Gegenstand messen**, nicht an der Meldung. Fuer die Ausstiegsregel ist
das der Zaehler im Journal:

   ```bash
   python -c "import replay,pathlib; print(replay.auf_der_marke(pathlib.Path('daten/backtest/<spur>/<lauf>/handelsjournal.csv')))"
   ```

   Vorher `{'ausstiege_an_marke': 0, 'ausstiege': 1506}`, nachher
   `{'ausstiege_an_marke': 1506, 'ausstiege': 1506}` - das ist der Beweis.

3. **Die Groesse unabhaengig beziffern** (Zeilenrechnung, ohne Paarung):

   ```bash
   python kerzenschluss_bias.py --spur <spur>     # --json fuer Maschinen
   ```

   Je Austrittszeile, weil die Marke in der Zeile selbst steht: `zuviel Gewinn`
   / `zuviel Verlust` in Prozentpunkten der Marke, `netto` vorzeichenrichtig,
   Spalte `Marke%` (100 % = Lauf nach dem Fix).

4. **Gegenprobe mit der Hausfunktion** auf denselben Journalen:

   ```bash
   python -c "import kosten_wendepunkt as kw;from pathlib import Path;print(kw.wendepunkt(kw.paarung(Path('daten/backtest/<spur>/<lauf>/handelsjournal.csv'))['runden']))"
   ```

5. **Bei Abweichung: den Unterschied isolieren, statt zu diskutieren.** Ein
   Hybrid-Journal bauen - dieselben Zeilen, nur die strittige Spalte getauscht -
   und die Hausfunktion darauf fahren. Reproduziert sie damit exakt den alten
   Wert, ist sie rein datengetrieben und der Fehler liegt in ihrer Auslegung
   (z. B. im Vorzeichen), nicht in der Paarung.

   ```python
   # gleiche Zeilen, nur der Preis der Austrittszeilen aus dem anderen Lauf
   z = dict(zeile_nach); z["preis"] = zeile_vor["preis"]
   ```

## Fremde Fixes pruefen - Reihenfolge

1. `git log -- <datei>`: ist die Regel schon gebaut? (Diesmal: ja, Commit der
   parallelen Sitzung - die eigene Arbeit war dann NUR die Gegenprobe.)
2. Den Zaehler des Fixes selbst benutzen (`replay.auf_der_marke`).
3. Die Wirkung unabhaengig beziffern (Schritte 3-5 oben).
4. Erst danach die eigene Fassung der Zahlen veroeffentlichen - und wenn die
   eigene frueher veroeffentlichte Lesart falsch war, sie KORRIGIEREN, nicht
   stillschweigend ersetzen. Belegter Fall: "die Gewinner sind zu gut
   gerechnet" war nur die kleinere Haelfte; die Verlustseite war doppelt so
   gross (938 gegen 445 Punkte).

## Wenn der Fehler in geteiltem Code sitzt

- **Ein Test, der ohne den Fix rot ist, und zwar in BEIDEN Richtungen.** Belegter
  Fall: `tests/test_kosten_wendepunkt.RichtungTest` faehrt eine Long- und eine
  Short-Runde im Ziel; ohne die Vorzeichen-Regel faellt die Short-Runde durch.
- **Die volle Suite vor dem Commit** - geteilter Code beruehrt viele Aufrufer
  (`kraken/wachen_kraken`, `orbk/wachen_orbk`, `scanner/wachen_pruefung`,
  `stoerungen`). Gemessen: 1329 Tests, OK.
- **Veroeffentlichte Zahlen werden zu Aufgaben.** Aendert sich eine Kennzahl,
  gehoeren die betroffenen Tabellen (Wiki, Auswertungen, Kosten-Wendepunkt) als
  eigener TASKS-Eintrag nachgezogen - mit der alten und der neuen Zahl, damit
  der Unterschied nachvollziehbar bleibt.
- **Additiv aendern.** Ein neues Feld (`ohne_seite`) im Rueckgabewert bricht
  keine Aufrufer; eine Aenderung an der Bedeutung eines BESTEHENDEN Feldes
  schon.

## Werkzeugfallen (diesmal erlebt)

- **`write_file` verweigert eine Datei, die nur per `patch` angefasst wurde**
  ("has not seen its full current content"). Entweder komplett mit `read_file`
  lesen oder die eigene, noch ungetrackte Datei loeschen und neu schreiben.
- **Die Glob-Ebene muss stimmen.** Die Backtest-Journale liegen ZWEI Ebenen
  unter `daten/backtest` (`<spur>/<lauf>/handelsjournal.csv`); ein Muster mit
  einer Ebene findet nichts und meldet "keine Journale", obwohl welche da sind.
- **Gleitkomma-Rauschen braucht eine Toleranz.** Eine Runde GENAU auf der Marke
  liegt rechnerisch bei `2e-15` Abweichung; ohne Schwelle zaehlt sie als
  betroffen. Relativ messen (`1e-6`) und die Schwelle im Code begruenden.
- **Ein fehlender Pfad ist kein Fehler.** Ein Messwerkzeug, das von Hand mit
  einem nicht vorhandenen Pfad aufgerufen wird (Modulwaechter!), soll `None`
  liefern statt `FileNotFoundError`.
- **Relative Pfade in der Anzeige.** `pfad.relative_to(WURZEL)` wirft, wenn das
  Werkzeug mit einem relativen Pfad aufgerufen wird - einmal absichern.
