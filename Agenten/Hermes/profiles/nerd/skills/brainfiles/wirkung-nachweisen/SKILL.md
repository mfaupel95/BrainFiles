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
   | Waechter/Neustarter | der GESTARTETE Prozess bzw. die Zustandsdatei des Dienstes — nie die eigene Logzeile `Neustart ausgeloest` |
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
   cd "$HERMES_HOME/../.."   # Werkzeuge starten in Agenten/Hermes; alles hier ist relativ zur Wurzel
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

7. **Eine ZAHL und ein fremder Fix sind eigene Gegenstaende** — beide werden
   nachgerechnet, nicht geglaubt. Dieselbe Groesse ueber DREI unabhaengige Wege
   rechnen (Zeilenrechnung, Schluessel-Paarung, Hausfunktion); weichen sie ab,
   ist der AUSREISSER der Fehler, nicht die Mehrheit. Belegter Fall: ein Fix
   einer parallelen Sitzung war echt (Zaehler `0/1506` → `1506/1506`), aber die
   Hausfunktion lieferte fuer dieselben zwei Journale `-47.7` gegen `+492.26`
   aus zwei anderen Wegen — sie rechnete das Rundenergebnis ohne die
   HANDELSRICHTUNG, jede Short-Runde stand mit verkehrtem Vorzeichen im Buch
   (Trefferquote 54,2 % statt 33,2 %). Vor jedem eigenen Fix in geteiltem Code:
   erst `git log -- <datei>`, ob er schon da ist. Rezept, die zwei Fallen
   (fehlende Richtung, einseitige Summe) und die Werkzeugfallen:
   `references/zahlen-nachrechnen.md`.

## Pitfalls

- **In einem Watchdog ist LEER doppeldeutig — und die zweite Deutung ist die
  gefaehrlichere.** Das Muster „leere Ausgabe = nichts senden" haengt davon ab,
  dass die Pruefung ueberhaupt gelaufen ist. Leer kann aber auch heissen: die
  Pruefung hat ihr Ziel nie gefunden. `subprocess.run` auf einen fehlenden Pfad
  liefert **leere Ausgabe statt eines Fehlers**, und die Wette „leer ist gesund"
  liest das als Gesundheit — die Wache meldet taeglich „alles ok", ohne je etwas
  geprueft zu haben, und weil nichts auffaellt, faellt es nie auf. Gemessen: ein
  Auftragsskript band seine Wache als `HIER / "wache.py"` ein, wobei
  `HIER = Path(__file__).resolve()` die **Datei** ist — der Pfad zeigte auf ein
  Verzeichnis mit py-Namen darin. Drei Regeln: (a) den Werkzeugpfad ueber den
  **ORDNER** bauen (`SCRIPTS = HIER.parent`), wenn `HIER` die Datei bleibt;
  (b) den Pfad auf Existenz pruefen, BEVOR er benutzt wird; (c) ein
  **Fehlercode des Kindes ist eine Ausnahme**, kein leeres Ergebnis — und im
  Aufrufer darf ein Fehler der Pruefung nie in den stillen Zweig fuehren,
  sondern zu einem gemeldeten Exitcode (2 = Befund, nicht 0 = gesund).
  **Gegenprobe pflichtig:** den Fehlpfad zurueckbauen und pruefen, dass Tests rot
  werden. Ein Test, der den Fehlerpfad nicht kennt, prueft die
  Fehlerbehandlung nicht. Merksatz: **ein stiller Fehlpfad in einem Wecker ist
  die teuerste Form von gruen** — ein Test faellt auf, ein Wecker meldet
  „nichts".
