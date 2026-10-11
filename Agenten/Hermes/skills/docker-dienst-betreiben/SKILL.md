---
name: docker-dienst-betreiben
description: "Use when ein Docker-Dienst headless aufgesetzt wird."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
category: brainfiles
metadata:
  hermes:
    tags: [Docker, Dienst, Headless, Workflow, Waechter]
---

# Einen Docker-Dienst selbst hosten (headless)

Gilt fuer lokale Dienste, die als Docker-Container laufen und ohne UI eingerichtet
werden sollen: n8n, freqtrade, ollama, nautilus-demo. Der Ablauf ist immer
derselbe: Container mit Daten-Volume und Restart-Policy starten, Konfiguration
und Workflows headless (per CLI/API) einspielen, Bereitschaft belegen, Wache als
Hermes-Cron.

## When to Use

- „X im Docker aufsetzen / selbst hosten / lokal betreiben“
- „Workflow importieren / Dienst headless konfigurieren“
- Ein lokaler Dienst soll mit Windows neu starten und nicht an eine Sitzung
  gebunden sein

## Ablauf

1. **Daten-Volume, nicht Container-Dateien.** Alle Zustandsdaten (DB, Workflows,
   Credentials) in ein gemountetes Verzeichnis legen, das in die Sicherung geht
   (z.B. `Agenten/Hermes/cache/<dienst>-data`). Container loeschen/neu bauen
   verliert dann nichts. Start mit `--restart unless-stopped` und
   `-p 127.0.0.1:<port>:<port>` (nur localhost, kein Netz).
2. **Headless konfigurieren, nicht per UI-Klick.** Der Dienst hat fast immer eine
   CLI oder API fuer Import/Export (`docker exec <dienst> <dienst> import:...`).
   Die UI ist fuer den Menschen, nicht fuer die Einrichtung.
3. **Bereitschaft belegen, nicht nur Liveness.** `curl /healthz` = 200 ist der
   Start; der erste echte Durchstoss (z.B. Webhook-POST -> Datei) beweist, dass
   der Workflow wirklich laeuft. Zwei echte Eingaben, Container-Neustart
   ueberlebt.
4. **Wache als Hermes-Cron** (Muster in `dauerprozess-bewachen`): healthz
   pruefen, bei tot `docker start <container>` (heilen), Befund/Erholung melden,
   leere Ausgabe = nichts senden.

## Fallen

- **CLI-Aenderungen wirken erst nach Neustart.** `update:workflow --active=true`
  (n8n) schreibt nur die DB; der Webhook antwortet erst nach `docker restart`.
  Nach jeder headless Aenderung: restart, dann erneut testen.
- **Sandbox blockt Module.** Code-/Script-Knoten laufen in einer Sandbox, die
  Node-Core-Module (z.B. `fs`) sperrt. Erlaubnis per Env beim Container-Start
  (`NODE_FUNCTION_ALLOW_BUILTIN=fs`).
- **Import verlangt Pflichtfelder.** Workflow-Import scheitert still an fehlenden
  Root-Feldern (z.B. `id`). Fehlermeldung lesen, Feld ergaenzen, erneut
  importieren.
- **Zugangsdaten des Dienstes in die Schluesselablage, nie in den Chat.**
  Owner-Konto automatisch anlegen, Passwort generieren und in
  `Wissen/Zugaenge.md` haengen (Muster: ai4trade/neu_anlegen.py). Nie ausgeben.

## Referenzen

- `references/n8n.md` — konkrete n8n-Rezepte (Container, Workflow-Import, Fallen)
