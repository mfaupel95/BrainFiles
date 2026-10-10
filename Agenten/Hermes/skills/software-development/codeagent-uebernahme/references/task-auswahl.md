# Sammelauftrag: welche Tasks sind ohne Entscheidung abgebbar?

Auftrag wie "alle tasks die keine entscheidung brauchen" / "alle ausfuehrbaren
ohene Entscheidung" ist ein Sammelauftrag: erst die Auswahl treffen, dann
Brief(e) schreiben. Die Auswahl ist eine eigene Prozedur - die bloesse
Aufzaehlung der Titel ist keine Grundlage fuer einen Brief.

## 1. Block-Parsing statt Zeilen-Lesen

TASKS.md ist gross (tausende Zeilen). Offene Tasks per Regex erkennen und je
Task den BLOCK bis zur naechsten Task-Zeile oder `## `-Ueberschrift sammeln:

```python
import re
lines = open(path, encoding="utf-8").read().splitlines()
task_re = re.compile(r'^\s*- \[(\s|x)\] \*\*(T-\d+)')
# Block = Zeilen[start:end], end = naechste Task-Zeile mit ANDERER id oder '## '
```

ACHTUNG: Alleinige Titel sind unzureichend - viele Titel klingen ausfuehrbar,
der Block sagt das Gegenteil ("Naechster Schritt: Entscheidung Max").

## 2. Klassifikation an den "Naechster Schritt"-Zeilen

Fehlerklasse 1: Ein regex-Signal auf den GANZEN Block markiert zu viele Tasks
als entscheidungsbeduerftig (das Wort "Entscheidung" steht auch in
Kontextvermerken ueber FRUEHERE Entscheidungen). Fehlerklasse 2: ein
Keyword-Test ohne Block-Kontext stuft "wartet auf Max"-Tasks als ausfuehrbar
ein.

Verlaesslich ist der Blick auf die zusammengehoerenden Zeilen je Block:
`Naechster Schritt:` / `Wartet auf:` / `ENTSCHEIDUNG` / `Betrifft:` und die
vorausgehenden 1-2 Zeilen. Abgebbar (in einen Brief) ist ein Task nur, wenn:

- der naechste Schritt ein KONKRETER Codeweg ist ("baue X nach Muster Y",
  "ergaenze die Vorpruefung in f()") und
- KEIN Entscheidungsbedarf besteht (Max, Geld, Hardware, externes Konto,
  Freigabekette, Portal) und
- KEIN Warten auf ein Ereignis ("beobachten", "nach dem naechsten
  Verschwinden", "Papierrunden abwarten", "erst ab N Runden") - solche
  Tasks gehren in keine Tranche.

Nicht in den Brief: Tasks, deren naechster Schritt mit "entscheiden",
"Max sagt", "Freigabekette oeffnen (nur Max)", "Guthaben bereitstellen"
beginnt. Ebenfalls nicht: Diagnose-/Messauftraege, die der Agent ohne
Zugriff nicht abschliessen kann (Docker-Status, Kontostand). Die Diagnose-
/Mess-/Doku-Tasks koennen in eine EIGENE Folgetranche oder haendisch -
nicht in den Codeagenten-Brief.

## 3. Abhaengigkeiten pruefen, bevor der Task in den Brief kommt

Mehrere Bloecke haben Voraussetzungen, die erst nachgeprueft werden muessen
(sonst verlangt der Brief etwas, das der Agent nicht vorfindet):

- "WARTEN, bis die Sitzung X committet hat": `git status --porcelain <pfad>`
  leer UND `git log -1 -- <pfad>` zeigt einen Commit - erst dann ist die
  Datei eine Basis.
- "nach Stufe-X-Merge": `git log --oneline -- <ordner>` bzw. Existenz der
  genannten Dateien pruefen.
- "es fehlt Datei D": `os.path.exists` - fehlt sie, ist der Task NICHT
  abgebbar (er verlangt einen Download/Extern, kein Codeweg).
- **Task schon erledigt, aber nicht abgehakt**: ein offener Task kann
  bereits umgesetzt sein, waehrend das `[ ]` in TASKS.md stehen blieb
  (gemessen 07.10.2026: T-345 war mit Commit cd57661e fertig, der Block
  war nicht abgehakt). Vor der Beauftragung je Kandidat
  `git log -1 --format="%h %ci %s" -- <betroffene Datei>` pruefen - ist
  der naechste Schritt schon im Commit, den Task als erledigt markieren
  statt ihn in den Brief zu geben.

## 4. Tranchengrenze ziehen

Ein opencode-Lauf klappt mit ~6 abgegrenzten Tasks pro Brief; 15+ Tasks in
EINEM Brief verwirft der Agent (Kontextgrenze, Abgabe wird unpruefbar).
Gruppieren nach Baum (Werkzeug/GUI/Infra vs. Handel-Code vs. Doku) und je
Gruppe einen eigenen Brief. Tasks, die Live-Orderweg-Dateien anfassen
(wachen.json, handeln.py scharfer Spuren, trailing.py), muessen in einen
eigenen Brief MIT ausdruecklicher Warnung oder besser haendisch bleiben -
die Spur-Skripte starten je Zyklus neu, ein halbfertiger Eingriff bricht
den LIVE-Zyklus.

## 5. Zustand fuer Max festhalten

Nach der Klassifikation dem Nutzer die drei Gruppen nennen (abgebbare
Tasks, Entscheidung noetig, wartet auf Ereignis), damit erkennbar ist,
was NIE an den Agenten geht und warum. Das verhindert, dass ein Task mit
versteckter Entscheidung im Brief landet und der Lauf mit einer Rueckfrage
abstuerzt.
