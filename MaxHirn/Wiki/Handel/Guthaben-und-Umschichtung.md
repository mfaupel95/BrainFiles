---
id: 20261001-guthaben-und-umschichtung
title: 'Handel — Guthaben und Umschichtung'
tags: [handel, boersen, guthaben]
created: 2026-10-01
updated: 2026-10-01
related: ['[[Handel/Boersen-und-Schluessel]]', '[[Handel/Gates-und-Freigabe]]']
summary: 'Wo Kapital liegt, was davon wirklich frei ist, und die drei Gruende, warum ein Posten nicht verkaufbar ist (Ordermin, costmin, gestakte Form).'
---

# Guthaben und Umschichtung

## Die Frage hinter jeder Sperre

Ein Guthaben-Tor liest die **freie** Waehrung, nicht den Kontowert. Beide Boersen
haben am 01.10.2026 gezeigt, wie weit das auseinanderliegt:

| Boerse | Kontowert | wirklich frei | was es bindet |
|---|---|---|---|
| OKX (EEA) | 1.094,77 USD | 30,84 USDC | 215,99 USD isoEq (XPERP-Margin) + ~500 USDC in drei scanner-Positionen mit Stop |
| Kraken | ~570 EUR (+ XXLM/XXBT/XETH ohne Kursaufloesung) | 53,81 EUR + 25,08 USDC | 4 Positionen der kraken-Spur (200 EUR), 1 Margin-Position SUIEUR |

**Merksatz:** `eqUsd` ist keine Verfuegbarkeit. Bei OKX ist das Feld `availBal`
massgeblich; `eq`/`eqUsd` zaehlen Margin und offene Orders mit.

## Drei Gruende, warum ein Posten nicht verkaufbar ist

Alle drei am 01.10.2026 an echten Posten erlebt — der Verkaufsversuch scheitert
sonst mit einer Kraken-Meldung, die wie ein Rechteproblem aussieht:

1. **Unter dem Ordermin.** `PEPEEUR` verlangt 1.500.000 PEPE, im Konto lagen
   409.009,94 (~1,58 EUR). `ONDOEUR` verlangt 15 ONDO, es lagen 10,74331
   (~4,84 EUR). Beide bleiben liegen, bis mehr zusammenkommt — kein Fehler,
   eine Mengenschwelle.
2. **Gestakte Form ohne eigenes Paar.** `ADA.S` ist gestakte Cardano; Kraken
   fuehrt **kein** `ADA.S/EUR` (`AssetPairs` liefert fuer `base=ADA.S` eine leere
   Liste). Der Verkauf muss ueber Unstaking laufen, nicht ueber eine Order.
   Gleiches Muster: `ATOM21.S`, `HYPE.B`, `XPEV.EQ` — der Punkt im Namen ist das
   Kennzeichen.
3. **Gebunden statt frei.** Bei OKX trugen ETH/SOL/BTC ein `availBal` von 7e-9
   (Rundungsrest) — sie stecken in Margin bzw. unter dem Schutz-Stop des scanner.

**Vor jedem Umschichten pruefen:** Paar existiert (`AssetPairs`, `status=online`),
Menge >= `ordermin`, Wert >= `costmin` (0,45 EUR bei Kraken). Ein `validate`-Lauf
kostet nichts und sagt vorher, ob die Boerse die Order annimmt.

## Der Umschichtungslauf vom 01.10.2026

Auftrag Max („umschichten"): acht ungenutzte Kraken-Kleinbestaende in EUR. Fuenf
davon waren verkaufbar:

| Paar | Menge | Erloes (brutto) |
|---|---|---|
| KASEUR | 1.228,38704 | ~47,87 EUR |
| STGEUR | 221,83731 | ~28,95 EUR |
| JTOEUR | 52,68217 | ~25,64 EUR |
| SYNEUR | 159,218683 | ~22,13 EUR |
| DUALEUR | 4.914,7 | ~12,83 EUR |

**ZEUR 53,81 -> 189,42 EUR** (+135,61 netto; die Differenz zu 137,42 brutto ist
die Taker-Gebuehr). Wirkung sofort messbar: `kraken/handeln.py --vorschau` nennt
das Guthaben-Tor nicht mehr — `EUR 189.42/60.00`.

Nicht angefasst: PEPE, ONDO, ADA.S (Gruende 1 und 2 oben).

## Falle im eigenen Aufruf

`markt_verkauf(paar, menge, echt=True)` liefert die Kraken-Antwort — **nicht** das
gewohnte `{result: {txid: [...]}}`-Dict, das `_roh_privat` zurueckgibt. Mein
`r.get('txid')` warf deshalb `'str' object has no attribute 'get'`, **nachdem**
alle fuenf Orders bereits gefuellt waren. Der Fehler sah wie fuenf Fehlschlaege
aus, war aber ein Parser-Fehler im Aufrufer.

**Merksatz:** Nach einem Verkauf nie der Rueckgabe glauben — Kontostand und
`ClosedOrders` sind die Zeugen. Im Zweifel beide vor dem zweiten Versuch lesen,
sonst verkauft man zweimal.