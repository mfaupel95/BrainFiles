---
id: 20261021-kelly-positionsgroesse
title: "Kelly-Kriterium: Positionsgröße aus gemessenem Vorteil (drei Papers, Vergleich mit Handelsregeln)"
tags: [handel, positionsgroesse, risiko, papers]
created: 2026-10-21
updated: 2026-10-21
related: [20260902-handelsregeln, 20260917-awesome-systematic-trading]
summary: "Kelly-Formel f* = p − q/b, Bruchteil-Kelly und Mehrfach-/Korrelationsfälle aus drei Papers; Vergleich mit Einsatzregeln, Drawdown-Ratsche und gemessenen Spuren. Ergebnis: Kelly nur als Diagnose mit Obergrenze, keine Größenerhöhung. Die Scanner-Stichprobe vom 29.09.2026 ist durch die Preisfix-Korrektur vom 02.10.2026 ungültig; die Diagnose rechnet nur gültige Runden."
---

# Kelly-Kriterium: Positionsgröße aus gemessenem Vorteil

Quellen (alle in `Wiki/Handel/`):

- **Dang & Woods**, „The Kelly Criterion in the Modern Day", April 2026 (`Dang_Woods.pdf`): Überblick, Herleitung, Bruchteil-Kelly nach Thorp, Mehrfach- und Korrelationsfälle, Anwendung Wetten und Aktien.
- **Markopoulos**, „Kelly Criterion Theory" (`Kelly Criterion Theory.pdf`): kurze Herleitung über den erwarteten Logarithmus des Vermögens, mit Rekursion über n Runden.
- **CryptoPredictions** (Bachelorarbeit Sharif, 2023, `CryptoPredictions.pdf`): Vergleich von acht Prognosemodellen auf Stundenkerzen. Das Toolkit selbst steht schon in `Wiki/Handel/CryptoPredictions_Wissen.md`.

## Die Formel

Mit `p` = Trefferquote, `q` = 1 − p und `b` = Gewinn je Einheit Verlust (Ziel/Stop in R):

- **Kelly-Anteil:** `f* = p − q/b = (b·p − q)/b`. Beispiel Münzwurf 60/40 bei b = 1: f* = 0,2, also 20 % des Kapitals.
- **Markopoulos in gleicher Form:** `f* = ((b+1)·p − 1)/b`. Die Umformung ist identisch.
- **Bruchteil-Kelly:** `f = c·f*` mit `0 < c < 1`. Thorp (zitiert bei Dang & Woods) zeigt: Bei `c > 1` (Überwetten) sinkt der Erwartungswert des Logarithmus, die Varianz steigt. Halb-Kelly ist ein üblicher Kompromiss.
- **Mehrere Wetten:** Unabhängige Wetten werden einzeln mit Kelly gerechnet. Korrelierte Wetten (Dang & Woods, Abschnitt 5.2) brauchen eine gemeinsame Verteilung, und das Ergebnis ist meist eine kleinere Quote.
- **Warnungen aus den Papers:** Kelly ist „garbage in, garbage out" (Rotando/Thorp, Abschnitt 5.3). Schon kleine Fehler in `p` oder `b` verändern `f*` stark. Samuelson-Kritik: Nutzenfunktionen anderer Art führen unter Kelly zu Verlust (Dang & Woods, Schluss).
- **Aktien-Form:** `f* = (μ − r)/σ²` (Dang & Woods, Abschnitt 5.3). Auch hier gilt die Schätzfehler-Warnung.

## Was die Papers nicht liefern

- Keine Kosten, keine Gebühren, kein Slippage. Die Formel rechnet mit Idealpreisen.
- Keine Stichprobengröße. Die Formel sagt nicht, wie sicher `p` gemessen ist.
- Die Dang-&-Woods-Beispiele (Wetten 60 %, Thorp Sportwetten 1994) sind Einzelfälle mit sehr vielen Runden.

## Die CryptoPredictions-Befunde

