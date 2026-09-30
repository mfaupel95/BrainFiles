---
id: 20260930-dauerlauf-tode
title: 'Handel — Warum der Dauerlauf stirbt: Rueckgabe 143 und der Sperren-Churn'
tags: [handel, betrieb, wachen]
created: 2026-09-30
updated: 2026-09-30
related: ['[[Handel/Spuren-Uebersicht]]', '[[Betrieb/Wachen-und-Aufgaben]]', '[[Lektionen/Windows-Umgebung]]']
summary: 'T-193: drei Todesarten des Dauerlaufs, belegt statt vermutet — 143 = MSYS-timeout, sofortiger Tod = Sperren-Churn (behoben), spurlos = Speicherdruck. Dazu die neue Wache.'
---

# Warum der Dauerlauf stirbt

Die Wächter-Aufgaben starten tote Läufe neu — aber **niemand meldete, dass einer
gestorben war**. Die Handelszentrale zeigte weiter einen Stand, der stehen blieb.
Am 30.09.2026 standen zwischen 01:52 und 02:39 alle drei Stufen still; aufgefallen
ist das nur, weil eine Sitzung zufällig nachsah. Diese Seite hält fest, was die
Ursachenforschung belegt hat, und was seither dagegen läuft.

## Die Fälle (belegt)

| Stufe | Start | Tod | letzte Spur | Rückgabe | Ursache |
|---|---|---|---|---|---|
| Basis | 29.09. 23:21:59 | 29.09. 23:22:59 | xperp | **143** | Handstart mit `timeout 60 python dauerlauf.py` |
| Basis | 30.09. 02:34:26 | 30.09. 02:36:55 | kraken (live) | **143** | Handstart mit `timeout 150 … --takt 15 --risiko niedrig` |
| alle drei | 29.09. 23:23 / 23:31 / 23:32 | ~01:52–02:07 | kein Eintrag | — | Speicherdruck (Ereignis 2004, Docker 15,7 GB) |
| Basis/mittel/hoch | 02:07 / 02:24 / 02:35 … / 02:51 | jeweils sofort | — | kein Eintrag | Sperren-Churn — **behoben** (Commit `41d2ffa`) |

## 1. Rückgabe 143 ist ein Fingerabdruck, kein Zufall

`143` = 128 + 15 = **SIGTERM, aus einem MSYS-/Git-Bash-Kontext**. Gemessen mit
einem nackten Schlafprozess je Werkzeug:

| Weg | Rückgabecode |
|---|---|
| `taskkill /T /F` | 1 |
| `taskkill /F` | 1 |
| `Stop-Process -Force` | 4294967295 |
| `os.kill(pid, 15)` | 15 |
| **MSYS `timeout N` / Bash-Job-Abbau** | **143** |

Ein zweiter MSYS-Kontext kann den Prozess dabei **nicht** erreichen (`kill` aus
einer anderen Bash: „LEBT NOCH“) — wer 143 sieht, muss also in **derselben**
Shell gesucht werden, die den Lauf gestartet hat. Genau dort stand es: beide
Tode sind in `Agenten/Hermes/state.db` als Sitzungsaufruf belegt, jeweils
`timeout <N> … dauerlauf.py`, und die Todeszeit liegt **auf die Sekunde** beim
Ablauf des Zeitlimits.

Windows-Werkzeuge erzeugen 143 **nie**. Der Verdacht aus T-193
(`moondev_dauerlauf._stoppe` mit `taskkill /T /F`) ist damit widerlegt.

## 2. Der Sperren-Churn (behoben)

`handel-dauerlauf.ps1` schreibt die PID, die `Start-Process` zurückgibt — bei
einem venv-Startprogramm ist das der **Elternteil** des Interpreters.
`sperre.belegt()` verglich sie mit `os.getpid()`, sah einen lebenden fremden
Python und ließ den Lauf mit „Es läuft bereits ein Dauerlauf“ **sofort** enden.
Der Wächter fand beim nächsten Takt eine tote PID, schrieb „verwaiste Sperre“ und
startete neu — im Drei-Minuten-Takt, 02:35 bis 02:51. Fix: `belegt()` nimmt auch
`os.getppid()` aus (der eigene Starter ist kein fremder Lauf). Seither laufen
alle drei Stufen durch.

## 3. Spurlos = Speicherdruck

Kein letzter Eintrag, kein Rückgabecode. Dazu passt Ereignis **2004**
(„virtueller Speicher unzureichend“) am 30.09. um 02:07:56, Spitzenreiter
`com.docker.sailor.exe` mit 15,7 GB, daneben zwei Python-Prozesse mit 2,9 und
2,2 GB. Das ist dieselbe Ursache wie T-215/T-216 — die Auslagerungsdatei bindet
die Commit-Grenze auf 75,7 GB, und die wirkt erst nach einem Neustart (T-220).

## 4. Was seither läuft: die Wache

`Agenten/Hermes/scripts/dauerlauf-wache.py`, Hermes-Cron **`dauerlauf-wache`**
(alle 15 min, `no_agent`, Telegram, **leere Ausgabe = nichts senden**).

Je Stufe **zwei Zeugen**: die Prozessnummer aus der Sperrdatei (mit Startzeit
gegen PID-Wiederverwendung) und die Frische des Protokolls. Befunde:

* `tot-143` — beendet durch SIGTERM, mit dem Hinweis auf den Handstart.
* `tot-code` — beendet mit einem anderen Rückgabecode (z. B. `3221226505`).
* `tot-spurlos` — steht, kein Rückgabecode (Speicherdruck).
* `haengt` — Prozess lebt, Protokoll älter als **20 min** (drei Zyklen).
* `churn` — drei „verwaiste Sperre“ in der letzten Stunde (niemand kommt hoch).

Sie **beendet, startet und kopiert nichts**; ein Befund wird höchstens alle 6
Stunden erneut gemeldet (Merker `Agenten/Hermes/cache/dauerlauf-wache.json`).

Prüfen:

    python Agenten/Hermes/scripts/dauerlauf-wache.py      # leer = gesund
    python -m unittest test_dauerlauf_wache -v            # 16 Tests, aus Agenten/Hermes/scripts

## 5. Die Regel für Sitzungen

**Den Dauerlauf nie zur Ansicht mit `timeout N python dauerlauf.py` starten.**
Ein Handstart nimmt die **echte** Sperre und schreibt ins **echte**
`dauerlauf.log`; wird er abgeschossen, bleibt eine `Rueckgabe 143`-Zeile stehen,
die wie ein Diensttod aussieht, und die Sperre bleibt liegen. Für einen Blick in
einen Zyklus: `python <spur>/handeln.py --vorschau`.