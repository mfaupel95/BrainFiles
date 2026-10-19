---
id: 20260919-moon-dev-code-studien
title: 'Moon-Dev-Code: die drei Strategie-PDFs'
tags: [handel]
created: 2026-09-19
updated: 2026-09-19
related: [20260916-moon-dev-agenten, 20260921-prognose-backtest]
summary: 'Gelesene Zusammenfassung der drei Paper in Werkstatt/Moon-Dev-Code/strategy_pdfs/ (Psychologie, Deep RL, EMH-Survey); kein Code oder Parameter übernommen.'
---

# Moon-Dev-Code: die drei Strategie-PDFs (gelesen 19.09.2026)

Stand 19.09.2026. `Werkstatt/Moon-Dev-Code/strategy_pdfs/` haelt drei
wissenschaftliche Paper. Diese Notiz fasst den Inhalt zusammen und zieht die
Verbindung zum eigenen Handelsbetrieb. Die Volltexte liegen als
`*.txt`-Extrakte neben den PDFs (pdftotext -layout). Alle drei sind
oeffentliche Open-Access-Artikel (CC BY-NC 4.0 bzw. MDPI).

## 1. Psychologie des Krypto-Handels (Delfabbro, King, Williams 2021)

`Journal of Behavioral Addictions 10 (2021) 201-207`, DOI
`10.1556/2006.2021.00037`. Open Access (CC BY-NC 4.0).

**Kernaussage:** Krypto-Handel traegt strukturell Suchtrisiken wie
Gluecksspiel + Social Media. Vier spezifische Risikofaktoren:

1. **Illusion der Kontrolle** - Ueberschaetzung von Wissen/Kompetenz. Bei
   steigendem BTC sind fast alle Entscheidungen positiv verstaerkt, Trader
   folgern faelschlich Kausalitaet (hindsight bias, hot-hand fallacy).
2. **Soziales Lernen/Verstaerkung** - Influencer, Pump-Signale, mutual
   social reinforcement; Bots verstaerken Botschaften.
3. **Beschaeftigung (Preoccupation)** - 24/7-Verfuegbarkeit, staendiges
   Checken stoert Schlaf und Alltag.
4. **FOMO und antizipiertes Bedauern** - Kauf auf kurzfristigen Spitzen,
   Halten trotz Verlust aus Angst zu verkaufen; Bedauern bei "commission"
   (verkauft, dann gestiegen) wie "omission" (nicht gekauft, dann gestiegen).

**Strukturelle Besonderheiten von Krypto** (aus dem Paper): 24/7-Handel,
fehlende fundamentale Bewertbarkeit (keine Dividenden/Bilanz), extreme
Volatilitaet (100%+ in Stunden, bis 40% Korrekturen im Bullenmarkt), Scam- und
Pump-Risiko, und - wichtig fuer das Portfoliodesign - **Altcoins bewegen sich
wie Derivate von BTC** (stark mit BTC korreliert, oft mit groesserer Amplitude;
eigene Absicherung zwischen Altcoins kaum moeglich).

**Schutzfaktoren (aus dem Paper):** Budget einhalten, Verluste nicht jagen
(Verluste sind steuerlich nutzbar), **Satisficing statt Optimieren** (nicht
exakt am Tief kaufen / Hoch verkaufen wollen), Profit rechtzeitig nehmen,
Liquiditaet halten (USD-Stablecoins), mehrere serioese Informationsquellen
statt Eilmeldungen, BTC-Dominanz als Korrektur-Vorbote im Blick behalten.

**Bezug zum eigenen Betrieb:** Die vier Risikofaktoren sind genau die
Versuchungen, die [[Handelsregeln]] und die Spuren-Architektur bauen bewusst
weg:

- Regelwerk + Stops ersetzen die Illusion der Kontrolle: eine Spur darf
  Entscheidungen nicht aus "Gefuehl" fallen lassen, sondern nur aus
  deterministischen Signalen.
- Ratschen/Stops (siehe [[RATSCHEN VEREINHEITLICHT]] in Hermes-Memory bzw.
  `pruefe_ratschen.py`) sind die Maschine gegen FOMO und antizipiertes
  Bedauern: kein manuelles Halten, kein Nachkaufen auf Spitzen.
- Die Beobachtung "Altcoins = BTC-Derivate" bestaetigt die Marktbreite-
  Filter (z.B. `moondev_marktlage` mit "BTC +2% UND Breite >= 60%"): ohne
  BTC-Trend laufen Altcoin-Signale ins Leere.
- Paper-Ergebnis "Korrektur haeufig nach niedriger BTC-Dominanz" ist ein
  Lesetipp fuer den [[Marktbriefing]]-Kontext - nicht als Spur umgesetzt.

## 2. Deep Reinforcement Learning fuer Krypto-Handelspunkte (2020)

