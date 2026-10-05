---
name: code-audit
description: "Use when ein Baum auf Bugs geprueft wird."
version: 0.1.1
author: Hermes Agent
platforms: [windows]
license: private
metadata:
  hermes:
    tags: [Code-Audit, Bugs, Subagenten, Verdrahtung, Gegenprobe, BrainFiles]
    related_skills: [trugschluesse, messwerkzeug-gegenprobe, handel-spuren, subagent-delegation, brainstorming]
---

# Code-Audit — einen Baum auf echte Bugs pruefen

Ein Audit ist kein Scan. Ein Scan liefert **Kandidaten**, ein Audit liefert
**Befunde** — und der Unterschied ist die Arbeit. Gemessen an einem Audit ueber
den BrainFiles-Baum: vier Schnellpruefungen der Sitzung meldeten zwei
scheinbar schwere Befunde, beide widerlegt (ein toter Import, der ein
Re-Export ist; vier Spuren, die angeblich keine Auswertung hatten, die aber
absichtlich eine eigene fuehren). Ohne den Widerlegungs-Schritt waeren zwei
Fehlalarme mit Datei:Zeile-Autorenschaft in die Antwort gegangen.

Subagenten liefern in diesem Auftrag erfahrungsgemaess **mehr Kandidaten als
Befunde**. Die Regel des Skills ist deshalb eine Reihenfolge, nicht eine
Tatsachenliste: erst Breite im Kind, dann Beleg, dann Verdacht im Haus.

## When to Use

- „Suche Bugs im Baum", „optimiere Code und Funktionen", „was ist hier falsch verdrahtet"
- ein Bereich ist ungepflegt oder rote Tests stehen neben gruenen
- vor einer Freigabe, einem Commit, einer Groessenaenderung
- eine Zahl aus dem Baum wirkt falsch und niemand weiss, welche Zeile sie schreibt

**Don't use for:** einen einzelnen konkreten Fehler lokalisieren
(`systematic-debugging`), Zustand im Betrieb belegen (`trugschluesse`), eine
Handelsspur anbinden (`handel-spuren`), die Reihenfolge einer Parameteraenderung
(`messwerkzeug-gegenprobe`, `handel-spur-optimierung`).

## When NOT to optimize

**Optimieren ist eine eigene Entscheidung, kein Audit-Ergebnis.** Ein Befund
rechtfertigt den Fix, nie die Umstellung. Geht der Auftrag ueber „Bugs finden"
hinaus, den zweiten Teil mit `/brainstorming` behandeln: erst zwei bis drei
Ansaetze mit Abwaegung und Empfehlung, Design vorlegen, **auf Zustimmung
warten**, dann bauen. Ohne diese Rueckfrage wird aus einem Audit still ein
Refactoring, das niemand bestellt hat.

## Prerequisites

- Aus der Repo-Wurzel arbeiten; Pfade relativ zur Wurzel, keine absoluten in
  Skripten oder Briefen.
- Vor jedem `python`/`hermes`-Aufruf aus dem MCP-Kontext `PYTHONHOME` und
  `PYTHONPATH` leeren.
- Das `terminal`-Backend laeuft in einer Sandbox auf demselben Host: native
  Programme brauchen Pfade als `C:/Users/...` mit Schraegstrichen (MSYS-Pfade
  schlagen bei nativen Programmen fehl, `cd` als Bash-Befehl geht).
  Die Sandbox-Uhr geht rund sieben Stunden nach: **Datum und Zeit nie aus
  `date` nehmen**, sondern aus Dateizeitstempeln oder `git log`.

## How to Run

1. Den Baum in **Bereiche ohne Ueberschneidung** schneiden (Handelskern /
   Betrieb und Dienste / viele gleichartige Einheiten / Werkzeuge und Config).
   Jeder Bereich genau ein Kind; nie zwei Kinder auf dieselbe Datei.
2. Jedem Kind den **Nur-Lesen-Vertrag** mitgeben und die Umgebungsfallen
   ausschreiben — ein Kind erbt weder die Regeln noch den Fremddateischutz.
   Fertige Briefe: `references/dispatch-briefs.md`.
3. Von jedem Kind **eine Gegenprobe je Befund** verlangen, nicht nur gelesenen
   Code: ein Wegwerf-Skript in `Agenten/Hermes/cache/scratch/`, das zeigt, dass
   das Fehlverhalten wirklich auftritt.
4. **Waehrend die Kinder laufen**, eigene breite Schnellpruefungen fahren
   (Sekunden, und sie liefern die Baseline, an der sich die Kandidatenmenge
   messen laesst).
