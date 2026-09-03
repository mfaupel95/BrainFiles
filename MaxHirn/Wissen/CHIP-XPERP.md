---
id: 20260901-chip-xperp
title: 'CHIP XPERP auf OKX'
tags: [handel]
created: 2026-09-01
updated: 2026-09-03
related: [20260830-handelsbots, 20260831-marktscanner, 20260902-handelsregeln]
summary: 'Analyse fuer einen gehebelten Anlauf auf CHIP: das 14-Tage-Fenster taeuscht, die reale 133-Tage-Historie ist negativ, alle drei Tore zu.'
---

# CHIP XPERP auf OKX

Analyse für einen gehebelten Anlauf auf **`CHIP-USD_UM_XPERP-310822`**
(Basiswert CHIP, USD.AI-Protokoll — „yield-bearing synthetic stablecoin backed
by compute". AI-Compute-Narrativ, kleiner Wert). Angefragt am 01.09.2026 mit
großer Erwartung. Der Bot ist [[XPERP-Handel|xperp]] (`../Agenten/Handel/xperp/`), er läuft
für CHIP ohne Änderung: `bot.py lage --wert CHIP`.

**Stand:** 2026-09-01. Kurs 0.0435.

## Der Befund in einem Satz

Der XPERP ist erst **14 Tage alt**, und genau dieses kurze Fenster täuscht —
in die gute Richtung. Auf der **realen 133-Tage-Historie** (`CHIP-USDT-SWAP`,
seit dem Listing 21.04.2026) ist der mechanische Trend-Anlauf **negativ**.

## Zwei Fenster, zwei Bilder

| Kennzahl | XPERP, 14 Tage | SWAP, 133 Tage |
|---|---|---|
| Trefferquote (Stop 1,5 ATR / Ziel 3 ATR) | **67 %** | **28 %** long, 28 % short |
| nötige Trefferquote | 34 % | 34 % |
| → Abstand zur Nulllinie | +33 pp | **−6 pp** |
| Hebel-Deckel long (größter 7-Tage-Rücklauf) | 4,8× | **2,2×** (30 Tage: 1,6×) |
| Hebel-Deckel short | 1,6× | **1,0×** — Bounces zu heftig |
| Vola p.a. | ~110 % | **160 %** |
| ATR(14) je 4h-Kerze | 4,6 % | 4,4 % Median |

Das ist die Falle aus [[Handelsbots]] wörtlich: „Dieselbe Rechnung ergab über
30 Tage +0,63 $ statt −0,22 $ über 12 Monate — weil BTC im Fenster 28,5 %
stieg." Bei CHIP ist der XPERP im ganzen bisherigen Leben nur gestiegen
(SuperTrend seit Listing auf AUF), weil er auf einem lokalen Tief startete.

## Kursverlauf, den das kurze Fenster verdeckt

- Allzeithoch 0,113 (Mai 2026) → jetzt 0,0435 = **−61 %**
- Seit SWAP-Listing (0,0577): −25 %
- Größter Drawdown Peak-to-Trough: **81 %**
- Tief 0,0217 (Aug 2026) → jetzt = +100 %. Der aktuelle „Trend" ist die
  Gegenbewegung aus diesem Tief.

## Die drei Tore des Bots — alle zu

| Tor | Standard | CHIP |
|---|---|---|
| Historie ≥ 21 Tage | 21 | **14** |
| Umsatz 24h ≥ 3 Mio USD | 3 Mio | **0,7 Mio** (XPERP) — dünn, Slippage |
| Hebel-Deckel ≥ 5× | 5 | **2,2×** long / 1,0× short (reale Historie) |

## Funding

+0,0008 %/8h im Schnitt der letzten 100 Perioden ≈ **+0,9 %/Jahr**, Long zahlt.
Vernachlässigbar, kein Argument in keine Richtung.

## Nachrechnen

```powershell
cd Agenten\Handel\xperp
..\scanner\.venv\Scripts\python.exe bot.py lage  --wert CHIP
..\scanner\.venv\Scripts\python.exe bot.py trend --wert CHIP   # Prüfpflicht-Tabelle
```

Die 133-Tage-Zahlen stammen aus `CHIP-USDT-SWAP` (nicht dem XPERP), der XPERP
selbst hat dafür zu wenig Kerzen (87 Stück à 4h). Seit dem 01.09.2026 macht das
der **`--historie`-Schalter** in `bot.py` selbst:

```powershell
cd Agenten\Handel\xperp
..\scanner\.venv\Scripts\python.exe bot.py trend --wert CHIP --historie auto
..\scanner\.venv\Scripts\python.exe historie.py CHIP        # Vergleich jung <-> tief
```

`--historie auto` zieht den `<Basis>-USDT-SWAP` und rechnet Hebel-Deckel und
Trefferquote darauf; das Signal bleibt am XPERP. Mit dem Schalter senkt der Bot
den Hebel selbständig auf **2,2×** und meldet bei Zahl 4 der Prüfpflicht
„trägt NICHT" (27,7 % gegen 33,7 %, 693 ausgelaufene Anläufe über 133 Tage).
Neues Modul `historie.py`, dazu ein eigener Vergleichsaufruf.

## Bewertung

Die Prüfpflicht aus [[Handelsregeln]] (Spur 2) sagt: nötige > beobachtete
Trefferquote auf der einzig belastbaren Historie → **wahrscheinlich
unprofitabel**. Das ist ein Widerspruch mit Zahlen, kein Veto. Auf ausdrückliche
Anweisung mit Kontrakt, Richtung, Hebel, Einsatz und Stop wird wie angewiesen
ausgeführt — vorbereitet, nicht ausgelöst.

Wenn überhaupt: Hebel ≤ 2×, Einsatz klein (Rahmen 50 USD Margin je Anlauf,
200 USD gesamt — wie [[Marktscanner]]), Stop ≥ 1,5 ATR (≈ 7 %), und eine Woche
Papierlauf zuerst, weil die Strategie auf diesem Kontrakt neu ist.

## Bestätigt von Max am 01.09.2026 — zwei Anläufe

Widerspruch (oben) ist einmal gesagt, Max hat beide bestätigt. Ausgeführt wird
wie angewiesen, vorbereitet, nicht ausgelöst. Die Tick-Preise stehen bewusst
**nicht** hier — sie sind beim nächsten Blick veraltet; der Aufruf erzeugt sie
neu (Stop und Ziel fallen aus `stop_atr_faktor`/`ziel_atr_faktor` in
`wachen.json`).

**Kontrakt gewechselt:** Max will die Orders auf **`CHIP-USDT-SWAP`**, nicht den
XPERP. Der SWAP ist der normale Perpetual — **~24 Mio USD Umsatz/Tag** gegen
~1 Mio beim XPERP, 134 Tage Historie, gleiche 20× / ctVal 100. Der Wechsel
öffnet zwei der drei Tore (Umsatz, Historie); das Kernurteil bleibt, weil
Hebel-Deckel 2,2× und Trefferquote 28 % schon immer aus dem SWAP kamen.

`okxf.py` kennt seit dem 01.09.2026 auch SWAP-Kontrakte: `instrument()` nimmt
einen vollen `…-SWAP`-instId direkt, `tickers("SWAP")` holt die passenden
Umsätze. `--historie auto` auf einem SWAP-instId zieht dessen eigene tiefe
Reihe (`kerzen_lang`, ~200 Tage) statt der 300 Signal-Kerzen.

| | Nr. 1 — Trend-Long | Nr. 3 — Grid-Long |
|---|---|---|
| Aufruf | `bot.py trend --wert CHIP-USDT-SWAP --historie auto --hebel 2` | `bot.py grid --wert CHIP-USDT-SWAP --historie auto --hebel 3 --einsatz 80` |
| Richtung | Long | Long, 6 Stufen |
| Hebel | 2× (unter Deckel 2,2×) | 3× — **über** Deckel 2,2×, Prüfpflicht sagt `ZU HOCH` |
| Einsatz | ~47 USD Margin (Rahmen 50) | ~76 USD Gesamtmargin (Rahmen 80) |
| Stop | 1,5 ATR ≈ −7,7 % | gemeinsamer Rasterboden, ~−32 % |
| Verlust wenn Stop/Boden | ~7 USD | ~37 USD (Kill-Switch 40) |
| Prüfpflicht Zahl 4 | 28,3 % gegen 33,9 % → trägt nicht | 90,8 % gegen 82,3 % → trägt |
| Funding 48 h | +0,06 % auf die Margin (Long zahlt) | +0,09 % auf die Margin |

**Auslösen:** `OKX_API_KEY/SECRET/PASSPHRASE` sind gesetzt
(`okxf.schluessel_vorhanden()` → True). Der Bot druckt trotzdem nur die
`okxf.hebel_setzen(...)` / `okxf.order_limit(...)`-Aufrufe. Absenden tut Max —
einzeilig aus PowerShell (`& ..\scanner\.venv\Scripts\python.exe -c "..."`), nie
die Claude-Sitzung ([[Handelsregeln]]). Preise vorher mit einem frischen
`bot.py`-Lauf erneuern, sie driften.
