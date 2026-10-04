# auxiliary.compression: das 64k-Fenster, an dem Karten still sterben

## Das Symptom

Ein Hermes-Worker bricht mit **Exit 1** ab, der Dispatcher versucht es zweimal
und gibt auf: die Karte landet in `blocked` mit `gave_up`. Im Kartenstatus steht
nichts Brauchbares — der Grund steckt im Log:

```
Auxiliary compression model gemma-e4b-8k:cpu has a context window of 8,192
tokens, which is below the minimum 64,000 required by Hermes Agent.
```

**Erst das Log lesen, dann die Karte bewerten.** `kanban --board X show <id>`
endet bei `gave_up` mit einem abgeschnittenen ANSI-Brocken und `worker_output`
ohne Klartext. Klar kommt er hier:

```
kanban/<board>/logs/<id>.log     # Pfad: je Board ein eigener logs-Ordner
kanban --board X log <id>        # ebenfalls board-spezifisch
```

## Die Ursache

`auxiliary.compression` ist **nirgends gesetzt**. Hermes faellt dann auf die
erste Zeile von `fallback_providers` zurueck. Steht dort ein lokales Ollama-
Modell (typisch `gemma-e4b-8k:cpu`, Fenster **8.192**), ist das unter dem
Boden von 64.000 — und zwar **nur beim Start einer langen Sitzung**, wenn die
Kompression das erste Mal wirklich läuft. Kurze Sitzungen fallen nicht auf.

Deshalb ist die Fehlermeldung wochenlang unsichtbar und dann auf einmal an
jedem Worker gleichzeitig.

## Der Weg, den die Werte nehmen

1. `auxiliary.compression.provider/model` aus der Config (Profil-Config, sonst
   die Root-Config).
2. Fehlt der Block, greift `fallback_providers` in Reihenfolge.
3. `_enforce_minimum_context` bzw. `check_compression_model_feasibility`
   (`agent/conversation_compression.py`) wirft den ValueError, sobald das
   aufgeloeste Fenster < 64.000 ist.

Der Boden ist `MINIMUM_CONTEXT_LENGTH` in
`agent/model_metadata.py`, nicht `model.context_length` des Hauptmodells.

## Was taugt als Kompressionsmodell

Gemessen mit `get_model_context_length` (nicht aus dem Namen geraten):

| Modell | Fenster |
|---|---|
| `deepseek/deepseek-v4-flash-0731` (nous) | 1.048.576 |
| `stealth/space-bunny-alpha` (nous) | 1.000.000 |
| `anthropic/claude-opus-5` (nous) | 1.000.000 |
| `poolside/laguna-xs-2.1:free` (nous) | 262.144 |
| `gemma-e4b-8k:latest` / `:cpu` (ollama-launch) | **8.192** |

Der Modellname `gemma-e4b-8k` traegt die 8k **im Namen**, weil das Modell so
gebaut ist — nicht weil die Konfiguration zu kurz wäre.

## Die Regel

**Jede Profil-Config, deren `fallback_providers` als erste Zeile ein lokales
Modell mit kleinem Fenster trägt, braucht einen eigenen
`auxiliary.compression`-Block.** Nicht auf die Fallback-Kette verlassen: sie ist
eine Notreserve für den HAUPTpfad, kein Ort für Kompression. Der Kompressions-
Weg darf nie der einzige sein, der an einem Modell scheitert.

```yaml
auxiliary:
  compression:
    provider: nous
    model: deepseek/deepseek-v4-flash-0731
    timeout: 180
```

## Werkzeug

`scripts/kompression-provider-setzen.py` setzt den Block in Root- und allen
Profil-Configs, legt vorher je eine Sicherung unter `.sicherung/` an und prüft
Zeilenenden und Größe:

```
python scripts/kompression-provider-setzen.py             # Trockenlauf
python scripts/kompression-provider-setzen.py --anwenden
python scripts/kompression-provider-setzen.py --anwenden --zuruecknehmen
```

## Nachweis

1. Jede Config parst als YAML und trägt `auxiliary.compression.provider/model`
   — mit `hermes_yaml.safe_load`, **nicht** mit `hermes_yaml.load` (existiert nicht).
2. `git diff --numstat` zeigt je Datei genau die eingefuegten Zeilen (4/0 bzw. 6/0).
3. Die Karte läuft: `kanban --board X list` zeigt `running`, `runs` zeigt einen
   Run ohne `crashed`.

## Fallen

- **Zwei Sprachen, ein Python.** `hermes-agent/venv` hat `ruamel` installiert,
  `tools/python-3.14.7+.../` (der Interpreter des Gateways) hat es **nicht** —
  dort bricht jeder Probe-Import mit `ModuleNotFoundError: ruamel` ab. Das sieht
  wie ein kaputter Pfad aus und ist nur der falsche Interpreter. Die staged
  venvs unter `installs/<hash>/environments/*/venv` haben die Abhaengigkeiten.
- **Kein Konfig-Block im Profil heißt nicht 'geerbt'.** Profile sind Inseln
  (`HERMES_HOME` je Profil); die Root-Config gilt für sie **nicht**. Deshalb
  muss der Block in **jede** Profil-Config.
- **`rm`/`mv` auf `.git/index.lock` unter Windows nicht blind.** Wenn eine
  parallele Sitzung committen kann, ist die Sperre ein laufender Vorgang. Erst
  echte git-Prozesse zählen (`Get-CimInstance Win32_Process -Filter
  "Name='git.exe'" | Where CommandLine -notmatch 'fsmonitor'` — die elf
  `git fsmonitor--daemon` beweisen nichts), bei 0 Prozessen **umbenennen**
  (`.git/index.lock.verwaist-JJJJMMTT`), nie löschen.
- **`notify-subscribe` nimmt EINEN Task je Aufruf.** Mehrere IDs hintereinander
  werden mit `unrecognized arguments` abgewiesen — je Karte ein Aufruf.
- **Die Meldung `dependency lock still held after 10.0s; continuing without it`**
  beim Kanban-Befehl ist harmlos: eine `.install.lock` aus dem Update-Lauf.