- **Ein Auditor, der N Mal falsch alarmiert, ist schlimmer als keiner.** Ein
  breites Muster nannte elf Wachen mit „subprocess ohne `returncode`-Pruefung";
  von Hand nachgeprueft fangen die beiden ersten den Fehler aktiv ab
  (`except OSError` mit Klartext, danach `return ""` mit dokumentierter
  Bedeutung) — der Befund war falsch. Eine noch breitere Fassung nannte 63
  Dateien: das ist der Normalbau der Wachenfamilie. **Breite zuerst messen, dann
  verengen, NIE umgekehrt.** Nur eng genug traegt eine Aussage; und was bleibt,
  meldet die FORM, nicht den Zustand — ein Auditor kann nicht wissen, ob ein
  Werkzeug fehlt, ohne jeden Pfad zu pruefen, und ein Befund ohne Beleg waere
  das Gegenteil der Hausregel. `Agenten/Hermes/scripts/audit-werkzeugpfad.py`
  (Exit 1 = Befund) macht das fuer den Datei-Anker; `references/wachter-pruefen.md`
  traegt die Muster und die Fallunterscheidung.
- **Bei zwei gleichnamigen Ablageorten ist die Quelle der Wahrheit das
  SCHREIBENDE Modul, nicht die Pfadannahme.** Ein Datenbestand lag doppelt: im
  echten Ordner (dorthin schreibt das Abrufmodul ueber seine Konstante `ORDNER`,
  und von dort liest der Verbraucher) und daneben in einem zweiten Ordner ohne
  die Dateiendung, den kein Lauf liest. Ein Werkzeug, das den Pfand ANNIMMT,
  zaehlt drei verwaiste Dateien und meldet eine Luecke, waehrend 30 frische
  daneben liegen. **Der Beleg fuer „leer" oder „voll" ist die Diskrepanz
  zwischen dem, was der Abruf meldet, und dem, was auf der Platte liegt** — nicht
  ein Test mit einer Attrappe, denn eine Attrappe im falschen Ordner bestaetigt
  die Regel. Abhilfe: den Pfad aus dem schreibenden Modul holen und ihn als
  **Modulwert** ablegen, nicht als reiner Funktionsweg — sonst umgeht der
  Importweg jedes Umbiegen im Test.
- **Ein Fehler, der einen `mkdtemp`-Pfad nennt, ist eine Aussage ueber die
  FASSUNG, nicht ueber den Ort.** Legt der Test die Datei selbst an (`setUp`),
  ist die Meldung die ehrliche Beschreibung einer alten Testfassung: die hat
  eine Nachbar-Datei geschrieben, nicht die, die `spur_buch.zyklus` liest.
  Bevor am Code gesucht wird, die FASSUNG belegen — der Sitzungsspeicher
  beantwortet „welche Fassung lief" in Sekunden, und die git-Historie zeigt
  die Reparatur (`git log --oneline -- <testdatei>`). Ein Gegenbau derselben
  Attrappe OHNE die Datei muss mit derselben Meldung abbrechen; bricht sie
  durch, ist die Ursache nicht belegt.
- **Eine rote Suite im Worktree ist kein Befund, solange der HAUPTBAUM
  ungeprueft ist.** Ein Worktree kann ganze Ordner missen, die ausserhalb
  liegen (verschachtelte Repos, per `.gitignore` gesperrte Pfade) — jeder Test
  ueber `wachen.json`/`handeln.py` meldet dann `FileNotFoundError` fuer Code,
  den es gibt. Zweitens kann der Worktree mitten in der Pruefung verschwinden
  (der Worker beendet und raeumt auf), dann ist die Beweislage weg. Reihenfolge:
  Suite im Worktree fahren, **dann** dieselben Suiten im Hauptbaum, mit einem
  Vorher/Nachher-Waechter auf den echten Spurenordnern (`spiegelstand.py` als
  Abschlussbeleg). Erst ein Befund, der in BEIDEN Baeumen steht, ist ein Befund.