- Acht Modelle (Random Forest, LSTM, GRU, Orbit, ARIMA, SARIMAX, Prophet, XGBoost), Stundenkerzen Nov 2022 bis Feb 2023. Testfenster nur gut sechs Wochen.
- **Trefferquote 54–72 % ist für Richtungsprognosen nahe Münzwurf.** Die Autoren nennen 0,55 für die meisten Modelle.
- **Accuracy allein täuscht:** SARIMAX hat eine der höchsten Trefferquoten (0,70), aber MAPE 5,48 % und MASE 24,6. Prophet hat die besten Fehlermaße (MAPE 0,40 %, MASE 1,7), Accuracy 0,71.
- **Brauchbarer Maßstab: MASE gegen den Naivprognose-Wert.** MASE < 1 heißt, das Modell schlägt „morgen = heute". Der Vergleich mit dem Naivwert ist fair, weil er Skalen und Richtung gleich behandelt.
- Keine Handelssimulation. Die Arbeit prüft nicht, ob die Prognose nach Kosten Geld bringt.

## Vergleich mit unserem System

| Thema | Papers | Unser System (Stand Handelsregeln) | Bewertung |
|---|---|---|---|
| Einsatz pro Position | Kelly-Anteil aus `p`, `b` | Fester Risikobetrag je Position, Pflicht-Stop, Hebel-Deckel `hebel_deckel` (Handelsregeln) | Kelly ist nicht Grundlage. Unser System setzt bewusst fest, weil `p` nicht sicher gemessen ist. |
| Obergrenze | Bruchteil-Kelly, `c` ≤ 0,5 | Drawdown-Ratsche: bei −15 % halbiert sich jede weitere Größe; Kill-Switch | Ratsche wirkt wie eine grobe Bruchteil-Logik nach Verlust. Kelly gibt keine Begründung für einen festen Schwellenwert. |
| Korrelation | Mehrfach-Kelly senkt die Quote | Mehrere Positionen gleichzeitig, z. B. 4 je Arm (Stand 21.09.2026), oft korrelierter Krypto-Beta | Eine Kelly-Rechnung je Position würde zu hoch sein. Eine Gesamtquote wäre nötig. |
| Schätzfehler | Warnung „garbage in" | Wochen-Soll-Ist mit gleitendem 30-Runden-Erwartungswert (Bedingung 5) | Gleiche Sorge, anderes Werkzeug. Der Erwartungswert ist Schutz gegen zu frühes Hochsetzen. |
| Prognosegüte | MASE gegen Naiv, Accuracy allein täuscht | Break-even-Trefferquote je Spur (Handelsregeln, Zeilen 717–720) | Unser Maß ist näher an Ökonomie. MASE wäre ein Vorfilter für Prognose-Modelle. |
| Kosten | fehlen in beiden Papers | Gebühren, Funding, Slippage sind Pflicht-Pflichtzahlen | Kein Paper bietet das. Unser System ist hier voraus. |

## Gemessene Spuren gegen Kelly

**Korrektur 21.10.2026:** Die Scanner-Zeile unten stammt aus 125 Runden vor dem Preisfix vom 02.10.2026 22:23 UTC. Damals war der Einstieg der Vortagesberichtspreis, und `strategie_kennzahlen.py` schließt diese Runden seither aus (165 Stück). Nach dem Fix bleiben für den Scanner nur 5 gültige Runden. Die Zeile ist deshalb nicht belastbar und wird als Kandidat gestrichen. Die anderen Zeilen sind ebenfalls nur Momentaufnahmen.

Zwei Stichproben, nicht vermischen. Die Trefferquote `p` und die Gewinn-Verlust-Quote `b` kommen aus dem Formelblatt `Wiki/Handel/Strategie-Kennzahlen.md` (Stand 29.09.2026, Runden aus `auswertung_alle.runden_fuer()`). Dort ist `b` nicht direkt gemessen, sondern aus dem Profit-Faktor PF abgeleitet: `b = PF · q / p`. Das ist eine Näherung. Kelly-Anteil `f*` = `p − q/b`. Konfidenzgrenze nach Wald (95 %) auf `p`, unten die Kelly-Quote an dieser Grenze.

