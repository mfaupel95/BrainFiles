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
   `jg files <ordner>`, dann suchen. Der Vorschalter im Wurzel-Aufrufer lehnt ueber
   300 Dateien oder 60 MiB ab (`--trotzdem` erzwingt) und nennt vorher Kosten und
   Anbieterzustand - er bricht auch ab, wenn der Anbieter 429/402/403 liefert.
3. **Jede Suche schickt Quelltext an den Dienst.** Vault, Schluesselordner und
   Personenbezogenes gehoeren nicht in die Wurzel; verengen mit
   `--exclude '**/zustand*.json' --exclude '**/*.csv'`.
4. **Bricht ein Lauf sofort mit Exit 1 und ohne Ausgabe ab, ist der ANBIETER schuld,
   nicht der Schluessel** — meist ist das freie Kontingent aufgebraucht (`429
   FreeUsageLimitError`). Nicht jevgrep debuggen, sondern die Sonde rufen:
   `python Agenten\Werkzeuge\jevgrep\sonde_zen.py` (nennt HTTP-Status und Dauer).
   Die Zeile `stdin is not a tty` ist MSYS-Rauschen und erscheint auch bei Erfolg.

## Wenn der Anbieter nicht kann: die eigene Bruecke (auch lokal)

Der Anbieter ist austauschbar. `Agenten/Werkzeuge/jevgrep/jev_bruecke.py` nimmt die
jevgrep-Anfragen an und beantwortet sie ueber ein OpenAI-kompatibles Modell — lokal
(Ollama), Inception Mercury 2.5, Nous, OmniRoute. Gefordert: JSON rein/raus, je Kennung
`noul` 0..1, **32k Kontext**, 60-400 Anfragen je Suche. Kein Chat-Modell mit Werkzeugen
noetig.

```powershell
Agenten\Werkzeuge\jevgrep\bruecke-mercury.cmd          # Mercury 2.5 (laeuft, gemessen)
'lokal' | .\jevgrep.cmd auth --provider custom --base-url http://127.0.0.1:8742/v1 --model bruecke --stdin
```

Mercury 2.5 ist verdrahtet (`INCEPTION_API_KEY` als Benutzervariable, wird aus der
Registry gelesen): Suche ueber `Agenten/Handel/scanner` 66 Dateien in 56,7 s, 13 Treffer,
70 Anfragen ~447.000 Token = **1,8 US-Cent** (10 Mio. Gratis-Token je Schluessel ≈ 22
Suchen). Jev (Zen) war 6,2 s schnell und gratis, aber rate-limitiert. Beide finden
dieselben Kernstellen.

Gemessen (lokales Ollama, 01.10.2026) - **lokal ist mechanisch moeglich, aber als
Richter nicht belastbar**: `qwen35-8k` gibt es nicht mehr (`HTTP 404`, alle Dateien
galten als nicht relevant), `gemma-e4b-8k-64k` lief in `HTTP 500 out-of-memory`, und ein
direkter Aufruf mit 20.000 Zeichen `handeln.py` antwortete nach 51 s mit **0.0** auf die
Frage, ob die Datei das Schliessen einer Position zeigt - also falsch. Die Bruecke
meldet solche Ausfaelle im Protokoll (`fehler`) und auf der Konsole, statt sie in 0.0
zu verschwinden. **Achtung:** `jg auth` ersetzt die gespeicherte Anmeldung; wer zurueck
zu OpenCode Zen will, ruft
`python Agenten\Werkzeuge\jevgrep\von_opencode_anmelden.py --anwenden`.

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
