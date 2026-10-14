---
id: 20260830-routinen
title: 'Routinen'
tags: [betrieb]
created: 2026-08-25
updated: 2026-09-29
related: [20260830-wiederholbare-aufgaben, 20260831-marktscanner, 20260902-handelsregeln, 20260916-optimierungen-finden]
summary: 'Welche Abläufe ohne Aufforderung laufen, mit Zeitplan und Protokollort.'
---

# Routinen

Abläufe, die ohne Aufforderung passieren sollen. Eine Routine ist immer ein
vorhandener Skill plus ein Zeitplan.

## Geplant

| Wann | Was | Skill | Status |
|---|---|---|---|
| täglich 09:00 | DCA-Fälligkeit prüfen | `Handel/agent.py check` | **eingeplant** 23.08.2026 — `MaxHirn-DCA-Pruefung` |
| täglich 07:30 | Marktscanner: **nur die Rangliste** | `Handel/scanner/scan.py` | **geändert** 14.09.2026 — `MaxHirn-Marktscanner`. `handeln.py --papier` ist aus dem Wrapper entfernt; die Spur handelt im Dauerlauf (alle 15 Min). |
| täglich 07:45 | Kraken-Spur 3: **nur die Rangliste** | `Handel/kraken/scan.py` | **geändert** 14.09.2026 — `MaxHirn-Kraken-Spur3`. Wie oben; gehandelt wird im Dauerlauf, seit derselbe Tag die Spur wieder führt. |
| täglich 08:10 | Scanner-Papier-Test v0 gegen v4 (nur Messung, kein Geld) | `Werkstatt/scanner-varianten/papier.py` | **eingeplant** 02.10.2026 — `MaxHirn-Scanner-Papier`, angelegt über `Routinen/scanner-papier-aufgabe.ps1`. Prüft Stops/Ziele offener Papier-Positionen mit frischen OKX-Kerzen und nimmt neue Signale auf. Auswertung erst nach ca. 30 Runden je Variante; Übernahme von v4 in den Live-Scanner nur nach Entscheidung von Max. |
| stündlich :05 | Scanner-Papier-Stundenprüfung (Stop/Ziel offener Papier-Positionen mit OKX-1H-Kerzen) | `Werkstatt/scanner-varianten/papier_stunde.py` | **angelegt** 02.10.2026 — `MaxHirn-Scanner-Papier-Stunde`, Registrierung über `Routinen/scanner-papier-stunde-aufgabe.ps1` (Administrator). Beschleunigt die Auswertung: Ausstiege binnen Stunden statt Tagen; Lockdatei `papier.lock` verhindert Überschneidung mit dem 08:10-Lauf. |
| — | XPERP-Spur 2 (läuft im Dauerlauf) | `Handel/xperp/handeln.py` | **Aufgabe gelöscht** 14.09.2026 — `MaxHirn-XPERP-Spur2` fuhr um 07:50 einen zweiten Zyklus (Ziel-Ausstieg FIL, drei Einstiege am 14.09.2026), den der Dauerlauf nicht kannte. `Routinen/xperp-handeln.ps1` bleibt als Notbetrieb von Hand. |
| alle 30 Min | Dauerlauf-Wächter (Neustart nach Abschaltung) | `handel-dauerlauf.ps1` | **eingeplant** 07.09.2026 — `MaxHirn-Handel-Dauerlauf-Waechter` |
| bei Anmeldung + alle 30 Min | Stufen-Wächter mittel und hoch (Start **und** Neustart in einem) | `handel-dauerlauf.ps1 -Risiko mittel` bzw. `hoch` | **nachgetragen** 29.09.2026 — `MaxHirn-Handel-Dauerlauf-Mittel-Waechter`, `MaxHirn-Handel-Dauerlauf-Hoch-Waechter`. Seit 16.09.2026 in Betrieb, aber hier nie vermerkt. Zeitauslöser am 29.09.2026 ergänzt, siehe unten. |
| alle 15 Min | Bus-Wächter (Neustart nach Ausfall, Meldung nur bei Befund) | `Agenten/Hermes/scripts/bus-waechter.py` | **eingeplant** 15.09.2026 — Hermes-Cron `bus-waechter`, **kein Windows-Task**: läuft absichtlich am Bus vorbei (`no_agent`, Ausgabe = Meldung), weil eine Wache, die über den Bus meldet, bei totem Bus schweigt. Anlass: der Bus war vom 11.09. 21:13 bis 15.09. 21:02 aus, vier Tage ohne Meldung. |
| alle 15 Min | Atlas-Wächter (startet den ProjectAtlas-Watcher neu, still bei Befundfreiheit) | `Agenten/Hermes/scripts/atlas-watcher.py` | **eingeplant** 15.09.2026 — Hermes-Cron `atlas-watcher`, ebenfalls **kein Windows-Task** (`no_agent`, leere Ausgabe = nichts senden). Prüft die PID aus `Agenten/Werkzeuge/projectatlas/logs/watch-omnitrade.pid`; der Watcher ist ein Dauerprozess auf `Werkstatt/omnitrade` und zieht den Atlas nach, wenn sich Dateien ändern. Anlass: ohne ihn veraltet die Karte still. |
| montags 09:15 | Repo-Klone unter `Werkstatt/` gegen upstream prüfen (Skill-Quellen aktuell halten) | `Agenten/Hermes/scripts/repo-updates-check.py` | **eingeplant** 16.09.2026 — Hermes-Cron `repo-updates-check`, **kein Windows-Task** (`no_agent`, Meldung nur bei Rückstand). Anlass: superpowers-Klon war zwei Monate hinter upstream; ohne Prüfung altern die Skill-Quellen still.
| montags 09:30 | Skill-Nutzung auswerten (Bibliothek schlank halten) | `Agenten/Hermes/scripts/skill-usage-report.py` | **eingeplant** 16.09.2026 — Hermes-Cron `skill-usage-report`, **kein Windows-Task** (`no_agent`, Top-10 nach Aufrufen + ungenutzte Skills). Anlass: jede geladene SKILL.md kostet bei jeder Anfrage Tokens; das Ausmisten am 11.09.2026 sparte ~3.000 Tokens je Anfrage.
| sonntags 08:00 | Wachen-Abgleich Spur 1 **und** 3 (Bedingung 5) | `scanner/handeln.py --wachen` + `kraken/handeln.py --wachen` | **eingeplant** 02.09.2026 — `MaxHirn-Handel-Wachen` |
| alle 4 Std | Automatik-Wächter: feuern die Cron-Aufträge noch, und kommen die Meldungen an? | `Agenten/Hermes/scripts/automatik-waechter.py` | **eingeplant** 18.09.2026 — Hermes-Cron `automatik-waechter`, **kein Windows-Task** (`no_agent`, leere Ausgabe = nichts senden). Prüft gegen `Agenten/Hermes/cron/jobs.json`: `last_run_at` gegen die Zeitplan-Lücke, `last_status`, `last_delivery_error` und einen hängenden `next_run_at`. Anlass: keine der vorhandenen Wachen bewacht die Wachen selbst — der Bus war vier Tage stumm, ohne dass es jemandem auffiel. Zweiter Zutritt: dieselbe Prüffunktion läuft in `MaxHirn-Optimierungen-Finden` (Windows-Aufgabe) mit, damit ein Ausfall des Schedulers nicht unbemerkt bleibt. |
| taeglich 07:45 | OKX- und Handels-Tagesbericht: DEX-Top-Volumen, Leaderboard, BTC/ETH/SOL, Spurenkennzahlen, Parametervorschlaege (nur Hinweise) | `Agenten/Hermes/scripts/okx-trading-bericht.py` | **eingeplant** 19.09.2026 - Hermes-Cron `okx-trading-bericht`, **kein Windows-Task** (`no_agent`, Ausgabe = Meldung). Rein lesend: onchainos-CLI (OKX-DEX) und OKX-REST ohne Schluessel; Vorschlaege zeigen nur an, WO eine Parameterpruefung (handel-spur-optimierung) lohnt, nichts wird geaendert (Schutzstufe 1).
| alle 30 Min | OKX-Gesundheit: sind REST-API und onchainos-CLI erreichbar? | `Agenten/Hermes/scripts/okx-gesundheit.py` | **eingeplant** 19.09.2026 - Hermes-Cron `okx-gesundheit`, **kein Windows-Task** (`no_agent`, leere Ausgabe = nichts senden). Prueft die zwei lesenden OKX-Kanaele ohne Schluessel; Guthaben/Wallet bewusst nicht (Zugaenge.md ist die einzige Ablage). MCP-Kanaele prueft systempruefung.ps1.
| montags 09:35 | Skill-Nutzung NUR okx-*/handel-* Skills | `Agenten/Hermes/scripts/okx-skill-nutzung.py` | **eingeplant** 19.09.2026 - Hermes-Cron `okx-skill-nutzung`, **kein Windows-Task** (`no_agent`). Wrapper um `skill-usage-report.py --nur okx,handel` - der Filter lebt im bestehenden Skript, hier steht nur der Aufruf.
| täglich 20:00 | Sicherung nach `G:` | `sichern.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Sicherung` |
| täglich 21:00 | Zweitkopie nach `O:` → **Ziel ist J:**, siehe Abschnitt „Zweitkopie“ unten | `sichern-zweitkopie.ps1` | **eingeplant** 23.08.2026 — `MaxHirn-Zweitkopie` |
| täglich 21:30 | Außer-Haus-Kopie auf `Q:` erneuern, **wenn** die Platte angesteckt ist; sonst nach Sekunden „übersprungen" (Exitcode 2, kein Fehlschlag) | `Routinen/ausserhaus-kopie.ps1` | **eingeplant** 29.09.2026 — `MaxHirn-Ausserhaus-Kopie`. Ruft `sichern-ausser-haus.ps1`. Steht hier, weil die Aufgabe läuft; das **außer Haus bringen** bleibt Handarbeit (Abschnitt unten). Zweiter Wächter: Hermes-Cron `ausserhaus-frist-wache` (08:00) meldet, wenn die Kopie 14 Tage alt wird. |
| täglich 22:00 | Posteingang einsortieren | `posteingang` | **eingeplant** 23.08.2026 — `MaxHirn-Posteingang` |
| stündlich, zur vollen Stunde | Zwischenstand der Textebene | `Routinen/zwischenstand.ps1` | **eingeplant** 25.08.2026 — `MaxHirn-Zwischenstand`. Lief bis 02.09.2026 stündlich, im Umfeld des System-Umzugs auf täglich 20:00 reduziert, am 29.09.2026 wieder auf stündlich gestellt (Max: „verliere andauernd Arbeit“ — der Umzug ist abgeschlossen, der Grund für die Reduzierung entfällt). Damit sinkt das ungesicherte Fenster von einem Tag auf höchstens eine Stunde. |
| stündlich, :20 nach der vollen Stunde | Fremdarbeit beendeter Sitzungen in die Hauptarbeit (`master`) übernehmen | `Routinen/fremdarbeit-einziehen.ps1` | **eingeplant** 21.09.2026 — `MaxHirn-Fremdarbeit-Einziehen`, am 29.09.2026 mit dem Zwischenstand auf stündlich umgestellt. Läuft **nach** dem jeweiligen Zwischenstand: der sichert die Arbeit erst auf den Branch `zwischenstand`, diese Aufgabe holt dieselbe Arbeit ein zweites Mal ab und schreibt sie in **einem** Commit mit dem Autor `Andere Sitzung <fremd@local>` nach `master`. Ruhend heißt weiterhin: länger als 30 Minuten unberührt. Details im Abschnitt „Fremdarbeit übernehmen“ unten. |
| täglich 07:00 | Systemprüfung (Drift-Bericht) | `Routinen/systempruefung.ps1` | **eingeplant** 02.09.2026 — `MaxHirn-Systempruefung`. Sucht nach toten Junctions, doppelten Ollama-Stores, kaputten Pfaden; räumt Eindeutiges selbst auf, meldet den Rest. Bericht: `Routinen/logs/systempruefung-letzter-lauf.md`. Details in [[Systempruefung]]. |
| täglich 07:00 (in Systemprüfung) | Konfig-Doktor (Konfigurationsgesundheit) | `Routinen/konfig-doktor.ps1` | **eingebunden** 09.10.2026 als Block 16 der Systemprüfung (`-Kurz`, nur Zählzeile; KRITISCH landet unter „Zu entscheiden"). Rein lesend; Module mcp-pfade, hermes, regelpaare, git-regeln, ballast, laufzeit. Vollbericht von Hand ohne `-Kurz` nach `Werkstatt/konfig-doktor-<datum>.md`. Exit 0/1/2. Tests: `Routinen/tests/konfig-doktor.test.ps1`. |
| alle 2 Min | Papier-Ausführung der Fremd-Signale (kraken-cli, OKX Agent Trade Kit) hinter dem Tor | `Routinen/fremd-papier.ps1` → `Handel/fremd_signale/handeln.py --papier` | **registriert** 11.10.2026 (`Routinen/fremd-papier-aufgabe.ps1`, `MaxHirn-Fremd-Papier`). Tor seit 11.10.2026 offen (`fremd_signale/wachen.json`, nur paper/demo). Nur Papier, kein `--live`. Zweig `claude/fremd-signal`. |
| alle 5 Min | Nautilus-Signalgeber mit echten OKX-Kerzen (BTC-USDC, 5m): neue EMA-Kreuzung → `Werkstatt/nautilus_intents.jsonl` | `Routinen/nautilus-okx.ps1` → `Bus/nautilus_okx_lauf.py` (nautilus-venv) | **registriert 11.10.2026, am 12.10.2026 DEAKTIVIERT** (Walk-forward ohne Vorteil, siehe Plan; `Routinen/nautilus-okx-aufgabe.ps1`, `MaxHirn-Nautilus-OKX`; Wiedereinschalten: `Enable-ScheduledTask`). Handelt nie; Beispielstrategie, kein belegter Vorteil. |
| alle 2 Min | Fremd-Adapter: neue Signale von nautilus_trader / moon-dev-ai-agents (/ itb, aus) an den Bus | `Routinen/fremd-adapter.ps1` → `Bus/adapter_lauf.py` (Quellen: `Bus/adapter_quellen.json`) | **registriert** 11.10.2026 (`Routinen/fremd-adapter-aufgabe.ps1`, `MaxHirn-Fremd-Adapter`). Meldet nur; das Tor entscheidet. Kein `--live`. |
| bei Systemstart | BrainFiles-Bus | `Agenten/Bus/bus.py` | **eingeplant** 10.09.2026 — `BrainFiles-Bus`, registriert über `Agenten/Routinen/bus.ps1`. Meldet Start und Ende aller geplanten Aufgaben, wertet deren Erfolg aus und sichert Fehler auf dem Handy. Ein toter Bus darf niemals einen Lauf abbrechen — alle Erzeuger schreiben lokal ins Journal zurück. |
| dauerhaft, Takt 15 min | Handels-Dauerlauf: Zyklus, Befehle vom Handy, Tagesbericht ab 08:00 | `Handel/dauerlauf.py` | **eingeplant** 07.09.2026 — `MaxHirn-Handel-Dauerlauf` (Anmeldung) + Wächter. `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` seit 07.09.2026 gesetzt, siehe Abschnitt „Der Telegram-Melder" |
| werktags 08:00 | Tagesbriefing | `tagesbriefing` | noch nicht eingeplant |
| werktags 07:15 | Marktüberblick (nur lesen) | `/marktbriefing` über `marktbriefing.ps1` | **Registrierbefehl bereit, Aufgabe noch nicht angelegt** — 07.09.2026, siehe Abschnitt „Marktbriefing" unten |
| freitags 17:00 | Wochenrückblick | `wochenrueckblick` | noch nicht eingeplant |
| bei Anmeldung (+2 Min) | OmniRoute-Router starten, falls er nicht läuft | `Routinen/omniroute-start.ps1` | **eingeplant** 13.09.2026 — `MaxHirn-OmniRoute`. Ohne den Router fällt der Hermes-Provider omniroute aus; jede Agenten-Delegation scheitert dann mit `Connection error`/HTTP 401 — das war nach jedem Neustart der Zustand. Startet nur, wenn Port 20128 frei ist (zwei Instanzen teilen sich `~/.omniroute/storage.sqlite`). Die alten Autostart-Einträge bleiben deaktiviert. |
| bei Anmeldung (+2 Min) | Handelszentrale öffnen (lesende Ansicht über alle Spuren) | `Handel/handelszentrale.py` | **eingeplant** 13.09.2026 — `MaxHirn-Handelszentrale`, angelegt über `Routinen/handelszentrale-aufgabe.ps1`. Zeigt Spuren, offene Positionen aller Spuren, Kerzenchart und die Konsole; **rein lesend** — der Dauerlauf bleibt der einzige Schreiber. Startet nur, wenn nicht schon ein Fenster offen ist (Fenstertitel statt PID-Datei, damit auch ein von Hand gestartetes Fenster zählt). |
| bei Anmeldung (+2 Min) | Nautilus-Quoten-Container (nautilus-demo) starten, falls er nicht läuft | `Routinen/nautilus-docker-start.ps1` | **eingeplant** 19.09.2026 — `MaxHirn-Nautilus-Docker`. Docker startet bei Anmeldung, der Container hat --restart unless-stopped; diese Aufgabe fängt den Restfall ab (Docker bereit, Container nicht hochgekommen). Idempotent. |
| montags 09:45 | Optimierungen finden: Läufe ohne Ende, Leichen, Prozess-Drift | `Agenten/Hermes/scripts/optimierungen-finden.py` | **eingeplant** 16.09.2026 — `MaxHirn-Optimierungen-Finden`, angelegt über `Routinen/optimierungen-finden-aufgabe.ps1`. Liest die Protokolle der anderen Routinen nach: wer angefangen und keine Ende-Zeile geschrieben hat, welche Aufgabe deaktiviert ist oder auf eine fehlende Datei zeigt, wie viel Speicher die Python-Familien belegen (nur die Veränderung gegenüber dem letzten Lauf). Anlass: die Sicherung um 20:00 war am 16.09.2026 von außen beendet worden (0xC000013A) — im Protokoll stand nur die Kopfzeile, und der Bus konnte nichts melden, weil das Ende-Ereignis nie geschrieben wurde. Der Befund geht als `hinweis` über den Bus, **nicht** als Fehlercode. |
| alle 60 Min | FOMO-Radar: neue On-Chain-Fuellungen der bewerteten Kohorte (Kauf/Verkauf je Token, Wallets, USD) plus Aenderung der Radar-Gesundheit | `profiles/hermes-wartung/scripts/fomo-radar-loop.py` | **eingeplant** 11.10.2026 - Hermes-Cron `fomo-radar-loop` (Job 7d6ce036051a), **kein Windows-Task** (`no_agent`, leere Ausgabe = nichts senden). Rein lesend: liest die Radar-DB und `fomo-radar health`, sammelt NICHT (das tut `radar-sammler`, alle 20 Min). Anlass: der erste Versuch (Job `fomo-radar Loop` im Profil `bots`) liess einen Agenten `fomo-radar run` aufrufen - eine Polling-Schleife, die nach 303 s im Timeout endete und danach 45 Min im Zustand `running` haengen blieb. Zahlen aus einer Datenbank brauchen kein Modell. Merkdatei `Agenten/Hermes/cache/fomo-radar-loop/letzter-stand.json`; Radar-Gesundheit seit 11.10.2026: `fomo collection` und `holdings` BAD (beides braucht Zugangsdaten bzw. den Sammler im Repo), Server `fomoradar.app` von hier nicht erreichbar (Port 443 Timeout). |

Die eingeplanten laufen über die **Windows-Aufgabenplanung**, nicht über
`/schedule` — Begründung unten. Sie starten nicht das Skript direkt, sondern
einen Wrapper aus `Routinen/`. Seit dem 02.09.2026 sind es **neun**; die drei
Handels-Routinen kamen an diesem Tag dazu und sind je einmal aus der
Aufgabenplanung heraus gelaufen (Ergebniscode 0):

| Aufgabe | Wrapper | Protokoll |
|---|---|---|
| `MaxHirn-Sicherung` | `Routinen/sicherung.ps1` | `Routinen/logs/sicherung-letzter-lauf.log` |
| `MaxHirn-Zweitkopie` | `Routinen/zweitkopie.ps1` | `Routinen/logs/zweitkopie-letzter-lauf.log` |
| `MaxHirn-Ausserhaus-Kopie` | `Routinen/ausserhaus-kopie.ps1` | `Routinen/logs/ausserhaus-kopie-letzter-lauf.log` |
| `MaxHirn-Posteingang` | `Routinen/posteingang.ps1` | `Routinen/logs/posteingang-letzter-lauf.log` |
| `MaxHirn-DCA-Pruefung` | `Routinen/dca-pruefung.ps1` | `Routinen/logs/dca-letzter-lauf.log` |
| `MaxHirn-Scanner-Papier` | `Routinen/scanner-papier.ps1` | `Routinen/logs/scanner-papier-letzter-lauf.log` |
| `MaxHirn-Scanner-Papier-Stunde` | `Routinen/scanner-papier-stunde.ps1` | `Routinen/logs/scanner-papier-stunde-letzter-lauf.log` |
| `MaxHirn-Fremd-Papier` | `Routinen/fremd-papier.ps1` | `Routinen/logs/fremd-papier-letzter-lauf.log` |
| `MaxHirn-Nautilus-OKX` | `Routinen/nautilus-okx.ps1` | `Routinen/logs/nautilus-okx-letzter-lauf.log` |
| `MaxHirn-Fremd-Adapter` | `Routinen/fremd-adapter.ps1` | `Routinen/logs/fremd-adapter-letzter-lauf.log` |
| `MaxHirn-Marktscanner` | `Routinen/marktscanner.ps1` | `Routinen/logs/marktscanner-letzter-lauf.log` |
| `MaxHirn-Kraken-Spur3` | `Routinen/kraken-scanner.ps1` | `Routinen/logs/kraken-scanner-letzter-lauf.log` |
| `MaxHirn-Handel-Wachen` | `Routinen/handel-wachen.ps1` | `Routinen/logs/handel-wachen-letzter-lauf.log` |
| `MaxHirn-Zwischenstand` | `Routinen/zwischenstand.ps1` | `Routinen/logs/zwischenstand-letzter-lauf.log` |
| `MaxHirn-Systempruefung` | `Routinen/systempruefung.ps1` (kein Wrapper, protokolliert selbst) | `Routinen/logs/systempruefung-letzter-lauf.md` + `systempruefung-JJJJ-MM-TT.log` |
| `BrainFiles-Bus` | `Agenten/Bus/bus.py` | `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` |
| `MaxHirn-OmniRoute` | `Routinen/omniroute-start.ps1` | `Routinen/logs/omniroute-letzter-lauf.log` |
| `MaxHirn-Handelszentrale` | `Routinen/handelszentrale.ps1` (angelegt über `Routinen/handelszentrale-aufgabe.ps1`) | `Routinen/logs/handelszentrale-letzter-lauf.log` |
| `MaxHirn-Optimierungen-Finden` | `Routinen/optimierungen-finden.ps1` (angelegt über `Routinen/optimierungen-finden-aufgabe.ps1`) | `Routinen/logs/optimierungen-finden-letzter-lauf.log` |
| `MaxHirn-Fremdarbeit-Einziehen` | `Routinen/fremdarbeit-einziehen.ps1` (angelegt über `Routinen/fremdarbeit-einziehen-aufgabe.ps1`) | `Routinen/logs/fremdarbeit-letzter-lauf.log` |

**Warum es zwei Sicherungen gibt:** `G:`, `H:` und `I:` sind dieselbe physische
Platte (Disk 2, siehe [[Hardware]]). Eine zweite Kopie dort hätte nichts
gewonnen. Die Zweitkopie liegt deshalb auf `O:` (Disk 1) und enthält den
unersetzlichen Teil ohne die Medienlast — 7,1 GB in 13.767 Dateien, gemessen
**8 Sekunden** (intern über NVMe). Videos, Musik, Software und Posteingang
(35,8 GB) bleiben draußen; sie stehen weiterhin in der Hauptsicherung auf `G:`.

## Die Zweitkopie: Ziel ist J:, nicht O:

**Korrektur des Ziels am 07.09.2026.** Der Kopf des Skripts
`sichern-zweitkopie.ps1` sagt „nach O:“, die Tabelle oben auch — **das
tatsächliche Ziel ist `J:\\MaxHirn-Zweitkopie`** (Zeile `$ziel = 'J:\\MaxHirn-Zweitkopie'`),
und das ist gewollt: J: ist die externe WD-My-Book-Sicherungsplatte, auf der
die Zweitkopie physisch getrennt von G: liegt. Die Notizen in
[[Dashboard]]/[[Routinen]], die „O:“ nennten, bezogen sich auf den früheren
Zustand. **O: ist seit dem 06.09.2026 durch die Archiv-Junctions belegt** und
steht für die Zweitkopie nicht mehr zur Verfügung.

Der Lauf vom 06.09.2026 21:07 (robocopy-Code 3, 635 „Extras“) war daher kein
Fehler: Das Skript lief zum ersten Mal gegen das J:-Ziel und räumte dort
(155 MB) Altbestand weg. Der Zielpfad in Code und Kommentar bleibt J:.

**Was das für die Routine bedeutet:**

| | |
|---|---|
| Ziel | `J:\\MaxHirn-Zweitkopie` (gewollt, bestätigt 07.09.2026) |
| Warum nicht O: | O: ist seit 06.09.2026 durch Archiv-Junctions belegt |
| Achtung | J: (WD My Book) hat 479 unkorrigierte Lesefehler — siehe [[Hardware]]. Die Zweitkopie liegt damit auf einer angeschlagenen Platte. |

## Die dritte Kopie: außer Haus

`sichern-ausser-haus.ps1` → `Q:\MaxHirn-AusserHaus` (SanDisk Portable SSD,
Disk 3, exFAT, 1,86 TB, Label `musik_lib`). Das Ziel war bis 12.09.2026 `E:`
(Netac MobileDataStar) — Platte gewechselt, das Skript folgt seitdem `Q:`.
Bestand und Dauer stehen im Protokoll
`Routinen/logs/ausserhaus-kopie-letzter-lauf.log`.

**Seit 29.09.2026 wird sie erneuert, sobald die Platte angesteckt ist**
(Aufgabe `MaxHirn-Ausserhaus-Kopie`, täglich 21:30 über
`Routinen/ausserhaus-kopie.ps1`): angesteckt → Kopie läuft; nicht angesteckt →
nach Sekunden Exitcode 2 „übersprungen", keine Meldung, kein Fehlschlag.
Zweiter Wächter: `Agenten/Hermes/scripts/ausserhaus-frist-wache.py`
(Hermes-Cron `ausserhaus-frist-wache`, täglich 08:00) meldet, wenn die jüngste
Spur im Ziel **älter als 14 Tage** ist — dann wurde die Platte lange nicht
angesteckt.

Handarbeit bleibt das Eigentliche: Platte anstecken → kopieren lassen (oder von
Hand starten) → „Hardware sicher entfernen" → **außer Haus bringen**. Eine
Kopie, die dauerhaft am Rechner hängt, ist keine Kopie außer Haus — genau der
Fall, gegen den sie schützt, ist der Netzteilschaden, der 2026 mehrere Platten
gleichzeitig getötet hat. Sie nimmt **alles** mit, nicht nur den Kern; Platz ist
genug.

**exFAT braucht `/FFT`.** `E:` ist exFAT formatiert, und exFAT speichert
Zeitstempel in 2-Sekunden-Schritten, NTFS in 100-Nanosekunden-Schritten. Ohne
`/FFT` gilt jede Datei bei jedem Lauf als verändert, und es würden jedes Mal
46 GB neu geschrieben statt nur der Unterschied. Für den laufenden Vault wäre
exFAT ungeeignet (siehe [[Portabilitaet]]), für eine reine Kopie ist es
unproblematisch — es läuft keine Datenbank darauf.

⚠️ **Auf der SSD liegen Klartext-Zugangsdaten** (`Wissen/Zugaenge.md`). Eine Platte außer Haus kann verloren gehen oder gestohlen
werden — anders als eine im Rechner. **Wer sie findet, liest sie: die Kopie bleibt bewusst unverschlüsselt**
(Entscheidung Max, 30.09.2026 — kein BitLocker To Go). Damit hängt die Vertraulichkeit allein am Ort:
die SSD gehört außer Haus an einen Platz, an den kein Dritter kommt. Siehe [[Zugaenge]] und [[Passwoerter-Quarantaene]].

`OKX_API.env` steht seit dem 12.09.2026 nicht mehr in dieser Aufzählung: die
Datei lag im Archiv-Posteingang und wurde bei jedem Lauf mitkopiert, dazu lag
eine zweite Fassung auf `J:`. Beide Streukkopien sind weg; die Datei liegt jetzt
in `Wissen/OKX_API.env` neben der Schlüsselablage. Dass sie damit auf derselben
Platte außer Haus steht, ist hingenommen: dieselben Schlüssel stehen in
`Zugaenge.md` ohnehin im Klartext.

Die Wrapper gibt es aus drei Gründen:

1. **Eine geplante Aufgabe hat kein Fenster.** Ohne Protokoll bliebe ein
   Fehlschlag unbemerkt. Jedes Protokoll enthält genau den letzten Lauf.
2. **Robocopy wirft keine Ausnahme, es meldet über den Exitcode.** Der erste
   Entwurf schrieb „ENDE ok", während die Sicherung mit Code 11 gescheitert war
   (23.08.2026). Der Wrapper prüft jetzt `$LASTEXITCODE` und reicht ihn weiter,
   `sichern.ps1` beendet bei Code ≥ 8 selbst mit `exit 1`.
3. **Sie benutzen `$PSScriptRoot`**, keine absoluten Pfade — der Vault bleibt
   umzugsfähig.

Alle drei sind mit **„Starten, sobald möglich"** angelegt. Das ist wegen der
[[Hardware]]-Abschaltungen wichtig: Ohne diese Einstellung fällt ein verpasster
Termin ersatzlos aus.

**Warum das Protokoll vom Sicherungslauf ausgeschlossen ist:** `Routinen/logs`
liegt im Vault und damit im Sicherungspfad. Robocopy kann die gerade
beschriebene Protokolldatei nicht kopieren und beendet mit Code 11 — deshalb
steht `logs` in der `/XD`-Liste von `sichern.ps1`.

### Nach einem Umzug auf die SSD

Die Wrapper ziehen mit, die **Registrierung nicht** — sie enthält den absoluten
Pfad. Danach also einmal neu anlegen (`Register-ScheduledTask`, Zeiten wie oben).
Prüfen mit `Get-ScheduledTask -TaskName 'MaxHirn-*'`, entfernen mit
`Unregister-ScheduledTask -TaskName 'MaxHirn-Sicherung'`.

## DCA-Prüfung: warum nicht über `/schedule`

`/schedule` legt **Cloud-Agenten** an. Die laufen nicht auf diesem Rechner und
hätten daher weder Zugriff auf `Handel/plan.json` noch auf die
`onchainos`-Anmeldung im lokalen Schlüsselspeicher. Für diese Routine ist die
**Windows-Aufgabenplanung** der richtige Weg:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\MaxHirn\Handel\.venv\Scripts\python.exe"
$arg = "$env:USERPROFILE\Documents\BrainFiles\MaxHirn\Handel\agent.py check"
schtasks /create /tn "DCA-Faelligkeit" /tr "$exe $arg" /sc daily /st 09:00
```

`check` schweigt, wenn nichts ansteht — eine Routine, die täglich „nichts zu tun"
meldet, wird nach einer Woche ignoriert.

**Die Routine löst nichts aus.** Sie meldet nur Fälligkeit; Quote holen,
vorlegen und ausführen bleibt ein bewusster Schritt von Hand. Das entspricht der
Regel in den globalen Arbeitsanweisungen: aus einem Zeitplan heraus wird nie
gehandelt.

## Marktscanner: warum die Routine nur Papier handelt

Der [[Marktscanner]] darf als einziger Agent im Rahmen fester Grenzen selbst
handeln (Ausnahme in [[Schutzregeln]]). Die **Routine** nutzt das nicht:
`marktscanner.ps1` ruft `handeln.py` ohne `--live` auf. Scharfhandel bleibt ein
bewusster Aufruf von Hand — dieselbe Regel wie bei der DCA-Prüfung, aus einem
Zeitplan heraus wird nie echtes Geld bewegt. Die Routine liefert also täglich
die Rangliste und einen Papier-Handelseintrag; mehr nicht.

**Eingeplant am 02.09.2026** als `MaxHirn-Marktscanner`, täglich 07:30. Zum
Wiederanlegen nach einem Umzug:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\marktscanner.ps1"
schtasks /create /tn "MaxHirn-Marktscanner" /sc daily /st 07:30 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

`schtasks` setzt **kein** „Starten, sobald möglich" — die drei Handels-Aufgaben
sind deshalb mit `Register-ScheduledTask` und
`New-ScheduledTaskSettingsSet -StartWhenAvailable` angelegt. Ohne das fällt ein
verpasster Termin nach einer [[Hardware]]-Abschaltung ersatzlos aus.

### Wachen-Abgleich: die fünf Bedingungen für unbeaufsichtigten Betrieb

[[Schutzregeln]] bindet den automatischen Handel seit dem 01.09.2026 an fünf
messbare Bedingungen. Vier davon prüft `handeln.py` bei **jedem** Lauf mit
(Freigabe, Drawdown-Ratsche, Herzschlag-Notausstieg, Journal-Spiegelung); die
fünfte — der rollierende Erwartungswert über die letzten 30 Runden — braucht
einen eigenen, selteneren Lauf, damit ein einzelner schlechter Tag die Spur
nicht sofort abschaltet. Dafür `handel-wachen.ps1`, **eingeplant am 02.09.2026**
als `MaxHirn-Handel-Wachen`, sonntags 08:00:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\handel-wachen.ps1"
schtasks /create /tn "MaxHirn-Handel-Wachen" /sc weekly /d SUN /st 08:00 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

Der Lauf legt `handel_erlaubt` **nie** auf `true` — er schließt die Sperre nur,
wenn der Erwartungswert negativ oder der Kill-Switch erreicht ist. Scharfschalten
bleibt ein Schritt von Hand. Der `xperp`-Bot hat kein Gegenstück: er führt nichts
aus und kein Journal, `bot.py wachen` zeigt nur die hinterlegten Grenzen.

Seit 02.09.2026 deckt derselbe Wrapper **beide** Live-Spuren ab: erst
`scanner/handeln.py --wachen`, dann `kraken/handeln.py --wachen`, jede mit
ihrer eigenen `wachen.json` und ihrer eigenen Währung. Ein zweiter Zeitplan ist
dafür nicht nötig.

### Der Dauerlauf — 24/7, aber nicht scharf

Angelegt am 03.09.2026 auf Max' Anweisung. `handel-dauerlauf.ps1` startet
`Handel/dauerlauf.py`: Befehle vom Handy sofort, ein Zyklus alle 15 Minuten,
Tagesbericht einmal täglich ab 08:00. **Er ersetzt die Tagesroutinen nicht**,
er legt sich darüber — `marktscanner.ps1` und `kraken-scanner.ps1` rechnen
deshalb weiterhin die Ranglisten der beiden Scanner-Spuren.

**Stille Spuren namentlich (Auftrag Max, 21.09.2026).** Der Tagesbericht nennt
neben der Sammelzeile ("N Spuren still: ...") jede stille Spur EINZELN, mit dem
Alter ihrer letzten **Buchung** und ihrem `handel_erlaubt`:

    Kraken-Futures (USD) (papier)  letzte Buchung vor 1 Tag(en)
    Omniquant (papier)             letzte Buchung vor 4 Tag(en)
    ORB-Kraken (Papier)            noch kein Handel (Journal traegt nur Kurse)
    SuperTrend (Indikator)         kein Journal

Buchung heisst kauf/verkauf/eroeffnen/schliessen/EINSTIEG/AUSSTIEG. Die
`zyklus`-Zeilen der Nautilus-Arme (Bid/Ask-Sammlung) zaehlen ausdruecklich
NICHT - sonst gaelte eine Spur als frisch beschaftigt, die seit Wochen nicht
handelt. Ein geteilter `schluessel` wird ausgeschrieben: beide Kraken-Arme
tragen `nautilus_kraken`, in der Sammelzeile stand deshalb zweimal derselbe
Name. Werkzeug: `tagesbericht.sammelzeile` / `stillblock` / `letzte_buchung`,
Tests `Handel/tests/test_stille_spuren.py`.

**Je Spur ein Schreiber (14.09.2026).** Der Dauerlauf führt seit dem
14.09.2026 auch die Kraken-Spur (sie war vom 03.09.2026 bis dahin stillgelegt);
ihre Rangliste kommt weiter aus der Tagesroutine, gehandelt wird nur im Takt.
Dieselbe Regel wurde für die zwei übrigen Alt-Aufrufe durchgesetzt:
`marktscanner.ps1` und `kraken-scanner.ps1` rufen `handeln.py` **nicht mehr**
auf (beide Wrapper haben stattdessen eine Sperre — solange der Dauerlauf lebt,
steigen sie mit einer Logzeile aus), und `MaxHirn-XPERP-Spur2` ist gelöscht.
Anlass war ein Befund vom 14.09.2026: der 07:50-Aufruf dieser Aufgabe hatte
einen vollständigen Zyklus gefahren — im Journal sichtbar, im Dauerlauf-Log
nicht, weil er zu keinem Zyklus gehörte. Zwei Schreiber auf denselben Zustand
machen jede Zustandsaussage mehrdeutig.

**Auch dieser Zeitplan legt keinen Schalter um.** Ohne offenes Zeitfenster aus
[[Handelsregeln]] läuft jeder Zyklus als Papierhandel. Freigegeben wird per
Telegram, auf Anfrage, höchstens 24 Stunden.

Zwei Auslöser, weil die Kernel-Power-41-Abschaltungen aus [[Hardware]] den
Rechner ohne Vorwarnung mitnehmen: einer bei der Anmeldung, einer alle
30 Minuten als Wächter. Der zweite prüft `dauerlauf.pid` und endet sofort,
wenn schon einer läuft — zwei Dauerläufe auf demselben Telegram-Token nehmen
sich gegenseitig die Nachrichten weg (Telegram antwortet dem zweiten Abrufer
mit 409).

**Eingeplant am 07.09.2026** als `MaxHirn-Handel-Dauerlauf` (bei Anmeldung)
und `MaxHirn-Handel-Dauerlauf-Waechter` (alle 30 Minuten):

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\handel-dauerlauf.ps1"
schtasks /create /tn "MaxHirn-Handel-Dauerlauf" /sc onlogon `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
schtasks /create /tn "MaxHirn-Handel-Dauerlauf-Waechter" /sc minute /mo 30 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

Der Wächter prüft `dauerlauf.pid` und endet sofort, wenn schon einer läuft;
nach einem Kernel-Power-41-Neustart ([[Hardware]]) startet er den Dauerlauf
wieder. Der Dauerlauf selbst läuft seit 06.09.2026 17:37 (PID 55000, Takt
15 min) und protokolliert in `Routinen/logs/handel-dauerlauf-letzter-lauf.log`.

**Die beiden Stufen-Wächter hingen an der Anmeldung (behoben 29.09.2026).**
Bei der Basisstufe sind die Rollen getrennt: `MaxHirn-Handel-Dauerlauf` startet
bei Anmeldung, der Wächter belebt zeitgesteuert wieder. Für mittel und hoch
gibt es keine eigene Startaufgabe — dort macht die Wächteraufgabe beides und
trug deshalb nur einen `LogonTrigger`. Die Startrolle war damit erfüllt, die
Wiederbelebung nicht: „Nächster Lauf" stand bei beiden leer, und
`StartWhenAvailable` half nicht, weil es nur für **zeitbasierte** Auslöser
gilt. Folge: nach einem Kernel-Power-41-Neustart ohne Anmeldung ([[Hardware]])
kam der Basislauf zurück, mittel und hoch blieben still liegen — ohne Meldung,
weil `melder.py` nach Zeitplan sendet und nicht nach Zustand.

Behoben, indem beide zusätzlich einen Zeitauslöser bekamen (alle 30 Minuten,
unbegrenzt). Der `LogonTrigger` bleibt: er ist der Anmeldungsstart, nicht
Beiwerk.

```powershell
foreach ($n in 'MaxHirn-Handel-Dauerlauf-Mittel-Waechter','MaxHirn-Handel-Dauerlauf-Hoch-Waechter') { $alt = @((Get-ScheduledTask -TaskName $n).Triggers); $neu = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 30); Set-ScheduledTask -TaskName $n -Trigger ($alt + $neu) }
```

Nachweis: `Get-ScheduledTaskInfo` zeigt für alle drei Wächter einen gefüllten
`NextRunTime`. Ein Probelauf von Hand schrieb „laeuft bereits (PID 8244, Stufe
mittel) - nichts zu tun" und ließ den Prozess unangetastet — der Auslöser
greift, ohne den laufenden Handel zu stören.

**Die Sperrdatei trägt jetzt zwei Felder (29.09.2026).** Die wiederbelebte
Wächteraufgabe hätte an einer zweiten Stelle wieder versagen können:
`dauerlauf.pid` enthielt nur eine Prozessnummer, und Windows vergibt Nummern
wieder. Trüge nach einem Neustart irgendein fremder Python-Prozess die alte
Nummer, meldete der Wächter dauerhaft „laeuft bereits" und startete nie mehr —
die Lücke hätte genau die Wiederbelebung ausgehebelt, die oben in Gang gebracht
wurde. Seither steht in der Datei `<PID> <Startzeit>`; eine wiederverwendete
Nummer hat eine andere Startzeit und fällt auf. Das erste Feld bleibt die nackte
Nummer, damit eine alte Datei lesbar bleibt.

Zugleich prüft `dauerlauf.py` die Sperre selbst und schreibt sie selbst. Vorher
tat das nur `handel-dauerlauf.ps1`: ein von Hand gestarteter `python
dauerlauf.py` ging daran vorbei und war für den Wächter unsichtbar — so entstand
am 15.09.2026 der Doppellauf auf denselben Dateien. Die Regel dabei lautet **im
Zweifel starten**: unlesbare Datei, verweigerter Zugriff, jeder Fehler gilt als
„nicht belegt". Ein Lauf, der fälschlich nicht startet, fällt niemandem auf,
weil `melder.py` nach Zeitplan sendet und nicht nach Zustand. Begründung im Kopf
von `Agenten/Handel/sperre.py`, Nachweis in `tests/test_sperre.py`.

### Der Telegram-Melder — eine Quelle, nicht zwei

Seit 07.09.2026 sind `TELEGRAM_TOKEN` und `TELEGRAM_CHAT_ID` als
Benutzervariablen gesetzt; ein Testversand an den Gruppenchat ist angekommen.
Damit sendet der Dauerlauf, was er ohnehin konnte.

**Der Tagesbericht braucht keine eigene Aufgabe.** `dauerlauf.py` prüft in
jedem Durchlauf, ob heute schon ein Bericht raus ist, und sendet ihn beim
ersten Durchlauf ab 8 Uhr selbst (`dauerlauf.py`, Abschnitt „Tagesbericht
faellig?"). Am 07.09.2026 wurde daneben eine zweite Aufgabe
`Tagesbericht-Telegram` angelegt, die dasselbe um 08:00 getan hätte — sie ist
noch am selben Tag wieder entfernt worden. **Zwei Quellen für denselben Bericht
sind kein doppelter Schutz, sondern zwei Stellen, an denen er falsch werden
kann.** Wer den Bericht ändern will, ändert `tagesbericht.py`.

**Ein Neustart nach dem Setzen ist nicht nötig — `melder.py` löst das selbst.**
Eine per `setx` oder `SetEnvironmentVariable(…, "User")` gesetzte Variable
erreicht laufende Prozesse nicht; `melder.py` liest deshalb bei **jedem**
Aufruf zuerst `os.environ` und fällt dann auf `HKCU:\Environment` zurück
(`_aus_registry`, denselben Umweg gehen `okxf.py`, `okx.py` und `kraken.py`).
Der laufende Prozess greift die neuen Werte also innerhalb eines Taktes von
selbst ab.

Das ist am 07.09.2026 im Protokoll zu sehen: Der Dauerlauf startete 23:24:11
mit „Melder nicht eingerichtet" — zu dem Zeitpunkt stimmte das —, und ab
23:29:54 nahm derselbe Prozess Befehle aus dem Chat entgegen, ohne dass er
neu gestartet worden wäre. **Die Startzeile ist eine Momentaufnahme, kein
Dauerzustand;** wer sie als „der Melder läuft nicht" liest, startet einen
Handelsprozess ohne Grund neu.

⚠️ **Der Bot-Token stand beim Einrichten im Klartext in Shell-Befehlen.** Am
07.09.2026 wurde er mehrfach direkt in Aufrufe geschrieben, statt einmal
gesetzt und danach nur noch als `$env:TELEGRAM_TOKEN` referenziert zu werden.
Nachgemessen am selben Tag, wo er tatsächlich gelandet ist:

| Ort | Vorkommen |
|---|---|
| PowerShell-History (`ConsoleHost_history.txt`) | **0** — PSReadLine schreibt nur interaktiv Getipptes, keine Tool-Aufrufe |
| `BrainFiles/` und damit die Sicherungen auf `G:` und `J:` | **0** |
| Sitzungsprotokoll unter `~/.claude/projects/*.jsonl` | 11, in einer Datei |

**Die Sicherungen sind sauber, und das ist der Punkt, auf den es ankommt.**
Ein Schlüssel, der in den Vault gerät, wandert mit jedem Lauf auf zwei weitere
Platten und ist dort praktisch nicht mehr einzufangen; ein Schlüssel im
Sitzungsprotokoll liegt in einer einzigen Datei im Benutzerprofil, die nicht
gesichert wird ([[KI-Ablagen-im-Benutzerordner]]).

Rotieren bleibt trotzdem der saubere Abschluss — `/revoke` bei BotFather,
danach `setx TELEGRAM_TOKEN`, kein Neustart nötig. Es kostet zehn Sekunden und
macht jede verbliebene Kopie wertlos. Der Schaden wäre ohnehin begrenzt: Mit
dem Token kann man in den Gruppenchat schreiben und mitlesen, aber
Handelsbefehle nimmt der Dauerlauf nur von `TELEGRAM_CHAT_ID` an, und Geld
bewegt keiner damit.

**Die Lehre ist nicht „Token nie anfassen", sondern: einmal setzen, danach nur
noch referenzieren.** `melder.py` liest ihn ohnehin selbst aus der Registry —
er hätte nie in einen Aufruf gehört.

### Kraken-Spur 3: derselbe Zuschnitt, andere Börse

Seit 02.09.2026 gibt es eine dritte bewachte Spur ([[Handelsregeln]]):
Kraken, Spot, nur Long, in EUR. Auch sie handelt aus dem Zeitplan heraus **nur
auf Papier** — `kraken-scanner.ps1` ruft `handeln.py` ohne `--live`, und selbst
mit `--live` blieben mehrere Sperren zu. **Eingeplant am 02.09.2026** als
`MaxHirn-Kraken-Spur3`, eine Viertelstunde nach dem Marktscanner, damit sich
die beiden Läufe nicht überschneiden:

```powershell
$exe = "$env:USERPROFILE\Documents\BrainFiles\Agenten\Routinen\kraken-scanner.ps1"
schtasks /create /tn "MaxHirn-Kraken-Spur3" /sc daily /st 07:45 `
  /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$exe`""
```

## Einplanen

In einer interaktiven Claude-Code-Sitzung:

```
/schedule
```

Dort Zeitplan und Prompt angeben, z. B. Prompt `/tagesbriefing`, Zeitplan
werktags 08:00. Danach oben in der Tabelle den Status ändern.

## Warum Tagesbriefing und Wochenrückblick noch warten

Die beiden gehören zu einer anderen Sorte als die drei eingeplanten: Sie
**starten eine Claude-Sitzung ohne dich davor**, während Sicherung, Posteingang
und DCA-Prüfung nur ein Skript ausführen und ein Protokoll hinterlassen. Ein
Tagesbriefing um 8 Uhr produziert eine leere Seite, solange [[Profil]] Lücken
hat und Verbindungen aus [[Verbindungen]] nicht authentifiziert sind. Erst
füllen, dann automatisieren.

## Zwischenstand: warum stündlich (wieder, seit 29.09.2026) und auf einem eigenen Branch

Die vier Sicherungen oben halten alle nur den **jetzigen** Stand, und Git hält
nur, was **committet** ist. Zwischen dem Schreiben einer Datei und ihrem Commit
liegt ein Fenster, in dem die Arbeit nirgends gesichert ist — bei mehreren
gleichzeitigen Sitzungen (Claude-Chats, Hermes) ist genau das das Risiko, siehe
[[Schutzregeln]], Abschnitt „Mehrere Sitzungen gleichzeitig".

`Routinen/zwischenstand.ps1` schließt dieses Fenster, ohne etwas anzufassen,
woran gerade jemand arbeitet:

- **Eigener Index** über `GIT_INDEX_FILE`. Eine Sitzung, die gerade selektiv
  `git add` gemacht hat, verliert ihre Vormerkung nicht.
- **Commit über `git commit-tree`** direkt auf den Branch `zwischenstand`.
  `HEAD`, `master` und der Arbeitsbaum werden nie angefasst.
- **Kein `checkout`, `reset`, `stash` oder `clean`.** Es wird ausschließlich
  geschrieben, nie verworfen.
- Ändert sich nichts, entsteht auch kein Commit.

Gemessen am ersten echten Lauf (25.08.2026): **4 Sekunden**, `HEAD`, `master`,
Arbeitsbaum und der normale Index (per SHA-256 verglichen) blieben unverändert.
Der Lauf sicherte 61 Zeilen an `Wissen/Hermes.md`, die eine andere Sitzung
uncommittet liegen hatte, sowie ein noch unversioniertes Skript.

**Autor der Commits ist `Routine Zwischenstand`**, nicht Max und kein Agent —
die Historie soll nicht behaupten, jemand hätte diese Arbeit getan.

Eine Datei zurückholen:

```
git log --oneline zwischenstand
git checkout <commit> -- <pfad>
```

Der Branch wächst mit jedem Lauf. Aufräumen, wenn er stört:
`git update-ref -d refs/heads/zwischenstand` — die Commits sind danach nicht
mehr erreichbar und verschwinden bei der nächsten Garbage Collection.

**Zugangsdaten sind nicht betroffen:** Die `.gitignore` ist eine Whitelist,
`Zugaenge.md`, `.env`, `.pem`, `.pfx`, `.p12`, `.kdbx` und `*_key.txt` bleiben
auch hier draußen. Geprüft am 25.08.2026 gegen den ersten Zwischenstand-Commit.

## Fremdarbeit übernehmen: ruhende Hintergrundarbeit in die Hauptarbeit

Der Zwischenstand oben **sichert** fremde Arbeit, er holt sie aber nicht in die
Hauptarbeit: sie bleibt als „Fremdarbeiter“ im Arbeitsbaum stehen (als `M` oder
`??` in jedem `git status`), und die Historie von `master` weiß nichts davon.
Genau das war der Dauerzustand — Hintergrund- und Parallel-Sitzungen (Subagenten,
Bots, Desktop-, CLI- und Telegram-Sitzungen) schreiben in denselben Baum und
committen ihre Arbeit oft nicht.

`Routinen/fremdarbeit-einziehen.ps1` (Aufgabe `MaxHirn-Fremdarbeit-Einziehen`,
stündlich zu :20, also **nach** dem jeweiligen Zwischenstand) schließt das:

- Es nimmt **nur ruhende** Änderungen — länger als 30 Minuten unberührt (dieselbe
  Schwelle wie in [[Schutzregeln]] und `arbeitsbaum-pruefen.ps1`). Was eine
  laufende Sitzung gerade schreibt, bleibt liegen.
- Es schreibt **einen** Commit mit dem Autor `Andere Sitzung <fremd@local>` — im
  Text steht, dass es eine Übernahme ist und welche Pfade sie umfasst, damit die
  Historie nicht behauptet, jemand hätte diese Arbeit getan.
- Es fasst den Arbeitsbaum nie an: eigener Index über `GIT_INDEX_FILE`,
  `git commit-tree`, dann `git update-ref` **mit Alt-Wert**. Bewegt eine andere
  Sitzung `master` währenddessen, bricht der Lauf ab statt zu überschreiben.
- Es ist bei jedem Zweifel lieber zu spät als zu früh: liegt `.git/index.lock`
  (eine andere Sitzung committet), wird der Lauf übersprungen; eine gelöschte
  Datei gilt nur dann als ruhend, wenn auch ihr **Ordner** alt ist (eine
  Löschung schreibt die Ordnerzeit fort — sonst würde die Aufräumarbeit einer
  laufenden Sitzung sofort übernommen).

Nach dem Commit zieht das Skript den **normalen Index** für die übernommenen
Pfade nach: sonst stünden sie in `git status` gleichzeitig als gelöscht und als
ungetrackt, und ein `git commit` einer anderen Sitzung ohne Pfadangabe (es
committet den ganzen Index) würde sie wieder aus `master` löschen. Dieselbe
Reparatur läuft zu Beginn jedes weiteren Laufs für die letzten eigenen
Übernahme-Commits — nachweisbare Herkunft statt Raten, idempotent.

Nachsehen:

```
powershell -File Agenten/Routinen/fremdarbeit-einziehen.ps1 -Testlauf   # was wuerde uebernommen
git log --oneline --author=fremd@local                                  # was uebernommen wurde
```

Geprüft am 21.09.2026: erst auf einer Probe (eigenes Repo unter
`Agenten/Hermes/cache/probe-fremdarbeit-*` mit geänderter, neuer, gelöschter und
bereits vorgemerkter Datei plus einer frischen, die liegen bleiben muss), dann am
echten Baum — vier Läufe, 36 Pfade übernommen, danach kein Phantomeintrag im
Index; in der Probe blieb frische Arbeit liegen und eine vorgemerkte fremde
Änderung unangetastet. Der Lauf über die Aufgabenplanung wurde mit Ergebniscode 0
gemessen.

**Was die Regel in [[AGENTS]] nicht ersetzt:** die 10-Minuten-Regel dort gilt für
Sitzungen, die selbst committen. Diese Routine ist der Nettofang für alles, was
trotzdem liegen bleibt.

## Grenzen

- Eine Routine läuft nur, wenn der Rechner an ist. Für echten Dauerbetrieb
  bräuchte es einen Server — bewusst zurückgestellt.
- Routinen, die Mails senden oder öffentlich posten, immer als Entwurf enden
  lassen, nicht als Versand.

## Ausnahme: Docker-Daten liegen im Vault

`MaxHirn/DockerDesktopWSL` traegt zwei VHDX-Dateien (4,88 GB: 
`disk/docker_data.vhdx` 4.896 MB + `main/ext4.vhdx` 96 MB) und wird von der 
Sicherung nach `G:` mitgenommen - nachgemessen am 07.10.2026: 
`G:\MaxHirn-Sicherung\MaxHirn\DockerDesktopWSL` enthaelt genau diese zwei Dateien.

**Entscheidung (Max, 07.10.2026): bewusst liegen lassen.** Die Alternative waere, den 
Datentraeger-Ort im Docker Desktop zu verlegen - das verlangt einen Docker-Neustart, und 
zu diesem Zeitpunkt laufen `nautilus-demo`, `freqtrade-*` und `openterminalui-*`. 
Ein Umzug im laufenden Betrieb ist das groessere Risiko als 4,88 GB in der Sicherung.

Wenn Docker einmal ohnehin steht (Neustart, Update), ist der Umzug nachzuholen: 
Docker Desktop > Settings > Resources > Advanced > Disk image location. Danach 
`MaxHirn/DockerDesktopWSL` loeschen und die naechste Sicherung ist 4,88 GB kleiner.
