# Risikostufen: derselbe Handel, andere Buchgroesse

Gehoert zu den Handelsspuren (`Agenten/Handel`). Zweck: mehr Beobachtungen je
Zeiteinheit, ohne eine Strategie zu aendern. Bei kleinen Einsaetzen dauert jede
Statistik Monate; mit dem Faktor sieht man denselben Fehler schneller. Ein
Messwerkzeug, kein Gewinnhebel.

## Bauform

- `Agenten/Handel/risikostufe.py` ist die EINE Umsetzung. Der Dauerlauf setzt je
  Stufe `HANDEL_RISIKO=niedrig|mittel|hoch` (Faktor 1 / 2 / 4) in die
  Prozessumgebung der Kindprozesse.
- **Ohne die Variable aendert sich nichts.** Das ist die Bedingung, unter der eine
  solche Umstellung in laufenden Handelscode darf: Basis = Faktor 1.0, kein
  Suffix, identisches Verhalten.
- Zustand und Journal MUESSEN je Stufe getrennt liegen
  (`zustand.mittel.json`, `handelsjournal.mittel.csv`, ueber `datei()`): zwei
  Laeufe auf derselben Datei ueberschreiben sich die Positionen. `journal_zweitziel`
  bleibt dagegen unveraendert — `spiegele_journal` kopiert unter dem QUELLnamen
  nach Q:, die Kopien heissen also von selbst `zustand.mittel.json`. Kein eigener
  Zielordner noetig.
