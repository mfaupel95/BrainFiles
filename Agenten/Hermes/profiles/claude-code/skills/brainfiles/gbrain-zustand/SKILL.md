---
name: gbrain-zustand
description: "GBrain (WSL) prüfen: Fakten zählen, Doctor deuten."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [gbrain, memory, fakten, wsl, diagnose]
    related_skills: [hermes-maintenance, windows-host-zugriff, hermes-config-ops]
---

# GBrain prüfen: Fakten zählen, Doctor deuten

GBrain ist das lokale Wissensgehirn in der WSL2-Distribution `archlinux`
(`/workspace/gbrain`). Dieser Skill beantwortet die Frage **„ist das Gehirn in
Ordnung?"** — und verhindert die zwei Fehlurteile, die dabei Daten kosten:
„0 Seiten, also alles weg" und „der Doctor empfiehlt X, also X tun".

Das Speichern und Erinnern selbst (Fakten anlegen, korrigieren, welche Quelle
gilt) gehoert in den Skill `gbrain-memory` der Hauptbibliothek. Hier steht die
**Zustandspruefung**.

## Wann (When to Use)

- "laeuft gbrain noch", "ist das Gehirn in Ordnung", "gbrain stats", "gbrain doctor"
- die Doctor-Ausgabe nennt `reinit`, `init`, einen Dimensions-Konflikt oder einen
  "never synced"-Befund → **vor jedem Handeln hier weiterlesen**
- ein `recall` findet nichts und die Frage ist, ob die Fakten weg sind
- die taegliche GBrain-Wache hat gemeldet

**Don't use for:** einen Fakt speichern oder korrigieren (`gbrain-memory`),
Hermes' eigenes Gedaechtnis (`hermes-gedaechtnis-pflegen`), die
Hermes-Installation selbst (`hermes-maintenance`).

## 1. Der eine Befehl, der den Bestand zeigt

    wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall

`recall` **ohne Argument** listet die aktiven Fakten (`id=<n> [<entitaet>] <text>`).
Das ist die Zahl, die zaehlt. Immer ueber den **absoluten Launcher** — ein `gbrain`
aus dem PATH ist eine andere Installation; der Launcher loescht ausserdem vererbte
Provider-/API-Key-Variablen, damit kein exportierter Schluessel die Installation
umlenkt.

## 2. Die Falle: `stats` und `list` zaehlen SEITEN, nicht Fakten

**`gbrain stats` meldet `Pages: 0` und `gbrain list` sagt `No pages found`,
waehrend alle Fakten da sind.** Beide gehen ueber die Seiten-Ebene; ein ueber die
Memory-Verben gefuelltes Gehirn hat dort nichts. Ebenso ist `search`/`query`
seitenbasiert und findet Fakten grundsaetzlich nicht — auch nicht, wenn sie
existieren.

Regel: **Der Faktenbestand kommt aus `recall`. Ein 0 in `stats`/`list` ist kein
Datenverlust und kein Anlass fuer irgendeinen Reparaturbefehl.** Wer die Zahl
braucht: `recall` auszaehlen, nicht `stats` lesen.

## 3. Der Doctor empfiehlt Zerstoerendes — nie ungeprueft folgen

`gbrain doctor` meldet bei einem Breiten-Konflikt (Konfiguration nennt eine
andere `embedding_dimensions` als die Spalte `content_chunks.embedding` breit
ist) als Loesung `gbrain reinit-pglite --embedding-model … --embedding-dimensions …`
und sagt selbst: *"Wipe-and-reinit is the only path"*. **Dieser Befehl loescht das
Gehirn** — PGLite kann eine Vektor-Spalte nicht umbauen, also faellt alles weg.

Vor JEDEM `init`/`reinit`/`migrate`:

1. Fakten zaehlen (`recall`, Schritt 1) und die Zahl nennen.
2. Ist sie > 0: **nicht ausfuehren.** Die Dimension ist bei abgeschaltetem
   Embedding wirkungslos — ein Schoenheitsfehler, kein Defekt.
3. Ein `stats: 0` ist **kein** Argument dafuer (siehe Schritt 2).

