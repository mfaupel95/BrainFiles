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
| Hermes-Cron (`no_agent`) | Wachhunde, die eine Nachricht schicken sollen | `bus-waechter` (15 min), `moondev-agenten-wache` (15 min), `nautilus-runden-wache` (30 min), `one-wache` (10 min), `breite-wache` (taeglich 19:00) |

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