- Ein unbekannter Wert zaehlt als Basis. Ein Tippfehler („mitel") darf nicht still
  die vierfache Position handeln.
- `datei()`/`datei_fuer()` erhalten den Pfadtyp: aus `str` kommt `str`, aus
  `Path` kommt `Path`. `scanner/handeln.py` ruft `.read_text()` auf dem Ergebnis
  auf — ein zurueckgegebener str waere dort ein Attributfehler im Zyklus.

## Was skaliert wird - und was nie

Positivliste, KEIN Namensmuster. Die naheliegende Regel „alles mit `_usd`" ist
falsch: an den echten Wachen gemessen trifft sie Felder, die keine Einsaetze sind.

| nicht skalieren | warum |
|---|---|
| `marketcap_band_usd` | Marktgroesse eines Tokens, kein Einsatz |
| `groesster_ruecklauf_papierlauf_*` | eine MESSUNG; skaliert waere sie eine Behauptung ueber die Vergangenheit |
| `mindest_guthaben_*`, `mindest_marge_frei_*` | Kontoschwellen der Boerse |
| `umsatz_bezug_usd`, `punkt_wert_usd` | Handelsvolumen, Vertragsgroesse |
| Felder mit fuehrendem `_` | dokumentierter Vorwert |

Skaliert werden die Begrenzer der Buchgroesse: `risiko_je_position_*`,
`risiko_pro_trade_*`, `risiko_je_anlauf_*`, `max_pro_trade_*`, `max_gesamt_*`,
`max_margin_*`, `max_einsatz_*`, `einsatz_usd`, `max_verlust_usd`, `stop_usd`.

**Mit skalieren MUSS die Ratsche** (`drawdown_halbierung_usd`) **und der
Kill-Schalter** (`kill_switch_gesamt_*`): beide sind in Buchrisiko ausgedrueckt
(1,0x, siehe `ratschen.py`). Blieben sie stehen, loeste die doppelte Position die
Halbierung nach dem ersten Verlust aus - die Stufe waere gesperrt und lieferte
keine Daten.

## Drei Regeln, die eine Stufe erst ungefaehrlich machen

1. **Nie live.** `risikostufe.live_erlaubt()` ist nur in der Basis true, und der
   Dauerlauf uebergibt auch bei offenem Freigabefenster `--papier`. Grund: das
   Buch der Stufe ist getrennt - live gehandeltes Geld stuende in keiner
   Auswertung, und derselbe Handel mit vierfachem Einsatz bringt keinen
   zusaetzlichen Erkenntnisgewinn.
   **Die Frage "mittel oder hoch?" ist bei einem Live-Vorhaben deshalb die
   falsche Frage:** eine Spur, die live handeln soll, gehoert in den BASIS-Lauf.
   Die Stufen sind ein Messwerkzeug fuer Papiervarianten; wer sie fuer echtes Geld
   vorsieht, baut einen zweiten Live-Pfad, dessen Buch in keiner Auswertung steht.
   Auf "welche Stufe fuer live?" ist die Antwort also: keine, sondern Basis.
2. **Kein Telegram.** Kein Senden, kein Abholen von Befehlen, keine
   Freigabe-Anfrage, kein Schliessen der Fenster beim Beenden. Zwei Dauerlaeufe
   an einem Bot nehmen sich die Nachrichten weg (Telegram: 409), und ein `/ja`
   waere nicht mehr zuzuordnen.
3. **Spiegel nur in der Basis.** Er hat in jeder Stufe denselben Einsatz
   (Vorgabe Max), ein zweites Buch waere dieselbe Beobachtung noch einmal - und
   zwei Laeufe schrieben in dieselben Dateien. `dauerlauf.NUR_BASIS` ueberspringt
   ihn, `spiegel.py` bricht in einer Stufe mit Klartext ab.

## Anschliessen je Spur (so ist es gebaut)

Es gibt keine zentrale Stelle: jede Spur bildet ihre Dateinamen selbst. Je Spur
sind es drei Eingriffe, alle nach demselben Muster:

1. `risikostufe` ueber den PFAD laden (wie `ratschen.py`) - die Spuren haben ihren
   eigenen Ordner als `sys.path[0]`, ein `import` auf `Handel/` scheitert.
2. Die Wachen nach dem Laden durch `skaliere(...)` schicken. **Die Wachen-Funktion
   ist der richtige Ort**, nicht `lauf()`: nur so kann ein Test dieselbe Funktion
   befragen, die der Betrieb benutzt.
3. `ZUSTAND`/`JOURNAL`/`ABLEHNUNGEN` (und `nautilus`: `KOPIER_*`) ueber `datei(...)`
   benennen.
4. Werkzeuge (`auswertung.py` je Spur) laden `risikostufe` **ausfallsicher**:
   `try: ... except Exception: risikostufe = None`, danach ein `_stufe(pfad)` als
   Rueckfall auf den Basisnamen. Grund: der Tagesbericht laedt
   `<spur>/auswertung.py` ueber den PFAD, und seine Tests kopieren die Datei in
   einen temp-Ordner - dort liegt `risikostufe.py` eine Ebene hoeher nicht, und
   ein harter Import schreibt „Auswertung nicht lesbar" in JEDEN Bericht. Ein
   Werkzeug darf nie daran scheitern, dass eine Stufe fehlt.

| Spur | Wachen aus | Dateien in |
|---|---|---|
| xperp | `bot.wachen()` | `handeln.py` |
| scanner, kraken | `scan.wachen()` | `handeln.py` |
| swap | `handeln.wachen()` | `handeln.py` |
| orbk | `handeln._wachen()` | `handeln.py` |
| kopier, kopier1zu1, nautilus, omniquant, gitter, squeeze, supertrend, wavetrend, macd_mtf, mosaic | `lade_wachen()` | `handeln.py`/`kopier.py` |
| spiegel | — (nur Basis) | — |

Werkzeuge, die eine FREMDE Stufe ansehen, nehmen `datei_fuer(pfad, stufe)` statt
der Umgebungsvariable: `spiegelstand.py` und `auswertung_alle.py` haben ein
`--risiko`, die `auswertung.py` in kopier/kopier1zu1/omniquant/gitter folgen der
Umgebungsvariable (dort wie die Spur selbst starten).

Betrieb:

- `dauerlauf.py --risiko mittel`: eigene Logdatei (`dauerlauf.mittel.log`) und
  eigene PID-Datei (`dauerlauf.mittel.pid`), sonst haetten sich zwei Laeufe
  gegenseitig „laeuft schon" gemeldet.
- `Routinen/handel-dauerlauf.ps1 -Risiko mittel`: Waechter-Aufruf der Stufe; er
  prueft `dauerlauf.mittel.pid` und steigt mit „laeuft bereits" aus. Dauerhaft
  gehoert dorthin eine EIGENE geplante Aufgabe (Anmeldung + alle 30 Minuten,
  Aktion mit `-Risiko mittel`) - der Basis-Waechter ruft den Wrapper OHNE den
  Schalter und startet eine Stufe nach einem Neustart deshalb nicht.
- **Neue Dateinamen sind erst aus dem Verlauf heraus, wenn eine Sperrzeile sie
  nennt.** `zustand.mittel.json` fiel unter die `*.json`-Freigabe (die Journale
  deckte `*.csv` schon ab) und waere sonst die einzige Zustandsdatei im
  Verlauf. Pruefen mit `git check-ignore -v <pfad>`; liegt die Spur in einem
  EIGENEN Repo (`nautilus/`), dort separat sperren - die BrainFiles-Sperre
  erreicht sie nicht.

## Die PID-Datei ist eine Pruefen-dann-Handeln-Sperre

Die je-Stufe-PID-Datei (`dauerlauf.pid`, `dauerlauf.mittel.pid`) verhindert
zwei Laeufe bei ruhigem Betrieb — aber sie ist keine Sperre: lesen, starten,
PID schreiben hat ein Zeitfenster. Feuern zwei Trigger gleichzeitig
(Anmeldung + Zeittrigger-Waechter), lesen beide „frei" und beide starten;
Mehrfachinstanzen DERSELBEN Stufe sind die Folge (dreimal Basis beobachtet),
auf gemeinsamem Zustand und einem Telegram-Token — die Befehle erreichen nur
eine, die anderen schreiben still mit.

- Instanzen zaehlen wie Prozesse zaehlt: Launcher+Kind-Paare nach
  `CreationDate` gruppieren (`Get-CimInstance Win32_Process`, Kommandozeile
  `*dauerlauf.py*`), nicht nach Prozessname und nicht nach PID-Zahl.
- Eine stale PID ist keine Sperre: der Waechter ersetzt die Datei, wenn die
  PID nicht lebt — und laesst die ORIGINAL-Instanz unerkannt weiterlaufen.
- Die robuste Form haelt eine OS-Dateisperre ueber die Lebensdauer des
  Prozesses (Muster `skillsbot.py`: `msvcrt.locking`/`fcntl.flock`). Wer die
  PID-Datei nicht ersetzen kann, haelt wenigstens die Schreib-Reihenfolge
ein: erst pruefen, dann starten, dann PID schreiben — und die Datei beim
Ende IMMER mitnehmen.

## Zwei Schreiber machen die Messreihe wertlos

Eine Stufe ist nur so viel wert wie ihre Buchfuehrung: laufen zwei Prozesse auf
denselben `zustand.mittel.json`, sind die Positionen doppelt und jede Zahl
unbrauchbar. Beim Starten eines zweiten Laufs von Hand deshalb:

- **Erst pruefen, dass kein Test-/Trockenlauf mehr lebt.** Ein venv-Python ist
  ein PROZESS-PAAR (Launcher-Shim + echtes Python); wird nur "die" PID beendet,
  laeuft der Lauf weiter und schreibt still mit. Nachsehen ueber die
  Kommandozeile, nicht ueber den Namen:

      Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -like '*dauerlauf.py*' } |
        Select-Object ProcessId, CommandLine