- **Ein Worktree-Test sieht eine ANDERE Datenwelt als das Haus — und meldet
  eine plausible Zahl statt eines Fehlers.** Ein Modul, dessen Datenordner
  relativ zur eigenen Datei liegt (`historie_binance.ORDNER =
  HIER/daten/historie`), liest in einem `git worktree` einen ANDEREN Ordner;
  ist der Datenordner nicht versioniert (`git check-ignore` belegt, `git
  ls-files` leer), existiert er dort gar nicht. Ein Replay-Test aus
  `.worktrees/<karte>/Agenten/Handel/tests` meldete deshalb „Historie fehlt,
  0 Kerzen" fuer Reihen, die im Haus vollstaendig lagen — die Fehlermeldung war
  richtige, der Schluss „348 Reihen weg" falsch. Vor jeder Verlustmeldung
  pruefen, aus WELCHEM Verzeichnis der rote Lauf kam (state.db, `session_id` +
  `cwd` des Aufrufers) und ob der Datenordner versioniert ist. Reproduktion:
  Modulkopie ohne `daten/` in einen Temp-Ordner legen — sie meldet belegt 0
  Kerzen.
  **Die Gegenmassnahme gehoert ins WERKZEUG, nicht in die Wachsamkeit:** prueft
  der Lader VOR dem Lesen, ob sein Ordner ueberhaupt existiert, und wirft einen
  BENANNTEN Fehler ("Ordner X nicht da — diese Kopie des Baums hat kein daten/"),
  dann sieht jeder kuenftige Lauf den Fehler statt einer plausiblen Null. Eine
  leere Liste ist die gefaehrlichste Rueckgabe eines Datenladers: sie ist von
  "wirklich keine Daten" nicht zu unterscheiden und wandert als Messergebnis in
  die Auswertung. Merksatz: **wo ein Lader leer zurueckgeben kann, gehoert eine
  Existenzpruefung mit benanntem Fehler hin** — die Regel gilt fuer jede relative
  Datenablage, nicht nur fuer diesen Ordner.
- **Eine Ordnermtime ist kein Loeschzeuge.** Sie aendert sich bei JEDEM
  Eintrag — auch wenn ein Unterordner angelegt wird. `daten/backtest/orb` mit
  mtime 04:23:17 sah aus wie der Moment des Verschwindens, war aber ein
  Replay-Unterordner, der NACH dem Ereignis geschrieben wurde. Ein mtime-
  Treffer ist ein Hinweis auf einen Zeitpunkt, kein Beweis fuer eine Aktion;
  die Aktion belegt der Aufruf (state.db `tool_calls`), nicht der Zeitstempel.
- **Eine Wache, die einen wachsenden Datenstand bemerkt, darf ihn nicht selbst
  beheben.** Nachfuellen gehoert entschieden, nicht gemeldet: ein Top-N-Universum
  bedeutet Tausende Kerzen und echte Laufzeit, und das ist eine Produktentscheidung.
  Muster: melden nach ALTER (nicht nach Kalender) und nach der Zahl, die der
  Verbraucher selbst verlangt (aus seinem Quelltext lesen, nicht schaetzen) —
  sonst ist die Wache strenger als der Lauf, den sie warnt, und meldet einen
  Lauf, der laeuft. Nur die Takte beobachten, die ein Lauf wirklich liest;
  Altbestand ohne Leser waere taegliches Rauschen. Leer = gesund (Watchdog).
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
- **Eine Zahl in der eigenen Doku ist eine Behauptung — sie braucht die Ausgabe,
  die sie gedruckt hat.** Lange Werkzeug-Ausgaben kommen gekuerzt zurueck
  (`… 1 lines output`, oder nur Kopf und Fuss); wer danach aus dem Gedaechtnis eine
  Zahl in Wiki, Notiz oder Bericht schreibt, veroeffentlicht eine Schaetzung im
  Kleid einer Messung — und sie ueberlebt, weil niemand nachrechnet. Gemessen: in
  einer frisch geschriebenen Wiki-Seite stand „Mittel 38,5 gegen 38,0", ein
  spaeterer echter Lauf zeigte fuer beide Fenster exakt gleiche Summenwerte. Bevor
  eine Zahl in eine Doku geht: die Sonde erneut fahren und die Zahl aus DER Ausgabe
  lesen — oder sie ausdruecklich als ungemessen kennzeichnen. Gegenprobe fuer eine
  fertige Doku: zu jeder Zahl den Lauf nennen koennen, der sie gedruckt hat.
