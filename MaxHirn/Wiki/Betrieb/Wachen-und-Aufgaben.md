---
id: 20260921-wachen-und-aufgaben
title: 'Betrieb — Wachen und geplante Aufgaben'
tags: [betrieb, wachen]
created: 2026-09-21
updated: 2026-09-23
related: ['[[Betrieb/Hermes]]', '[[Handel/Gates-und-Freigabe]]']
summary: 'Zwei Scheduler (Windows-Aufgabenplanung und Hermes-Cron), das Wachen-Muster, und die Frage, die man vor jeder Wache stellt.'
---

# Wachen und geplante Aufgaben

## Zwei Scheduler — nicht verwechseln

| Scheduler | Wofuer | Beispiel |
|---|---|---|
| Windows-Aufgabenplanung (`MaxHirn-*`) | Dauerlaeufe, Sicherungen, Fensteraufgaben | `MaxHirn-Handel-Dauerlauf`, `MaxHirn-OmniRoute`, `MaxHirn-Handelszentrale` |
| Hermes-Cron (`no_agent`) | Wachhunde, die eine Nachricht schicken sollen | `bus-waechter` (15 min), `moondev-agenten-wache` (15 min), `nautilus-runden-wache` (30 min), `one-wache` (10 min), `breite-wache` (taeglich 19:00), `ausserhaus-aufgabe-sichern` (taeglich 08:30) |

Hermes-Cron laeuft **am Bus vorbei** und liefert direkt nach Telegram — genau deshalb
darf eine Wache nicht ueber den Weg melden, den sie ueberwacht.

## Das Wachen-Muster

1. **Leere Ausgabe = nichts senden.** Der Job schreibt nur, wenn etwas nicht stimmt.
2. **Wache fragt den Zustand ab, nicht die Absicht.** Beispiel Gateway: Port pruefen,
   nicht den Prozessnamen raten; Beispiel Dauerlauf: Alter des letzten Zyklus im Journal.
3. **Gnadenfrist** nach Neustart einbauen (Boot 120 s, Zyklus 15 min), sonst meldet die
   Wache ihren eigenen Neustart als Stoerung.
4. **Erst fragen: hat der Dienst ueberhaupt eine Wache?** Der Telegram-Bus hatte keine —
   er war vom 11.09. bis 15.09. aus, die Routinen schrieben weiter ins Journal, niemand
   bekam Meldungen. Vier Tage unbemerkt.

## Windows-Aufgaben: Fallen

- **`IgnoreNew` fehlt → Instanzen wachsen.** Am 16.09.2026 liefen vier Dauerlaeufe
  gleichzeitig (drei niedrig, eine mittel) = zwoelf Spur-Laeufe je Viertelstunde, bei
  offenem Fenster echtes Doppelorder-Risiko. Belegquellen vor jeder Doppellauf-Meldung:
  `Get-ScheduledTask` der drei Aufgaben plus Instanzen mit Startzeit und Eltern-PID.
  Ein venv-Start ist Launcher + Kind — kein Doppellauf.
- **Nie per Prozessname beenden**, nur per PID, und vorher `freigabe_fenster.json` pruefen.
- **Fenster verstecken:** Routine-Aufgaben mit `-WindowStyle Hidden` in der Action
  registrieren, sonst flackert alle 30 min ein PowerShell-Fenster (die Python-Tools
  `pythonw`/`wscript //B` sind von sich aus fensterlos).
- **Logs sind die Belegquelle:** `Agenten/Routinen/logs/*.log`, Zeile „ENDE FEHLER",
  plus `Get-ScheduledTaskInfo`.
- **Admin-Aufgaben** (Disable-/Register-ScheduledTask): Elevation selbst anstossen
  (`Start-Process -Verb RunAs -Wait`), danach **Zustand verifizieren** und ein Beleg-Log
  schreiben. Der Task `Hermes_Gateway` liess sich so nicht deaktivieren
  (HRESULT 0x80070005) — Zustand nachlesen, nicht annehmen.
