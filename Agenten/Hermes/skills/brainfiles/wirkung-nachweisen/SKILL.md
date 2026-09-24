---
name: wirkung-nachweisen
description: Use when ein Automat "ok" meldet, die Wirkung aber fehlt.
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Belege, Verifikation, Automatik, Betrieb, Handel, BrainFiles]
    related_skills: [trugschluesse, handel-spuren, systemdiagnose, dauerprozess-bewachen]
---

# Wirkung nachweisen — der Statusbericht ist nicht das Ereignis

Jeder Automat (Dauerlauf, Cron, Treiber, Agent) meldet ueber seinen EIGENEN
Zustand: "Zyklus ok", "laeuft", "live". Diese Zeile beweist nur, dass der
Fahrer gefahren ist — nicht, dass die Sache, die er fahren sollte, etwas getan
hat. Der teuerste Fehlschluss im Betrieb ist deshalb nicht ein Absturz, sondern
der Satz "X laeuft" auf Grund einer Statuszeile: er ueberlebt Wochen, weil
niemand nachsieht.

Dieser Skill ergaenzt `trugschluesse` (Zustandsaussagen an der Quelle belegen)
um die zweite Haelfte: die WIRKUNG. Er ist kein Leitfaden zum Anbinden einer
Spur (`handel-spuren`) und keine Systempruefung (`systemdiagnose`).

## When to Use

- ein Fahrer meldet den Lauf/die Spur als `ok`/`live`, und die Wirkung fehlt
  (kein Eintrag im Journal, keine Zeile in der Ausgabe, keine Datei)
- eine Spur/ein Cron ist "scharf" geschaltet, aber es passiert nichts
- vor der Meldung "X laeuft" oder "X ist live" an Max
- zwei Zeugen widersprechen sich: Fahrerlog gruen gegen Buch/Report leer
- eine Sperrmeldung im Chat klingt plausibel (`<spur>: --live angefordert, aber
  gesperrt: <grund>`) und Max fragt nach dem WARUM — dann zuerst pruefen, ob der
  GENANNTE Grund stimmt (Schritt 5), statt den Grund zu erklaeren

**Don't use for:** eine Zustandsaussage ohne Automatik (`trugschluesse`), einen
Prozess neu starten (`dauerprozess-bewachen`), eine Spur erst anbinden
(`handel-spuren`).

## Procedure

0. **Ein Befehl ist der SOLL-Stand, nicht der IST-Stand.** Bevor ein Schalter
   gesetzt wird, den Max befiehlt (`handel_erlaubt`, `freigabe.erfuellt`, ein
   Limit, eine Grenze): den Wert in der Datei LESEN. Steht er schon so, wird
   NICHT geschrieben - sonst entsteht ein leerer Diff, ein Commit ohne Aenderung
   und die Meldung, man habe gerade etwas bewirkt. Stattdessen die
   Wirkungskette nachmessen (Vorschau in der Fahrerumgebung, Konto-/Boersenzeuge,
   Journal) und den Ist-Stand berichten: "war schon gesetzt, hier ist der Beleg,
   dass es wirkt". Faellt beim Nachmessen ein Fehler auf, der die Anordnung
   faktisch wirkungslos macht, ist DAS der Befund - belegt: ein befohlenes
   Freischalten war laengst gesetzt, aber der erste signierte Leseaufruf des
   Zyklus scheiterte an einem nonce-Fehler, die Spur war also scharf und
   trotzdem blockiert. Ein Nebeneffekt auf einem ANDEREN Gegenstand ist oft das
   einzige Symptom.

1. **Behauptung und ihre Quelle trennen.** Schreib hin, wer was gesagt hat:
   `dauerlauf.log` sagt `(live) ok`; das Journal sagt gar nichts. Das sind zwei
   verschiedene Saetze.
