---
titel: Ollama-Bruecke (OpenAI-kompatibel, think:false)
aktualisiert: 2026-09-24
tags: [werkzeug, sprachmodell, ollama, fremd-agenten]
---

# Ollama-Bruecke — der eine Weg zum lokalen Urteil ohne Schluessel

> **Falle zuerst:** Der Ollama-eigene OpenAI-Adapter (`/v1/chat/completions`)
> liefert bei **Denk-Modellen** einen **leeren** `content`. Gemessen am
> 24.09.2026 mit `qwen35-8k` und `gemma-e4b-8k`: `finish_reason: length`, der
> Text steht im Feld `reasoning`, die 1500 Token waren vom Denken verbraucht.
> `"think": false` im `/v1`-Body wird **nicht durchgereicht**, und der
> Soft-Switch `/no_think` im Prompt wirkt hier ebenfalls nicht. Wer einen
> Fremd-Agenten auf `/v1` zeigt, bekommt stumme Agenten, keine Fehlermeldung.

## Was sie ist

`Agenten/Werkzeuge/ollama-openai-bruecke.py` — ein Dienst (nur
Standardbibliothek) auf **127.0.0.1:11499**. Sie nimmt den OpenAI-Aufruf
entgegen und ruft Ollama **nativ** (`/api/chat`) mit `"think": false` auf.
Damit laeuft jeder Agent, der seine Sprachmodell-Antwort ueber das OpenAI-SDK
holt, **ohne bezahlten Schluessel** und ohne eine Zeile Aenderung am Fremd-Repo.

- Zuordnung der Modellnamen (eine Stelle, kein `ollama cp`):
  `deepseek-chat`/`deepseek-coder`/`gpt-4o`/`gpt-3.5-turbo` → `qwen35-8k:latest`,
  `deepseek-reasoner` → `qwen36-35b-a3b:8k`. Namen mit Tag gehen unveraendert durch.
- Wege: `POST /v1/chat/completions`, `GET /v1/models`, `GET /gesundheit`.
- Protokoll (nur Zahlen, keine Inhalte):
  `Agenten/Hermes/cache/ollama-openai-bruecke.log`.

```bash
python Agenten/Werkzeuge/ollama-openai-bruecke.py --trocken   # Zuordnung zeigen
python Agenten/Werkzeuge/ollama-openai-bruecke.py --pruefen   # echter Aufruf + Dauer
curl -s http://127.0.0.1:11499/gesundheit
```

## In der .env des Fremd-Repos

```ini
DEEPSEEK_KEY=lokal-ollama
DEEPSEEK_BASE_URL=http://127.0.0.1:11499/v1
```

`DEEPSEEK_KEY` ist **kein** Anbieterschluessel, sondern nur ein nicht-leerer Wert
(die Agenten pruefen `if key:`); deshalb steht dort ein sprechender Platzhalter
und kein erfundenes Geheimnis.

## Wache und Anschluss

- Hermes-Cron `ollama-bruecke-wache` (Job `b0d33eee895f`, alle 15 min, `no_agent`,
  Skript `Agenten/Hermes/scripts/ollama-bruecke-wache.py`): leere Ausgabe =
  Bruecke laeuft; sonst startet sie der Waechter und meldet den Befund.
- Der MoonDev-Treiber (`Agenten/Handel/moondev_dauerlauf.py`) startet sie am
  Zykluskopf selbst (`_bruecke_sicherstellen`, leise wenn sie laeuft) und legt
  `DEEPSEEK_KEY`/`DEEPSEEK_BASE_URL` als **Vorgabe** in die Kindumgebung; der
  Nous-Weg des Agenten `new_or_top` ueberschreibt beides danach.

## Gemessene Zahlen (24.09.2026)

| Was | Wert |
|---|---|
| Ein Aufruf warm (qwen35-8k, 120 Token) | 0,7–1,6 s |
| Ein Aufruf ueber den OpenAI-Weg des Agenten | 4,0 s (erster, kalt) |
| `coingecko_agent`: komplette Runde zweier „AI-Agenten“ | lokal, ohne Schluessel, Urteile im Log |
| Antwort ohne Bruecke (`/v1` direkt) | **leer** (`finish_reason: length`) |
| Kleiner Text (8k Zeichen) ueber die Bruecke | 1 Aufruf, kein `num_ctx` im Rumpf |
| Grosser Text (150k Zeichen, ~60k Token) | **1 Aufruf**, Fenster automatisch auf 32768 angehoben, Umweg ueber den Nachbesserungspfad (2 Aufrufe) messbar langsamer |

