---
name: memory-verlust-rettung
description: Findet verlorene Memory-Eintraege und holt sie zurueck.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Memory, Recovery, Hermes, Datenbank]
---

# Memory-Verluste finden und zurueckholen

Stellt fest, welche Eintraege aus dem Hermes-Gedaechtnis (`Agenten/Hermes/memories/MEMORY.md`)
verschwunden sind, und holt sie im Volltext zurueck. Die Quelle ist `state.db`: das
Ergebnis-JSON jedes `replace`/`remove`-Aufrufs traegt unter `replaced_entries` bzw.
`removed_entries` den VOLLEN Text des getroffenen Eintrags. Nur stdlib (sqlite3, json),
alles lesend - das Werkzeug schreibt nie in die Datenbank.

Es heilt keine beschaedigte Datei und bewertet nicht, ob ein alter Eintrag heute noch
stimmt: gefundener Text wird vor dem Zurueckholen gegen die Wirklichkeit geprueft.

## When to Use

- "Im Gedaechtnis fehlt ein Eintrag, der doch bestaetigt wurde."
- Ein `replace` hat den falschen Eintrag getroffen (`replaced_entries` nennt einen anderen).
- "Was stand frueher im Memory?" / "Search for missing memory content in archived and running sessions."
- Nach `/memory approve all` oder einer Aufraeumaktion: kam wirklich etwas an?
- Ein Bot-Profil ("Insel") hat Wissen, das im Hauptgedaechtnis fehlt.

## Prerequisites

- Arbeitsverzeichnis ist die BrainFiles-Wurzel: aus einer Hermes-Sitzung erst
  `cd "$HERMES_HOME/../.."`, sonst schlagen alle relativen Pfade fehl.
- `Agenten/Hermes/state.db` (kann >500 MB sein) - immer `mode=ro` oeffnen.
- Kein Zugang noetig: `memories/MEMORY.md` ist per .gitignore gesperrt, es gibt also
  KEINE Git-Historie des Gedaechtnisses. state.db ist das einzige Archiv.

## How to Run

Alles ueber das `terminal`-Werkzeug, aus der BrainFiles-Wurzel:

```
python Agenten/Hermes/scripts/memory-verlust.py            # belegte Verluste
python Agenten/Hermes/scripts/memory-verlust.py --alles    # mit Volltext
python Agenten/Hermes/scripts/memory-verlust.py --retten D.md
python Agenten/Hermes/scripts/memory-verlust-wache.py      # leise = nichts Neues
```

Der Fund gehoert zurueck ins Gedaechtnis ueber das `memory`-Werkzeug (nicht per
`write_file` in MEMORY.md - die Datei gehoert dem Werkzeug).

## Quick Reference

| Zweck | Aufruf |
|---|---|
| Belegte Verluste listen | `python Agenten/Hermes/scripts/memory-verlust.py` |
| Volltexte sichern | `... --retten Agenten/Hermes/cache/memory-verluste.md` |
| Memory-Aufrufe roh | `select timestamp,session_id,content from messages where tool_name='memory'` |
| Schnappschuesse (Backups + Anfrage-Dumps) | `python Agenten/Hermes/skills/brainfiles/memory-verlust-rettung/scripts/memory-quellen.py schnappschuesse` |
| Profil-Inseln vergleichen | `python Agenten/Hermes/skills/brainfiles/memory-verlust-rettung/scripts/memory-quellen.py inseln` |
| Pending-Queue | `Agenten/Hermes/pending/memory/*.json` |
| Zustand der Wache | `Agenten/Hermes/cache/memory-verlust-wache.json` |

## Procedure

1. **Verluste belegen.** `python Agenten/Hermes/scripts/memory-verlust.py --alles`. Als
   Verlust gilt: Text steht heute nicht mehr in MEMORY.md, sein Anfang (70 Zeichen) auch
   nicht und seine Kopf-Signatur (erste drei Wortzeichen) auch nicht - sonst wurde der
   Eintrag nur umgeschrieben.
2. **Ursache lesen.** Die `memory`-Aufrufe um den Verlustzeitpunkt aus state.db holen
   (`select timestamp, session_id, content from messages where tool_name='memory' and
   content like '%_entries%'`): `replaced_entries` nennt im Volltext, WELCHER Eintrag
   getroffen wurde, `removed_entries` den absichtlich entfernten. Ein `remove`
   19 Sekunden nach dem `add` ist eine Entscheidung, kein Unfall - nicht zurueckholen.