| Spur | p | n echte Runden | b (aus PF) | Break-even (1/(1+b)) | f* voll | f* halb | f* an der Grenze von `p` |
|---|---|---|---|---|---|---|---|
| scanner | 84,8 % | 125 | 3,16 | 24 % | 0,800 | 0,400 | 0,717 |
| xperp | 45,8 % | 24 | 3,56 | 22 % | 0,306 | 0,153 | 0,051 |
| orbk | 60,0 % | 15 | 1,49 | 40 % | 0,332 | 0,166 | −0,082 |
| moondev_topmovers | 65,0 % | 20 | 1,28 | 44 % | 0,376 | 0,188 | 0,003 |

Zum Vergleich der ältere Stand aus `Handelsregeln.md` (Zeilen 717–720 und 647–650, andere Stichprobe und anderer Zeitpunkt): scanner 64 % bei n = 14, xperp/swap 55 % bei n = 20, spiegel 39 % bei n = 107. Dort war nur spiegel mit genug Runden belastbar, und auch dort liegt `f*` an der Grenze bei rund 0,5 %.

**Befund:**

- **Scanner:** Die frühere Zahl (84,8 % in 125 Runden, Kelly halb 40 %) ist nach der Korrektur oben nicht mehr gültig. Der aktuelle Scanner hat 5 gültige Runden und ist damit nicht messbar.
- **xperp:** An der Grenze knapp positiv (0,05), mit 24 Runden. Zu wenig für eine Größenregel.
- **orbk, moondev_topmovers:** An der Grenze null oder darunter. Keine Basis für eine Größenänderung.

Heißt: Heute trägt keine Spur einen Kelly-Einsatz. Die Entscheidung bleibt bei der Ratsche und dem festen Risiko.

## Einbindung ins System

**Jetzt eingebunden (Wissen):**

- Diese Notiz, mit Verweis auf die Herkunft der drei Papers.
- Eintrag in `Wissen/INDEX.md`.

**Umgesetzt 21.10.2026:** Die Kelly-Diagnose läuft als reine Anzeige in der Wochen-Routine (`Agenten/Routinen/handel-wachen.ps1` ruft `Handel/strategie_kennzahlen.py --kelly` und schreibt ins Log). Sie ändert keinen Einsatz und keine Freigabe.

**Weiter offen (braucht Entscheidung von Max, weil es Live-Handel betrifft):**

1. **Kelly-Diagnose als reine Anzeige in der Wochen-Soll-Ist-Routine (Bedingung 5).** (umgesetzt, siehe oben.) Pro Spur: gleitendes `p` und `b`, Konfidenzgrenze, Kelly-Anteil am unteren Rand. Keine Wirkung auf Einsatz, nur Befund. Das würde zeigen, wann eine Größenregel überhaupt sinnvoll wäre.
2. **Keine Kelly-basierte Erhöhung des Einsatzes.** Eine Größenänderung braucht mindestens zwei getrennte Zeitfenster, in denen die Grenze von `p` über dem Break-even liegt, und einen Out-of-Sample-Lauf. Bis dahin bleiben Ratsche und Hebel-Deckel die einzigen Größenregeln.
3. **MASE gegen Naivprognose als Vorfilter** für Prognosemodelle, falls wieder Prognosen in eine Spur fließen sollen. Schon in `CryptoPredictions_Wissen.md` vermerkt. Keine Code-Änderung nötig.

## Grenzen

- Kelly setzt unabhängige Wiederholungen mit bekannter Auszahlung voraus. Stops und Ziele sind diskret, und Liquidation ist ein dritter Ausgang. Das Modell passt nur grob.
- Die Trefferquoten stammen aus Papierläufen und Live-Läufen mit unterschiedlichen Spurdefinitionen. Sie sind nicht direkt vergleichbar.
- Keine Aussage zur Profitabilität einzelner Spuren. Die Notiz vergleicht nur Größenregeln.
