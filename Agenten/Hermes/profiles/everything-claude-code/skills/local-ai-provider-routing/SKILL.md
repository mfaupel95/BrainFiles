---
name: local-ai-provider-routing
description: "Lokalen KI-Client auf anderen Anbieter/Proxy schalten."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [betrieb, ki-agenten, codex, claude-code, routing]
    related_skills: [codex, claude-code, verbindungen]
---

# Lokale KI-Clients: Anbieter, Proxy, Gateway

## When to Use

- Ein KI-CLI oder eine KI-Desktop-App soll auf einen anderen Anbieter umgestellt werden.
- Ein Proxy/Router (claude-unlimited-Pool, OmniRoute) soll installiert oder angeschlossen werden.
- Eine App nutzt den falschen Provider, das Modell ist unbekannt, ein Gateway soll wieder ganz normal sein.

## 1. Erst das Drahtformat, dann die Config

Ein Proxy kann einen Client nur bedienen, wenn beide dasselbe Drahtformat sprechen.
Das ist eine Eigenschaft des Proxy-Codes, keine Konfiguration — eine Config-Änderung
bringt hier nichts.

| Client | sendet |
|---|---|
| Claude-Code-CLI, Claude-Desktop-App, claude-unlimited-Pool | Anthropic Messages (`/v1/messages`) |
| Codex-CLI, ChatGPT-Desktop-App | OpenAI Responses |

**Vor der Umsetzung prüfen:** im Quelltext des Proxy den Pfad suchen, den er
wirklich bridgt (`grep -n "bridged for real" <site-packages>/<paket>/gateway.py`),
und im README die Zeile „Anything that speaks the ... API". Serviert der Proxy
nur einen anderen Pfad, als der Client sendet, ist die Umsetzung nicht machbar.
Dann den Beleg nennen, die Config in Ruhe lassen und die umgekehrte Richtung
anbieten, wenn sie trägt: ein Pool mit Übersetzung kann die Accounts des anderen
Ökosystems für Claude Code bereitstellen, nicht umgekehrt.

Belege und die Prüfmuster dafür: `references/wire-formats.md`.

## 2. Welche Datei steuert welchen Client

| Client | Datei | wirkt auf |
|---|---|---|
| Codex-CLI **und** ChatGPT-Desktop-App | `~/.codex/config.toml` | beide gemeinsam |
| Claude-Code-CLI | `~/.claude/settings.json`, Feld `env` | nur die CLI |
| Claude-Desktop-App | `%LOCALAPPDATA%\Claude-3p\configLibrary\*.json` plus `_meta.json` | nur die App |
| claude-unlimited-Pool | `~/.claude-unlimited/config.json`, Daemon auf `127.0.0.1:4317` | nur der Pool |

`model` und `model_provider` in `~/.codex/config.toml` sind der **Default für neue
Threads der Desktop-App**, nicht nur für die CLI. Wer sie ändert, ändert beide
Clients. Die Desktop-App bietet zusätzlich jeden `[model_providers.*]` als Auswahl
im Modell-Picker an; ein Picker-Eintrag ist Verlauf, kein Beleg für den aktiven
Provider. Den zuletzt gewählten Stand der Desktop-App steht in
`~/.codex/.codex-global-state.json` unter `electron-persisted-atom-state` →
`composer-recent-model-configurations-v1` (oberster Eintrag = zuletzt gewählt).

## 3. Ablauf beim Ändern

1. **`LastWriteTime` prüfen** — mehrere Sitzungen und Bots schreiben in dieselben Dateien.
2. **Sicherung mit Zeitstempel**, Pfad nennen: `cp <datei> <datei>.bak-$(date +%Y%m%d-%H%M%S)`
3. **Zeile exakt ersetzen**, als Datei schreiben (`open(p,'rb')`), nicht per Heredoc:
   diese Config-Dateien sind LF, und ein Muster mit `\n` findet in einer
   CRLF-Datei nichts.
4. **Syntax parsen** (`tomllib.load`), nicht nur lesen.
5. **Echter Lauf als Nachweis** — `scripts/codex-provider-lauf-pruefen.sh`.
   Ein geparstes File beweist nicht, dass das Modell annonciert wird.
6. **Den Provider-Block behalten:** den unerwünschten Anbieter als
   `model_provider`-Default entfernen, seine `[model_providers.<name>]`-Sektion
   aber im File lassen — so bleibt er über `-c model_provider="<name>"` wählbar
   und nichts wird unrückgängig.
7. **App-Neustart mitteilen:** Desktop-Apps lesen ihre Config beim Start; ohne
   Neustart wirkt die Änderung nicht.

## 4. Modellnamen verifizieren, nicht übernehmen

Ein Modell, das eine App anbietet, ist damit noch nicht vom anderen Client
annonciert. Ein im Desktop-Picker angebotener Name wurde von derselben CLI mit
`HTTP 400 … is not supported when using Codex with a ChatGPT account`
zurückgewiesen. Deshalb die gesetzte `model`-Zeile direkt durch einen echten Lauf
prüfen; schlägt sie fehl, die Zeile weglassen — der Client nimmt dann sein eigenes
Standardmodell — und den im Lauf gemeldeten Namen als Modell verwenden.

## 5. Nicht still umkonfigurieren

Steckt einer von zwei geforderten Clients an der Drahtformat-Grenze: die umsetzbare
Hälfte ändern, die Grenze mit Beleg benennen, die Rückfrage einmal stellen. Läuft
die Rückfrage in ein Zeitlimit, den umsetzbaren Teil allein ausführen und im Bericht
trennen: was geändert wurde, was nicht ging und warum. Ein stilles Weglassen
erzeugt „ich hab dir gesagt, mach es", ein stilles Überschreiben eine Änderung,
die niemand bestellt hat.