- **Eine Aufgabe NICHT aus der Sandbox anlegen** (30.09.2026): `Register-ScheduledTask`
  meldete dort zweimal „Ready" samt naechstem Lauf — im naechsten Aufruf war die Aufgabe
  weg. Die Sandbox hat eine eigene Sicht auf `C:\Windows\System32\Tasks` (dort standen
  keine `MaxHirn-*`-Dateien, waehrend `schtasks /query` die 25 Host-Aufgaben zeigte).
  Anlegen deshalb **aus dem Gateway heraus** (Hermes-Cron, `no_agent`) und mit
  `schtasks /create /xml` (XML in UTF-16LE); pruefen mit `schtasks /query`, starten mit
  `schtasks /run`. Vorbild: `Agenten/Hermes/scripts/ausserhaus-aufgabe-sichern.py`.
- **`Get-ScheduledTask -TaskName <name>` ist kein Beleg** — es findet in dieser Umgebung
  auch **vorhandene** Aufgaben nicht (`HRESULT 0x80070002`). Verlaesslich sind die
  Aufzaehlung (`Get-ScheduledTask | Where-Object TaskName -like 'MaxHirn-*'`) und
  `schtasks /query /tn <name>`. Also: eine Aufgabe erst im **zweiten** Aufruf als
  angelegt betrachten, nie in dem, der sie angelegt hat.

## Dauerprozess-Muster

- Treiber startet Kinder, ueberwacht sie, raeumt **vor** jedem Spawn Waisen auf
  (>300 s Schonfrist), beendet beim Sterben der Wurzel den ganzen Baum (`taskkill /T /F`).
  Ohne das: der 84-Prozess-Leak vom 21.09.2026 (siehe [[Lektionen/Windows-Umgebung]]).
- Neustartabstand nicht zu kurz: `PAUSE_NEUSTART` 120 s, sonst haemmert der Treiber gegen
  Rate Limits der Datenanbieter und erzeugt selbst die Abstuerze, die er beheben will.

## Herzschlag misst die SPUR, nicht den Live-Pfad (22.09.2026)

Der Herzschlag (Bedingung 3) ist das Alter des letzten Zyklus. Er darf NICHT aus
dem Live-Buch-Zustand kommen: den schreibt nur der Live-Pfad, der Live-Pfad laeuft
nur bei offenem Freigabefenster, und das Fenster oeffnet `AUTO_FREIGABE` nur, wenn
als EINZIGER Grund das Fenster fehlt. Eine Spur, die lange nicht live lief, meldet
dann fuer immer "Herzschlag alt" und kann sich nie selbst scharf machen.

Richtig ist der Zustand, den der LAUFENDE Zyklus schreibt (bei einer Spur mit
eigenem Live-Buch also `<spur>/zustand.json`, nicht `zustand.live.json`) - ueber
`risikostufe.datei()` stufenrichtig. Belegter Fall: `moondev_marktlage` nannte vor
der Aenderung zwei Gruende, danach genau einen ("Freigabefenster nicht offen") -
erst damit greift die Auto-Freigabe.

**Prueffrage bei jeder neuen Live-Spur:** nennt die Vorschau mit `MAXHIRN_ROUTINE=1`
genau EINEN Grund und enthaelt er das Wort "Freigabefenster"?

## Ein Merker braucht eine Wache (23.09.2026)

