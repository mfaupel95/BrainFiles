# GUI-Kontrollzentrum fuer Fremd-Agenten-Repos (Tkinter)

Wenn ein Repo-Kontrollpanel gewuenscht ist (Boersendaten, Agenten-Start/
Stop, Wallet, Doku-Browser, Batch-Laeufer) — bewaehrtes Muster.

## Architektur

- **Nur stdlib** (`tkinter` + `urllib`), keine zusaetzliche Abhaengigkeit,
  solange das venv des Repos requests/pandas fuer die Agenten selbst schon
  mitbringt. Ein eigenstaendiges GUI-Skript soll ohne `pip install` laufen.
- **Ein Worker-Thread pro Netzwerk-/Subprocess-Aktion**, nie im Main-Thread
  blockieren. Ergebnisse ueber `queue.Queue` zurueckgeben,
  `root.after(150, poll)` im Main-Thread leert die Queue. Tkinter-Widgets
  NIE aus einem Fremd-Thread anfassen — nur ueber diese Queue.
- **`ttk.Notebook`** mit einem Tab je Funktionsblock (Boersen/Wallet/
  Agenten/LLM/READMEs/Batch-Laeufer); jeder Tab baut sich in einer eigenen
  `_build_<tab>(nb)`-Methode, damit Tabs unabhaengig voneinander wachsen.
- **Agenten-Start/Stop:** `subprocess.Popen([VENV_PY, "-u", "-m",
  f"src.agents.{mod}"], cwd=REPO, env=env, stdout=open(logfile, "ab"),
  stderr=subprocess.STDOUT)` — deckt sich mit dem Modul-Startpfad aus
  `fremdrepo-agent-start`. Prozesse in einem Dict `self.threads[mod] =
  [popen, logpfad]` halten, im Poll-Loop `p.poll()` pruefen und dort
  aufraeumen statt eines eigenen Watchdog-Threads.
- **Log-Widgets:** `scrolledtext.ScrolledText(state="disabled")`, nur ueber
  eine `_log()`-Helper-Methode beschreiben (`configure(normal)` → `insert`
  → `see("end")` → `configure(disabled)`), sonst kann der Nutzer im Log
  herumtippen.

## Boersen-/Marktdaten ohne Schluessel

- OKX/Kraken/Binance-oeffentliche Endpunkte brauchen einen vollen
  Browser-User-Agent, sonst 403 (siehe Haupt-Skill Punkt 6) — beim Bau
  eines neuen Adapters immer zuerst gegen `curl` oder ein Terminal-Python
  pruefen, bevor der Code in die GUI wandert.
- POST mit JSON-Body (Solana-RPC, Kraken-Private) braucht `Content-Type:
  application/json` EXPLIZIT (siehe Haupt-Skill Punkt 6).
- **Order-Funktionen nur mit doppelter Absicherung:** ein Hartlimit auf
  die Order-Groesse im Code UND eine UI-Checkbox „wirklich senden“, die
  nach jedem Sende-Klick automatisch wieder zurueckgesetzt wird. Kein
  Order-Pfad ohne diese zwei Stufen — deckt sich mit dem Hausstandard
  „Paper zuerst, Live nur explizit“.

## Werkstatt-Schreibzugriff beim GUI-Bau

Siehe Haupt-Skill Abschnitt „Werkstatt-Schreibzugriff“, zweites Muster:
Staging-Datei in der Safe-Root pflegen, per `terminal("cp ...")` ins Repo
synchronisieren, dort mit `py_compile` und einem echten Kurzlauf pruefen
(z. B. `pythonw <skript>.py` per `terminal(background=true)` 10-15 s
laufen lassen, `Get-Process` bestaetigt den Start, danach
`Stop-Process -Force`; das Log muss leer/fehlerfrei bleiben — ein
erfolgreicher Prozessstart allein beweist nichts).