**Ebenso:** ein "Source has never been synced" im Doctor ist normal, wenn das
Gehirn ueber die Verben gefuellt wird und die Seiten-Ebene leer bleibt. `sync`
holt die Git-Quelle — es repariert keine fehlenden Fakten.

## 4. Abgeschaltete Embeddings sind ein gueltiger Betrieb

`embedding_disabled: true` (kein Embedding-Anbieter) heisst nicht kaputt:
`remember`/`recall` arbeiten stichwortbasiert und finden zuverlaessig;
`search`/`query`/`ask` laufen degradiert (nur Stichwortsuche, ohne Expansion) und
**sagen das selbst** (`degraded: embed_unavailable, keyword_zero`). Ein "No
results" dort ist kein Befund. Fuer Fakten immer `recall --grep <wort>` nehmen.

## 5. Der Doctor richtig lesen

- `doctor --fast --json` **ueberspringt die DB-Pruefungen** (`connection: Skipping
  DB checks`). Wenn der Datenbankzustand die Frage ist, den vollen `doctor` fahren.
- Normal auf einer reinen CLI-Installation, **kein Fehler**:
  `retrieval_reflex_health` ("serve IPC socket not present" — den Socket bindet nur
  ein laufendes `serve`), `self_upgrade_health` (mode=notify), die
  "disabled (opt-in)"-Zeilen.
- Urteil an `status` und den Checks auf `error`/`fail` festmachen, nicht an der
  Zahl der Warnungen.

## 6. Schreibproben wieder zuruecknehmen

Wer den Schreibweg belegt, hinterlaesst sonst einen Fakt. Pflicht:

    gbrain forget <id> --reason "<zweck der probe, kein fakt>"
    gbrain recall --grep <stichwort>      # Gegenprobe: no matching facts

Die ID ist **positionell**; `--id` gibt es nicht. `recall --help` und
`forget --help` geben nur einen Zeiger auf die Haupt-Hilfe aus — kein Fehler.

## 7. Die Wache schweigt bei Warnungen (und initialisiert nie)

`Agenten/Hermes/scripts/gbrain-maintenance-wache.py` laeuft als Hermes-Cron
(`no_agent`, taeglich) und fahrt nur `doctor --fast --json`; **leere Ausgabe heisst
gesund**. Sie ruft nie `init`/`reinit`/`serve` — eine Doctor-Warnung kann also
nichts loeschen. Dieses Muster beim Erweitern beibehalten: melden, nie
reparieren.

## Fallen

- **`recall <wort>` sucht ZUERST eine ENTITAET.** Ist der Begriff keine, meldet es
  `no facts for entity '<wort>'; matched N fact(s) by text` und listet sie darunter.
  Die Einleitung irrefuehrt, die Treffer sind da. Textsuche erzwingen: `--grep`.
- **`--grep` will EIN praegnantes Wort** (Zahl, Name, Pfad), keine Phrase — die
  Suche greift wortweise. Bei "nicht gefunden" erst mit dem auffaelligsten
  Einzelwort gegentreten.
- **Ein zweiter Bot ist keine zweite Installation.** Es gibt EIN gemeinsames
  lokales Gehirn; die Fakten eines Bots sind die aller. `GBRAIN_BRAIN_ID` aus dem
  Launcher ist der Anker, nicht ein Pfad aus einer Notiz.
- **Bewegte Zahlen sind kein Verlust, solange `recall` sie zeigt.** Die PGLite-Ablage
  (`.gbrain/brain.pglite/`, Groesse und `pg_wal/`) aendert sich bei jeder Operation —
  daraus laesst sich nichts ablesen. Der Beleg ist `recall`.

## Nachweis

- `recall` nennt die Fakten und die hoechste ID; die Zahl wird im Bericht genannt.
- `doctor` mit `status` und den `error`/`fail`-Checks zitiert, nicht nur "ok".
- Eine gesetzte Schreibprobe ist per `forget` + `recall --grep` nachweislich weg.
- Bei einem Doctor-Befund mit Reparaturvorschlag: genannt, ob er Daten kostet, und
  ob er ausgefuehrt oder abgelehnt wurde — mit Grund.
