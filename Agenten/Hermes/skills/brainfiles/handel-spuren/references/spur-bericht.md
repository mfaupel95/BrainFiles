# Zustandsbericht zu einer Spur ("Bericht")

## Wann
Max fragt "Bericht", "wie laeuft <Spur>", "Status der Nautilus/HANDEL-Spur".
Ein LESENDER Bericht ueber eine laufende Spur: nichts schreiben, nichts
neustarten, nichts reparieren - auch wenn dabei ein Befund auffaellt (der
Befund geht in den Bericht, der Fix erst nach Max' Wort).

## Quellen, in dieser Reihenfolge (lesen, nicht erinnern)
1. `Agenten/Handel/dauerlauf.SPUREN` - welche Spuren es gibt, Soll-Takt
   (`TAKT_MAX_MINUTEN`, 15), `skript`/`python` je Spur.
2. `<spur>/zustand.json` - Herzschlag (`letzter_lauf`), `zyklen`,
   `positionen`, die spur-eigene Kennzahl (z. B. `quotes_letzter_zyklus`).
3. `<spur>/handelsjournal.csv` - Zyklen, Abstaende, Kennzahl je Zeile, Kursband.
4. `Agenten/Bus/journal/<JJJJ-MM-TT>.jsonl` - `start`/`ende` mit Rueckgabecode:
   der Beleg, dass der Dauerlauf die Spur wirklich gestartet hat (nicht nur,
   dass eine Datei alt ist).
5. `<spur>/wachen.json` - Grenzen, `handel_erlaubt`, `freigabe`-Block.
6. `git -C <spur> log --oneline -1` + `git status -sb` - ist der Stand gepusht;
   die `.gitignore` der Spur nimmt Zustandsdateien aus, ein sauberer Stand sagt
   also nur etwas ueber den CODE, nichts ueber den Lauf.

## Fallen beim Lesen
- **Das Bus-Journal traegt ein BOM.** Mit `encoding="utf-8"` wirft `json.loads`
  "Unexpected UTF-8 BOM" und der Bericht bricht beim ersten Datensatz ab:
  `open(pfad, encoding="utf-8-sig")`.
- **Zonen nicht mischen.** `zustand.letzter_lauf` ist UTC (`+00:00`), die
  Bus-Zeilen sind lokal (`+02:00`). Das Herzschlag-Alter in UTC rechnen und
  gegen `herzschlag_max_minuten` stellen; im Text dann lokale Zeit nennen.
- **Zwei Bus-Eintraege je Zyklus sind normal, kein Doppellauf.** Nach dem
  Zykluslauf (`start`/`ende`, Dauer in Sekunden) folgt ein zweiter Lauf von
  ~1 s: das ist `dauerlauf.nur_fenster_fehlt`, der die Spur mit `--vorschau`
  fragt, ob nur das Freigabefenster fehlt. Er darf nichts schreiben - taucht im
  Journal der Vorschau eine Zeile auf, ist das ein Befund.
- **Zwei PIDs mit identischer Kommandozeile sind ein venv-Paar**, kein
  Doppellauf (Pitfall in SKILL.md): vor jeder Doppellauf-Meldung Eltern-PID und
  Startzeit jeder PID einzeln zeigen.
- **Kurze Abstaende sind Handlaeufe, keine Taktluecke.** Median der Abstaende
  gegen den Soll-Takt stellen und Luecken > Takt zaehlen - ein Abstand von 1-8
  Minuten kommt von Tests/Handstart am selben Tag und ist kein Alarm. Alarm
  sind Luecken und Nullrunden.
- **Ein Journal-Stempel zwischen zwei Dauerlauf-Zyklen ohne Bus-Paar ist ein
  Lauf ausserhalb des Dauerlaufs.** Der Takt steht im `dauerlauf.log`
  (15-min-Raster, Zyklus-Burst ~1 min); jeder echte Lauf durch `main()`
  schreibt ein Bus-Paar `start`/`ende` (`wer: handel/<spur>`). Ein Zyklus,
  der Journalzeilen UND `zustand`-Zeitstempel hinterlaesst, aber weder
  Logzeile noch Bus-Paar hat, lief ueber einen Nicht-`main()`-Pfad
  (Handstart per Import, Testlauf, Wegwerfskript) mit ECHTEM Zustand -
  Befund, kein Normalzustand. Gegenprobe: den Bus um die Minute nach ALLEN
  `wer` filtern (z. B. findet sich nur die Routine des Tages-Wrappers) und
  vorher die Zeitzonen angleichen (Journal UTC, Bus lokal).
- **Vermerk-Felder (`_...`) in wachen.json sind Historie, kein Zustand.** Sie
  beschreiben den Stand beim Schreiben und altern: `_stillgelegt` sagte
  "STILLGELEGT ... laeuft nicht mehr", waehrend `stillgelegt: false` stand
  und die Spur wieder papier-handelte. Den SCHALTER lesen (`stillgelegt`,
  `handel_erlaubt`), nie den Vermerk; bei Widerspruch ist der Vermerk alt,
  die Flagge wahr - und der Widerspruch selbst ein Doku-Befund.
- **Eine Nullrunde ist ein Alarm, kein Rauschen.** Die Kennzahl je Zyklus
  (Quotes, Kerzen, Kandidaten) muss > 0 sein; 0 heisst "Pfad tot", nicht
  "ruhig am Markt".
- **Eine Kennzahl ohne ihre Ausnahmen ist eine halbe Zahl.** Die Zeile
  `7 Tage: N Runden, +X, Treffer Y %` zaehlt nur HANDELSRUNDEN:
  `stoerungen.ist_stoerung` nimmt Zwangsschluss (herzschlag/zwangsschluss/notaus)
  und Buchhaltungs-Korrektur (buchbereinigung) heraus und weist sie getrennt aus
  (`n_stoerung`, `stoerung_ergebnis`). Seit dem 25.09.2026 nennt die Zeile sie im
  Klartext (`| +18 Ausstiege ohne Handelsentscheidung (+210.14 USD, nicht in der
  Quote)`); fehlt der Zusatz, ist „Treffer 100 %" nicht die Quote des Buchs - der
  scanner hatte 101 Runden, 2 Verlierer (beide `buchbereinigung`, 97,9 %).
  Gegenprobe: `auswertung_alle.kennzahlen()` liefert `n`, `n_stoerung` und
  `runden_gesamt`; `n + n_stoerung == runden_gesamt` muss aufgehen.
- **Reihenfolge der Zeitzonen in der Ausgabe pruefen**: eine Ausgabezeile ohne
  Datum/Zone liest sich als abgelaufene Frist (Pitfall in SKILL.md).

## Was in den Bericht gehoert
- Zuerst die Kennzahl/das Urteil, dann die Zahlen: Zyklen im Zeitraum,
  Takt-Treue (Median gegen Soll), Kennzahl je Zyklus (Median/min/max),
  Fehlerzahl aus dem Bus-Journal, Herzschlag-Alter gegen die Grenze.
- **Was die Spur nicht kann.** 0 Positionen bei einer Quotes-/Beobachtungsspur
  heisst "kein Einstiegspfad", nicht "keine Gelegenheit". Dazu gehoert die
  Frage, ob die Spur ihre eigenen Freigabe-Kriterien je erreichen kann
  (`freigabe.min_runden`, `min_wochen`, `netto_positiv`): eine Spur ohne
  Einstiege wird sie nie erfuellen, und wer das verschweigt, verspricht einen
  Live-Zweig, der nicht kommt.
- **Bedingung 4 mitpruefen**: `journal_zweitziel` gesetzt UND ein Aufrufer von
  `spiegele_journal` in der Spur (Skill `journal-spiegelung`). Ein gesetztes
  Ziel ohne Aufrufer spiegelt nichts. Der `journal_zweitziel_ok`-Vermerk im
  Zustand ist nicht bei allen Spuren da (xperp/kraken schreiben ihn nicht,
  spiegeln aber byte-gleich) - als Nachweis zaehlt `spiegelstand.py`, nicht
  das Feld.
- **Teststand nennen, nicht behaupten**: die Spur-Tests einmal laufen lassen
  (`./.venv/Scripts/python.exe test_<spur>.py` bzw.
  `python -m unittest discover -s tests`), Ergebnis in den Bericht.
  Liegen die Testdateien IM Spurordner (kein `tests/`, xperp-Muster
  "Direkt ausfuehrbar: python test_X.py"), jede einzeln mit absolutem
  Interpreter ausfuehren - und danach die mtimes von `zustand.json` und
  `handelsjournal.csv` mit dem Stand VOR dem Lauf vergleichen
  (`ls -l --time-style=full-iso`): unveraendert heisst, kein Test hat einen
  echten Zyklus geschrieben.
- **Form fuer Max**: Ergebnis zuerst, Bullets mit Zahlen statt Prosa,
  hoechstens fuenf "Offen"-Punkte nach Relevanz, am Ende GENAU EINE naechste
  Aktion (unter zwei Minuten) - und ein Satz, was absichtlich nicht angefasst
  wurde (lesend, kein Neustart, keine Config).
