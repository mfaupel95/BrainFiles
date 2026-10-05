---
name: hermes-profil-antwortet-nicht
description: Diagnose a Hermes profile that seems to hang or not answer.
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Hermes, Profile, Auth, Diagnose, Logs, Belege]
    related_skills: [hermes-doctor, stille-ausfaelle-eingrenzen, trugschluesse, telegram-bruecke-diagnose]
---

# Hermes-Profil antwortet nicht — Auth ist fast nie die Ursache

Wenn ein Profil oder Bot „nicht antwortet", ist die naheliegendste Vermutung
(Auth) fast immer falsch. Dieser Skill belegt die Antwort zuerst und benennt
dann die Latenz als das, was sie ist. Er aendert nichts an Config oder
Prozessen — das gehoert `hermes-config-ops` und `hermes-maintenance`.

Der teuerste Fehler dieser Klasse: **man misst den eigenen Testlauf als
Fehler des Systems** (belegt 05.10.2026, `lotse`).

## When to Use

- „fix hermes -p <profil> auth", „der Bot schweigt", „<profil> haengt"
- eine Antwort erscheint nicht, obwohl der Aufruf Exit 0 liefert
- `doctor` sagt `logged in`, der Bot antwortet trotzdem nicht oder langsam
- eine Meldung wie „not logged into Nous Portal", 401 oder ein Prompt, der stehen bleibt

**Don't use for:** ein allgemeiner Update-/Install-Defekt (`hermes-maintenance`),
ein Aufruf, der mit Erfolg zurueckkehrt und nichts erzeugt
(`stille-ausfaelle-eingrenzen`), ein Telegram-Bot, der nicht antwortet, weil
der Bus steht (`telegram-bruecke-diagnose`).

## Prerequisites

- `HERMES_HOME` zeigt auf die aktive Installation. **Nicht gesetzt** laeuft der
  Aufruf in eine alte Alt-Installation und baut dort minutenlang Abhaengigkeiten
  (belegt: `AppData\Local\hermes`, config 14.09., auth 09.09.). Pruefen:
  `[Environment]::GetEnvironmentVariable('HERMES_HOME','User')`.
- Vor jedem `hermes.exe`-Aufruf aus einem MCP-/Sandbox-Kontext: `PYTHONHOME`
  und `PYTHONPATH` entfernen (vergiftetes uv-venv).
- Zugriff auf `profiles/<profil>/logs/agent.log`.

## How to Run

Alle drei Aufrufwege ueber das `terminal`-Werkzeug, aus `Agenten/Hermes`:

    unset PYTHONHOME PYTHONPATH
    export HERMES_HOME="C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes"
    ./bin/hermes.exe -p <profil> auth status <provider>     # 1 Credential
    ./bin/hermes.exe -p <profil> chat -q "Sag genau das Wort: ok" -Q
    ./bin/hermes.exe -p <profil> doctor

Den TUI-Weg als Hintergrundprozess mit `pty=true` starten, dann mit
`process_manage` `submit` (nicht `write`) beantworten und mit `wait` beobachten.

## Quick Reference

    # Antwortzeit je Turn belegen (der einzige ehrliche Erfolgsnachweis)
    grep -n "conversation turn: session=" profiles/<p>/logs/agent.log | tail -3
    grep -n "API call #\|Turn ended:" profiles/<p>/logs/agent.log | tail -6

    # Prozessbestand: MCP-Spawn-Kreis?
    powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\").Count"

    # Commit-Reservierung (die Grenze, nicht der RAM)
    powershell.exe -NoProfile -Command "\$os=Get-CimInstance Win32_OperatingSystem; '{0:N1} GB von {1:N1} GB' -f ((\$os.TotalVisibleMemorySize-\$os.FreePhysicalMemory)/1MB),(\$os.TotalVisibleMemorySize/1MB)"

    # vorhandene Hauswache gegen den Spawn-Kreis
    ./hermes-agent/venv/Scripts/python.exe scripts/mcp-zombie-wache.py

## Procedure

1. **Die vermutete Ursache zuerst pruefen, nicht beheben.** `auth status <provider>`
   und `doctor` sind zwei Zeilen. Sind beide gruen, ist Auth **erledigt** —
   jede weitere Auth-Arbeit ist Raten und wird als „repariert" gemeldet, ohne
   dass etwas kaputt war.
2. **Drei Wege getrennt fahren.** `chat -q` (headless), TUI, und der
   Bot-Weg `chat -q … -Q` aus der Repo-Wurzel. Ein funktionierender Weg
   beweist die Credential-Kette; drei funktionierende beweisen den Aufruf.
   Ein haengender Weg ist erst dann ein Befund, wenn die anderen beiden laufen.
