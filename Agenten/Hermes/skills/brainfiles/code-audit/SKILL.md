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
| Stimmt ein Kandidat? | Aufrufer + Prosa im Modul | Befund oder Fehlalarm |
| Wirkt ein Fix ueberhaupt? | zwei Laeufe, ein Wert verschieden | siehe `messwerkzeug-gegenprobe` |

Die vier Schnellpruefungen als Kopiervorlage: `references/dispatch-briefs.md`.

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

### 7. Erwartete Fehlalarmklassen

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
- **Ein Befund, der die Grenze eines anderen Fachgebiets beruehrt, wird dort
  eingetragen und nicht hier erfunden** — die offene Liste des Hauses ist der
  Ort fuer das, was eine Entscheidung braucht.

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