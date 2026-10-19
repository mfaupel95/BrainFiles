---
name: fremdrepos-signal
description: "Adapter-Contract: externe Trading-Repos (agent-trade-kit, kraken-cli) als typisiertes Signal liefern. MCP-Rohmaterial bleibt im Bot-Kontext; Handel/ sieht nur das Schema."
license: MIT
metadata:
  hermes:
    tags: [handel, signal, adapter, okx, kraken, mcp]
    related_skills: [fremdrepo-agent-start, handel-risikosteuerung]
---

# Fremdrepos-Signal — Adapter-Contract

Externe Trading-Repos liefern Signale. Sie werden NICHT ausgeführt.
Ausführung liegt ausschließlich bei `Handel/` hinter dem `wachen.json`-Gate.

## Wann

Ein Hermes-Bot-Profil (Bereich `bot`) delegiert über Topic `handel` und soll
ein Signal von `agent-trade-kit` (OKX-Demo) oder `kraken-cli` (Papier) holen.

## Designregeln (Atlas-Begründung)

- **Dediziertes Profil je Repo** — OKX und Kraken haben verschiedene
  Credentials und Effect-Authorities. Geteiltes Profil = vermischte Worlds.
- **Skill = Signal-Producer (pure/isolated)** — MCP-Rohmaterial bleibt im
  Bot-Profil-Kontext, erreicht nie `Handel/`. Nur das typisierte Signal-Schema
  verlässt den Skill.
- **Stale-Verwurf an der Skill-Naht** — Ein Signal mit `ts_utc` älter als
  `expiry_s` Sekunden wird VERWORFEN, bevor es den Heartbeat-Gate erreicht.
  Kein Retry über das 180-min-Fenster hinaus.
- **Gate vor Execution** — Das `wachen.json`-Gate prüft das Schema. Irreversibles
  (Papier-Orders) erst nach Gate-Freigabe. Live-Handel nur nach explizitem Ja.

## Signal-Schema (Contract Keystone)

```json
{
  "instrument": "BTC/USD",
  "venue":      "okx | kraken",
  "direction":  "long | short | flat",
  "size_pct":   0.5,
  "source":     "agent-trade-kit | kraken-cli",
  "ts_utc":     1728432000,
  "expiry_s":   180,
  "mode":       "paper | demo",
  "confidence": 0.72,
  "grund":      "freier Text (optional)"
}
```

Pflichtfelder: `instrument`, `venue`, `direction`, `source`, `ts_utc`, `expiry_s`, `mode`.
`mode` darf NICHT `live` sein — Gate weist das zurück.

## Vorgehen

1. MCP-Tool des Bot-Profils aufrufen (kraken-native oder okx-trade-mcp).
2. Antwort ins Schema übersetzen. Fehlende Pflichtfelder → Signal verwerfen, Grund melden.
3. Stale-Check: `now_utc - ts_utc > expiry_s` → verwerfen, KEIN Retry.
4. Validiertes Signal-Objekt an `Handel/` übergeben (JSON-Datei oder Bus).
5. `Handel/` prüft gegen `wachen.json`. Gate-Ergebnis ist final.

## Verfügbare Bot-Profile

| Profil | Repo | MCP-Services | Modus |
|---|---|---|---|
| `agent-trade-kit` | Werkstatt/agent-trade-kit | okx-trade-mcp (Demo) | demo |
| `kraken-cli` | Werkstatt/kraken-cli | market, paper, workspace | paper |

## Grenzen

- Keine Live-Ausführung aus diesem Skill heraus.
- Keine Credentials im Skill oder in Ausgaben — nur Vorhandensein und Länge melden.
- Signal-Fan-out: jedes Profil separat, Ergebnis je als eigenes Schema-Objekt.
- Für den okx-trade-mcp: Paket muss zuerst gebaut werden (`pnpm build` im Repo).

## Nächste Schritte (Phase 2)

- `agent-trade-kit` MCP-Server in Profil eintragen (nach `pnpm build`).
- Bus-Integration: Signal-Schema in `Agenten/Bus/` als Nachrichtentyp definieren.
- `wachen.json`-Gate um `fremdrepo_signal`-Typ erweitern.
- Tests: Signal-Validierung in `Agenten/Handel/tests/test_signal_schema.py`.
