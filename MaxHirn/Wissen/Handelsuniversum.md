---
id: 20261021-handelsuniversum
title: 'Handelsuniversum'
tags: [handel, sicherheit, regeln]
created: 2026-10-21
updated: 2026-10-21
related: [20260902-handelsregeln, 20260830-schutzregeln, 20261021-quant-konzepte, 20261021-signature-plot]
summary: 'Welche Instrumente eine Handelsspur überhaupt anfassen darf, wo diese Liste steht, und wie Backtest und Betrieb auf derselben Liste bleiben.'
---

# Handelsuniversum

Das **Handelsuniversum** ist die Menge der Instrumente, die eine Spur handeln
oder rechnen darf. Es ist eine eigene Grenze, getrennt von Einsatz, Hebel und
Stop ([[Handelsregeln]]). Diese Notiz ist für den Agenten gedacht, der neu
einsteigt: Sie sagt, wo die Liste steht und welche Regeln für sie gelten.

**Warum:** Ein Backtest auf einem anderen Universum als dem Betrieb misst etwas
anderes. Am 07.10.2026 zählte die Signalwelle des Marktscanners im Live-Lauf nur
37 Instrumente in 111 Transaktionen, der Ruecklauf rechnete aber auf einem
Universum von 300. Die Zahl im Backtest galt deshalb nicht für den Betrieb (T-144,
erledigt mit dem Vermerk „Universum gezählt“). Wer das Universum nicht in jeder
Aussage nennt, verkauft eine Zahl für einen Zeitraum, den niemand gelebt hat.

## Die Regeln

1. **Eine Quelle je Spur.** Das Universum steht in der Konfigurationsdatei der
   Spur, nicht im Gedächtnis einer Sitzung und nicht in einem Skript-Literal.
   Ein Agent ergänzt keine Instrumente „mal eben“ für einen Test.
2. **Jede Aussage nennt Größe, Quelle und Zeitraum.** Bei jedem Backtest,
   jeder Rangliste und jeder Auswertung steht dabei, wie viele Instrumente
   gerechnet wurden, woher die Liste kommt und über welche Zeit. Fehlt das, ist
   die Aussage kein Befund.
3. **Backtest und Betrieb sind dasselbe Universum.** Weicht es ab, ist die
   Abweichung selbst der Befund und wird dazugeschrieben.
4. **Änderung ist Stufe 1.** Ein Universum wird wie eine `wachen.json` geändert:
   `.bak` vorher, eigener Commit, Begründung in der Commit-Nachricht, nie mit
   anderer Arbeit gebündelt ([[Schutzregeln]], Stufe 1).
5. **Nachweis vor Aufnahme.** Ein Instrument kommt nur dazu, wenn Historie für
   den Backtest vorliegt und die Liquidität in der Begründung steht. Beispiel aus
   `xperp/wachen.json`: XAU mit 10,7 Mio. Volumen als liquidester Rohstoff.
6. **Mehrere Familien brauchen eigene Tore.** Wo ein Venue Krypto, Aktien und
   Rohstoffe unter demselben Schlüssel führt, bekommt jede Familie eigene
   Grenzen (so in XPERP, [[Handelsregeln]] Spur 2).

## Wo die Listen heute stehen (Stand 21.10.2026, geprüft)

| Spur | Universum | Quelle |
|---|---|---|
| 1 — Marktscanner (OKX Spot) | Liste aus dem Scanner, Live-Zählung 37 Instrumente (07.10.2026) | `Agenten/Handel/scanner/` |
| 2 — XPERP (OKX Futures) | Drei Familien: 115 Krypto, 45 Aktien, 4 Rohstoffe (XAU, XAG, CL, BZ). Vier Rohstoffe sind die aktive Auswahl. | `Agenten/Handel/xperp/wachen.json` |
| 3 — Kraken (Spot, EUR) | Paare in EUR, nur Long | `Agenten/Handel/kraken/wachen.json` |
| Freqtrade-Bots | Whitelists je Bot. Am 11.10.2026 auf Auftrag von Max von 3 auf 10 Paare erweitert. Zurück: nur BTC/ETH/SOL. | `Agenten/Handel/freqtrade/bots.json` |
| Gitter (Papier) | BTC-USDT Spot, einzelnes Paar | `Agenten/Handel/gitter/` |
| Nautilus (Papier) | BTC-USDT-SWAP, einzelnes Paar | `Agenten/Handel/nautilus/` |

Die Backtest-Seite rechnet mit Listen wie `moondev_historie.py --universum 300`
(Top 300, Tageskerzen). Welche Liste gilt, steht in
`MaxHirn/Wiki/Handel/Backtest-Fundament.md` und im Befund zu T-144 (`MaxHirn/Archiv/TASKS.md`).

## Was ein neuer Agent zuerst liest

1. Diese Notiz.
2. Die `wachen.json` der Spur, in der er arbeitet. Sie ist die einzige Wahrheit
   über die Grenzen.
3. [[Handelsregeln]] für die Spuren und Bedingungen.
4. [[Quant-Konzepte-fidetolabs]], wenn es um Methoden auf diesem Universum geht.

## Offen

- Die Listen sind nicht in einer gemeinsamen Übersicht zusammengeführt. Das
  Verzeichnis oben ist eine Momentaufnahme, keine Quelle. Max entscheidet, ob
  daraus ein Skript wird, das die Listen einsammelt und vergleicht.
- Das 300er-Universum ist nicht überall gerechnet. Ob es für die
  Signalwelle wieder aufgezogen wird (1H-Kerzen für 250 Symbole, ~1,5 GB), ist
  ungeklärt.
