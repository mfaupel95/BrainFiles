# Ausstieg rechnen, Journal deuten, Spur auswertbar machen

Gilt fuer jede Spur unter `Agenten/Handel/<spur>/`: die Ausstiegsrechnung in
`handeln.py`, die Form ihres Journals und der Anschluss an die Auswertung.

## G/V immer auf den Nominalwert

- Formel: `gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz`
  (vz = +1 long, -1 short), dann `erloes = p["nominal"] + gv`.
- Die **rohe Kursdifferenz** `(kurs - p["einstieg"])` ist der Fehler: sie ist
  ein Betrag in Kurshoehe, kein Ergebnis. Bei BTC ist der Faktor rund 70.000 -
  eine Runde mit 100 USD Nominal und 3 % Gewinn steht dann als "Erloes 3000 USD"
  im Journal, im Extremfall als 75911,19. Der Wert faellt nur beim Nachrechnen
  auf, weil er wie ein Kontostand aussieht.
- **Gegenprobe vor dem Abschluss:** 3 % Kursbewegung bei 100 USD Nominal MUSS
  +3 USD ergeben. Ein Test, der genau das festhaelt, gehoert zur Spur.
- `nominal` ist risikonormiert (`risiko_je_position_usd / (stop_pct/100)`,
  gedeckelt auf `max_pro_trade_usd`). Auf den Nominalwert zu rechnen haelt
  damit auch Ratsche, Halbierung und Kill-Schwelle konsistent.

## Ausstiegspruefung je Instrument

- `k` sind die Kerzen EINES Instruments. Die Ausstiegsfunktion muss das
  Instrument entgegennehmen (`pruefe_ausstiege(z, k, w, nur=<inst>)`) und
  fremde Positionen unveraendert durchreichen - sonst wird eine SOL-Position
  mit dem BTC-Kurs bewertet und der G/V ist frei erfunden.
- Die Aufruferschleife baut bereits `bestehend = [p for p in z["positionen"]
  if p["inst"] == inst]`; dieses Filter ist die Vorlage, keine zweite Liste.
- Trailing-Varianten (Supertrend) berechnen ihre Linie ueber `k` ebenfalls
  einmal je Instrument - die Einschraenkung gehoert vor die Positionsschleife,
  nicht in den Stop-Vergleich.
- Beim Nachziehen der Signatur: die Funktionskoepfe der Spuren sind NICHT
  identisch (Docstring, vorgeschalteter `try`-Block). Nach jeder Massenaenderung
  per `grep -n "def pruefe_ausstiege" */handeln.py` pruefen, dass Aufruf und
  Definition zusammenpassen - ein geaenderter Aufruf ohne Parameter ist ein
  `TypeError` im naechsten Zyklus.

## Journalformate der Familien

- Kontrakt (`xperp`, `swap`): `eroeffnen`/`schliessen`, Betrag in `margin_usd`,
  dazu `nominal_usd`, Gebuehr und Funding als Spalten.
- Spot (`scanner`, `kraken`): `kauf`/`verkauf`, Betrag in `usd` bzw. `eur`,
  Gebuehr ist in der Zeile schon eingerechnet.
- `orbk`: die fertige Runde steht in `gv_usd`, Ausstieg im Feld `ausgang`
  (kein `aktion`).
- `gitter`: `KAUF`/`VERKAUF` mit `stufe`, Gewinn in `gw_usd`.
- Indikator (`squeeze`, `wavetrend`, `macd_mtf`, `supertrend`): `kauf`/`verkauf`,
  Betrag in `einsatz_usd` - **beim Kauf der Einsatz, beim Verkauf der Erloes**.
  Derselbe Feldname traegt zwei Bedeutungen.
- Keine Gebuehr im Journal UND kein `gebuehr_taker` in der `wachen.json`:
  `kosten = 0` ausweisen, nicht schaetzen. Steht die Gebuehr irgendwo, gehoert
  sie gelesen, nicht gerechnet.
- Feldnamen nie aus dem Kopf lesen: `head -1 <spur>/handelsjournal.csv` zeigt
  den Kopf, `grep -n "journal(" <spur>/handeln.py` die schreibenden Stellen.

## Neue Spur auswertbar machen

- Zwei Stellen, beide noetig: die Spur in `auswertung_alle.SPUREN` (sonst kennt
  `--spur` sie nicht) UND ein Zweig in `kennzahlen_fuer()`. Diese Funktion ist
  die EINE Zuordnung Spur -> Rechenweg; `main()` und `befehle.py /strategien`
  rufen beide sie.
- Fehlt der Zweig, faellt die Spur in den leeren `else`-Zweig und `/strategien`
  meldet "keine geschlossene Runde", obwohl Zeilen im Journal stehen - der
  Fehler sieht wie fehlende Daten aus, nicht wie eine Luecke im Code.
- Rechenweg als eigene Funktion je Journalform (`runden_indikator`,
  `runden_spot`, `runden_xperp`, `runden_orbk`, `gitter_zyklen`) auf
  `_paare(...)` aufsetzen; Kosten in der Funktion begruenden, nicht im Aufrufer.
