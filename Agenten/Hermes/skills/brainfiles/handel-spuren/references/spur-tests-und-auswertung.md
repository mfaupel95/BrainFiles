# Tests und Auswertung einer Spur

## Tests richtig aufrufen

Die Spur-Suiten laufen NUR aus ihrem `tests/`-Ordner heraus:

    cd Agenten/Handel/<spur>/tests && ../../scanner/.venv/Scripts/python.exe -m unittest test_<spur>

Drei Aufrufe, die scheitern und dabei nach einem Code-Fehler aussehen:

- `discover -s tests` aus dem Spurenordner: `ImportError: Start directory is not
  importable` — es fehlt kein `__init__.py`, der Aufruf ist der falsche.
- `-m unittest tests.test_<spur>` aus dem Spurenordner: der Modulkopf schiebt
  `scanner/` und `HANDEL` auf `sys.path`, und je nach Reihenfolge gewinnt
  `scanner/handeln.py`. Symptom: `AttributeError: module 'handeln' has no attribute
  'pruefe_einstieg'. Did you mean: 'pruefe_einstiege'?` — der Test laeuft, prueft
  aber ein fremdes Modul. Bei dieser Meldung ZUERST `handeln.__file__` ausgeben
  lassen, bevor der eigene Code verdaechtigt wird.

## Tests gegen echte Laufzeitdateien schuetzen: das Modul patchen, das den Pfad BESITZT

Ein Test, der die Pfad-Konstante des falschen Moduls patcht, liest still die
ECHTEN Laufzeitdateien — er haengt am Bestand statt an seinem Fixture. Wandert
eine Spur-Funktion in ein anderes Modul (z. B. `spur_spiegel` nach `lage.py`,
tagesbericht re-exportiert nur noch), patcht der alte Test weiter
`tagesbericht.HIER` — die Funktion baut ihren Ordner aber ueber das `HIER` des
Moduls, in dem SIE definiert ist, und liest das echte Journal. Eine
hartkodierte Erwartung ("1 Ausstiege") faellt dann nach ein paar Tagen
Dauerlauf ("875 Ausstiege"), schlimmer: eine falsche Erwartung kann gegen
Live-Daten gruen bleiben.

Regel: **vor dem Patch nachsehen, wo die Funktion ihren Pfad wirklich aufbaut**
(Modul-Konstante, nicht Funktionsargument), und das besitzende Modul patchen
(z. B. `patch.object(lage, "HIER", t)` ZUSAETZLICH zu tagesbericht). Eine
hartkodierte Zeilenzahl im Test ist nur gueltig, wenn das gelesene Journal
nachweislich das Temp-Journal ist — im Zweifel die Pfad-Konstante pruefen, die
der Test-Code durchlaufen muss. Erkennungszeichen, dass ein Test am echten
Bestand haengt: die Erwartung nennt eine Zahl, die mit dem Dauerlauf waechst.

## Ausstiegsrechnung: zwei Fehler, die jede neue Spur aus der Vorlage erbt

1. **G/V auf den NOMINALWERT, nicht auf den Kurs.**
   Richtig: `gv = nominal * (kurs - einstieg) / einstieg * vz`, `erloes = nominal + gv`.
   Falsch und unauffaellig: `gv = (kurs - einstieg) * vz` — die rohe Kursdifferenz.
   Bei BTC ist das ein Faktor in Zehntausenden: aus 100 USD Nominal und 3 % Gewinn
   wird ein „Erloes“ in Kurshoehe. Erkennungszeichen im Journal: Erloes > Einsatz x 3
   ohne Hebel. Jede Spur braucht einen Test, der 3 % Kursgewinn bei 100 USD Einsatz
   auf +3 USD festnagelt (Gegenprobe: die alte Formel ergaebe hier +3000).
2. **Nur Positionen des EIGENEN Instruments pruefen.** `pruefe_ausstiege(z, k, w)`
   bekommt `k` — die Kerzen eines Instruments — und lief ueber alle Positionen; eine
   SOL-Position wurde so mit dem BTC-Kurs bewertet. Signatur
   `pruefe_ausstiege(z, k, w, nur=None)` und in der Schleife
   `if nur is not None and p.get("inst") != nur: behalten.append(p); continue`,
   Aufruf mit `nur=inst`.

Ein verdorbenes Journal NICHT loeschen: als
`handelsjournal.falsch-skaliert-JJJJMMTT.csv` daneben legen und leer neu starten —
die Spur legt die Datei beim naechsten Schreibvorgang selbst mit Kopfzeile an
(`journal()` prueft `not os.path.exists`). Die offenen Positionen in `zustand.json`
sind davon nicht betroffen: falsch war nur die Ausstiegsrechnung.

## Anschluss an die Auswertung

In `auswertung_alle.py` sind drei Stellen zu bedienen, sonst bleibt die Spur
unsichtbar oder stumm:

1. `SPUREN` um die Spur erweitern (steuert `--spur` und die Uebersicht),
2. eine `runden_*`-Funktion fuer ihr Journal-Format,
3. der Zweig in `kennzahlen_fuer()` — DAS ist der eigentliche Anschluss: ohne ihn
   faellt die Spur in den leeren `else`-Zweig und `/strategien` meldet „keine
   geschlossene Runde“, obwohl Zeilen im Journal stehen.

`/strategien` in `befehle.py` ruft `aa.kennzahlen_fuer(spur)`; Spuren mit eigenem
`auswertung.py` stehen in `EIGENE_AUSWERTUNG`. Kosten nur behaupten, wenn sie in der
Zeile stehen — fuehrt die `wachen.json` kein `gebuehr_taker`, ist `kosten = 0` und
nicht geschaetzt.

Muster fuer den Test: `Agenten/Handel/tests/test_indikator_auswertung.py` —
synthetisches Journal schreiben, per `csv.DictReader` einlesen, `runden_*` direkt
aufrufen (kein Netz, kein Lauf, kein Schreiben in echte Pfade).
