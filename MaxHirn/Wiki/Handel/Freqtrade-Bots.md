---
id: 20260930-freqtrade-bots
title: 'Freqtrade-Bots aus den Moon-Dev-Agenten'
tags: [handel, freqtrade, bots, backtest]
created: 2026-09-30
updated: 2026-09-30
related: ['[[Handel/Spuren-Uebersicht]]', '[[Handel/Backtest-Fundament]]', '[[Handel/Kosten-und-Bedingungen]]', '[[Betrieb/Docker-und-Sandbox]]', '[[Betrieb/Systemleistung-2026-09-29]]']
summary: 'Wie die drei Moon-Dev-Agenten als Freqtrade-Bots laufen, was der erste echte Backtest ueber sie sagt (alle drei negativ, Kosten = Verlust) und warum sie trotzdem im Probebetrieb laufen.'
---

# Freqtrade-Bots aus den Moon-Dev-Agenten

Die alte Aufgabe: die Agenten aus `Werkstatt/Repos/moon-dev-ai-agents` nach
Freqtrade uebertragen. Die Uebertragungsliste liegt in
`Agenten/Handel/freqtrade/bots.json` — **3 portiert, 11 nicht portierbar**,
dazu die Eintraege unter `als_schutzschicht_portiert` (das
`risk_agent`-Verhalten steckt jetzt als Freqtrade-Schutzschicht in allen Bots).

## Was laeuft

| Bot | Container | Port | Strategie | Paare | Plaetze |
|---|---|---|---|---|---|
| Trading Agent | `freqtrade-trading-agent` | 8081 | `MoonDevTradingAgent` | 12 | 4 |
| Top Movers | `freqtrade-topmovers` | 8082 | `MoonDevTopMovers` | 24 | 3 |
| Marktlage/Regime | `freqtrade-marktlage-regime` | 8083 | `MoonDevMarketRegime` | 1 | 1 |
| (Vorgaenger) | `freqtrade` | 8080 | `SampleStrategy` | — | — |

Alle drei: `dry_run: true`, Zeitrahmen 1h, je eine **eigene Datenbank**
(`user_data/tradesv3-<bot>.sqlite`). Ohne eigene Datei schreiben alle drei in
dieselbe `tradesv3.sqlite` und die Buecher sind nicht mehr zu trennen —
`--db-url` ist kein Beiwerk, sondern die Trennung.

Start: `bash Agenten/Handel/freqtrade/bots_starten.sh` (legt die Container neu
an, `--restart unless-stopped`; nach einem Docker-Neustart kommen sie von
selbst wieder).

## Die Aufsaetze (Overlays)

Jeder Bot hat in `user_data/bots/<name>.json` nur seinen **Aufsatz**:
Strategie, Zeitrahmen, Plaetze, `dry_run`, API-Port, Paarliste. Zugangsdaten,
Boerse und Risiko bleiben in `user_data/config.json`. Freqtrade mischt mehrere
`--config` tief ineinander, deshalb sind es zwei Dateien statt einer Kopie —
so liegen die Zugangsdaten der Weboberflaeche genau einmal auf der Platte.

**Falle (gemessen 30.09.2026):** der Aufsatz setzte zuerst
`api_server.listen_ip_address = 127.0.0.1`. Das ist IM Container der eigene
Loopback — die Weboberflaeche war von aussen nicht erreichbar, alle drei Bots
antworteten mit `ConnectionReset`. Richtig ist `0.0.0.0` im Container; die
Absicherung nach aussen macht das Port-Mapping `-p 127.0.0.1:<port>:<port>`.
Eine Bindung an den Loopback ist kein Schutz, sondern ein Defekt.

## Was der Backtest sagt — und zwar zum ersten Mal

Die drei Strategien waren **nie gemessen** worden. Am 29.09.2026 wurden dafuer
24 Paare auf 1h ueber zwei Jahre geladen (2024-09-29 → 2026-09-29, gleiche
Laenge bei allen Paaren), dann gerechnet:

| Strategie | 2 Jahre | H1 (2024-10…2025-09) | H2 (2025-09…2026-09) |
|---|---|---|---|
| `MoonDevTradingAgent` | **−66 %** (Treffer 25 %, max. Rueckgang 83 %) | −62,9 % (1543 Trades) | −55,5 % (1418 Trades) |
| `MoonDevTopMovers` | negativ | −18,3 % (608) | −33,9 % (316) |
| `MoonDevMarketRegime` | negativ | −25,5 % (113) | −15,9 % (98) |

**Kein einziges Fenster positiv.** Und der Grund ist nicht die Richtung,
sondern die Frequenz: `MoonDevTradingAgent` macht 3,23 Trades pro Tag. In der
Config steht kein `fee`, also rechnet Freqtrade mit der Boersengebuehr
(Binance 0,1 % je Seite = 0,2 % je Runde). Bei 3,23 Runden/Tag sind das über
**240 % Kosten im Jahr** — mehr, als jede Strategie erwirtschaften kann. Der
Beleg steht im Backtest selbst: Gebuehren 8.399 USDT gegen ein Ergebnis von
−8.335 USDT. **Der Verlust IST die Gebuehr.**

## Warum sie trotzdem laufen

Die Bots laufen im Probebetrieb, weil die Messung zwar die Strategie
verurteilt, aber der Auftrag war, die Uebertragung nach Freqtrade
nachvollziehbar zu machen — und weil ein laufender Papierbot die Frage
„warum verliert der?" jeden Tag neu und mit echten Kursen beantwortet.
**Scharf gestellt wird hier nichts:** `dry_run: true`, kein Orderweg, kein
Guthaben, keine Freigabe. Ein Live-Betrieb dieser drei waere nach dieser
Messung nicht zu verantworten.

Der naheliegende naechste Schritt ist nicht ein Parameter, sondern die
**Frequenz**: die Vorfilter der Feed-Spuren (`Handel/risikovorfilter.py`,
Handelszentrum) und die Sperrfrist nach Ziel-Ausstieg
(`handeln.in_zielsperre`) existieren im Haus schon — sie fehlen nur in der
Freqtrade-Uebertragung.

## Was am 30.09.2026 dazwischenkam

Beim Start der Bots starb der Docker-Daemon und nahm **alle** Container mit.
Ursache war kein Fehler der Bots: **Commit-Erschoepfung** (1,0 GB frei von
86,4 GB), ausgeloest von einem MCP-Spawn-Sturm — der Gateway gleicht alle paar
Minuten die MCP-Server mit der Config ab, wollte `MCP_DOCKER`
(Docker-MCP-Server) starten, Docker war gerade weg, und daraufhin startete der
Abgleich jedes Mal **alle sechs lokalen Gruppen** neu: 146 Python-Prozesse.
Ohne Commit kann die WSL-VM nicht hochkommen, ohne VM kein Docker — ein
geschlossener Kreis. Einzelheiten und die Kur stehen in
[[Betrieb/Systemleistung-2026-09-29]].

Die Bots selbst haben das ueberlebt: `--restart unless-stopped` brachte alle
drei von allein zurueck, sobald Docker wieder lief.

## Offen

- Die Frequenz-Bremse aus dem Haus fehlt in der Uebertragung (siehe oben).
- `bots.json` nennt 11 Agenten als **nicht portierbar** — die Gruende stehen
  dort je Eintrag und sind nicht nachgeprueft worden.
- Der Vorgaenger-Container `freqtrade` (8080, `SampleStrategy`) laeuft weiter
  und hat keinen Zweck mehr; er wurde nicht angefasst.