- **Nach einem Lauf ohne Freigabe die PID-Datei mitnehmen** (`rm dauerlauf.mittel.pid`),
  sonst meldet der naechste Waechter-Aufruf faelschlich „laeuft bereits".
- **Waren zwei Schreiber dran, die Buecher verwerfen und neu anfangen:** lokale
  `*.mittel.*` UND die Q:-Kopien loeschen (`Q:\Handel_Journal\<spur>\*.mittel.*`),
  Stufe neu starten. Nur die Basisdateien sind unantastbar - die Stufe ist eine
  Messreihe, kein Buch, das jemand liest.

## Leser gehoeren zum Auftrag, nicht zum Nachtrag

Eine zweite Buchfuehrung ist erst angeschlossen, wenn die WERKZEUGE sie zeigen
koennen - sonst sammelt die Variante Daten, die niemand sieht:

- Die GUI (`handelszentrale.py`) bekommt Umschalter und Startwert und bildet ALLE
  Pfade (Zustand, Journal, PID- und Logdatei, Konsole) ueber EINE Stelle
  (`stufenname()`). Nachweis ist der Aufruf MIT Variante
  (`handelszentrale.py --pruefen --risiko mittel` nennt PID und
  `zustand.mittel.json`), nicht nur der Basisaufruf.
