# Systemleistung 2026-09-29 — Design & Entscheidung

Stand: 2026-09-29, Europe/Berlin.

## 1. Zweck

Der PC meldete sich "sehr langsam". Diese Doc hält Ursache, Sofortbehebung,
die getroffene Entscheidung (Option 4: nichts weiter bauen) und den geplanten
Neustart fest. Sie ist Spezifikation für die Nachwelt, kein Arbeitsplan.

## 2. Befund (gemessen am Host)

| Größe                       | vorher (Notfall)            | nachher (jetzt)        |
|-----------------------------|-----------------------------|------------------------|
| Freies Commit (virt. Speicher) | **1,7 GB** von 87,7 GB     | **14 GB** von 78,5 GB  |
| Python-Prozesse             | **248** (195 älter 60 min)  | **40**                 |
| RAM frei                    | 30,7 GB                     | 33 GB                  |
| CPU                         | 12 % (idle)                 | 9 % (idle)             |
| Uptime                      | 99,6 h                      | 100 h                  |

**Ursache war die Commit-Erschöpfung, nicht CPU oder RAM.**
- ~200 Zombie-Python-Prozesse der MCP-Server (mail 44×, windows-mcp 42×,
  kraken 42×, archiv 38×, tooluniverse 38×, blender 14×) belegten
  **~29,6 GB Commit**. Sie wachsen seit dem Boot im Kreis (Spawn-Kette,
  siehe unten), ohne jemals zu enden.
- Folgen: `WinError 1455 "Auslagerungsdatei zu klein"`, SIGTERM-Wellen,
  und der lokale Modell-Rückfall der Bots (Ollama qwen35-8k) war wertlos,
  weil kein Commit für neue Modelle übrig war.

## 3. Sofortbehebung (bereits wirksam, heute Abend)

1. **Zombies gekillt** — jede MCP-Gruppe auf die 3 jüngsten Prozesse
   begrenzt (`Stop-Process`), 200 beendet. Python 248 → 40, Commit 14 GB frei.
2. **Wache `mcp-zombie-wache`** — Hermes-Cron, alle 15 min, `no_agent`,
   Telegram, **leere Ausgabe = gesund**: hält jede MCP-Gruppe bei den
   3 jüngsten Prozessen, meldet nur Aenderung/Anomalie.
3. Live-Handel (3 Stufen), MoonDev und Gateway wurden **nicht angefasst**.

## 4. Entscheidung Max (Option 4, 29.09.2026)

- **Kein weiterer Umbau jetzt.** Die Wache bleibt aktiv und wird beobachtet.
- Die **Spawn-Kette (Ursache) wird NICHT jetzt angefasst** — sie erfordert
  einen eigenen, abgestimmten Eingriff in die MCP-Startkonfiguration
  (Claude-Desktop / Hermes-Gateway vs. Server-venv-Autostart) und ist als
  Folgeaufgabe dokumentiert (T-152).
- **Kein Code an der Wache oder am Tagesbericht.**
- Unter der Hand sichtbar bleiben: 100 h Uptime, Memory Compression 7,5 GB —
  wird vom geplanten Neustart (Abschnitt 6) entlastet.

## 5. Bewertung der übrigen Kandidaten (nicht umgesetzt)

| Kandidat                          | Einschätzung                                     | Status        |
|-----------------------------------|--------------------------------------------------|---------------|
| MCP-Spawn-Kette beheben           | eigentliche Ursache; braucht eigenen Eingriff    | Folgeaufgabe T-152 |
| Defender-Ausnahmen (MsMpEng 532 MB) | scannt zur Laufzeit; sinnvoll, aber später     | Vorschlag, offen |
| Autostart-Last (NordVPN, Docker, Chrome) | kein akutes Problem, da Commit jetzt frei | Vorschlag, offen |
| Geplanter Neustart                | entlädt Memory Compression + Restlecks           | **einplanen** (Abschnitt 6) |

## 6. Geplanter Neustart (einplanen, NICHT jetzt ausführen)

