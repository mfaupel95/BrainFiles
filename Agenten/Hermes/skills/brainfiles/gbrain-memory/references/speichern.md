# Schreiben: einen Fakt sicher ablegen

Alles hier ist an der Installation gemessen (gbrain 0.51.0.0, WSL `archlinux`,
`/workspace/gbrain`). Aufruf immer ueber das `terminal`-Werkzeug:

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain remember "$(cat <pfad>)" \
    --provenance "<quelle, datum>" --entity <entitaet>
```

## Optionen (aus `gbrain remember --help`, wortgetreu)

| Option | Bedeutung |
|---|---|
| `<fact>` | EINE Behauptung je Aufruf, Pflicht |
| `--provenance` | woher der Fakt kommt, **Pflicht**, max. 500 Zeichen, z. B. `"conversation 2026-06-12"`, `"user said in chat"` |
| `--entity` | Person/Firma/Projekt (Name oder Slug, serverseitig kanonisiert); fehlt sie, findet die entitaetsbezogene Erinnerung den Fakt nicht |
| `--kind` | `event` \| `preference` \| `commitment` \| `belief` \| `fact` (Vorgabe) |
| `--ttl` | Kurzform `"30d"`, `"12h"`, `"45m"` oder absoluter ISO-8601-Zeitpunkt; ISO-DAUERN wie `"P30D"` werden mit Korrekturhinweis abgelehnt |
| `--visibility` | `world` (Vorgabe, jeder verbundene Agent darf lesen) oder `private` (nur lokale CLI) |
| `--request-id` | eigene UUID; bei Zeitueberschreitung mit denselben Argumenten erneut senden, um das Ergebnis zu erfahren |
| `--force` / `--expected-revision` | nur fuer das Ueberschreiben einer Seite; schliessen sich aus |

**Antwort lesen:** nach `status` entscheiden (`inserted` | `duplicate` | `superseded`),
NIE nach `status_text` (nur Anzeige). Bei `duplicate` ist `id` die ID des BEREITS
vorhandenen Fakts.

## Die zwei gemessenen Verstuemmelungen

1. **Inline-Text wird von der Huelle zerlegt** (29.09.2026): einfache Anfuehrungszeichen
   schuetzen NICHT gegen Backticks, `$`-Ausdruecke und `$(...)` - sie werden ausgewertet,
   bevor gbrain den Text sieht. Vier Fakten landeten verstuemmelt im Gehirn
   (`must run as ,`, `/usr/bin/bash.ProcessId -ne `).
2. **Auch im Dateiweg wird `$NAME` im Inhalt expandiert** (01.10.2026): der Text kam
   unversehrt durch die eigene Shell, aber `$HERMES_HOME` wurde auf dem Weg zur
   Installation zu LEER (im Fakt stand danach `jedes cd "/../.."`).

Regeln daraus: Langtext mit `write_file` in eine Datei legen, im Faktentext **kein `$`**
verwenden (Ersatzschreibweise `<HERMES_HOME>` und im Text erklaeren), und der `cat`-Pfad
muss in der Form der AUFRUFENDEN Shell liegen - aus dem Windows-Terminal `/c/Users/...`
(MSYS), nicht `/mnt/c/Users/...` (WSL). Ein WSL-Pfad im `cat` gibt `No such file or
directory`, und gbrain meldet dann nur `invalid_params: fact must be a non-empty string`.

## Nach dem Schreiben

1. `recall --grep <stichwort>` und den zurueckgelesenen Text **gegen die Vorlage**
   vergleichen (zeichengenau), nicht nur "gefunden" zaehlen - die Verstuemmelung oben
   fiel erst beim Zeichenvergleich auf.
2. Bei Verlust: `forget <id> --reason "<was fehlte>"`, Datei korrigieren, neu `remember`.
3. gbrain meldet beim Schreiben keinen Inhaltsverlust, nur `remembered as fact #n`.

## Stoerung, die keine ist

`The local persistence owner is unavailable. Fix: Restart the persistence owner, then
retry.` (01.10.2026): der Schreibweg geht per IPC an einen residenten Owner; gebunden
wird der Socket nur von einem laufenden `gbrain serve`. Die Ursache ist nicht
abschliessend geklaert - die Probe zeigt aber, dass **ein zweiter Aufruf Sekunden spaeter
durchging**. Also wiederholen statt an Locks drehen; `recall` funktioniert in derselben
Lage (nur lesend).

## Nachweis der Einrichtung (20.09.2026, gueltig)

- Init-Modus: schluessellose Faktenspeicherung (`--pglite --no-embedding`), Suchmodus
  `conservative` (automatisch: kein Schluessel fuer Expansion).
- Round Trip belegt: Fakt #1 `"My setup test phrase is amber-orbit-f0c2c7"`,
  Provenance `"explicit setup test, 2026-09-20"`, Entitaet `projects/gbrain-setup`,
  von einem SEPARATEN Prozess mit dem exakten Wortlaut erinnert.
- Frische Sitzung VERIFIZIERT: eine neue Unterhaltung erinnerte den Satz ueber diesen
  Skill und den WSL-Launcher, ohne ihn zu kennen.
- Empfangsbestaetigung: `/workspace/gbrain/.gbrain/agent-install/receipt.json`
  (Zustand `ready`).
