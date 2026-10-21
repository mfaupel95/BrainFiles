---
id: 20261021-signature-plot
title: 'Signature Plot auf XBTEUR (21.10.2026)'
tags: [handel, messung]
created: 2026-10-21
updated: 2026-10-21
related: [20261021-quant-konzepte, 20261021-handelsuniversum, 20260902-handelsregeln]
summary: 'Realized Volatility von XBTEUR über Abtastintervalle, 720 Fünf-Minuten-Kerzen. Zwischen 5 und 60 Minuten flach, kein Rauschaufschlag. Methode und Fallen.'
---

# Signature Plot auf XBTEUR (21.10.2026)

Messung über Abtastintervalle, Quelle [[Quant-Konzepte-fidetolabs]]. Eine
Einzelmessung, kein Dauerbefund.

**Warum:** Ein zu feines Sampling kann die gemessene Volatilität aufblasen
(Bid-Ask-Rauschen). Die Frage war, ob das bei XBTEUR ein Problem ist, bevor
Risikozahlen aus Kursen rechnen.

## Daten und Methode

- **720 Fünf-Minuten-Kerzen**, knapp 60 Stunden (Stand 21.10.2026), direkt von
  der öffentlichen Kraken-API: `https://api.kraken.com/0/public/OHLC?pair=XBTEUR&interval=5`.
  Kein Zugangsschlüssel nötig.
- Realized Volatility aus Log-Renditen der Schlusskurse, annualisiert.
  Für jedes Intervall werden alle Startversätze gemittelt.

| Abtastintervall | Renditen | Volatilität (annualisiert) |
|---|---|---|
| 5 min | 719 | 35,5 % |
| 10 min | 359 | 34,8 % |
| 15 min | 239 | 34,6 % |
| 20 min | 179 | 33,3 % |
| 30 min | 119 | 33,3 % |
| 60 min | 59 | 33,0 % |
| 120 min | 29 | 29,8 % (schwach, wenige Renditen) |

## Einordnung

- Zwischen 5 und 60 Minuten ist die Kurve flach. Für XBTEUR über diesen Zeitraum
  ist 5-Minuten-Sampling ausreichend. Feineres Sampling bringt keine verlässlichere
  Zahl.
- Ein Rauschaufschlag wie im Reel (Faktor 2,4) zeigt sich hier nicht. Ob er bei
  Sekundendaten auftritt, ist offen.
- Die Annualisierung einer kurzen Stichprobe ist eine Extrapolation. Für
  Risikomodelle reicht eine Messung über Tage nicht. Monate fehlen.

## Fallen

- **Die 2-Stunden-Stichprobe täuscht.** Mit 120 Minutenkerzen (15:13 bis 17:12)
  ergab sich 63 % bei 1 Minute, rund 50 % bei 3 bis 5 Minuten. Die Stichprobe
  enthielt einen Kursrutsch und einen Spike. Die 60-Stunden-Messung glättet das.
- **MCP-Ausgabe zu groß.** Der Kraken-MCP-Server liefert nur die jüngsten N
  Kerzen. Ab etwa 120 bis 150 Kerzen wird die Antwort in eine Datei geschrieben,
  die sich nicht lesen lässt. Lange Reihen deshalb per curl holen (siehe
  [[Verbindungen]]).
- **Keine öffentlichen Tickdaten** über die verfügbaren Kraken-Werkzeuge. Der
  Trades-Endpunkt liefert nur eigene Fills.

## Nächster Schritt, falls wiederholt

Dieselbe Messung über mehrere Wochen, und zwar mit einer Datenquelle, die
Sekunden- oder Tickdaten liefert. Dann lässt sich die Reel-Behauptung (Rauschen
bei Sekundensampling) prüfen. Das Universum muss im Lauf vermerkt werden
([[Handelsuniversum]]).