5. Jeden Kandidaten **am echten Aufrufer im ganzen Baum** gegenpruefen und
   darauf pruefen, ob das Fehlen **absichtlich** ist.
6. Befunde nach Schwere ordnen: ein Fehler, der Buch, Geld oder Positionen
   falsch rechnet, schlaegt ein Fehler in einer Meldung.

## Quick Reference

| Frage | Werkzeug | Was die Antwort beweist |
|---|---|---|
| Parst der ganze eigene Code? | `ast.parse` je `.py` | Syntax ist ausgeschlossen |
| Parst der ganze eigene PowerShell? | `[System.Management.Automation.Language.Parser]::ParseFile` | Klassenfehler gefunden, die erst zur Laufzeit schlagen |
| Gibt es stille Ausnahmen? | AST: `except:` bzw. Handler mit leerem Rumpf | ein verschluckter Fehler |
| Ist eine Verdrahtungsliste vollstaendig? | Liste aus **beiden Modulen importieren**, dann Differenz | Kandidat, kein Befund |
| Ist eine Messzahl **verdaechtig glatt** (0 Runden, 0 %, exakt runde Zahl)? | Das Betriebsmerkmal der Konfiguration pruefen: loest es im Messweg ueberhaupt aus? | Befund — ein Gatter, das nur im Betrieb zuegt |
| Meldet eine Sonde **alles leer/gesperrt/fehlend**? | Erst ihren eigenen Pfad und ihre Config-Aufloesung pruefen | Der Befund liegt an der Sonde, nicht am Bestand |
| Meldet eine Sonde **alles leer**, obwohl der Bestand voll ist? | Aufloesen, ob ihr Datenwurzelpfad **aus `__file__`** kommt, und `git ls-files` auf den Datenordner | Sie sieht in jeder Kopie ohne den (nicht versionierten) Bestand einen anderen Ordner — der Befund liegt an der **Aufrufumgebung**, der Bestand ist richtig |
| Bewegt sich die Zahl eines Pruefers nach einer bekannten Aenderung **nicht**? | Der Pruefer liest nicht alles, was er zu lesen glaubt | Pruefer-Fehler, nicht Datenfehler |
| Stimmt ein Kandidat? | Aufrufer + Prosa im Modul | Befund oder Fehlalarm |
| Wirkt ein Fix ueberhaupt? | zwei Laeufe, ein Wert verschieden | siehe `messwerkzeug-gegenprobe` |

Die vier Schnellpruefungen als Kopiervorlage: `references/dispatch-briefs.md`.
Der Sweep fuer tote Konstanten: `scripts/tote_konstanten.py` (fuenfte
Schnellpruefung).

## Procedure

### 1. Schneiden, ohne Ueberschneidung

Ein Bereich je Kind, und die Bereiche decken den Baum ab. Die Liste der
abgedeckten Bereiche **vor** dem Dispatch festhalten — sie ist die Antwort auf
„was wurde nicht geprueft". Was nicht geprueft wurde, wird im Bericht genannt,
nicht verschwiegen.

### 2. Der Nur-Lesen-Vertrag

Jedes Kind bekommt ausgeschrieben (es kennt keine dieser Fallen):

- keine Datei aendern, kein `git add/commit`, kein Neustart von Diensten, kein
  `schtasks create/run`, kein Anlegen geplanter Aufgaben
- **kein Aufruf, der in echte Betriebsdaten schreibt** — Spuren, Journale,
  `ablehnungen.csv`, Zustandsdateien bleiben unberuehrt
- Wegwerf-Skripte nur in `Agenten/Hermes/cache/scratch/`
- die Dateien der parallelen Sitzung namentlich als fremd benennen
- Sandbox-Pfade, Uhr, CRLF-Falle
- Antwortform: hoechstens zehn Befunde, Form **Schwere, Datei:Zeile,
  Fehlverhalten, Beleg, Fix-Vorschlag in Prosa**; Unbelegtes kommt nicht in
  die Liste

### 3. Der Auftrag verlangt eine Gegenprobe

Gelesener Code ist ein Verdacht, kein Befund. Der Auftrag verlangt pro Befund
einen **ausgefuehrten** Beleg: ein Skript, das das Fehlverhalten zeigt.
Kinder, die das liefern, liefern zwei bis drei Mal weniger Rauschen als
Kinder, die nur lesen duerfen.

### 4. Eigene Schnellpruefungen parallel fahren

