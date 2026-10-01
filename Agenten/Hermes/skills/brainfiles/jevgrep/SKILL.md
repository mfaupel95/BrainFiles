---
name: jevgrep
description: "Use when Code per Frage gesucht wird (jevgrep/jg)."
version: 0.1.0
author: Hermes Agent
platforms: [windows]
license: MIT
metadata:
  hermes:
    tags: [werkzeuge, code, suche, fremd]
    related_skills: [codebasis-bestand, repos-zentrale, trugschluesse]
---

# jevgrep (`jg`): Code finden, indem man nach Verhalten fragt

`jg` beantwortet eine Frage zu einem Repository mit **Dateiliste, Lesespuren und
Quelltextausschnitten** (Modell Jev urteilt je Datei). Es ist der Weg, wenn man den
**Ort nicht kennt**: „wie wird entschieden, ob …", „wo wird geprueft, bevor …".
Kennst du den Symbolnamen, ist `search_files` schneller und kostenlos.

## When to Use

- eine Frage zu einem Repo, dessen Aufbau unbekannt ist (Klon, fremdes Projekt,
  gewachsener eigener Baum)
- mehrere Kandidaten sollen eingegrenzt werden, bevor man liest
- ein Verhalten soll ueber Dateigrenzen hinweg gefunden werden

**Don't use for:** exakte Symbole oder Pfade (`search_files`), Bestand messen
(`codebasis-bestand`), Zustand belegen (`trugschluesse`).

## Aufruf (PowerShell — die Shell von Max; Werkzeug-Shells sind bash)

```powershell
cd 'C:\Users\faupe\Documents\BrainFiles'
.\jevgrep.cmd files Agenten\Handel\scanner          # kostenlos: was wuerde gelesen
.\jevgrep.cmd 'Wie wird entschieden, ob eine offene Position geschlossen wird?' Agenten\Handel\scanner
```

Voraussetzung und Anmeldung: `OPENCODE_API_KEY` als Windows-Benutzervariable ist
gesetzt, `jg` ist angemeldet (Modell `jev-1.13-free` ueber OpenCode Zen, **Kosten 0**).
Nachpruefen: `.\jevgrep.cmd doctor` muss „Jev connection verified" sagen.
Einzelheiten, Protokoll und Nachweise: `MaxHirn/Wiki/Werkzeuge/jevgrep.md`.

## Die vier Regeln, die ueber Nutzen und Kosten entscheiden

1. **Nach Verhalten fragen, nicht nach Namen** — ein Satz, keine Aufzaehlung.
2. **Die Wurzel ist der Kostenhebel**, nicht die Frage: `Agenten/Handel/scanner`
   66 Dateien (6,2 s) gegen `Agenten/Handel` 5.247 Dateien. Immer erst
   `jg files <ordner>`, dann suchen.
3. **Jede Suche schickt Quelltext an den Dienst.** Vault, Schluesselordner und
   Personenbezogenes gehoeren nicht in die Wurzel; verengen mit
   `--exclude '**/zustand*.json' --exclude '**/*.csv'`.
4. **Bricht ein Lauf sofort mit Exit 1 und ohne Ausgabe ab, ist der ANBIETER schuld,
   nicht der Schluessel** — meist ist das freie Kontingent aufgebraucht (`429
   FreeUsageLimitError`). Nicht jevgrep debuggen, sondern die Sonde rufen:
   `python Agenten\Werkzeuge\jevgrep\sonde_zen.py` (nennt HTTP-Status und Dauer).
   Die Zeile `stdin is not a tty` ist MSYS-Rauschen und erscheint auch bei Erfolg.

## Ergebnisse lesen

Die Ausgabe ist **Belegmaterial, keine Antwort**: Dateien und Rollen sind
Schaetzungen („implementation", „caller", „test"), Quelltextausschnitte sind
wortgetreu. `Exit 2` heisst unvollstaendig (nicht falsch) — die genannten Stellen
sind trotzdem brauchbar; `Issue: "resource_limit"` nennt den Grund. Antworten
liegen in `~/.cache/jevgrep` — ein zweiter Lauf derselben Frage ueber derselben
Wurzel ist schneller und kostet nichts.

## Gegenprobe

Wer behauptet, `jg` habe etwas gefunden, nennt **Datei und Zeile** und liest die
Stelle mit `read_file` nach. Eine Trefferliste ohne nachgelesene Stelle ist kein
Befund.
