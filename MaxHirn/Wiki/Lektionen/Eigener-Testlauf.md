---
id: 20261005-eigener-testlauf-als-messpunkt
title: 'Der eigene Testlauf ist der schlimmste Messpunkt'
tags: [lektion, hermes, diagnose, profile, logs, messwerkzeug]
created: 2026-10-05
updated: 2026-10-05
related: ['[[Lektionen/Wahrheit-pruefen]]', '[[Lektionen/Werkzeug-Fallen]]', '[[Wahrheit-pruefen]]', '[[Betrieb/Hermes]]']
summary: 'Ein haengendes Hermes-Profil wurde als Auth-Defekt gemeldet; die Ursache waren zwei eigene parallele Testprozesse und der MCP-Spawn-Kreis. Auth war nie kaputt — Antwort in 14 s.'
---

# Der eigene Testlauf ist der schlimmste Messpunkt

Am 05.10.2026 kam der Auftrag `fix hermes -p lotse auth`. Nach vier gruenen
Pruefungen wurde gemeldet: der Turn haengt, kein API-Call, drei Minuten
Stille. **Das war eine Falschmeldung** — der eigene Testaufbau war das Problem.

## Der Ablauf, der es erzeugt hat

1. Zwei PTY-Prozesse (`hermes -p lotse` und `hermes -p nerd`) wurden
   gleichzeitig ueber das `terminal`-Werkzeug gestartet und mit
   `process_manage` beantwortet.
2. Beide zeigten nach dem `submit` keine Antwort. Das wurde als
   profil- bzw. modellspezifischer Defekt gelesen.
3. Der Systemdruck wurde gemessen: **89 MCP-Server-Prozesse** (mail 20,
   windows-mcp 18, tooluniverse 18, kraken 16, archiv 12), Commit-Reservierung
   bei **1,7 GB** von 63,7 GB.
4. Die Hauswache lief einmal: 89 → 20 Prozesse, 1,7 → 31 GB.
5. Erneuter TUI-Test: **haengt weiterhin**. Die Meldung „haengt" blieb.
6. Max lieferte einen Screenshot derselben TUI-Sitzung mit **fertiger
   Antwort**. Das Log bestaetigte sekundengenau: `03:57:34` Turn,
   `03:57:48` `Turn ended: reason=text_response` — **14 Sekunden**.

## Die Regel

**Ein Testlauf, den man selbst gestartet hat, misst die Verzoegerung der
Konkurrenz, nicht den Gegenstand.** Bevor ein „haengt" gemeldet wird:

- alle eigenen Prozesse beenden (`process_manage` `kill`, nicht nur pollen),
- den Vorgang **einmal ohne Konkurrenz** wiederholen,
- die Antwortzeit **aus dem Log** lesen, nicht aus dem Bauchgefuehl:

```bash
grep -n "conversation turn: session=\|API call #\|Turn ended:" \
  profiles/lotse/logs/agent.log | tail -6
```

Erwartet drei Zeilen derselben Session-Id: Turn mit `msg=`, `API call #1` mit
`latency=`, `Turn ended:`. Steht `Turn ended` mit Latenz, war es langsam, nicht
kaputt.

## Die Merksaetze

- **`latency=` ist eine Messung, „haengt" ist eine Behauptung.** Beide sehen
  im Terminal gleich aus, bis man die eine Zahl liest.
- **Auth ist fast nie die Ursache.** Zwei gruene Zeilen (`auth status
  <provider>`, `doctor`) beenden das Thema. Wer danach weiter an Auth
  arbeitet, meldet am Ende eine Reparatur, die nichts kaputt war.
- **Vier gruene Wege = ehrliche Meldung:** „Auth ist nicht die Ursache, ich
  habe es nicht reproduzieren koennen" — mit den gefahrenen Wegen als Beleg.
- **Der MCP-Spawn-Kreis verlangsamt jeden Start**, auch den des Nutzers.
  Er ist ein Systemdruck-Fund, aber **nicht** die Ursache eines einzelnen
  haengenden Turns. Beides auseinanderhalten.
- **Falsche eigene Meldung aktiv zuruecknehmen**, mit Grund und Beleg — nicht
  still ersetzen. Sie stand als naechster Schritt in [[Werkzeug-Fallen]] und
  gehoert hierher.
- **`HERMES_HOME` nicht gesetzt** laesst den Aufruf in eine Alt-Installation
  (`AppData\Local\hermes`, config 14.09., auth 09.09.) laufen und dort
  minutenlang Abhaengigkeiten bauen. Das sieht wie ein Installationsfehler
  aus, ist aber ein Umgebungsfehler.

## Was davon wo steht

| Lehre | Ort |
|---|---|
| Verifikation vor der Fertigmeldung | Skill `verification-before-completion` |
| Zustand an der Quelle belegen | Skill `trugschluesse` |
| Vollstaendige Prozedur (drei Wege, Log-Grenze, Systemdruck) | Skill `hermes-profil-antwortet-nicht` |
| Diese konkrete Begebenheit | diese Seite |

## Nachweis

```bash
grep -n "conversation turn: session=\|API call #\|Turn ended:" \
  profiles/lotse/logs/agent.log | tail -6
powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\").Count"
```

**Datum.** 05.10.2026 (gemessen; Profil `lotse`, `nerd`, Hauptprofil).
**Betroffene Version.** Hermes v0.21.5+7022.g15cf141 (2026.9.24).