`Applied Sciences 10(4):1506` (MDPI), DOI `10.3390/app10041506`.

**Kernaussage:** Ein DRL-Agent (TensorFlow/Keras) lernt Handelspunkte fuer
BTC, LTC, ETH aus stundlichen OHLC-Daten (Zeitreihen-Input) mit drei
Aktionen (kaufen/halten/verkaufen), Reward = Preisdifferenz
Kauf-Verkauf. Vergleich gegen Double-Cross (SMA-Kreuz), Swing- und
Scalping-Strategie.

**Ergebnisse (im Testzeitraum, je ~1 Monat):**

| Instrument | DRL-Rendite | Vergleich |
|---|---|---|
| BTC | +114,4 % | Double Cross +2,4 % |
| LTC | +74,6 % | Scalping +23,7 % |
| ETH | +41,4 % | Double Cross -2,9 %, Scalping -2,4 % |

**Einordnung (kritisch):** Das sind **Backtest-/In-Sample-Ergebnisse eines
Monats** ohne nachgewiesene Out-of-Sample-Performance, ohne Kostenmodell fuer
das hohe Handelsvolumen (642 Aktionen in einem Monat bei LTC!) und ohne
Slippage. Die Zahl der Aktionen zeigt: der Agent tradet extrem aktiv, echte
Kosten wuerden die Rendite deutlich schrumpfen. Fuer den eigenen Betrieb ist
das Paper kein direktes Rezept, sondern ein Beleg, dass **rein preisbasierte
Muster (zeitliche Abhaengigkeit) existieren** - konsistent mit dem
Ineffizienz-Befund aus Paper 3.

**Bezug zum eigenen Betrieb:** Kein Import von Code oder Parametern. Die
eigenen Spuren entscheiden deterministisch und mit explizitem Kostenmodell
(gebuehr_taker je wachen.json), waehrend dieses Paper die Kosten gar nicht
modelliert - das ist der Unterschied zwischen "Papier-Rendite" und
"echtem Buch".

## 3. Effizienz und profitable Handelsmoeglichkeiten in Krypto-Maerkten (2019)

`Journal of Risk and Financial Management 12(2):67` (MDPI), DOI
`10.3390/jrfm12020067`. Systematischer Survey ueber 38 EMH-Studien.

**Kernaussage:** Die ueberwiegende Mehrheit der akademischen Studien findet
**Ineffizienz im Krypto-Markt (schwache Form)**: vergangene Preise tragen
Information fuer zukuenftige Returns (Long Memory, Hurst-Exponent > 0,5,
DFA). D.h. technische Muster sind statistisch nachweisbar vorhanden.

**Wichtige Nuance:** Die Ineffizienz **verblaesst mit zunehmender Reife des
Marktes** - je etablierter ein Coin (v.a. BTC), desto naeher am
Random-Walk. Spaetere Studien (Hattori/Ishida 2019, Ji et al. 2018) finden
teilweise Effizienz; das Gesamtbild ist "Adaptive Markets": Ineffizienz
existiert, wandert aber.

**Methodik-Hinweis:** Die Studien nutzen Hurst-Exponent, R/S-Analyse,
Varianz-Ratio-Tests, MF-DFA, GARCH-Familie - alles Langzeit-Gedaecchtnis-
Tests auf taeglichen Daten, **nicht** kurzfristige Signal-Systeme.

**Bezug zum eigenen Betrieb:** Das Paper untermauert den Ansatz der
Signal-Spuren (dass technische Muster ueberhaupt existieren) und
widerspricht der Annahme "Muster sind laengst weg". Aber: Die Ineffizienz
ist auf Tagesdaten gemessen; die eigenen Spuren handeln auf 4H/30M/5M
(Mosaic) oder auf 1H-Kerzen. Ob das Gedaecchtnis auf Intraday-Zeitskalen
ebenso besteht, beantwortet das Paper nicht - das pruefen die
Backtests der eigenen Spuren (z.B. GITTER-Walk-Forward).

## Fazit fuer den Betrieb

1. **Kein Code und keine Parameter aus den drei PDFs uebernehmen** -
   sie sind Studienmaterial, keine Strategie.
2. Bestaetigt: deterministische Regeln + Stops + Kostenmodell sind der
   richtige Weg; die psychologischen Risiken (FOMO, Kontroll-Illusion)
   werden von der Architektur abgefangen, nicht vom Menschen.
3. Der Langzeit-Gedaecchtnis-Befund ist ein Grund, die Intraday-Spuren
   weiter zu beobachten - aber nur mit eigenem Backtest und
   Walk-Forward-Nachweis (Muster im eigenen Datenfenster pruefen, nicht aus
   dem Survey ableiten).

Verwandt: [[Moon-Dev-Agenten]], [[Handelsregeln]], [[Marktbriefing]],
[[Marktlage-September-2026]].