### Das Kontextfenster ist die zweite Stummschaltung

Lokale Modelle sind auf **8192 Token** gebaut. Ist eine Anfrage groesser,
antwortet Ollama hart mit **HTTP 400** (`request (25219 tokens) exceeds the
available context size (8192 tokens)`) — der Fremd-Agent sieht nur „503 Ollama
nicht erreichbar“ und haelt die Bruecke fuer tot, obwohl sie laeuft. Die Bruecke
rechnet deshalb jetzt mit (`geschaetzte_token`, `ZEICHEN_JE_TOKEN = 2.5`
konservativ), hebt `num_ctx` in Zweierpotenzen bis **32768** an und kuerzt erst
darueber die **Mitte** des Textes (Kopf = Anweisung, Ende = frischeste Daten).
Kommt trotzdem eine „exceeds the available context size“-Antwort, wird die Mitte
gekuerzt und **erneut gesendet** (hoechstens drei Versuche) — der Agent bekommt
eine Antwort statt einer 503. Jede Kuerzung steht im Protokoll.

## Was ausdruecklich offen ist

- **Tote Datenquelle bleibt tot:** `whale_agent`, `funding_agent`,
  `liquidation_agent` und alles unter `src/agents/api.py` holen ihre Daten von
  `api.moondev.com` (Port 8000, antwortet nicht). Ein Schluessel hilft dort
  nicht — die Datenquelle selbst fehlt (Ersatz: siehe Skill
  `fremd-agenten-betrieb`, dort schon fuer `sniper_agent` gemacht).
- **Content-/Medienagenten** (Twitter, YouTube, Restream, ElevenLabs, Google)
  brauchen Fremdkonten und haben mit Handel nichts zu tun: nicht verdrahtet.

## Lektion (aus dem Umbau)

- **`import os` kann NACH der Konstantenzeile stehen.** In 5 der 11 Agenten
  stand `DEEPSEEK_BASE_URL = os.getenv(...)` **vor** dem Import → `NameError`
  beim Laden. Gemessen, bevor der Agent lief. Muster, das traegt: die Konstante
  bleibt, der **Aufrufort** liest die Umgebungsvariable (`base_url=os.getenv(...)
  or DEEPSEEK_BASE_URL`).
- Eine Umleitung, die „schluessellos“ heissen soll, muss am **Aufrufort der
  Bibliothek** ansetzen, nicht am Anbieternamen: die Fremd-Agenten waehlen ihren
  Weg nach `AI_MODEL`/Schluessel-Anwesenheit — die Umgebungsvariable ist der
  Hebel, der ohne Codeaenderung wirkt.
- **Nebenwege sprechen oft einen ANDEREN Client als der Hauptweg.** Im
  `coingecko_agent` bauten Token-Extraktor und Synopsis je ihren eigenen
  Anthropic-Client, waehrend die Haupturteile schon lokal liefen: das Haupturteil
  war „repariert“, zwei Drittel des Agenten aber tot. Muster, das traegt: **die
  Form des Clients abfragen** (`hasattr(client, "chat")` → OpenAI-Form,
  sonst Anthropic-Bloecke) und den Extraktor den Client uebergeben lassen
  (`TokenExtractorAgent(agent.client, agent.model)`) statt ihn einen eigenen
  bauen zu lassen. Eine Umleitung ist erst fertig, wenn **jeder** Aufruf im
  Modul durch sie laeuft — `grep -n "messages.create\|\.messages\b" <datei>`.
- **Ein Fehler im Nebenweg ist ein Fehler, kein Rauschen:** beide Ausfaelle
  standen als `❌ Error extracting tokens` / `Synopsis generation failed` im Log,
  waehrend die Runde „Complete“ meldete. Ein Agent, der seine Zusammenfassung
  still verliert, sieht fuer den Betreiber gesund aus.

Verwandt: [Betrieb/Wachen-und-Aufgaben.md](../Betrieb/Wachen-und-Aufgaben.md),
[Werkzeuge/openmontage.md](openmontage.md) (lokale Kette statt Cloud-Schluessel),
`fremd-agenten-betrieb` in der Skill-Bibliothek.