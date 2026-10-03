# Prozessflut und Neustartschleife — Ablauf

Stand: 30.09.2026. Fall: der Hermes-Gateway starb 81 Minuten lang im
Zwei-Minuten-Takt, waehrend der Waechter ihn jedes Mal neu startete.

## Symptome, die hierher fuehren

- Ein Dienst antwortet nicht, obwohl die Zustandsdatei `running` meldet.
- Der Rechner wird kriechend langsam, ohne CPU-Fresser und ohne vollen RAM.
- Cron-Jobs melden `Overdue … (is the scheduler running?)` — der Scheduler
  laeuft im Gateway, sein Ausfall sieht wie ein Cron-Fehler aus.
- `docker`-Aufrufe und `git` brechen mit `WinError 1455` ab.

## Messkette (in DIESER Reihenfolge)

1. **Ports und Zustandsdatei trennen.** *Laeuft* und *erreichbar* sind zwei
   Aussagen. Ports: `Get-NetTCPConnection -LocalPort <p>` oder ein echter
   TCP-Connect. Zustandsdatei: `Agenten/Hermes/gateway_state.json`
   (`pid`, `gateway_state`, `updated_at`).
2. **Die PID ueber mehrere Proben verfolgen** (3–5 Proben, 15 s Takt). Eine
   ueber die Proben WECHSELNDE PID ist der Beleg fuer die Schleife — nicht der
   Zustandstext. Zweiter Zeuge: `lifecycle_ledger … exited UNCLEANLY` im
   Dienstprotokoll, und die Startzeilen (`Starting Hermes Gateway…`) zaehlen.
3. **Zahlen ueber die Zeit, nicht einmal.** `scripts/prozessflut-messen.ps1`
   ueber das `terminal`-Werkzeug (Vorgabe: Trockenlauf, 3 Proben a 10 s):
   python, node, `FreeVirtualMemory`, `FreePhysicalMemory`, Pagefile-Nutzung.
4. **Nach dem SKRIPT gruppieren, nicht nach dem Prozessnamen** — und beide
   Interpreten abfragen. Die node-Server tauchen in einer python-Zaehlung
   nicht auf; die Zahl sieht dann gesund aus, waehrend der Rechner erstickt.
5. **Den ERZEUGER suchen:** Kinder nach `ParentProcessId` gruppieren
   (`$kinder | Group-Object ParentProcessId | Sort-Object Count -Descending`).
   Die Gruppe, deren Eltern-PID dem verdaechtigen Dienst gehoert, nennt den
   Verursacher.

## Der belegte Fall (30.09.2026)

| Zeit | Beobachtung |
|---|---|
| 10:05 | Gateway antwortet nicht mehr (Prozess 7,3 h alt) |
| 10:43 / 11:18 / 11:26 / 11:36 | vier Starts, pid 35148 → 40964 → 35328 → 28188 |
| 10:16–11:28 | Hermes-Cron tot, alle Jobs `Overdue`, Catch-up „1h 24m late" |
| 11:33:36 → 11:36:34 | node 3 → 65, python 29 → 194, **Commit frei 24,8 → 0,5 GB** |
| 11:31 | **161 von 255** MCP-Kindprozessen hatten den Gateway als Eltern |

Deutung: Der Gateway startet je Profil/Client seine MCP-Server. Bei vielen
Profilen ist das keine Spawn-Kette, sondern **Multiplikation** — hunderte
Kinder. Die Commit-Erschoepfung toetet den Dienst unsauber, der Waechter
startet ihn zwei Minuten spaeter neu, die Runde beginnt von vorn.

## Die zwei Wachen und ihre Luecke

| Wache | Was sie sieht | Luecke |
|---|---|---|
| `Agenten/Hermes/scripts/mcp-zombie-wache.py` (Cron 15 min) | nur `python.exe`/`pythonw.exe` | **die node-basierten MCP-Server gar nicht** |
| `Agenten/Routinen/gateway-waechter.ps1` (2 min) | Prozess + Antwort | Startdauer > Neustart-Takt ⇒ Endlosschleife |

Merksatz: **eine Wache, die nur einen Interpreten fragt, ist blind fuer den
anderen.** Wer eine Prozesswache prueft, prueft ihren Filter mit.

## Abhilfe — in dieser Reihenfolge

1. **Erst den Erzeuger benennen** (Schritt 5 der Messkette). Ohne ihn ist
   jedes Beenden eine Tretmuehle: der Erzeuger startet in Sekunden nach.