**Wann:** ein ruhiges Zeitfenster AUSSERHALB der Nachtsicherungen
(20:00 G:, 21:00 O:, 22:00 Posteingang) — sinnvoll: nach 22:30 Uhr oder
vor 07:30 Uhr morgens.

**Warum sicher (Live-Richtungen):**
- Die drei Handels-Dauerlauf-Stufen starten sich über ihre Wächter-Tasks
  bei der nächsten Anmeldung selbst (Anmeldung-Trigger). Ein Neustart ist
  damit Selbstheilung, kein Eingriff.
- Offene Live-Positionen laufen mit Herzschlag-Regel 180 min: selbst wenn
  der Dauerlauf nach dem Logon 2-3 h nicht startete, würde nichts
  unkontrolliert flachgestellt.
- Voraussetzung vor dem Neustart ist ein frischer Zwischenstand
  (20:00-Nachtsicherung) bzw. die Zweitkopie — nie um 19:50 neu starten.

**Ausführung:**
1. `spiegelstand.py` und offene Live-Positionen prüfen (sind gesichert /
   freigabefenster zu).
2. Neustart mit `Restart-Computer -Force` (Status: wartet auf ein
   ruhiges Fenster + Max' Freigabe des Zeitpunkts).
3. Nach dem Logon: Dauerlauf-Stufen (PID-Dateien), Gateway, Dashboard,
   MCP-Wachen-Prüfung `mcp-zombie-wache` und Commit-Lage prüfen.

## 7. Erfolgskriterien

- Commit dauerhaft ≥ 8 GB frei bei 40-50 Python-Prozessen.
- `mcp-zombie-wache` meldet nichts (gesund) über mehrere Tage.
- Nach dem Neustart laufen alle drei Risikostufen + Gateway + Dashboard
  wieder, Bedingung 4 (Spiegelung) unverändert byte-gleich.

## 8. Beschlossen

- **29.09.2026** — Max: Option 4, Reboot einplanen.

## 9. Nachtrag 30.09.2026 — der Kreis kam wieder, diesmal mit Docker

Der Reboot war noch nicht gefahren, da stand dieselbe Erschöpfung erneut da —
aber mit einer anderen Ursache und einer härteren Folge: **der Docker-Daemon
starb und nahm alle Container mit.**

**Befund (02:20):** Commit frei 1,0 GB von 86,4 GB; `docker ps` antwortet leer,
WSL meldet „keine Distributionen ausgeführt", die Auslagerungsdateien sind
dabei fast leer (Commit ist *vergeben*, nicht *benutzt*). 146 Python-Prozesse
halten 28,3 GB Commit bei 9 GB echtem RAM. **134 davon waren jünger als eine
Stunde** — ein Spawn-Sturm, kein Altbestand.

**Ursache (aus dem Gateway-Log, nicht geraten):**

```
02:19:01 MCP servers reconciled with config (default): added=['MCP_DOCKER']
02:22:14 MCP servers reconciled with config (default): added=['MCP_DOCKER']
02:26:31 … 02:31:30 …
```

Der Gateway gleicht die MCP-Server regelmäßig mit der Config ab. In der Config
steht `MCP_DOCKER: docker`. Der Docker-Daemon war weg → dieser eine Server
scheitert → **der Abgleich startet daraufhin jedes Mal ALLE sechs lokalen
Gruppen neu** (kraken, windows-mcp, tooluniverse, mail, archiv, blender), je
ein 4-MB-Starter und sein Kind, im Sekundentakt. Das frisst den Commit, und
ohne Commit kann die WSL-VM nicht hochkommen — **ohne VM kein Docker, ohne
Docker kein `MCP_DOCKER`: ein geschlossener Kreis.** Der Gateway selbst war
der Erzeuger: eine PID mit 56 Kindern in zehn Minuten.

**Kur (wirksam, gemessen):** nur die Prozesse mit `MCP-Server` in der
Kommandozeile beendet — nicht den Gateway, nicht die Handels-Dauerläufe, nicht
die MoonDev-Agenten. Ergebnis: **130 Prozesse weg, Commit 2,6 → 17 GB.** Danach
Docker Desktop samt WSL neu gestartet (`wsl --shutdown`, dann die App) →
`daemon=29.8.1`, Commit 24,3 GB, Python 146 → 23. Der MCP-Abgleich läuft weiter
alle ~5 Minuten, startet aber nichts mehr nach (0 MCP-Prozesse).

**Zwei Lehren, die über den Einzelfall hinausgehen:**

1. **Eine scheiternde Abhängigkeit kann mehr kosten als die Abhängigkeit
   selbst.** Ein einziger nicht startbarer MCP-Server hat über den
   Abgleich-Mechanismus das ganze System in den Abgrund gezogen. Wer einen
   Server einträgt, trägt auch seinen Ausfallweg mit ein.
2. **Commit-Erschöpfung sieht nicht wie Speichermangel aus.** 20 GB RAM frei,
   Auslagerungsdateien fast leer — und trotzdem kann kein Arbeitsprozess mehr
   starten. `hermes mcp remove` scheiterte in dieser Lage mit
   `pm: worker exited without a result`: das Werkzeug, das die Ursache beheben
   sollte, konnte wegen der Ursache nicht laufen. **Der Ausweg ist dann nicht
   das Werkzeug, sondern das gezielte Beenden.**

**Nicht angefasst:** die drei Handels-Risikostufen, die MoonDev-Agenten, der
Gateway (er lief weiter), und die 12 `docker-mcp`-Prozesse. Die
kind-Kubernetes-Container von Docker Desktop (5 Stück) sind ebenfalls wieder
hoch und fressen einen Teil des Commits zurück — sie sind ein Kandidat, aber
noch nicht entschieden.

## 10. Nachtrag 30.09.2026 (2) — derselbe Kreis, diesmal den ganzen Tag und mit Kollateralschäden an Fremdsoftware

Derselbe Docker/MCP-Spawn-Kreis aus Abschnitt 9 lief heute **nicht nur einmal
nachmittags, sondern durchgehend seit 02:05 Uhr** weiter: Der Hermes-Gateway
selbst ist laut eigenem Lebenszyklus-Protokoll (`Agenten\Hermes\logs\gateway.log`,
`lifecycle_ledger`) zwischen 02:05 und 17:03 Uhr **26-mal unsauber gestorben**
(„exited UNCLEANLY … SIGKILL / OOM / VM death") und wurde jedes Mal automatisch
neu gestartet — im Schnitt alle 20-30 Minuten, den ganzen Arbeitstag über. Nach
17:03 Uhr keine weiteren unsauberen Neustarts mehr: der Docker/WSL-Neustart
(unten) hat den Kreis durchbrochen.

Sichtbarster Ausschlag dieses Dauerzyklus war das Fenster 16:46–17:04, das
diesmal per Fail-Fast **vier unbeteiligte Prozesse** lahmlegte:
`KrakenDesktop.exe` (3×), `Telegram.exe` (1×) und Hermes' gebündeltes
`python.exe` (1×) — belegt über die Ereignisanzeige (Application-Log,
Event 1000 „Faulting Application"), alle im selben engen Zeitfenster, alle
mit Exceptioncode `0xC0000409` (Telegram/Kraken) bzw. `0xC00000FD`
(python.exe, STATUS_STACK_OVERFLOW — verwandter Fail-Fast-Pfad). Parallel
riss es auch den manuellen `sicherung.ps1`-Testlauf (PID 19444) mit — eine
zusätzliche WER-`OutOfMemoryException` für `powershell.exe` um 16:50:16 fiel
in dasselbe Fenster. Ein weiterer manueller Testlauf (Datensortierung, 15:37,
Hintergrundprozess `bhtif4ert`) brach mitten im Lauf mit Exitcode 255 ab —
ebenfalls erklärt durch denselben Dauerzyklus (Gateway-Neustart 15:32:58, nur
5 Minuten vor Testbeginn), keine eigene Ursache im Sortierskript.

**Wichtige Korrektur:** Damit ist die bisherige Vermutung widerlegt, die
wiederkehrenden `3221225786`-Abbrüche von `MaxHirn-Sicherung`,
`-Zweitkopie` und `-OmniRoute` lägen an Task-Scheduler-Eigenheiten oder an
Claude-Desktop-Dateisperren. Es ist derselbe system­weite
Commit-Erschöpfungskreis wie in Abschnitt 9 — unabhängig davon, ob der
Aufruf interaktiv oder über die Aufgabenplanung kam. Der irreführende
Kommentar dazu in `Agenten\sichern.ps1` (Zeile ~199, „STATUS_CONFLICT_WITH_LOCK
= Claude Desktop war noch offen") wurde am 30.09.2026 korrigiert.

**Kur:** identisch zu Abschnitt 9 — 38 überzählige MCP-Server-Prozesse
beendet (je Gruppe die 3 jüngsten behalten; RAM frei 15,7 → 21,7 GB, Python
270 → 62), danach `wsl --shutdown` + Docker Desktop neu gestartet.

**Dritte Lehre:** Der Schaden bleibt nicht auf MCP-Server oder Claude
beschränkt — jeder Prozess auf demselben Host kann per Fail-Fast sterben,
sobald der Commit ausgeht. `0xC0000409` in der Ereignisanzeige ist also kein
Hinweis auf einen Fehler *in* der abgestürzten Anwendung, sondern ein starkes
Indiz für System-Commit-Erschöpfung, wenn zeitgleich mehrere unabhängige
Prozesse denselben Code melden — genau danach lohnt sich beim nächsten Mal
zuerst zu suchen (`Get-WinEvent -FilterHashtable @{LogName='Application';
Id=1000}`), bevor eine Ursache im einzelnen Skript vermutet wird.

## 11. Nachtrag 05.10.2026 — erst CPU messen, dann RAM freigeben

**Regel: der Auftrag „RAM freigeben" ist haeufig ein CPU-Befund.** Der Rechner
kann 21 GB frei haben, `LoadPercentage` 100 anzeigen und sich trotzdem tot
anfuehlen. **Vor** jeder Speicher-Aktion eine Momentanlast messen — als
Differenz zweier Ablesungen, weil `Sort-Object CPU` Lebenszeit zeigt, nicht
Last:

```powershell
$a=@{}; Get-Process | ForEach-Object { $a[$_.Id]=$_.CPU }
Start-Sleep -Seconds 8
Get-Process | ForEach-Object {
  if ($a.ContainsKey($_.Id) -and $null -ne $_.CPU) {
    $d=[double]($_.CPU-$a[$_.Id]); if ($d -gt 0.4) { '{0} {1} {2:N2} Kerne' -f $_.Name,$_.Id,($d/8) }
  }
} | Sort-Object { $d } -Descending
```

`Win32_Processor.LoadPercentage` taugt als Alarmschwelle, nicht als Beweis — es
kann dauerhaft 100 zeigen, obwohl die Last woanders liegt.

**Der stille Vollgas-Fresser: ein lokales Modell auf `:cpu`.** Gemessen 47,6 von
28 Kernen ueber 8 Sekunden bei 5,2 GB RAM, bei **null** offenen Verbindungen und
einem Logeintrag von Stunden her. Drei Zeugen, bevor ein Prozess als Fresser
gilt: die Differenzmessung oben, `Get-NetTCPConnection -RemotePort 11434 -State
Established` (gibt es die Verbindung noch?), und der Zeitstempel von
`%LOCALAPPDATA%\Ollama\server.log`. `/api/ps` mit `size_vram: 0` ist das
eindeutige Kennzeichen der CPU-Variante; `expires_at` in der Vergangenheit plus
unveraendertes Log heisst „abgelaufen, nur nicht freigegeben". Entladen ohne
Neustart ueber `/api/generate` mit `keep_alive: 0`.

**Merksatz: ein leerer Log bedeutet fuer einen Dauerprozess „er rechnet
nicht", nicht „er ist weg".** Die Stille eines Idle-Modells und die Stille eines
abgestuerzten Dienstes sehen gleich aus — der Unterschied ist der offene Port.
