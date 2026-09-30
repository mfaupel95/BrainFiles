---
name: hermes-gedaechtnis-pflegen
description: "Use when Hermes-Gedaechtnis gepflegt oder gerettet wird."
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Gedaechtnis, MEMORY.md, USER.md, pending, Vorschlaege, Verluste, BrainFiles]
---

# Das Gedaechtnis von Hermes pflegen

Das Hauptgedaechtnis ist ein Paar Textdateien, das in JEDEN Turn geladen wird. Es ist
kein Log und kein Beleg: es traegt Systemfakten und Nutzerpraeferenzen. Dieser Skill ist
das Vorgehen beim Aufraeumen, Nachziehen und Retten.

## When to Use

- `/memory approve` wurde ausgefuehrt oder soll ausgefuehrt werden
- "Gedaechtnis aufraeumen", "Vorschlaege nachziehen", "was steht im Gedaechtnis"
- ein Eintrag fehlt, ein Werkzeug meldet einen Verlust, oder eine Memory-Notiz ist als
  falsch aufgefallen (dann gehoert sie hier korrigiert, nicht nur im Wiki)
- am Ende einer Aufgabe, wenn eine Notiz durch eine Messung widerlegt wurde

## Landkarte

| Was | Wo |
|---|---|
| Hauptgedaechtnis | `Agenten/Hermes/memories/MEMORY.md` |
| Nutzerprofil | `Agenten/Hermes/memories/USER.md` |
| Vorschlaege aus `background_review` | `Agenten/Hermes/pending/memory/*.json` |
| Sonde: greift das Tor? | `Agenten/Hermes/scripts/probe-memory-pinning.py` (mit dem hermes-agent-venv-Python) |
| Verlust-Suche / Rettung | `Agenten/Hermes/scripts/memory-verlust.py` (`--alles`, `--retten`, `--json`) |
| Wache | `Agenten/Hermes/scripts/memory-verlust-wache.py` (Cron, leere Ausgabe = nichts senden) |
| Archiv aller Ersetzungen | `state.db`, Tabelle `messages`, `tool_name='memory'` |
| Ausgeschriebene Lehre | `MaxHirn/Wiki/Lektionen/Memory-Verluste.md` |

**Beide Dateien sind NICHT versioniert** (`.gitignore` sperrt `Agenten/Hermes/**`): es gibt
KEINEN Git-Rueckweg. Vor jedem groesseren Eingriff eine Kopie daneben legen, und das
Loeschen einer Vorschlagsdatei ist endgueltig - deshalb der Digest (Ablauf 5).

## Kernregel: was `approve` wirklich tut

`/memory approve` ist weder ein stiller Blindgaenger noch ein "Freigeben" - es ist eine Kette
mit einem Tor, und das Tor hat eine Bedingung:

- Beim EINLAGERN haengt `tools/memory_tool.py` an jede `replace`/`remove`-Operation die volle
  getroffene Eintragung als `matched_entry`. Genehmigt wird genau DIESE Eintragung - der Anker
  wird beim Genehmigen gar nicht mehr gesucht.
- Beim GENEHMIGEN verweigert `apply_memory_pending` jede destructive Operation OHNE Pin:
  "This destructive pending write predates entry pinning and cannot be verified; nothing was
  applied. Reject it and recreate the change."
- Ein Vorschlag von VOR dem Pin (Feld fehlt) ist damit nicht "verfallen", sondern **nicht
  genehmigungsfaehig**. `/memory pending` nennt ihn "unpinned legacy target - reject and
  recreate before approving", `approve` listet ihn unter `Failed:` - es MELDET also, und wer
  die Ausgabe liest, sieht es.
- Ein FRISCHER Vorschlag (mit Pin) ist genehmigungsfaehig; die Queue ist kein Sondermuell.
- Ein **Batch** wird als GANZES verweigert: enthaelt er eine ungepinnte `replace`, geht auch
  sein reines `add` verloren. Das ist die eigentliche Luecke der Queue.

Warum die Queue trotzdem von Hand nachgezogen wird: ein tagealter Vorschlag beschreibt seinen
Gegenstand nicht mehr zuverlaessig (Pfade umgezogen, Schalter laengst umgestellt), und ein `add`
in einem verweigerten Batch kommt nie an. Ein Vorschlag ist eine Momentaufnahme, kein wartender
Auftrag - das Brauchbare von Hand nachziehen, den Rest loeschen.

## Ablauf

1. **Queue einlesen - sie hat zwei Formen.** Jede Datei traegt `payload`; entweder mit
   `payload.operations` (Batch, meist 1-3 Operationen) ODER `payload` ist selbst die
   Operation (`action`/`target`/`content`/`old_text`). Beide Faelle abdecken, sonst
   zaehlt man eine Queue als leer.
2. **Kandidaten billig vorfiltern.** Stichwoerter jeder `content` gegen den heutigen Text
   halten (Anteil der Woerter > 4 Zeichen, die schon vorkommen) und aufsteigend sortieren:
   die niedrigsten Anteile sind die Kandidaten fuer "fehlt wirklich". Das ist eine
   VORAUSWAHL, kein Urteil - der Anteil ist bei umgeschriebenen Eintraegen hoch, obwohl
   die Aussage fehlt.
