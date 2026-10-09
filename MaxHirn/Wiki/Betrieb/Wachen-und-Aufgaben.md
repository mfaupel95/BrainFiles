---
id: 20260921-wachen-und-aufgaben
title: 'Betrieb — Wachen und geplante Aufgaben'
tags: [betrieb, wachen]
created: 2026-09-21
updated: 2026-10-08
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

## Leere Ausgabe: die gefaehrlichste Ausgabe (05.10.2026)

**Regel: in einem Watchdog ist „leer" nicht eindeutig.** Punkt 1 oben sagt
„leere Ausgabe heisst nichts senden" — das erzeugt eine doppelte Bedeutung: leer
kann „nichts zu melden" heissen ODER „die Pruefung lief nie". Die zweite Form
faellt nie auf, weil nichts auffaellt.

Gemessen in `Agenten/Hermes/scripts/historie-auftrag.py`. Der Auftrag band die
Wache als `HIER / "historie-wache.py"` ein, wobei `HIER = Path(__file__).resolve()`
die **Datei** ist — der Pfad zeigte auf ein Verzeichnis mit py-Namen darin.
`subprocess.run` meldet einen fehlenden Pfad **nicht** als Fehler, sondern mit
leerer Ausgabe. Die Regel aus Punkt 1 machte daraus „alles in Ordnung". Der
Auftrag haette taeglich „nichts zu tun" gemeldet, ohne dass jemand es gemerkt haette.

Drei Regeln folgen daraus:

1. **Der Werkzeugpfad braucht den ORDNER**: `HIER = Path(__file__).resolve().parent`,
   oder `SCRIPTS = HIER.parent` wenn `HIER` die Datei bleibt.
2. **Ein Fehlercode des Kindes ist eine Ausnahme**, kein leeres Ergebnis — sonst
   wird „Abruf kaputt" zu „alles frisch".
3. **Im Aufrufer darf ein Fehler der Pruefung nie in den stillen Zweig fuehren**,
   sondern zu einem gemeldeten Exitcode (2 = Befund, nicht 0 = gesund).

**Gegenprobe pflichtig:** den Fehlpfad zurueckbauen und pruefen, dass Tests rot
werden. Ein Test, der den Fehlerpfad nicht kennt, prueft die Fehlerbehandlung nicht.

**Merksatz: ein stiller Fehlpfad in einem Wecker ist die teuerste Form von gruen** —
weil die Wette „leer ist gesund" ihn als Gesundheit liest.

### Nachweis

```bash
python Agenten/Hermes/scripts/audit-werkzeugpfad.py --ordner <Ordner>
```

Exit 1 = Befund, Exit 0 = sauber. Stand 05.10.2026: `Agenten/Hermes/scripts`,
`Agenten/Routinen`, `Agenten/Bus` und `Agenten/Handel` sauber — der Fehler war auf
eine Datei beschraenkt. Der Auditor meldet die **Form**, nicht den Zustand: er
kann nicht wissen, ob ein Werkzeug fehlt, ohne jeden Pfad zu pruefen. Ein Befund
ohne Beleg waere das Gegenteil der Hausregel.

### Zwei Auditoren wurden verworfen (gleicher Tag)

