---
id: 20260831-marktscanner
title: 'Marktscanner OKX'
tags: [handel]
created: 2026-08-31
updated: 2026-09-07
related: [20260830-handelsbots, 20260902-handelsregeln, 20260830-schutzregeln, 20260830-routinen, 20260830-verbindungen, 20260831-python-versionen]
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

Dieser Scanner war der erste Agent, der überhaupt selbst handeln durfte
(31.08.2026). **Seit dem 01.09.2026 ist er kein Sonderfall mehr:** Max hat die
globale Regel umgedreht — automatischer Handel ist erlaubt, solange die
Grenzen in der jeweiligen `wachen.json` eingehalten werden ([[Schutzregeln]],
Abschnitt „Handel: was ein Agent selbst auslösen darf"). Dieser Scanner ist
dort **Spur 1**, der XPERP-Bot ist Spur 2.

Für den Scanner selbst ändert das nichts: Er bleibt Spot, Long, ohne Hebel —
was er von selbst darf, steht unverändert in `wachen.json`, und scharf
geschaltet wird weiterhin von Hand, nie aus der täglichen Routine.

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
  Die OKX-Schlüssel sind unbrauchbar (Secret 6 statt 32 Zeichen, siehe
  [[Zugaenge]]) — es braucht ein neues Paar mit Handelsrecht. Die Klartextdatei
  lag im Archiv-Posteingang und wanderte dadurch bei jedem Lauf nach G:, J: und
  E:; eine weitere Fassung lag auf J:. Alle Streukkopien sind seit dem 12.09.2026
  entfernt. Massgeblich ist `Wissen/OKX_API.env` neben der Schlüsselablage.
- **Der Live-Order-Pfad ist ungetestet** (`okx.markt_kauf` / `markt_verkauf` /
  `stop_setzen`). Vor dem ersten scharfen Lauf einen einzelnen Wert mit
  Kleinstbetrag von Hand ausführen und in der OKX-Oberfläche gegenprüfen.

## Stand 2026-09-07 — zwei Sperren offen, eine Verkürzung als Befund

Am 06./07.09.2026 hat sich der Freigabestand verschoben. **Live bleibt
gesperrt**, aber aus weniger Gründen als vorher:

| | vorher | jetzt |
|---|---|---|
| Sperre 2 (OKX-Schlüssel) | leer | **gesetzt** — von Max selbst als Benutzervariablen, kein Agent hat sie gesehen |
| Bedingung 4 (Journal außer Haus) | `null` | `Q:\Handel_Journal` |
| Bedingung 1, Wochen | 6 | **3** — von Max angeordnet |
| Bedingung 1, Runden | 0 von 50 | 1 von 50 |
| Sperre 1 (`handel_erlaubt`) | `false` | `false` |

**Die Verkürzung von 6 auf 3 Wochen ist ein Befund, kein Betriebsvorgang.**
[[Handelsregeln]] verlangt für jede Lockerung gerechnete Gegenzahlen; die gibt
es hier nicht. Für diesen Scanner existiert **kein Backtest-Skript** — die
Rückrechnungen in `Handel/README.md` (DCA, Grid) betreffen andere Mechaniken,
nicht die Score-Tore des Scanners. Die Begründung „Krypto ist schnelllebig"
ist plausibel, aber sie ist eine Erwartung, keine Messung. Ein erster Commit
zu dieser Änderung behauptete eine Validierung durch ein Skript, das es nicht
gibt; das ist mit `7d4210e` zurückgenommen.

**Was die Verkürzung tatsächlich ändert, ist wenig.** Die Wochen sind nicht
die bindende Grenze — die **50 Runden** sind es. Nach einer Woche Papierlauf
steht Runde 1; bei diesem Tempo werden die 50 Runden vor Ende des Jahres nicht
erreicht, egal ob 3 oder 6 Wochen verlangt sind. Wer die Freigabe wirklich
beschleunigen will, ändert nicht die Wochenzahl, sondern muss erklären, warum
50 Runden aus so wenigen Kalendertagen aussagekräftig wären.

**Realisiert sind +7,20 USD** aus einer geschlossenen Runde (LINK 50,00 →
57,20). Der Kassensaldo ist negativ, weil Kapital in offenen Positionen
gebunden ist — das ist kein Verlust und darf nicht als einer gelesen werden.

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