Vier breite Laeufe kosten Sekunden und sind ein guter Anlass, selbst zu
pruefen statt nur zu warten:

1. `ast.parse` ueber alle eigenen `.py` (venv, Fremd-Repos, `site-packages`
   ausgenommen)
2. `Parser::ParseFile` ueber alle eigenen `.ps1`
3. AST auf `except:` und auf Handler mit leerem Rumpf
4. Verdrahtungslisten aller Module **importieren** und Differenz bilden
5. **Tote Modulkonstanten**: `scripts/tote_konstanten.py` meldet jede
   Konstante, die definiert, aber nie gelesen wird — und jede, die nur im
   Docstring vorkommt. Beides behauptet eine Sicherung, die es nicht gibt
   (`python scripts/tote_konstanten.py --breite <ordner>`).

Ihr Ergebnis ist eine **Baseline**: „null Syntaxfehler, null stille
Ausnahmen" ist eine Aussage, die man dem Nutzer geben kann, und sie grenzt
die Kandidatenmenge der Kinder ein.

### 5. Kandidat ist nicht Befund

Drei Filter, in dieser Reihenfolge:

- **Gegensaetige Quelle:** Was liest und schreibt diese Stelle wirklich?
  Ein Name, den nur der Aufrufer kennt, kann nicht befundlich sein.
- **Absicht:** Fehlt eine Verdrahtung **absichtlich**, steht der Grund als
  Prosa im Modul selbst — Docstring, Fusszeile, Kommentar neben der Stelle.
  Immer greppen, bevor ein Loch gemeldet wird.
- **Grund, nicht nur Differenz:** Wer meldet, nennt, was ohne den Befund
  passiert. Ein Loch, das dokumentiert ist, ist eine Entscheidung.

Widerlegte Kandidaten werden **benannt und zurueckgenommen**, nicht
weggelassen: sie zeigen dem Nutzer, dass die Suche geprueft hat.

#### Der vierte Filter: eine Sonde, die alles leer meldet, ist selbst der Befund

Wenn eine Sonde **systematisch** „nichts vorhanden", „alles gesperrt",
„kein Ziel" oder „0" meldet, ist das Ergebnis verdächtiger als ein
gemischtes Ergebnis: ein Fehler in der **Pfad- oder Config-Aufloesung der Sonde**
erzeugt genau diese Form, weil `open()` fehlende Dateien als leeres Dict
liefert und ein falscher Basispfad **keinen** Fehler ausloest. Ein Beispiel aus
dem Haus: ein Werkzeug bildete seine Basis mit einem festen `dirname` zwei
Ebenen zu hoch, bekam fuer jede Einheit `{}` und meldete daraufhin
„alle 12 gesperrt" — was plausibel klingt und die Umkehrung der Wahrheit war
(10 waren scharf). **Die Form des Ergebnisses ist das Warnsignal:** je
einheitlicher das Ergebnis, desto eher ist es die Sonde.

#### Der fuenfte Filter: derselbe Filter, aber der Leser sitzt woanders

Der vierte Filter prueft die **Basis** der Sonde. Diese Variante ist
schwieriger, weil der Code **richtig** ist: das Werkzeug bildet seinen
Datenwurzelpfad aus der Modulposition (`HIER = os.path.dirname(os.path.abspath(__file__))`,
dann `ORDNER = HIER/daten/…`). Das ist portabel und richtig — und **falsch**
in jeder Kopie, die der Pfad aufloest, ohne den Datenbestand mitzubringen.
Betroffen sind Worktrees (`.worktrees/<karte>`), Kloene und jede Kopie, die nur
den Code bekommt. Was **nicht** versioniert ist (`git ls-files '<ordner>'` leer),
fehlt in **allen** Kopien — eine Testsuite aus einem Worktree meldet dann
ehrlich „Historie fehlt, 0 Kerzen", und der Bestand auf der Platte ist voll.

Beim Befund gehoeren deshalb **drei** Dinge zusammen, nicht die Meldung allein:

1. **der Pfad, den der Aufruf wirklich aufloest** — `python -c "import modul;
   print(modul.ORDNER); print(os.path.isdir(modul.ORDNER))"`, nicht der
   Pfad, den man im Kopf hat;
2. **das Arbeitsverzeichnis des Absenders**, im Sitzungsspeicher belegt und
   damit in Sekunden auffindbar: `state.db`, Tabelle `messages`,
   `role='assistant'`, `tool_calls` als JSON, **`session_id` mitschreiben** —
   ohne diese Spalte sieht man nur die eigene Sitzung und schliesst die
   Nachbarsitzungen aus, die zur selben Minute liefen;