`scanner/zustand.json` trug 23 Kopien DESSELBEN Notausstiegs-Stops; jede Live-Runde
meldete `offener Stop ... bleibt liegen: OKX 50014`. Aufgefallen ist das **Max**, nach
einer Nacht - es gab keine Wache auf diesen Merker. Zwei Fehler auf einmal: `cancel-algos`
verlangt `instId` (ohne sie geht der Storno NIE durch), und `51400` ("gefuellt, storniert
oder nicht vorhanden") wurde als Fehler behandelt statt als *erledigt*.

Merksatz: **ein Merker, der nur beim Erfolg faellt, braucht einen Dedupe - und ein
Ereignis, das "gibt es nicht mehr" bedeutet, ist kein Fehler.** Und: jeder Merker, der
wachsen kann, gehoert in eine Wache (hier `live_wache.stop_lage`, alle 10 min ueber
`scanner-live-wache`): sie meldet den Merker, Waisenstops (an der Boerse, zu keiner
Position) und Positionen ohne Boersenstop - nur bei Aenderung, leere Ausgabe sonst.

Nachweis: `python Agenten/Hermes/scripts/scanner-live-wache.py` (leise, Zustand
`stop_lage` zeigt `boerse: 5, buch: 5`); Tester
`Agenten/Hermes/scripts/test_live_wache_stops.py` (7); Aufraeumer
`Agenten/Handel/scanner/stops_bereinigen.py`; Details in
[[Handel/Boersen-und-Schluessel]].

## Eine Wache prueft eine BEDINGUNG, keine Adresse (29.09.2026)

`Agenten/Routinen/gateway-waechter.ps1` fuehrt als "erste Wahrheit" **Port 9900** und startet
den Gateway neu, wenn der Port zu ist. Bis zum 25.09.2026 war das richtig; seit der neuen
Hermes-Fassung lauscht der Gateway auf einem Named Pipe (`\\.\pipe\hermes-gateway-*`) und
bedient Webhooks auf 8644 - **TCP 9900 kann zu bleiben, waehrend der Gateway gesund laeuft**
(belegt: `hermes gateway status` = "Gateway process running", `hermes doctor` = "gateway
running", Telegram wurde bedient). Eine Wache, die auf die Adresse prueft, startet in diesem
Zustand **alle 2 Minuten einen neuen Gateway** - und jeder Neustart reisst die laufenden
Verbindungen mit.

Richtig ist die Bedingung selbst, nicht ihr frueherer Nebeneffekt: **laeuft ein Prozess mit
`hermes_cli.main gateway run`, und kann der Updater ihn zuordnen**
(`find_profile_gateway_processes(strict=True)`)? Das prueft
`Agenten/Hermes/scripts/gateway-identitaet-wache.py`; der Port bleibt nur Rueckfall fuer alte
Fassungen.

**Prueffrage bei jeder Wache:** prueft sie die Sache - oder eine Adresse, eine Datei, einen
Zaehler, der die Sache einmal begleitet hat? Siehe [[Lektionen/Wahrheit-pruefen]] 8 und 10.
Angelegt als T-139/T-140 in `Archiv/TASKS.md`.

## Das Dashboard hatte keine Wache (30.09.2026, T-147)

Das Hermes-Web-Dashboard (`http://127.0.0.1:9119/`) war der letzte Dienst ohne Wache. Beim
Wartungslauf vom 29.09.2026 endete `hermes update` mit `outcome=partial` (`phase_error:
Could not restart every paused Windows gateway`) — der Gateway heilte sich ueber
`gateway-identitaet-wache`, das Dashboard blieb aus und musste von Hand mit
`Start-ScheduledTask -TaskName 'Hermes_Dashboard'` gestartet werden.

Zwei Messungen vom 30.09.2026 bestimmen die Bauform:

- **Ein offener Port ist keine Wahrheit.** Der Prozess lief, `Get-NetTCPConnection -LocalPort
  9119` nannte PID 27864 — aber es kam 60 s keine Antwort, waehrend OmniRoute (20128) und der
  Gateway-Webhook (8644) im selben Moment in Millisekunden antworteten. Die Wache fragt
  deshalb nach einer echten HTTP-Antwort (jeder Statuscode zaehlt).
- **Ein Bau ist kein Haenger.** Ein abgebrochener Quell-Update-Lauf laesst den Starter
  `hermes: finishing an interrupted source update ...` lesen und VOR dem Bereitstellen den
  ganzen Bau fahren (Node-Abhaengigkeiten, TUI, Web-UI, Desktop-App; gemessen ueber 6
  Minuten, die `node`-Kinder mit wachsender CPU-Zeit), waehrend Port 9119 noch zu ist. Ein
  Neustart hilft hier NICHT — die neue Instanz faengt denselben Bau an, und ein Abbruch
  hinterlaesst ein halb gebautes `dist`. Die Wache misst daher vor jedem Eingriff zweimal die
  CPU-Zeit der Prozesskette (12 s Abstand, Kinder mitgezaehlt): steigt sie, wird nichts
  angefasst (erst nach 25 min gemeldet); steht sie still (gemessener Haenger: 1 s CPU in 5
  Minuten), wird geheilt.

Die Aufgabe `Hermes_Dashboard` traegt `RestartCount 999 / 1 min` — sie faengt einen ABSTURZ
ab, einen HAENGER nicht: der Prozess laeuft weiter, und niemand merkt es.

`Agenten/Hermes/scripts/dashboard-wache.py`, Hermes-Cron **`dashboard-wache` (Job
`bf375a2ac65f`, alle 15 min, `no_agent`, Telegram, leere Ausgabe = nichts senden)**:
gesund → still; sonst Kette per `Stop-Process` beenden (nie `taskkill`) und die Aufgabe
starten, bis 90 s auf die Antwort warten und melden. Kein Eingriff waehrend eines
Wartungslaufs, Bremse (ein Heilversuch je 30 min), dieselbe Feststellung erst nach 6 h
wieder. Tests: `Agenten/Hermes/scripts/test_dashboard_wache.py` (18, alles mit Attrappen).
Beleg-Lauf: `silent (empty output)` im Cron-Ordner, HTTP 200 nach der Heilung.

## Der Demo-Lauf hatte keine Wache (30.09.2026, T-211)

Der omnitrade-Lauf (`Werkstatt/omnitrade`, OKX-Demo, BTCUSDC) hatte als einziger
Dauerprozess **keine** Wache. Am 30.09.2026 gab es in zwei Stunden **fuenf** PIDs
(76116, 63732, 64440, 62416, 69800) — nach jedem harten Ende blieb `status/live.json`
auf `"state": "running"` mit einer **toten PID** stehen. Wer nur die Datei liest, glaubt
an laufenden Handel.

**Zwei Zeugen, nicht einer.** Die Wache fragt nicht die Datei allein, sondern benutzt
`Agenten/Handel/omnitrade_lauf.py`: Statusdatei **und** PID in der Prozessliste. Keine der
beiden Quellen genuegt fuer sich — der Programmname beweist nichts (`omnitrade-cli.exe`
faehrt auch `backtest`), und die Datei luegt nach einem harten Ende.

**Der haertere Zeuge gewinnt.** Ist die PID tot, heisst es `beendet` — auch wenn die Datei
zugleich alt ist. Sonst stuende in der Meldung „PID lebt noch", waehrend der Prozess
laengst weg ist (dieselbe Klasse Fehler wie die Anzeige-Luege selbst). Genau dieser Fall
hat beim Bau einen Test rot gemacht.

**Die Altersgrenze kommt aus dem Lauf, nicht aus dem Kopf.** Die Statusdatei wird nur
geschrieben, wenn eine Kerze verarbeitet wird — bei `--interval 1h` also stuendlich. Eine
feste 5-Minuten-Grenze erklaert einen gesunden Lauf fuer tot (am 30.09. real passiert: der
Lauf stand 13 Minuten still und galt als tot). Die Grenze steht deshalb in
`omnitrade_bridge.altersgrenze_s()`: `max(300 s, 2,5 x Kerzenabstand)` aus den
mitgeschriebenen Kerzen.

**Ein PID-Wechsel ist kein Fehler.** Der Lauf wird auch von Hand neu gestartet, und
mehrere Laeufe schreiben dieselbe Statusdatei. Die Wache fuehrt keine PID-Historie und
vergleicht keine Staende; der Merkschluessel ist die Meldung **ohne Zahlen**, damit
„PID 111 tot" und „PID 222 tot" dieselbe Feststellung bleiben.

**Sie startet nichts.** `omnitrade.cmd start` steht nur als Hinweis in der Meldung — ob
neu gestartet wird, entscheidet Max. Der Test prueft das an der Quelle (kein
`subprocess`, kein `Start-Process`, kein `taskkill` im Skript).

`Agenten/Hermes/scripts/omnitrade-lauf-wache.py`, Hermes-Cron **`omnitrade-lauf-wache`
(Job `804473084f4e`, alle 15 min, `no_agent`, Telegram, leere Ausgabe = nichts senden)**.
Meldungsform: `omnitrade-Demo-Lauf steht:` / `Lauf beendet: PID … lebt nicht, die
Statusdatei bleibt auf 'running' stehen …` bzw. `Statusdatei HAENGT: kein Lebenszeichen
seit …` / `Statusdatei KAPUTT: …` / `keine Statusdatei …`, je mit Symbol, Alter, Netz und
dem Startbefehl. Dieselbe Feststellung erst nach 6 h wieder (Merkdatei
`Agenten/Hermes/cache/omnitrade-lauf-wache.json`). Tests:
`Agenten/Hermes/scripts/test_omnitrade_lauf_wache.py` (17, Temp-Statusdatei, gestellte
Prozessliste); Gegenprobe: Zeugen-Reihenfolge und Wiederholungsschutz zurueckgenommen →
4 Tests rot.