Eine Fassung „subprocess mit geschluckter Ausgabe ohne `returncode`-Pruefung" nannte
elf Dateien. Von Hand nachgeprueft: die beiden ersten fangen den Fehler **aktiv**
ab (`except OSError` mit Klartext, danach `return ""` mit dokumentierter Bedeutung
„leer heisst nicht messbar"). Der Befund war falsch. Eine breitere Fassung nannte
63 Dateien ohne jede Meldung in `except` — das ist der Normalbau der
Wachenfamilie, kein Befund.

**Merksatz: ein Auditor, der elf Mal falsch alarmiert, ist schlimmer als keiner.**
Breite zuerst messen, dann verengen — nie umgekehrt.

## Zwei Ablageorte, ein Name (05.10.2026)

**Regel: bei zwei gleichnamigen Ordnern ist die Quelle der Wahrheit das SCHREIBENDE
Modul, nicht die Pfadannahme.**

Die Feed-Historie der MoonDev-Spuren lag in zwei Orten:

- **echt:** `Agenten/Handel/daten/historie/FEED/` — dorthin schreibt
  `moondev_historie` (Konstante `ORDNER`, Zeile 42) und von dort liest
  `replay.lauf_feed` ueber `moondev_historie.lade_feed`
- **verwaist:** `Agenten/Handel/daten/historie/` OHNE `feed` — drei 1D-Dateien
  (BTC, ETH, SOL) vom 25.09.2026, die kein Lauf liest

Der Befund fiel **nicht** durch einen Test, sondern durch die Diskrepanz selbst:
der Abruf meldete „30 Reihen geschrieben, 0 ohne Kerzen", die Dateizahl blieb bei
drei. Ein Test mit einer Attrappe im falschen Ordner haette die Regel bestaetigt
statt sie zu brechen.

Beide Wachen holen den Pfad jetzt aus `moondev_historie.ORDNER` ueber das
Modul-Schaetzfeld `FEED_ORDNER` — nicht geraten, und **nicht** als reiner
Funktionsweg: der Importweg umgeht sonst jedes Umbiegen von `HANDEL` im Test
(gemessen: 15 Fehlschlaege mit „Historie fehlt", alle dieselbe Ursache).

**Nachweis:** `grep -n "^ORDNER" Agenten/Handel/moondev_historie.py` — die Konstante
ist die Wahrheit; `ls Agenten/Handel/daten/historie/feed/*_1D.json` — 30 Reihen.

## Ein Verweis kann verschwinden, ohne dass es jemand merkt (05.10.2026, T-369)

Am 05.10.2026 um 22:12:52 war `BrainFiles/Werkstatt` kein Verweis mehr auf
`O:/Werkstatt`, sondern ein **echter, fast leerer Ordner** - nur die zwei
konfig-doktor-Dateien lagen darin. Alle 49 Repos, omnitrade, OmniRoute und die
Projekte waren ueber den BrainFiles-Pfad unsichtbar. Auf `O:` lag alles unversehrt;
nur der Verweis war weg. Aufgefallen ist es **nur**, weil eine Sitzung zufaellig den
omnitrade-Stand pruefen wollte: `omnitrade.cmd` meldete 'keine Statusdatei'.

Es gab keine Wache dafuer - obwohl der konfig-doktor `LAUFZEIT-JUNCTION-*` als
KRITISCH kennt. Nur rief ihn niemand auf. **Ein Pruefer ist keine Wache.**

### Die Wache: zwei Zeugen, absichtlich

`Agenten/Hermes/scripts/konfig-doktor-wache.py`, Cron `konfig-doktor-wache`
(`1beb6d64a8c8`, alle 4 h, `no_agent`, Telegram, leere Ausgabe = nichts senden):

1. **Direkter Verweis-Test** (schnell, ohne Fremdprozess): existiert der Pfad, ist er
   ein Reparse-Punkt, ist das Ziel erreichbar. Das faengt den Vorfall in
   Millisekunden - und funktioniert auch, wenn der Doktor selbst defekt ist.
2. **Konfig-Doktor** (`konfig-doktor.ps1 -Kurz -OhneExtern`, ~8 s): der breite Blick.
   Gemeldet wird **nur KRITISCH** - WARNUNGEN und HINWEISE sind fuer eine Wache
   Rauschen.

### Zwei Lehren, beide uebertragbar

* **Ein Fehler der Pruefung ist nie ein leeres Ergebnis.** Exitcode 2, Zeitueberschreitung
  und unlesbare Ausgabe werden GEMELDET, nicht verschwiegen. Eine leere Ausgabe heisst
  genau eines: alles geprueft, nichts KRITISCH.
* **Die Merkkennung ignoriert Zahlen als ganze Folge** (`re.sub(r'[0-9]+', '#', text)`).
  Je Ziffer ersetzt macht aus `3` -> `#` und `99` -> `##` zwei VERSCHIEDENE Kennungen -
  derselbe Befund meldet dann doch bei jedem Lauf. Der Test
  `test_zahlen_aendern_die_kennung_nicht` hat genau das gefunden.

### Die Reparatur (verlustfrei, wiederholbar)

```
# 1. Inhalt des echten Ordners nach O: retten (hier: die zwei Dateien)
# 2. Remove-Item -LiteralPath <wurzel>\Werkstatt -Recurse -Force
# 3. New-Item -ItemType Junction -Path <wurzel>\Werkstatt -Target 'O:\Werkstatt'
# 4. (Get-Item <wurzel>\Werkstatt -Force).LinkType  -> muss 'Junction' melden
```

**NIE `rm -rf` aus bash auf einen Pfad, der ein Junction sein koennte** - das
Junction-Removal-Verhalten ist unklar, und ein Fehlgriff loescht das ZIEL mit.
PowerShell `Remove-Item -LiteralPath` + `New-Item -ItemType Junction` nehmen.

**Ursache unbewiesen** (T-369): `konfig-doktor.ps1` (schreibt nur eine Datei) und seine
Testsuite (Fixtures in `GetTempPath` mit eigener GUID) sind ausgeschlossen. Zeitgleich
22:12:52 wurden `datensortierung.ps1`, `sicherung.ps1` und `wissen-index-pruefen.ps1`
geschrieben - eine parallele Sitzung war im Baum; keine dieser drei fasst Werkstatt an.

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

## Zeitgrenze und Einzelinstanz: zwei Fallen der Aufgabenplanung (30.09.2026)

**Ein Nicht-0-Code ist erst mit seiner Zeitgrenze ein Befund.** `3221225786`
(0xC000013A, STATUS_CONTROL_C_EXIT) sieht wie ein Skriptabsturz aus, ist bei einem
Wrapper, der einen Dauerdienst startet, aber meistens die `ExecutionTimeLimit` der
Aufgabe: `MaxHirn-Sicherung` und `-Zweitkopie` standen auf `PT1H` und wurden nach genau
einer Stunde mitten im Lauf abgeraeumt — erkennbar daran, dass ihr Protokoll nur die
Startzeile enthaelt und keine Ende-Zeile. Beide stehen jetzt auf `PT3H`,
`MaxHirn-OmniRoute` (startet `npm run start`, kehrt erst nach dem Hochfahren zurueck) von
`PT15M` auf `PT1H`. Vor jeder Deutung eines Codes also
`(Get-ScheduledTask <name>).Settings.ExecutionTimeLimit` mitlesen. Umgekehrt ist
`267014` bei einem Stundenlauf kein Skriptfehler, sondern der Neustart.

**`IgnoreNew` schuetzt nur gegen die Aufgabe selbst.** Ein Wrapper, der sein Kind startet
und sofort zurueckkehrt, laeuft bei jeder zweiten Ausloesung erneut — Handstart,
Fremdsitzung oder ein Skriptaufruf erzeugen dann ein ZWEITES Kind. Am 30.09.2026 liefen
so zwei MoonDev-Treiber samt doppeltem Agentensatz (15:36 und 16:29). Der
Einzelinstanz-Schutz gehoert in den Wrapper (Prozessabfrage; den Suchtext aus Teilen
bauen, sonst trifft der Filter die eigene Kommandozeile und der Wrapper beendet sich
selbst). Dieselbe Luecke hat die Datensortierung: drei Handstarts an einem Tag haben sich
das Tagesprotokoll gegenseitig ueberschrieben (T-240).

**Ein Volltext-Suchlauf ueber den eigenen Baum ist O(156.000).** `Agenten` und `MaxHirn`
tragen zusammen so viele Dateien, auch nach Abzug von `node_modules`, `.venv` und
`hermes-agent`. Der Suchblock der Datensortierung holte sich je Kandidat die Dateiliste
NEU per `Get-ChildItem -Recurse` (ohne die Ausschlussliste, also inklusive der
Umgebungen) — mit fuenf Zertifikaten stand der Lauf nach 43 Minuten noch darin und wurde
beim Neustart abgebrochen. Richtig ist: erst alle Kandidaten sammeln, dann EIN Suchlauf,
und der nur ueber Textendungen und ohne `site-packages`, `.venv*` und `dist-info`
(`.venv.bak-*` faellt durch keine Liste, die nur `.venv` kennt). Gemessen danach: 446 s,
Ende ok. Umgebungs-CA-Buendel (`certifi/cacert.pem`) sind keine losen Schluesseldateien
und werden nicht mehr gemeldet.
## gbrain-maintenance-Wache (08.10.2026)

Hermes-Cron `gbrain-maintenance` (Job f8137b52e0ac, taeglich 06:00, `no_agent`,
Watchdog-Muster: leere Ausgabe = nichts senden), Skript
`Agenten/Hermes/scripts/gbrain-maintenance-wache.py`. Faehrt
`gbrain doctor --fast --json` ueber den WSL-Launcher und meldet nur echte
Fehler; startet nie serve/cron/daemon und keine bezahlten Pfade.

**Die Faktenzahl ist der eigentliche Waechter (gemessen 08.10.2026):**
`gbrain stats`/`list` zaehlen SEITEN, nicht Fakten. Ein Gehirn, das nur ueber
die Memory-Verben gefuellt wurde, meldet dort 0, obwohl der Bestand da ist
(gemessen: 0 Seiten gegen 44 aktive Fakten, ids bis #51). Wer sich auf stats
verlaesst, sieht einen Verlust nicht - und `gbrain doctor` empfiehlt bei genau
diesem Bestand `gbrain reinit-pglite`, was laut eigener Ausgabe *"drops every
embedding in your brain"* bedeutet. Die Wache zaehlt deshalb zusaetzlich die
AKTIVEN FAKTEN gegen die Merkdatei.
