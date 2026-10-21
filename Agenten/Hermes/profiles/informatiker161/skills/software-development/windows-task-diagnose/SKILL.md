---
name: windows-task-diagnose
description: "Haus-Routine-Fehler via schtasks-Status diagnostizieren."
version: 1.0.0
author: Informatiker161
license: Proprietary
metadata:
  hermes:
    tags: [windows, scheduled-task, routinen, betrieb, diagnose]
    related_skills: [systematic-debugging]
---

# Windows-Scheduled-Task-Diagnose (BrainFiles-Routinen)

Klasse: eine geplante Windows-Aufgabe (Haus-Routinen unter `Agenten/Routinen/`,
aber auch Paperclip/Verbesserer/Ausserhaus-Kopie) meldet Fehler. Ziel: die
WURZEL erheben und belegen, nicht den Exit-Code als Fehler wiederholen.

## When to Use

Wenn eine geplante Windows-Aufgabe der Haus-Routinen einen Fehler meldet
(`LastResult` ungleich 0, vermisste Sicherung, Prozess-Server antwortet
nicht, Kopier-Routine mit robocopy-Code) und der Exit-Code allein nicht
zeigt, woran es lag.

## Reihenfolge

1. **Exit-Codes ueber `Get-ScheduledTaskInfo` messen, NICHT ueber
   `Get-ScheduledTask`.** Nur `Get-ScheduledTaskInfo` liefert `LastRunTime`/
   `LastResult`; `Get-ScheduledTask` laesst beide leer. Aus dem MSYS-Terminal
   direkt:
   ```bash
   MSYS_NO_PATHCONV=1 schtasks /query /tn "MaxHirn-Paperclip" /fo LIST /v \
     | grep -iE "Err|Result|Run Time|Status|Lauf|Ergebnis"
   ```
   Der grep ueber `LastResult` zeigt den gemessenen Fehlercode und die genaue
   `Letzte Laufzeit` (Datum + Uhrzeit), mit der man das richtige Log findet.
2. **`schtasks` scheitert an MSYS-Pfad-Konvertierung.** `schtasks //query` wirft
   `Ungueltige(s) Option/Argument - "//query"`. Warum: MSYS wandelt `/`-Argumente
   in Pfade um. Fix: Voranstellen `MSYS_NO_PATHCONV=1` und normales `/query`
   verwenden. Zusammen mit `grep -iE` kann man gezielt nach den Feldern suchen.
3. **`LastResult` ist nur der Trigger, das Log ist die Wahrheit.** Ein `LastResult=1`
   sagt nicht, warum. Im Log des Skripts unter `Agenten/Routinen/logs/` steht die
   Ursache (`paperclip-start.log`, `verbesserer-*.log`,
   `ausserhaus-kopie-letzter-lauf.log`). Zwei Faelle, die sich erst im Log trennen:
   * Start-Skript, das NICHTS schreibt: Log-Zeitstempel vs. `LastRunTime`
     vergleichen, Dateigroesse/`mtime` des stdout-Logs pruefen. Schreibt der
     produzierende Prozess (z.B. `paperclip-stdout.log`) seit Tagen nichts mehr,
     stirbt er sofort beim Start (kein Output, kein stderr) — das ist ein
     Start-Abbruch, kein "laeuft schon".
   * `robocopy-Code N`: robocopy meldet ueber den Exitcode, nicht per
     Ausnahme. Der Code (z.B. `11` = Fehler, `1` = kopiert) ist der Befund.
   * Exitcode `2` bei einer Kopier-Routine kann eine bewusste
     "uebersprungen"-Regel sein (SSD nicht angesteckt) und KEIN Fehlschlag —
     die Skript-Doku entscheidet.
4. **Live-Zustand pruefen bevor repariert wird.** Fuer einen Prozess-Server:
   `netstat -ano | grep ":3100 "` (Port belegt?), `tasklist | grep -i node`.
   Ein freier Port + fehlende neue Logzeilen = laeuft nicht, nicht "laeuft schon".
5. **Jede Aufgabe einzeln benennen.** Bei mehreren Fehltaetern erst alle
   Exit-Codes sammeln und einzeln zuordnen — nicht den ganzen Block auf alle
   anwenden. Eine Schwester-Aufgabe (z.B. `MaxHirn-Verbesserer-Spur2`) kann
   `0` sein, obwohl die Haupt-Aufgabe scheitert.

## Fallen

- Auf `LastResult` allein schieben, ohne die `Letzte Laufzeit` zu notieren.
  Ohne Datum/Uhrzeit findet man das falsche Log.
- `schtasks //query` ohne `MSYS_NO_PATHCONV=1` zu wiederholen — es scheitert
  garantiert an MSYS; das ist kein zweiter Versuch wert, sofort den Prefix nehmen.
- Ein Log-Zeitstempel, der aelter ist als `LastRunTime`: der Lauf hat das Log
  nie erreicht (Start brach vor dem Schreiben ab). Umgekehrt: Log neuer als
  `LastRunTime` = wartend/ueberlappend, nicht der gepruefte Lauf.
