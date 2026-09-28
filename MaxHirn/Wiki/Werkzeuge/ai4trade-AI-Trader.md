---
titel: AI-Trader (ai4trade.ai) — Agent angemeldet
aktualisiert: 2026-09-28
tags: [werkzeug, handel, plattform]
---

# AI-Trader / ai4trade.ai — Zugang im Haus

> **Kurz:** Der Agent **`HermesMax`** ist auf `https://ai4trade.ai` angemeldet
> (Agent-ID **25970**, Papierkonto 100.000 USD). Die Kennung liegt in
> `Agenten/Handel/ai4trade/.env` (per `.gitignore` Zeile 265 `**/.env` gesperrt).
> Der Endpunkt `GET /api/claw/agents/me` gibt das Token **im Klartext zurueck** —
> eine Ausgabe dieses Aufrufs gehoert nie in ein Protokoll oder einen Chat.

AI-Trader ist eine **Signalplattform mit Papierhandel** (simuliertes Guthaben,
Punkte, Reputation, Challenges). Kein echter Orderweg, kein Boersenzugang: hier
wird nichts von Max' Geld bewegt. Ein Agent veroeffentlicht Signale, folgt
anderen Tradern oder tritt Wettbewerben bei.

## Was im Haus liegt

| Pfad | Inhalt |
|---|---|
| `Agenten/Handel/ai4trade/.env` | `AI4TRADE_EMAIL`, `AI4TRADE_PASSWORD`, `AI4TRADE_TOKEN` — gesperrt, nie ausgeben |
| `Agenten/Handel/ai4trade/skill/SKILL.md` | Hauptskill (34.037 B, identisch mit dem Alias `https://ai4trade.ai/SKILL.md`) |
| `Agenten/Handel/ai4trade/skill/<kind>/SKILL.md` | Kind-Skills `copytrade`, `tradesync`, `heartbeat`, `polymarket`, `market-intel` |

Die Skill-Dateien liegen **absichtlich hier** und nicht in der
Hermes-Bibliothek: die Anleitung `~/.openclaw/skills/...` aus dem Skill gilt fuer
OpenClaw, nicht fuer dieses Haus (Skill `fremde-skill-sammlung-einbinden`).

## Der Weg hinein (nachpruefbar)

```bash
cd Agenten/Handel/ai4trade
python - <<'PY'
import json,urllib.request,pathlib
tok=[l.split('=',1)[1].strip() for l in pathlib.Path('.env').read_text().splitlines()
     if l.startswith('AI4TRADE_TOKEN=')][0]
req=urllib.request.Request('https://ai4trade.ai/api/claw/agents/me',
                           headers={'Authorization':'Bearer '+tok})
print(json.loads(urllib.request.urlopen(req,timeout=45).read().decode())['name'])
PY
```

Registrierung selbst: `POST /api/claw/agents/selfRegister` mit `name`, `email`,
`password`. Antwort enthaelt `token`, `agent_id`, `name`.

## Gemessener Stand 28.09.2026

- Anmeldung: `selfRegister` -> `agent_id 25970`, Token 43 Zeichen.
- `GET /api/claw/agents/me` -> `name HermesMax`, `cash 100000.0`, `points 0`,
  `reputation_score 0`, `role agent`, `identity_status normal`, `is_verified false`.
- `POST /api/claw/agents/heartbeat` -> HTTP 200, `message_count 0`,
  `recommended_poll_interval_seconds 30`.
- Die Basis-URL ist `https://ai4trade.ai/api`; **kein** zweiter Host, keine
  Boersenanbindung, keine Schluessel fuer einen Orderweg.

## Was NICHT angeschlossen ist

- **Heartbeat wird nicht gepollt.** Der Skill nennt ihn „part of normal
  operation" (Antworten, Erwaehnungen, neue Follower kommen nur dort an). Ein
  einzelner Testaufruf ist gemacht, eine Wache/Routine fehlt (offener Punkt).
- Keine Signale veroeffentlicht, keinem Trader gefolgt, keinem Challenge
  beigetreten — das ist eine Entscheidung, kein technischer Schritt.
- Die Kennung steht noch **nicht** in `Wissen/Zugaenge.md` (Stufe 0, dort ist die
  einzige Ablage; Nachtragen ist Handarbeit).

## Merksatz

Ein „Skill" einer fremden Plattform ist zuerst eine **API-Beschreibung**, kein
Hausverfahren. Erst die Endpunkte pruefen, dann eine eigene Kopie ablegen — und
Zugangsdaten dorthin, wo sie hingehoeren, nicht in den Skill-Ordner.

## Heartbeat — der einzige Weg, auf dem etwas ankommt (T-113, 29.09.2026)

Der Heartbeat ist kein Gimmick: Antworten auf eigene Beitraege, Erwaehnungen,
neue Follower und Aufgaben kommen **ausschliesslich** dort an, nicht per Mail.
Ohne Polling ist der Agent passiv — genau das war bis zum 28.09.2026 der Fall.

Gepollt wird jetzt von:

- `Agenten/Handel/ai4trade/heartbeat.py` — die Logik (liest die `.env` selbst,
  Ausgabe ist nur NEUES, leere Ausgabe = nichts senden, Zustand in
  `ai4trade/cache/heartbeat-stand.json`)
- `Agenten/Hermes/scripts/ai4trade-heartbeat.py` — duenne Cron-Bruecke (der
  Scheduler laeuft nur Skripte aus `Agenten/Hermes/scripts/`)
- Hermes-Cron `ai4trade-heartbeat`, Job `2f886828dcdf`, alle 5 min, `no_agent`,
  Ausgabe nach Telegram

```
cd Agenten/Handel/ai4trade
python heartbeat.py --pruefen     # Zugang und Zustand, keine Ausgabe an Telegram
python heartbeat.py               # nur Neues
python heartbeat.py --alles       # auch schon Gemeldetes
```

### Die Auth-Falle

Der Plattform-Skill (`skill/heartbeat/SKILL.md`) nennt den Kopf
`X-Claw-Token: <token>`. Die API antwortet damit am 28.09.2026 **401
`{"detail":"Invalid token"}`** — derselbe Aufruf mit
`Authorization: Bearer <token>` liefert 200. `heartbeat.py` probiert beide Wege,
damit eine spaetere Umstellung nicht still ausfaellt.

### Die Echo-Falle

Fehlerantworten dieser API enthalten das Feld `input` — also den **gesamten
Anfragetext inklusive Passwort** im Klartext (bei einem 422 gesehen). Wer eine
Antwort dieser Plattform roh protokolliert oder ausgibt, schreibt ein Geheimnis
in den Verlauf. `heartbeat.py` wertet bei Fehlern nur `detail.loc` aus, niemals
`input`. Das Passwort des Agenten wurde am 28.09.2026 einmal so sichtbar →
eigenen Punkt in `TASKS.md` (T-116).
