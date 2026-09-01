---
id: 20260831-marktscanner
title: 'Marktscanner OKX'
tags: [handel]
created: 2026-08-31
updated: 2026-08-31
related: [20260830-handelsbots, 20260830-schutzregeln, 20260830-routinen, 20260830-verbindungen, 20260831-python-versionen]
summary: 'Täglicher Krypto-Scanner mit begrenztem Selbsthandel auf OKX — Entscheidung, Grenzen, Scharfschalt-Weg und Stand.'
---

# Marktscanner OKX

Am 31.08.2026 gebaut auf Max' Anweisung: ein Agent, der täglich die großen
Krypto-Werte scannt, jeden auf **Chance gegen Risiko** bewertet und daraus
konkrete, hart begrenzte Handelsvorschläge macht — und diese im Rahmen fester
Grenzen **selbst** ausführen darf.

Code, Bedienung und das Bewertungsmodell im Detail:
`../Agenten/Handel/scanner/README.md`. Diese Notiz hält fest, was dort **nicht**
steht: die Entscheidung, ihre Grenzen und den Stand.

## Die Entscheidung

Die globale Regel „das Auslösen von Geldbewegungen bleibt bei Max" gilt
weiter — **außer für diesen einen Agenten**. Der Sonderfall ist in
[[Schutzregeln]] eingetragen (Abschnitt „Handel: was ein Agent selbst auslösen
darf", Spur 1). Er gilt für dieses Skript, nicht für Claude allgemein, und
nicht für die tägliche Routine.

**Seit 01.09.2026 ist er nicht mehr die einzige Ausnahme.** Gehebelte
Positionen laufen über Spur 2 derselben Regel und brauchen dort eine Anweisung
von Max je Vorgang. Für diesen Scanner ändert das nichts: Er bleibt Spot, Long,
ohne Hebel — was er von selbst darf, steht unverändert in `wachen.json`.

## Die Grenzen (in `scanner/wachen.json`, einzige Wahrheit)

| Grenze | Wert |
|---|---|
| je Trade | 50 USD |
| gesamt gebunden | 200 USD |
| offene Positionen | höchstens 4 |
| Pflicht-Stop | 4–12 %, nicht abschaltbar |
| Abklingzeit nach Stop-Out | 3 Tage je Wert |
| Tore für einen Vorschlag | Score ≥ 60, Volatilität p.a. ≤ 1,2, Chance/Risiko ≥ 1,5 |
| Instrumente | nur Spot, nur Long, kein Hebel |

Die Betragsgrenze deckt sich mit der bestehenden OKX-Agentic-Wallet-Politik
(50 USD je Transaktion, siehe [[Verbindungen]]).

## Drei Sperren vor echtem Handel

`handeln.py --live` handelt nur scharf, wenn **alle drei** offen sind:

1. `wachen.json` → `handel_erlaubt: true`
2. `OKX_API_KEY` / `OKX_API_SECRET` / `OKX_API_PASSPHRASE` als
   Windows-Benutzervariablen — **nicht** in [[Zugaenge]], nicht neben den Code.
   `okx.py` liest sie ersatzweise aus der Registry, wie der Kraken-MCP.
3. `--live` ausdrücklich auf der Kommandozeile.

Fehlt eine, läuft Papierhandel und es wird gesagt, welche Sperre zu war.

## Stand 2026-08-31

- **Papierhandel läuft.** Scan und Vorschläge getestet, 6 von 15 Werten
  passierten am 31.08. die Tore (SOL, LINK, BTC, ETH, BNB, LTC).
- **Live-Handel noch nie scharf gelaufen.** Sperre 1 ist zu, Sperre 2 leer.
  Die OKX-Schlüssel in `Claude/Worktrees/investment/OKX_API.env` sind unbrauchbar
  (Secret 6 statt 32 Zeichen, siehe [[Zugaenge]]) — es braucht ein neues Paar
  mit Handelsrecht.
- **Der Live-Order-Pfad ist ungetestet** (`okx.markt_kauf` / `markt_verkauf` /
  `stop_setzen`). Vor dem ersten scharfen Lauf einen einzelnen Wert mit
  Kleinstbetrag von Hand ausführen und in der OKX-Oberfläche gegenprüfen.

## venvs — Stand nach dem Python-Neustand (31.08.2026)

Beide venvs laufen jetzt auf **Python 3.13.15** (Systemstandard, siehe
[[Python-Versionen]]):

- `scanner/.venv` — nur Standardbibliothek, am 31.08. neu gebaut.
- `../Agenten/Handel/.venv` (DCA-Agent) — war tot (Basis-Python `C:\Python314`
  weg, jeder Aufruf Exit 103; die DCA-Routine meldete am 30.08. noch „ENDE ok"
  und lief seither ins Leere). Am 31.08. neu gebaut, `pandas`/`numpy`/`yfinance`/
  `requests` installiert, `agent.py check` verifiziert. Neu: `Handel/requirements.txt`
  (pip freeze) für den nächsten Wiederaufbau. Der tote Alt-Ordner liegt als
  `Handel/.venv.kaputt-20260831` daneben und kann weg.

## Scharfschalten

Schrittfolge im README, Abschnitt „Scharfschalten". Kurz: OKX-Schlüsselpaar mit
Handelsrecht erzeugen → als Benutzervariablen setzen → Guthaben prüfen → einen
Vorschlag von Hand scharf ausführen und gegenprüfen → dann erst
`handel_erlaubt: true`.

## Grundlinie nicht vergessen

Aus [[Handelsbots]]: über lange Zeiträume lag jede getestete mechanische
Krypto-Strategie nahe null, leicht darunter — die Gebühren fressen den Vorteil,
kurze Fenster täuschen. Der Scanner rechnet Gebühren/Funding nicht in die
Vorschläge ein; real liegen die Ergebnisse darunter. Die Kleinstbeträge sind
Absicht.