- Test, der den Anschluss festhaelt: Spur in `SPUREN` UND
  `"<GRUPPE>" in inspect.getsource(kennzahlen_fuer)`. Eine Spur nur in `SPUREN`
  sieht angeschlossen aus und ist trotzdem stumm.
- `MIN_RUNDEN` (8) gilt weiter: darunter ist die Zahl ein Befund, keine Messung;
  `/strategien` markiert sie mit `*`.

## Falsch geschriebene Zeilen archivieren, nicht loeschen

- Betroffenes Journal umbenennen (`handelsjournal.<fehler>-JJJJMMTT.csv`): es ist
  Beweis der Laufzeit, nicht Muell, und die Auswertung liest nur
  `handelsjournal.csv`.
- `journal()` legt eine fehlende Datei samt Kopfzeile selbst an - eine leere
  Auswertung danach ist erwartbar, kein Fehler.
- `zustand.json` NICHT zuruecksetzen: offene Positionen und ihre Einstandswerte
  waren richtig, falsch war nur die Ausstiegsrechnung.
- Die Quelle bleibt die Formel im `handeln.py` der Spur; ein Fix an den
  Journalzeilen ist keiner.
- Die Wirkung zeigt sich erst im naechsten Dauerlauf-Zyklus (die Spuren laufen
  als Unterprozess, das laufende Modul im Speicher traegt den alten Code).
  Nachweis ist eine neue Zeile mit plausibler Groessenordnung, nicht der gruene
  Test.

## Wiedereinstieg nach dem Ausstieg

- **Ein Ausstieg, der das Ziel erreicht, hat das Signal VERBRAUCHT.** Der
  Kandidat bleibt danach auf der Rangliste (sein Signal ist ja nicht
  verschwunden, sondern gerade erfuellt), und der naechste Zyklus kauft
  dasselbe Instrument zum fast selben Kurs neu: zwei Gebuehrenrunden fuer eine
  Bewegung. Nach einem Ausstieg mit Grund `ziel` deshalb das Instrument fuer
  `sperrfrist_nach_ziel_stunden` sperren (Zahl in der `wachen.json`, 0 = aus).
- **Zwei Mechanismen, zwei Zeitraeume.** Nach einem STOP gilt die laengere
  Abklingzeit in TAGEN (`abklingzeit_tage`, z. B. 4) — ein gescheiterter
  Versuch ist ein anderer Grund als ein gelungener. Nicht einen Mechanismus
  fuer beide Gruende bauen und nicht einen Zeitraum fuer beide.
- **Den ZEITPUNKT merken, nicht das Datum.** Fuer Stunden braucht der Zustand
  einen ISO-Zeitstempel je Instrument (`zustand["letzte_ziele"][inst]`),
  gesetzt in `pruefe_ausstiege` unmittelbar neben dem Stop-Merker und geprueft
  in der Kaufliste. Eine Tagesangabe macht aus 2 Stunden eine Sperre bis
  Mitternacht.
- **Altbestand-Rueckfall im Zustandslader**: `lade_zustand()` setzt das neue
  Feld auf `{}`, wenn die vorhandene `zustand.json` es nicht kennt — sonst
  faellt der naechste Zyklus ueber einen fehlenden Schluessel.
- **Ein kaputter Zeitstempel sperrt NICHT dauerhaft** (fail-open mit Meldung),
  sonst legt ein alter Zustand die Spur still. Der Rueckfall ist hier bewusst
  die Gegenrichtung zum Rest des Hauses: die Sperre schuetzt Gebuehren, keine
  Position.
- **Die Sperre muss im Ablehnungsprotokoll sichtbar sein** (eigener Grund
  "Sperrfrist nach Ziel-Ausstieg"), sonst liest sich die Stille wie "kein
  Kandidat" und beim Kalibrieren sucht man am falschen Ende.
- **Test mit GEGENPROBE.** Nur "in der Sperrfrist wird nicht gekauft" zu
  pruefen findet eine Sperre nicht, die nie aufgeht. Der Test braucht drei
  Faelle: Ziel-Ausstieg setzt die Sperre, STOP-Ausstieg setzt sie NICHT, und
  nach Ablauf der Frist wird wieder gekauft. Der Zweite ist der wichtigste — er
  haelt die beiden Mechanismen auseinander.

## Spurtests aufrufen

- Aus `<spur>/tests` heraus: `<Handel>/scanner/.venv/Scripts/python.exe -m unittest test_<spur>`
  (der Aufruf steht im Docstring der Testdatei). Eigene venvs haben nur wenige
  Spuren - im Zweifel den scanner-Interpreter nehmen.
- Aus dem Spurenordner scheitert `discover` mit "Start directory is not
  importable"; `-m unittest tests.test_x` laedt stattdessen `scanner/handeln.py`
  und endet mit "module 'handeln' has no attribute pruefe_einstieg". Das ist der
  Importpfad, kein Fehler der Spur.
