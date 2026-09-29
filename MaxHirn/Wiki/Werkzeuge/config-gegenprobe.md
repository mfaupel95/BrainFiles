---
id: 20260929-config-gegenprobe
title: 'Config-Gegenprobe — Behauptung gegen Wirklichkeit'
tags: [werkzeug, hermes, konfiguration, wache]
created: 2026-09-29
updated: 2026-09-29
related: ['[[Lektionen/Wahrheit-pruefen]]', '[[Betrieb/Hermes]]', '[[Werkzeuge/Bonsai-2-27B]]']
summary: 'Ein Aufruf prueft jede Behauptung der Hermes-Configs gegen die Wirklichkeit: Programmpfade, lokale Adressen, lokale Modellnamen. Am 29.09.2026 fand er vier erfundene Modellnamen in 18 Configs.'
---

# Config-Gegenprobe

## Regel

**Eine Config ist eine Sammlung von Behauptungen.** Jede Zeile sagt: dieser Pfad
existiert, dieser Dienst laeuft auf diesem Port, dieses Modell liegt im Store.
Faellt eine davon aus, meldet **nichts** einen Fehler — die Zeile wird erst
gebraucht, wenn der Hauptweg schon weggebrochen ist. Deshalb wird jede
Behauptung einmal gegen die Wirklichkeit gehalten, nicht gegen die Erinnerung.

## Aufruf

```
cd Agenten/Hermes
python scripts/config-gegenprobe.py            # Bericht, rein lesend
python scripts/config-gegenprobe.py --json     # maschinenlesbar
```

Rueckgabe 0 = alles belegt, 1 = mindestens ein Befund.

## Was geprueft wird

| Pruefung | Gegen was | Warum |
|---|---|---|
| `command:` jedes MCP-Servers | Dateisystem | Ein fehlender Interpreter laesst den Server still ausfallen |
| Jede lokale Adresse (`127.0.0.1`, `localhost`) in Hauptconfig und 22 Profilen | TCP-Port | Ein Port ohne Dienst ist ein Rueckfall, der nicht greift |
| Jeder lokale Modellname (Provider `ollama-launch`) samt `models:`-Liste | `/api/tags` des laufenden Ollama | Ein Name, den der Dienst nicht kennt, faellt erst im Notfall auf |

## Befund vom 29.09.2026 (Anlass des Werkzeugs)

- **Vier erfundene Modellnamen** in der `models:`-Liste von Hauptconfig und
  17 Profilen: `qwen3.8:27b`, `qwen3.8:latest`,
  `huihui_ai/qwen3-abliterated:32b`, `kimi-k2.7-code:cloud`. Im Store lagen
  andere Namen. Der Vorgabewert war am selben Abend schon gerichtet, die Liste
  nicht — dieselbe Behauptung, zwei Stellen.
- **`providers.bonsai` zeigte auf Port 8080** — dort antwortete die
  FreqTrade-Oberflaeche (HTTP 200), der Startbaustein
  `Werkzeuge/bonsai-27b.ps1` hat aber **8081** als Vorgabe. Zwei Zahlen fuer
  dieselbe Sache; eine davon war eine fremde Anwendung.
- **`localhost:6767`** (`SSE_URL` des affinity-Servers) ist in 18 Configs
  eingetragen und antwortet nicht. Der Server selbst arbeitet trotzdem
  (`hermes mcp test affinity` listet seine Werkzeuge) — der Eintrag ist ein
  Rest, kein Ausfall. **Kein Fehlalarm daraus machen:** eine tote Adresse ist
  erst dann ein Befund, wenn der zugehoerige Weg sie wirklich braucht.

## Gegenprobe in beide Richtungen

Der erste Lauf des Werkzeugs meldete `auto/coding:free` als „nicht im Store" —
ein **Fehlalarm**: der Block `fallback_providers:` (Spalte 0) erbte die
Einstufung „lokaler Provider" vom letzten `providers:`-Block. Behoben, indem
jeder Schluessel in Spalte 0 die Einstufung zuruecksetzt. Ein Pruefer ohne
Gegenprobe produziert Reparaturen an Stellen, die in Ordnung sind.

## Wache

`scripts/config-gegenprobe-wache.py` (Hermes-Cron `config-gegenprobe`, montags
07:40, `no_agent`, Telegram, **leere Ausgabe = nichts senden**). Sie fuehrt die
Gegenprobe aus und meldet **nur Aenderungen** — ein neuer fehlender Pfad, eine
neu tote Adresse, ein Modell, das aus dem Store faellt. Der Merker liegt in
`cache/config-gegenprobe-wache.json`. Ohne diese Wache waere die Gegenprobe ein
Nachweis, den niemand von selbst aufruft — und ein Nachweis ist keine Wache.

```
python Agenten/Hermes/scripts/config-gegenprobe-wache.py --alle      # Lage immer zeigen
python Agenten/Hermes/scripts/config-gegenprobe-wache.py --vergessen # Merker loeschen
```

## Was es nicht tut

Es aendert nichts, es startet nichts, es urteilt nicht ueber Kosten oder
Sinnhaftigkeit einer Einstellung. Es nennt nur die Stellen, an denen die Config
etwas behauptet, das nicht stimmt.