- Der Tagesbericht bekommt eine Zeile je laufender Variante (Spuren mit Buch,
  Alter des juengsten Zyklus, Runden mit Summe; deutlich ueber dem Takt = „laeuft
  sie noch?") und laesst sie ohne Variante WEG. Die Buchliste aus dem Ordner
  lesen, NICHT `dauerlauf.SPUREN` importieren: `dauerlauf` importiert den
  Bericht, ein Rueckimport ist ein halb geladener Zyklus.
- **Zahlen in solchen Zeilen aus DERSELBEN Funktion holen, die die Auswertung
  benutzt** (`auswertung_alle.kennzahlen_fuer`, mit dem `HIER` des Berichts), nie
  aus einer zweiten Formel - eine zweite Formel laeuft beim naechsten Umbau still
  auseinander, und der Bericht behauptet dann etwas anderes als das Werkzeug.
- Gegenprobe in beide Richtungen: ohne Variante muss jede Ausgabe unveraendert
  sein (Basisnamen, keine Zusatzzeile, kein leerer Absatz).

### Der Bericht einer Stufe (25.09.2026)

`tagesbericht.py --risiko mittel|hoch` baut den GANZEN Bericht aus den Dateien
dieser Stufe; `--risiko alle` gibt Basis, mittel und hoch untereinander aus (die
XPERP-Rangliste ist eine Marktgroesse und wird EINMAL geholt, nicht je Stufe).
`baue(stufe_=...)` setzt `HANDEL_RISIKO` nur fuer die Dauer des Aufbaus und stellt
die Umgebung danach zurueck - ein Bericht darf den aufrufenden Prozess (den
Dauerlauf!) nicht umstellen.

Bis dahin kuendigte der Bericht die Stufe nur AN (`stufenzeile`) und las trotzdem
`zustand.json` und `handelsjournal.csv` der Basis - ein Kopf „Faktor 4" ueber den
Zahlen der Basis. Die Stufe wirkt jetzt ueber `lage._buch()`:

- Suffix an `zustand*` und `handelsjournal*`, auch an Arm- und Fassungsnamen
  (`zustand.knapp.json`, `handelsjournal.weit.csv`) - das Stufensuffix steht
  ZULETZT.
- **`wachen.json` bekommt NIE ein Suffix.** Die Wachen werden beim Laden skaliert
  (`risikostufe.skaliere`), die Datei behaelt ihren Namen. Mit Suffix gelesen
  waere die Wachenlage jedes Stufenberichts leer und jede Sperre darin falsch.
- Jede weitere Datei eines Buchs gehoert durch `_buch`, sonst zeigt der Bericht
  sie wieder aus der Basis. `_lies()` ist der eine Weg zu Zustandsdateien - dort
  ist der Aufruf eingebaut, die Journalpfade in den Spur-Rueckgaben tragen ihn
  ebenfalls.
- **Auch die Zahlen aus `auswertung_alle` brauchen die Stufe.** Dort ist
  `STUFE` eine MODULVARIABLE (Vorgabe `None` = Basis; nur die Kommandozeile setzt
  sie), und `kennzahlen_fuer`/`hat_buch` lesen sie. `lage.zu_lage` stellt sie
  deshalb fuer die Dauer des Aufbaus auf die Stufe des Prozesses
  (`_stufe_der_umgebung`, Quelle `HANDEL_RISIKO`) und im `finally` zurueck — ohne
  das standen in einer Zeile die Positionen der Stufe und die Runden der Basis
  (7-Tage-Zeile in allen drei Berichten identisch).
- Pruefen: `tests/test_bericht_stufen.py` (18) haelt die Regel - Suffix ja/nein,
  `_lies` trifft die Stufendatei, eine echte Spur liest im Stufenlauf ihren
  Zustand aus der Stufe UND ihre Wachen aus der Basis, `--risiko alle` baut drei
  Berichte, Umgebung danach zurueckgestellt.

## Die Stufen gegen einander lesen

Drei Laeufe sind **kein Skalierungsexperiment**: jede Stufe fuehrt ihr EIGENES
Buch und eroeffnet ihre Positionen in ihren eigenen Zyklen. Gemessen standen bei
derselben Spur 20 Runden in der Basis gegen 11 in der mittleren Stufe, bei einer
anderen 123 gegen 229 — die Stufen handeln also nicht dieselben Geschaefte mit
anderem Einsatz, sondern VERSCHIEDENE Geschaefte. Eine Gegenueberstellung der
Summen mischt damit zwei Effekte (andere Trades UND groesserer Einsatz) und
misst am Ende Glueck mit.

- **Je Runde vergleichen, nicht die Summe** — `Ergebnis / Runden`, mit der
  Rundenzahl daneben. Der Quotient zwischen zwei Stufen muss in der Naehe des
  Stufen-Faktors (2 bzw. 4) liegen; ein Vielfaches davon zeigt andere Trades an,
  nicht einen besseren Einsatz.
- **Paaren, sobald es eine Aussage tragen soll:** je Instrument und ueberlappendem
  Zeitfenster die Runden einander zuordnen. Ohne diese Paarung ist der Vergleich
  eine Behauptung.
- **Erst ab der Mindest-Rundenzahl je Stufe** (die Grenze aus
  `auswertung_alle.py` nehmen, nicht selbst setzen). Eine frisch gestartete Stufe
  beginnt bei 0 Runden, fuellt ihre ersten aber schon in den ersten Minuten - ihr
  erster Zyklus eroeffnet selbst Positionen, und ein enger Stop schliesst sie
  sofort wieder. Der Massstab ist deshalb die RUNDENZAHL, nicht das Startdatum:
  „die Stufe ist neu" begruendet keine Aussage, „die Stufe hat 4 Runden"
  schon gar nicht. Das im Bericht sagen, statt eine Null - oder eine
  Ein-Runden-Zahl mit Vorzeichen - als Ergebnis zu lesen.
- **Vor dem Start der dritten Stufe die Last messen** (freier Commit): jede Stufe
  faehrt alle Objekte ein weiteres Mal. Rezept fuer den Waechter-Task der neuen
  Stufe (aus dem XML der Geschwisterstufe klonen): `dauerprozess-bewachen`,
  Abschnitt „Zweite Instanz“.

Stand 24.09.2026: Basis, `mittel` und `hoch` laufen gleichzeitig, jede Stufe mit
PID-Datei, Log und eigenem Waechter-Task.

## Pruefen

`Agenten/Handel/tests/test_risikostufe.py` faehrt ueber JEDE Spur: sie wird per
`importlib` geladen (wie im Betrieb) und dann gefragt, ob ihre Dateikonstanten den
Suffix tragen und ihre Wachen-Funktion die Betraege verdoppelt - in beiden
Richtungen. Dazu die Gegenprobe, dass der Spiegel die Basisnamen behaelt.

Nach jeder Aenderung an den Stufen:

    cd Agenten/Handel/tests && python -m unittest test_risikostufe
    cd Agenten/Handel && python spiegelstand.py          # Basis muss byte-gleich sein
    cd Agenten/Handel && python spiegelstand.py --risiko mittel

Der zweite Aufruf ist der eigentliche Nachweis: eine Stufe darf die Q:-Kopien der
Basis NICHT anfassen. Faellt dort eine Abweichung an, die es im Basislauf nicht
gibt, schreibt eine Stufe in Basispfade.

FALLE beim Nachweis: Nach einem Lauf der Spurentestsuiten meldet `spiegelstand.py`
kurzzeitig Abweichungen (beobachtet: scanner/ablehnungen.csv, orbk/zustand.json) -
die Tests schreiben in die ECHTEN Spurenordner, und Q: wird erst im naechsten Zyklus
nachgezogen. Das heilt von selbst; bleibt eine Abweichung ueber zwei Zyklen, ist es
ein echter Befund. Immer erst den naechsten Basislauf-Zyklus abwarten, bevor man
"Basis unberuehrt" behauptet.

Abgrenzung: `journal-spiegelung` (Kopie nach Q:), `dauerprozess-bewachen` (eine
Stufe ist ein eigener Dauerprozess mit eigener PID-Datei und eigener Wache).
