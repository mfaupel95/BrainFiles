---
name: dauerprozess-bewachen
description: "Lang laufende Prozesse starten und per Cron bewachen."
version: 0.1.0
author: Hermes
platforms: [windows]
category: brainfiles
metadata:
  hermes:
    tags: [Windows, Dauerprozess, Waechter, Cron]
---

# Einen Dauerprozess starten und bewachen

Gilt fuer alles, was laufen soll und nicht endet: Bus, Handels-Dauerlauf,
Handelszentrale, Router, Atlas-Watcher. Der Ablauf ist immer derselbe: Start ueber
eine `.cmd`, Zustand ueber eine PID-Datei, Wache als Hermes-Cron `no_agent`.

## Wann

- „X soll laufen / dauerhaft laufen / starten / im Hintergrund“
- „starte Y neu, wenn es abstuerzt“, „warum ist X wieder aus“
- Eine Komponente soll nicht mehr an eine Agentensitzung gebunden sein

## Ablauf

1. **Starter als idempotentes Skript** (`<komponente>-start.ps1`) neben die
   Komponente legen: erst PID-Datei lesen und pruefen, ob der Prozess lebt ->
   „laeuft schon“ + Exit 0. Nur sonst starten.
2. **Start ueber eine `.cmd` je Ziel, nicht die EXE direkt.** In der `.cmd` macht
   die Shell die Umleitung, dann `start "" /b "<exe>" <argumente> >> "<log>" 2>&1`.
   Aufruf des Starters:
   `Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', "<pfad>.cmd") -WindowStyle Hidden`.
3. **PID nach dem Start ermitteln** (`Get-Process <name>` vorher/nachher vergleichen,
   den juengsten nehmen) und in `<komponente>.pid` schreiben — das ist der einzige
   Zustand, dem die Wache glaubt.
4. **Wache als Hermes-Cron**, nicht als Windows-Aufgabe:
   `cronjob_manage action=create name=<komponente>-waechter schedule='15m'
   script=<wache>.py no_agent=true deliver='telegram'`.
   Die Wache gibt **nichts** aus, wenn alles laeuft (leere Ausgabe sendet nichts),
   und beschreibt nur den Befund, wenn sie eingreift. Nicht-0-Exit oder Timeout
   loest die Fehlermeldung aus.
5. **Gegenproben in beide Richtungen, vor dem Bericht:**
   (a) Prozess laeuft -> Wache gibt 0 Zeichen aus, Exit 0;
   (b) `Stop-Process -Id <pid> -Force` -> Wache meldet „PID ... laeuft nicht“,
   startet neu, schreibt die neue PID, Exit 0;
   (c) **Alarmrichtung ohne Eingriff:** die Wache nimmt einen abweichenden Port
   bzw. ein `--nicht-starten` an, damit sich Meldung und Befund zeigen lassen,
   ohne den echten Dienst zu stoppen — sonst kostet jede Probe einen echten
   Ausfall, und die Probe wird deshalb nicht gemacht.
6. **Wirksamkeit der Komponente selbst belegen** (nicht nur den Prozess): eine
   Eingabe erzeugen und nachsehen, dass die Ausgabe nachzieht.

## Zweite Instanz derselben Komponente

Soll derselbe Code ein zweites Mal laufen (gleiche Spuren, anderer Parameter),
ist er ein EIGENER Dauerprozess - kein zweiter Aufruf derselben Datei:

1. **Eigene PID-Datei und eigenes Log** (`<komponente>.<variante>.pid`,
   `.<variante>.log`). Eine gemeinsame Sperre meldet der zweiten Instanz
   „laeuft schon“, ein geteiltes Log macht beide ununterscheidbar (wer ist
   abgestuerzt?).
2. **Starter parameterisieren, Basis-Namen unveraendert lassen.**
   `<start>.ps1 -Risiko mittel` bildet Sperre, Log und Melde-Namen aus der
   Variante; die Basis behaelt ihre alten Namen - sonst suchen alle vorhandenen
   Aufgaben, Auswertungen und Fenster ploetzlich woanders.
3. **Eigene Wache fuer die zweite Instanz.** Die bestehende Wache startet nur die
   Basis; ohne zweite Aufgabe ist die Variante nach jedem Neustart einfach weg.
   Gegenprobe: `Start-ScheduledTask` auf die neue Aufgabe muss die Logzeile
   „laeuft bereits (PID …, Variante …)“ erzeugen, Exit 0 - sie startet nicht doppelt.
4. **Der Eingabekanal gehoert GENAU EINER Instanz.** Telegram-`getUpdates`,
   gemeinsame Warteschlangen und Freigabedateien: die zweite laeuft stumm, liest
   keine Befehle, oeffnet/schliesst keine Fenster der ersten. Zwei Abrufer an
   einem Bot verschlucken sich gegenseitig (Telegram 409).
6. **Den Waechter-Task der zweiten Instanz aus dem der ersten KLONEN**, nicht von
   Hand bauen: `Export-ScheduledTask -TaskName '<geschwister>'` liefert das XML mit
   Trigger, `IgnoreNew`, Laufzeitgrenze und Principal; darin Name, das
   Varianten-Argument und die Beschreibung ersetzen und mit
   `Register-ScheduledTask -TaskName '<neu>' -Xml $x -Force` registrieren. Ein von
   Hand gebauter Trigger vergisst regelmaessig den Anmelde-Trigger oder die
   Wiederholung, und der Vergleich mit dem Geschwister faellt weg. Danach EINMAL
   feuern: die Logzeile „laeuft bereits (PID …, Variante …)“ plus
   `LastTaskResult 0` und eine unveraenderte Prozesszahl beweisen, dass der Klon
   greift und nicht ein zweites Mal startet.
   **Vor der DRITTEN Variante die Last messen** (freier Commit): jede Variante
   faehrt alle Objekte ein weiteres Mal, und ein erschoepftes Commit-Limit laesst
   danach fremde Dinge scheitern, die mit der Variante nichts zu tun haben
   (`references/massenprozesse-und-commit-limit.md`).

## Doppelbetrieb erkennen und beenden

- **Eine PID-Datei als Sperre hat ein Zeitfenster.** `Test-Path` → PID lesen →
  Prozess pruefen → starten ist Pruefen-dann-Handeln: feuern zwei Ausloeser
  gleichzeitig (Anmelde-Trigger und Zeit-Trigger derselben Komponente), sehen
  beide „frei" und starten doppelt. Auch eine neu vergebene PID laesst eine tote
  Sperre lebendig aussehen, und `IgnoreNew` in der Aufgabe hilft nicht,
  wenn der Starter den Prozess abgekoppelt startet und selbst schon fertig ist.
  Wer genau eine Instanz will, laesst den **Prozess selbst** eine exklusive
  OS-Dateisperre (`msvcrt.locking`/`fcntl.flock`) ueber seine Laufzeit halten und
  sich mit klarer Meldung beenden, wenn er sie nicht bekommt — eine stale PID
  ist keine Sperre.