3. **Jeden Kandidaten gegen die WIRKLICHKEIT pruefen, nicht gegen den Vorschlag.** Die
   genannte Datei, das Skript, den Code lesen. Ein Vorschlag kann FALSCH sein, nicht nur
   veraltet - typische Formen:
   - er nennt Pfade oder Ziele, die inzwischen umgezogen sind (Kopieziele, Pruefpfade);
   - das Gedaechtnis behauptet "OFFEN (Entscheidung Max)", waehrend der Code die Sache
     laengst umsetzt - dann ist die NOTIZ zu korrigieren, nicht der Vorschlag zu uebernehmen;
   - ein frueher gemeldeter Fehlalarm ist inzwischen behoben, der Vorschlag behauptet ihn
     weiter.
   Was sich als falsch erweist, wird im Ergebnis benannt (es ist der nuetzlichste Teil der
   Arbeit), aber nicht ins Gedaechtnis geschrieben.
4. **Nur was fehlt UND stimmt, von Hand schreiben** - per `memory`-Werkzeug als EIN Batch.
   `MEMORY.md` = Systemfakten, `USER.md` = wer Max ist und wie er Antworten will. Ein
   Arbeitsprotokoll (Commit-Hash, Testzahl, "noch als Subagent unterwegs") ist KEIN
   Gedaechtnisinhalt und wird verworfen, auch wenn es fehlt. Beim Schreiben Zeichenzahl
   vorher/nachher vergleichen und die Wirkung greppen (`grep -c '<Stichwort>' <datei>`) -
   die Erfolgsmeldung des Werkzeugs allein ist kein Beleg.
5. **Verworfenes als Digest ablegen, dann loeschen.** Alle Operationen im Volltext nach
   `Agenten/Hermes/.sicherung/memory-queue-verworfen-<datum>.md`, erst danach die JSONs
   entfernen. Ohne den Digest ist ein geloeschter Vorschlag unwiederbringlich.
6. **Nachziehen und committen:** die Lehre in `Wiki/Lektionen/Memory-Verluste.md`
   ergaenzen (Befund + die widerlegten Vorschlaege), die offenen Entscheidungen und die
   NICHT angefassten Punkte als Task in `Archiv/TASKS.md` (Skill `aufgabenliste-pflegen`),
   dann die eigenen Pfade committen und pushen.

## Fallen

- **`old_text` ist der eigene ANFANG des Eintrags, nie eine Schlusszeile.** Ein `replace`
  ersetzt den GANZEN Eintrag, den der Anker trifft - ein Anker, der als Teilstring in einem
  anderen Eintrag steht, loescht diesen. Nach JEDEM `replace`/`remove` das Feld
  `replaced_entries`/`removed_entries` lesen: dort steht im Volltext, welcher Eintrag
  getroffen wurde. Es ist die einzige Kontrolle.
- **Ein Verlust ist erst ein Verlust, wenn Text UND Anfang fehlen.** `memory-verlust.py`
  vergleicht die ersten ~70 Zeichen; ein umgeschriebener Eintrag ist der Normalfall, kein
  Verlust. Erst bei beiden Fehlanzeigen suchen - und der Rueckweg steht in `state.db`
  (das Ergebnis-JSON jedes Schreibvorgangs traegt den vollen alten Text).
- **Den Vorschlag nie als Beleg fuer den Zustand nehmen.** Die Queue ist ein Vorschlag aus
  dem Hintergrund; die Wahrheit steht im Code, in der Datei oder im Journal. Ein Vorschlag
  mit "stimmt noch" ist eine Behauptung, bis die Stelle gelesen wurde.
- **Zeichenbudget im Blick halten.** Das Gedaechtnis wird in JEDEN Turn geladen; beim
  Nachziehen zuerst zusammenfassen und ersetzen statt anhaengen, sonst waechst die
  Dauerlast. Die Ausgabe des Werkzeugs nennt Prozent und Grenze.
- **Eine Sonde baut denselben Store wie das Tor.** `MemoryStore()` ohne Argumente traegt die
  CODE-Vorgaben (2200/1375 Zeichen), waehrend `config.yaml` 750000/237500 setzt - die Sonde
  meldet dann "MEMORY.md exceeds its char limit on load ... further additions are blocked" und
  man haelt ein gesundes Gedaechtnis fuer gesperrt. Immer
  `from tools.memory_tool import load_on_disk_store` nehmen (genau der Store, den
  `/memory approve` baut) und die Sonde mit dem hermes-agent-venv-Python starten.
- **Zugangsdaten nie ausgeben.** Beim Pruefen nur die EXISTENZ und die Laenge messen,
  niemals den Wert protokollieren - `Wissen/Zugaenge.md` bleibt Stufe 0.

## Nachweis

- `grep -c '<Stichwort>' memories/MEMORY.md` (bzw. `USER.md`) fuer jeden nachgezogenen
  Eintrag - die Wirkung, nicht die Erfolgsmeldung.
- `python Agenten/Hermes/scripts/memory-verlust.py` meldet KEINEN neuen Verlust nach dem
  eigenen Schreiben (der eigene `replace` darf dort nicht auftauchen).
- `pending/memory/` ist leer und der Digest liegt unter `Agenten/Hermes/.sicherung/`.
- Die Verweigerung ist belegbar statt behauptet: `Agenten/Hermes/scripts/probe-memory-pinning.py`
  laesst beide alten Formen (einzelnes `replace`, Batch mit `replace`) durch das ECHTE Tor laufen -
  erwartet `success: false` samt Meldung, und MEMORY.md danach byte-gleich (Groesse UND mtime).