2. **Ueberschuss beenden, um Luft zu schaffen** — je Gruppe die 3 jüngsten
   behalten, den Rest mit `Stop-Process -Id <pid> -Force` (nativer Befehl;
   `taskkill` aus windows-mcp tut still nichts). Messbar: Commit 0,5 → 26,5 GB.
3. **Die Wache erweitern** statt nur zu killen: Muster auf beide Interpreten,
   Takt von 15 auf 3 Minuten, Gesamtdeckel fuer MCP-Kinder.
4. **Startdauer gegen Waechter-Takt halten.** Braucht ein Dienst unter Last
   laenger zum Hochkommen als der Neustart-Takt, kommt er nie fertig — dann
   Takt oder Gnadenfrist anpassen, nicht den Dienst neu starten.

## Der Ausloeser ist oft ein NEUSTART, und die Abhilfe ist der Docker-Neustart

Wenn die Flut **kurz nach einem Docker- oder Gateway-Neustart** einsetzt und
der RAM in Ordnung ist, ist es nicht ein Fresser, sondern eine Kettenreaktion:
die MCP-Server starten nach dem Neustart mehrfach, statt je Gruppe bei drei zu
bleiben (gemessen: 10 bis 18 je Gruppe). Der RAM sagt dazu nichts — die
**Prozesszahl** und der **Commit** sind die Messgroessen, nicht der freie
Arbeitsspeicher.

Vorher und nachher dieselben vier Zahlen nehmen, sonst ist die Abhilfe eine
Behauptung: Prozesse gesamt, `python`/`pyw` gesamt, Commit belegt und frei,
RAM frei. Zwei Schwellen genuegen als Befund — **mehr als 50 Python-Prozesse
oder weniger als 8 GB Commit frei**.

Der gepruefte, schnellste Hebel ist ein sauberer Docker-Neustart:

1. Docker-Desktop-Prozesse beenden, `wsl --shutdown`, Docker Desktop starten.
2. **Bereitschaft abwarten** (`docker info` in Schleife, bis sie antwortet, mit
   Obergrenze) — der Start dauert zweistellig bis dreistellig Sekunden, und
   „gestartet“ ist kein „bereit“.
3. Danach die vier Zahlen erneut nehmen **und** die Container zaehlen. Gemessen
   ueber einen Neustart hinweg: Prozesse 991 auf 880, Python 90 auf 54, RAM
   frei 12,0 auf 18,2 GB, Commit belegt 87,8 auf 74,3 GB — und die MCP-Gruppen
   lagen wieder bei zwei bis vier Stueck je Gruppe, also innerhalb der Regel.

**Nebenwirkung vor dem Neustart pruefen:** Container mit
`RestartPolicy = "no"` werden mit beendet und kommen nicht zurueck. Vorher
`docker ps --format "{{.Names}}\t{{.Status}}"` sichern und die Namen mit
`"Up"` merken — im Bericht steht, was man mit beendet hat, sonst glaubt der
naechste Blick, es laufe noch.

**Und derRestart loest die Ursache nicht:** er macht die Flut nur billiger.
Jeder weitere Docker- oder Gateway-Neustart zueendet erneut — das ist der offene
Punkt, nicht der Messwert.

## Fallen

- **Die eigene Abfrage traegt den Suchtext.** `CommandLine -match 'gateway'`
  trifft die eigene bash-/PowerShell-Zeile, in der das Wort steht — dann
  liest man „stabile PIDs", die in Wahrheit die eigenen Abfragen sind.
  Muster aus Teilen bauen, `Name` mitpruefen, eigenen `$PID` ausschliessen.
- **`docker` und `git` sterben als Kollateralschaden.** Ihr Fehlerbild
  (`WinError 1455`, haengende Engine) zeigt auf Ressourcen, nicht auf sich
  selbst. Ad-hoc-`docker` immer mit Zeitgrenze, und **nicht** `$?` nach einer
  Pipe lesen — das misst `head`, nicht docker.
- **Ein Bericht ist keine Wache.** `spiegelstand.py`, der Nachtbericht und
  `hermes doctor` belegen einen Stand; gerufen werden muss er von etwas
  anderem.
- **Das Wissen liegt ausserhalb:** der offene Punkt zur Ursache ist T-152 in
  `MaxHirn/Archiv/TASKS.md`.