- **Variante heisst nicht automatisch getrennte Zustandsdateien.** Der Starter
  kann die Sperre je Variante bilden („Basis und Stufenlauf duerfen gleichzeitig
  laufen"), waehrend beide Varianten in **dieselben** Zustands- und
  Journaldateien schreiben. Vor dem Einrichten einer zweiten Variante die
  Zustandspfade im Code lesen, nicht dem Kommentar im Starter glauben: ohne
  getrennte Pfade ist die zweite Variante kein eigener Dauerprozess, sondern
  Doppelbetrieb auf gemeinsamem Zustand (doppelte Ueberwachung, doppelte
  Einstiege, konkurrierende Schreibvorgaenge).
- **Ueberzaehlige Instanzen beenden: erst sichern, dann pruefen, dann PID-genau
  beenden.** Reihenfolge: (1) die Zustandsdateien in einen eigenen Ordner
  kopieren — ein Abbruch mitten im Schreiben hinterlaesst eine halb geschriebene
  JSON, die der Ueberlebende als „keine Positionen" liest und dann nicht mehr
  ueberwacht; (2) aus dem Journal den `modus` der letzten Zeilen lesen, um zu
  wissen, ob echte (Live-)Positionen offen sind und wer sie weiter ueberwachen
  muss; (3) beenden per PID fuer **Launcher UND Kind**, nie per Prozessname;
  (4) danach nachlesen, dass jede Zustandsdatei wieder parst und die
  Positionszahl unveraendert ist, und dass genau EIN Prozess der Komponente
  laeuft.
- **Ein langsamer Rechner ist ein Symptom, keine Ursache.** Vor jedem
  Neustart oder Update die Doppelbetriebe zaehlen: Python-Prozesse nach
  Kommandozeile gruppieren und je Gruppe die Eltern-Kind-Paare trennen. Vier
  Instanzen desselben Dauerlaufs heissen vierfache Scan-/Netzlast je Takt —
  und bei gemeinsamen Zustandsdateien zusaetzlich vierfache
  Positionsueberwachung.

## Wache auf eine DATEI statt auf einen Prozess

Manchmal ist nicht ein Prozess zu bewachen, sondern ein Ergebnis: „melde die
erste echte Order dieser Spur“, „melde, wenn das Buch sich aendert“. Der Aufbau
ist derselbe Cron `no_agent`, nur das Kriterium ist eine Datei.

1. **Ein Zustand in `cache/`, ein Befund je NEUEM Ereignis.** Die Wache merkt
   sich in einer eigenen JSON den letzten Stand (z. B. die Zahl der
   Ereigniszeilen) und meldet nur die Differenz. Ohne diesen Merker meldet sie
   entweder bei jedem Lauf dasselbe (Spam) oder nie (weil sie den alten Stand
   als neu liest).
2. **Erstlauf still stellen.** Beim ersten Lauf nur den Stand schreiben und
   nichts senden — sonst kommt beim Einrichten sofort eine Meldung ueber
   Ereignisse, die der Nutzer laengst kennt.
3. **Auch Zustandswechsel melden**, nicht nur neue Zeilen (z. B. „Fenster zu,
   laeuft wieder Papier“). Ein stiller Rueckfall sieht sonst aus wie „die Spur
   tut nichts“.
4. **Eine kritische Lage muss sich wiederholen, eine gute nie.** Ein Merker, der
   nur auf Aenderung meldet, laesst den Nutzer nach der ersten Warnung
   verstummen, obwohl die Lage unveraendert kritisch bleibt (eine Position, die
   seit Stunden 5 % vor der Liquidation steht, wird nicht besser, weil sich
   nichts geaendert hat). Denselben Zustand deshalb nach einer Frist erneut
   melden (z. B. 6 h), gute Lagen aber nur einmal beim Wechsel.

**Alle Melde-Bedingungen gehoeren in EINE Entscheidung — was hinter dem
Stille-Ausstieg steht, wird nie ausgewertet.** Baut die Wache ihren fruehen
Ausstieg („nichts geaendert") VOR die weiteren Kriterien, ist jede spaetere
Bedingung toter Code: gemessen war eine ausdrueckliche Meldeschwelle
wirkungslos, weil der Ausstieg vor ihr lag — ein dauerhaft zu niedriger Wert
waere nie gemeldet worden, und die Wache sah dabei gesund aus. Form:
`melden = stufenwechsel or neu_darunter or messfehler or schwelle_neu` als EINE
Zeile, und den Zustand einer Schwelle mitmerken (`schwelle_aktiv`), damit der
Uebergang einmal kommt und nicht taeglich.
**Und vergleiche gegen den zuletzt GEMELDETEN Wert, nicht gegen den letzten
Messwert.** Ein Rueckgang in Haeppchen von 2-3 Punkten am Tag ist sonst nie
sichtbar: jede einzelne Messung liegt knapp unter der Schwelle, die Stufe bleibt
dieselbe, und die Wache schweigt fuer immer — obwohl genau das die Lage ist, die
man wissen will. Den Bezugswert erst NACH einer Meldung nachziehen, damit ein
langsamer Rueckgang EINE Nachricht kostet statt einer je Tag (oder keiner).

**Die Tests einer Wache pruefen die REGELN, nicht den Tageswert.** Ein Test, der
die gemessene Zahl erwartet, ist jeden Tag anders rot oder gruen, ohne dass sich
etwas geaendert hat. Stattdessen erfundene Messungen in die Melde-Funktion geben
und die Faelle abdecken: erste Messung (wird gemeldet), keine Aenderung (still),
Stufe faellt, Stufe erholt sich, neues Element unter der Schwelle, dasselbe
Element bleibt darunter (still), unvollstaendige Messung (wird gemeldet).
**Die Attrappe muss die Vorbedingung der Wache erfuellen:** liefert der
Testdatensatz nur zwei Elemente, waehrend die Wache eine Mindestdeckung verlangt,
meldet sie „unvollstaendig" und JEDER Regeltest wird rot — das sieht wie ein
Fehler der Wache aus und ist einer der Testdaten. Die Vorbedingung im Helfer
standardmaessig erfuellen und den Verletzungsfall ausdruecklich bestellen.

**Ein Ergebnis, das nur bei angestecktem Ziel laeuft, altert still — und der
Befund ist sein ALTER, nicht ein Prozess.** Eine Kopie auf ein Wechselmedium kann
keinen Zeitplan haben (ohne das Medium findet sie nichts), also gibt es keinen
fehlgeschlagenen Lauf, der auffiele: die Kopie ist einfach alt, und das faellt
niemandem auf, bis jemand sie braucht. Eine Wache vergleicht deshalb das Alter des
Ziels (oder seinen letzten Zyklusvermerk) gegen eine Frist und meldet nur die
Ueberschreitung — nicht den Prozess.

Reihenfolge beim Nachholen: **erst Trockenlauf** (das Skript hat meist einen
`-NurPruefen`-Schalter bzw. robocopy `/L`), damit Umfang und Ziel vor dem Schreiben
feststehen — **dann abgekoppelt starten** (ein Massenlauf ueber sechsstellige
Dateizahlen sprengt jedes Anfrage-Zeitfenster) und den Fortschritt ueber die
Prozessliste lesen, nicht ueber die Rueckkehr des Aufrufs. **Das Ziel nie rekursiv
nachzaehlen, waehrend kopiert wird**: eine Verzeichnis-Rekursion ueber
hunderttausend Dateien auf einem Wechselmedium laeuft selbst in den Timeout — die
Zahlen des Kopierwerkzeugs (Fehler, verglichen, kopiert) sind der Beleg, und
`robocopy`-Codes 0-3 heissen Erfolg, erst ab 8 ist es ein Fehler.

**Der Herzschlag muss aus JEDEM Ausgang kommen, auch aus dem leeren.** Ist das
Kriterium der Wache `letzter_lauf` im Zustand des Objekts, dann darf kein Pfad
zurueckkehren, BEVOR der Zustand geschrieben (und gespiegelt) ist — auch der
Zweig „keine Daten / nichts zu tun“ nicht. Sonst friert der Zeitstempel ein,
waehrend das Objekt gesund weiterarbeitet: gemessen meldete eine Wache
„TOT — Zustand 6,8 h alt“ fuer eine Spur, die alle 15 Minuten `ok` ins
Betriebslog schrieb, weil ihr gemeinsamer Buchkern im Zweig „keine Daten“
ohne Zustandsschreiben ausstieg. Der Nur-Lese-Modus (`--vorschau`) schreibt
weiterhin nichts — der Unterschied liegt zwischen „nichts gebucht“ und
„nichts geschrieben“.

**Der Grund des Nichtstuns gehoert in den Zustand, nicht nur ins Log.** Wer nur
den Zeitstempel frisch haelt, hat Stille immer noch nicht gedeutet: das Objekt
rechnet fuer seine eigene Ablehnung oft schon Zaehler („zu wenige bewertete
Kaeufer“) und **niemand sieht sie**. Ein Feld im Zustand, das je Zyklus Grund
und Zahlen traegt (`{"keine_daten": true, "grund": …, "hinweis": {"<tor>": n}}`),
macht aus „Spur tut nichts“ ein „Spur wartet auf X“. Dafuer einen optionalen
Haken an der gemeinsamen Laufschnittstelle vorsehen (Rueckruf, der die Zaehler
liefert) statt den Vertrag aller Aufrufer zu erweitern; wer den Haken nicht
setzt, verliert nichts.

**Eine Wache muss den Stand lesen, den der LAUFENDE Zweig schreibt.** Laeuft ein
Objekt live, schreibt es seinen Papierzustand nicht mehr mit; eine Wache auf
einen fest verdrahteten Dateinamen meldet es dann faelschlich als tot (dieselbe
Falle wie beim Herzschlag eines Gates). Die vorhandenen Staende einlesen und den
mit dem juengsten `letzter_lauf` nehmen — Papier ODER Live, nicht eine feste
Datei. Eine unlesbare Nebendatei darf das Urteil nicht umwerfen, sondern wird
uebergangen.
4. **Die Wache sieht nur, was geschrieben wird.** Ein Fehlerpfad, der seine
   Meldung nach stderr schreibt und die Zeile im Datenfile auslaesst, ist fuer
   die Wache unsichtbar — und der Supervisor meldet die Spur trotzdem als „ok“,
   weil er stderr verwirft. Gehoert genau dieser Fehler ueberwacht (darf der
   Schluessel wirklich ordern?), muss der Fehler ZUERST eine Zeile im
   ueberwachten File bekommen — mit eigenem Kennzeichen, damit die Wache ihn
   anders formatiert als den Normalfall. Diese Zeile ist kein Buchungssatz:
   sie darf die Auswertung nicht verfaelschen (Kennzeichen ausserhalb der
   Buchungs-Menge waehlen und das in der Auswertung pruefen).
8. **Die Objektliste nicht im Wachenskript fuehren, sondern aus der EINEN Quelle
   lesen.** Eine eigene Liste ist eine zweite Wahrheit: ein neu angelegtes Objekt
   fehlt in der Wache, und niemand merkt es. Die Liste aus der zentralen
   Registrierung ziehen — und wenn das die Datei des FAHRERS ist (`SPUREN` im
   Treiber), per `ast.parse` statt `import`: ein Import startet dessen Prozesse.
   `ast.literal_eval` scheitert, sobald der Wert Aufrufe enthaelt
   (`os.path.join`) — deshalb den Baum abschreiten, die Dict-Schluessel und das
   Pfadfeld (`ordner`) einzeln herausziehen und zwei Spuren, die sich einen
   Ordner teilen, ueber den ORDNER zaehlen, nicht ueber den Namen. Ein Test
   nagelt die Kopplung fest (Mindestzahl plus ein bekannter Name), damit sie
   nicht still verloren geht. Belegt: eine Wache ueber "alle Spuren" fand beim
   ersten Lauf 30 statt der erwarteten 29 — die Liste war mitgewachsen, ohne
   dass die Wache angefasst wurde.
5. **Gegenprobe ohne echte Ereignisse:** die Wache in einem Einmal-Aufruf gegen
   ein Temp-File mit erfundener Zeile laufen lassen — sie muss genau einmal
   melden und beim zweiten Lauf schweigen. Danach `cronjob_manage action=run`
   fuer den echten Weg; ein Lauf mit leerer Ausgabe ist der Beweis, dass der
   still bleibende Fall still bleibt.
   **Die Alarmrichtung zusaetzlich an ECHTEN Daten zeigen — mit Rueckweg.** Die
   Zustandsdatei EINES Objekts kopieren (`.probe`), einen Zustand verfaelschen,
   der das Kriterium reisst (z. B. `letzter_lauf` weit in die Vergangenheit),
   die Wache laufen lassen (sie muss GENAU dieses Objekt melden), dann die Kopie
   zurueckschieben und erneut laufen lassen (wieder still). Das ist der staerkere
   Beleg als ein Temp-File: er zeigt, dass die Wache die echte Datei am echten
   Ort liest. Ohne das Zurueckschieben bleibt ein verfaelschter Betriebszustand
   stehen — und die naechste Sitzung sucht einen Fehler, den es nie gab.
   **Melde nur zwei Lagen: tot und ueberfaellig.** Stille ist der NORMALFALL,
   nicht ein Befund. Ein Objekt ohne Buch, dessen Zustand frisch ist, WARTET
   (gesund — jede neue Spur startet dort); ein Objekt mit offenen Posten
   innerhalb ihrer Frist HAELT (gesund, die Strategie tut nichts); die beiden
   meldenswerten Lagen sind TOT (Zustand aelter als die Schonfrist, oder Ordner
   weg) und UEBERFAELLIG (Frist abgelaufen, ohne dass der Ausstieg gebucht
   wurde). Wer "still" als Fehler meldet, baut einen Wecker, der beim
   Normalbetrieb klingelt — und wer die Altersgrenze nicht setzt, meldet eine
   abgeschaltete Spur nie.
6. **Mehrere Objekte derselben Art: EIN Modul, je Objekt ein duenner Wrapper.**
   Fuenf Buecher heissen nicht fuenf Wachenskripte: die Rechnung (letzter Stand,
   Differenz, Fensterwechsel) liegt EINMAL in `scripts/<familie>_wache.py` mit
   einer Tabelle `{objekt: {datei, schluessel, waehrung}}`, und je Cron-Job gibt
   es eine Wrapper-Datei, die `main("<objekt>")` aufruft. Sonst muss jede
   Verbesserung in N Kopien nachgezogen werden, und eine Kopie wird vergessen.
7. **Nur Handelszeilen melden, nicht jede Zeile mit dem Ziel-Modus.** Ein
   Journal schreibt im Live-Modus auch Verwaltungszeilen (Funding alle 8 h,
   Rollover, Zyklus, Quote) — eine Wache, die stumpf auf `modus == live`
   filtert, meldet alle 8 h ein „Ereignis“, das keine Order ist. Die
   Ausschlussliste aus der Fachlogik uebernehmen (hier: dieselben Wortlaute
   `funding/rollover/zyklus/quotes/info` wie in der Runden-Zaehlung), statt sie
   in der Wache neu zu erfinden.

## Wache auf einen BETRIEBSZUSTAND am Handelsplatz (Waisen, Stops, Salden)

Manche Wachen pruefen weder einen Prozess noch eine Datei, sondern den Zustand an
einem echten Konto (Schutz-Orders ohne Position, Guthaben, Sperren). Fuenf Regeln,
ohne die so eine Wache selbst zum Risiko wird:

1. **Eine Wache meldet, sie handelt nicht.** Ein Waechter mit Storno-/Loeschrecht an
einem echten Konto ist selbst das Risiko. Das Werkzeug daneben darf schreiben
(`<werkzeug> --stornieren`), die Wache ruft es nie mit Schreibrecht auf — und ein
**Quelltext-Test** haelt das fest (der Modultext der Wache darf den Storno-Aufruf
nicht enthalten). Ohne diesen Test haengt eine spaetere Erweiterung still eine
Loeschfunktion in den Automatikpfad.
2. **Ein Messfehler ist keine Entwarnung.** Kann die Wache nicht messen (Rechte,
Netz, Schluessel), meldet sie das AUSDRUECKLICH („das ist keine Entwarnung — es ist
unbekannt, ob ...") — aber hoechstens einmal je Frist (Merker `letzter_fehler`),
sonst kommt bei jedem Takt derselbe Fehler.
3. **Mehrere Quellen: je Quelle ein eigener `try`, und der Fehler nennt die
Quelle.** Sonst verdeckt die eine Boerse die andere: gemessen meldete eine Wache
fuer Kraken `EGeneral:Permission denied`, waehrend derselbe Aufruf aus der Shell
durchging — ohne Quellenname und zweiten `try` waere das als „Wache schweigt"
durchgegangen, obwohl die andere Boerse ungeprueft blieb. Ein Ausfall EINER Quelle
ist kein Grund, die andere nicht zu melden.
4. **`--selbsttest`: die fertige Meldung einmal zeigen, ohne Netz und ohne
Zustand.** Eine Wache, deren Meldung noch niemand gesehen hat, ist in ihrem
wichtigsten Teil ungeprueft. Der Selbsttest beweist die FORM, nicht die Lage — das
auch so sagen. Er darf die Merkdatei nicht schreiben (Test: nach dem Lauf
existiert sie nicht).
5. **An eine bestehende Testdatei anhaengen: erst die Namen der Datei lesen.**
Ersetzt deren `setUp` die Fachfunktion (`modul.messen = lambda: ...`), pruefen neue
Faelle ueber diese Instanz die Attrappe statt den Code — die eigenen Faelle brauchen
ein FRISCH geladenes Modul. Und die Namen sind nicht uebertragbar (Modulvariable,
Hilfsfunktion, Pfadkonstante): geraten (`W`, `HIER`, `JETZT`) reisst die ganze
Suite mit `NameError` um, obwohl der Testcode fachlich stimmt.

**Der Job-Status `ok` sagt nur, dass der Auftrag gelaufen ist.** Eine Wache, die
einen Messfehler oder eine echte Fundmenge meldet, ist genauso `ok` wie eine
lautlose. Wer `last_status` liest und daraus „nichts gefunden" schliesst, hat
nichts geprueft — die Aussage steht im Ausgabetext
(`cron/output/<job-id>/<zeitstempel>.md`) bzw. in der Telegram-Meldung. Erst den
Text lesen, dann urteilen.

**Einen Waise nicht als Position lesen.** Ein Stop-Loss bleibt am Handelsplatz
offen, wenn seine Position geschlossen wurde; er sieht in der Oberflaeche wie eine
offene Position aus, und ein Schliessversuch scheitert ohne Bestand. Vor jeder
Aussage „es steht noch eine Position" den Bestand/die offenen Positionen am
Handelsplatz lesen, nicht die Orderliste.

## Wache auf ein SELTENES SIGNAL (Ereignis kommt vielleicht tagelang nicht)

Fuer Spuren/Jobs, deren Tor selten aufgeht. Stille ist hier der NORMALFALL —
und damit ist "wartet korrekt" ohne Wache nicht von "kaputt" zu unterscheiden
(ein stiller ImportError liess eine Spur einmal tagelang signalfrei laufen).
Die Wache meldet deshalb nicht den Zustand, sondern das **zurueckgehaltene
Signal** — und nur das.

1. **ZURUECKGEHALTENES Signal melden, nicht Abwesenheit.** Der Befund ist: das
   Ereignis ist DA, aber ein Tor ist zu (Filter, Kapazitaet, Entfernung).
   Formulierung immer mit Grund und Zahlen ("Wende da, aber Schluss liegt
   darueber", "Wand handelbar bei X, Kurs noch Y % entfernt"). Wer nur
   "kein Signal" meldet, baut einen Wecker, der beim Normalzustand klingelt.
2. **Datenlage ist kein Befund.** Ein Datenfehler (Feed nicht erreichbar, zu
   wenige Kerzen) und eine strukturell unerreichbare Lage ("mehr als 3 Sigma
   entfernt") bleiben STILL — sie sind der Normalfall, nicht die Regel bei der
   Arbeit. Nur der Fall, in dem die Komponente bei vorhandenem Ereignis nicht
   handelt, ist meldenswert.
3. **Kennung = Identitaet des Ereignisses**, nicht der Zustandstext: Kerzenzeit
   oder `Tag|Instrument|Preis`. Der Merker in `cache/` haelt die Kennung, die
   Meldung kommt EINMAL je Kennung. Ein wechselnder Freitext als Kennung feuert
   sonst bei jedem Takt (dieselbe Feststellung, hundertmal).
4. **Mit den FUNKTIONEN der Komponente rechnen, nie mit einer Nachbildung.**
   Die Wache laedt das Modul der Spur und ruft deren `signal()`/`wand()`/
   `quelle()` — sonst prueft sie die Nachbildung, nicht die Spur. Auch die Daten
   ueber die Funktion der Spur holen, damit Wache und Zyklus auf DENSELBEN
   Eingaben rechnen.
5. **Fehler LAUT, Signal leise.** Rueckgabe `(None, text)` = echter Fehler (wird
   gemeldet), `(None, None)` = kein Befund (still). Ein Fehler darf nie als
   "kein Signal" durchgehen — genau so verschwindet eine kaputte Spur.
6. **Test ohne Netz und ohne echtes Buch:** das Laden der Spur ersetzen
   (`wache._spur_laden = lambda spur: SimpleNamespace(...)` mit nur den
   benoetigten Funktionen) und die Modulkonstante mit dem Wurzelpfad
   (`HANDEL`) auf ein Temp-Verzeichnis biegen, in dem `zustand.json` liegt.
   Vier Faelle je Spur: Ereignis+zurueckgehalten, kein Ereignis (still),
   Datenfehler (still), echter Fehler (laut).



## Wache auf PROZESSE (wenn ein Prozesskriterium geprueft wird)

Eine Wache, die Prozesse zaehlt, ist die fehleranfaelligste Bauform: sie schlaegt
Alarm, wenn ihre Zaehlregel falsch ist, nicht wenn etwas kaputt ist. Eine Wache,
die bei JEDEM Lauf dasselbe meldet, ist deshalb zuerst ein Fehler der Wache -
pruefe die Regel, nicht den Zustand. Drei Regeln, ohne die es nicht geht:

1. **Je Einheit zaehlen, nicht ueber alles.** Ein Dienst unter Windows ist ein
   PAAR (Startprogramm + Interpreter). Erwartet sind **genau zwei Prozesse je
   Kind** (4 Kinder = 8). Eine Gesamtzahl oder das ALTER als Kriterium ist
   falsch: ein Agent laeuft legitim stundenlang, sein Paar altert mit (gemessen:
   eine Wache meldete „8 Prozesse aelter als 1 h = Leak" alle 15 Minuten, obwohl
   genau der Normalzustand vorlag).
2. **Erst ab der Aufraeum-Schonfrist zaehlen.** Raeumt der Treiber selbst auf
   (jeder Zyklus, Schonfrist z. B. 300 s), stehen nach jedem Neustart junge
   Waisen im Zaehlfenster, die in Minuten von allein verschwinden. Wer sie
   mitzaehlt, alarmiert bei jedem Neustart. Also nur Prozesse aelter als die
   Schonfrist als Befund werten — und die Gesamtzahl ebenfalls so filtern.
3. **Zwei Bedingungen fuer einen Treffer: Kennung UND Prozessname.** Eine
   `CommandLine`-Suche nach dem Modulnamen trifft auch die eigene Abfrage und
   jede Huelle, die den Text enthaelt — in beide Richtungen schaedlich: die
   Wache zaehlt Phantome (kraken=5 statt 2), und ein Aufraeumer, der das fuer ein
   Kind haelt, BEENDET seine eigene Suche per `taskkill /T`. Immer zusaetzlich auf
   `python.exe`/`pythonw.exe` (bzw. den echten Programmnamen) filtern.

**`powershell` immer mit absolutem Pfad aufrufen**
(`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`): unter der
Aufgabenplanung ist der PATH ein anderer als in einer Sitzung. Symptom einer
leeren Prozessliste ist NICHT ein Fehler, sondern **stilles Nichtstun** — der
Treiber raeumt dann nichts auf und meldet trotzdem „ok". Wo „leer = nicht raten"
gilt, muss die leere Liste LAUT protokolliert werden, und die Abfrage je Zyklus
EINMAL laufen (Ergebnis an die Aufraeumfunktion durchreichen, nicht zweimal fragen).

Gegenprobe in beide Richtungen: auf gesundem System gibt die Wache **nichts** aus,
und im Treiber-Log steht die Aufraeumzeile mit der Zahl der beendeten Waisen.

## Wache auf die DAUER eines Ausfalls (Neustart-Schleifen sichtbar machen)

Ein Zustands-Waechter („laeuft / laeuft nicht“) sieht eine Neustart-Schleife
nicht: er startet brav neu, jeder Lauf meldet Erfolg, und dass der Dienst den
halben Tag weg war, faellt nur als Nebenwirkung auf (gescheiterte Auftraege,
unklare Meldungen an den Nutzer). Dafuer eine ZWEITE, unabhaengige Wache - nicht
in den Neustart-Waechter hineinbauen: stirbt der Neustart-Waechter, muss die
Messung weiterlaufen.

1. **Zustand = Ausfallbeginn, nicht „aus“.** Eigene JSON in `cache/`:
   `{"seit": <ISO>, "gemeldet": <bool>}`. Erster Lauf mit zu Port: nur den
   Beginn schreiben, lautlos.
2. **Meldeschwelle in Sekunden** (Startwert 300): ein Neustart von zwei Minuten
   ist Betrieb, kein Befund. Darunter nichts ausgeben.
3. **Zweiter Lauf im selben Ausfall schweigt** (`gemeldet` setzen) - sonst feuert
   die Wache bei jedem Takt denselben Alarm.
4. **Die Erholung melden, sobald die Schwelle ueberschritten war**, mit der
   gemessenen Dauer, und den Zustand danach loeschen. Ein Ausfall ohne
   Erholungsmeldung laesst offen, ob es weitergeht.
5. **Den Zustand des Neustart-Waechters in den Befund schreiben** (Windows:
   `Get-ScheduledTask`/`Get-ScheduledTaskInfo`). Sonst ist „Dienst weg“ nicht von
   „Waechter tot“ zu unterscheiden - und genau dafuer ist die zweite Wache da.
6. **Fuenf Richtungen belegen, bevor „fertig“ gemeldet wird:** gesund = lautlos;
   Ausfall ueber der Schwelle = Alarm mit Dauer; zweiter Lauf = lautlos; Ausfall
   unter der Schwelle = lautlos; wieder offen = Erholungsmeldung plus geloeschter
   Zustand. Dafuer nimmt das Skript Pruefhaken (`--port`, `--stand`,
   `--schwelle`) und laeuft gegen einen geschlossenen Port / eine
   Temp-Zustandsdatei - nie gegen den echten Dienst.
- **Ein Pruefhaken ist ein eigener Code-Pfad und gehoert in die Probe.** Liegt der
  Zustandspfad als `Path` im Modul und kommt ueber den Haken als `str`, bricht
  `pfad.parent` NUR im Pruefweg ab, waehrend der Produktivpfad gesund aussieht.
  Im Schreib-/Lesepfad zuerst `pfad = Path(pfad)` normalisieren, und die Probe
  ueber genau diesen Weg fahren.

## Pitfalls

- **`Start-Process -RedirectStandardOutput` blockiert bei einem Dauerprozess** —
  der Aufrufer wartet auf das Ende des Kindes, also nie. Symptom: der Startbefehl
  laeuft in den Timeout, obwohl der Prozess danach laeuft. Die Umleitung gehoert in
  die `.cmd`, der Starter kehrt sofort zurueck.
- **Den Dauerprozess nie ueber eine Pipe des Aufrufers starten**
  (`& powershell -File <starter> *>&1 | Add-Content $protokoll`). Das Kind haelt die
  Pipe offen, der Starter kehrt also nie zurueck — mit drei Folgen, die zusammen wie
  ein Fehler der Komponente aussehen: (1) die geplante Aufgabe bleibt auf „Running“,
  (2) das eigene Protokoll ist von aussen gesperrt (`Get-Content` meldet „Device or
  resource busy“, die `ENDE`-Zeile als Beleg fehlt), und (3) wer die Aufgabe beendet
  (`^C` im Protokoll des Kindes, Aufgabencode 267014 = „von aussen beendet“), reisst
  den laufenden Dienst mit — der Ausfall beginnt Minuten nach dem Start, und der
  Aufgabencode liest sich dabei harmlos. Richtig: das Startskript losgeloest in
  eigener Konsole starten
  (`Start-Process -FilePath 'powershell.exe' -ArgumentList @('-ExecutionPolicy','Bypass','-NoProfile','-File', ('"' + $starter + '"')) -WindowStyle Hidden`)
  — eigener Prozessbaum, ueberlebt die Sitzung — und danach **selbst** auf den Port
  warten (`while (-not (Test-PortOffen $port)) { … Start-Sleep -Seconds 3 }`, Frist
  grosszuegig, der erste Lauf baut notfalls erst). Die Rueckkehr des Starters ist der
  Befund, nicht die Ausgabe des Kindes.
- **Vor jedem Ausfallurteil fragen, ob die Komponente ueberhaupt eine Wache hat.**
  Eine fehlende Wache ist der eigentliche Befund — ohne sie ist die Ausfallzeit die
  Zeit bis zum Zufall (gefunden wird der Ausfall dann von einer Sitzung, die den Port
  zufaellig antippt). Deshalb zuerst die Wachenliste ansehen (Hermes-Cron-Liste und
  `Get-ScheduledTask -TaskName 'MaxHirn-*'`, Zustand `Ready` heisst nur „registriert“),
  dann nach dem Muster aus Schritt 4 nachruesten.
- **Ein Objekt, das live geht, braucht seine Wache im SELBEN Schritt.** Die
  Vollstaendigkeitspruefung laeuft ueber die Liste der Objekte, die wirklich handeln
  koennen (Erlaubnis-Haken UND Freigabe-Haken UND ein echter Orderweg im Code) — nicht
  ueber die, an die man sich erinnert. Gemessen lief ein Objekt tagelang live, ohne
  dass irgendeine Wache seinen Ausfall gemeldet haette; nur der Tagesbericht haette ihn
  gezeigt. Nachruesten ist billig und braucht KEIN zweites Wachenskript: eine Zeile in
  der Tabelle der gemeinsamen Wache (Datei, Schluessel, Waehrung) + eine duenne
  Wrapper-Datei, die `main("<objekt>")` aufruft + ein Cron `no_agent`. Gegenprobe: der
  erste Lauf meldet den Ist-Stand EINMAL ("N Zeilen im Journal - Beobachtung laeuft ab
  jetzt") und schweigt danach.
- **Ein Watchdog mit hoher `RestartCount` kann einen Crash-Loop stundenlang
  verstecken.** `RestartCount 99 / RestartInterval 1 min` startet einen sofort
  wieder abstuerzenden Prozess brav neu — der Scheduler zeigt `Running`/`Ready`
  ohne Fehlermeldung, waehrend in Wahrheit seit Stunden kein einziger Zyklus
  durchlief. Prozess-**Uptime** (`Get-Process <name> | Select StartTime`) gegen
  den Zeitpunkt des letzten VOLLSTAENDIGEN Zyklus im eigenen Log halten — klafft
  das auseinander (Prozess wenige Minuten alt, letzter echter Erfolg Stunden
  zurueck), ist es ein Crash-Loop und kein gesunder Dauerbetrieb, auch wenn
  gerade ein Prozess laeuft.
- **Ein aus der Agentensitzung gestarteter Hintergrundprozess stirbt mit ihr.**
  Symptom: Stunden spaeter endet er mit Exit 127, waehrend der per `.cmd`
  gestartete weiterlaeuft — das ist kein Fehler der Komponente und kein Grund zur
  Annahme, der Dauerbetrieb sei weg. Deshalb fuehrt der Weg ueber die `.cmd`
  (Schritt 2), und Testprozesse werden danach beendet, damit kein Doppelbetrieb
  bleibt.
- **Einen langen Start nie in derselben Anfrage abwarten.** Ein Kommando ueber eine
  Werkzeugbruecke hat ein Zeitfenster (hier rund 300 s); ein Lauf, der laenger
  braucht, wird als Timeout gemeldet, obwohl er weiterarbeitet - und wer ihn
  danach noch einmal startet, hat zwei Instanzen. Lange Laeufe deshalb ABGEKOPPELT
  starten (`Start-Process` ohne `-Wait`, Ausgabe UND Fehler in eine Datei) und
  spaeter die Datei lesen; ob der Lauf noch lebt, entscheidet die Prozessliste,
  nicht die Rueckkehr des Aufrufs. Eine Ausgabedatei mit 0 Byte bei winzigem
  Speicherverbrauch heisst „haengt beim Laden“, nicht „arbeitet noch“ - dann
  nachsehen, was er importiert, und den Versuch beenden statt weiter zu warten.
- **Ein Massenlauf, der im Sandbox-Terminal abbricht, gehoert auf den Host.**
  Bei knappem Commit scheitert das Terminal der Werkzeug-Sandbox mit
  `WinError 1455` („Auslagerungsdatei zu klein“), waehrend dieselbe Schleife ueber
  die Host-PowerShell durchlaeuft. Symptom ist ein Abbruch MITTEN im Lauf, ohne
  Fehler der Komponente.
- **Die Uhr messen, bevor ein Ausbleiben gemeldet wird** (`date`): aus den letzten
  Zeitstempeln im Kopf eine Uhrzeit weiterzaehlen erzeugt Fehlalarme („Zyklus seit
  2 h ausgeblieben"). Gegenprobe in derselben Reihenfolge: PID lebt -> Log-Zeile des
  Starters -> `Get-ScheduledTaskInfo` (`last_run`/`next_run`) -> erst dann urteilen.
- **Ein Statuskommando der Komponente beschreibt nicht immer den Prozess.**
  Beispiel `projectatlas watch-status`: meldet `active: false` auch bei laufendem
  Watcher, weil es einen Durchgang meint. Wer damit prueft, startet einen zweiten
  Prozess. Maßgeblich ist die PID-Datei plus `Get-Process`.
- **Unter Windows ist ein venv-Prozess ein PAAR** (Launcher-Shim + Kind). Ein
  `Stop-Process` auf die verfolgte PID laesst das Kind weiterlaufen - und das
  schreibt unsichtbar in dieselben Dateien. Vor „beendet“ per
  Kommandozeilen-Abfrage pruefen, dass KEIN Glied der Kette mehr laeuft, und
  beide PIDs beenden. Umgekehrt gilt: das Paar ist kein Doppellauf (nicht Alarm
  schlagen, bevor ParentProcessId/ExecutablePath geprueft sind).
- **Eine Messreihe mit zwei Schreibern ist unbrauchbar.** Hat ein versehentlich
  parallel laufender Test- oder Zweitprozess in dieselben Zustands- und
  Journaldateien geschrieben, sind die Zahlen dieser Minuten Mischwerte:
  Dateien loeschen und die Reihe sauber neu starten, statt die Vermischung
  spaeter herausrechnen zu wollen.
- **`Get-CimInstance Win32_Process` mit `CommandLine`-Filter ist teuer** in einem
  gewachsenen Prozessbaum. Zuerst PID-Datei und `Get-Process` nutzen; NUR wenn
  zwei gleichnamige Prozesse unterschieden werden muessen (Basis vs. Variante -
  `Get-Process` zeigt keine Argumente), ist die WMI-Abfrage das Mittel - dann
  einmal gezielt, nicht in einer Schleife.
- **Eine NEUE Aufgabe fuer den eigenen Benutzer braucht keinen Administrator -
  eine BESTEHENDE aus erhoehtem Kontext zu aendern schon.** Gemessen: einen Klon
  mit demselben interaktiven Benutzer und `RunLevel Limited` registrieren lief
  ohne Erhoehung durch, waehrend `Set-ScheduledTask` auf einer erhoeht
  registrierten Aufgabe mit `0x80070005` abgewiesen wird. Also nicht pauschal
  „braucht Admin“ annehmen und die Aufgabe deshalb gar nicht anlegen, sondern
  erst registrieren und den Fehler auswerten. Fuer alles andere gilt weiter: der
  Hermes-Cron laeuft ohne Erhoehung und heilt zusaetzlich einen toten Prozess, was
  ein Autostart-Eintrag nicht kann - nur wenn Max eine sichtbare Aufgabe will,
  braucht es einen erhoehten Aufruf von ihm.
- **Geplante Routine-Aufgaben versteckt registrieren** (`-WindowStyle Hidden` in
  der Task-Action): eine sichtbare Aufgabe zeigt bei JEDEM Lauf ein
  PowerShell-Fenster. Drei Dauerlauf-Aufgaben feuern je 30 Minuten (Dauerlauf
  selbst + Waechter + Mittel-Waechter) — das ist das „andauernd flackernde
  Fenster". Beim Anlegen Hidden von Anfang an mit aufnehmen; Bestandsaufgaben per
  `Set-ScheduledTask -Action` nachziehen (interaktive Aufgaben ohne Erhoehung,
  `LogonType=ServiceAccount`-Aufgaben erhoeht). Wrapper-Kinder muessen auch
  versteckt starten (`Start-Process -WindowStyle Hidden` oder pythonw), sonst
  bleibt deren Konsole sichtbar, wenn nur der Wrapper versteckt ist.
- **Ein Dienst-Task mit `python.exe` bei Interactive-Logon zeigt ein DAUER-
  Konsolenfenster** — auch wenn der Wrapper versteckt ist: `-WindowStyle Hidden`
  versteckt die PowerShell, nicht das Konsolen-Subsystem eines python.exe.
  Diagnose bei „aufploppender Konsole“: alle Task-Aktionen listen
  (`Get-ScheduledTask … | % Actions[0]`) und nach `python.exe` (sichtbar) vs.
  `pythonw.exe` (versteckt) filtern — Dienste, die ihr Journal auf die Platte
  schreiben (Prints nur Status), auf pythonw umstellen. Das gilt fuer den
  Wrapper **und** fuer die vom Treiber gespawnten Kinder: ein Supervisor, der
  seine Agenten mit `python.exe` (Repo-venv) startet, poppt bei jedem
  Kindprozess ein Fenster auf; `pythonw.exe` im Startbefehl des Supervisors
  (nicht nur im Task) schaltet ALLE Kindfenster ab, die Ausgabe laeuft weiter
  in die ag_log-Dateien.
- **Einen Konsolen-Rundgang fahren: alle Task-Aktionen nach Sichtbarkeit
  klassifizieren, nicht raten.** Der schnelle Diagnose-Scan fuer
  "aufploppende Fenster" listet die Top-Aufgaben (`MaxHirn-*`, `BrainFiles-*`,
  `Hermes-*`) und stuft jede Action in drei Klassen ein: `-WindowStyle Hidden`
  im Arguments => versteckt; `pythonw.exe` / `wscript //B` => fensterlos (ok);
  alles andere => `CHECK` (potenziell sichtbar). `CHECK` heisst noch nicht
  Fenster: `pythonw` ist immer fensterlos, aber jedes `python.exe` und ein
  `powershell.exe` OHNE `-WindowStyle Hidden` zeigt eine Konsole. Echte
  Verursacher sind oefters die leisen Nebenlaeufer (ein Waechter, der alle
  2 Minuten feuert, ohne Hidden ist das staendige Flackern) als die grossen
  Dauerlauefe. Fuer den Endcheck die laufenden Prozesse nach
  `ExecutablePath`/Kommandzeile ansehen — nicht nur die Action lesen.
- **Den Fix in BEIDE Schichten schreiben: die Live-Task-Action UND das
  Registrierungs-Wrapper-Skript.** `Set-ScheduledTask` aendert die laufende
  Aufgabe, aber der Anleger (`*-aufgabe.ps1` im Routinen-Ordner) traegt die
  ALTE Executable/Argumente weiter (`python.exe`, ohne Hidden). Wer nur den
  Task fixen, gibt den Fix beim naechsten Re-Registrieren zurueck. Beides
  patchen (pythonw + Hidden), versionskontrolliert committen.
- **Eine Aktion zu aendern verweigert die normale Sitzung, sobald die Aufgabe
  aus erhoehtem Kontext registriert wurde — unabhaengig vom `-RunLevel` des
  Prinzipals** (0x80070005, `Set-ScheduledTask` wie `Register-ScheduledTask`).
  Auch eine `Limited`-Principal-Aufgabe weist einen nicht erhoehten
  Action-Umbau ab; `Principal.RunLevel` vorhersagen zu wollen in die Irre.
  Solche Fixes als weiteren Schritt in das vorhandene Admin-Skript legen
  (`vorsorge-*-admin.ps1`), damit EINE Admin-Sitzung alles erledigt. Das
  Admin-Skript schreibt sein Ergebnis in eine Log-Datei (das Fenster ist
  versteckt); der Aufrufer liest die Datei statt der stdout der erhoehten
  Sitzung.
- **Ein laufender Treiber, der je Zyklus eine neue Kindgeneration spawnt und die
alte nicht beendet, ist ein Speicherleck — und die Symptome tauchen ANDERSWO auf.**
Der Treiber gilt als gesund (Prozess lebt, Log frisch), waehrend sich die Kinder
stapeln: gemessen 84 gleichartige Agentenprozesse, 80 davon aelter als eine Stunde,
aus einem einzigen Tag. Sichtbar wird das nicht am RAM, sondern am **Commit-Limit**:
bei 28 GB freiem RAM war das Commit zu 99 % reserviert (`Win32_OperatingSystem`:
`FreeVirtualMemory` gegen `TotalVirtualMemorySize`), und danach scheiterten fremde
Dinge — jede Puffer-Anforderung eines Modellladers, `git commit`, ganze Werkzeugaufrufe
(`WinError 1455`). Diagnose: Prozesse nach Kommandozeilen-MUSTER des Kindes gruppieren
(nicht nach Name), `CreationDate` ansehen und die Generationen zaehlen; erwartet ist
EINE je laufendem Zyklus. Aufraeumen durch Beenden der alten Generationen per PID,
dann Commit frei nachmessen — und den Fix im Treiber nachziehen (Kinder vor dem
naechsten Spawn beenden), sonst ist der Speicher in Stunden wieder weg.
  Der Gegenentwurf, der sich bewaehrt hat (moondev_dauerlauf, 21.09.2026):
  (a) Stoppen beendet den ganzen BAUM (`taskkill /T /F /PID`) — das Kind ist
  unter Windows ein PAAR, das Startprogramm allein zu beenden laesst den
  Interpreter als Waise stehen; (b) jeder Zyklus raeumt VOR dem Spawn auf:
  Prozesse mit der Kennung des Kindes, die zu keinem lebenden Kind gehoeren
  und aelter als eine Schonfrist sind (300 s), werden beendet — die Schonfrist
  schuetzt einen gerade startenden Enkel; (c) stirbt die verfolgte Wurzel,
  wird ihr Baum VOR dem Neustart beendet, sonst laufen mit jedem Zyklus zwei
  Kinder desselben Namens. Erwarteter Ruhezustand: GENAU zwei Prozesse je Kind
  (Startprogramm + Interpreter) — 4 Kinder = 8 Prozesse, gemessen nach dem
  Fix; vorher 84. Prozessliste ueber `Get-CimInstance Win32_Process` (wmic ist
  auf Windows 11 abgekuendigt), und bei fehlgeschlagener Abfrage NICHT
  aufraeumen statt zu raten. Wer die Aufraeumfunktion aus einer frischen
  Instanz ruft, erschlaegt die legitimen Kinder des laufenden Treibers — der
  Aufruf gehoert in den Zyklus des laufenden Treibers.
  Symptomkatalog (was bei erschoepftem Commit alles scheitert), die Messbefehle und
  die Route fuer einen Massenlauf, der im Sandbox-Terminal abbricht:
  `references/massenprozesse-und-commit-limit.md`.
- **Eine Testsuite, die den Treiber baut und `zyklus()` ruft, greift in den
  LAUFENDEN Betrieb.** Gemessen: ein Testlauf hat die lebenden Agenten als Waisen
  beendet (8 PIDs — der Treiber startete sie 60 s spaeter neu, der Eingriff fiel
  nur daran auf), die Logdatei des laufenden Betriebs gedreht, seine Startzeilen
  ins ECHTE Treiberlog geschrieben und vier eigene Agenten als Waisen stehen
  gelassen. Kein Modulwaechter faengt das ab: der Eingriff ist ein Prozesskill,
  keine Dateiaenderung. Gegenmittel ist ein **Trockenmodus im Konstruktor**
  (`trocken=True`, Standard `False`), der drei Dinge abschaltet: Aufraeumen
  fremder Prozesse, Schreiben ins echte Log, Agentenlogs in einen
  `tempfile.mkdtemp()`-Ordner — dazu ein Test, der den Vertrag selbst prueft
  (Treiberlog unveraendert, Logbasis im Temp, `aufraeumen()` nicht gerufen).
  Ein Umbiegen einzelner Logkonstanten in `setUp`
  (`m.LOG = Path(tmp)/"log.txt"`) genuegt nur fuer Tests, die keine Prozesse
  starten — sonst landet „PIDs 600" als Zeile im Betriebsprotokoll.
  **Zweite Falle: die Wurzel ist frueher tot als der Nachfahre.** `_stoppe()`
  endet bei `poll() is not None`, und ein Baumkill ueber eine tote Wurzel
  erreicht nichts mehr — der Test muss die Nachfahren VOR dem Beenden aus der
  Prozessliste sammeln (Parentkette, transitive Huelle) und einzeln beenden.
  Nachweis: die Prozesszahl danach ist die erwartete (zwei je Kind), gefiltert
  auf den echten Programmnamen — sonst zaehlt die eigene Abfrage mit.
- **Das Log eines langlebigen Kindes waechst unbegrenzt und faellt nur am
  Plattenplatz auf.** Ein Anzeige-Agent schrieb ~50 MB je Tag in die
  stdout-Datei, die der Treiber beim Spawn oeffnet (nach vier Tagen 160 MB) —
  RAM, Prozesszahl und Zykluszeiten sahen gesund aus, der Schwund fiel erst bei
  der Platznachmessung auf; eine Wache ueber Prozesse oder RAM erkennt das nie.
  Deshalb gehoert in den Spawn-Pfad eine **Drehung**: vor dem Oeffnen bei
  Ueberschreiten einer Schwelle (50 MB) nach `<name>.log.1` umbenennen, die alte
  `.1` dabei ersetzen, und die Drehung als Zeile ins Treiberlog schreiben.
  **Gedreht wird BEIM START, nie im Betrieb** — das laufende Kind haelt die
  Datei offen, Windows verweigert dann jedes Umbenennen (`mv` schlaegt fehl,
  solange der Prozess lebt). Eine Aenderung am Treiber wirkt erst in der neuen
  Instanz: solange der alte Treiberprozess laeuft, dreht niemand.
- **Ein toter Supervisor laesst seine Kinder als Waisen weiterlaufen.**
  Endet der Treiber von aussen (`Get-ScheduledTaskInfo`-Result 267014), bleiben
die von ihm gespawnten Agentenprozesse am Leben — sichtbare Konsolenfenster,
die "laufende Aufgaben" vortaeuschen, obwohl der Supervising-Prozess weg ist.
  Vor dem Bericht pruefen, ob der Treiber ueberhaupt noch laeuft
  (`State=Ready` statt `Running`, Result=267014): wenn nicht, die Kinder per
  PID beenden (`Get-CimInstance` nach dem Agenten-Modulnamen filtern, nie per
  Prozessname), Treiber per `Start-ScheduledTask` neu starten und das
  Prozesspaar samt Kindern nachverifizieren. Das Speichern der Orphans ist
  Aufraeumen, kein Bestandsfehler.
- **Ein Prozess je Ziel.** `watch` und Verwandte nehmen EIN Ziel; „alle 33 Repos“
  sind 33 Prozesse. Bewusst nur das Standardziel anbinden und das im Bericht sagen.
- **Ein Waechter darf nicht ueber den Weg melden, den er ueberwacht.** Eine Wache,
  die ihren Befund in den Bus oder in die ueberwachte Warteschlange schreibt,
  schweigt genau beim Ausfall. Deshalb Cron/Scheduler direkt nach Telegram.
- **Das Wachenskript liegt unter `Agenten/Hermes/scripts/` — ein Skript neben der
  Komponente wird nicht angenommen.** `cronjob_manage` erwartet einen Pfad RELATIV
  zu diesem Ordner; ein absoluter Pfad auf einen anderen Ort (z. B.
  `Agenten/Handel/…`) wird abgewiesen. Gehoert die Logik fachlich zur Komponente,
  also einen duennen Wrapper in `scripts/` legen, der die eigentliche Datei ueber
  `importlib.util.spec_from_file_location` laedt (NICHT ueber `sys.path` — ein
  Eintrag kann gleichnamige Module verdecken) und deren `main()` aufruft; beide
  Dateien versionieren. Der Wrapper haelt dieselbe Melde-Regel ein: leere Ausgabe,
  wenn es nichts zu melden gibt.
- **Eine Wache laeuft unter dem Interpreter von Hermes, nicht in der venv der
  Komponente.** Ein Skript, das `requests`, `pandas` oder ein Spur-venv braucht,
  stirbt im Cron — und zwar lautlos, weil niemand die Ausgabe liest, wenn der
  Auftrag nur „ok“ meldet. Deshalb nur Standardbibliothek importieren und die
  Fachmodule ueber `importlib.util.spec_from_file_location` per PFAD laden (deren
  eigene Stdlib-Abhaengigkeit vorher pruefen: `grep '^import\|^from' <modul>`),
  und den Beweis mit einem FREMDEN Interpreter fahren, nicht mit der venv, in der
  man entwickelt hat — die Wache muss auch mit dem nackten python.org-Interpreter
  laufen.
- **Aus `Agenten/Hermes/scripts/` sind es DREI `dirname()`-Stufen bis zur
  Repo-Wurzel** (`scripts` -> `Hermes` -> `Agenten` -> Wurzel). Mit zwei landet man
  auf `Agenten/` und der Modulpfad wird zu `Agenten/Agenten/Handel/...` — Symptom
  ist ein `FileNotFoundError` beim Laden des Fachmoduls, obwohl die Datei
  existiert. Nach jeder Pfadherleitung einmal ausgeben und gegen die echte Datei
  pruefen statt zu zaehlen.
- **`subprocess` mit `text=True`** stirbt an Umlauten aus `tasklist`/`powershell`:
  die Konsole schreibt cp1252, nicht UTF-8. `encoding="cp1252", errors="replace"`
  setzen, sonst reisst ein `UnicodeDecodeError` im Lesethread den Aufruf ab.
- **Ein neuer Prozess gleich nach dem Neustart ist kein Befund.** Wer seinen
  eigenen Treiber neu startet, erzeugt regelmaessig Waisen der VORIGEN Instanz:
  `Stop-Process` auf die Treiber-PID beendet den Baum nicht, und die Kinder des
  alten Laufs leben weiter, bis der neue sie beim Aufraeumen erwischt. Vor jeder
  Aussage „zu viele Prozesse" die Startzeit der Treiberinstanz gegen die
  `CreationDate` der Prozesse halten — was vor dem Neustart entstand, ist
  Altlast, kein Doppellauf.
- **Ein Dienstprozess ist keine Sitzung am Bildschirm - und die Zeitgrenze des
  Treibers toetet mitten in der Buchfuehrung.** Zwei zusammenhaengende Fallen im
  Zyklusbetrieb: (a) eine Spur, die per `isatty()` auf stdin prueft, ob jemand am
  Bildschirm sitzt, haelt einen Dienstprozess fuer eine Sitzung (er erbt ein
  Terminal) und wartet auf eine Freigabe, die niemand geben kann - Symptom ist
  `TIMEOUT` / Rueckgabe 124 in JEDEM Zyklus, waehrend die Spur selbst "nichts tut".
  Die Routine-Umgebungsvariable deshalb in BEIDEN Modi setzen, nicht mit der
  Begruendung "bei live ist die Freigabe ohnehin erteilt" weglassen. (b) Die
  Zeitgrenze je Kind muss zum Aufwand passen (breite Scanner brauchen mehr als
  enge Signal-Spuren) - und weil ein gekilltes Kind seine letzten Schritte NIE
  erreicht, gehoert jede Abschlussarbeit (Spiegelung, Zustandsschreiben,
  Protokollzeile) an den ANFANG oder an einen Punkt vor den langsamen Teil: sonst
  bleibt die Kopie ausser Haus still stehen und sieht wie ein Datenproblem aus.
  Beleg in beide Richtungen: Log-Zeile des Zyklus ohne `TIMEOUT` UND ein
  frischer Zeitstempel des Ziels ausser Haus.
- **Vor dem Neustart des Treibers die Herzschlag-Zeitstempel der uebernommenen
  Objekte frisch setzen.** Nimmt der neu gestartete Lauf Objekte auf, die vorher
  nicht in seiner Liste standen (neue Spur, neuer Schattenarm), traegt deren
  Zustand noch den alten `letzter_lauf`. Der erste Zyklus liest das als
  „Herzschlag alt“ und faehrt den Notausstieg: gemessen stellte ein frisch
  aufgenommener Arm seine gerade gebuchten Papierpositionen im ERSTEN Zyklus
  flach (`grund=herzschlag`) und stand danach leer da — die Positionsdaten waren
  weg. Also fuer jede neu aufgenommene Datei den Zeitstempel auf jetzt setzen
  (`.bak`-Kopie behalten), DANN neu starten; der Nachweis ist die erste
  Buchzeile nach dem Neustart (kein `herzschlag`-Ausstieg) und der frische
  Zykluszeitpunkt je Objekt im Log.
- **Ein Neustartskript muss einen bereits toten Prozess vertragen.** Stirbt die
  Wurzel mit ihrem Kind (Windows: venv-Startprogramm + Interpreter), wirft
  `Stop-Process -Id <wurzel>` „kein Prozess mit dieser ID“ — mit
  `$ErrorActionPreference='Stop'` bricht das Skript DA ab und die Komponente
  bleibt tot, waehrend der Aufrufer „Neustart ausgefuehrt“ liest. Reihenfolge:
  erst das Kind, dann die Wurzel beenden, jeden Schritt als „schon weg“
  hinnehmen (Fehler gezielt schlucken, nicht global abschalten), erst danach
  starten. Beleg ist NICHT die ausbleibende Fehlermeldung, sondern die
  nachgezaehlte Prozesszahl (Erwartung: ein Paar je Loop) plus die gelesene
  PID-Datei UND eine frische Zykluszeile im Log.
- **Nicht jeder Codefix braucht einen Neustart des Treibers.** Startet der Treiber
  je Zyklus ein KIND als eigenen Prozess (typisch `handeln.py`), liest das Kind die
  Datei bei jedem Start neu — ein Fix in der Komponente wirkt also im NAECHSTEN
  Zyklus, ohne den Treiber anzufassen (nachgemessen: das Aufraeumen einer Spur lief
  schon vor dem Treiber-Neustart). Ein Neustart ist noetig, wenn sich der
  TREIBER-Code selbst aendert (seine Konstanten, seine Modulliste) — der laufende
  Prozess hat das Modul beim Start importiert.
- **Eine Zykluszeile meldet die WIRKUNG, nicht die Anforderung.** Leitet der
  Treiber den Modus allein aus einer Erlaubnis ab (offenes Zeitfenster) und
  entscheidet das KIND erst, ob es sie nutzt, dann steht im Log `(live)`,
  waehrend die Komponente Papier arbeitet — nachgewiesen an einer Spur, die
  selbst "--live angefordert, aber gesperrt" schrieb, waehrend die Logzeile
  `(live) ok` sagte. Vor dem Melden den eigenen Riegel der Komponente lesen
  (`wachen.json`/Konfigfeld) und den Modus danach waehlen. Der AUFRUF bleibt der
  angeforderte Modus — ein umgeschriebener Aufruf waere eine stille
  Verhaltensaenderung (Aufraeumpfade haengen am Live-Zweig).
- **Ein Zustandswort und ein Aenderungswort nicht in eine Zeile legen.**
  "N Spuren still: …" hiess "seit dem letzten Bericht nichts Neues", wurde aber
  als "abgeschaltet" gelesen. Sammelzeilen sagen ihre Bedeutung selbst an, oder
  sie tragen den Modus je Eintrag — der Nutzer fragt sonst genau danach.
- **Vor dem Neustart eines Treibers mit echten Ordern pruefen, dass kein Kind
  gerade im Order-Zyklus steht.** Die Prozessliste nach dem Kommandozeilen-Merkmal
  des Live-Laufs filtern (z. B. `--live`) und warten, bis keines mehr laeuft —
  ein `taskkill /T` mitten im Zyklus reisst eine Order ab. Danach Baeume PID-genau
  beenden, Basis UND Variante neu starten und im Log den frischen Zyklus plus die
  unveraenderte Live-Position nachweisen.
- **Kein Doppelbetrieb.** Nach einem Test mit `Stop-Process` pruefen, dass genau EIN
  Prozess der Komponente laeuft (`Get-Process <name>`); verwaiste PID-Dateien nach
  dem Aufraeumen loeschen.
- **Nach jedem Deploy des Starters die Routine-Zeile nachziehen**
  (`Wissen/Routinen.md`) — sonst weiss die naechste Sitzung nichts von der Wache.
- **Ein Kind, das mit Exit-Code 0 endet, ist im Supervisor-Log unsichtbar.**
  Ein Supervisor, der nur bei `code != 0` die stderr des Kindes loggt, zeigt bei
  einem Kind, das nach wenigen Sekunden sauber endet, nur „gestartet … gestoppt“
  ohne Grund — und die Sterbeschleife sieht aus wie ein Kinderfehler, obwohl der
  Treiber selbst von aussen abgebrochen wird (Task-Result 3221225786). Diagnose:
  das Kind EINMAL direkt mit der Umgebung starten, die der Supervisor setzt
  (die env-Variablen, die er dem Kind mitgibt — nicht die eigene Shell-Umgebung),
  und die stderr ansehen; laeuft es dort, ist der Treiber das Problem, nicht das
  Kind. Danach den Task-Weg pruefen: `Get-ScheduledTaskInfo`-Result 3221225786
  = der Treiber wurde abgebrochen, nicht die Kinder.
- **`Start-ScheduledTask` auf eine Aufgabe mit `MultipleInstances=IgnoreNew`**
  ist ein No-Op, wenn der Scheduler die Aufgabe noch als „Running“ sieht** —
  der ALTE Prozess (mit dem ALTEN Code) laeuft einfach weiter, ohne
  Fehlermeldung und ohne dass ein neuer Prozess entsteht. Nach jeder
  Codeaenderung an einem so registrierten Dauerprozess zuerst
  `Get-ScheduledTaskInfo` pruefen, dann den KOMPLETTEN Prozessbaum beenden
  (`taskkill /F /T /PID <Wurzel-PID>` — ein einfaches `Stop-Process` auf die
  Wurzel-PID laesst Kinder weiterlaufen), erst DANACH neu starten und am
  Zeitstempel im Log verifizieren, dass die beobachtete Instanz wirklich seit
  dem Neustart laeuft — sonst wird der alte, ungepatchte Lauf fuer einen
  Beleg des Fixes gehalten.
- **Manuell beenden: `Stop-Process -Id <pid> -Force`, nicht `taskkill`.** Aus der
  windows-mcp-PowerShell beendet `taskkill` **nichts** — weder in einer Schleife mit
  `| Out-String` noch als `$r = & taskkill /T /F /PID $p 2>&1; $r -join ' | '`
  (in beiden Formen blieben 4 von 4 Prozessen am Leben, ohne Fehlermeldung, waehrend
  der naechste Schritt schon startete). Folge: kurzzeitig vier Dauerlauf-Loops statt
  zwei — vierfache Netz-/Scanlast und bei gemeinsamem Zustand vierfache
  Positionsueberwachung. `Stop-Process` meldet je PID Erfolg oder „kein Prozess mit
  dieser ID“, und **die Prozesszahl wird danach NACHGEZAEHLT** — Beleg ist die
  gezaehlte Zahl plus die gelesene PID-Datei, nicht die Schleife. Ist versehentlich
  schon neu gestartet worden, sind die ALTEN PIDs zu beenden (die neuen tragen den
  frischen Code), nicht alles. Im CODE eines Treibers bleibt `taskkill /T` fuer den
  ganzen Baum richtig — die Regel hier gilt fuer den Handgriff aus einer Sitzung.
- **Vor dem Beenden die WURZELN der Prozessgruppe bestimmen, nicht eine beliebige PID
  greifen.** Aus einer Liste gleichartiger Prozesse sind die Wurzeln die, deren
  `ParentProcessId` nicht selbst zur Gruppe gehoert; beendet wird jede Wurzel per
  `Stop-Process -Id <wurzel-pid> -Force`, danach die Kindprozesse nachpruefen (sie
  haengen unter Windows nicht automatisch am Elternprozess). Trifft man nur Kinder,
  laeuft die Wurzel weiter und die Kinder wachsen nach — es sieht aus, als haette
  der Kill nicht gewirkt.
- **Eine `CommandLine -like '*Suchtext*'`-Abfrage trifft oft die eigene
  Suchanfrage**, wenn das Terminal den Befehl selbst in einer Bash-/
  PowerShell-Huelle mit dem vollen Text weiterreicht — der gesuchte String
  taucht dann in der Kommandozeile des Abfrageprozesses auf und erzeugt
  Phantomtreffer, die wie ein echter laufender Prozess aussehen. Vor
  „laeuft noch“ das `CommandLine`-Feld ansehen (nicht nur die PID zaehlen);
  ein Treffer, dessen Kommandozeile die eigene Abfrage enthaelt, ist kein
  echter Prozess.
- **Kommandozeilen-Filter praezise auf den SKRIPTnamen stellen, nicht auf einen
  gemeinsamen Wortstamm.** `*dauerlauf*` matcht auch `moondev_dauerlauf.py`
  und andere verwandte Treiber desselben Stamms — eine „laueft noch“-/Instanzen-
  Zaehlung wird damit um eine fremde Prozessgruppe falsch (gemessen: 9 Treffer,
  davon 6 Fremdprozesse). Vor dem Zaehlen die Trefferliste je Prozess gegen den
  vollen Skriptnamen halten oder auf den exakten Pfad filtern
  (`CommandLine` endet auf `handel\dauerlauf.py`).
- **Vor einem manuellen Neustart den Cron-Verlauf des Waechters lesen, nicht
  nur den Live-Zustand.** Ein `no_agent`-Hermes-Cron schreibt jeden Lauf nach
  `Agenten/Hermes/cron/output/<job-id>/<zeitstempel>.md` — bei Erfolg leer
  (`silent (empty output)`), bei Eingriff mit Befund und Startversuch. Die
  Job-ID liefert `hermes.exe cron list`. Mehrere Dateien in Zeitfolge zeigen,
  ob der Waechter einen Ausfall bereits selbst geheilt hat, bevor manuell
  eingegriffen wird — sonst ist der manuelle Neustart entweder ueberfluessig
  ueberfluessig oder verdeckt, dass der Waechter allein schon ausgereicht haette.
  Ob ein frisch angelegter Auftrag ueberhaupt schon gefeuert hat, steht im
  Job-Satz selbst (`Agenten/Hermes/cron/jobs.json`: `last_run_at`, `last_status`,
  `failure_streak`, `next_run_at`) — fuer `no_agent`-Auftraege kann
  `hermes cron runs <name>` leer bleiben; der Job-Satz plus die Ausgabedatei sind
  die Belege. Ein neuer Cron gilt erst als eingerichtet, wenn `last_status=ok`
  und mindestens eine Ausgabedatei mit dem erwarteten Inhalt existiert.
- **Nach der Reparatur eines Cron-Skripts den Auftrag SOFORT feuern, nicht auf den
  naechsten Takt warten.** Der gespeicherte `last_status` bleibt auf `error`
  stehen, bis der Auftrag wieder gelaufen ist — bei einem 6-Stunden-Takt also bis
  zu sechs Stunden nach dem Fix. In dieser Zeit meldet jede Wache, die den
  Job-Satz liest (Automatik-Waechter), weiter den reparierten Defekt, und eine
  Frische-Pruefung, die auf `letzter_lauf` der betroffenen Objekte schaut, sieht
  einen Ausfall, der schon behoben ist. Reihenfolge: Skript reparieren ->
  `cronjob_manage action=run` -> den frischen Lauf als `ok` lesen -> erst dann
  "behoben" berichten. Ein Befund, der nur aus einem alten Status stammt, ist
  kein Befund.
- **Ein `Script exited with code 15` (SIGTERM) ist eine EXTERNE Beendigung des
  Prozesses, kein Fehler des Skripts.** Ein no_agent-Skript, das nur 0/1
  zurueckgibt, kann einen 15er nie selbst erzeugen - der Prozess wurde waehrend
  des Laufs von aussen gekillt. Diagnoseweg: (1) `cron/executions.db`
  (`sqlite3`) abfragen und die fehlgeschlagenen Laufe NACH JOB und UHRZEIT
  gruppieren: mehrere code-15 an EINEM Tag ueber verschiedene Jobs weisen auf
  einen gemeinsamen externen Killer (Speicherdruck, MoonDev-Leak, ein
  Aufraeumer mit `taskkill`) statt auf die Jobs; (2) Laufzeit des geplatzten
  Laufs gegen die gesunden vergleichen - ein viel kuerzerer Lauf wurde
  abgebrochen, nicht abgestuerzt; (3) Gateway-Restarts zum Zeitpunkt
  ausschliessen (`gateway.log`); (4) freien Commit pruefen
  (`Win32_OperatingSystem.FreeVirtualMemory`) - knapper Commit ist die
  haeufigste Quelle solcher Killings, mit `WinError 1455` als Vorbote.
  Ein code-15 ist ein ALARM, kein echter Ausfall: der Job heilt von selbst
  (naechster Takt laeuft wieder), und das ueberwachte Objekt lief nie ohne
  Daten. Das Skript nur anfassen, wenn danach wirklich etwas reproducible
  scheitert; den 15er allein nicht als Skriptbug behandeln.
  Jeder Lauf stirbt an derselben Stelle mit demselben Traceback, waehrend der
  Schaden woanders sitzt: Berichte und Merker, die dieses Skript schreiben
  sollen, frieren ein, und die Objekte sehen danach "seit Tagen alt" aus. Beim
  Reparieren das Skript mit `write_file` schreiben und als DATEI ausfuehren -
  Python-Quelltext mit Escape-Sequenzen durch einen Shell-Heredoc zu schieben
  zerstoert ihn (die Huelle loest die Escapes auf). Und in einer Reparaturschleife
  mit `ast.parse` pruefen: `py_compile.compile(..., doraise=True)` wirft
  `PyCompileError`, das ein `except SyntaxError` NICHT faengt.

## Verification

Eingerichtet ist ein Dauerprozess, wenn alle drei stehen: (a) der Prozess laeuft und
PID-Datei und `Get-Process` stimmen ueberein, (b) die Wache gibt bei laufendem
Prozess **nichts** aus und startet nach einem `Stop-Process` nachweislich neu,
(c) die Komponente tut ihre Arbeit — mit einer erzeugten Eingabe und der
beobachteten Ausgabe belegt.

## Abgrenzung

- Was die Komponente fachlich tut: ihr eigener Skill (z. B. `projectatlas`)
- Dienstzustaende und Ereignisse pruefen: `systemdiagnose`
- Eine geplante Aufgabe an den Bus melden: `bus-integration`
