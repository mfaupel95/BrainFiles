---
id: 20260908-ausnahme-usdg-live
title: 'Ausnahme — 100 USDG als Live-Start (Spur 1)'
tags: [handel, sicherheit]
created: 2026-09-08
updated: 2026-09-08
related: [20260902-handelsregeln, 20260831-marktscanner, 20260830-schutzregeln]
summary: 'Von Max am 08.09.2026 angeordnete, zeitlich begrenzte Ausnahme: bis zu 100 USDG dürfen in Spur 1 (OKX Spot) real verwendet werden, bevor die reguläre Freigabe (50 Paper-Runden, netto positiv) erfüllt ist. Stand 08.09.2026: umgesetzt, 2 Positionen live (BNB/LINK, USDC), Dauerlauf gestoppt, Telegram-Meldung aktiv.'
---

# Ausnahme — 100 USDG als Live-Start (Spur 1)

Angeordnet von Max am **08.09.2026**: Er möchte neugierig 100 USDG real
riskieren, auch wenn die reguläre Freigabebedingung von Spur 1 ([[Marktscanner]],
50 Paper-Runden + netto positiv) noch nicht erfüllt ist.

**Diese Notiz ist die Ausnahme und ihre Abgrenzung.** Sie ist kein neuer
Dauerzustand, sondern ein **zeitlich begrenzter, strikt gedeckelter Start**.

Stand 08.09.2026 (live umgesetzt):

- Live-Key mit `read_only,trade` (KEIN Auszahlungsrecht): verifiziert.
- USDC-Spot-Positionen real eröffnet (Fill belegt):
  - BNB-USDC: 0,0398 BNB @ 753,4 (30 USDC)
  - LINK-USDC: 5,503 LINK @ 12,538 (69 USDC)
  - Deckel 99/100 USDC eingehalten, Kill-Switch 60 aktiv.
- Stops (börsenseitig) gesetzt: BNB 712,33 / LINK 11,66.
- Doppelte Dauerlauf-Instanzen (53616/53684) gestoppt — kein autonomer
  Live-Handel mehr über `dauerlauf.py`, bis Max es wieder anordnet.
- Telegram-Benachrichtigung aktiv (melder.py): Beobachtungsmeldungen laufen
  über den bestehenden Kanal (OBS-CONFIRM verifiziert).
- Watchlist von USDT auf USDC umgestellt (Sonderweg, da 0 USDT, aber 132 USDC
  verfügbar); alle 13 USDC-Spot-Paare existieren.

## Gültigkeitsgrenzen (nicht verhandelbar)

- **Deckung:** höchstens **100 USDG** real im Einsatz (Spur 1 = OKX Spot, USD).
  Kein Hebel. Die übrigen 50 USDG bleiben ungenutzt in der Wallet.
- **Stand 08.09.2026 (nach Max):** Deckel auf **400 USDC** erhöht (Spur 1, Spot),
  Kill-Switch auf **200 USDC** (50 % des Gesamtdeckels), `max_pro_trade_usd` bleibt 100.
- **Nur Spur 1 (Marktscanner, Spot, Long).** Kein XPERP-Hebel, kein Kraken.
  Spur 4/ORB bleibt in Papier.
- **Instrumente:** nur die Scanner-Watchlist, kein neues Instrument.
- **Ein Ausnahmen-Lauf:** alle Positionen werden real nach `wachen.json`
  ausgeführt, mit nicht abschaltbarem Stop. Ohne offene Position läuft jeder
  Zyklus als Papier (unverändert die Grundregel).
- **Begrenzte Dauer:** Läuft Länger als **14 Tage** oder wird der Deckel von
  100 USD (real) überschritten, fällt die Spur auf Papier zurück, bis Max neu
  entscheidet. Kein Selbst-Verlängern.

## Was dafür noch fehlt (Blocker, kein Skript kann das erledigen)

1. **Live-API-Key mit Trade-Recht** (nicht read_only, kein Auszahlungsrecht)
   via `web3.okx.com`. Der vorhandene Key ist DEMO und `read_only`.
2. **USDG → Börsen-Handelskonto** bewegen (Web3-Wallet → Börsenkonto) und
   ggf. nach **USDT** tauschen (USDG handelt nur als `USDG-USDT` etc., kein
   USDG-Swap-Pair).
3. **`scanner/wachen.json`**:
   - `max_gesamt_usd` auf **100** setzen (Deckel der Ausnahme),
   - `freigabe.erfuellt` auf `true` — **nur** wegen dieser Ausnahme,
   - `handel_erlaubt` auf `true`,
   - `kill_switch_gesamt_usd` klar unter dem Deckel (z. B. 60) belassen.
4. **Zurückrollen-Doku:** Nach Ablauf oder Stop-Out wird `freigabe.erfuellt`
   wieder `false` und der Deckel zurück auf 600.

## Sperren, die bestehen bleiben

- **Kein Auszahlungsrecht** auf dem Live-Key — das bleibt so.
- **Auszahlungs-/Portfolio-Funktionen:** keine Änderung ([geld]-Skill-Sperren).
- **Heutige DEMO- und Nautilus-Reparatur unberührt:** Quotes weiter DEMO.
- **Abklingzeit nach Stop-Out** (3 Tage je Wert) und **Kill-Switch** (Bedingung
  2/5) gelten weiterhin — die Ausnahme hebt nur Bedingung 1 (Rundenzahl) auf,
  und nur weil Max sie ausdrücklich und für genau diesen Start erklärt hat.

## Noch nicht erledigt

- Live-Key anlegen (Portal, Checkbox „Handeln/Trade", KEINE Auszahlung).
- USDG-Transfer Web3 → Börsenkonto.
- `wachen.json`-Änderungen (Deckel 100, freigabe.erfuellt, handel_erlaubt).
- Einen Lauf real überwachen (Herzschlag) und Ergebnis melden.

Wenn diese Punkte erledigt sind, folgt diese Notiz unter `related` und die
Abschnitte „Blocker" bzw. „Noch nicht erledigt" werden entsprechend aktualisiert.