- **Ein Lauf `ok` ist kein Zustellbeleg.** Ein Cron-Auftrag meldet seinen
  Exit-Code; ob die Nachricht ankam, steht woanders - im Job-Satz
  (`last_delivery_error`) und in der Ausgabedatei unter
  `cron/output/<job-id>/`. Ein Auftrag mit `deliver: all` scheitert, sobald EIN
  Kanal nicht kann (Photon/iMessage, SMS): der Lauf bleibt gruen, und niemand
  bekommt etwas. Auf einen Kanal umstellen, der nachweislich liefert, und das
  BELEGEN statt annehmen: einen EINMAL-Auftrag auf genau diesen Kanal feuern
  (Skript unter `Agenten/Hermes/scripts/`, absolute Pfade werden abgewiesen),
  den Zustellstatus lesen, danach Auftrag und Testskript wieder entfernen. Bleibt
  der Fehler, liegt die Ursache auf der Anbieterseite und gehoert als solche
  berichtet (Drosselung fuer NEUE Kontakte: „replies are limited … until they
  respond“ - die Behebung liegt beim Empfaenger, nicht im Code); die Gegenprobe
  nach der Behebung ist derselbe Einmal-Auftrag mit leerem
  `last_delivery_error`.
- **Ein Neustart-Waechter protokolliert seinen VERSUCH, nicht den Erfolg — und darf
  nicht ueber den Weg melden, den er ueberwacht.** `… kein Gateway-Prozess - Neustart
  ausgeloest` liest sich wie eine Erfolgsmeldung und ist nur die Absicht: ob der Start
  gelungen ist, steht nirgends. Gemessen: so eine Zeile lief eine Stunde lang alle zwei
  Minuten, waehrend der Dienst durchgehend tot war — die Ursache lag im Startweg selbst
  (der Launcher konnte gar nichts starten), und weil die Wache ihre Meldung ueber den
  Bus schickte, der an genau diesem Dienst haengt, erfuhr es niemand. Drei Regeln fuer
  jeden Neustarter: (a) nach dem Start die WIRKUNG nachsehen (Prozess da? Zustandsdatei
  `running`? Port/Pipe antwortet?) und DAS ins Log schreiben, nicht den Aufruf;
  (b) melden ueber einen Weg, der vom ueberwachten Gegenstand unabhaengig ist (direkter
  Telegram-Versand wie bei einer Bus-Wache, Windows-Benachrichtigung) — nie ueber den
  Dienst, den man gerade vermisst; (c) nach N erfolglosen Versuchen in Folge
  (drei reichen) eskalieren statt weiter im Takt zu schweigen. Gegenprobe nach der
  Reparatur: die Wache einmal von Hand laufen lassen und pruefen, dass sie STILL bleibt
  (Exitcode 0, keine neue Logzeile) — eine Wache, die den gesunden Dienst nicht
  erkennt, startet ihn im Takt weiter neu.
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
- **Ein Automat, der sein Erzeugnis selbst baut, wird am SOLL-Bestand gemessen — nicht
  an seiner Meldung und nicht an seinem Alter.** „ok", Exitcode 0 und ein frischer
  Zeitstempel sagen nur, dass der Lauf stattfand; ob das Erzeugnis vollstaendig ist,
  sagt allein ein Vergleich gegen die Referenz. Zwei Formen derselben Wurzel, beide
  mit gruener Meldung: (a) eine SICHERUNG, die ihren Bestand aus einer falschen
  Quelle aufbaut — die gemeldete Zahl passt dann zur Meldung, nicht zum Soll, und
  still fehlt ein Teil (Umfang UND Loeschungen gegen die Quelle zaehlen, nicht nur
  einen der beiden Werte); (b) eine geplante Aufgabe, die es im PLANER gar nicht
  gibt — Registrierer-Skript, Commit-Text und eine abgehakte Aufgabe behaupten den
  festen Takt, waehrend die Aufgabe nie angelegt wurde oder nicht haelt (das
  Registrierer-Skript kann selbst dokumentieren, dass „Ready" samt naechstem Lauf
  gemeldet wurde, ohne dass die Aufgabe blieb); (c) eine REGENERATOR-Routine,
  die ihr eigenes Ziel taeglich neu anlegt und dabei taeglich DASSELBE meldet
  („war nicht vorhanden und ist angelegt"). Die wortgleiche Wiederholung ueber
  mehrere Tage IST der Befund — ein Selbstheiler, der nie aufhoert zu heilen,
  heilt nichts, und das Erzeugnis (hier die Ausser-Haus-Kopie) laeuft nur noch
  von Hand. Zeuge ist der Ausgabe-ARCHIV des Cron ueber mehrere Tage
  nebeneinander (`cron/output/<job-id>/*.md`), nicht der letzte Lauf: der sieht
  gruen aus und traegt die Wiederholung in sich. Beleg ist die Liste ALLER Aufgaben
  plus die Abfrage nach Namen (`schtasks /query /fo TABLE`, `schtasks /query /tn
  <name>`), nicht der Registrierer-Log — ein Log mit frischem Zeitstempel belegt
  nur einen HANDLAUF. Und `Get-ScheduledTask -TaskName <name>` findet auch
  VORHANDENE Aufgaben nicht: nur die Aufzaehlung oder `schtasks` zaehlen als
  Zeuge. Merksatz: **ein Erzeugnis ohne Vollstaendigkeitszahl ist keine
  Sicherung, und ein Auftrag ohne Eintrag im Planer laeuft nicht** — beide
  Gegenproben gehoeren in dieselbe Meldung wie das „ok".
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
- **Eine Lebendpruefung, die nur die PID nachschlaegt, ist kein Zeuge — Windows
  vergibt PIDs wieder.** Eine Statusdatei mit `state: running` und einer laengst
  beendeten PID zeigt dann auf ein voellig fremdes Programm: `tasklist /FI "PID
  eq <n>"` findet es, der Lauf gilt dauerhaft als "laeuft schon" (jeder Start
  gesperrt) und ein Waechter spiegelt eine Geisterposition. Die IDENTITAET
  mitpruefen, nicht die Existenz: Prozess-NAME **und** ein Merkmal aus der
  eigenen Kommandozeile (der Pfad der Statusdatei) — `Get-CimInstance
  Win32_Process -Filter 'ProcessId=<n>'` liefert Name und CommandLine in einem
  Aufruf. Die schaerfere Pruefung so einhaengen, dass sie nur auf dem ECHTEN
  Prozessweg greift: eingespeiste Testnaehte (`lebt=lambda pid: True`) bleiben
  unberuehrt, sonst schlaegt jede Suite fehl, die den Ablauf ohne echten Prozess
  prueft.
- **Ein Launcher, der einen Namen ueber eine gepflegte Liste aufloest, sperrt
  alles, was nicht in der Liste steht.** Loest er stattdessen ueber die DATEI auf
  der Platte auf (jede Datei in `strategien/`), ist jeder neue Gegenstand sofort
  startbar; die benannten Eintraege bleiben die Abkuerzung mit festem Symbol.
  Nach so einer Erweiterung mit `--trocken` belegen, dass ein benannter Eintrag
  DIESELBE Zieldatei nennt wie vorher (sonst entstehen zwei Staende fuer einen
  Lauf).
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

- **Der Statusbericht luegt in BEIDE Richtungen — auch ein gemeldeter FEHLSCHLAG
  ist zu pruefen.** Dieser Skill handelt vom gruenen Bericht ohne Wirkung; die
  Umkehrung kostet genauso viel. Gemessen: ein Aufruf gab einen Fehlercode zurueck
  (`wevtutil sl <Log> /e:true` -> Exit 5, "Zugriff verweigert"), und der Ziel-Abruf
  (`wevtutil gl <Log>`) zeigte danach `enabled: true` — die Aenderung war
  durchgelaufen. Wer den Code glaubt, meldet "braucht Admin" fuer etwas, das schon
  wirkt, und laesst die Wirkung unbemerkt. Regel: Aktion fahren, DANN den
  Ziel-Abruf lesen, und das Urteil aus DESSEN Ergebnis bilden; den Exitcode daneben
  nennen, nie als Beweis — in keiner der beiden Richtungen.
- **Ein Alarm, der aufhoert zu feuern, ist kein Beweis fuer den Fix — das
  ueberwachte Objekt kann verschwunden sein.** Eine Sicherheitsluecken-Meldung
  stoppte, nachdem der Fix gesetzt war; die Ursache war aber nicht, dass die
  Bedingung sich loeste, sondern dass die Position aus dem Buch verschwand (ohne
  Journal-Ausstieg) und an der Boerse nicht mehr offen war — ein SCHLIMMERER
  Zustand, den die Stille verbarg. Wenn ein Alarm nach einem Fix still wird,
  pruefen, ob die Bedingung wirklich aufgeloest ist ODER ob das ueberwachte Objekt
  weg ist (Position geschlossen/entfernt, Datei geloescht, Prozess beendet). Die
  Abwesenheit des Alarms ist keine Wirkung: den Gegenstand selbst befragen
  (Boerse/Journal/Datei), nicht die Meldung.
- **Ein Audit-Tor, das nur eine Richtung kennt, laesst die andere durch.** Wer eine
  Menge gegen eine Quelle prueft (Dateien, Aufgaben, Positionen), prueft in der
  Regel "ist alles da, was da sein soll". Der zweite Teil — "liegt dort etwas, das
  NICHT dorthin gehoert" — wird vergessen und ist der teurere: ein verwaister
  Eintrag faellt nie auf, weil jede Soll-Liste erfuellt ist. Beide Richtungen in
  dieselbe Meldung: fehlend UND ueberzaehlig, je mit Namen.
- **Ein Messwerkzeug, das am Betrieb vorbei misst, liefert ein praezise aussehendes
  falsches Urteil.** Gibt es fuer dieselbe Sache ZWEI Wege (zwei Schnittstellen,
  zwei Adapter, zwei Dateiformate), dann muss die Sonde den Weg ueber DIESELBE
  Auswahlfunktion nehmen, die der Betrieb benutzt; ein direkter Aufruf der
  Transportfunktion fixiert still den ersten Zweig. Belegt: eine Modellsonde rief
  den Transport direkt und meldete das zweite Modell als "(leer) 0/6, 0,0 s" —
  befragt hatte sie es nie; die Schuld lag am Werkzeug, nicht am Modell. Nach dem
  Umbau auf die Wegewahl des Betriebs hielt dasselbe Modell 6/6. **Vor dem Bau
  einer Sonde nachsehen, welchen Pfad der Betrieb nimmt, und die Sonde durch
  dieselbe Entscheidung schicken.** Dazu gehoert die Stueckzahl: ein Messwert
  ohne die Zahl der Wiederholungen ist eine Stichprobe (dieselbe Sonde: 3/3 bei
  2,9 s mit einer Wiederholung, 6/6 bei 1,3 s mit zweien) — die belastbare Zahl
  mit Wiederholungen nehmen und beide mit ihrer Stueckzahl nennen.

- **Ein Beleg, der den PROZESS festhaelt, ist kein Beleg — und ein Fehlschlag
  darin ist schlimmer als keiner.** Wird fuer einen Startvorgang eine Belegdatei
  angelegt (Startzeile, Endezeile), gehoert die WIRKUNG hinein: die Antwort des
  Ports oder die Bereitschaftszeile des Programms. Steht dort stattdessen
  "Prozess lief N Sekunden", sieht die Datei wie ein Nachweis aus und ist keiner
  — die naechste Sitzung liest sie als "laeuft" und sucht an der falschen Stelle.
  Am irrefuehrendsten, weil selbstverschuldet: ein zu frueh abgebrochener Probelauf
  schreibt sein eigenes Scheitern hinein (`HTTP 000`, "keine Verbindung"), und ab
  da traegt die Belegdatei die FALSCHFESTSTELLUNG. Drei Regeln:
  (a) auf die WIRKUNG warten, nicht auf eine Sekundenzahl — ein Programm, das nach
  8 s noch nicht bereit ist, ist nicht widerlegt (gemessen 57 s bis
  `Application startup complete`); (b) jede Antwort zaehlt, die KOMMT — ein `401`
  auf einem geschuetzten Endpunkt beweist den laufenden Server genau wie ein
  `200`, ein `000` beweist nichts; (c) erst nach dem Beweis beenden und den
  Ausgang mitschreiben. Fuer einen Dienst heisst das: den Port fragen, nicht die
  Prozessliste.
- **Zwischen Nachweis und Meldung darf nichts geschehen, was den Nachweis
  entwertet.** Ein Beleg gilt fuer den Zustand, in dem er erhoben wurde. Wird
  danach ein Befehl gefahren, der den Gegenstand veraendern kann, ist der Beleg
  weg, waehrend die Belegdatei weiter "ok" sagt. Der gefaehrlichste Fall ist ein
  BAU-Befehl: ein fehlgeschlagener Frontend-Build LEERT sein
  Ausgabeverzeichnis (`dist/`, `.next/`) VOR dem Schreiben — danach liefert der
  laufende Server eine leere Oberflaeche, und der Fehlversuch hat nicht nur
  nichts gebaut, sondern das Vorhandene zerstoert. Vor einem solchen Versuch eine
  Kopie des Ausgabeverzeichnisses anlegen, bei Fehlschlag zurueckholen, und danach
  den Beleg ERNEUERN statt den alten zu zitieren.
  **Und das Arbeitsverzeichnis vorher klaeren:** liegt der Gegenstand unter einer
  Junction (einer Windows-Pfad-Weiterleitung), entscheidet das
  ARBEITSVERZEICHNIS, ob ein relativer Pfad noch stimmt — derselbe Befehl laeuft
  aus dem echten Pfad durch und bricht aus dem weitergeleiteten ab, weil das
  Werkzeug die Junction aufloest und dem nachgelagerten Programm absolute Pfade
  vorlegt, die es ablehnt. Zu Beginn eines Beleglaufs deshalb ausgeben und
  ansehen, mit WELCHEM Verzeichnis gestartet wird, statt es anzunehmen.

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
Skill `handel-spuren`, `references/betriebsfehler-spuren.md` (dort im
Skill-Ordner, nicht in diesem).

Fuer eine ZAHL ist der Nachweis der Drei-Wege-Test aus Schritt 7 - alle drei
Wege im selben Lauf, mit ihren Zahlen:

```bash
cd Agenten/Handel && python kerzenschluss_bias.py --spur <spur> | tail -6
```

Erwartet: `netto` stimmt mit der Hausfunktion auf denselben Journalen ueberein
(auf die Nachkommastelle, wenn beide mit demselben Vorzeichen rechnen). Weicht
eine Zahl ab, gehoert die Abweichung in die Antwort - nicht die geglaettete
Fassung.
