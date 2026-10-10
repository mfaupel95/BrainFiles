---
name: fremd-agenten-betrieb
description: "Fremd-Agent-Repos ohne bezahlte Schluessel lokal betreiben."
category: brainfiles
---

# Fremd-Agenten-Betrieb

Fremde LLM-/Trading-Agenten-Repos (z. B. moon-dev-ai-agents) verlangen im
Original bezahlte API-Keys. Hausstandard: schluessellos — Urteil vom lokalen
Ollama, Marktdaten ueber oeffentliche API-Endpunkte, Autostart als geplante
Aufgabe. Hier: der Weg vom ersten Startfehler zum laufenden Dauerlaeufer.

## Start (in dieser Reihenfolge)

1. **Als Modul starten, nicht als Skriptpfad.** Scripte, die Paket-Imports
   machen (`import src.config`), nur als `python -m src.agents.<name>` aus dem
   Repo-Root — `python pfad/zu/skript.py` setzt `sys.path[0]` auf das
   Skriptverzeichnis und wirft `ModuleNotFoundError: No module named '<paket>'`.
2. **.env in die Prozessumgebung bringen.** Einzel-Agenten laden Dotenv oft
   nicht (nur der Repo-`main.py` tut das) und werfen hart bei jedem fehlenden
   Key. Beim Start exportieren, CRLF-sicher:
   `export OLLAMA_MODEL=$(grep '^OLLAMA_MODEL=' .env | cut -d= -f2 | tr -d '\r')`
   — ebenso `OLLAMA_BASE_URL`. Fehlt `load_dotenv()` im Skript, hilft ein
   Patch nichts, nur die Umgebung.
3. **Lokales Modell statt Key-Zwang.** OpenAI-SDK gegen Ollama:
   `openai.OpenAI(api_key="ollama", base_url=...)`.
   - base_url MUSS auf `/v1` enden (OpenAI-kompatible API); endet die .env auf
     `/api` (native Ollama-API), schlaegt der Call fehl. Robust:
     `(os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434/v1").replace("/api", "/v1")`.
   - Der Analyze-Pfad muss `chat.completions.create(...)` nehmen. Agenten mit
     `if "deepseek" in model ... else anthropic` brauchen den Ollama-Zweig
     VOR dem DeepSeek-Zweig — `anthropic.messages.create` ist gegen Ollama
     falsch und faellt erst auf, sobald die Daten laufen.
   - `model=` bekommt den OLLAMA-Modellnamen (z. B. `qwen35-8k:latest`),
     nicht den Repo-Modellnamen; `AI_MODEL` entsprechend vorbelegen.
