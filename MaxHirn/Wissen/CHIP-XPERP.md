---
id: 20260901-chip-xperp
title: 'CHIP XPERP auf OKX'
tags: [handel]
created: 2026-09-01
updated: 2026-09-01
related:
  - id: 20260830-handelsbots
  - id: 20260831-marktscanner
---

# CHIP XPERP auf OKX

Analyse für einen gehebelten Anlauf auf **`CHIP-USD_UM_XPERP-310822`**
(Basiswert CHIP, USD.AI-Protokoll — „yield-bearing synthetic stablecoin backed
by compute". AI-Compute-Narrativ, kleiner Wert). Angefragt am 01.09.2026 mit
großer Erwartung. Der Bot ist [[xperp]] (`../Agenten/Handel/xperp/`), er läuft
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

Die Prüfpflicht aus [[Schutzregeln]] (Spur 2) sagt: nötige > beobachtete
Trefferquote auf der einzig belastbaren Historie → **wahrscheinlich
unprofitabel**. Das ist ein Widerspruch mit Zahlen, kein Veto. Auf ausdrückliche
Anweisung mit Kontrakt, Richtung, Hebel, Einsatz und Stop wird wie angewiesen
ausgeführt — vorbereitet, nicht ausgelöst.

Wenn überhaupt: Hebel ≤ 2×, Einsatz klein (Rahmen 50 USD Margin je Anlauf,
200 USD gesamt — wie [[Marktscanner]]), Stop ≥ 1,5 ATR (≈ 7 %), und eine Woche
Papierlauf zuerst, weil die Strategie auf diesem Kontrakt neu ist.