3. **der Gegenbeweis ohne den Bestand**: eine Kopie der `.py`-Dateien im
   Temp-Ordner **ohne** den Datenordner erzeugt dieselbe Meldung. Damit ist
   belegt, dass kein Loeschvorgang stattgefunden haben muss.

Zwei Fehlinterpretationen, beide gemessen, und beide teuer, weil sie als Beleg
auftreten: der **mtime eines Nachbarverzeichnisses** gilt nicht als
Loeschbeleg (ein Ordner ohne Inhalt traegt keinen eigenen Zeitstempel; man
greift dann zum Nachbarn, und dessen frische mtime ist ein Schreibvorgang),
und eine Suche nach dem **Loesch-Aufruf** beantwortet nicht die Frage, **ob**
geloecht wurde — 28 Loeschaufrufe im Zeitfenster, keiner davon im Zielordner,
ist das richtige Ergebnis und gehoert in den Bericht. **Reihenfolge: hat der
Leser den Bestand ueberhaupt gesehen, dann wer ihn nicht sieht, dann ob
ueberhaupt jemand zustandig war.**

Die Nachfuehrung ist eine **Naht**, keine neue Rechnung: die Meldung nennt den
gelesenen Pfad, oder ein Schalter laesst den Pfad aus der Umgebung kommen. Ein
zweiter Treffer derselben Art (Werkzeug **und** Testsuite bilden den Pfad
gleich) ist ein Muster und der richtige Moment fuer die Naht — nicht fuer eine
weitere Fehlermeldung.

#### Ein Gatter, das im Messweg nie ausloest

Der teuerste Befund dieser Klasse: ein **Betriebsmerkmal**, das im Betrieb
arbeitet (ueber einen getrennten Ausfuehrer, eine Queue, ein Zeitfenster) und
im Messweg **strukturell nie** greift — also 0 Buchungen, 0 Signale, 0
Eintraege erzeugt, ohne Fehlermeldung. Geprueft wird das so: wenn eine Zahl
**auffaellig glatt** ist (0 Runden ueber Jahre, exakt 0 %, eine Quote, die
sich nie bewegt), das Konfigurationsfeld dieser Spur lesen und fragen, was es
im Betrieb tut. Ein Merkmal, das Signale umleitet statt zu buchen, macht die
gesamte Historie dieser Kennzahl unbrauchbar — auch wenn die Zahl nie
auffaellig war, sondern einfach aus einem Lauf mit dem Feld stammt. Das ist ein
Befund **ueber der Zeile**, keine Zahl, und gehoert an den Nutzer, bevor er
irgendeine Zahl aus dieser Quelle zitiert.

### 6. Konstanten vergleichen: importieren, nicht extrahieren

