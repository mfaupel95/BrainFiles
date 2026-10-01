---
name: hermes-config-ops
description: "Use when Config, .env oder Profile zu aendern sind."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, config, secrets, soul, persona, brainfiles, verifikation]
    related_skills: [skill-library-sync]
---

# Hermes' eigene Konfiguration ändern

Änderungen an `Agenten/Hermes/config.yaml` und `.env` so ausführen, dass kein
Geheimnis im Klartext in der Konfiguration steht, laufende Agenten unberührt
weiterlaufen und die Änderung mit einem echten Lauf belegt ist.

## When to Use

- "da steht ein Schlüssel im Klartext", "der Token gehört da nicht rein",
  "fix das, ohne die Agenten zu stören"
- eine Einstellung in `config.yaml` soll anders sein (Arbeitsverzeichnis,
  Backend, Timeout)
- nach einem Update oder Setup, das Werte materialisiert hat
- der Agent soll dauerhaft anders antworten (Stil, Ton, Form) — das ist kein
  Skill, sondern `SOUL.md` (references/soul-persona.md)
- "wo trage ich diesen Schlüssel ein / mit welchem Befehl setze ich die
  Umgebungsvariable" — erst die Ablage nach dem Verbraucher entscheiden, dann
  setzen und am laufenden Dienst belegen (nicht nur "steht drin")

**Don't use for:** MCP-Server-Einträge zwischen Claude und Hermes (`mcp-sync`),
Skill-Kopien (`skill-library-sync`), Update/venv/SQLite (`hermes-maintenance`).

## Regeln (immer)

1. **Drei Ablagen, nach Verbraucher getrennt.** Mensch → `Wissen/Zugaenge.md`
   (nie lesen, nie ausgeben, nie protokollieren). Hermes →
   `Agenten/Hermes/.env` (je Profil eine Kopie). Verbraucher außerhalb von
   Hermes (MCP, Claude, Skript, curl) → Windows-Benutzervariable
   `HKCU\Environment`. Einen Wert, den eine Ablage schon hält, nie ein zweites
   Mal ablegen. `config.yaml` enthält nur `${NAME}`-Verweise.
2. **Kein Geheimnis in eine Kommandozeile.** Werte in der Datei lesen; ausgeben
   nur Länge und SHA-256-Anfang. Vergleichen über Hashes, nie über Werte. Auch
   eine Vorschau ist eine Ausgabe — `.env` nur NAMEN und Längen zeigen.
3. **Nie einen laufenden Agenten neu starten.** Beleg: `hermes gateway status`
   vor und nach der Änderung.
4. **Stufe 1:** vor jeder Änderung an `Agenten/Hermes/**`
   `Agenten/Hermes/.sicherung/<datei>.bak-JJJJMMTT`.
5. **Genau eine Zeile, wo eine Zeile gemeint ist.** Belegen mit `Compare-Object`
   Sicherung gegen Datei — genau ein Zeilenpaar.
6. **Kodierung erhalten.** BOM und LF/CRLF vorher bestimmen, danach gegenprüfen.
7. **Vault-Notiz nachziehen** (`Wissen/Hermes.md`, Stufe 1 → vorher
   `.bak-JJJJMMTT`), dann `git -C <BrainFiles> commit --author="Hermes
   <hermes@local>" -- <pfad>` — nur benannte Pfade, nie `-A`. Vor dem Schreiben
   `git status --porcelain <pfad>` und `git diff --cached <pfad>` lesen; fremd
   Gestagetes nie mitcommitten.

## Index — references laden, wenn ...

- references/soul-persona.md — laden, wenn der Agent dauerhaft anders antworten soll (SOUL.md statt Skill)
- references/klartext-verweis.md — laden, wenn ein Klartext-Geheimnis in config.yaml auf einen ${NAME}-Verweis umgestellt wird
- references/benutzervariablen.md — laden, wenn ein Zugangswert fuer einen Verbraucher ausserhalb von Hermes (MCP, Claude, Skript, curl) gesetzt oder geprueft wird
- references/docker-sandbox.md — laden, wenn Tools im Docker-Backend Variablen nicht sehen (${env:NAME} leer)
- references/mcp-server-anbinden.md — laden, wenn ein fremder MCP-Server (HTTP/OAuth) angebunden werden soll
- references/config-gegenprobe.md — laden, wenn "optimier meine Config" / "warum greift die Einstellung nicht" / nach Update
- references/einstellung-umstellen.md — laden, wenn eine einzelne Einstellung umgestellt wird (Wert setzen mit Beleg)
- references/fallback-kette.md — laden, wenn die Fallback-Kette aufgebaut, geprueft oder repariert wird
- references/hauptmodell-provider.md — laden, wenn das Hauptmodell auf einen anderen Provider umgestellt wird
- references/config-zusammenfuehren.md — laden, wenn config.yaml fremde Aenderungen traegt und zusammengefuehrt werden muss
- references/profil-kanalzugangsdaten.md — laden, wenn ein Bot-Token/Photon-Zugang einem Profil zugeordnet oder entfernt wird
- references/profilflotte-audit.md — laden, wenn mehrere Profile auf einmal geprueft/repariert werden ("ein Bot antwortet nicht")
- references/repo-bot.md — laden, wenn ein Bot fuer ein Fremd-Repo angelegt wird (Geschwisterprofil kopieren)
- references/profil-ohne-repo.md — laden, wenn ein Profil OHNE Repo (Hausordner/Wartungsbot) angelegt wird
- references/modell-anmeldung.md — laden, wenn ein Profil keine Modell-Anmeldung hat ("/bot NAME antwortet nicht")
- references/modellwechsel-flotte.md — laden, wenn ein Modellwechsel ueber viele Profile laeuft
- references/desktop-multiplex.md — laden, wenn die Desktop-App nur das default-Profil zeigt oder multiplex-Probleme hat
- references/fallen.md — laden, wenn eine Aenderung an config.yaml/.env unerwartete Nebenwirkungen zeigt
- references/auswahllisten-erweitern.md — laden, wenn eine Modell-/Auswahlliste unvollstaendig ist oder gekuerzt werden soll

## Nachweis (Abschluss)

- `scripts/config-wert-pruefen.py` meldet denselben `sha8` wie vorher.
- `Compare-Object` Sicherung ↔ Datei: genau eine geänderte Zeile.
- `hermes gateway status`: Aufgabe registriert, Prozess läuft — ohne Neustart.
- `Wissen/Hermes.md` nennt Änderung, Prüfweg, Sicherungspfad und Falle; committet.