3. **Das Log an der Turn-Grenze lesen, nicht im allgemeinen Log.** Die Kette
   ist `conversation turn: session=… msg=…` → `API call #N: … latency=Ns` →
   `Turn ended: reason=text_response`. Fehlt `API call`, haengt der Turn **vor**
   dem Modellaufruf (Werkzeugaufbau/Discovery). Da steht die Ursache; steht
   `Turn ended` mit Latenz, war es langsam, nicht kaputt.
4. **Latenz gegen Haenger entscheiden.** `Turn ended` mit `latency=9.5s` ist
   eine-Antwort-Situation, kein Fehler. „Haengt" ist eine Behauptung des
   Betrachters; `latency=` ist eine Messung.
5. **Eigene Testprozesse zuruecknehmen, BEVOR man den Zustand bewertet.**
   Zwei parallele TUI-Prozesse plus der Spawn-Kreis erzeugen genau das
   Bild, das man als Fehler des Profils meldet. Alle eigenen Prozesse
   beenden und den Vorgang einmal ohne Konkurrenz wiederholen.
6. **Den Systemdruck messen.** MCP-Server-Prozesse zaehlen und Commit
   lesen. Der Spawn-Kreis (mail 20, windows-mcp 18, tooluniverse 18,
   kraken 16, archiv 12 = 89 Prozesse) drueckte die Commit-Reservierung
   auf 1,7 GB und verlangsamte **jeden** Start — auch den des Nutzers.
   Die vorhandene Wache einmal laufen lassen: 89 → 20 Prozesse, 1,7 → 31 GB.
7. **Die Fehlermeldung beim Menschen holen, wenn alles gruen ist.** Nach vier
   gruenen Wegen ist die ehrliche Meldung: „Auth ist nicht die Ursache,
   ich habe es nicht reproduzieren koennen" — mit den gefahrenen Wegen als
   Beleg. Ein Screenshot oder eine Log-Zeile des Nutzers ist oft die
   fertige Antwort.

## Pitfalls

- **Der eigene Testlauf ist der schlimmste Messpunkt.** Pollt man einen PTY,
  den man selbst gestartet hat, waehrend ein zweiter laeuft, sieht man die
  Verzoegerung des anderen. Belegt 05.10.2026: `lotse` TUI gemeldet als
  „haengt3 min, kein API-Call"; der Nutzer-Screenshot zeigte dasselbe
  TUI mit fertiger Antwort — Log: `03:57:34` Turn, `03:57:48` Antwort, **14 s**.
- **Eine falsche HERMES_HOME fuehrt in die Irre.** Wer sie nicht setzt,
  nicht setzt, landet in `AppData\Local\hermes` und sieht
  `Installing Python dependencies failed` plus einen fuenfminuetigen Bau —
  das ist die Alt-Installation, nicht das Profil.
- **`credential pool: no available entries (all exhausted or empty)` ist oft
  ein Nebenschauplatz.** Sie steht im Log zwischen `Vision auto-detect` und
  dem Turn und geht an einen *anderen* Provider (Auxiliary). Sie ist kein
  Beleg fuer einen Fehler des Hauptmodells — beweisen muss sie sich an der
  Zeile danach.
- **`Background MCP discovery previously exited with no connected servers;
  retrying discovery thread`** ist eine Warnung, die beim **ersten**
  Discovery-Versuch normal ist; danach lief der Turn. Sie beweist keine
  Endlosschleife, ausser sie wiederholt sich im selben Turn.
- **Ein runder Befund ist das Warnsignal.** „89 Prozesse", „0 Positionen",
  „alle gruen" — glatte Zahlen kommen fast immer aus dem falschen
  Sammelbegriff (`trugschluesse`).
- **Befehle fuer Max sind PowerShell, mit Leerzeichen vor der Umleitung.**
  `doctor2>&1` liest PowerShell als Argument und startet einen Hintergrundjob;
  `doctor 2>&1` leitet um. Fuer ihn nie ein bash-Werkzeug nennen.

## Verification

Belegt heisst: derselbe Aufruf antwortet, und das Log nennt die Latenz.

    grep -n "conversation turn: session=\|API call #\|Turn ended:" \
      profiles/lotse/logs/agent.log | tail -6

Erwartet drei aufeinanderfolgende Zeilen derselben Session-Id: Turn mit
`msg=`, `API call #1: … latency=…s`, `Turn ended: reason=text_response`.
Fehlt `Turn ended`, ist der Turn unvollstaendig — dann erst weitergrenzen.
Ein Exit 0 aus `chat -q` ohne Logzeile ist kein Nachweis.