Ein AST-Walker, der „alle grossgeschriebenen Zuweisungen" sammelt, greift
auch Nachbarliterale auf und liefert eine Liste, in der `kill-switch` und
`notausstieg` als Spurnamen stehen. **Module importieren und das Attribut
lesen:**

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && python -c "
import sys; sys.path.insert(0, '.')
import dauerlauf, auswertung_alle
print(len(dauerlauf.SPUREN), len(set(auswertung_alle.SPUREN)))"
```

Geht der Import nicht (fehlendes Paket, Fremdbau), ist der Kandidat ein
Hinweis auf einen toten Import — nicht auf einen Zahlendreher.

### 7. Ein neuer Pruefer prueft sich selbst zuerst

Ein Pruefer, Register-Check oder Verdrahtungs-Differenz, den man selbst gebaut
hat, ist am Anfang die fehleranfaelligste Stelle des ganzen Audits — seine
Annahmen sind ungeprueft, und eine falsche Annahme produziert Befunde gegen
korrekte Daten. **Die Annahmen gegen die ECHTEN Daten stellen, nicht gegen eine
Fixture, die ihnen zustimmt.** Drei Formen, alle im Haus gemessen:

- **Annahme „das ist ein Ordner".** Ein Besitzregister darf Ordner *und*
  Einzeldateien fuehren (`TASKS.md`, ein Manifest). `os.path.isdir` meldete
  beide als „toten Bereich" — der Pruefer war der Fehler, das Register korrekt.
  Der Fix ist `os.path.exists`, und die Regel lautet: **eine Typannahme ueber
  den Bestand muss die Vielfalt des Bestands kennen**, sonst sucht sie einen
  Fehler, den sie selbst gebaut hat.
- **Annahme „ein Abschnitt ist eine Section-Marke".** `count("## Erledigt")`
  zaehlte die Erklaerung am Dateianfang mit (dieselben Woerter in einem
  Aufzaehlungspunkt) und brach mit „Abschnittsmarken veraendert" ab. **Nur die
  MARKE am Zeilenanfang zaehlen**, nie das Wort.
- **Annahme „ein Block ist eine Zeile".** `git worktree list --porcelain`
  liefert je Baum einen Block aus drei Zeilen, getrennt durch LEERZEILEN.
  Zeilenweise gelesen hat der Pfad des naechsten Blocks den vorigen
  ueberschrieben: es kam EIN Eintrag heraus statt zwei, ohne Fehlermeldung.
  **Blockstrukturen als Bloecke lesen.**

  **Und dieselbe Regel gilt fuer die Breite des Pruefers selbst: der ERSTE
  Befund geht von Hand an den Quelltext, bevor die Liste gemeldet wird — und
  ein falscher erster Befund heisst „Pruefer verengen", nicht „Liste mit
  Einschraenkung melden".** Zwei Auditor-Fassungen an einem Tag, beide
  verworfen: eine nannte elf Dateien mit „Rufumfang ohne Fehlercode, Ausgabe
  nicht geprueft", von Hand nachgefuehrt faengten die beiden ersten den Fehler
  aktiv ab (`except` mit Klartext, danach ein zurueckgegebener Leerwert mit
  dokumentierter Bedeutung) — der Befund war falsch. Die breitere Fassung
  nannte 63 Dateien ohne jede Fehlermeldung: das ist der Normalbau der
  ganzen Familie, kein Befund. **Ein Pruefer, der elf Mal falsch alarmiert,
  ist schlimmer als keiner** — er kostet die Aufmerksamkeit, die ein echter
  Befund braucht. Die Reihenfolge ist deshalb **Breite zuerst messen, dann
  verengen, NIE umgekehrt**; und was ein Pruefer nicht beweisen kann, meldet
  er nicht: meldet eine Form statt eines Zustands („baut die Datei mit `/`
  einen Dateinamen“), nicht „dieses Werkzeug fehlt“ — das waere eine
  Behauptung ohne Beleg. Auf die leere Liste folgt kein zweiter Versuch mit
  derselben Annahme, sondern eine engere Regel oder das Eingeständnis, dass
  die Frage nicht mechanisch entscheidbar ist.
  **Und dieselbe Regel fuer Testattrappen: eine Attrappe traegt die ANNAHMEN des
  Pruefers, nicht die Regel.** Fuenf Baufehler einer Attrappenklasse, alle an
  einem Tag gemessen, mit 7 / 4 / 9 Fehlschlaegen aus drei davon:
  (a) **eine Ebene zu hoch** — die Attrappe lag in `tmp/historie`, das Werkzeug
  liest `tmp/daten/historie`; getestet wurde der Fehlerpfad. (b) **zwei
  Zeitanker** — Datei und „jetzt" trugen verschiedene Konstanten, die gespannte
  Datei lag damit in der ZUKUNFT, jede Reihe war juenger als null Tage, und die
  Fehlschlaege kamen aus einem Vorzeichenfehler im Attrappenbau, nicht aus der
  Regel. (c) **zu wenig Datenmenge** — die Tests legten 1–4 Reihen an, der
  Verbraucher verlangt `mindest_symbole=30`; die Meldung handelte dann immer von
  der Mindestzahl und die eigentlich gepruefte Regel (Alter) war gar nicht
  entscheidbar. (d) **falscher Anker** — `HIER.parents[3]` endete eine Ebene zu
  weit und las eine Datei, die es dort nicht gibt; die Meldung liest sich wie
  ein Dateifehler, nicht wie ein Ankerfehler. (e) **`self` im falschen Lambda** —
  eine umgebogene Funktion braucht dieselbe **Signatur** wie das Original,
  sonst bricht schon der Aufbau.
  **Die zwei Massvorgaben, die die Klasse abschaffen:** EIN Zeitanker fuer
  Datei und „jetzt" (eine Konstante `Attrappe.JETZT`), und **genau die Menge,
  die die gepruefte Regel verlangt** — jede Regel mit eigener Menge, sonst
  entscheidet die benachbarte Regel. Und die Regel darueber: **die Zahl der
  Fehlschlaege sagt nichts ueber die Regel, sie zaehlt die Annahmen der
  Attrappe.** Fuenf solcher Baufehler hintereinander sind kein Zufall, sondern
  fehlende Massvorgaben — ab dann ist die Attrappe das Problem, nicht der Code.

Dazu zwei Regeln, die beim Bau von Werkzeugen mit Handlungsfolgen gelten und
die ein Audit als **Befund an der Bremse** pruefen soll, nicht an der
Funktion: ein Pflichtfall muss **unveraendert ueberleben** (ein Objekt mit
echtem Inhalt wird nie entfernt), und ein Befund braucht einen **Exitcode**,
nur eine Zeile im Text meldet ein Cron als „alles ok". Beides ist im
Aufraeumen-Werkzeug `Agenten/Werkzeuge/zweige.py` so gebaut und getestet.

### 9. Ein eingefrorener Testwert ist kein Befund, sondern eine Alarmstufe

Rote Tests beim Audit sind **zwei** Klassen, und die Unterscheidung gehoert in
den Befund:

- **Kaputte Pruefung.** Ein Test haelt einen Wert fest, der einer **gelegentlichen
  Aenderung** folgen darf — ein Boersensatz, ein Schalterstand, eine Zuordnung
  zu einem Ziel, ein Format-Checker, der auch eine Datei oder Ordner akzeptiert.
  Der Test meldet nicht mehr, was die Regel soll, sondern einen alten Stand.
  Behandelt wird die **Eigenschaft**, nicht der Wert: „der Satz dieser Boerse",
  „der Arm handelt nicht", „die Zahl stimmt mit der Quelle ueberein".
- **Falscher Test durch Uebergeneralisierung.** Eigener Zusatz an einem Feld,
  dessen Wert einer **feste Menge** unterliegt (eine Familie, ein Dateiformat).
  Auch das ist eine kaputte Pruefung, keine Codeaenderung.

Der Nachweis ist immer derselbe: **auf `HEAD` zuruecknehmen** (nur die
Aenderungen dieses Audits, mit Sicherung daneben), die Suite erneut fahren, und
das Ergebnis festhalten. Ein Test, der auf `HEAD` genauso rot ist, ist
vorbestehend — das gehoert als eigene Zeile in den Bericht, nicht als
stillschweigende Korrektur. Ein Test, der erst durch die eigene Aenderung rot
wurde, ist fast immer eine kaputte Pruefung, die die Aenderung sichtbar macht.

### 10. Ein gruener Pruefer, der nicht alles liest

Ein Pruefer, der gruen meldet, beweist nur, **was er liest**. Zwei Formen, beide
gemessen:

- Ein Muster erkennt nicht alle Schreibweisen des Bestands (Statuszeichen,
  Leerraum, Endung) und zaehlt deshalb nur einen Teil der Eintraege — er
  meldete die hoechste Nummer einer Liste, die 26 Eintraege weiter war.
- Ein Cache auf Modulebene wird nur bei **leerem** Inhalt neu geladen und
  ueberlebt damit jeden Test, der danach in einem Temp-Ordner arbeitet: das
  Ergebnis ist eine Zahl aus fremden Daten, ohne Fehlermeldung.

Gegenprobe beider Formen ist dieselbe: **eine Aenderung ausloesen, von der man
weiss, dass der Pruefer sie sehen muss**, und die Zahl sich bewegen sehen. Ein
Pruefer, dessen Zahl sich nicht bewegt, ist kaputt, egal was er sagt.

### 11. Ein Massstab aus einem ANDEREN Skill: erst die Uebertragbarkeit pruefen

Wenn ein Zielbild in einem Skill steht (eine Design-Rubrik, eine
Konformitaetsliste, eine Stilregel), ist der naheliegende Auftrag an die
Kinder, sie daran zu messen. Das erzeugt ohne eine Zusatzregel systematisch
Fehlbefunde, weil **ein Kriterium nicht in jedes Medium uebertragbar ist**.
Das richtige Schema ist: jede Rubrikposition wird gegen ihre Uebertragbarkeit
geprueft und die Entscheidung mitgeliefert — „gilt voll / gilt in dieser
Form nicht, weil X im Medium fehlt / gilt als Aequivalent in Form Y".

Der Nutzen ist doppelt: die Kinder melden echte Befunde statt solcher, die
die Oberflaeche gar nicht haben kann, und die Urteilsfaehigkeit „welche
Kriterien ueberhaupt gelten" wird selbst zum Ergebnis. Ein Audit, das nur
zaehlt, verhaelt sich zum angebotenen Massstab wie ein Pruefer, der nicht
alles liest — es beweist nur, was es zu pruefen hatte.

Zwei Formen der Uebertragbarkeit, beide im Haus gemessen:

- **Medium, nicht Werkzeug:** Kriterien, die eine CSS-Eigenschaft
  beschreiben (Verlauf, Weichzeichner, abgerundete Bildflaeche), existieren
  im Desktop-Widget-Baum nicht. Sie als „nicht erfuellt\" zu melden waere
  ein Fehlbefund — **ersetzen durch das, was dasselbe Problem in diesem
  Medium loest**, oder als gegenstandslos streichen und begruenden.
- **Sonderfall Nutzen:** eine Rubrik verlangt, keine Zahl zur Schau zu
  stellen. In einem Werkzeug, in dem die Zahl selbst der Nutzen ist, gilt
  das nicht. Der richtige Befund ist dann die **Umkehrung** — die
  wichtigste Zahl ist die kleinste und blasseste, waehrend eine
  nebensachliche Anzeige die groessere bekommt.

Zaehlt eine Rubrik am Ende nur „ein Punkt von zehn", ist die Frage nicht die
Punktezahl, sondern ob die Punkte ueberhaupt die schweren Befunde tragen. Ein
niedriger Wert neben zwei Funktionsausfaellen ist ein Befund ueber die
**Reihenfolge der Arbeit**: die schweren Dinge lagen nicht in dem, was die
Rubrik misst. **Ein Rubrikpunkt ist kein Freipass fuer das, was er nicht
prueft** - die Score-Zahl gehoert neben die Liste der Funktionsausfaelle in
dieselbe Zeile, sonst liest sie sich als Entwarnung fuer das ganze Fenster.

Daraus folgt die Frage, die man sich nach jedem Rubriklauf stellt: **welche
Klasse von Schaden kann diese Rubrik ueberhaupt nicht sehen?** Fuer eine
Layout-Rubrik sind es drei, und alle drei kamen im Haus vor: eine Funktion,
die gar nicht aufgerufen wird; ein Wert, der nach einem Bedienvorgang
ueberschrieben wird; ein Text, der gar nicht sichtbar ist. Keines davon hat
Punkte gekostet.

### 12. Erwartete Fehlalarmklassen

Diese vier treten bei dieser Pruefung regelmaessig auf und gehoeren
ausdruecklich zur Arbeit:

- **`from __future__ import annotations`** erscheint in jeder Liste toter
  Importe. Das ist die Compiler-Anweisung, kein Import — immer ausfiltern.
- **Ein Import, der nur re-exportiert.** Ein Modul fuehrt Namen weiter, weil
  andere Module sie historisch ueber dieses Modul holen. Die Namen sind
  unbenutzt und trotzdem noetig; der Kommentar an der Importstelle sagt es.
- **Eine Verdrahtungsliste, die ein Modul bewusst auslaesst**, weil es eine
  eigene Auswertung mit eigener Paarung fuehrt (gemessen: 107 Runden falsch
  gepaart, wenn man sie in die gemeinsame Paarung zwingt).
- **Rundenzahlen, die nach einem Muster aussehen.** Runden kommen aus der
  Paarungsfunction des Hauses, nicht aus gezaehlten Zeilen.

## Pitfalls

- **Ein Sweep ist eine Kandidatenliste, kein Ergebnisbericht.** Die Regel gilt
  fuer die eigene Sitzung genauso wie fuer jedes Kind: was statisch
  abweicht, kann Absicht sein. Wer die Sweeps als Befunde weitergibt, liefert
  Fehlalarme mit Datei:Zeile-Autorenschaft — das schlimmste Format, weil es
  belegt wirkt.
- **Fehlende Verdrahtung wird im Modul selbst begruendet.** Immer die Prosa
  neben der Stelle lesen, bevor eine Luecke gemeldet wird.
- **Ein Audit darf keinen Schaden anrichten.** Die Sonden eines Kindes sind
  manchmal schaedlicher als der gesuchte Bug — der Auftrag muss ein Aufrufen
  von `handeln.py` im echten Modus, das Schreiben in Spurordner und jeden
  Dienststart ausschliessen.
- **Die Sandbox-Uhr ist kein Datum.** Ein Audit, das „seit drei Tagen"
  behauptet, hat `date` gelesen.
- **Ein Kind, das Befunde meldet, ohne eine ausgefuehrte Gegenprobe**, hat
  gelesen. Seine Liste ist eine Leseliste; beim Umgang den Faktor einkalkulieren.
- **Ein Fix ohne Messung ist eine Vermutung mit Schreibzugriff.** Erst die
  Zahl, dann der Eingriff (`messwerkzeug-gegenprobe`).
- **Ein abgebrochener Laufliefert kein Ergebnis.** Ein langer Testlauf, der ohne
  Zusammenfassung stirbt (Zeitlimit, killed, abgebrochene Kette), hinterlaesst
  eine Logdatei mit viel Ausgabe und **ohne** Ergebniszeile. Diese Logdatei ist
  kein Testresultat und wird nicht als eines berichtet — immer auf die
  Zusammenfassung und den Exitcode pruefen, sonst gilt „unbekannt", nicht
  „gruen". Fuer die Restlaeufe die Suite in Bloecke teilen und je Block fahren.
- **Ein Wert darf nicht aus den Notizen abgeleitet werden.** Konfigurationswerte
  stehen in Feldern; die Prosa daneben (`_vermerk`, `_quelle`, Kommentare)
  erwaehnt haeufig die falschen Begriffe und ist kein Feld. Ein Pruefer, der
  das ganze Objekt nach einem Schluesselwort durchsucht, liest Kommentare.
- **Eine Liste von Namen, die einer anderen Liste folgen muss, wird abgeleitet,
  nicht abgeschrieben.** Fest verdrahtete Namen fallen bei der naechsten neuen
  Einheit still aus — und eine neue Einheit, die in keiner Liste steht, sieht
  vollstaendig aus.
- **Eine Grenze, die als Konstante dasteht und von niemandem gelesen wird,
  ist keine Grenze.** Der teuerste Befund dieser Klasse hat die Form „das Feld
  ist gesetzt, der Code prueft es nie" — eine Abbruchbedingung im Kommentar
  beschrieben, im Abbruch selbst vergessen. Gemessen: eine Oberflaeche, die
  Spaltenbreiten nach dem ersten Befuellen nachrechnen sollte, tat das bei
  jeder Aenderung weiter; die Nutzereinstellung war nach EINEM Takt wieder
  weg. **Die Suche nach toten Konstanten ist eine eigene Sweep und gehoert in
  die vier Schnellpruefungen**: ein Modulkonstante, die definiert, aber im
  Modul (inklusive Docstring) nirgands gelesen wird, ist ein Befund — sie
  behauptet eine Sicherung, die es nicht gibt. Umgekehrt gilt dasselbe fuer
  eine **Erklaerung im Code, die der Code nicht einhaelt**: zwei
  uebereinanderliegende Kommentarbloecke, von denen der zweite den ersten
  widerlegt, sind ein Befund, weil die naechste Pflege dem oberen folgt.

## Verification

Ein Audit gilt als abgeschlossen, wenn **alle vier** true sind:

1. Jede beibehaltene Fundstelle hat einen **ausgefuehrten** Beleg, nicht
   gelesenen Code.
2. Jeder Widerruf ist **benannt** (Kandidat, Grund, Widerlegung) — im Bericht,
   nicht nur im Kopf.
3. Die Schnellpruefungen sind mit ihrer Zahl im Bericht belegt (Syntaxfehler,
   stille Ausnahmen, Differenz der Verdrahtungslisten).
4. Der Abschnitt „nicht geprueft" nennt die **Bereiche**, die kein Kind
   abgedeckt hat — zusammen mit der Liste der gescannten Bereiche.

Nach der Entscheidung fuer Umsetzung: jeder Befund mit Schwere und Fundstelle
als offener Punkt, und **erst dann** die Umsetzung — jede Aenderung einzeln
mit Test und Beleg, fremde Arbeit liegen gelassen und benannt.

Jede Reparatur bekommt eine **fallende Gegenprobe**: den Fix zuruecknehmen und
den neuen Test laufen lassen. Ein Test, der auch ohne den Fix gruen ist, prueft
nichts — das ist die Regel, mit der ein Audit sich selbst kontrolliert, bevor
es Fehler als behoben meldet. Zwei Fallen dabei, beide gemessen: der Anker
einer Ersetzung kann den **Kommentar** statt der Codezeile treffen (die
Gegenprobe bleibt dann faelschlich gruen), und ein Test, der eine
Handlungsdatei des Betriebs anfasst, braucht **zwei** Schranken (Schreibmodus
aus und Pfad umbiegen) — im `tearDown` erst loeschen, dann zuruecksetzen, sonst
loescht der Waechter die echte Datei.

Die Fehlerklassen dieser Pruefung als Muster zum Wiederverwenden:
`references/fehlerklassen-verdrahtung.md`.