2. **Zeugen am GEGENSTAND holen**, nicht am Fahrer. Je Automatik:

   | Gegenstand | Zeuge |
   |---|---|
   | Handelsspur | Journalzeilen mit der echten Aktion (`kauf`/`verkauf`, `modus=live`), dazu die Boerse (`/account/positions`, Kraken Balance+OpenOrders) |
   | Cron/Aufgabe | was der Job ins Ziel geschrieben hat (Nachricht, Datei, DB-Zeile), plus `Get-ScheduledTaskInfo` fuer den Lauf selbst |
   | Feed-/Papierspur | Zeilen mit Handelsaktion, nicht `zyklus`/`funding`/`quotes` (Betriebszeilen sehen wie Betrieb aus) |
   | Agent/Treiber | Ergebnisdatei des Auftrags, nicht der `gestartet/gestoppt`-Zaehler |

3. **Die Sonde in der UMGEBUNG des Fahrers fahren.** Ein Probelauf ohne die
   Variablen, die der Fahrer setzt, misst einen anderen Codepfad und "beweist"
   Unschuld:

   ```bash
   cd <spurordner> && MAXHIRN_ROUTINE=1 <spurinterpreter> handeln.py --vorschau
   ```

   `MAXHIRN_ROUTINE=1` heisst "hier sitzt niemand" und wird vom Dauerlauf in
   BEIDEN Modi gesetzt. Ohne die Variable sieht dieselbe Spur frei aus, mit ihr
   gesperrt — der Unterschied ist der Befund, nicht das Rauschen.

4. **Die Sperrenkette des Gegenstands selbst lesen** (die eigene
   `--vorschau`/`--wachen`-Ausgabe), nicht die Kriterien des Fahrers. Ein Fahrer
   oeffnet nur dann von selbst eine Freigabe, wenn der Sperrtext GENAU EINEN
   Grund nennt und darin das erwartete Wort steht — eine Schleife aus
   schliessenden und wieder oeffnenden Fenstern ist das typische Symptom.

5. **Pruefe, ob der genannte Grund ueberhaupt WAHR ist**, bevor du an der Spur
   reparierst. Ein Sperrtext ist eine Aussage, kein Messergebnis. Rezept fuer
   jede Spur, aus der Repo-Wurzel:

   ```bash
   # a) Was steht WIRKLICH in der Zustandsdatei, die das Tor liest?
   python -c "import json;print(json.load(open('Agenten/Handel/freigabe_fenster.json',encoding='utf-8'))['<spur>'])"
   # b) Was liest die SPUR, wenn sie wie beim Fahrer startet (cwd = Spurenordner)?
   cd Agenten/Handel/<spur> && MAXHIRN_ROUTINE=1 <spurinterpreter> -c \
     "import handeln; print(handeln.zeitfenster_offen())"
   ```

   Widersprechen sich a und b, ist nicht die Lage kaputt, sondern die Wache —
   und die falsche Zeile steht als Meldung im Chat. Den Widerspruch vor dem Fix
   mit beiden Ausgaben zitieren (er ist der Nachweis, dass die Reparatur etwas
   aendert), danach dieselbe Sonde wiederholen: b muss a entsprechen.

6. **Erst dann melden**, mit beiden Zeugen im selben Lauf zitiert.

## Pitfalls

- **Zwei Formen derselben Bedingung: eine kann still fehlen.** Eine Freigabe
  existiert am Bildschirm (Fenster, Klick je Vorgang) UND im Dauerbetrieb
  (Zeitfenster/Zustandsdatei, vom Fahrer oder per Befehl geoeffnet). Eine Spur,
  die nur die Bildschirmform prueft, kann im Fahrerbetrieb NIE durchkommen —
  waehrend der Fahrer sie als "live" protokolliert und im festen Takt Fenster
  oeffnet, die nichts loesen. Beim Nachbauen immer beide Formen einbauen und den
  Sperrtext woertlich dem der nachgebauten Spur angleichen.