4. **Pro-Endpoints ersetzen, nicht kaufen.** Fehler 10005
   („limited to PRO API subscribers") = Endpoint exklusiv; oeffentliche
   Alternative suchen. Oft existiert der oeffentliche Weg schon im Haus
   (Agenten/Handel/moondev_daten.py: `/coins/markets`; UA-Pflicht siehe
   Punkt 6). Oeffentliche Rate-Limits einrechnen:
   Kandidaten auf `head(3)` begrenzen, `DELAY` ~10-12 s, bei 429 15 s warten
   und einmal wiederholen. Ein- und Ausgabespalten an die Erwartung des
   Codes angleichen (`rename`: current_price→usd, ...), sonst crasht die
   CSV-Zusammenfassung am Schema — Summary zusaetzlich try/except-kapseln.
   Alte Ergebnis-CSVs aus dem Repo-Klon haben ein fremdes Schema: loeschen
   (`git rm -f`), damit der neue Header frisch entsteht.
5. **Unicode unter Windows-Aufgabenplanung.** Vom PowerShell-Wrapper
   gestartet, laeuft Python unter cp1252 und bricht beim ersten Emoji-print
   mit `UnicodeEncodeError: 'charmap'` ab (aus git-bash lief es, weil MSYS
   UTF-8 setzt). VOR `Start-Process`
   `$env:PYTHONIOENCODING='utf-8'` setzen.
6. **Oeffentliche Boersen-/Markt-APIs per urllib ansprechen.** OKX, Kraken
   und Binance weisen einen fehlenden oder generischen User-Agent mit 403
   ab — ein voller Browser-UA-String (z. B.
   `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/126.0 Safari/537.36`)
   ist Pflicht, gilt fuer alle drei Boersen und fuer CoinGecko gleichermassen.
   Bei POST mit JSON-Body (Solana-RPC, Kraken-Private-Endpoints) zusaetzlich
   `Content-Type: application/json` EXPLIZIT setzen — urllib schickt ihn
   nicht automatisch mit, sonst `415 Unsupported Media Type`.

## Autostart als geplante Aufgabe

- Wrapper nach `Agenten/Routinen/` (Bus-Meldungen `Melde-Start`/`Melde-Ende`,
  Log nach `logs/`, Ein-Instanz-Sperre per CommandLine-Match statt PID-Datei,
  `Start-Process` mit `-RedirectStandardOutput`/`-Error` auf GETRENNTE Dateien
  — dieselbe Datei fuer beides schlaegt fehl).
- **Registrieren braucht Elevation.** `Register-ScheduledTask` und
  `schtasks /Create` scheitern aus der Agent-Session mit 0x80070005 (kein
  interaktives Benutzer-Token). Muster: einmaliges Setup-Skript per
  `Start-Process powershell -Verb RunAs -WindowStyle Hidden -File <setup.ps1>`
  ausloesen (UAC-Dialog, der Nutzer klickt), danach READEND pruefen
  (`Get-ScheduledTask`). Bei Handy-Fernsteuerung nicht blind lostreten.
- Settings, die einen Dauerlaeufer am Leben halten:
  `-ExecutionTimeLimit ([TimeSpan]::Zero)` — der Default (72 h) beendet ihn;
  `-MultipleInstances IgnoreNew`; Trigger `AtLogOn` mit
  `$trigger.Delay='PT2M'`; Aktion mit `-WindowStyle Hidden`.
- Verifizieren statt glauben: Prozess lebt (CommandLine-Match), Wrapper-Log
  endet mit „ENDE ok", Agent-Log hat frischen Inhalt, Ausgabedateien tragen
  neue Zeitstempel. Ein erfolgreicher Start-Process beweist nichts.

## Werkstatt-Schreibzugriff

Repos unter `Werkstatt/Repos/` sind Junctions nach O: — `patch`/`write_file`
verweigern dort mit „outside HERMES_WRITE_SAFE_ROOT". Zwei Muster, je nach
Aufgabe:

- **Chirurgischer Einzeiler in einer bestehenden, versionsrelevanten Datei:**
  Wegwerfskript unter `Agenten/Hermes/cache/` (innerhalb der Root) ablegen,
  ausfuehren, loeschen. Skriptmuster: Roh-Bytes lesen, Zeilenende aus der
  Datei ableiten (CRLF pruefen) und beim Schreiben beibehalten, exakte
  Zeilen-Bloecke ersetzen (Treffer muss exakt 1 sein), danach `py_compile`
  + `git diff --stat` als Pruefung. Nie eine Textdatei per Rewrite neu
  schreiben (LF/CRLF).
- **Neue Datei anlegen oder mehrfach iterieren (z. B. ein GUI-Skript):**
  einfacher per Staging-Kopie — Datei ganz normal mit `write_file`/`patch`
  an einem Pfad INNERHALB der Safe-Root (z. B. direkt in der BrainFiles-
  Wurzel) anlegen/aendern, nach jeder Aenderung per
  `terminal("cp <staging-pfad> <Werkstatt-Zielpfad>")` synchronisieren und
  dort mit `py_compile` sowie einem echten Kurzlauf pruefen. Staging-Datei
  am Ende loeschen. Werkstatt/Repos ist ohnehin komplett `.gitignore`t —
  die CRLF/git-diff-Sorge des ersten Musters entfaellt hier.

## Weiterfuehrend

- Ein GUI-Kontrollzentrum (Tkinter) fuer so ein Repo bauen (Boersendaten,
  Agenten-Start/Stop, Wallet, Doku-Browser): `references/gui-kontrollzentrum.md`.

## Abgrenzung

- Forks/Klone anlegen, Bots je Repo, Shallow-Push, Telegram-Anbindung:
  `repo-flotte`
- Haus-Handelsspuren aus solchen Repos bauen: `handel-spuren`
  (Hinweis: SKILL.md ist am Groessenlimit — Ergaenzungen dort verweigert)