3. **Aeltere Staende pruefen** (optional): `memory-quellen.py schnappschuesse` zieht   MEMORY.md aus `Agenten/Hermes/backups/*.zip` und den Memory-Block aus
   `Agenten/Hermes/sessions/request_dump_*.json` (er liegt in `request.body.system`, der
   `USER PROFILE`-Block gehoert NICHT dazu). Profil-Inseln: `memory-quellen.py inseln`.
4. **Inhalt gegen die Wirklichkeit pruefen**, bevor er zurueckgeht: jede Zahl, jeder Pfad,
   jeder Schalter aus dem alten Text wird heute nachgemessen (`read_file`, `search_files`,
   `terminal`). Ein Eintrag, der eine Laenge oder einen Wert nennt, wird mit dem heutigen
   Wert geschrieben, mit Vermerk.
5. **Zurueckholen** mit dem `memory`-Werkzeug: `add` mit dem geprueften Text, im ersten Satz
   der Vermerk "am TT.MM.JJJJ aus state.db wiederhergestellt". Nie `write_file` auf MEMORY.md.
6. **Wache pruefen/setzen:** Hermes-Cron `memory-verlust-wache` (no_agent, taeglich,
   Telegram, leere Ausgabe = nichts senden) laeuft ueber `memory-verlust-wache.py`.
   Nach einem Reparaturlauf die Merkdatei neu setzen: `--neu-baseline`.
7. **Befund dauerhaft ablegen:** Wiki-Seite `MaxHirn/Wiki/Lektionen/Memory-Verluste.md`
   ergaenzen, offene Punkte als Task in `MaxHirn/Archiv/TASKS.md`.
8. **Beweisen:** Werkzeug erneut laufen lassen - die Zahl der Verluste muss sinken; Tests
   `python -m unittest test_memory_verlust test_memory_verlust_wache` im scripts-Ordner.

## Pitfalls

- **`old_text` ist eine Teilstring-Suche.** Ein Anker, der als Schlusszeile in einem ANDEREN
  Eintrag steht, loescht diesen Eintrag komplett (so verschwand `HERMES-CONFIG 30.09.2026`,
  1117 Zeichen, durch ein `replace` mit dem Anker `` `terminal.backend: local` = Standard. ``).
  Anker ist immer der eigene, unverwechselbare ANFANG des Eintrags.
- **`replaced_entries`/`removed_entries` im Ergebnis lesen** - es ist die einzige Kontrolle,
  WELCHER Eintrag getroffen wurde. Das Feld `success: true` sagt nichts darueber.
- **`/memory approve all` gibt nichts frei, wenn die Anker alt sind.** Die Pending-Queue
  (`pending/memory/`, Vorschlaege aus `background_review`) verfaellt mit ihrem Anker:
  MEMORY.md wurde neu geschrieben, kein Inhalt aus der Queue stand danach im Gedaechtnis.
  Vorschlaege inhaltlich nachziehen oder loeschen, nicht "freigeben".
- **MEMORY.md ist gitgesperrt** (`Agenten/Hermes/**`): keine Historie, kein `git checkout`.
- **Kein `date` aus der Sandbox** fuer Datumsangaben in Notizen/Commits - die Container-Uhr
  kann Stunden zurueckliegen; Datum vom Host oder aus `git log -1 --format=%ci`.
- **`memories/`-Schnappschuesse aus dem Backup-Zip** liegen je Profil mehrfach vor
  (`profiles/<bot>/memories/MEMORY.md`) - beim Auspacken den Profilpfad in den Dateinamen
  aufnehmen, sonst ueberschreiben sich die Kopien.
- **Profil-Inseln sind getrennte Gedaechtnisse:** Bots lesen nur ihr eigenes `MEMORY.md`.
  Inhalt von dort ist ein Fund, aber vor dem Uebernehmen pruefen (oft alte Fassungen).
- **Frisch per `write_file` geschriebene Skripte** verschwinden gelegentlich binnen Minuten
  (T-100) - nach dem Schreiben sofort `git add`/Commit, sonst faellt der Verlust erst beim
  Commit auf.

## Verification

```
python Agenten/Hermes/scripts/memory-verlust.py
```

Erwartet: die Zahl "davon heute NICHT mehr im Gedaechtnis" ist kleiner als vor der Rettung,
und der wiederhergestellte Eintrag erscheint nicht mehr in der Liste. Gegenprobe: seinen Kopf
mit `search_files` in `Agenten/Hermes/memories/MEMORY.md` suchen.