- **Ein Tor, das den Zustand liest, den nur der freigegebene Weg schreibt, kann
  nie aufgehen.** Der Herzschlag (Bedingung 3) ist Voraussetzung jeder Freigabe:
  kommt er aus der Zustandsdatei des LIVE-Buchs, dann frischt ihn nur ein
  Live-Lauf auf, ein Live-Lauf startet nur bei offenem Fenster, und das Fenster
  oeffnet der Fahrer nur bei frischem Herzschlag — ein Kreislauf, der sich
  selbst blockiert. Die Spur bleibt fuer immer Papier, waehrend alles "scharf"
  gesetzt aussieht. Der Herzschlag misst die SPUR, nicht den Pfad — und er muss aus dem
 FRISCHESTEN der beiden Staende kommen, die es je Spur geben kann
 (Papierzustand UND Live-Zustand), nicht aus einem von beiden.
 Nur der Live-Zustand ist der Kreislauf oben. Nur der Papierzustand ist die
 ZWEITE Falle, genau so gemessen: laeuft die Spur live, schreibt der
 Papierzweig nichts mehr, der Papierzustand fror ein — und nach der
 Herzschlag-Grenze sperrte sich die Spur SELBST ("Live waere gesperrt durch:
 Herzschlag alt"), obwohl sie alle 15 Minuten live lief. Faellt das Sperrwort
 auf "Herzschlag alt" bei einer Spur, die nachweislich zyklisch laeuft, ist
 die QUELLE des Herzschlags falsch, nicht die Grenze. Beide Staende zu
 vergleichen macht den Kreislauf unmoeglich, ohne den Sinn zu aendern: nur
 Papier sperrt eine Spur, die noch nie live lief, nur Live ist ein Kreislauf.
  Belegt: eine fertig verdrahtete Spur mit `handel_erlaubt`/`freigabe.erfuellt`
  true blieb Papier, weil ihre Vorschau ZWEI Gruende nannte (Herzschlag alt +
  Fenster) und der Fahrer bei zwei Gruenden kein Fenster oeffnet. Nachweis der
  Reparatur ist die Fahrerzeile `Auto-Freigabe <spur>` plus der naechste Zyklus
  `(live)` — die eigene Vorschau allein belegt es nicht.
- **Eine Statuszeile im Log ist der Modus des Fahrers, kein Orderbeleg.**
  Massstab ist die Zeile mit der Aktion am Gegenstand (Journal/Boerse).
- **Ein stiller `except`-Zweig macht aus einem Beweis ein Nichts — und aus
  einem Fehler eine Behauptung.** Zwei Faelle, eine Wurzel. (a) Die
  Protokollierung im `try` zu haben ist gut, aber dann muss die Funktion
  isoliert aufrufbar und einmal pruefbar sein — sonst verschwindet der Fehler in
  `except: pass` und die Wirkung fehlt lautlos (belegt: ein `AttributeError` VOR
  dem `try` liess jeden Einstieg mit "nicht verfuegbar" enden, und weil der
  Betriebspfad ihn nie erreichte, fiel es lange nicht auf). (b) Der Zweig gibt
  einen ERFUNDENEN Zustand zurueck und der Sperrtext behauptet ihn danach als
  Tatsache: `except Exception: return False` in einer Torpruefung heisst
  "Bedingung nicht erfuellt", obwohl nur das PRUEFEN scheiterte. Fail-safe
  handeln ist richtig, laut melden ist Pflicht — nach `stderr` schreiben und den
  Text vom Befund trennen ("nicht lesbar" ist nicht "ist zu").
- **Module aus dem Elternordner im Spurlauf ueber den PFAD laden.** Eine Spur
  startet mit ihrem EIGENEN Ordner als `sys.path[0]`; ein blankes
  `import <elternmodul>` (`freigabefenster`, `freigabe`, `ratschen`,
  `risikostufe`, `spur_buch`) findet dort nichts und wirft
  `ModuleNotFoundError` — der im `except` zu einem falschen Sperrgrund wird.
 - **Ein halber `except` faengt nur die Haelfte — und der Rest kippt den GANZEN
 Lauf.** Ein Zweig auf einen HTTP-Statuscode (429) faengt keinen
 Verbindungsabbruch, keinen Timeout und keine mitten im Rumpf abgeschnittene
 Antwort; diese Ausnahme laeuft aus der Datenschicht bis in den Fahrer und macht
 aus einem Zyklus eine Rueckgabe 1 mit Alarm, obwohl die Logik gesund ist. Bei
 jedem `except` in einem Abruf-Pfad hinschreiben, was im NICHT gefangenen Fall
 passiert, und die Netzklasse fangen (`URLError`/`OSError`/`ValueError`),
 einmal nachfassen, dann `None`. Der Nachweis ist dann die **Rueckgabe des
 ganzen Laufs** (0), nicht die Feststellung, dass die Ausnahme nicht mehr
 fliegt — plus eine Gegenprobe, dass die gesunde Leitung weiter bucht.
  Richtig: `spec_from_file_location` mit absolutem Pfad oder
  `sys.path.insert(0, HANDEL)` VOR dem Import. Belegt: eine live geschaltete
  Spur handelte Papier, waehrend der Fahrer `(live)` protokollierte, und der
  Fahrer OEFFNETE im festen Takt Freigaben, weil er dem falschen Grund glaubte.
- **`HIER`/`HANDEL` sind nicht ueberall `Path`.** In manchen Spuren sind sie
  Strings (`os.path.dirname`), in anderen `Path`-Objekte. `str(HIER.parent)`
  wirft im String-Fall `AttributeError`; wer einen Block aus einer Spur mit
  `Path` in eine mit String kopiert, bricht den Pfad-Eintrag still. Vor dem
  Kopieren nachsehen, dann `sys.path.insert(0, HANDEL)` schreiben.
- **Eine Uebersprung-Wache, die fuer einen Teil gebaut wurde, schaltet den Rest
  mit ab.** Eine Routine, die "ueberspringen, solange der Fahrer laeuft" meldet
  und mit Code 0 endet, sieht gesund aus — sie kann aber seit dem Dauerbetrieb
  gar nichts mehr getan haben. Vor der Betriebsaussage ueber eine Aufgabe
  pruefen, WAS sie inzwischen ueberhaupt noch tut (der ausgenommene Teil kann
  laengst entfernt sein), und das Alter ihres ERZEUGNISSES messen, nicht ihren
  Exitcode. Belegt: ein Tageslauf uebersprang sich selbst, sein Bericht war
  einen Tag alt, und eine Spur kaufte danach zu diesen alten Preisen.
- **Der stille Skip hat einen Namen: Exitcode 0 plus `uebersprungen`.** Gemessen
  24.09.2026 an der Fremdarbeit-Routine: bei liegender `.git/index.lock` endet ihr
  Lauf mit Code 0 und der Zeile `ENDE uebersprungen` - `Get-ScheduledTaskInfo`
  zeigt `LastTaskResult: 0`, die Aufgabenplanung meldet also ERFOLG. Eine Nacht
  lang wurde nichts uebernommen, 44 Dateien lagen bis zu 44 h im Baum. Wer den
  Ausfall sucht, liest nicht den Exitcode, sondern den GRUND in der Logzeile (bei
  dieser Routine gibt es zwei: falscher Zweig, liegende Sperre) und misst das
  Alter des ERZEUGNISSES. Das Log war ein Einzellauf-Protokoll und beim naechsten
  Lauf ueberschrieben - den Befund also sofort abschreiben, danach hilft nur noch
  die Historie der Uebernahme-Commits (`git log --author=fremd@local`). Weckzeichen
  im Alltag ist die Zeile "N uncommittete Datei(en) aelter als 1 h" des
  Tagesberichts; danach gehoert der Ausfall bewacht
  (`Agenten/Hermes/scripts/sperren-wache.py`, Cron `sperren-wache`), nicht nur
  repariert.
- **Der Fahrer meldet jede Spur als `ok`, auch wenn sie intern Papier handelt.**
  Vor "die Spur handelt live" immer die Journalzeilen mit `modus=live` zaehlen
  (0 heisst: kein einziger Vorgang).
- **Tests, die Seams patchen, muessen sie zuruecknehmen.** Echte Funktionen VOR
  dem Patchen sichern und im `tearDown` zurueckholen; sonst prueft der naechste
  Test den Fake des Vorgaengers (`setUp` hatte die echte Funktion schon
  ersetzt) und bleibt gruen, ohne etwas zu pruefen. Das Zeitfenster der Spur in
  Tests auf einen Festwert patchen — ein Test darf nicht davon abhaengen, ob Max
  gerade freigegeben hat.
- **Ein Test, der das falsche Modul laedt, ist gruen, ohne etwas zu pruefen.**
  Laedt die Suite vorher eine Nachbarspur (die ihre Pfade selbst auf `sys.path`
  legt), stehen diese Pfade schon in der Liste — ein `if p not in sys.path:
  insert(0, p)` sieht "schon da" und schiebt den EIGENEN Ordner nie nach vorn,
  und `import handeln` holt das `handeln.py` der Nachbarspur. Den eigenen Ordner
  unbedingt (ohne Vorbedingung) per `insert(0, ...)` nach vorn legen und mit
  `assert modul.__file__.startswith(SPUR)` absichern — ein gruener Lauf ohne
  diese Zusicherung beweist nichts.
- **Ein "nichts abzusetzen" ist eine Aussage, die man belegen muss.** Bevor ein
  Auftrag wie "storniere die Order" als erledigt oder als gegenstandslos
  gemeldet wird, drei Stellen lesen: den Orderpfad im CODE (gibt es ueberhaupt
  einen Aufruf, oder nur Signalbuchung?), das eigene Buch (Journalzeilen mit
  echter Aktion) und die BOERSE (`offene_orders`). Ein leeres Ergebnis an allen
  drei Stellen ist ein vollwertiges Ergebnis — es gehoert mit den drei Aufrufen
  in die Antwort, nicht als Vermutung.
- **Bevor du einen roten Test dir zuschreibst oder freisprichst: den A/B-Lauf
  fahren.** `git stash push -- <datei>` (nur die eigene Aenderung), Suite laufen
  lassen, `git stash pop`, Suite erneut. Sind beide Zahlen gleich, ist der
  Fehler vorbestehend. Ohne diesen Lauf wird entweder eine fremde Regression als
  eigene gemeldet (und an der falschen Stelle gesucht) oder die eigene Aenderung
  als unschuldig durchgewinkt. Das Urteil mit BEIDEN Zahlen belegen
  ("vorher 30 Fehler, nachher 30") — nicht nur mit dem Wort "vorbestehend".
  `git stash` nie auf den ganzen Baum anwenden: parallel laufende Fremdarbeit
  verschwindet sonst mit.
- **Zaehle mit der Hausdefinition, nicht mit einer eigenen Wortliste.** Ein
  selbstgebautes Auswertungsskript, das seine Aktionswoerter selbst mitbringt,
  zaehlt jede Komponente falsch, die ein anderes Schema fuehrt (belegt: eine
  Spur mit acht abgeschlossenen Runden stand als "still, 0 Einstiege" da, weil
  sie keine `aktion`-Spalte schreibt, sondern `ausgang`). Die Woerter und die
  Trennung echter Runden von Betriebszeilen aus dem EINEN Modul nehmen, das sie
  im Haus definiert (hier `stoerungen.py`), per `spec_from_file_location` laden
  und dessen `teile()`/`ist_stoerung()` aufrufen. Faellt der eigene Zaehler
  daneben, ist zuerst der Zaehler falsch — nicht die Komponente.

## Verification

Ein Nachweis ist vollstaendig, wenn Statuszeile UND Wirkung im selben Lauf
sichtbar sind:

```bash
# Fahrer
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && grep -n "<spur>" dauerlauf.log | tail -3
grep -c ",live," <spur>/handelsjournal.csv          # 0 = nie gehandelt
# Gegenstand in der Fahrer-Umgebung
cd <spur> && MAXHIRN_ROUTINE=1 <spurinterpreter> handeln.py --vorschau
# Unversehrtheit der Nebenwege
cd .. && python spiegelstand.py | tail -3
```

Erwartet: die Statuszeile, mindestens eine Aktionszeile am Gegenstand (oder das
ehrliche "0"), und die Vorschau-Zeile unter denselben Variablen wie der Fahrer.
Eine Null ist ein Ergebnis und gehoert in die Antwort — "laeuft" ohne sie nicht.

Nach einem Absturzfix ist der Nachweis die Rueckgabe des GANZEN Laufs: den
festen Lauf mit nachgestellter Netzstoerung (Double fuer `urlopen`) gegen einen
Temp-Ordner fahren und `0` erwarten - dazu den naechsten echten Zyklus im
Fahrerlog zeigen. Rezept und Fallunterscheidung Netzfehler/Spurenfehler:
Skill `handel-spuren`, `references/betriebsfehler-spuren.md`.
