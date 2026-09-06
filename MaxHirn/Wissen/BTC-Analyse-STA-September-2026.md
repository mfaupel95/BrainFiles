---
id: 20260905-btc-analyse-sta
title: 'BTC-Analyse STA Solutions — September 2026'
tags: [handel]
created: 2026-09-05
updated: 2026-09-05
related:
  - id: 20260902-analyse-quellen
  - id: 20260902-xrp-analyse-sta
  - id: 20260830-marktlage-august-2026
  - id: 20260831-marktscanner
summary: 'Charttechnik- und Volumen-Analyse zu Bitcoin aus einem YouTube-Beitrag von STA Solutions (05.09.2026): OBV/CVD-Squeeze-Diagnostik, RSI/MACD-Divergenzen, strukturelle Marken, Primärszenario.'
---

# BTC-Analyse STA Solutions — September 2026

Aus einem YouTube-Beitrag von *STA Solutions* (Alexander Schulz), veröffentlicht
**05.09.2026**, 37:39 min, Video-ID `U20JPw8BJ-M`, Titel »Bitcoin: Einstieg
verpasst? HIER kommt die WICHTIGSTE Kauf-Chance!«. Derselbe Kanal wie in
[[Marktlage-August-2026]] und [[XRP-Analyse-STA-September-2026]] — die
**Quellenbewertung in [[Analyse-Quellen]] gilt unverändert** und wird hier
nicht wiederholt. Dies ist die **dritte** ausgewertete Quelle dieses Kanals.

## Kernthese

BTC steht bei ca. **-54 % vom Allzeithoch** (lokales Tief Anfang Juli,
~56–57 Tsd. USD) — historisch **noch nicht so tief korrigiert** wie frühere
Bärenmärkte (2018: -71 %, 2022: -74 %, 2014: -78 %). These: laufender
Bärenmarkt ist flacher/kürzer als die Vorgänger ("Mini-Bärenmarkt").
Kurzfristig (Wochen) hohes Risiko eines Rücksetzers **unter 70 Tsd. USD**,
im Extremfall Richtung 50/40 Tsd. USD — laut Video die eigentliche
Nachkauf-Gelegenheit. Mittel-/langfristig steigt die Wahrscheinlichkeit für
Bodenbildung und Bullenmarkt-Beginn (Wochen-RSI auf 18-Monats-Extrem).

## Methodik: Volumen-Diagnostik (neuer Baustein ggü. den vorigen Videos)

Im Unterschied zu den XRP-/August-Analysen liegt der Schwerpunkt hier auf
**OBV** (On-Balance-Volume) und **CVD** (Cumulative Volume Delta) zur
Unterscheidung von organischer Spot-Nachfrage und synthetischen
Squeeze-Rallyes:

- Kursanstieg **mit** OBV/CVD-Ausschlag → Spot-Nachfrage vorhanden, Trend
  eher tragfähig.
- Kursanstieg **ohne** OBV/CVD-Ausschlag → Rally beruht auf
  Derivate-Squeeze, gilt als fragil. Beispiel aus dem Video: Short-Squeeze
  vom 19.08. (mit OBV-Ausschlag, organische Anschlusskäufe) vs.
  Short-Squeeze vom Donnerstag vor Aufnahme (~77k→83k, ohne Ausschlag,
  Bewegung lief danach zurück).
- Grundmechanik: je schneller/stärker ein Kurs steigt, desto größer der
  latente Gewinnmitnahme-Druck; ein Aufwärtstrend bleibt nur stabil, wenn
  neues Spot-Kaufinteresse diesen Druck laufend absorbiert.

Zusätzlich klassische Indikatoren:

| Indikator | Befund im Video |
|---|---|
| RSI (Wochenchart) | stark überkauft, höchster Stand seit Mai 2025 → erhöhte Korrekturwahrscheinlichkeit |
| MACD (Tageschart) | beginnende **bärische Divergenz** (höheres Kurshoch, fallendes MACD) |
| MACD (Wochenchart, zurückliegend) | **bullische Divergenz** (tieferes Kurstief, höheres MACD-Tief) als Bodenbildungssignal gewertet |
| Strukturelle Hochs/Tiefs | frühere lokale Extrempunkte (~70k, ~48k) als Reaktions-/Entscheidungszonen für Marktteilnehmer |
| Elliott-Wellen | Primärszenario: laufende Aufwärtsbewegung = Welle 2 einer übergeordneten Abwärtsstruktur, solange keine höheren Hochs entstehen; Bestätigung braucht 5-teilige Aufwärtsstruktur |

## Preismarken (aus dem Video, nicht gegengeprüft)

| Marke | Bedeutung |
|---|---|
| ~74.000 USD | genannte Unterstützungs-/Reaktionszone |
| ~70.000 USD | strukturelles Hoch/Referenzmarke; Unterschreiten würde Bodenbildungsbereich re-aktivieren |
| 90.000–100.000 USD | nächste Hürde im bullischen Primärszenario |
| 50.000 (ggf. 40.000er) USD | bärisches Alternativszenario bei Fortsetzung des Bärenmarkts |

## Kritische Einordnung

Wie in [[Analyse-Quellen]] festgehalten, ohne Wiederholung im Detail:

- **Kein hartes Invalidierungskriterium** für die Gesamtthese; "Bärenmarkt
  flacher/kürzer" ist mit fast jedem Verlauf vereinbar.
- OBV/CVD-Argumentation ist in sich stimmig und nachvollziehbar begründet
  (Marktpsychologie-Erklärung ausführlicher als in den Vorvideos), bleibt
  aber nachträglich interpretierbar — keine festen Schwellenwerte genannt.
- Geschäftsmodell unverändert (Aboverkauf, Kraken- und Ledger-Affiliate-Links
  im Video).
- Ankündigung einer Rabattaktion für kostenpflichtige Aktienanalysen im
  Video — kommerzieller Kontext bei der Veröffentlichung mitzudenken.

**Einstufung wie gehabt:** brauchbar als Hypothesen- und Marken-Lieferant,
unbrauchbar als alleinige Handlungsgrundlage.

## Bezug zum eigenen System

`BTC-USDT` steht als **erster Eintrag** ohnehin in der Watchlist des
[[Marktscanner]]s (`Agenten/Handel/scanner/wachen.json`) und wird bereits
täglich mechanisch bewertet — keine Aufnahme nötig. Ein aktueller
Score/Chance-Risiko-Stand wurde für diese Notiz **nicht** abgefragt (kein
Scan-Lauf ausgelöst); bei Bedarf liefert `scanner/scan.py` den aktuellen
Stand.

Die im Video verwendete OBV/CVD-Logik ist **nicht** Teil von
`xperp/indikatoren.py` oder `scanner/bewertung.py` (dort: SuperTrend, EMA,
nachgebaute Saisonalität, siehe [[Saisonalitaet-Signal]]). Eine Übernahme
wäre ein eigener Entwicklungsschritt, keine automatische Ableitung aus
diesem Video — hier nur als möglicher Ansatzpunkt vermerkt, nicht umgesetzt.

Verwandt: [[Analyse-Quellen]], [[XRP-Analyse-STA-September-2026]], [[Marktlage-August-2026]], [[Marktscanner]], [[Saisonalitaet-Signal]]
