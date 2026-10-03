# Erinnern und Korrigieren

## recall: erst Entitaet, dann Text

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall --grep <einzelwort>
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall "projects/hermes-agent"
```

- **`recall <wort>` sucht ZUERST eine ENTITAET.** Ist der Begriff keine, meldet es
  `no facts for entity '<wort>'; matched N fact(s) by text` und listet sie darunter - die
  Fundstelle ist da, nur die Einleitung irrefuehrend. Textsuche erzwingen: `--grep`.
- **`--grep` mit EINEM praegnanten Stichwort, nicht mit einer Phrase** (gemessen
  30.09.2026): `--grep "lauschte wieder auf TCP"` meldete `No matching facts.`, waehrend
  `--grep 9900` denselben Fakt sofort fand. Die Suche greift wortweise. Bei "nicht
  gefunden" also erst mit dem auffaelligsten Einzelwort (Zahl, Name, Pfad) gegentreten.
- Ausgabeform je Fakt: `id=<n> [<entitaet>] <text> (fact, conf <wert>)`.
- `recall --help` und `forget --help` geben nur `gbrain recall - run gbrain --help for the
  full command list.` aus - kein Fehler, die Optionen stehen im Haupt-Hilfetext.

## search und query sind etwas anderes

- **`search`/`query` finden KEINE Fakten** - sie gehen ueber Seiten.
- Ohne Embedding-Anbieter laufen sie degradiert (nur Stichwortsuche) und sagen das
  selbst; `query`/`ask` brauchen zusaetzlich Expansion, die ohne Schluessel fehlt.

## forget: zuruecknehmen, nicht loeschen

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain forget <fact-id> --reason "<text>"
```

- Die ID ist **positionell**; `--id` gibt es nicht.
- Korrektur heisst immer `forget` + neues `remember` - es gibt kein Update.
- Vergessen nimmt nur die AKTIVE Erinnerung zurueck; Historie, Quellmaterial und private
  Sicherungen koennen bleiben. **Nie physische Loeschung zusagen.**
- Danach frisch erinnern und den Wegfall zeigen (Gegenprobe).

## Regeln aus der Installationsanweisung

Quelle: `/workspace/gbrain/instructions/gbrain-skill.md` (im WSL lesbar mit
`wsl.exe -d archlinux -- cat <pfad>`):

- Unsicherheit erhalten und unterscheiden, was der Nutzer GESAGT hat und was eine
  Ableitung ist.
- Veraltetes auf Zuruf korrigieren oder vergessen und die Aenderung mit einem frischen
  `recall` belegen.
- **Nie** Historie verbundener Dienste importieren und **nie** automatische Erfassung
  einschalten, ohne dass Max es verlangt.
- Die Identitaet des Agenten nicht ersetzen - dies ist EINE gemeinsame lokale
  Installation, keine Grenze zwischen Bots.
- Speicheraufrufe sind endliche CLI-Prozesse: eine belegte Datenbank heisst, dass ein
  anderer Befehl laeuft - danach wiederholen, **niemals** seine Sperre entfernen.

## Welche Quelle gilt

GBrain speichert Aussagen, das Wiki (`MaxHirn/Wiki`) die Lehren, Hermes-`memory` die
Regeln jeder Sitzung und `MaxHirn/Archiv/TASKS.md` die offenen Aufgaben. Bei
Widerspruch gewinnt die Quelle, die den Beleg traegt (Commit, Log, Messung) - und der
Widerspruch gehoert als Korrektur in GBrain, nicht als stiller Zweiteintrag.
